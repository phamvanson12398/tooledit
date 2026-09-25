"""Các nhiệm vụ của đạo diễn: chuẩn bị dữ liệu gửi đi (gọn để tiết kiệm hạn mức Pro) và kiểm tra kết quả."""

from __future__ import annotations

import json
from pathlib import Path

from app import config
from app.styles import available_styles, styles_for_prompt
from app.director.base import Director
from app.director.schemas import Understanding, check_ranges


def load_analysis(analysis_dir: Path, footage: int = 0) -> dict:
    def pick(name: str) -> dict:
        items = json.loads((analysis_dir / name).read_text(encoding="utf-8"))
        return next(x for x in items if x.get("footage") == footage)

    frames = [f for f in json.loads((analysis_dir / "frames.json").read_text(encoding="utf-8"))
              if f.get("footage") == footage]
    return {"transcript": pick("transcript.json"), "scenes": pick("scenes.json"),
            "subjects": pick("subjects.json"), "frames": frames}


def format_transcript(segments: list[dict], max_chars: int = 12000) -> str:
    lines = [f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in segments]
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[:max_chars] + "\n...(cắt bớt)"


def pick_evenly(items: list, n: int) -> list:
    if len(items) <= n:
        return list(items)
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def understand(director: Director, analysis_dir: Path, client_style: str | None = None,
               footage: int = 0) -> Understanding:
    a = load_analysis(analysis_dir, footage)
    sc, tr = a["scenes"], a["transcript"]
    n_frames = config.load("director").get("frames", {}).get("understand", 12)
    frames = pick_evenly(a["frames"], n_frames)
    variables = {
        "styles": styles_for_prompt(),
        "client_style": client_style or "chưa có (khách mới, bạn tự chọn)",
        "duration": f"{sc['duration']:.1f}",
        "width": sc["width"], "height": sc["height"], "scene_count": len(sc["scenes"]),
        "language": tr.get("language") or "không rõ",
        "scenes": "\n".join(f"- {s['start']:.1f}–{s['end']:.1f}" for s in sc["scenes"]),
        "transcript": format_transcript(tr.get("segments", [])) or "(không có thoại)",
        "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames),
    }
    images = [analysis_dir / f["file"] for f in frames]
    styles = available_styles()

    def extra(r) -> list[str]:
        errors = check_ranges([*r.key_moments, r.usable_range], sc["duration"], "mốc")
        if r.suggested_style not in styles:
            errors.append(f"suggested_style '{r.suggested_style}' không có; chọn một trong: {', '.join(styles)}")
        return errors

    return director.run("understand", variables, Understanding, images, extra_check=extra)


def apply_name_corrections(text: str, corrections) -> str:
    """Thay tên nhận dạng sai bằng tên đúng (dùng cho phụ đề)."""
    for c in corrections:
        if c.wrong:
            text = text.replace(c.wrong, c.right)
    return text


# ---------------- Hook và kế hoạch dựng ----------------

LANGUAGE_NAMES = {"ja": "tiếng Nhật", "ko": "tiếng Hàn", "en": "tiếng Anh"}
HOOK_MAX_CHARS = {"ja": 32, "ko": 30, "en": 70}  # đọc được trong ~4 giây


def _segments_in(segments: list[dict], start: float, end: float) -> list[dict]:
    return [s for s in segments if s["end"] > start and s["start"] < end]


def _shared_context(u, segments: list[dict]) -> dict:
    return {
        "summary": u.summary_vi,
        "sensitive_notes": "\n".join(f"- {n}" for n in u.sensitive_notes_vi) or "(không có)",
        "name_corrections": "\n".join(f"- {c.wrong} → {c.right}" for c in u.name_corrections) or "(không có)",
        "key_moments": "\n".join(f"- {m.start:.1f}–{m.end:.1f}s: {m.why_vi}" for m in u.key_moments),
        "transcript": format_transcript(
            [{**s, "text": apply_name_corrections(s["text"], u.name_corrections)} for s in segments]
        ) or "(không có thoại)",
        "range": f"{u.usable_range.start:.1f}–{u.usable_range.end:.1f}",
    }


def for_video(u, video: dict):
    """Understanding thu hẹp về một video (khi chia video): đoạn dùng được, tóm tắt, khoảnh khắc trong đoạn."""
    from app.director.schemas import TimeRange

    start, end = float(video["start"]), float(video["end"])
    moments = [m for m in u.key_moments if m.end > start and m.start < end]
    summary = video.get("summary_vi") or u.summary_vi
    return u.model_copy(update={"usable_range": TimeRange(start=start, end=end), "key_moments": moments or
                                u.key_moments[:1], "summary_vi": summary})


