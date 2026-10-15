"""Dựng draft CapCut cho chế độ "CONTENT NHIỀU PHIM TỪ BÀI TIKTOK ẢNH" (chủ dự án yêu cầu 14/10).

Mỗi câu đọc → hình từ ĐÚNG phim của câu đó (nhiều file phim trong một draft):
- câu `video`: cắt cảnh nhanh trong đoạn phim AI đã tìm, tổng đúng bằng câu đọc (cut_pieces — như review);
- câu `freeze` (DỪNG HÌNH): video chạy tới `freeze_t` rồi đứng hình — ảnh tĩnh cắt từ phim (tool tự trích), zoom chậm,
  tiếng "tách" + tên nhân vật hiện lên.
Tiếng phim tắt; giọng đọc + phụ đề + nhạc nền nhẹ (tự hạ dưới giọng); bố cục như review (config/review.yaml → layout);
sang phim mới thì tên phim hiện ở góc trên khối hình.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from app import config
from app.capcut_writer import SEC, Crop, DraftTemplate, DraftWriter, Keyframe, VideoSource, block_crop
from app.capcut_writer.layout import RATIOS, row_to_y
from app.planner.builder import (BuildResult, _add_audio_item, _animations, _fallback_sfx, _style, add_title_lines,
                                 db_to_gain, duck_keyframes, four_title_positions, pick_music)
from app.styles import layout_for


def extract_still(src: Path, at_s: float, dst: Path, crop, width: int) -> tuple[Path, int, int]:
    """Khung hình ở giây at_s (độ phân giải gốc, tối đa 1920 ngang), cắt đúng vùng khối hình. Trả (file, rộng, cao)."""
    import cv2

    from app.analysis import ffmpeg

    raw = dst.with_name(dst.stem + "_raw.jpg")
    if not ffmpeg.extract_frame(src, at_s, raw, min(int(width), 1920), 2):
        raise RuntimeError(f"Không trích được khung hình {at_s:.1f}s của {Path(src).name} để dừng hình")
    img = cv2.imread(str(raw))
    h, w = img.shape[:2]
    x0, x1 = round(crop.left * w), round(crop.right * w)
    y0, y1 = round(crop.top * h), round(crop.bottom * h)
    img = img[y0:y1, x0:x1]
    cv2.imwrite(str(dst), img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    raw.unlink(missing_ok=True)
    return dst, img.shape[1], img.shape[0]


def build_films(idea, picks: dict[int, dict], films: dict[str, dict], template: DraftTemplate, drafts_root: Path,
                name: str, *, language: str, voices: dict[int, tuple[Path, int]], stills_dir: Path,
                vi_subtitles: bool = False, cfg: dict | None = None, keep_frame: bool = False,
                still_fn: Callable | None = None) -> BuildResult:
    """films[key] = {path, width, height, duration (giây), scene_starts}; picks[số câu] = {film, start, end, freeze_t};
    voices[số câu] = (file voice, độ dài µs). Câu chưa có voice tạm tính theo số chữ (dựng thử trước khi thu)."""
    from app.director.films import est_s
    from app.planner.dub_io import split_text, spread_cues
    from app.planner.review_sync import cut_pieces

    cfg = config.load("films") if cfg is None else cfg
    rcfg = config.load("review")
    still_fn = still_fn or extract_still
    if keep_frame and films:  # chủ dự án 15/10: khung video GỐC (theo phim đầu), không cắt, không thu phóng
        from app.capcut_writer.layout import nearest_ratio

        f0 = next(iter(films.values()))
        ratio = nearest_ratio(int(f0["width"]), int(f0["height"]))
        four = layout_for({"layout": rcfg.get("layout", "review_story"), "block_ratio": ratio, "keep_frame": True}) or {}
    else:
        four = layout_for({"layout": rcfg.get("layout", "review_story"), "block_ratio": "9:10"}) or {}
        ratio = four.get("frame_ratio") or four.get("block_ratio", "9:10")
    if ratio not in RATIOS:
        ratio = "9:10"
    bg = four.get("background_color", "#000000FF")
    pos = four_title_positions(four) if four else {"top": 0.5, "bottom": -0.4, "center": 0.0, "x": 0.0}
    sub_style = dataclasses.replace(_style(four.get("subtitle") or {"size": 11}), bold=True)
    max_chars = (four.get("subtitle_max_chars") or {}).get(language, 14)
    label_style = dataclasses.replace(_style({"size": 16, "color": [1, 0.9, 0.2], "stroke_color": [0, 0, 0],
                                              "stroke_width": 0.2}), bold=True)
    film_style = dataclasses.replace(_style(four.get("topic") or {"size": 8}), bold=True)
    anims_in = _animations(template, ["in"])
    gap = float(rcfg.get("voice_gap_s", 0.05))
    lead_cfg = float(cfg.get("freeze_lead_s", 0.8))
    freeze_max = float(cfg.get("freeze_max_s", 3.0))
    zoom = float(cfg.get("freeze_zoom", 1.12))
    titles = {f.key: f.title for f in idea.films}
    sfx_item = next((x for k in cfg.get("freeze_sfx") or ["pop"]
                     if (x := _fallback_sfx(template.library, k)) is not None), None)

    w = DraftWriter(template, drafts_root, name)
    missing, notes, used_local = [], [], []
    spoken: list[tuple[int, int]] = []
    sources: dict[str, VideoSource] = {}
    t, prev_film, n_freeze, frozen_us = 0, None, 0, 0
    stills_dir.mkdir(parents=True, exist_ok=True)

    def source(key: str) -> VideoSource:
        if key not in sources:
            f = films[key]
            sources[key] = VideoSource(Path(f["path"]), int(f["width"]), int(f["height"]), round(float(f["duration"]) * SEC))
        return sources[key]

    for i, ln in enumerate(idea.lines, 1):
        p = picks.get(i)
        if p is None or ln.film not in films:
            notes.append(f"Câu {i}: chưa có cảnh phim — bỏ qua hình câu này.")
            continue
        src = source(ln.film)
        f = films[ln.film]
        crop = Crop() if keep_frame else block_crop(src.width, src.height, ratio)
        v = voices.get(i)
        voice_s = v[1] / SEC if v else est_s(ln.text, language)
        want = voice_s + gap
        want_us = round(want * SEC)
        dur_s = src.duration / SEC
        if ln.shot == "freeze" and p.get("freeze_t") is not None:
            ft = min(max(float(p["freeze_t"]), 0.05), dur_s - 0.05)
            hold = max(0.3, min(want - min(lead_cfg, want * 0.4), freeze_max))
            run = want - hold
            a = max(0.0, ft - run)
            run_us = round((ft - a) * SEC)
            if run_us > 0:
                w.add_video(src, target_start=t, duration=run_us, source_start=round(a * SEC), crop=crop, volume=0.0,
                            background_color=bg)
            hold_us = want_us - run_us
            still, iw, ih = still_fn(src.path, ft, stills_dir / f"{ln.film}_{ft:09.2f}.jpg", crop, src.width)
            w.add_image(still, iw, ih, target_start=t + run_us, duration=hold_us, background_color=bg,
                        keyframes=None if keep_frame or zoom == 1.0 else
                        [Keyframe("scale", 0, 1.0), Keyframe("scale", hold_us, zoom)])
            if ln.label.strip():
                w.add_text(ln.label, start=t + run_us, duration=hold_us, x=pos["x"], y=pos["center"],
                           style=label_style, animations=anims_in[:1])
            if sfx_item is not None:
                _add_audio_item(w, sfx_item, target_start=t + run_us,
                                duration=min(sfx_item.material.get("duration", SEC), hold_us), volume=0.8)
                if sfx_item.material.get("local"):
                    used_local.append(sfx_item.material["path"])
            n_freeze += 1
            frozen_us += hold_us
        else:
            a, b = float(p["start"]), min(float(p["end"]), dur_s)
            pos_t = t
            pieces = cut_pieces(a, b, want, f.get("scene_starts") or [], cut_s=float(cfg.get("cut_s", 2.0)),
                                min_cut_s=float(cfg.get("min_cut_s", 1.0)))
            for k, (pa, pb, sp) in enumerate(pieces):
                # khúc cuối lấp đúng tới hết câu (làm tròn µs không làm lệch giọng với hình)
                d_us = t + want_us - pos_t if k == len(pieces) - 1 else round((pb - pa) / sp * SEC)
                if d_us <= 0:
                    continue
                s_us = min(round(pa * SEC), max(0, src.duration - round(d_us * sp)))
                w.add_video(src, target_start=pos_t, duration=d_us, source_start=s_us, speed=sp, crop=crop,
                            volume=0.0, background_color=bg)
                pos_t += d_us
        if cfg.get("film_label", True) and ln.film != prev_film and titles.get(ln.film):
            w.add_text(titles[ln.film], start=t, duration=min(round(float(cfg.get("film_label_s", 2.5)) * SEC), want_us),
                       x=float(four.get("topic_x", 0.3)), y=row_to_y(float(four.get("topic_row", 0.2))),
                       style=film_style, animations=anims_in[:1])
        prev_film = ln.film
        v_us = round(voice_s * SEC)
        if v:
            w.add_local_audio(v[0], v[1], target_start=t, duration=v[1])
            spoken.append((t, t + v[1]))
        else:
            missing.append({"kind": "voice", "what": f"video01_dub{i:02d}.wav", "video": 1, "at_s": round(t / SEC, 2),
                            "purpose_vi": f"Lời đọc: {ln.text}"})
        for s0, e0, txt in spread_cues(split_text(ln.text, language, max_chars), t, t + v_us):
            w.add_text(txt, start=s0, duration=max(1, e0 - s0), x=pos["x"], y=pos["bottom"], style=sub_style)
        if vi_subtitles and ln.text_vi.strip():
            vcfg = config.load("dub").get("vi_subtitles") or {}
            vi_style = dataclasses.replace(_style({"size": vcfg.get("size", 8), "color": vcfg.get("color", [1, 0.95, 0.4]),
                                                   "stroke_color": [0, 0, 0], "stroke_width": 0.12}), bold=False)
            for s0, e0, txt in spread_cues(split_text(ln.text_vi, "en", int(vcfg.get("max_chars", 34))), t, t + v_us):
                w.add_text(txt, start=s0, duration=max(1, e0 - s0), x=pos["x"],
                           y=pos["bottom"] - float(vcfg.get("gap", 0.075)), style=vi_style)
        t += want_us

    end = t
    if four.get("titles") and add_title_lines(w, SimpleNamespace(titles_top=idea.titles_top, title_top="",
                                                                 titles_bottom=[]), four, 0, end) < 1:
        notes.append("Thiếu dòng tiêu đề.")
    music = pick_music(template, SimpleNamespace(music=idea.music))
    if music is None:
        missing.append({"kind": "music", "what": idea.music.mood_vi, "energy": idea.music.energy, "video": 1,
                        "at_s": 0.0, "purpose_vi": f"Nhạc nền ({idea.music.energy}) — không có bài phù hợp"})
    else:
        acfg = config.load("audio")
        base = float(acfg.get("music_base_db", -5.0))
        hi, lo = db_to_gain(base), db_to_gain(base + float(acfg.get("duck_db", -10.0)))
        m_dur, m_t = music.material.get("duration", 0), 0
        while m_dur > 0 and m_t < end:
            seg = min(m_dur, end - m_t)
            _add_audio_item(w, music, target_start=m_t, duration=seg,
                            keyframes=duck_keyframes(m_t, m_t + seg, spoken, lo, hi, 250_000))
            m_t += seg
        if music.material.get("local"):
            used_local.append(music.material["path"])
    if end:
        notes.insert(0, f"Dựng {len(idea.lines)} câu từ {len(films)} phim, dài {end / SEC:.1f}s; dừng hình {n_freeze} lần "
                        f"({frozen_us / end:.0%} thời lượng).")
    if sfx_item is None and n_freeze:
        missing.append({"kind": "sfx", "what": "pop", "video": 1, "at_s": 0.0,
                        "purpose_vi": "Tiếng 'tách' khi dừng hình — không có SFX pop / ding / whoosh trong kho"})
    return BuildResult(writer=w, duration_us=end, missing_assets=missing, notes=notes, used_local=sorted(set(used_local)))
