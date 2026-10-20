"""THẾ GIỚI ĐỘNG VẬT (chủ dự án yêu cầu 20/10).

Nhiều file ngắn (tool nối thành source/montage.mp4) → dùng TOÀN BỘ cảnh, không bỏ; MỘT lượt AI (`make_wild_script`, prompt
`wild.md`) chỉ ĐẢO THỨ TỰ cảnh cho hợp lý (`order` = hoán vị đủ mọi cảnh) và viết lời dẫn MỚI kiểu phim tài liệu: nói một
đoạn rồi nghỉ (`min_pause_s`), lời dẫn chiếm `min_talk_share`–`max_talk_share` thời lượng. Kế hoạch dựng + kịch bản lồng
tiếng tạo bằng code (`wild_plan`, `wild_to_dub`) → dùng chung trang voice / OmniVoice / phụ đề.
"""

from __future__ import annotations

from pathlib import Path

from app import config
from app.director.base import Director


def wild_cfg() -> dict:
    return config.load("wild") or {}


def units(scenes: list[dict], duration: float, parts: list[dict] | None = None, min_s: float = 0.5) -> list[dict]:
    """Các CẢNH để xếp lại: cảnh máy dò, cắt thêm ở chỗ nối 2 file (montage_parts), cảnh quá ngắn gộp vào cảnh trước.
    Trả [{id (từ 1), start, end}] phủ kín 0 → duration."""
    cuts = {0.0, round(duration, 3)}
    for s in scenes or []:
        cuts.add(round(float(s["start"]), 3))
    for p in parts or []:
        cuts.add(round(float(p["start"]), 3))
    pts = sorted(c for c in cuts if 0 <= c <= duration)
    spans = [[a, b] for a, b in zip(pts, pts[1:]) if b - a > 1e-3]
    out: list[list[float]] = []
    for a, b in spans:
        if out and b - a < min_s:
            out[-1][1] = b
        else:
            out.append([a, b])
    if len(out) > 1 and out[0][1] - out[0][0] < min_s:  # cảnh đầu vụn → gộp vào cảnh sau
        out[1][0] = out[0][0]
        out.pop(0)
    return [{"id": i, "start": round(a, 3), "end": round(b, 3)} for i, (a, b) in enumerate(out, 1)]


def out_times(order: list[int], us: list[dict]) -> dict[int, float]:
    """Giây bắt đầu của từng cảnh trên video mới (theo thứ tự mới)."""
    by = {u["id"]: u for u in us}
    t, out = 0.0, {}
    for i in order:
        if i in by:
            out[i] = t
            t += by[i]["end"] - by[i]["start"]
    return out


def check_wild(r, language: str, *, us: list[dict], cps: float, cfg: dict) -> list[str]:
    from app.director.policy import find_forbidden
    from app.director.tasks import speech_chars, wrong_language

    errors = []
    ids = [u["id"] for u in us]
    by = {u["id"]: u for u in us}
    if sorted(r.order) != ids:
        missing = sorted(set(ids) - set(r.order))
        dup = sorted({i for i in r.order if r.order.count(i) > 1})
        extra = sorted(set(r.order) - set(ids))
        errors.append("`order` phải gồm ĐỦ mọi cảnh, mỗi cảnh đúng MỘT lần (không được bỏ cảnh)"
                      + (f" — thiếu C{', C'.join(map(str, missing))}" if missing else "")
                      + (f" — lặp C{', C'.join(map(str, dup))}" if dup else "")
                      + (f" — không có C{', C'.join(map(str, extra))}" if extra else ""))
        return errors
    total = sum(u["end"] - u["start"] for u in us)
    pos = out_times(r.order, us)
    fill = float(cfg.get("line_fill", 1.15))
    spans = []
    for k, ln in enumerate(r.lines, 1):
        u = by.get(ln.scene)
        if u is None:
            errors.append(f"câu {k}: không có cảnh C{ln.scene}")
            continue
        if ln.end <= ln.start or ln.start < u["start"] - 0.2 or ln.end > u["end"] + 0.2:
            errors.append(f"câu {k}: giây {ln.start}-{ln.end} phải nằm trong cảnh C{ln.scene} "
                          f"({u['start']:.1f}–{u['end']:.1f}s)")
            continue
        o0 = pos[ln.scene] + (ln.start - u["start"])
        spans.append((o0, o0 + (ln.end - ln.start), k))
        chars = speech_chars(ln.text)
        if chars > (ln.end - ln.start) * cps * fill:
            errors.append(f"câu {k}: {chars} chữ — đoạn {ln.end - ln.start:.1f}s chỉ đọc kịp ~"
                          f"{int((ln.end - ln.start) * cps * fill)} chữ: viết ngắn lại hoặc cho đoạn dài hơn")
        if ln.end - ln.start > float(cfg.get("max_line_s", 9)) + 0.3:
            errors.append(f"câu {k}: dài {ln.end - ln.start:.1f}s — tối đa {cfg.get('max_line_s', 9)} giây một câu (nói "
                          "một chút rồi nghỉ)")
        if wrong_language(ln.text, language):
            errors.append(f"câu {k}: phải viết bằng ngôn ngữ đích")
        bad = find_forbidden(ln.text, language)
        if bad:
            errors.append(f"câu {k}: có từ không được phép trên TikTok ({', '.join(bad)})")
    spans.sort()
    if [k for _, _, k in spans] != sorted(k for _, _, k in spans):
        errors.append("các câu phải xếp theo đúng thứ tự hiện trên video mới (theo `order`)")
    pause = float(cfg.get("min_pause_s", 2.0))
    for (a0, a1, ka), (b0, b1, kb) in zip(spans, spans[1:]):
        if b0 - a1 < pause - 0.05:
            errors.append(f"câu {ka} và {kb} cách nhau {max(0.0, b0 - a1):.1f}s — nghỉ ít nhất {pause:.0f}s giữa 2 câu "
                          "(kiểu phim tài liệu: nói một chút rồi để tiếng thiên nhiên)")
    talk = sum(b - a for a, b, _ in spans)
    lo, hi = float(cfg.get("min_talk_share", 0.2)), float(cfg.get("max_talk_share", 0.55))
    if total and talk > hi * total:
        errors.append(f"lời dẫn chiếm {talk / total:.0%} video — tối đa {hi:.0%}: bớt câu / câu ngắn hơn, nghỉ nhiều hơn")
    if total and talk < lo * total:
        errors.append(f"lời dẫn chỉ chiếm {talk / total:.0%} video — cần ít nhất {lo:.0%}: thêm câu ở cảnh đáng nói")
    if spans and spans[0][0] > float(cfg.get("first_line_s", 5)) + 0.2:
        errors.append(f"câu dẫn đầu tiên phải bắt đầu trong {cfg.get('first_line_s', 5)} giây đầu video (mở lời dẫn dắt)")
    return errors


