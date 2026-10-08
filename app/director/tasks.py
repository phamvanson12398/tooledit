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
    events = None  # None = job cũ chưa dò sự kiện âm thanh
    if (analysis_dir / "audio_events.json").is_file():
        events = pick("audio_events.json").get("events", [])
    return {"transcript": pick("transcript.json"), "scenes": pick("scenes.json"),
            "subjects": pick("subjects.json"), "frames": frames, "events": events}


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
        errors = check_ranges([*r.key_moments, r.usable_range, *r.policy_issues], sc["duration"], "mốc")
        if r.suggested_style not in styles:
            errors.append(f"suggested_style '{r.suggested_style}' không có; chọn một trong: {', '.join(styles)}")
        return errors

    from app.director.policy import add_auto_issues

    u = director.run("understand", variables, Understanding, images, extra_check=extra)
    return add_auto_issues(u, tr.get("segments", []))  # + từ tục máy tự dò trong transcript


def apply_name_corrections(text: str, corrections) -> str:
    """Thay tên nhận dạng sai bằng tên đúng (dùng cho phụ đề)."""
    for c in corrections:
        if c.wrong:
            text = text.replace(c.wrong, c.right)
    return text


# ---------------- Hook và kế hoạch dựng ----------------

LANGUAGE_NAMES = {"ja": "tiếng Nhật", "ko": "tiếng Hàn", "en": "tiếng Anh", "zh": "tiếng Trung"}
HOOK_MAX_CHARS = {"ja": 32, "ko": 30, "en": 70}  # đọc được trong ~4 giây
HOOK_INTRO_MAX_CHARS = {"ja": 45, "ko": 45, "en": 120}  # 1–2 câu đời thường dẫn vào (~4–5 giây)


def _segments_in(segments: list[dict], start: float, end: float) -> list[dict]:
    return [s for s in segments if s["end"] > start and s["start"] < end]


def _shared_context(u, segments: list[dict], events: list[dict] | None = None) -> dict:
    from app.analysis.audio_events import events_for_prompt
    from app.director.policy import policy_for_prompt

    return {
        "translate_note": translate_note(u),
        "policy_cuts": policy_for_prompt(u, u.usable_range.start, u.usable_range.end),
        "audio_events": ("(chưa phân tích — job cũ)" if events is None else
                         events_for_prompt(events, u.usable_range.start, u.usable_range.end)),
        "summary": u.summary_vi,
        "sensitive_notes": "\n".join(f"- {n}" for n in u.sensitive_notes_vi) or "(không có)",
        "name_corrections": "\n".join(f"- {c.wrong} → {c.right}" for c in u.name_corrections) or "(không có)",
        "key_moments": "\n".join(f"- {m.start:.1f}–{m.end:.1f}s: {m.why_vi}" for m in u.key_moments),
        "transcript": format_transcript(
            [{**s, "text": apply_name_corrections(s["text"], u.name_corrections)} for s in segments]
        ) or "(không có thoại)",
        "range": f"{u.usable_range.start:.1f}–{u.usable_range.end:.1f}",
    }


def translate_note(u) -> str:
    """Chế độ Đổi ngôn ngữ: transcript là tiếng gốc, mọi chữ xuất ra viết bằng ngôn ngữ đích."""
    src, dst = u.source_language, u.language
    if src == dst:
        return ""
    s, d = LANGUAGE_NAMES.get(src, src), LANGUAGE_NAMES.get(dst, dst)
    return (f"\n## ĐỔI NGÔN NGỮ: {s} → {d}\nFootage gốc nói {s} (transcript bên dưới là {s}). Bản TikTok này được "
            f"THUYẾT MINH + PHỤ ĐỀ bằng {d} cho khán giả {d}: mọi chữ trên màn hình, tiêu đề, hook, caption, hashtag "
            f"viết bằng {d} — dịch Ý tự nhiên như người bản xứ nói, không dịch từng chữ, không để sót chữ {s}. "
            f"Tên riêng giữ cách đọc quen thuộc với khán giả đích. Nếu footage có chữ {s} in sẵn trên hình, ghi rõ "
            "trong editor_notes để người dùng che trong CapCut.\n" + localize_brief(u))


def localize_brief(u) -> str:
    """Viết theo NƯỚC của khán giả đích (không chỉ dịch chữ): giọng, cách hài, tên riêng, đơn vị, điều nên tránh."""
    if u.source_language == u.language:
        return ""
    m = (config.load("localize").get("markets") or {}).get(u.language) or {}
    if not m:
        return ""
    return (f"\n### BẢN ĐỊA HÓA cho {m.get('audience', u.language)}\n"
            "Viết như một người bản xứ làm video cho chính khán giả nước mình — người xem phải hiểu ngay và thấy gần gũi. "
            "Chi tiết văn hóa của nước gốc mà khán giả đích không biết thì giải thích ngắn hoặc so sánh với thứ quen thuộc "
            "của họ; câu đùa không hợp thì đổi cách nói cho buồn cười theo kiểu nước họ (giữ đúng ý, không bịa sự việc).\n"
            + (m.get("brief") or ""))


