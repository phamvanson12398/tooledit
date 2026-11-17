"""CHỮ THEO HÀNH ĐỘNG (chủ dự án yêu cầu 17/11).

MỘT video, giữ NGUYÊN hình + tiếng gốc (không cắt — trừ đoạn vi phạm chính sách, không đổi thứ tự / khung / tốc độ, không
nhạc). MỘT lượt AI (`make_textnote_script`, prompt `textnote.md`): thỉnh thoảng có hành động đáng chú ý thì viết MỘT dòng
chữ ngắn lên màn hình (ngôn ngữ đích). Kế hoạch dựng tạo bằng code (`textnote_plan`: một clip cả video, chữ = `emphasis`).

Ô tick "🎙️ Có giọng nói" (`JobOptions.textnote_voice`): mỗi dòng còn được ĐỌC thành voice ở NGÔI THỨ NHẤT — như chính người
trong video vừa làm vừa nói thẳng với người xem; khi đó chữ là phụ đề của câu đọc (`textnote_to_dub` → trang voice /
OmniVoice / phụ đề dùng chung), không thêm chữ nhấn.
"""

from __future__ import annotations

from pathlib import Path

from app import config
from app.director.base import Director


def textnote_cfg() -> dict:
    return config.load("textnote") or {}


def limits(cfg: dict, voice: bool) -> dict:
    """Giới hạn đang dùng: có giọng nói thì theo mục `voice` (câu dài hơn, dày hơn)."""
    v = cfg.get("voice") or {}
    if voice:
        return {"min_s": float(cfg.get("min_note_s", 1.2)), "max_s": float(v.get("max_line_s", 7)),
                "gap": float(v.get("min_gap_s", 2.0)), "share": float(v.get("max_share", 0.5)),
                "every": float(v.get("every_s", 8)), "fill": float(v.get("line_fill", 1.15)),
                "overlap": float(v.get("max_speech_overlap", 0.5))}
    return {"min_s": float(cfg.get("min_note_s", 1.2)), "max_s": min(4.0, float(cfg.get("max_note_s", 4.0))),
            "gap": float(cfg.get("min_gap_s", 3.0)), "share": float(cfg.get("max_share", 0.35)),
            "every": float(cfg.get("every_s", 12)), "fill": 0.0, "overlap": 1.0}


def max_chars(cfg: dict, language: str) -> int:
    return int((cfg.get("max_chars") or {}).get(language, 36 if language in ("en", "de") else 18))


def speech_overlap(a: float, b: float, segs: list[dict]) -> float:
    return sum(max(0.0, min(b, float(s["end"])) - max(a, float(s["start"]))) for s in segs)


def check_textnote(r, language: str, *, duration: float, cfg: dict, voice: bool, cps: float = 0.0,
                   segs: list[dict] | None = None) -> list[str]:
    from app.director.policy import find_forbidden
    from app.director.tasks import speech_chars, wrong_language

    lim = limits(cfg, voice)
    errors = []
    prev = None
    for k, n in enumerate(r.notes, 1):
        if not (0 <= n.start < n.end <= duration + 0.3):
            errors.append(f"dòng {k} ({n.start}–{n.end}s) phải nằm trong video 0–{duration:.1f}s và end > start")
            continue
        d = n.end - n.start
        if d < lim["min_s"] - 0.05 or d > lim["max_s"] + 0.05:
            errors.append(f"dòng {k} hiện {d:.1f}s — phải {lim['min_s']:.1f}–{lim['max_s']:.0f} giây")
        if prev is not None and n.start < prev.end + lim["gap"] - 0.05:
            errors.append(f"dòng {k} ({n.start}s) sát dòng trước (hết {prev.end}s) — cách ít nhất {lim['gap']:.0f} giây")
        prev = n
        if not n.text.strip():
            errors.append(f"dòng {k}: chữ rỗng")
            continue
        if wrong_language(n.text, language):
            errors.append(f"dòng {k}: KHÔNG viết bằng ngôn ngữ đích ({language}) — `text` phải là ngôn ngữ đích, nghĩa "
                          "tiếng Việt ghi ở `text_vi`")
        bad = find_forbidden(n.text, language)
        if bad:
            errors.append(f"dòng {k}: có từ không được phép ({', '.join(bad[:3])})")
        if voice:
            need = speech_chars(n.text) / max(cps, 0.1)
            if cps and need > d * lim["fill"] + 0.2:
                errors.append(f"dòng {k}: câu đọc mất ~{need:.1f}s mà chỉ có {d:.1f}s — viết ngắn lại")
            if segs and speech_overlap(n.start, n.end, segs) > d * lim["overlap"]:
                errors.append(f"dòng {k} ({n.start}–{n.end}s) đè lên lời nói gốc — chuyển sang chỗ lặng gần đó")
        elif len(n.text.strip()) > max_chars(cfg, language):
            errors.append(f"dòng {k}: {len(n.text.strip())} ký tự — tối đa {max_chars(cfg, language)} ký tự (một dòng)")
    total = sum(max(0.0, n.end - n.start) for n in r.notes)
    if duration > 0 and total > duration * lim["share"] + 0.5:
        errors.append(f"chữ hiện tổng {total:.0f}s = {total / duration:.0%} video — tối đa {lim['share']:.0%} (chỉ ở "
                      "hành động đáng chú ý, bỏ bớt dòng)")
    return errors


