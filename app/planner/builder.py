"""Biến kế hoạch dựng (EditPlan) + kết quả phân tích thành draft CapCut qua DraftWriter.

Code tự làm những việc cần chính xác: phụ đề từ transcript theo từ, vị trí chữ trong vùng an toàn,
crop bám chủ thể, ducking nhạc theo khoảng có thoại. Tài nguyên không có (SFX, nhạc) được ghi vào
danh sách cần bổ sung thay vì bịa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app import config
from app.capcut_writer import (
    SEC, DraftTemplate, DraftWriter, Keyframe, TextBackground, TextStyle, VideoSource, block_crop,
)
from app.capcut_writer.layout import band_centers
from app.director.schemas import EditPlan, HookOption, Understanding
from app.planner.subtitles import build_cues, speech_intervals
from app.planner.timeline import TimeMap


@dataclass
class BuildResult:
    writer: DraftWriter
    duration_us: int
    missing_assets: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _style(d: dict) -> TextStyle:
    bg = d.get("background")
    return TextStyle(size=d.get("size", 12), color=tuple(d.get("color", (1, 1, 1))),
                     stroke_color=tuple(d["stroke_color"]) if d.get("stroke_color") else None,
                     stroke_width=d.get("stroke_width", 0.08),
                     background=TextBackground(**bg) if bg else None)


def _animations(template: DraftTemplate, kinds: list[str]) -> list:
    """Chọn animation chữ trong thư viện theo loại (in / loop / out), mỗi loại một cái."""
    out = []
    for kind in kinds:
        item = next((a for a in template.library if a.kind == "text_animation" and a.category == kind), None)
        if item:
            out.append(item)
    return out


def text_positions(ratio: str, safe: dict) -> dict:
    """y (nửa khung, hướng lên) cho tiêu đề trên, phụ đề dưới, chữ nhấn; x lệch trái né cột nút."""
    y_max = 1 - 2 * safe.get("top", 0.08) - 0.06
    y_min = -1 + 2 * safe.get("bottom", 0.18) + 0.06
    if ratio == "full":
        top, bottom = 0.62, -0.50
    else:
        top, bottom = band_centers(ratio)
    return {"top": min(top, y_max), "bottom": max(bottom, y_min), "center": 0.0,
            "x": -(safe.get("right", 0.12) - safe.get("left", 0.04))}


def duck_keyframes(seg_start: int, seg_end: int, intervals, v_speech: float, v_gap: float,
                   fade_us: int) -> list[Keyframe]:
    """Keyframe âm lượng cho một đoạn nhạc: thấp khi có thoại, cao hơn ở khoảng trống."""
    def level(t: int) -> float:
        return v_speech if any(s <= t < e for s, e in intervals) else v_gap

    points = [(0, level(seg_start))]
    for s, e in intervals:
        for edge in (s, e):
            if seg_start < edge < seg_end:
                rel = edge - seg_start
                before = level(edge - 1)
                after = level(edge)
                if before != after:
                    points.append((max(points[-1][0] + 1, rel - fade_us), before))
                    points.append((rel, after))
    points.append((seg_end - seg_start, level(seg_end - 1)))
    dedup = []
    for t, v in points:
        if not dedup or t > dedup[-1][0]:
            dedup.append((t, v))
    return [Keyframe("volume", t, v) for t, v in dedup]


def zoom_keyframes(zooms, clip, style_zoom: dict) -> list[Keyframe]:
    """Keyframe scale trong một clip (thời gian tương đối với đầu segment)."""
    kfs = [Keyframe("scale", 0, 1.0)]
    dur = clip.out_duration
    for z in sorted(zooms, key=lambda z: z.source_start):
        if not (clip.source_start <= z.source_start < clip.source_end):
            continue
        t0 = round((z.source_start - clip.source_start) / clip.speed * SEC)
        t1 = round((min(z.source_end, clip.source_end) - clip.source_start) / clip.speed * SEC)
        if t0 <= kfs[-1].time:
            t0 = kfs[-1].time + 1
        if t1 <= t0 or t0 >= dur:
            continue
        if z.kind == "punch":
            peak = min(t0 + round(style_zoom.get("punch_in_s", 0.15) * SEC), t1)
            kfs += [Keyframe("scale", t0, 1.0), Keyframe("scale", peak, style_zoom.get("punch_scale", 1.15)),
                    Keyframe("scale", t1, style_zoom.get("punch_scale", 1.15))]
            if t1 + 1 < dur:
                kfs.append(Keyframe("scale", min(dur, t1 + round(0.15 * SEC)), 1.0))
        else:
            kfs += [Keyframe("scale", t0, 1.0), Keyframe("scale", t1, style_zoom.get("slow_scale", 1.1))]
            if t1 + 1 < dur:
                kfs.append(Keyframe("scale", min(dur, t1 + round(0.2 * SEC)), 1.0))
    return kfs if len(kfs) > 1 else []


def subject_center(subjects: dict, start: float, end: float) -> float:
    pts = [cx for t, cx, _ in subjects.get("points", []) if start <= t <= end]
    return sum(pts) / len(pts) if pts else 0.5


def build(plan: EditPlan, u: Understanding, analysis: dict, template: DraftTemplate, drafts_root: Path,
          name: str, style: dict, *, hook: HookOption | None = None, voice: tuple[Path, int] | None = None,
          clean_audio: Path | None = None, video_index: int = 1) -> BuildResult:
    """analysis: kết quả load_analysis(); voice: (đường dẫn, độ dài µs) nếu đã thu."""
    safe = config.load("safe_area")
    sub_cfg = config.load("subtitles")
    sc, tr, subjects = analysis["scenes"], analysis["transcript"], analysis["subjects"]
    src = VideoSource(Path(sc["path"]), sc["width"], sc["height"], round(sc["duration"] * SEC))
    vertical = src.height >= src.width
    w = DraftWriter(template, drafts_root, name)
    missing: list[dict] = []
    notes: list[str] = []
    anims_in = [a for a in template.library if a.kind == "text_animation" and a.category == "in"]
    transition = next((i for i in template.library if i.kind == "transition"), None)
    subtitle_style, emph_style = _style(style.get("subtitle", {})), _style(style.get("emphasis", {}))
    title_style = _style(style.get("title", {}))
    hook_cfg = style.get("hook_text") or style.get("emphasis", {})
    hook_style = _style(hook_cfg)
    hook_anims = _animations(template, hook_cfg.get("animations", ["in"]))

    def ratio_for(clip_ratio) -> str:
        return "full" if vertical else (clip_ratio or plan.default_ratio if plan.default_ratio != "full" else "4:3")

    def crop_for(ratio: str, start: float, end: float):
        if ratio == "full":
            return None
        return block_crop(src.width, src.height, ratio, center_x=subject_center(subjects, start, end))

    # ---------- hook ----------
    hook_us = 0
    if hook is not None:
        hcfg = style.get("hook", {})
        want = voice[1] + 200_000 if voice else round(hcfg.get("min_s", 3.0) * SEC)
        hook_us = max(round(hcfg.get("min_s", 3.0) * SEC), want)
        if voice and voice[1] > hcfg.get("max_s", 5.0) * SEC:
            notes.append(f"Voice hook dài {voice[1] / SEC:.1f}s, vượt {hcfg.get('max_s', 5.0)}s khuyến nghị.")
        h_start = min(hook.footage.start, max(0.0, sc["duration"] - hook_us / SEC))
        ratio = ratio_for(None)
        w.add_video(src, target_start=0, duration=hook_us, source_start=round(h_start * SEC),
                    crop=crop_for(ratio, h_start, h_start + hook_us / SEC), volume=0.15,
                    keyframes=[Keyframe("scale", 0, 1.0), Keyframe("scale", hook_us, 1.12)],
                    transition=transition)
        pos = text_positions(ratio, safe)
        w.add_text(hook.onscreen_text, start=0, duration=hook_us, x=pos["x"], y=pos["top"], style=hook_style,
                   animations=hook_anims)
        if voice:
            w.add_local_audio(voice[0], voice[1], target_start=0, duration=voice[1])
        else:
            missing.append({"kind": "voice", "what": f"video{video_index:02d}_hook.wav", "video": video_index,
                            "at_s": 0.0, "purpose_vi": f"Voice hook: {hook.line}"})

    # ---------- clip chính ----------
    tmap = TimeMap(plan.clips, offset_us=hook_us)
    for clip, p in zip(plan.clips, tmap.placed):
        ratio = ratio_for(clip.ratio)
        w.add_video(src, target_start=p.out_start, duration=p.out_duration,
                    source_start=round(clip.source_start * SEC), speed=clip.speed,
                    crop=crop_for(ratio, clip.source_start, clip.source_end),
                    volume=0.0 if clean_audio else 1.0,
                    keyframes=zoom_keyframes(plan.zooms, p, style.get("zoom", {})) or None)
        if clean_audio:
            w.add_local_audio(clean_audio, src.duration, target_start=p.out_start, duration=p.out_duration,
                              source_start=round(clip.source_start * SEC), speed=clip.speed)

    # ---------- chữ ----------
    main_ratio = ratio_for(None)
    pos = text_positions(main_ratio, safe)
    lang = u.language
    max_chars = style.get("subtitle", {}).get("max_chars", {}).get(lang) or \
        sub_cfg.get("limits", {}).get(lang, {}).get("max_chars_per_line", 16)
    cues = build_cues(tr.get("segments", []), tmap, lang, max_chars, min_cue_s=sub_cfg.get("min_cue_s", 0.35),
                      gap_merge_s=sub_cfg.get("gap_merge_s", 0.15), corrections=u.name_corrections)
    for c in cues:
        w.add_text(c.text, start=c.start, duration=c.end - c.start, x=pos["x"], y=pos["bottom"],
                   style=subtitle_style)
    for e in plan.emphasis:
        t = tmap.to_out(e.source_time)
        if t is None:
            continue
        dur = min(round(e.duration * SEC), tmap.end - t)
        w.add_text(e.text, start=t, duration=dur, x=pos["x"], y=pos["center"] if e.position == "center"
                   else pos["top"], style=emph_style, animations=anims_in[:1])
    if plan.title_top:
        w.add_text(plan.title_top, start=hook_us, duration=tmap.end - hook_us, x=pos["x"], y=pos["top"],
                   style=title_style)

    # ---------- SFX: chưa có kho → ghi danh sách cần bổ sung ----------
    for s in plan.sfx:
        t = tmap.to_out(s.source_time)
        if t is not None:
            missing.append({"kind": "sfx", "what": s.kind, "video": video_index, "at_s": round(t / SEC, 2),
                            "purpose_vi": s.reason_vi})

    # ---------- nhạc nền + ducking ----------
    music = next((m for m in template.library if m.kind == "music" and m.name == plan.music.name), None)
    if music is None:
        missing.append({"kind": "music", "what": plan.music.mood_vi, "video": video_index, "at_s": 0.0,
                        "purpose_vi": f"Nhạc nền ({plan.music.energy}) — không có bài phù hợp trong danh mục"})
    else:
        mcfg = style.get("music", {})
        intervals = speech_intervals(cues)
        if hook is not None:
            intervals = [(0, hook_us), *intervals]  # hạ nhạc dưới voice hook
        m_dur = music.material.get("duration", 0)
        t = 0
        while m_dur > 0 and t < tmap.end:
            seg_len = min(m_dur, tmap.end - t)
            w.add_music(music, target_start=t, duration=seg_len,
                        keyframes=duck_keyframes(t, t + seg_len, intervals, mcfg.get("volume_speech", 0.12),
                                                 mcfg.get("volume_gap", 0.35), round(mcfg.get("fade_s", 0.25) * SEC)))
            t += seg_len

    return BuildResult(writer=w, duration_us=tmap.end, missing_assets=missing, notes=notes)
