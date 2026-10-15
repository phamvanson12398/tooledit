"""Chế độ "CONTENT NHIỀU PHIM TỪ BÀI TIKTOK ẢNH" (chủ dự án yêu cầu 14/10).

1. Bài gốc: ảnh + tiêu đề / mô tả — chủ dự án tải ảnh lên và tự gõ tiêu đề (14/10: bỏ lấy từ link).
2. AI xem ảnh + tiêu đề → nhận ra các PHIM / nhân vật → viết content MỚI (lời đọc ngôn ngữ video), mỗi câu gắn một phim,
   kiểu hình (video / dừng hình) và cảnh cần tìm (`make_idea`, prompt `films_idea.md`).
3. Chủ dự án thả file từng phim → phân tích (nhanh: dò cảnh + khung hình) → AI tìm cảnh cho từng câu TRONG ĐÚNG PHIM đó
   (`make_match`, prompt `films_match.md`, mỗi phim một lượt hỏi, chạy song song).
4. Bài đọc thành kịch bản voice như review (`to_script`) → thu voice → app/planner/films_build.py dựng.
Cấu hình: config/films.yaml.
"""

from __future__ import annotations

import re
from pathlib import Path

from app import config
from app.director.base import Director


def load_cfg() -> dict:
    return config.load("films")


def voice_cps(language: str) -> float:
    """Tốc độ giọng đọc — dùng chung với giọng review (cùng kiểu đọc liền một mạch)."""
    from app.director.tasks import effective_cps, review_dub_cfg

    return effective_cps(review_dub_cfg(config.load("dub")), language)


def est_s(text: str, language: str) -> float:
    from app.director.tasks import speech_chars

    return max(0.8, speech_chars(text) / max(voice_cps(language), 1e-6))


def freeze_part(est: float, cfg: dict) -> float:
    """Phần dừng hình của một câu freeze: video chạy freeze_lead_s rồi đứng hình, tối đa freeze_max_s."""
    lead = float(cfg.get("freeze_lead_s", 0.8))
    return max(0.0, min(est - lead, float(cfg.get("freeze_max_s", 3.0))))


# ---------------- AI viết content ----------------

def check_idea(idea, language: str, cfg: dict, music_names: set[str]) -> list[str]:
    from app.director.policy import find_forbidden
    from app.director.tasks import LANG_SCRIPT_VI, localize_violations, wrong_language

    errors = []
    keys = [f.key for f in idea.films]
    if len(set(keys)) != len(keys):
        errors.append("mã phim (`key`) bị trùng — mỗi phim một mã riêng")
    if len(keys) > int(cfg.get("max_films", 10)):
        errors.append(f"tối đa {cfg.get('max_films', 10)} phim")
    used = {ln.film for ln in idea.lines}
    errors += [f"câu {i}: phim '{ln.film}' không có trong `films`" for i, ln in enumerate(idea.lines, 1)
               if ln.film not in keys]
    errors += [f"phim {k} không có câu nào — bỏ khỏi `films` hoặc thêm câu" for k in keys if k not in used]
    lang = LANG_SCRIPT_VI.get(language, language)
    total, frozen = 0.0, 0.0
    for i, ln in enumerate(idea.lines, 1):
        e = est_s(ln.text, language)
        total += e
        if ln.shot == "freeze":
            frozen += freeze_part(e, cfg)
            if not ln.label.strip():
                errors.append(f"câu {i} dừng hình: thiếu `label` (tên nhân vật hiện lên khi đứng hình)")
            elif wrong_language(ln.label, language):
                errors.append(f"câu {i}: `label` phải viết bằng {lang}")
        if e > 12:
            errors.append(f"câu {i} đọc ~{e:.0f}s — tách thành 2 câu")
        if wrong_language(ln.text, language):
            errors.append(f"câu {i}: `text` phải viết bằng {lang} (nghĩa tiếng Việt để ở `text_vi`)")
        if find_forbidden(ln.text, language):
            errors.append(f"câu {i} có từ không được phép trên TikTok")
        odd = localize_violations(ln.text, language)
        if odd:
            errors.append(f"câu {i}: '{', '.join(odd)}' không quen với khán giả này")
    lo, hi = (float(x) for x in cfg.get("video_s") or [60, 120])
    cps = voice_cps(language)
    if total < lo * 0.92 or total > hi * 1.03:
        errors.append(f"cả bài đọc ~{total:.0f}s (tốc độ {cps:.1f} chữ/giây) — cần {lo:.0f}–{hi:.0f}s: "
                      + ("viết THÊM" if total < lo * 0.92 else "rút gọn bớt"))
    share = float(cfg.get("image_share", 0.3))
    if not any(ln.shot == "freeze" for ln in idea.lines):
        errors.append("chưa có câu nào DỪNG HÌNH (`shot: freeze`) — chủ dự án thích kiểu này, dùng ở khoảnh khắc đắt "
                      "của mỗi nhân vật")
    elif total and frozen / total > share + 0.05:
        errors.append(f"dừng hình chiếm ~{frozen / total:.0%} thời lượng — tối đa {share:.0%}: đổi bớt câu sang `video`")
    for t in idea.titles_top + [idea.caption]:
        if wrong_language(t, language):
            errors.append(f"'{t[:30]}' phải viết bằng {lang}")
    if idea.music.name and idea.music.name not in music_names:
        errors.append(f"bài nhạc '{idea.music.name}' không có trong danh sách — chọn tên đúng hoặc null")
    if len(idea.hashtags_vi) != len(idea.hashtags):
        errors.append("`hashtags_vi` phải cùng số phần tử với `hashtags`")
    return errors


