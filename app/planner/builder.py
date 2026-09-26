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
from app.styles import layout_for  # dùng chung với bước lập kế hoạch
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


ARROW_ROTATION = {"right": 0, "down_right": 45, "down": 90, "down_left": 135, "left": 180, "up_left": 225,
                  "up": 270, "up_right": 315}  # độ, chiều kim đồng hồ [CẦN KIỂM TRA TRÊN MÁY] chiều xoay của CapCut
ARROW_VECTOR = {"right": (1, 0), "down_right": (0.707, 0.707), "down": (0, 1), "down_left": (-0.707, 0.707),
                "left": (-1, 0), "up_left": (-0.707, -0.707), "up": (0, -1), "up_right": (0.707, -0.707)}


def block_point(fx: float, fy: float, crop, ratio: str, canvas_w: int = 1080, canvas_h: int = 1920):
    """Điểm (fx, fy) 0..1 trên khung gốc → (x, y) nửa khung của CapCut, khi khối video tràn ngang ở giữa màn.
    None nếu điểm nằm ngoài vùng cắt."""
    from app.capcut_writer.layout import block_size

    left, top, right, bottom = (crop.left, crop.top, crop.right, crop.bottom) if crop else (0.0, 0.0, 1.0, 1.0)
    u, v = (fx - left) / (right - left), (fy - top) / (bottom - top)
    if not (0.0 <= u <= 1.0 and 0.0 <= v <= 1.0):
        return None
    bw, bh = block_size(ratio, canvas_w)
    return (u - 0.5) * 2 * bw / canvas_w, -(v - 0.5) * 2 * bh / canvas_h


def arrow_placement(target: tuple[float, float], points: str, offset_px: float,
                    canvas_w: int = 1080, canvas_h: int = 1920) -> tuple[float, float, float]:
    """Tâm mũi tên nằm lùi về phía ngược hướng chỉ, cách điểm cần chỉ offset_px; trả (x, y, góc xoay)."""
    vx, vy = ARROW_VECTOR[points]  # hướng trên màn hình, y hướng xuống
    x = target[0] - vx * offset_px / (canvas_w / 2)
    y = target[1] + vy * offset_px / (canvas_h / 2)
    return x, y, ARROW_ROTATION[points]


def four_title_positions(four: dict) -> dict:
    """y cho phụ đề / chữ nhấn / nhãn trong khối video giữa màn (bố cục cố định)."""
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


def db_to_gain(db: float) -> float:
    """dB → hệ số âm lượng tuyến tính của CapCut (1.0 = 0 dB; -5 dB ≈ 0.562)."""
    return min(1.0, 10 ** (db / 20.0))