def localize_violations(text: str, language: str) -> list[str]:
    """Từ không hợp khán giả đích (vd đơn vị đo kiểu Mỹ với khán giả Nhật / Hàn)."""
    terms = ((config.load("localize").get("markets") or {}).get(language) or {}).get("avoid_terms") or []
    return [t for t in terms if t and t in (text or "")]


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
    variables = {**_shared_context(u, segs, a.get("events")), "duration": f"{duration:.1f}",
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
    intro_max = HOOK_INTRO_MAX_CHARS.get(u.language, 60)
    variables = {**_shared_context(u, segs, a.get("events")), "video_index": video_index,
                 "language_name": LANGUAGE_NAMES.get(u.language, u.language), "max_chars": max_chars,
                 "intro_max_chars": intro_max,
                 "preferred_hooks": ", ".join(preferred_hooks or []) or "chưa có"}
    lo, hi = u.usable_range.start - 0.5, u.usable_range.end + 0.5

    from app.director.policy import cut_ranges, find_forbidden, overlap_s

    banned = cut_ranges(u)

    def extra(r) -> list[str]:
        errors = check_hooks(r, duration, max_chars, intro_max)
        for i, o in enumerate(r.options, 1):
            ranges = [("footage", o.footage), ("nguồn", o.source)] + \
                ([("intro_footage", o.intro_footage)] if o.intro_footage else [])
            for what, t in ranges:
                if overlap_s(t.start, t.end, banned) > 0.05:
                    errors.append(f"hook {i}: {what} {t.start:.1f}–{t.end:.1f}s chạm đoạn vi phạm chính sách TikTok "
                                  "(sẽ bị cắt) — chọn đoạn khác")
            odd = localize_violations(f"{o.intro} {o.line} {o.onscreen_text}", u.language)
            if odd and u.source_language != u.language:
                errors.append(f"hook {i}: '{', '.join(odd)}' không quen với khán giả này — đổi cách nói")
            bad = find_forbidden(f"{o.intro} {o.line} {o.onscreen_text}", u.language)
            if bad:
                errors.append(f"hook {i}: có từ không được phép trên TikTok ({', '.join(bad)}) — viết lại")
        if r.video_index != video_index:
            errors.append(f"video_index phải là {video_index}")
        if restrict:
            for i, o in enumerate(r.options, 1):
                for what, t in [("footage", o.footage), ("nguồn", o.source)] + \
                        ([("intro_footage", o.intro_footage)] if o.intro_footage else []):
                    if t.start < lo or t.end > hi:
                        errors.append(f"hook {i}: {what} {t.start:.1f}–{t.end:.1f}s nằm ngoài video này "
                                      f"({u.usable_range.start:.1f}–{u.usable_range.end:.1f}s)")
        return errors

    return director.run("hooks", variables, HookSet, extra_check=extra)


def hook_text(hook, vi: bool = False) -> str:
    """Toàn bộ lời hook cần đọc: câu đời thường dẫn vào + câu hook."""
    parts = [hook.intro_vi, hook.line_vi] if vi else [hook.intro, hook.line]
    return " ".join(p.strip() for p in parts if p and p.strip())


def cap_per_mood(items: list, per_mood: int, total: int) -> list:
    """Kho lớn → prompt dài, tốn hạn mức Claude Pro. Mỗi nhóm (mood) chỉ liệt kê vài mục, luân phiên giữa các nhóm
    để danh sách vẫn đa dạng. Mục không có nhóm (nhạc/SFX từ CapCut) coi như mỗi mục một nhóm."""
    groups: dict[str, list] = {}
    for i, it in enumerate(items):
        groups.setdefault(it.mood or f"_{i}", []).append(it)
    picked, rnd = [], 0
    while len(picked) < total and rnd < per_mood:
        for g in groups.values():
            if rnd < len(g) and len(picked) < total:
                picked.append(g[rnd])
        rnd += 1
    return picked


def make_plan(director: Director, analysis_dir: Path, u, style: dict, *, hook=None, hook_s: float = 0.0,
              music_items: list | None = None, sfx_items: list | None = None, decor_items: list | None = None,
              business: bool = False,
              reframe: bool = False, default_ratio: str = "4:3", video_index: int = 1, footage: int = 0):
    from app import config
    from app.analysis.montage import parts_brief
    from app.director.schemas import (EditPlan, check_hype, check_montage, check_plan, check_remix, check_reorder,
                                      check_titles, reorder_hype, repair_montage)

    from app.styles import layout_for

    lay = layout_for(style)
    four = bool(lay and lay.get("titles"))
    bottom_titles = bool(lay and lay.get("bottom_titles", True))
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
        arrow_brief = ARROW_BRIEF.format(examples=style.get("arrow_examples") or ARROW_EXAMPLES) + "\n" + "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames)
    sc = a["scenes"]
    duration = sc["duration"]
    vertical = sc["height"] > sc["width"]
    segs = _segments_in(a["transcript"].get("segments", []), u.usable_range.start, u.usable_range.end)
    lim = config.load("director").get("prompt_limits", {})
    music_lines = [
        f"- {m.name} ({m.category}{', tâm trạng: ' + m.mood if m.mood else ''}"
        f"{', Commercial' if m.commercial else ''}{', Pro' if m.is_vip else ''}, "
        f"{m.material.get('duration', 0) / 1e6:.0f}s)"
        for m in cap_per_mood(music_items or [], lim.get("music_per_mood", 4), lim.get("music_total", 60))
    ]
    sfx_lines = [f"- {m.name}{' (' + m.mood + ')' if m.mood else ''}"
                 for m in cap_per_mood(sfx_items or [], lim.get("sfx_per_mood", 3), lim.get("sfx_total", 90))]
    decor = {k: [i for i in (decor_items or []) if i.kind == k] for k in ("video_effect", "sticker", "transition", "filter")}

    def lines(kind: str) -> str:  # tên trong ngoặc kép, nhóm tách riêng — để đạo diễn không chép nhầm nhóm vào tên
        return "\n".join(f'- "{i.name}"{"  · nhóm: " + i.category if i.category else ""}' for i in decor[kind]) or "(trống)"
    b = u.burned_in_text
    variables = {
        **_shared_context(u, segs, a.get("events")), "video_index": video_index,
        "style_name": style.get("name", ""), "style_description": style.get("description_vi", ""),
        "style_brief": style.get("director_brief", ""), "hook_s": f"{hook_s:.1f}",
        "width": sc["width"], "height": sc["height"],
        "default_ratio": (f"{lay['block_ratio']} (bố cục cố định)" if fixed else
                          ("full (footage dọc)" if vertical else default_ratio)),
        "reframe": "không — bố cục cố định" if fixed else
        ("có — chọn 4:3 hoặc 1:1 cho từng clip" if reframe else "không — mọi clip dùng khung mặc định"),
        "layout_brief": (FOUR_TITLES_BRIEF.format(max_chars=title_max, ratio=lay["block_ratio"],
                                                  bg=_bg_name(lay.get("background_color", "")),
                                                  title_rows_vi=("2 dòng tiêu đề CHỮ RẤT TO phía trên (`titles_top`) và 2 "
                                                                 "dòng phía dưới (`titles_bottom`)" if bottom_titles else
                                                                 "CHỈ 2 dòng tiêu đề CHỮ RẤT TO phía trên (`titles_top`)"),
                                                  bottom_rule=BOTTOM_ON if bottom_titles else BOTTOM_OFF,
                                                  plan_ratio=lay["block_ratio"] if lay["block_ratio"] in
                                                  ("16:9", "4:3", "1:1") else "16:9",
                                                  language=LANGUAGE_NAMES.get(u.language, u.language))
                         if four else ("- Bố cục không có dòng tiêu đề: để `title_top`, `titles_top`, `titles_bottom` rỗng."
                                       if fixed else "- `title_top`: tiêu đề cố định dải trên (có thể rỗng).")),
        "arrow_brief": arrow_brief,
        "order_rule": (REMIX_RULE if style.get("remix") and not style.get("hype") and not style.get("montage_parts")
                       else "") + (
                       (HYPE_RULE.format(**_hype_cfg(style)) if style.get("hype") else "")
                       + (MONTAGE_RULE.format(parts=parts_brief(style["montage_parts"]), **_montage_cfg())
                          if style.get("montage_parts") else "")
                       if style.get("hype") or style.get("montage_parts") else
                       REORDER_RULE.format(max_clip=style.get("pacing", {}).get("max_clip_s", 4))
                       if style.get("reorder") else COLD_OPEN_RULE if style.get("cold_open")
                       else "Các clip theo đúng thứ tự thời gian, không chồng nhau."),
        "burned_in": (f"có, ở {', '.join(b.regions)}. {b.note_vi}" if b.present else "không"),
        "music_list": "\n".join(music_lines) or "(không có bài nào — đặt name = null)",
        "sfx_list": "\n".join(sfx_lines) or "(kho SFX trống — đặt name = null, tool sẽ ghi vào danh sách cần bổ sung)",
        "effect_list": lines("video_effect"), "sticker_list": lines("sticker"),
        "transition_list": lines("transition"), "filter_list": lines("filter"),
        "decor_brief": style.get("decor_brief", ""),
        "business_note": "Khách là doanh nghiệp: CHỈ chọn bài có nhãn Commercial." if business else "",
        "hook": (f"{hook_text(hook)} ({hook_text(hook, vi=True)}) — footage {hook.footage.start:.1f}–{hook.footage.end:.1f}s"
                 if hook else "không có hook"),
        "scenes": "\n".join(f"- {s['start']:.1f}–{s['end']:.1f}" for s in sc["scenes"]),
    }
    names = {m.name for m in (music_items or [])}
    sfx_names = {m.name for m in (sfx_items or [])}
    commercial = {m.name for m in (music_items or []) if m.commercial}

    from app.director.policy import check_policy, cut_ranges, load_cfg, overlap_s, repair_policy

    banned = cut_ranges(u)
    available = u.usable_range.end - u.usable_range.start - overlap_s(u.usable_range.start, u.usable_range.end, banned)
    keep = bool(style.get("keep_footage"))  # chế độ chỉ thay tiếng: clip = toàn bộ video (trừ đoạn vi phạm chính sách)
    vcfg = config.load("dub").get("voice_only") or {}

    def keep_clips():
        from app.director.schemas import PlanClip

        pieces, t = [], 0.0
        for a0, b0 in sorted(banned):
            if a0 - t >= 0.5:
                pieces.append((t, a0))
            t = max(t, b0)
        if duration - t >= 0.5:
            pieces.append((t, duration))
        return [PlanClip(source_start=round(a0, 2), source_end=round(b0, 2), purpose_vi="giữ nguyên video gốc")
                for a0, b0 in pieces or [(0.0, duration)]]

    def extra(plan) -> list[str]:
        if keep:  # không giới hạn 60–150 giây: giữ đúng độ dài video gốc
            errors = check_plan(plan, duration + 0.5, hook_s, min_s=0, max_s=1e9)
        elif style.get("montage_parts"):  # ghép nhiều video: một video khoảng 2 phút (chủ dự án chốt 08/10)
            mc = _montage_cfg()
            errors = check_plan(plan, min(duration, u.usable_range.end + 0.5), hook_s,
                                min_s=mc["target_s"] - mc["tolerance_s"], max_s=mc["target_s"] + mc["tolerance_s"])
            errors += [f"clip {c.source_start}-{c.source_end} dài quá {mc['max_clip_s']:.0f}s — chọn đoạn đắt nhất"
                       for c in plan.clips if not c.replay and (c.source_end - c.source_start) / c.speed
                       > mc["max_clip_s"] + 0.5]
        else:
            errors = check_plan(plan, min(duration, u.usable_range.end + 0.5), hook_s, available=available)
        errors += check_policy(plan, banned, u.language)
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
            errors += check_titles(plan, title_max, bottom_titles)
        if style.get("remix"):
            errors += check_remix(plan, bool(decor["filter"]), keep_order=not style.get("hype"))
        if style.get("hype"):
            hc = _hype_cfg(style)  # nới nhẹ so với lời dặn 3–5s ("hoặc nhiều hơn, tùy" — chủ dự án)
            errors += check_hype(plan, hc["min_clip"] - 0.5, hc["max_clip"] + 1.0)
        if style.get("montage_parts"):
            errors += check_montage(plan, style["montage_parts"],
                                    float(config.load("hype").get("montage_min_share", 0.8)))
        if style.get("reorder"):
            errors += check_reorder(plan, style.get("pacing", {}).get("reorder_share", 0.25),
                                    style.get("pacing", {}).get("max_clip_s"))
        if not style.get("arrows") and plan.arrows:
            errors.append("kiểu dựng này không dùng mũi tên: để `arrows` rỗng")
        if not reframe and not fixed and any(c.ratio and c.ratio != plan.default_ratio for c in plan.clips):
            errors.append("không bật đổi khung theo cảnh: mọi clip phải dùng default_ratio (ratio = null)")
        if plan.video_index != video_index:
            errors.append(f"video_index phải là {video_index}")
        return errors

    from app.director.schemas import repair_plan

    def repair(p):
        if keep:  # hình giữ nguyên: tool tự đặt clip, bỏ mọi thứ làm thay đổi hình
            upd = {"clips": keep_clips(), "zooms": [], "arrows": [], "transitions": []}
            if not vcfg.get("allow_filter", False):
                upd["filter"] = None
            if not vcfg.get("allow_emphasis", False):
                upd["emphasis"] = []
            p = p.model_copy(update=upd)
            p, more = repair_names(p, {k: [i.name for i in v] for k, v in decor.items()}, names, sfx_names)
            return p, more
        p, cut = repair_policy(p, banned, load_cfg().get("min_piece_s", 0.5))
        p, fixes = repair_plan(p, min(duration, u.usable_range.end + 0.5))
        fixes = cut + fixes
        if style.get("montage_parts"):
            p, more = repair_montage(p, style["montage_parts"])
            fixes += more
        if style.get("hype"):  # cảnh gay cấn lên đầu, còn lại về sau — code xếp, không phụ thuộc AI
            p, more = reorder_hype(p)
            fixes += more
        p, more = repair_names(p, {k: [i.name for i in v] for k, v in decor.items()}, names, sfx_names)
        return p, fixes + more

    return director.run("plan", variables, EditPlan, images, extra_check=extra, repair=repair)


def match_name(name: str, valid: list[str] | set[str]) -> str | None:
    """Tên đạo diễn viết → tên thật trong kho: đúng y hệt; bỏ ngoặc kép / phần "(...)" cuối; không phân biệt hoa
    thường; gần giống (≥ 80%). Không khớp → None."""
    import difflib
    import re

    valid = list(valid)
    if name in valid:
        return name
    cleaned = re.sub(r"\s*[（(][^()（）]*[)）]\s*$", "", name.strip().strip('"“”「」')).strip()
    for cand in (cleaned, name.strip().strip('"“”')):
        if cand in valid:
            return cand
    low = {v.casefold(): v for v in valid}
    for cand in (cleaned, name):
        if cand.casefold() in low:
            return low[cand.casefold()]
    close = difflib.get_close_matches(cleaned, valid, n=1, cutoff=0.8) or \
        difflib.get_close_matches(name, valid, n=1, cutoff=0.8)
    return close[0] if close else None


def repair_names(plan, decor_names: dict[str, list[str]], music_names: set[str], sfx_names: set[str]):
    """Sửa tên tài nguyên viết sai chút ít; trang trí không khớp thì bỏ (không bắt đạo diễn làm lại),
    nhạc/SFX không khớp thì để trống (bộ dựng tự tìm bài / tiếng cùng loại hoặc ghi vào danh sách cần bổ sung)."""
    fixes: list[str] = []
    upd: dict = {}

    def fix_list(field: str, kind: str, label: str):
        kept = []
        for it in getattr(plan, field):
            m = match_name(it.name, decor_names.get(kind, []))
            if m is None:
                fixes.append(f"bỏ {label} '{it.name}' (không có trong kho)")
                continue
            if m != it.name:
                fixes.append(f"{label} '{it.name}' → '{m}'")
            kept.append(it.model_copy(update={"name": m}))
        upd[field] = kept

    fix_list("effects", "video_effect", "hiệu ứng")
    fix_list("stickers", "sticker", "sticker")
    fix_list("transitions", "transition", "chuyển cảnh")
    if plan.filter:
        m = match_name(plan.filter, decor_names.get("filter", []))
        if m != plan.filter:
            fixes.append(f"filter '{plan.filter}' → {repr(m) if m else 'bỏ (không có trong kho)'}")
        upd["filter"] = m
    if plan.music.name:
        m = match_name(plan.music.name, music_names)
        if m != plan.music.name:
            fixes.append(f"nhạc '{plan.music.name}' → {repr(m) if m else 'để trống (tool tự chọn nhạc cùng mức năng lượng)'}")
            upd["music"] = plan.music.model_copy(update={"name": m})
    sfx = []
    for x in plan.sfx:
        if x.name:
            m = match_name(x.name, sfx_names)
            if m != x.name:
                fixes.append(f"SFX '{x.name}' → {repr(m) if m else 'để trống (tool tự tìm tiếng cùng loại)'}")
                x = x.model_copy(update={"name": m})
        sfx.append(x)
    upd["sfx"] = sfx
    return plan.model_copy(update=upd), fixes


FOUR_TITLES_BRIEF = """- Bố cục CỐ ĐỊNH của mọi video (theo video mẫu chủ dự án chọn): nền {bg}, khối video {ratio} ở giữa,
  {title_rows_vi}, hiện suốt video.
  Phụ đề thoại nằm trong khối video (code tự làm). `default_ratio` = "{plan_ratio}", mọi clip `ratio` = null.
- `titles_top` (2 dòng): tình huống / câu gợi tò mò, dòng 1 mở (có thể kết bằng "…"), dòng 2 là chi tiết bất ngờ.
  Ví dụ tiếng Nhật: ["大事な試合の前に…", "隣室から突然流れる演歌"].
{bottom_rule}
- Mỗi dòng tối đa {max_chars} ký tự, viết bằng {language} tự nhiên kiểu tiêu đề TikTok bản xứ, không xuống dòng.
  Phải ĐÚNG nội dung có thật trong footage; không hứa điều video không có; không lộ hết "lời giải".
- `topic_label`: nhãn ngắn chủ đề đoạn nói chuyện (ví dụ "同期のパンチ佐藤さんについて"), hoặc rỗng nếu footage đã có sẵn.
  `title_top` để rỗng."""

BOTTOM_ON = ('- `titles_bottom` (2 dòng): nhân vật / kết luận về người trong video. '
             'Ví dụ: ["全くぶれない男だった", "亜細亜大のキャプテン"].')
BOTTOM_OFF = "- `titles_bottom`: để RỖNG [] (bố cục chỉ có 2 dòng tiêu đề phía trên)."


def _montage_cfg() -> dict:
    h = config.load("hype") or {}
    target, tol = float(h.get("montage_target_s", 120)), float(h.get("montage_tolerance_s", 20))
    return {"target_s": target, "tolerance_s": tol, "min_s": target - tol, "max_s": target + tol,
            "max_clip_s": float(h.get("montage_max_clip_s", 10))}


def _hype_cfg(style: dict) -> dict:
    h = style.get("hype") if isinstance(style.get("hype"), dict) else {}
    return {"min_clip": float(h.get("min_clip_s", 3.0)), "max_clip": float(h.get("max_clip_s", 5.0))}


def _bg_name(color: str) -> str:
    c = (color or "").upper()
    return "trắng" if c.startswith("#FFFFFF") else "đen" if c.startswith("#000000") else f"màu {color}"


REMIX_RULE = """BẢN DỰNG LẠI (khác bản gốc ~80%): giữ đúng THỨ TỰ thời gian của câu chuyện (không đảo cảnh), nhưng
KHÔNG cảnh nào được giống bản gốc: code tự đổi khung/cắt cận bám người và thêm chuyển động cho mọi clip; bạn phải
cắt gọn nhịp mạnh (bỏ khoảng lặng, câu thừa), đặt zoom ở các điểm nhấn, chọn filter màu cho cả video (bắt buộc nếu kho
có filter), nhạc nền mới, tiêu đề / chữ nhấn mới viết bằng ngôn ngữ đích. """

COLD_OPEN_RULE = """Các clip theo thứ tự thời gian, không chồng nhau. Được phép (khuyến khích) MỞ ĐẦU bằng 1 clip
  ngắn 1–3 giây lấy khoảnh khắc buồn cười / sốc nhất ở phía sau (cold open) — đặt "repeat": true cho clip đó
  (được trùng footage với clip dựng sau) — rồi dựng từ đầu theo thứ tự."""


HYPE_RULE = """CHUYỂN CẢNH LIÊN TỤC (chủ dự án yêu cầu): cắt thành THẬT NHIỀU cảnh ngắn, mỗi cảnh {min_clip:.0f}–{max_clip:.0f}
  giây (không clip nào dài hơn {max_clip:.0f}s), lấy hết các khoảnh khắc đáng xem. Đánh dấu "highlight": true cho các
  cảnh GAY CẤN / đắt giá nhất (cao trào, hành động mạnh, phản ứng lớn, khoảnh khắc bất ngờ) — CODE SẼ TỰ XẾP chúng lên ĐẦU
  video theo đúng thứ tự bạn liệt kê; các cảnh còn lại (bối cảnh, giải thích, đoạn nhẹ) code xếp về SAU theo thời gian,
  vẫn cắt ngắn {min_clip:.0f}–{max_clip:.0f}s để chuyển cảnh liên tục tới cuối. Clip không chồng nhau. Đừng cắt giữa câu
  quan trọng; câu dài thì chọn đoạn hình đẹp nhất của nó. """

MONTAGE_RULE = """GHÉP NHIỀU VIDEO THÀNH MỘT CÂU CHUYỆN (chủ dự án chốt 08/10): footage là nhiều video (vd nhiều tập phim / hoạt
  hình) nối lại — mốc giây từng video ở dưới. Hãy chọn lọc các đoạn HAY NHẤT, ghép thành MỘT video dài khoảng
  {target_s:.0f} giây ({min_s:.0f}–{max_s:.0f}s) có Ý NGHĨA RIÊNG: một chặng đường, một quá trình trưởng thành, một khoảng thời
  gian đáng nhớ, một câu chuyện tình bạn / tình cảm đẹp... (chọn mạch hợp nhất với nội dung, ghi ra trong editor_notes).
  - Lấy cảnh từ GẦN NHƯ MỌI video (mỗi video một chút); xếp theo mạch câu chuyện có mở – diễn biến – cao trào – kết lắng
    đọng (thường theo thứ tự thời gian của các tập để thấy được "chặng đường").
  - Mỗi cảnh khoảng 3–5 giây; khoảnh khắc đắt (câu thoại / cảm xúc trọn vẹn) được dài hơn, tối đa {max_clip_s:.0f}s.
    Không cắt giữa câu thoại quan trọng — tiếng gốc được GIỮ.
  - Nhạc nền cảm xúc hợp mạch truyện (ấm áp / hoài niệm / truyền cảm hứng), chuyển cảnh mềm giữa các video, hiệu ứng tiết
    chế; tiêu đề + chữ nói về ý nghĩa chung của câu chuyện, không nói về một tập riêng.
  - Một clip chỉ nằm trong MỘT video (không vắt qua ranh giới).
{parts}
"""


REORDER_RULE = """ĐẢO THỨ TỰ CLIP (kiểu giải trí — khách muốn người xem không nhận ra video gốc): KHÔNG dựng theo
  thứ tự thời gian. Mở bằng khoảnh khắc đắt / buồn cười nhất (cold open), rồi nhảy về bối cảnh, xen kẽ trước–sau,
  cắt qua lại giữa câu nói và phản ứng, lặp lại câu chốt bằng clip replay. Mỗi clip ngắn (≤ {max_clip}s), không
  chồng nhau (trừ replay). Vẫn phải xem hiểu được và KHÔNG tạo nghĩa sai: giữ trọn câu nói, không ghép phản ứng
  vào một câu hỏi/tình huống khác để bịa ra điều không xảy ra."""


ARROW_EXAMPLES = "găng tay tung đòn, chân bước, bóng, cầu thủ"
ARROW_BRIEF = """- `arrows`: mũi tên chỉ ĐÚNG chi tiết mà lời nói / lời bình đang nói tới ({examples}),
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
    variables = {**_shared_context(u, kept, a.get("events")), "video_index": video_index,
                 "language_name": LANGUAGE_NAMES.get(u.language, u.language),
                 "market": MARKETS.get(u.language, "TikTok"),
                 "hook": f"{hook_text(hook)} ({hook_text(hook, vi=True)})" if hook else "không có hook"}
    from app.director.policy import find_forbidden

    def extra(r) -> list[str]:
        errors = check_captions(r) + ([] if r.video_index == video_index else [f"video_index phải là {video_index}"])
        odd = localize_violations(r.caption, u.language) if u.source_language != u.language else []
        if odd:
            errors.append(f"caption có '{', '.join(odd)}' không quen với khán giả này — đổi cách nói")
        bad = find_forbidden(" ".join([r.caption, *r.hashtags]), u.language)
        if bad:
            errors.append(f"caption/hashtag có từ không được phép trên TikTok ({', '.join(bad)}) — viết lại")
        return errors

    return director.run("captions", variables, Captions, extra_check=extra)


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


# ---------------- Thuyết minh (chế độ Đổi ngôn ngữ) ----------------

def speech_chars(text: str) -> int:
    """Số ký tự được đọc (bỏ dấu cách, dấu câu) — để ước lượng tốc độ nói."""
    import unicodedata

    return sum(1 for ch in text if not ch.isspace() and not unicodedata.category(ch).startswith("P"))


def silent_gaps(plan, segments: list[dict], events: list[dict] | None = None, cfg: dict | None = None) -> list[dict]:
    """Chỗ KHÔNG có giọng nói trên video đã dựng (đủ dài) → cần lời dẫn.
    Trả [{out_start, out_end (µs), pieces: [(giây gốc đầu, cuối)]}]. Clip replay / lặp lại không tính (nhạc dẫn)."""
    from app.planner.timeline import SEC, TimeMap

    full = config.load("dub") if cfg is None else cfg
    cfg = full.get("narration") or {}
    # tiếng gốc bị tắt hẳn → chỗ tiếng cười / hò reo cũng thành im lặng, không giữ lại nữa
    keep_reactions = cfg.get("keep_reactions", True) and not full.get("mute_original", True)
    min_gap = round(float(cfg.get("min_gap_s", 3.0)) * SEC)
    tmap = TimeMap(plan.clips)
    busy: list[tuple[int, int]] = []  # khoảng có thoại hoặc không cần lời dẫn (µs trên video)
    words = [(w["start"], w["end"]) for s in segments for w in (s.get("words") or [])] or \
        [(s["start"], s["end"]) for s in segments]
    for c, p in zip(plan.clips, tmap.placed):
        if c.replay or c.repeat:
            busy.append((p.out_start, p.out_end))
            continue
        for a, b in words:
            a, b = max(a, c.source_start), min(b, c.source_end)
            if b > a:
                busy.append((p.out_start + round((a - c.source_start) / c.speed * SEC),
                             p.out_start + round((b - c.source_start) / c.speed * SEC)))
    busy.sort()
    gaps, t = [], 0
    for a, b in busy + [(tmap.end, tmap.end)]:
        if a - t >= min_gap:
            gaps.append((t, a))
        t = max(t, b)

    def pieces(g0: int, g1: int) -> list[tuple[float, float]]:
        out = []
        for c, p in zip(plan.clips, tmap.placed):
            a, b = max(g0, p.out_start), min(g1, p.out_end)
            if b > a and not c.replay and not c.repeat:
                out.append((round(c.source_start + (a - p.out_start) / SEC * c.speed, 2),
                            round(c.source_start + (b - p.out_start) / SEC * c.speed, 2)))
        return out

    out = []
    for g0, g1 in gaps:
        src = pieces(g0, g1)
        if keep_reactions and events and src:
            react = sum(max(0.0, min(e["end"], b) - max(e["start"], a)) for a, b in src for e in events
                        if e.get("kind") in ("laugh", "cheer"))
            if react >= 0.6 * sum(b - a for a, b in src):
                continue  # tiếng cười / hò reo: giữ nguyên khoảnh khắc
        out.append({"out_start": g0, "out_end": g1, "pieces": src})
    return out


def opening_gap(gaps: list[dict], cfg: dict | None = None) -> dict | None:
    """Video mở đầu bằng cảnh im lặng (vd show món ăn / sản phẩm) → khoảng lặng đó, để bắt buộc lời dẫn mở đầu."""
    from app.planner.timeline import SEC

    ocfg = ((config.load("dub") if cfg is None else cfg).get("narration") or {}).get("opening") or {}
    if not ocfg.get("enabled", True) or not gaps:
        return None
    g = gaps[0]
    if g["out_start"] <= float(ocfg.get("within_s", 1.0)) * SEC and \
            g["out_end"] - g["out_start"] >= float(ocfg.get("min_len_s", 2.0)) * SEC:
        return g
    return None


def check_narration(script, plan, gaps: list[dict], cfg: dict | None = None) -> list[str]:
    """Lời dẫn chỉ nói ở cảnh hay / hành động đáng chú ý trong chỗ không có giọng nói — không nói liên tục:
    phải ghi rõ hành động (action_vi), nằm trong khoảng lặng (không đè lời thoại), tổng thời lượng không quá dày."""
    from app.planner.timeline import TimeMap

    ncfg = (config.load("dub") if cfg is None else cfg).get("narration") or {}
    max_ratio = float(ncfg.get("max_cover_ratio", 0.6))
    tmap = TimeMap(plan.clips)
    errors, used = [], 0
    silent = sum(g["out_end"] - g["out_start"] for g in gaps)
    for i, ln in enumerate(script.lines, 1):
        if ln.kind != "narration":
            continue
        if not ln.action_vi.strip():
            errors.append(f"câu {i} (lời dẫn): ghi `action_vi` — cảnh / hành động đáng nói lúc đó (vd thêm gia vị)")
        a, b = tmap.to_out(ln.source_start), tmap.to_out(ln.source_end)
        if a is None or b is None or b <= a:
            continue
        inside = sum(max(0, min(b, g["out_end"]) - max(a, g["out_start"])) for g in gaps)
        if inside < 0.8 * (b - a):
            errors.append(f"câu {i} (lời dẫn) {ln.source_start}-{ln.source_end}s đè lên lời thoại — chỉ đặt lời dẫn ở "
                          "chỗ không có giọng nói")
        used += inside
    og = opening_gap(gaps, cfg)
    if og is not None:
        from app.planner.timeline import SEC

        by = og["out_start"] + round(float((ncfg.get("opening") or {}).get("start_by_s", 1.0)) * SEC)
        starts = [tmap.to_out(ln.source_start) for ln in script.lines if ln.kind == "narration"]
        if not any(t is not None and og["out_start"] - SEC // 2 <= t <= by for t in starts):
            x, y = og["pieces"][0]
            errors.append(f"video mở đầu im lặng (giây gốc {x:.1f}–{y:.1f}, đang show món / sản phẩm): BẮT BUỘC có câu "
                          f"lời dẫn mở đầu bắt đầu ngay từ ~{x:.1f}s — gần gũi, gợi thèm, gợi tò mò cách làm")
    if silent and used > max_ratio * silent:
        errors.append(f"lời dẫn quá dày ({used / silent:.0%} thời gian lặng, tối đa {max_ratio:.0%}) — chỉ nói ở cảnh hay / "
                      "hành động đáng chú ý, chỗ khác để nhạc và âm thanh hiện trường")
    return errors


def effective_cps(cfg: dict, language: str) -> float:
    """Tốc độ nói tối đa dùng để viết / kiểm tra câu thuyết minh: theo config, nhưng nếu đã đo được giọng thu thật
    của bạn đọc chậm hơn (config/local.yaml → voice_cps) thì dùng tốc độ đó — câu sẽ vừa với giọng, khỏi đè."""
    base = float((cfg.get("max_cps") or {}).get(language, 10.0))
    if cfg.get("use_measured_rate", True):
        from app import settings

        measured = (settings.load().get("voice_cps") or {}).get(language)
        if measured:
            return min(base, float(measured))
    return base


def repair_dub(script, plan, cfg: dict | None = None, language: str = ""):
    """Tự sửa lỗi vặt của kịch bản thuyết minh (đỡ phải hỏi lại AI — mỗi lần mất vài phút):
    - câu vắt qua 2 clip → thu về clip chứa phần lớn câu (còn < 0.5 giây thì bỏ câu);
    - câu quá ngắn so với số chữ (nói không kịp) mà sát câu sau trong cùng clip → gộp 2 câu."""
    from app.planner.timeline import TimeMap

    cfg = config.load("dub") if cfg is None else cfg
    cps = effective_cps(cfg, language) * float(cfg.get("max_speed", 1.25))
    tmap = TimeMap(plan.clips)
    kept = [c for c in plan.clips if not c.replay and not c.repeat]
    fixes, lines = [], []
    for ln in script.lines:
        a, b = ln.source_start, ln.source_end
        best = max(kept, key=lambda c: min(b, c.source_end) - max(a, c.source_start), default=None)
        if best is None or min(b, best.source_end) - max(a, best.source_start) < 0.5:
            fixes.append(f"bỏ câu thuyết minh {a}-{b}s (nằm ngoài các clip được giữ)")
            continue
        na, nb = max(a, best.source_start), min(b, best.source_end)
        if (na, nb) != (a, b):
            fixes.append(f"câu thuyết minh {a}-{b}s vắt qua 2 clip → thu về {na:.2f}-{nb:.2f}s")
            ln = ln.model_copy(update={"source_start": round(na, 2), "source_end": round(nb, 2)})
        lines.append(ln)
    merged = []
    for ln in lines:
        prev = merged[-1] if merged else None
        if prev is not None:
            pa, pb = tmap.to_out(prev.source_start), tmap.to_out(ln.source_start)
            same_clip = tmap.clip_at(prev.source_start) is tmap.clip_at(ln.source_end)
            dur = ((pb - pa) / 1e6 - 0.12) if pa is not None and pb is not None else 0  # giống check_dub
            too_fast = dur > 0 and speech_chars(prev.text) / dur > cps * 1.1
            close = ln.source_start - prev.source_end <= 0.6
            if too_fast and close and same_clip:
                sep = "" if language == "ja" else " "
                merged[-1] = prev.model_copy(update={
                    "source_end": ln.source_end, "text": prev.text.rstrip() + sep + ln.text.lstrip(),
                    "text_vi": f"{prev.text_vi.rstrip()} {ln.text_vi.lstrip()}",
                    "kind": "dub" if "dub" in (prev.kind, ln.kind) else "narration",
                    "action_vi": prev.action_vi or ln.action_vi, "adapt_vi": "; ".join(x for x in (prev.adapt_vi, ln.adapt_vi) if x)})
                fixes.append(f"gộp câu thuyết minh {prev.source_start}-{prev.source_end}s (quá ngắn để đọc kịp) với câu sau")
                continue
        merged.append(ln)
    if not merged:
        return script, fixes
    return script.model_copy(update={"lines": merged}), fixes


def check_dub(script, plan, language: str, cfg: dict | None = None) -> list[str]:
    from app.director.policy import find_forbidden
    from app.planner.timeline import SEC, TimeMap

    cfg = config.load("dub") if cfg is None else cfg
    lo, hi = cfg.get("line_s", [1.5, 9.0])
    cps = effective_cps(cfg, language)
    max_speed = float(cfg.get("max_speed", 1.25))
    tmap = TimeMap(plan.clips)
    outs = [(tmap.to_out(ln.source_start), tmap.to_out(ln.source_end)) for ln in script.lines]
    errors, last_end = [], -1
    for i, ln in enumerate(script.lines, 1):
        clip = tmap.clip_containing((ln.source_start + ln.source_end) / 2)
        a, b = outs[i - 1]
        if clip is None or a is None or b is None or b <= a or not (
                clip.source_start - 0.05 <= ln.source_start and ln.source_end <= clip.source_end + 0.05):
            errors.append(f"câu {i} ({ln.source_start}-{ln.source_end}s) phải nằm gọn trong MỘT clip được giữ")
            continue
        dur = (b - a) / SEC
        if dur < lo * 0.6 or dur > hi + 1.0:
            errors.append(f"câu {i} dài {dur:.1f}s, nên {lo}–{hi}s (gộp hoặc tách câu)")
        # voice được dùng chỗ trống tới lúc câu sau bắt đầu và tăng tốc tối đa max_speed (giống lúc dựng)
        nxt = outs[i][0] if i < len(outs) and outs[i][0] is not None else tmap.end
        room = max(dur, (nxt - a) / SEC - 0.12)
        n = speech_chars(ln.text)
        if room > 0 and n / room > cps * max_speed * 1.1:
            errors.append(f"câu {i} có {n} ký tự cho {room:.1f}s (>{cps:.0f} ký tự/giây) — nói gọn lại hoặc gộp với câu bên cạnh")
        if a < last_end - 50_000:
            errors.append(f"câu {i} chồng lên câu trước hoặc sai thứ tự")
        last_end = max(last_end, b)
        odd = localize_violations(ln.text, language)
        if odd:
            errors.append(f"câu {i}: '{', '.join(odd)}' không quen với khán giả này — đổi sang đơn vị / cách nói của họ")
        bad = find_forbidden(ln.text, language)
        if bad:
            errors.append(f"câu {i} có từ không được phép trên TikTok ({', '.join(bad)})")
    return errors


def dense_note(plan, segs: list[dict], cfg: dict) -> str:
    """Video gốc nói DÀY ĐẶC (lời chiếm phần lớn thời gian) → dặn AI nén ý, không dịch hết từng câu."""
    kept = [c for c in plan.clips if not c.replay and not c.repeat]
    total = sum(c.source_end - c.source_start for c in kept)
    talk = sum(max(0.0, min(s["end"], c.source_end) - max(s["start"], c.source_start)) for c in kept for s in segs)
    ratio = talk / total if total else 0.0
    if ratio < float(cfg.get("dense_ratio", 0.7)):
        return ""
    keep = int(float(cfg.get("dense_keep", 0.75)) * 100)
    return (f"- **VIDEO NÓI DÀY ĐẶC** (lời chiếm {ratio:.0%} thời gian): KHÔNG dịch hết từng câu — voice thuyết minh sẽ "
            f"đè lên nhau. NÉN Ý còn khoảng {keep}% độ dài lời gốc: bỏ câu đệm, câu lặp, ý phụ, từ cảm thán; gộp 2 câu "
            "ngắn thành 1; mỗi câu chừa ~0.3 giây cuối để lấy hơi. Giữ đủ ý chính và các câu khớp động tác trên hình.")


def shorten_dub_lines(director: Director, script, items: list[tuple[int, int]], u):
    """AI viết lại ngắn hơn đúng các câu bị tràn. items: [(số câu, số ký tự tối đa)]. Trả kịch bản đã thay câu."""
    from app.director.policy import find_forbidden
    from app.director.schemas import DubShorten

    limits = dict(items)
    rows = []
    for no, mx in items:
        ln = script.lines[no - 1]
        prev = script.lines[no - 2].text if no >= 2 else "(đầu video)"
        nxt = script.lines[no].text if no < len(script.lines) else "(hết)"
        rows.append(f"- câu {no} (tối đa {mx} ký tự, hiện có {speech_chars(ln.text)}): {ln.text}\n"
                    f"  nghĩa: {ln.text_vi}\n  câu trước: {prev}\n  câu sau: {nxt}")
    variables = {"language_name": LANGUAGE_NAMES.get(u.language, u.language), "market": MARKETS.get(u.language, "TikTok"),
                 "lines": "\n".join(rows), "localize_brief": localize_brief(u)}

    def extra(r) -> list[str]:
        errors = []
        got = {x.no for x in r.lines}
        if got != set(limits):
            errors.append(f"phải trả đúng các câu {sorted(limits)} (đang có {sorted(got)})")
        for x in r.lines:
            if x.no in limits and speech_chars(x.text) > limits[x.no]:
                errors.append(f"câu {x.no} có {speech_chars(x.text)} ký tự, tối đa {limits[x.no]}")
            bad = find_forbidden(x.text, u.language)
            if bad:
                errors.append(f"câu {x.no} có từ không được phép trên TikTok ({', '.join(bad)})")
        return errors

    r = director.run("dub_shorten", variables, DubShorten, extra_check=extra)
    lines = list(script.lines)
    for x in r.lines:
        if x.no in limits:
            lines[x.no - 1] = lines[x.no - 1].model_copy(update={"text": x.text, "text_vi": x.text_vi})
    return script.model_copy(update={"lines": lines})


def check_rewrite(script, plan, cfg: dict) -> list[str]:
    """Kịch bản viết mới: mở lời ngay đầu video, không nói kín mít."""
    from app.planner.timeline import TimeMap

    rcfg = cfg.get("rewrite") or {}
    tmap = TimeMap(plan.clips)
    outs = [(tmap.to_out(ln.source_start), tmap.to_out(ln.source_end)) for ln in script.lines]
    outs = [(a, b) for a, b in outs if a is not None and b is not None and b > a]
    errors = []
    if outs and min(a for a, _ in outs) > float(rcfg.get("open_within_s", 1.5)) * 1e6:
        errors.append(f"câu đầu tiên phải bắt đầu trong {rcfg.get('open_within_s', 1.5)} giây đầu video (mở lời cuốn hút ngay)")
    total = tmap.end or 1
    cover = sum(b - a for a, b in outs) / total
    if cover > float(rcfg.get("max_cover", 0.9)):
        errors.append(f"lời chiếm {cover:.0%} thời lượng — quá kín, chừa chỗ thở (≤ {float(rcfg.get('max_cover', 0.9)):.0%})")
    return errors


def _rewrite_dub(director: Director, analysis_dir: Path, u, plan, *, hook=None, video_index: int = 1, footage: int = 0):
    from app.director.schemas import DubScript

    cfg = config.load("dub")
    rcfg = cfg.get("rewrite") or {}
    a = load_analysis(analysis_dir, footage)
    segs = a["transcript"].get("segments", [])
    kept_clips = [c for c in plan.clips if not c.replay and not c.repeat]
    kept = [s for s in segs if any(s["end"] > c.source_start and s["start"] < c.source_end for c in kept_clips)]
    pool = [f for f in a["frames"] if any(c.source_start - 0.3 <= f["t"] <= c.source_end + 0.3 for c in kept_clips)]
    frames = pick_evenly(sorted(pool, key=lambda f: f["t"]), int(rcfg.get("frames", 16)))
    lo, hi = cfg.get("line_s", [1.5, 9.0])
    variables = {**_shared_context(u, kept, a.get("events")), "video_index": video_index,
                 "language_name": LANGUAGE_NAMES.get(u.language, u.language),
                 "source_name": LANGUAGE_NAMES.get(u.source_language, u.source_language),
                 "market": MARKETS.get(u.language, "TikTok"), "line_min": lo, "line_max": hi,
                 "max_cps": round(effective_cps(cfg, u.language) * float(cfg.get("write_cps_factor", 0.85)), 1),
                 "localize_brief": localize_brief(u),
                 "hook": f"{hook_text(hook)} ({hook_text(hook, vi=True)})" if hook else "không có hook",
                 "clips": "\n".join(f"- clip {i}: {c.source_start:.1f}–{c.source_end:.1f}s"
                                    f"{' (replay / lặp lại — không thuyết minh)' if c.replay or c.repeat else ''}"
                                    for i, c in enumerate(plan.clips)),
                 "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) or "(không có)"}

    def extra(r) -> list[str]:
        errors = check_dub(r, plan, u.language, cfg) + check_rewrite(r, plan, cfg)
        if r.video_index != video_index:
            errors.append(f"video_index phải là {video_index}")
        return errors

    return director.run("dub_rewrite", variables, DubScript, [analysis_dir / f["file"] for f in frames],
                        extra_check=extra, repair=lambda r: repair_dub(r, plan, cfg, u.language))


def make_dub(director: Director, analysis_dir: Path, u, plan, *, hook=None, video_index: int = 1, footage: int = 0,
             mode: str = "translate"):
    """Kịch bản thuyết minh theo các clip của kế hoạch dựng (giây gốc), bằng ngôn ngữ đích u.language.
    mode="translate": dịch sát lời gốc (+ lời dẫn chỗ im lặng); mode="rewrite": AI xem hình rồi VIẾT MỚI nội dung
    hợp khán giả nước đích (chủ dự án yêu cầu 07/10)."""
    from app.director.schemas import DubScript

    cfg = config.load("dub")
    if mode == "rewrite":
        return _rewrite_dub(director, analysis_dir, u, plan, hook=hook, video_index=video_index, footage=footage)
    a = load_analysis(analysis_dir, footage)
    segs = a["transcript"].get("segments", [])
    kept = []
    for c in plan.clips:
        if c.replay or c.repeat:
            continue
        kept += [s for s in segs if s["end"] > c.source_start and s["start"] < c.source_end and s not in kept]
    lo, hi = cfg.get("line_s", [1.5, 9.0])
    clips = "\n".join(f"- clip {i}: {c.source_start:.1f}–{c.source_end:.1f}s"
                      f"{' (replay quay chậm — không thuyết minh)' if c.replay else ''}"
                      f"{' (lặp lại — không thuyết minh)' if c.repeat else ''}"
                      for i, c in enumerate(plan.clips))
    variables = {**_shared_context(u, kept, a.get("events")), "video_index": video_index,
                 "language_name": LANGUAGE_NAMES.get(u.language, u.language),
                 "source_name": LANGUAGE_NAMES.get(u.source_language, u.source_language),
                 "market": MARKETS.get(u.language, "TikTok"), "line_min": lo, "line_max": hi,
                 "max_cps": round(effective_cps(cfg, u.language) * float(cfg.get("write_cps_factor", 0.85)), 1),
                 "dense_note": dense_note(plan, segs, cfg), "localize_brief": localize_brief(u),
                 "original_audio_note": (
                     "- TIẾNG GỐC BỊ TẮT HẲN: người xem chỉ nghe voice thuyết minh + nhạc. Câu thoại quan trọng nào cũng phải "
                     "có câu thuyết minh; khoảnh khắc cười / hò reo nếu đáng giữ thì nói ngắn (vd \"cả nhà cười lăn\")."
                     if cfg.get("mute_original", True) else
                     "- Tiếng cười, hò reo ngắn thì để nguyên tiếng gốc (giữ khoảnh khắc)."),
                 "hook": f"{hook_text(hook)} ({hook_text(hook, vi=True)})" if hook else "không có hook", "clips": clips}
    gaps = silent_gaps(plan, segs, a.get("events"), cfg)
    images = []
    if gaps:
        ncfg = cfg.get("narration") or {}
        pool = [f for f in a["frames"] if any(x - 0.5 <= f["t"] <= y + 0.5 for g in gaps for x, y in g["pieces"])]
        frames = pick_evenly(pool, int(ncfg.get("frames", 8)))
        images = [analysis_dir / f["file"] for f in frames]
        cuts = [x["start"] for x in a["scenes"].get("scenes", [])]

        def gap_line(g) -> str:
            inner = [t for t in cuts if any(x < t < y for x, y in g["pieces"])]
            return (f"- giây gốc {', '.join(f'{x:.1f}–{y:.1f}' for x, y in g['pieces'])} "
                    f"({(g['out_end'] - g['out_start']) / 1e6:.1f}s trên video)"
                    + (f" · đổi cảnh ở {', '.join(f'{t:.1f}' for t in inner)}s" if inner else ""))

        variables["silent_gaps"] = "\n".join(gap_line(g) for g in gaps) + \
            ("\nKhung hình ở các chỗ này (mở bằng Read để xem có hành động gì):\n" +
             "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) if frames else "")
    else:
        variables["silent_gaps"] = "(không có — video có thoại gần như liên tục)"

    og = opening_gap(gaps, cfg)
    variables["opening_note"] = (
        f"\n**MỞ ĐẦU IM LẶNG** (giây gốc {og['pieces'][0][0]:.1f}–{og['pieces'][0][1]:.1f}): video mở bằng cảnh chưa ai nói "
        "(thường là show thành phẩm — món ăn, sản phẩm). BẮT BUỘC đệm lời dẫn mở đầu, cất lên ngay từ đầu cảnh, giọng "
        "như các video nấu ăn TikTok: gần gũi như nói với bạn bè, gợi thèm (tả màu, độ giòn, nước sốt... đúng cái đang "
        "thấy), rồi gợi tò mò cách làm (vd \"Món này làm dễ hơn bạn nghĩ nhiều, xem nhé\"). 1–2 câu, ngắn, tự nhiên; "
        "không hứa điều video không có (không nói \"chỉ 5 phút\" nếu không thấy).\n" if og else "")

    def extra(r) -> list[str]:
        errors = check_dub(r, plan, u.language, cfg) + check_narration(r, plan, gaps, cfg)
        if r.video_index != video_index:
            errors.append(f"video_index phải là {video_index}")
        return errors

    return director.run("dub", variables, DubScript, images, extra_check=extra,
                        repair=lambda r: repair_dub(r, plan, cfg, u.language))