def make_segments(director: Director, analysis_dir: Path, u, footage: int = 0):
    """Chia footage dài thành nhiều video độc lập 60–150s (mục 4)."""
    from app.director.schemas import SegmentPlan, check_segments

    cfg = config.load("split")
    a = load_analysis(analysis_dir, footage)
    duration = a["scenes"]["duration"]
    segs = _segments_in(a["transcript"].get("segments", []), u.usable_range.start, u.usable_range.end)
    min_raw, max_raw = cfg.get("min_raw_s", 55), cfg.get("max_raw_s", 300)
    variables = {**_shared_context(u, segs), "duration": f"{duration:.1f}",
                 "min_video_s": cfg.get("min_video_s", 60), "max_video_s": cfg.get("max_video_s", 150),
                 "min_raw_s": min_raw, "max_raw_s": max_raw,
                 "scenes": "\n".join(f"- {s['start']:.1f}–{s['end']:.1f}" for s in a["scenes"]["scenes"]) or "(không có)",
                 "transcript": format_transcript(
                     [{**s, "text": apply_name_corrections(s["text"], u.name_corrections)} for s in segs],
                     max_chars=cfg.get("transcript_max_chars", 30000)) or "(không có thoại)"}
    return director.run("segment", variables, SegmentPlan,
                        extra_check=lambda r: check_segments(r, duration, u.usable_range, min_raw, max_raw))


def make_hooks(director: Director, analysis_dir: Path, u, video_index: int = 1,
               preferred_hooks: list[str] | None = None, footage: int = 0, restrict: bool = False):
    """restrict=True (khi chia video): footage và nguồn của hook phải nằm trong đoạn của video này."""
    from app.director.schemas import HookSet, check_hooks

    a = load_analysis(analysis_dir, footage)
    duration = a["scenes"]["duration"]
    segs = _segments_in(a["transcript"].get("segments", []), u.usable_range.start, u.usable_range.end)
    max_chars = HOOK_MAX_CHARS.get(u.language, 40)
    variables = {**_shared_context(u, segs), "video_index": video_index,
                 "language_name": LANGUAGE_NAMES.get(u.language, u.language), "max_chars": max_chars,
                 "preferred_hooks": ", ".join(preferred_hooks or []) or "chưa có"}
    lo, hi = u.usable_range.start - 0.5, u.usable_range.end + 0.5

    def extra(r) -> list[str]:
        errors = check_hooks(r, duration, max_chars)
        if r.video_index != video_index:
            errors.append(f"video_index phải là {video_index}")
        if restrict:
            for i, o in enumerate(r.options, 1):
                for what, t in (("footage", o.footage), ("nguồn", o.source)):
                    if t.start < lo or t.end > hi:
                        errors.append(f"hook {i}: {what} {t.start:.1f}–{t.end:.1f}s nằm ngoài video này "
                                      f"({u.usable_range.start:.1f}–{u.usable_range.end:.1f}s)")
        return errors

    return director.run("hooks", variables, HookSet, extra_check=extra)