def make_idea(director: Director, images: list[Path], title: str, language: str, *, music_items: list | None = None,
              feedback: str = "", previous=None, uploader: str = ""):
    """AI xem ảnh + tiêu đề bài gốc → content MỚI nhiều phim (FilmsIdea)."""
    from app.director.schemas import FilmsIdea
    from app.director.tasks import LANGUAGE_NAMES, MARKETS, cap_per_mood, review_style_examples

    cfg = load_cfg()
    lo, hi = (float(x) for x in cfg.get("video_s") or [60, 120])
    cps = voice_cps(language)
    music = cap_per_mood(music_items or [], 4, 60)
    variables = {
        "language_name": LANGUAGE_NAMES.get(language, language), "market": MARKETS.get(language, "TikTok"),
        "title": title.strip() or "(không có tiêu đề)", "uploader": uploader or "(không rõ)",
        "images": "\n".join(f"- {Path(p).name}" for p in images) or "(không có ảnh — chỉ dựa vào tiêu đề)",
        "video_s": f"{lo:.0f}–{hi:.0f}", "cps": f"{cps:.1f}", "chars": f"{int(lo * cps)}–{int(hi * cps)}",
        "image_share": f"{float(cfg.get('image_share', 0.3)):.0%}", "max_films": cfg.get("max_films", 10),
        "freeze_max_s": cfg.get("freeze_max_s", 3.0),
        "music_list": "\n".join(f"- {m.name} ({m.category}{', ' + m.mood if m.mood else ''})" for m in music)
        or "(không có — đặt name = null)",
        "style_examples": review_style_examples(),
        "feedback": (f"GÓP Ý CỦA CHỦ DỰ ÁN cho bản trước (sửa ĐÚNG theo góp ý, giữ cái hay của bản trước):\n"
                     f"{feedback.strip()}\n\nBản trước:\n" + "\n".join(
                         f"[{i}] ({ln.film}, {ln.shot}) {ln.text} // {ln.text_vi}"
                         for i, ln in enumerate(previous.lines, 1))
                     if feedback.strip() and previous is not None else feedback.strip() or "(không có)"),
    }
    names = {m.name for m in music_items or []}
    return director.run("films_idea", variables, FilmsIdea, list(images),
                        extra_check=lambda r: check_idea(r, language, cfg, names))


# ---------------- AI tìm cảnh trong từng phim ----------------

def check_match(r, lines: dict[int, object], duration: float, language: str, cfg: dict) -> list[str]:
    errors = []
    got = {p.line for p in r.picks}
    miss = sorted(set(lines) - got)
    if miss:
        errors.append(f"thiếu cảnh cho câu {', '.join(map(str, miss))} — mỗi câu được giao một cảnh")
    lead = float(cfg.get("freeze_lead_s", 0.8))
    for p in r.picks:
        ln = lines.get(p.line)
        if ln is None:
            continue
        name = f"câu {p.line}"
        if p.start < 0 or p.end > duration + 0.5 or p.end <= p.start:
            errors.append(f"{name}: {p.start}–{p.end}s phải nằm trong phim (0–{duration:.0f}s)")
            continue
        span = p.end - p.start
        if ln.shot == "freeze":
            if p.freeze_t is None or not p.start - 0.05 <= p.freeze_t <= p.end + 0.05:
                errors.append(f"{name} dừng hình: `freeze_t` phải nằm trong {p.start:.1f}–{p.end:.1f}s")
            elif p.freeze_t - p.start < lead - 0.05:
                errors.append(f"{name}: `start` phải sớm hơn `freeze_t` ít nhất {lead:.1f}s (video chạy rồi mới đứng)")
        else:
            need = max(1.0, (est_s(ln.text, language)) * 0.9)
            if span < need:
                errors.append(f"{name} đọc ~{need / 0.9:.1f}s nhưng đoạn phim chỉ {span:.1f}s — chọn đoạn dài hơn")
    picks = sorted(r.picks, key=lambda p: p.start)
    for a, b in zip(picks, picks[1:]):
        ov = min(a.end, b.end) - max(a.start, b.start)
        if ov > 0.5 * min(a.end - a.start, b.end - b.start):
            errors.append(f"câu {a.line} và câu {b.line} dùng gần như cùng một cảnh — chọn cảnh khác cho một câu")
    return errors


