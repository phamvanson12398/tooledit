"""BÁN CONTENT YOUTUBE (chủ dự án yêu cầu 19/10): video nguồn dài (< 1h30) → video YouTube 10–20 phút (hoặc AI tự chọn).

1. Danh mục cảnh: dùng chung `app.director.ideas.make_catalog` (AI xem từng phần ~10 phút song song).
2. Dàn ý (`make_outline`, prompt `yt_outline.md`): góc làm (content MỚI hoặc xào nấu lại content gốc, đúng chính sách
   YouTube), tiêu đề, mô tả, tag, ý tưởng ảnh bìa, các CHƯƠNG (tên, nội dung, giây, cảnh dùng). Tool chỉnh tổng giây đúng
   thời lượng chủ dự án chọn (hoặc AI tự chọn trong `auto_min`). Tick "Dừng duyệt dàn ý" thì job chờ duyệt / góp ý.
3. Lời từng chương (`make_sell_script(idea=chapter_job(...))`, prompt `yt_chapter.md`) viết SONG SONG, ghép thành MỘT bài
   (`merge`), rồi dùng chung voice / dựng / đóng gói của Bán content.
4. Gói YouTube (`package_text`): tiêu đề, mô tả + mốc chương (tool tính từ voice thật), tag, ý tưởng ảnh bìa.
"""

from __future__ import annotations

from pathlib import Path

from app import config
from app.director.base import Director


def yt_cfg() -> dict:
    return config.load("youtube") or {}


def target_seconds(outline_min: float, minutes: int | float, cfg: dict | None = None) -> float:
    """Tổng thời lượng (giây): chủ dự án chọn thì đúng số đó; không chọn thì số AI đề xuất, kẹp trong auto_min."""
    cfg = cfg if cfg is not None else yt_cfg()
    if minutes:
        return float(minutes) * 60
    lo, hi = (cfg.get("auto_min") or [5, 20])[:2]
    return min(max(float(outline_min), float(lo)), float(hi)) * 60


def normalize(outline, minutes: int | float = 0, cfg: dict | None = None):
    """Chia lại giây các chương cho tổng = thời lượng đích (giữ tỉ lệ AI đề xuất, kẹp min / max mỗi chương)."""
    cfg = cfg if cfg is not None else yt_cfg()
    total = target_seconds(outline.target_min, minutes, cfg)
    lo, hi = float(cfg.get("min_chapter_s", 45)), float(cfg.get("max_chapter_s", 240))
    raw = [max(1.0, c.seconds) for c in outline.chapters]
    secs = [total * r / sum(raw) for r in raw]
    for _ in range(5):  # kẹp rồi chia lại phần dư cho các chương chưa chạm biên
        secs = [min(max(x, lo), hi) for x in secs]
        diff = total - sum(secs)
        free = [i for i, x in enumerate(secs) if (diff > 0 and x < hi) or (diff < 0 and x > lo)]
        if abs(diff) < 0.5 or not free:
            break
        for i in free:
            secs[i] += diff / len(free)
    chapters = [c.model_copy(update={"seconds": round(x, 1)}) for c, x in zip(outline.chapters, secs)]
    return outline.model_copy(update={"chapters": chapters, "target_min": round(sum(secs) / 60, 1)})


def check_outline(r, ids: set[str], language: str, cfg: dict) -> list[str]:
    from app.director.policy import find_forbidden

    errors = []
    for k, c in enumerate(r.chapters, 1):
        if not [x for x in c.shots if x.strip().upper() in ids]:
            errors.append(f"chương {k} ({c.title_vi}) không có mã cảnh hợp lệ trong danh mục")
    for t in [*r.titles, *r.titles_top, r.description, *r.tags, *(c.title for c in r.chapters)]:
        bad = find_forbidden(t, language, platform="youtube")
        if bad:
            errors.append(f"'{t[:40]}' có từ không được phép ({', '.join(bad)}) — viết lại")
    return errors


def make_outline(director: Director, analysis_dir: Path, cat, u, *, language: str, minutes: int | float = 0,
                 feedback: str = "", previous=None):
    """AI lập dàn ý video YouTube → YtOutline đã chỉnh giây chương theo thời lượng đích."""
    from app.director.ideas import catalog_text, shot_id
    from app.director.schemas import YtOutline
    from app.director.tasks import (LANGUAGE_NAMES, format_transcript_spread, load_analysis, localize_brief,
                                    pick_evenly)

    cfg = yt_cfg()
    a = load_analysis(analysis_dir)
    duration = float(a["scenes"]["duration"])
    ids = {shot_id(i) for i in range(1, len(cat.shots) + 1)}
    usable = sum(s.end - s.start for s in cat.shots if s.quality >= 2)
    best = sorted(cat.shots, key=lambda s: -s.quality)[: int(cfg.get("outline_frames", 40)) * 2]
    picks = {}
    for s in sorted(best, key=lambda s: s.start):
        if a["frames"]:
            f = min(a["frames"], key=lambda f, t=(s.start + s.end) / 2: abs(f["t"] - t))
            picks[f["file"]] = f
    frames = pick_evenly(sorted(picks.values(), key=lambda f: f["t"]), int(cfg.get("outline_frames", 40)))
    lo, hi = (cfg.get("auto_min") or [5, 20])[:2]
    length = (f"Chủ dự án chọn **{minutes} phút** — chia chương cho tổng đúng khoảng {minutes} phút."
              if minutes else
              f"Chủ dự án để AI TỰ CHỌN: xem nội dung dày tới đâu rồi đề xuất `target_min` trong {lo}–{hi} phút — đủ ý "
              "thì dài, ít ý thì ngắn, KHÔNG kéo dài nhân tạo.")
    variables = {
        "language_name": LANGUAGE_NAMES.get(language, language), "localize_brief": localize_brief(u),
        "summary": u.summary_vi, "source_min": f"{duration / 60:.0f}", "usable_min": f"{usable / 60:.0f}",
        "length": length, "catalog": catalog_text(cat),
        "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) or "(không có)",
        "transcript": format_transcript_spread(a["transcript"].get("segments", []), 15000) or "(không có lời nói)",
        "feedback": (f"Sửa ĐÚNG theo góp ý này:\n{feedback.strip()}\n\nDàn ý trước:\n" + outline_text(previous)
                     if feedback.strip() and previous else "(không có)")}

    def repair(r):
        fixes, chapters = [], []
        for k, c in enumerate(r.chapters, 1):
            good = [x.strip().upper() for x in c.shots if x.strip().upper() in ids]
            if len(good) != len(c.shots):
                fixes.append(f"chương {k}: bỏ mã cảnh không có trong danh mục")
            chapters.append(c.model_copy(update={"shots": good or c.shots}))
        return r.model_copy(update={"chapters": chapters}), fixes

    r = director.run("yt_outline", variables, YtOutline, [analysis_dir / f["file"] for f in frames],
                     extra_check=lambda r: check_outline(r, ids, language, cfg), repair=repair)
    return normalize(r, minutes, cfg)


