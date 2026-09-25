"""Biến kế hoạch dựng (EditPlan) + kết quả phân tích thành draft CapCut qua DraftWriter.

Code tự làm những việc cần chính xác: phụ đề từ transcript theo từ, vị trí chữ trong vùng an toàn,
crop bám chủ thể, ducking nhạc theo khoảng có thoại. Tài nguyên không có (SFX, nhạc) được ghi vào
danh sách cần bổ sung thay vì bịa.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path

from app import config
from app.capcut_writer import (
    SEC, DraftTemplate, DraftWriter, Keyframe, TextBackground, TextStyle, VideoSource, block_crop,
)
from app.capcut_writer.layout import band_centers, fit_scale, row_to_y
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


def layout_for(style: dict) -> dict | None:
    """Cấu hình bố cục 4 dòng tiêu đề (config/layout.yaml), hoặc None nếu dùng bố cục cũ (classic)."""
    lay = config.load("layout")
    if lay.get("preset", "four_titles") != "four_titles" or style.get("layout") == "classic":
        return None
    return lay.get("four_titles", {})


def four_title_positions(four: dict) -> dict:
    """y cho phụ đề / chữ nhấn / nhãn trong khối video giữa màn (bố cục 4 dòng tiêu đề)."""
    return {"top": row_to_y(four.get("topic_row", 0.362) + 0.05), "bottom": row_to_y(four.get("subtitle_row", 0.612)),
            "center": row_to_y(four.get("emphasis_row", 0.5)), "x": 0.0}


def add_title_lines(w: DraftWriter, plan: EditPlan, four: dict, start: int, end: int) -> int:
    """2 dòng tiêu đề trên + 2 dòng dưới, cố định suốt video, tự canh cỡ cho dòng tràn gần hết chiều ngang."""
    top = [t for t in plan.titles_top if t.strip()] or ([plan.title_top] if plan.title_top.strip() else [])
    bottom = [t for t in plan.titles_bottom if t.strip()]
    rows = four.get("title_rows", [0.094, 0.262, 0.745, 0.893])
    styles = four.get("title_styles") or [{}]
    size = four.get("title_size", 30)
    placed = 0
    for slot, text in list(zip((0, 1), top[:2])) + list(zip((2, 3), bottom[:2])):
        st = dataclasses.replace(_style(styles[slot % len(styles)]), size=size, bold=True)
        scale = fit_scale(text, size, four.get("title_width", 0.94), four.get("char_width_per_size", 0.0017),
                          four.get("title_scale_max", 2.2))
        w.add_text(text, start=start, duration=end - start, x=0.0, y=row_to_y(rows[slot]), scale=scale, style=st)
        placed += 1
    return placed


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

    four = layout_for(style)
    if four:
        subtitle_style = dataclasses.replace(_style(four.get("subtitle", {})), bold=True)

    def ratio_for(clip_ratio) -> str:
        if four:
            return four.get("block_ratio", "16:9")
        return "full" if vertical else (clip_ratio or plan.default_ratio if plan.default_ratio != "full" else "4:3")

    bg = config.load("capcut").get("background", {"type": "blur", "blur": 0.375})

    def bg_kwargs(ratio: str) -> dict:
        if four:
            return {"background_color": four.get("background_color", "#000000FF")}
        if ratio == "full" or bg.get("type") == "none":
            return {}
        if bg.get("type") == "color":
            return {"background_color": bg.get("color", "#000000FF")}
        return {"background_blur": bg.get("blur", 0.375)}

    def positions(ratio: str) -> dict:
        return four_title_positions(four) if four else text_positions(ratio, safe)

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
                    transition=transition, **bg_kwargs(ratio))
        pos = positions(ratio)
        w.add_text(hook.onscreen_text, start=0, duration=hook_us, x=pos["x"], y=pos["center"] if four else pos["top"],
                   style=hook_style, animations=hook_anims)
        if voice:
            w.add_local_audio(voice[0], voice[1], target_start=0, duration=voice[1])
        else:
            missing.append({"kind": "voice", "what": f"video{video_index:02d}_hook.wav", "video": video_index,
                            "at_s": 0.0, "purpose_vi": f"Voice hook: {hook.line}"})

    # ---------- clip chính ----------
    tmap = TimeMap(plan.clips, offset_us=hook_us)
    replay_cfg = style.get("replay_label") or {}
    replay_text = (replay_cfg.get("text") or {}).get(u.language, "REPLAY")
    replay_style = _style(replay_cfg) if replay_cfg else emph_style
    lib = {(i.kind, i.name): i for i in template.library}
    trans_after = {t.after_clip: lib.get(("transition", t.name)) for t in plan.transitions}
    for idx, (clip, p) in enumerate(zip(plan.clips, tmap.placed)):
        ratio = ratio_for(clip.ratio)
        kfs = zoom_keyframes(plan.zooms, p, style.get("zoom", {})) if not clip.replay else \
            [Keyframe("scale", 0, 1.0), Keyframe("scale", p.out_duration, style.get("zoom", {}).get("slow_scale", 1.12))]
        w.add_video(src, target_start=p.out_start, duration=p.out_duration,
                    source_start=round(clip.source_start * SEC), speed=clip.speed,
                    crop=crop_for(ratio, clip.source_start, clip.source_end),
                    volume=0.0 if (clean_audio or clip.replay) else 1.0,
                    keyframes=kfs or None, transition=trans_after.get(idx), **bg_kwargs(ratio))
        if clean_audio and not clip.replay:  # replay quay chậm: tắt tiếng gốc, để nhạc/SFX dẫn
            w.add_local_audio(clean_audio, src.duration, target_start=p.out_start, duration=p.out_duration,
                              source_start=round(clip.source_start * SEC), speed=clip.speed)
        if clip.replay:
            rpos = positions(ratio)
            w.add_text(replay_text, start=p.out_start, duration=p.out_duration, x=rpos["x"], y=rpos["top"],
                       style=replay_style, animations=anims_in[:1])

    # ---------- chữ ----------
    main_ratio = ratio_for(None)
    pos = positions(main_ratio)
    lang = u.language
    max_chars = style.get("subtitle", {}).get("max_chars", {}).get(lang) or \
        sub_cfg.get("limits", {}).get(lang, {}).get("max_chars_per_line", 16)
    cues = build_cues(tr.get("segments", []), tmap, lang, max_chars, min_cue_s=sub_cfg.get("min_cue_s", 0.35),
                      gap_merge_s=sub_cfg.get("gap_merge_s", 0.15), corrections=u.name_corrections)
    for c in cues:
        w.add_text(c.text, start=c.start, duration=c.end - c.start, x=pos["x"], y=pos["bottom"],
                   style=subtitle_style)
    palette = [tuple(c) for c in style.get("emphasis_palette") or []] or [emph_style.color]
    emph_anims = _animations(template, style.get("emphasis", {}).get("animations", ["in"]))
    for i, e in enumerate(plan.emphasis):
        t = tmap.to_out(e.source_time)
        if t is None:
            continue
        dur = min(round(e.duration * SEC), tmap.end - t)
        colored = dataclasses.replace(emph_style, color=palette[i % len(palette)])
        w.add_text(e.text, start=t, duration=dur, x=pos["x"], y=pos["center"] if e.position == "center"
                   else pos["top"], style=colored, animations=emph_anims)

    # ---------- trang trí: hiệu ứng hình, sticker, filter ----------
    corners = {"top_left": (-0.55, 0.55), "top_right": (0.45, 0.55), "center": (0.0, 0.25),
               "bottom_left": (-0.55, -0.3), "bottom_right": (0.45, -0.3)}
    if four:  # trong khối video giữa màn, không đè 4 dòng tiêu đề
        corners = {"top_left": (-0.62, 0.2), "top_right": (0.62, 0.2), "center": (0.0, 0.0),
                   "bottom_left": (-0.62, -0.16), "bottom_right": (0.62, -0.16)}
    for e in plan.effects:
        item, t = lib.get(("video_effect", e.name)), tmap.to_out(e.source_time)
        if item and t is not None:
            w.add_effect(item, start=t, duration=min(round(e.duration * SEC), tmap.end - t))
    for st in plan.stickers:
        item, t = lib.get(("sticker", st.name)), tmap.to_out(st.source_time)
        if item and t is not None:
            x, y = corners[st.position]
            w.add_sticker(item, start=t, duration=min(round(st.duration * SEC), tmap.end - t), x=x, y=y, scale=0.55)
    if plan.filter and lib.get(("filter", plan.filter)):
        w.add_filter(lib[("filter", plan.filter)], start=hook_us, duration=tmap.end - hook_us)
    if four:
        if add_title_lines(w, plan, four, 0, tmap.end) < 4:
            notes.append("Kế hoạch dựng thiếu dòng tiêu đề (cần 2 dòng trên + 2 dòng dưới).")
        if plan.topic_label.strip():
            w.add_text(plan.topic_label, start=hook_us, duration=tmap.end - hook_us, x=four.get("topic_x", 0.3),
                       y=row_to_y(four.get("topic_row", 0.362)), style=dataclasses.replace(
                           _style(four.get("topic", {})), bold=True))
    elif plan.title_top:
        w.add_text(plan.title_top, start=hook_us, duration=tmap.end - hook_us, x=pos["x"], y=pos["top"],
                   style=title_style)

    # ---------- SFX: lấy từ kho (CapCut + assets/); không có thì ghi danh sách cần bổ sung ----------
    sfx_lib = {m.name: m for m in template.library if m.kind == "sfx"}
    for s in plan.sfx:
        t = tmap.to_out(s.source_time)
        if t is None:
            continue
        item = sfx_lib.get(s.name or "") or _fallback_sfx(template.library, s.kind)
        if item is not None:
            length = min(item.material.get("duration", SEC), 3 * SEC, max(1, tmap.end - t))
            _add_audio_item(w, item, target_start=t, duration=length, volume=0.8)
        else:
            missing.append({"kind": "sfx", "what": s.kind, "video": video_index, "at_s": round(t / SEC, 2),
                            "purpose_vi": s.reason_vi})

    # ---------- nhạc nền + ducking ----------
    music = next((m for m in template.library if m.kind == "music" and m.name == plan.music.name), None)
    if music is None:  # đạo diễn không chọn được bài → thử nhạc local cùng mức năng lượng
        music = next((m for m in template.library if m.kind == "music" and m.material.get("local")
                      and m.mood == plan.music.energy), None)
    if music is None:
        missing.append({"kind": "music", "what": plan.music.mood_vi, "energy": plan.music.energy,
                        "video": video_index, "at_s": 0.0,
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
            _add_audio_item(w, music, target_start=t, duration=seg_len,
                        keyframes=duck_keyframes(t, t + seg_len, intervals, mcfg.get("volume_speech", 0.12),
                                                 mcfg.get("volume_gap", 0.35), round(mcfg.get("fade_s", 0.25) * SEC)))
            t += seg_len

    return BuildResult(writer=w, duration_us=tmap.end, missing_assets=missing, notes=notes)


def _fallback_sfx(library, kind: str):
    """Đạo diễn không nêu tên (hoặc tên không có trong kho) → lấy SFX cùng loại: file local trong
    assets/sfx/<loại>/ trước, rồi SFX CapCut có tên chứa từ khóa của loại đó."""
    from app.assets.scan import SFX_KEYWORDS

    local = [m for m in library if m.kind == "sfx" and m.material.get("local") and m.mood == kind]
    if local:
        return local[0]
    keys = [k.lower() for k in SFX_KEYWORDS.get(kind, (kind,))]
    return next((m for m in library if m.kind == "sfx" and not m.material.get("local")
                 and any(k in m.name.lower() for k in keys)), None)


def _add_audio_item(w, item, *, target_start: int, duration: int, volume: float = 1.0, keyframes=None):
    """Âm thanh thư viện CapCut → tham chiếu trong draft; file local (assets/) → âm thanh trên máy."""
    if item.material.get("local"):
        return w.add_local_audio(Path(item.material["path"]), item.material["duration"], target_start=target_start,
                                 duration=duration, volume=volume, keyframes=keyframes)
    return w.add_music(item, target_start=target_start, duration=duration, volume=volume, keyframes=keyframes)