def make_plan(director: Director, analysis_dir: Path, u, style: dict, *, hook=None, hook_s: float = 0.0,
              music_items: list | None = None, sfx_items: list | None = None, decor_items: list | None = None,
              business: bool = False,
              reframe: bool = False, default_ratio: str = "4:3", video_index: int = 1, footage: int = 0):
    from app import config
    from app.director.schemas import EditPlan, check_plan, check_titles

    from app.styles import layout_for

    lay = layout_for(style)
    four = bool(lay and lay.get("titles"))
    fixed = lay is not None  # bố cục cố định: không chọn khung 4:3 / 1:1
    title_max = ((lay or {}).get("title_max_chars") or {}).get(u.language, 12)
    a = load_analysis(analysis_dir, footage)
    images = []
    arrow_brief = "(kiểu dựng này không dùng mũi tên — để `arrows` rỗng)"
    if style.get("arrows"):
        n = config.load("director").get("frames", {}).get("plan", 10)
        lo, hi = u.usable_range.start, u.usable_range.end
        pool = [f for f in a["frames"] if lo <= f["t"] <= hi] or a["frames"]
        near = [min(pool, key=lambda f, t=m.start: abs(f["t"] - t)) for m in u.key_moments] if pool else []
        chosen = {f["file"]: f for f in near + pick_evenly(pool, n)}
        frames = sorted(chosen.values(), key=lambda f: f["t"])
        images = [analysis_dir / f["file"] for f in frames]
        arrow_brief = ARROW_BRIEF + "\n" + "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames)
    sc = a["scenes"]
    duration = sc["duration"]
    vertical = sc["height"] > sc["width"]
    segs = _segments_in(a["transcript"].get("segments", []), u.usable_range.start, u.usable_range.end)
    music_lines = [
        f"- {m.name} ({m.category}{', tâm trạng: ' + m.mood if m.mood else ''}"
        f"{', Commercial' if m.commercial else ''}{', Pro' if m.is_vip else ''}, "
        f"{m.material.get('duration', 0) / 1e6:.0f}s)"
        for m in (music_items or [])
    ]
    sfx_lines = [f"- {m.name}{' (' + m.mood + ')' if m.mood else ''}" for m in (sfx_items or [])]
    decor = {k: [i for i in (decor_items or []) if i.kind == k] for k in ("video_effect", "sticker", "transition", "filter")}

    def lines(kind: str) -> str:
        return "\n".join(f"- {i.name}{' (' + i.category + ')' if i.category else ''}" for i in decor[kind]) or "(trống)"
    b = u.burned_in_text
    variables = {
        **_shared_context(u, segs), "video_index": video_index,
        "style_name": style.get("name", ""), "style_description": style.get("description_vi", ""),
        "style_brief": style.get("director_brief", ""), "hook_s": f"{hook_s:.1f}",
        "width": sc["width"], "height": sc["height"],
        "default_ratio": (f"{lay['block_ratio']} (bố cục cố định)" if fixed else
                          ("full (footage dọc)" if vertical else default_ratio)),
        "reframe": "không — bố cục cố định" if fixed else
        ("có — chọn 4:3 hoặc 1:1 cho từng clip" if reframe else "không — mọi clip dùng khung mặc định"),
        "layout_brief": (FOUR_TITLES_BRIEF.format(max_chars=title_max,
                                                  language=LANGUAGE_NAMES.get(u.language, u.language))
                         if four else ("- Bố cục không có dòng tiêu đề: để `title_top`, `titles_top`, `titles_bottom` rỗng."
                                       if fixed else "- `title_top`: tiêu đề cố định dải trên (có thể rỗng).")),
        "arrow_brief": arrow_brief,
        "burned_in": (f"có, ở {', '.join(b.regions)}. {b.note_vi}" if b.present else "không"),
        "music_list": "\n".join(music_lines) or "(không có bài nào — đặt name = null)",
        "sfx_list": "\n".join(sfx_lines) or "(kho SFX trống — đặt name = null, tool sẽ ghi vào danh sách cần bổ sung)",
        "effect_list": lines("video_effect"), "sticker_list": lines("sticker"),
        "transition_list": lines("transition"), "filter_list": lines("filter"),
        "decor_brief": style.get("decor_brief", ""),
        "business_note": "Khách là doanh nghiệp: CHỈ chọn bài có nhãn Commercial." if business else "",
        "hook": (f"{hook.line} ({hook.line_vi}) — footage {hook.footage.start:.1f}–{hook.footage.end:.1f}s"
                 if hook else "không có hook"),
        "scenes": "\n".join(f"- {s['start']:.1f}–{s['end']:.1f}" for s in sc["scenes"]),
    }
    names = {m.name for m in (music_items or [])}
    sfx_names = {m.name for m in (sfx_items or [])}
    commercial = {m.name for m in (music_items or []) if m.commercial}

    def extra(plan) -> list[str]:
        errors = check_plan(plan, min(duration, u.usable_range.end + 0.5), hook_s,
                            available=u.usable_range.end - u.usable_range.start)
        if any(c.source_start < u.usable_range.start - 0.5 for c in plan.clips):
            errors.append(f"có clip bắt đầu trước đoạn dùng được ({u.usable_range.start:.1f}s)")
        if plan.music.name and plan.music.name not in names:
            errors.append(f"bài nhạc '{plan.music.name}' không có trong danh sách")
        for sfx in plan.sfx:
            if sfx.name and sfx.name not in sfx_names:
                errors.append(f"SFX '{sfx.name}' không có trong kho SFX")
        for kind, used in (("video_effect", [e.name for e in plan.effects]), ("sticker", [x.name for x in plan.stickers]),
                           ("transition", [t.name for t in plan.transitions]),
                           ("filter", [plan.filter] if plan.filter else [])):
            valid = {i.name for i in decor[kind]}
            errors += [f"'{n}' không có trong kho {kind}" for n in used if n not in valid]
        if business and plan.music.name and plan.music.name not in commercial:
            errors.append(f"khách doanh nghiệp: bài '{plan.music.name}' không có nhãn Commercial")
        if four:
            errors += check_titles(plan, title_max)
        if not style.get("arrows") and plan.arrows:
            errors.append("kiểu dựng này không dùng mũi tên: để `arrows` rỗng")
        if not reframe and not fixed and any(c.ratio and c.ratio != plan.default_ratio for c in plan.clips):
            errors.append("không bật đổi khung theo cảnh: mọi clip phải dùng default_ratio (ratio = null)")
        if plan.video_index != video_index:
            errors.append(f"video_index phải là {video_index}")
        return errors

    return director.run("plan", variables, EditPlan, images, extra_check=extra)