def outline_text(o) -> str:
    if o is None:
        return ""
    return "\n".join([f"Góc làm: {o.angle_vi}", f"Tiêu đề: {o.titles[0]}"] +
                     [f"{k}. {c.title} ({c.title_vi}, {c.seconds:.0f}s): {c.summary_vi}"
                      for k, c in enumerate(o.chapters, 1)])


def chapter_job(o, k: int, cat) -> dict:
    """Chương k (từ 1) → tham số cho make_sell_script(idea=…): kho cảnh của chương + bối cảnh cả dàn ý."""
    from app.director.ideas import shot_id

    shots = {shot_id(i): s for i, s in enumerate(cat.shots, 1)}
    c = o.chapters[k - 1]
    pool = sorted({(shots[x].start, shots[x].end, shots[x].desc_vi) for x in c.shots if x in shots})
    return {"chapter": k, "n": len(o.chapters), "title": c.title, "title_vi": c.title_vi, "summary_vi": c.summary_vi,
            "seconds": c.seconds, "video_title": o.titles[0], "outline": outline_text(o),
            "pool": [{"start": a, "end": b, "desc_vi": d} for a, b, d in pool]}


def chapter_brief(ch: dict) -> str:
    k, n = ch["chapter"], ch["n"]
    pos = ("chương MỞ ĐẦU — câu 1 là hook (giữ người xem ngay 15–30 giây đầu: hé lộ điều hấp dẫn nhất video sẽ nói), rồi "
           "giới thiệu ngắn video này nói gì" if k == 1 else
           "chương CUỐI — khép lại gọn, tóm ý đáng nhớ, có thể kêu gọi đăng ký kênh / bấm thích / bình luận ở cuối" if k == n
           else "chương GIỮA — câu đầu nối tự nhiên từ chương trước, câu cuối gợi tò mò sang chương sau")
    return "\n".join([f"- Video: \"{ch['video_title']}\"", f"- Đây là chương {k}/{n}: {ch['title']} ({ch['title_vi']})",
                      f"- Chương này nói: {ch['summary_vi']}", f"- Vị trí: {pos}",
                      "- Dàn ý cả video (để nối mạch, KHÔNG viết lấn sang chương khác):", ch["outline"]])


def merge(scripts: list, outline):
    """Lời các chương → MỘT SellScript (video 1) + chỉ số câu đầu mỗi chương."""
    from app.director.schemas import SellScript

    lines, starts = [], []
    for s in scripts:
        starts.append(len(lines))
        lines += list(s.lines)
    first = scripts[0]
    merged = SellScript(video_index=1, onscreen_text=first.onscreen_text,
                        outline_vi=outline_text(outline), titles_top=(outline.titles_top or first.titles_top)[:2],
                        music=first.music, lines=lines,
                        editor_notes=" | ".join(f"Ch{k}: {s.editor_notes}" for k, s in enumerate(scripts, 1)))
    return merged, starts


def fmt_ts(sec: float) -> str:
    sec = int(round(sec))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def package_text(o, stamps: list[tuple[float, str]]) -> str:
    """Gói đăng YouTube: tiêu đề, mô tả + mốc chương (mốc đầu luôn 00:00 — yêu cầu của YouTube), tag, ý tưởng ảnh bìa."""
    out = ["=== TIÊU ĐỀ (chọn một) ==="]
    for i, t in enumerate(o.titles):
        vi = o.titles_vi[i] if i < len(o.titles_vi) else ""
        out.append(f"{i + 1}. {t}" + (f"   ({vi})" if vi else ""))
    out += ["", "=== MÔ TẢ (dán nguyên vào ô mô tả) ===", o.description.strip(), ""]
    if stamps:
        out += [f"{fmt_ts(0 if i == 0 else t)} {title}" for i, (t, title) in enumerate(stamps)]
    out += ["", "=== TAG ===", ", ".join(o.tags), "", "=== Ý TƯỞNG ẢNH BÌA ==="]
    out += [f"- {x}" for x in o.thumbnails_vi]
    out += ["", f"(Ghi chú editor: {o.editor_notes})"]
    return "\n".join(out) + "\n"