def pick_music(template: DraftTemplate, plan: EditPlan):
    """Bài đạo diễn chọn; không có thì nhạc local cùng mức năng lượng; không có nữa thì None."""
    music = next((m for m in template.library if m.kind == "music" and m.name == plan.music.name), None)
    if music is None:
        music = next((m for m in template.library if m.kind == "music" and m.material.get("local")
                      and m.mood == plan.music.energy), None)
    return music


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
          clean_audio: Path | None = None, video_index: int = 1, beats_fn=None) -> BuildResult:
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

    four = layout_for(style)  # bố cục cố định (4 dòng tiêu đề / thể thao) hoặc None = bố cục cũ
    if four and four.get("subtitle"):
        subtitle_style = dataclasses.replace(_style(four["subtitle"]), bold=True)

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
    # ---------- cắt theo nhịp nhạc: dời điểm cắt về beat gần nhất ----------
    music = pick_music(template, plan)
    beats_out: list[float] = []
    bcfg = style.get("beat_sync") or {}
    if bcfg.get("enabled") and music is not None:
        from app.planner.beats import beats_for_music, looped_beats, snap_cuts

        try:
            raw_beats = (beats_fn or beats_for_music)(music)
        except Exception as exc:  # không có FFmpeg / file nhịp hỏng: dựng bình thường, không theo nhịp
            raw_beats = []
            notes.append(f"Không lấy được nhịp của bài '{music.name}': {exc}")
        if raw_beats:
            est_total = hook_us / SEC + sum((c.source_end - c.source_start) / c.speed for c in plan.clips) + 5
            beats_out = looped_beats(raw_beats, music.material.get("duration", 0) / SEC, est_total)
            words = [(wd["start"], wd["end"]) for sg in tr.get("segments", []) for wd in (sg.get("words") or [])]
            clips, n = snap_cuts([c.model_dump() for c in plan.clips], hook_us / SEC, beats_out, words,
                                 sc["duration"], bcfg.get("tolerance_s", 0.3))
            plan = plan.model_copy(update={"clips": [type(plan.clips[0]).model_validate(c) for c in clips]})
            notes.append(f"Cắt theo nhịp nhạc '{music.name}': dời {n}/{max(0, len(clips) - 1)} điểm cắt về đúng beat.")
        else:
            notes.append(f"Bài '{music.name}' chưa có dữ liệu nhịp — không cắt theo nhịp.")
    tmap = TimeMap(plan.clips, offset_us=hook_us)
    replay_cfg = style.get("replay_label") or {}
    replay_text = (replay_cfg.get("text") or {}).get(u.language, "REPLAY")
    replay_style = _style(replay_cfg) if replay_cfg else emph_style
    lib = {(i.kind, i.name): i for i in template.library}
    trans_after = {t.after_clip: lib.get(("transition", t.name)) for t in plan.transitions}
    cam_cfg = style.get("camera") or {}
    camera_on = cam_cfg.get("mode") == "speaker"
    if camera_on:  # góc máy theo người đang nói (podcast)
        from app.planner.camera import persons_from_faces, plan_shots, shot_crop

        faces = subjects.get("faces") or [  # phân tích cũ (chưa có dữ liệu từng mặt): dùng mặt chính
            [t, [[cx - 0.05, cy - 0.08, 0.1, 0.16, 0.0]]] for t, cx, cy in subjects.get("points", [])]
        people = persons_from_faces(faces)
        speech = [{"start": sg["start"], "end": sg["end"]} for sg in tr.get("segments", [])]
        if cam_cfg.get("reactions") and analysis.get("events"):  # giải trí: cắt sang người đang cười
            from app.planner.camera import merge_reactions

            speech = merge_reactions(speech, analysis["events"])
        since_wide, shot_count = 0.0, {"close": 0, "medium": 0, "wide": 0}
    for idx, (clip, p) in enumerate(zip(plan.clips, tmap.placed)):
        ratio = ratio_for(clip.ratio)
        last_trans = trans_after.get(idx)
        if camera_on and not clip.replay and ratio != "full":
            shots, since_wide = plan_shots(clip.source_start, clip.source_end, speech, faces, people, cam_cfg,
                                           opening=idx == 0, since_wide=since_wide)
            bounds = [p.out_start + round((sh.start - clip.source_start) / clip.speed * SEC) for sh in shots] + [p.out_end]
            for j, sh in enumerate(shots):
                sub = dataclasses.replace(p, source_start=sh.start, source_end=sh.end, out_start=bounds[j])
                kfs = zoom_keyframes(plan.zooms, sub, style.get("zoom", {}))
                w.add_video(src, target_start=bounds[j], duration=bounds[j + 1] - bounds[j],
                            source_start=round(sh.start * SEC), speed=clip.speed,
                            crop=shot_crop(sh, people, ratio, src.width, src.height, cam_cfg,
                                           fallback_cx=subject_center(subjects, sh.start, sh.end)),
                            volume=0.0 if clean_audio else 1.0, keyframes=kfs or None,
                            transition=last_trans if j == len(shots) - 1 else None, **bg_kwargs(ratio))
                shot_count[sh.kind] += 1
        else:
            kfs = zoom_keyframes(plan.zooms, p, style.get("zoom", {})) if not clip.replay else \
                [Keyframe("scale", 0, 1.0), Keyframe("scale", p.out_duration, style.get("zoom", {}).get("slow_scale", 1.12))]
            w.add_video(src, target_start=p.out_start, duration=p.out_duration,
                        source_start=round(clip.source_start * SEC), speed=clip.speed,
                        crop=crop_for(ratio, clip.source_start, clip.source_end),
                        volume=0.0 if (clean_audio or clip.replay) else 1.0,
                        keyframes=kfs or None, transition=last_trans, **bg_kwargs(ratio))
        if clean_audio and not clip.replay:  # replay quay chậm: tắt tiếng gốc, để nhạc/SFX dẫn
            w.add_local_audio(clean_audio, src.duration, target_start=p.out_start, duration=p.out_duration,
                              source_start=round(clip.source_start * SEC), speed=clip.speed)
        if clip.replay:
            rpos = positions(ratio)
            w.add_text(replay_text, start=p.out_start, duration=p.out_duration, x=rpos["x"], y=rpos["top"],
                       style=replay_style, animations=anims_in[:1])

    if camera_on:
        notes.append(f"Góc máy theo người nói: {len(people)} người, {shot_count['close']} cảnh cận, "
                     f"{shot_count['medium']} trung, {shot_count['wide']} toàn.")

    # ---------- chữ ----------
    main_ratio = ratio_for(None)
    pos = positions(main_ratio)
    lang = u.language
    max_chars = ((four or {}).get("subtitle_max_chars") or {}).get(lang) or \
        style.get("subtitle", {}).get("max_chars", {}).get(lang) or \
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
        if beats_out:  # chữ nhấn hiện đúng nhịp nhạc
            from app.planner.beats import nearest_beat

            b = nearest_beat(t / SEC, beats_out, bcfg.get("text_tolerance_s", 0.2))
            if b is not None and b * SEC < tmap.end - SEC // 2:
                t = round(b * SEC)
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
    # ---------- mũi tên chỉ chi tiết (kiểu thể thao) ----------
    arrow_cfg = (four or {}).get("arrow") or {}
    arrow_style = dataclasses.replace(_style({"size": 40, "color": [0.2, 1, 0.25], "stroke_color": [0, 0.35, 0.05],
                                              "stroke_width": 0.12, **arrow_cfg}), bold=True)
    for a in plan.arrows:
        t, p = tmap.to_out(a.source_time), tmap.clip_containing(a.source_time)
        if t is None or p is None:
            continue
        ratio = ratio_for(None)
        crop = crop_for(ratio, p.source_start, p.source_end)
        target = block_point(a.x, a.y, crop, ratio) if ratio != "full" else ((a.x - 0.5) * 2, -(a.y - 0.5) * 2)
        if target is None:
            notes.append(f"Mũi tên ở {a.source_time}s chỉ vào chỗ nằm ngoài khung đã cắt — bỏ qua.")
            continue
        x, y, rot = arrow_placement(target, a.points, arrow_cfg.get("offset_px", 120))
        w.add_text(arrow_cfg.get("glyph", "→"), start=t, duration=min(round(a.duration * SEC), tmap.end - t),
                   x=x, y=y, rotation=rot, style=arrow_style, animations=anims_in[:1])

    if plan.filter and lib.get(("filter", plan.filter)):
        w.add_filter(lib[("filter", plan.filter)], start=hook_us, duration=tmap.end - hook_us)
    if four and four.get("titles"):
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
    if music is None:
        missing.append({"kind": "music", "what": plan.music.mood_vi, "energy": plan.music.energy,
                        "video": video_index, "at_s": 0.0,
                        "purpose_vi": f"Nhạc nền ({plan.music.energy}) — không có bài phù hợp trong danh mục"})
    else:
        mcfg = style.get("music", {})
        acfg = config.load("audio")
        base_db = float(acfg.get("music_base_db", -5.0))  # mức gốc khi không có thoại
        duck_db = float(mcfg.get("duck_db", acfg.get("duck_db", -10.0)))  # hạ thêm khi có thoại
        v_gap, v_speech = db_to_gain(base_db), db_to_gain(base_db + duck_db)
        intervals = speech_intervals(cues)
        if hook is not None:
            intervals = [(0, hook_us), *intervals]  # hạ nhạc dưới voice hook
        m_dur = music.material.get("duration", 0)
        t = 0
        while m_dur > 0 and t < tmap.end:
            seg_len = min(m_dur, tmap.end - t)
            _add_audio_item(w, music, target_start=t, duration=seg_len,
                        keyframes=duck_keyframes(t, t + seg_len, intervals, v_speech, v_gap,
                                                 round(mcfg.get("fade_s", 0.25) * SEC)))
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