# lỗi KHÔNG được bỏ qua khi AI sai 3 lần: sai ngôn ngữ, từ cấm, ngoài video
HARD_MARKS = ("ngôn ngữ đích", "không được phép", "phải nằm trong video", "chữ rỗng")


def hard_problems(problems: list[str]) -> list[str]:
    return [p for p in problems if any(m in p for m in HARD_MARKS)]


def repair_textnote(r, duration: float, cfg: dict, voice: bool):
    """Tự sửa lỗi vặt: xếp theo thời gian, kẹp vào video, dòng dài quá thì rút lại, dòng quá ngắn thì kéo dài (còn chỗ),
    dòng sát dòng trước quá thì lùi chút ít (≤ `max_shift_s`, để chữ vẫn đúng lúc hành động) hoặc bỏ."""
    lim = limits(cfg, voice)
    fixes, out = [], []
    for n in sorted(r.notes, key=lambda n: n.start):
        a, b = max(0.0, n.start), min(duration, n.end)
        if b - a > lim["max_s"]:
            b = a + lim["max_s"]
            fixes.append("rút dòng chữ dài quá")
        if b - a < lim["min_s"]:
            b = min(duration, a + lim["min_s"])
        if out and a < out[-1].end + lim["gap"]:
            shift = out[-1].end + lim["gap"] - a
            if shift <= float(cfg.get("max_shift_s", 1.5)) and b + shift <= duration:  # lùi xa quá thì lệch hành động
                a, b = a + shift, b + shift
                fixes.append("lùi dòng chữ cho đủ khoảng cách")
            else:
                fixes.append("bỏ dòng chữ sát dòng trước")
                continue
        if b - a < lim["min_s"] - 0.05:
            continue
        out.append(n.model_copy(update={"start": round(a, 2), "end": round(b, 2)}))
    if not out:
        return r, []
    return r.model_copy(update={"notes": out}), sorted(set(fixes))


