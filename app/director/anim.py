"""HOẠT HÌNH — GIỮ ÂM THANH GỐC (chủ dự án yêu cầu 20/10).

Video hoạt hình ~1 phút → MỘT lượt hỏi AI (`make_anim_script`, prompt `anim.md`): AI xem từng cảnh, viết cốt truyện MỚI
(khác bản gốc ≥ `min_story_diff`%), xếp lại cảnh theo cốt truyện đó (`beats`, mỗi đoạn gốc dùng một lần), cảnh nào nhân
vật nói thì viết lời thoại MỚI (`line`: nhân vật, câu ngôn ngữ đích). Máy tự đo mức đảo cảnh (`order_diff`).
Kế hoạch dựng + kịch bản lồng tiếng tạo bằng code (`anim_plan`, `anim_to_dub`) → dùng chung trang voice / OmniVoice theo
nhân vật / phụ đề / tách nhạc nền của chế độ Lồng tiếng nhân vật. Không đạt 70% (`feasible: false`) → runner dừng báo.
"""

from __future__ import annotations

from pathlib import Path

from app import config
from app.director.base import Director


def anim_cfg() -> dict:
    return config.load("anim") or {}


def order_diff(beats, gap_s: float = 1.0) -> float:
    """Tỉ lệ cặp cảnh liền nhau trong video mới mà ở bản gốc KHÔNG nối tiếp nhau (cảnh sau bắt đầu ngay sau cảnh trước,
    cách ≤ gap_s). 1.0 = đảo hết, 0 = giữ nguyên thứ tự."""
    pairs = list(zip(beats, beats[1:]))
    if not pairs:
        return 0.0
    same = sum(1 for a, b in pairs if 0 <= b.start - a.end <= gap_s)
    return round(1 - same / len(pairs), 3)


def _overlap(a: float, b: float, segs: list[dict]) -> float:
    return sum(max(0.0, min(b, s["end"]) - max(a, s["start"])) for s in segs)


def check_anim(r, language: str, *, duration: float, segments: list[dict], cps: float, cfg: dict,
               banned: list[tuple[float, float]] | None = None) -> list[str]:
    from app.director.policy import find_forbidden, overlap_s
    from app.director.tasks import speech_chars, wrong_language

    errors = []
    min_beat = float(cfg.get("min_beat_s", 0.8))
    speech_beat = float(cfg.get("speech_beat_s", 0.6))
    fill = float(cfg.get("line_fill", 1.15))
    for k, b in enumerate(r.beats, 1):
        d = b.end - b.start
        if b.end <= b.start or b.start < 0 or b.end > duration + 0.3:
            errors.append(f"cảnh {k} ({b.start}-{b.end}) nằm ngoài video gốc (0–{duration:.1f}s)")
            continue
        if d < min_beat - 0.05:
            errors.append(f"cảnh {k} ({b.start}-{b.end}) ngắn hơn {min_beat:.1f} giây")
        if banned and overlap_s(b.start, b.end, banned) > 0.05:
            errors.append(f"cảnh {k} chứa đoạn vi phạm chính sách TikTok — bỏ cảnh đó")
        speech = _overlap(b.start, b.end, segments)
        if speech >= speech_beat and b.line is None:
            errors.append(f"cảnh {k} ({b.start}-{b.end}) có {speech:.1f}s lời nói gốc (giọng gốc bị tách bỏ) — phải có câu "
                          "lồng tiếng `line` cho nhân vật đang nói")
        if b.line is not None:
            if wrong_language(b.line.text, language):
                errors.append(f"cảnh {k}: lời thoại phải viết bằng ngôn ngữ đích (không để nguyên lời gốc)")
            chars = speech_chars(b.line.text)
            if chars > d * cps * fill:
                errors.append(f"cảnh {k}: câu \"{b.line.text[:30]}\" {chars} chữ — cảnh chỉ {d:.1f}s, đọc kịp tối đa "
                              f"~{int(d * cps * fill)} chữ: viết ngắn lại")
            bad = find_forbidden(b.line.text, language)
            if bad:
                errors.append(f"cảnh {k}: lời thoại có từ không được phép trên TikTok ({', '.join(bad)})")
    srt = sorted(r.beats, key=lambda b: b.start)
    for a, b in zip(srt, srt[1:]):
        if b.start < a.end - 0.1:
            errors.append(f"cảnh {a.start}-{a.end} và {b.start}-{b.end} chồng nhau — mỗi đoạn gốc chỉ dùng MỘT lần")
    total = sum(max(0.0, b.end - b.start) for b in r.beats)
    if total < float(cfg.get("min_cover", 0.6)) * duration:
        errors.append(f"video mới chỉ dùng {total:.0f}s / {duration:.0f}s — dùng thêm cảnh (≥ "
                      f"{float(cfg.get('min_cover', 0.6)):.0%})")
    if not any(b.line for b in r.beats):
        errors.append("cần ít nhất 1 câu lồng tiếng (ở cảnh nhân vật đang nói / mở miệng)")
    if r.feasible:
        if r.story_diff < int(cfg.get("min_story_diff", 70)):
            errors.append(f"cốt truyện mới chỉ khác {r.story_diff}% — cần ≥ {cfg.get('min_story_diff', 70)}%: đổi mạch truyện / "
                          "vai trò nhân vật / kết mạnh hơn; thật sự không thể thì đặt feasible=false và ghi lý do")
        od = order_diff(r.beats)
        if od < float(cfg.get("min_order_diff", 0.7)):
            errors.append(f"thứ tự cảnh mới còn giống bản gốc (chỉ {od:.0%} cặp cảnh bị đảo, cần ≥ "
                          f"{float(cfg.get('min_order_diff', 0.7)):.0%}) — xếp lại cảnh theo cốt truyện mới")
    for t in r.titles_top:
        bad = find_forbidden(t, language)
        if bad:
            errors.append(f"tiêu đề '{t}' có từ không được phép ({', '.join(bad)})")
    return errors