def make_wild_script(director: Director, analysis_dir: Path, u, us: list[dict], *, feedback: str = ""):
    from app.director.schemas import WildScript
    from app.director.tasks import (LANGUAGE_NAMES, MARKETS, effective_cps, format_transcript, load_analysis,
                                    localize_brief, pick_evenly)

    cfg = wild_cfg()
    a = load_analysis(analysis_dir)
    cps = effective_cps(config.load("dub"), u.language)
    picks = {}
    for x in us:  # mỗi cảnh ít nhất một khung (gần giữa cảnh)
        if a["frames"]:
            f = min(a["frames"], key=lambda f, t=(x["start"] + x["end"]) / 2: abs(f["t"] - t))
            picks[f["file"]] = f
    n = int(cfg.get("frames", 60))
    for f in pick_evenly(a["frames"], max(0, n - len(picks))):
        picks.setdefault(f["file"], f)
    frames = pick_evenly(sorted(picks.values(), key=lambda f: f["t"]), max(n, 1))
    total = sum(x["end"] - x["start"] for x in us)
    variables = {
        "language_name": LANGUAGE_NAMES.get(u.language, u.language), "market": MARKETS.get(u.language, "TikTok"),
        "localize_brief": localize_brief(u), "summary": u.summary_vi, "total": f"{total:.0f}", "n": len(us),
        "cps": f"{cps:.1f}", "pause": f"{float(cfg.get('min_pause_s', 2.0)):.0f}",
        "talk_lo": f"{float(cfg.get('min_talk_share', 0.2)):.0%}", "talk_hi": f"{float(cfg.get('max_talk_share', 0.55)):.0%}",
        "max_line": cfg.get("max_line_s", 9), "first_line": cfg.get("first_line_s", 5),
        "scenes": "\n".join(f"- C{x['id']}: {x['start']:.1f}–{x['end']:.1f}s ({x['end'] - x['start']:.1f}s)" for x in us),
        "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) or "(không có)",
        "transcript": format_transcript(a["transcript"].get("segments", []), 4000) or "(không có lời nói)",
        "feedback": feedback.strip() or "(không có)"}

    def repair(r):  # câu lố mép cảnh vài phần giây → kẹp về trong cảnh
        by = {x["id"]: x for x in us}
        lines = []
        for ln in r.lines:
            x = by.get(ln.scene)
            if x:
                ln = ln.model_copy(update={"start": max(ln.start, x["start"]), "end": min(ln.end, x["end"])})
            lines.append(ln)
        return r.model_copy(update={"lines": lines}), []

    return director.run("wild", variables, WildScript, [analysis_dir / f["file"] for f in frames],
                        extra_check=lambda r: check_wild(r, u.language, us=us, cps=cps, cfg=cfg), repair=repair)


def wild_plan(r, us: list[dict], default_ratio: str = "16:9"):
    """Kế hoạch dựng: TOÀN BỘ cảnh theo thứ tự mới, nguyên vẹn, tốc độ 1 (không zoom / lật / hiệu ứng)."""
    from app.director.schemas import EditPlan, MusicChoice, PlanClip

    by = {x["id"]: x for x in us}
    clips = [PlanClip(source_start=by[i]["start"], source_end=by[i]["end"], repeat=True, purpose_vi=f"C{i}")
             for i in r.order]
    return EditPlan(video_index=1, titles_top=r.titles_top[:2], default_ratio=default_ratio, clips=clips,
                    music=MusicChoice(name=None, mood_vi="giữ âm thanh thiên nhiên gốc", energy="low"),
                    editor_notes=r.editor_notes)


def wild_to_dub(r):
    from app.director.schemas import DubLine, DubScript

    lines = [DubLine(kind="narration", source_start=ln.start, source_end=ln.end, text=ln.text, text_vi=ln.text_vi)
             for ln in r.lines]
    return DubScript(video_index=1, lines=lines, editor_notes=r.editor_notes, story_vi=r.story_vi)