def make_textnote_script(director: Director, analysis_dir: Path, u, language: str, *, voice: bool = False,
                         feedback: str = ""):
    from app.director.base import DirectorError
    from app.director.schemas import TextNoteScript
    from app.director.tasks import (
        LANGUAGE_NAMES,
        MARKETS,
        effective_cps,
        format_transcript,
        load_analysis,
        pick_evenly,
    )

    cfg = textnote_cfg()
    lim = limits(cfg, voice)
    a = load_analysis(analysis_dir)
    duration = float(a["scenes"]["duration"])
    segs = a["transcript"].get("segments", [])
    cps = effective_cps(config.load("dub"), language) if voice else 0.0
    frames = pick_evenly(a["frames"], int(cfg.get("frames", 60)))
    lname = LANGUAGE_NAMES.get(language, language)
    voice_rule = (
        f"- CÓ GIỌNG NÓI: mỗi dòng còn được ĐỌC thành voice và hiện làm phụ đề. Viết ở NGÔI THỨ NHẤT — như CHÍNH người "
        f"trong video vừa làm vừa nói thẳng với người xem (vd \"Giờ mình cho trứng vào nè\", \"Chỗ này phải làm thật nhẹ "
        f"tay nha\"), văn nói tự nhiên của người bản xứ, gần gũi. Câu phải đọc KỊP: ≤ (end − start) × {cps:.1f} chữ / giây "
        f"(không tính dấu cách, dấu câu). Đặt câu vào CHỖ LẶNG (không đè lời nói gốc — xem lời nói gốc bên dưới có giây).")\
        if voice else (
        f"- KHÔNG có giọng nói: chữ ngắn gọn như chú thích / bình luận trên màn hình, MỘT dòng ≤ {max_chars(cfg, language)} "
        "ký tự, emoji tối đa 1 cái khi hợp.")
    variables = {
        "language_name": lname, "market": MARKETS.get(language, "TikTok"), "summary": u.summary_vi,
        "duration": f"{duration:.0f}", "min_s": f"{lim['min_s']:.1f}", "max_s": f"{lim['max_s']:.0f}",
        "gap": f"{lim['gap']:.0f}", "share": f"{lim['share']:.0%}", "every": f"{lim['every']:.0f}",
        "voice_rule": voice_rule,
        "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) or "(không có)",
        "transcript": format_transcript(segs, int(cfg.get("transcript_chars", 5000))) or "(không có lời nói)",
        "feedback": feedback.strip() or "(không có)"}

    def check(r):
        return check_textnote(r, language, duration=duration, cfg=cfg, voice=voice, cps=cps, segs=segs)

    try:
        return director.run("textnote", variables, TextNoteScript, [analysis_dir / f["file"] for f in frames],
                            extra_check=check, repair=lambda r: repair_textnote(r, duration, cfg, voice))
    except DirectorError as exc:  # AI sai vặt 3 lần → vẫn dùng bản cuối nếu chỉ còn lỗi nhỏ (như Thế giới động vật)
        if exc.last is None or not cfg.get("accept_minor", True) or hard_problems(exc.problems):
            raise
        director.log("⚠️ AI vẫn còn lỗi nhỏ sau 3 lần — vẫn dùng bản cuối: " + "; ".join(exc.problems))
        return exc.last.model_copy(update={"editor_notes": (exc.last.editor_notes + " | ⚠️ Còn lỗi nhỏ (tool vẫn dùng): "
                                                            + "; ".join(exc.problems))[:2000]})


def keep_ranges(duration: float, cuts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Cả video trừ các đoạn vi phạm chính sách (giữ nguyên thứ tự)."""
    out, t = [], 0.0
    for a, b in sorted((max(0.0, a), min(duration, b)) for a, b in cuts):
        if a > t + 0.05:
            out.append((round(t, 3), round(a, 3)))
        t = max(t, b)
    if duration > t + 0.05:
        out.append((round(t, 3), round(duration, 3)))
    return out


def textnote_plan(r, duration: float, cuts: list[tuple[float, float]], cfg: dict, *, voice: bool,
                  default_ratio: str = "16:9"):
    """Kế hoạch dựng: cả video nguyên vẹn, tốc độ 1 (chỉ bỏ đoạn vi phạm); không voice thì chữ = `emphasis`."""
    from app.director.schemas import EditPlan, Emphasis, MusicChoice, PlanClip

    ranges = keep_ranges(duration, cuts) or [(0.0, round(duration, 3))]
    clips = [PlanClip(source_start=a, source_end=b, purpose_vi="giữ nguyên video gốc") for a, b in ranges]
    pos = "center" if cfg.get("position") == "center" else "top"
    emphasis = [] if voice else [
        Emphasis(source_time=n.start, duration=max(0.4, min(4.0, n.end - n.start)), text=n.text.strip(), position=pos)
        for n in r.notes if n.text.strip()]
    return EditPlan(video_index=1, titles_top=[], default_ratio=default_ratio, clips=clips, emphasis=emphasis,
                    music=MusicChoice(name=None, mood_vi="giữ tiếng gốc", energy="low"),
                    editor_notes=f"Giữ nguyên video gốc, {len(r.notes)} dòng "
                                 + ("lời nói ngôi thứ nhất (voice + phụ đề)." if voice else "chữ theo hành động.")
                                 + (f" {r.editor_notes}" if r.editor_notes else ""))


def textnote_to_dub(r):
    from app.director.schemas import DubLine, DubScript

    lines = [DubLine(kind="narration", source_start=n.start, source_end=n.end, text=n.text, text_vi=n.text_vi)
             for n in r.notes if n.text.strip()]
    return DubScript(video_index=1, lines=lines, editor_notes=r.editor_notes)