def make_anim_script(director: Director, analysis_dir: Path, u, *, feedback: str = ""):
    from app.director.policy import cut_ranges
    from app.director.schemas import AnimScript
    from app.director.tasks import (LANGUAGE_NAMES, MARKETS, effective_cps, format_transcript, load_analysis,
                                    localize_brief, pick_evenly)

    cfg = anim_cfg()
    a = load_analysis(analysis_dir)
    sc = a["scenes"]
    duration = float(sc["duration"])
    scenes = sc.get("scenes") or [{"start": 0.0, "end": duration}]
    segs = a["transcript"].get("segments", [])
    cps = effective_cps(config.load("dub"), u.language)
    firsts = {min(a["frames"], key=lambda f, t=s["start"]: abs(f["t"] - t))["file"]: None for s in scenes} \
        if a["frames"] else {}
    chosen = {f["file"]: f for f in a["frames"] if f["file"] in firsts}
    n = int(cfg.get("frames", 50))
    for f in pick_evenly(a["frames"], max(0, n - len(chosen))):
        chosen.setdefault(f["file"], f)
    frames = pick_evenly(sorted(chosen.values(), key=lambda f: f["t"]), max(n, 1))
    variables = {
        "language_name": LANGUAGE_NAMES.get(u.language, u.language), "market": MARKETS.get(u.language, "TikTok"),
        "localize_brief": localize_brief(u), "summary": u.summary_vi, "duration": f"{duration:.0f}",
        "min_story_diff": cfg.get("min_story_diff", 70), "min_order_diff": f"{float(cfg.get('min_order_diff', 0.7)):.0%}",
        "min_cover": f"{float(cfg.get('min_cover', 0.6)):.0%}", "cps": f"{cps:.1f}",
        "scenes": "\n".join(f"- C{i}: {s['start']:.1f}–{s['end']:.1f}s" for i, s in enumerate(scenes, 1)),
        "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) or "(không có)",
        "transcript": format_transcript(segs, 8000) or "(không có lời nói)",
        "feedback": feedback.strip() or "(không có)"}
    banned = cut_ranges(u)

    def repair(r):  # cảnh lố đuôi video vài phần giây → cắt về hết video
        beats = [b.model_copy(update={"end": min(b.end, duration)}) for b in r.beats if b.start < duration - 0.3]
        return r.model_copy(update={"beats": beats or r.beats}), []

    return director.run("anim", variables, AnimScript, [analysis_dir / f["file"] for f in frames],
                        extra_check=lambda r: check_anim(r, u.language, duration=duration, segments=segs, cps=cps,
                                                         cfg=cfg, banned=banned),
                        repair=repair)


def anim_plan(r, default_ratio: str = "16:9"):
    """Kế hoạch dựng: các cảnh theo thứ tự mới, tốc độ 1 (không zoom / lật / chuyển cảnh — hình giữ tự nhiên)."""
    from app.director.schemas import EditPlan, MusicChoice, PlanClip

    clips = [PlanClip(source_start=b.start, source_end=b.end, repeat=True, purpose_vi=b.what_vi[:60]) for b in r.beats]
    return EditPlan(video_index=1, titles_top=r.titles_top[:2], default_ratio=default_ratio, clips=clips,
                    music=MusicChoice(name=None, mood_vi="giữ âm thanh gốc", energy="mid"),
                    editor_notes=r.editor_notes)


def anim_to_dub(r):
    """Câu lồng tiếng gắn với đoạn gốc của cảnh → DubScript (dùng chung trang voice / OmniVoice theo nhân vật)."""
    from app.director.schemas import DubLine, DubScript

    lines = [DubLine(kind="dub", source_start=b.start, source_end=b.end, text=b.line.text, text_vi=b.line.text_vi,
                     speaker=b.line.speaker.strip(), action_vi=b.what_vi) for b in r.beats if b.line]
    return DubScript(video_index=1, lines=lines, editor_notes=r.editor_notes,
                     story_vi=f"Cốt truyện mới (khác ~{r.story_diff}% bản gốc): {r.new_story_vi}")