FOUR_TITLES_BRIEF = """- Bố cục CỐ ĐỊNH của mọi video (theo video mẫu chủ dự án chọn): nền đen, khối video 16:9 ở giữa,
  2 dòng tiêu đề CHỮ RẤT TO phía trên (`titles_top`) và 2 dòng phía dưới (`titles_bottom`), hiện suốt video.
  Phụ đề thoại nằm trong khối video (code tự làm). `default_ratio` = "16:9", mọi clip `ratio` = null.
- `titles_top` (2 dòng): tình huống / câu gợi tò mò, dòng 1 mở (có thể kết bằng "…"), dòng 2 là chi tiết bất ngờ.
  Ví dụ tiếng Nhật: ["大事な試合の前に…", "隣室から突然流れる演歌"].
- `titles_bottom` (2 dòng): nhân vật / kết luận về người trong video. Ví dụ: ["全くぶれない男だった", "亜細亜大のキャプテン"].
- Mỗi dòng tối đa {max_chars} ký tự, viết bằng {language} tự nhiên kiểu tiêu đề TikTok bản xứ, không xuống dòng.
  Phải ĐÚNG nội dung có thật trong footage; không hứa điều video không có; không lộ hết "lời giải".
- `topic_label`: nhãn ngắn chủ đề đoạn nói chuyện (ví dụ "同期のパンチ佐藤さんについて"), hoặc rỗng nếu footage đã có sẵn.
  `title_top` để rỗng."""


ARROW_BRIEF = """- `arrows`: mũi tên xanh chỉ ĐÚNG chi tiết mà lời bình đang nói tới (găng tay tung đòn, chân bước, bóng, cầu thủ),
  mỗi 2–5 giây khi có chi tiết đáng chỉ; không chỉ khi không chắc vị trí. `x`,`y` là vị trí điểm cần chỉ trong
  KHUNG HÌNH GỐC (0–1), ước lượng từ khung hình gần mốc đó nhất (mở file bằng Read để xem); `points` là hướng mũi tên
  chỉ tới. Chi tiết di chuyển nhanh → mũi tên ngắn (duration 0.8–1.5). Khung hình có sẵn:"""


MARKETS = {"ja": "TikTok Nhật Bản", "ko": "TikTok Hàn Quốc", "en": "TikTok tiếng Anh"}


def make_captions(director: Director, analysis_dir: Path, u, plan, *, hook=None, video_index: int = 1,
                  footage: int = 0):
    from app.director.schemas import Captions, check_captions

    a = load_analysis(analysis_dir, footage)
    kept = [s for s in a["transcript"].get("segments", [])
            if any(s["end"] > c.source_start and s["start"] < c.source_end for c in plan.clips)]
    variables = {**_shared_context(u, kept), "video_index": video_index,
                 "language_name": LANGUAGE_NAMES.get(u.language, u.language),
                 "market": MARKETS.get(u.language, "TikTok"),
                 "hook": f"{hook.line} ({hook.line_vi})" if hook else "không có hook"}
    return director.run("captions", variables, Captions,
                        extra_check=lambda r: check_captions(r)
                        + ([] if r.video_index == video_index else [f"video_index phải là {video_index}"]))


def captions_text(c) -> str:
    """Nội dung captions.txt: bản đăng (ngôn ngữ video) + bản dịch tiếng Việt."""
    return "\n".join([
        "=== ĐĂNG TIKTOK (copy nguyên phần này) ===",
        c.caption,
        "",
        " ".join(c.hashtags),
        "",
        "=== DỊCH TIẾNG VIỆT (không đăng) ===",
        c.caption_vi,
        "",
        *[f"{h} = {vi}" for h, vi in zip(c.hashtags, c.hashtags_vi)],
        "",
        f"Ghi chú editor: {c.editor_notes}",
    ]) + "\n"