def make_match(director: Director, analysis_dir: Path, footage: int, film, lines: dict[int, object], language: str):
    """Một phim: AI xem khung hình của phim đó, chọn đoạn phim (và giây đứng hình) cho từng câu được giao."""
    from app.director.schemas import FilmMatch
    from app.director.tasks import load_analysis

    cfg = load_cfg()
    a = load_analysis(analysis_dir, footage)
    duration = float(a["scenes"]["duration"])
    frames = sorted(a["frames"], key=lambda f: f["t"])
    variables = {
        "title": film.title, "title_vi": film.title_vi, "duration": f"{duration:.0f}",
        "characters": ", ".join(film.characters) or "(không ghi)",
        "lead": f"{float(cfg.get('freeze_lead_s', 0.8)):.1f}",
        "lines": "\n".join(f"[{n}] {'DỪNG HÌNH' if ln.shot == 'freeze' else 'video'} · đọc ~{est_s(ln.text, language):.1f}s"
                           f" · cần cảnh: {ln.want_vi} · lời: {ln.text_vi}" for n, ln in sorted(lines.items())),
        "scenes": ", ".join(f"{s['start']:.0f}" for s in a["scenes"].get("scenes", [])[:400]) or "(không có)",
        "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) or "(không có)",
        "transcript": "\n".join(f"[{s['start']:.0f}] {s['text']}" for s in a["transcript"].get("segments", [])[:400])
        or "(chế độ nhanh: không nghe lời thoại — tìm cảnh bằng khung hình)",
    }

    def repair(r):  # chỉ giữ câu của phim này; kẹp vào trong phim; câu dừng hình lùi start cho đủ đoạn chạy trước
        lead = float(cfg.get("freeze_lead_s", 0.8))
        picks, fixes = [], []
        for p in r.picks:
            if p.line not in lines:
                continue
            upd = {"start": max(0.0, p.start), "end": min(duration, p.end)}
            if lines[p.line].shot == "freeze" and p.freeze_t is not None and p.freeze_t - upd["start"] < lead:
                upd["start"] = max(0.0, p.freeze_t - lead)
                fixes.append(f"câu {p.line}: lùi đầu đoạn về {upd['start']:.1f}s cho video chạy trước khi đứng hình")
            picks.append(p.model_copy(update=upd))
        return r.model_copy(update={"picks": picks}), fixes

    return director.run("films_match", variables, FilmMatch, [analysis_dir / f["file"] for f in frames],
                        extra_check=lambda r: check_match(r, lines, duration, language, cfg), repair=repair)


# ---------------- thành kịch bản voice / caption ----------------

def to_script(idea, picks: dict[int, dict]):
    """Bài đọc → DubScript (video 1) để dùng chung trang voice / đọc cả bài một file / OmniVoice với review.
    source_start/end = đoạn phim của câu (mỗi câu một phim khác nhau — chỉ để hiện cho chủ dự án)."""
    from app.director.schemas import DubLine, DubScript

    titles = {f.key: f.title_vi or f.title for f in idea.films}
    lines = []
    for i, ln in enumerate(idea.lines, 1):
        p = picks.get(i) or {"start": 0.0, "end": 1.0}
        shot = "⏸️ dừng hình" if ln.shot == "freeze" else "🎬"
        lines.append(DubLine(kind="narration", source_start=float(p["start"]), source_end=float(p["end"]),
                             text=ln.text, text_vi=ln.text_vi,
                             action_vi=f"{titles.get(ln.film, ln.film)} {shot} — {ln.want_vi}"))
    return DubScript(video_index=1, lines=lines, editor_notes=idea.editor_notes, story_vi=idea.story_vi)


def to_captions(idea):
    from app.director.schemas import Captions

    return Captions(video_index=1, caption=idea.caption, caption_vi=idea.caption_vi, hashtags=idea.hashtags,
                    hashtags_vi=idea.hashtags_vi, editor_notes=idea.editor_notes)
