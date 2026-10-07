"""Tuân thủ Nguyên tắc cộng đồng TikTok: đoạn vi phạm bị CẮT BỎ khỏi video.

- Đạo diễn đánh dấu đoạn vi phạm (`Understanding.policy_issues`) ở bước hiểu nội dung.
- Máy tự dò thêm từ tục trong transcript (mốc giây từng từ) theo `config/policy.yaml`.
- Kế hoạch dựng: clip chạm vào đoạn vi phạm được tự tách/cắt (không cần hỏi lại đạo diễn); hook không được dùng
  đoạn vi phạm; chữ trên màn hình, câu hook, caption không được chứa từ tục.
"""

from __future__ import annotations

import re

from app import config
from app.director.schemas import POLICY_VI, PolicyIssue


def load_cfg() -> dict:
    return config.load("policy") or {}


def _find(text: str, lists: dict, langs: list[str]) -> list[str]:
    hits = []
    low = text.lower()
    for lang in langs:
        for w in lists.get(lang) or []:
            w = str(w).lower()
            if lang == "en":  # khớp theo đầu từ: "fuck" bắt "fucking", "pushit" thì không
                if re.search(rf"(?<![a-z0-9]){re.escape(w)}", low):
                    hits.append(w)
            elif w in low:
                hits.append(w)
    return hits


def find_bad_words(text: str, language: str | None = None, cfg: dict | None = None) -> list[str]:
    """Từ tục có trong text. language=None: kiểm tra mọi ngôn ngữ."""
    cfg = load_cfg() if cfg is None else cfg
    if not cfg.get("enabled", True) or not text:
        return []
    lists = cfg.get("bad_words") or {}
    return _find(text, lists, [language] if language in lists else list(lists))


def find_platforms(text: str, language: str | None = None, cfg: dict | None = None) -> list[str]:
    """Tên / lời kêu gọi của nền tảng khác (YouTube, Instagram...). Luôn xét mọi ngôn ngữ, vì video tiếng Hàn/Nhật
    vẫn hay nói "YouTube" bằng chữ Latin."""
    cfg = load_cfg() if cfg is None else cfg
    if not cfg.get("enabled", True) or not text:
        return []
    lists = cfg.get("other_platforms") or {}
    return _find(text, lists, list(lists))


def find_forbidden(text: str, language: str | None = None, cfg: dict | None = None) -> list[str]:
    """Mọi thứ không được xuất hiện trong chữ trên màn hình / hook / caption / hashtag trên TikTok."""
    return find_bad_words(text, language, cfg) + find_platforms(text, language, cfg)


def merge_ranges(ranges: list[tuple[float, float]], gap: float = 0.0) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for s, e in sorted(ranges):
        if out and s <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(round(s, 3), round(e, 3)) for s, e in out]


def _word_hits(segments: list[dict], language: str | None, cfg: dict, finder, whole_sentence_s: float = 0.0
               ) -> list[tuple[float, float]]:
    """Đoạn lời thoại chứa từ bị cấm: theo mốc từng từ; câu ngắn ≤ whole_sentence_s giây thì cắt cả câu."""
    ranges: list[tuple[float, float]] = []
    for s in segments:
        if not finder(s.get("text", ""), language, cfg):
            continue
        if whole_sentence_s and s["end"] - s["start"] <= whole_sentence_s:
            ranges.append((s["start"], s["end"]))
            continue
        words = s.get("words") or []
        hit = [(w["start"], w["end"]) for w in words if finder(w.get("word", ""), language, cfg)]
        if not hit and words:  # từ tục bị tách thành nhiều "từ" (tiếng Hàn/Nhật): tìm cụm từ liền nhau chứa nó
            for span in range(2, 5):  # cụm ngắn nhất trước, để không cắt lan sang từ vô hại
                hit = [(words[i]["start"], words[i + span - 1]["end"]) for i in range(len(words) - span + 1)
                       if finder("".join(w.get("word", "") for w in words[i:i + span]), language, cfg)]
                if hit:
                    break
        ranges += hit or [(s["start"], s["end"])]
    return merge_ranges(ranges, cfg.get("merge_gap_s", 0.6))


def transcript_hits(segments: list[dict], language: str | None, cfg: dict | None = None) -> list[PolicyIssue]:
    """Từ tục + nhắc nền tảng khác trong lời thoại → đoạn cần cắt."""
    cfg = load_cfg() if cfg is None else cfg
    out = [PolicyIssue(start=a, end=max(b, a + 0.05), category="profanity", auto=True,
                       reason_vi="từ tục trong lời thoại (máy tự dò)")
           for a, b in _word_hits(segments, language, cfg, find_bad_words)]
    out += [PolicyIssue(start=a, end=max(b, a + 0.05), category="other_platform", auto=True,
                        reason_vi="nhắc tới nền tảng khác ngoài TikTok (máy tự dò)")
            for a, b in _word_hits(segments, language, cfg, find_platforms, cfg.get("platform_sentence_s", 6.0))]
    return sorted(out, key=lambda p: p.start)


def add_auto_issues(u, segments: list[dict], cfg: dict | None = None):
    """Gộp từ tục máy tự dò vào policy_issues (bỏ những chỗ đạo diễn đã đánh dấu)."""
    cfg = load_cfg() if cfg is None else cfg
    if not cfg.get("enabled", True):
        return u
    have = [(p.start, p.end) for p in u.policy_issues]
    new = [h for h in transcript_hits(segments, u.language, cfg)
           if not any(s <= h.start and h.end <= e for s, e in have)]
    return u.model_copy(update={"policy_issues": list(u.policy_issues) + new}) if new else u


def policy_key(p) -> str:
    """Khóa nhận diện một đoạn vi phạm (để người dùng chọn GIỮ LẠI đoạn đó)."""
    get = p.get if isinstance(p, dict) else lambda k, d=None: getattr(p, k, d)
    return f"{float(get('start')):.2f}-{float(get('end')):.2f}-{get('category')}"


def cut_ranges(u, cfg: dict | None = None) -> list[tuple[float, float]]:
    """Các đoạn phải cắt (đã nới rộng + gộp)."""
    cfg = load_cfg() if cfg is None else cfg
    if not cfg.get("enabled", True):
        return []
    pad = cfg.get("pad_s", 0.15)
    return merge_ranges([(max(0.0, p.start - pad), p.end + pad) for p in getattr(u, "policy_issues", [])],
                        cfg.get("merge_gap_s", 0.6))


def overlap_s(start: float, end: float, ranges: list[tuple[float, float]]) -> float:
    return sum(max(0.0, min(end, e) - max(start, s)) for s, e in ranges)


def policy_for_prompt(u, start: float = 0.0, end: float = 1e9) -> str:
    rows = [p for p in getattr(u, "policy_issues", []) if p.end > start and p.start < end]
    return "\n".join(f"- {p.start:.1f}–{p.end:.1f}s: {POLICY_VI.get(p.category, p.category)} — {p.reason_vi}"
                     for p in rows) or "(không có)"


def repair_policy(plan, ranges: list[tuple[float, float]], min_piece: float = 0.5):
    """Tách/cắt mọi clip chạm vào đoạn vi phạm. Trả (plan mới, danh sách sửa)."""
    if not ranges:
        return plan, []
    fixes: list[str] = []
    clips = []
    last_piece: dict[int, int] = {}  # clip cũ i → vị trí mẩu cuối cùng của nó trong danh sách mới
    for i, c in enumerate(plan.clips):
        if overlap_s(c.source_start, c.source_end, ranges) <= 0.02:
            clips.append(c)
            last_piece[i] = len(clips) - 1
            continue
        pieces, t = [], c.source_start
        for s, e in ranges:
            if e <= t or s >= c.source_end:
                continue
            if s - t >= min_piece:
                pieces.append((t, s))
            t = max(t, e)
        if c.source_end - t >= min_piece:
            pieces.append((t, c.source_end))
        fixes.append(f"clip {c.source_start}-{c.source_end} chứa đoạn vi phạm chính sách TikTok → "
                     + (f"giữ {', '.join(f'{a:.2f}-{b:.2f}' for a, b in pieces)}" if pieces else "bỏ cả clip"))
        clips += [c.model_copy(update={"source_start": round(a, 3), "source_end": round(b, 3)}) for a, b in pieces]
        if pieces:
            last_piece[i] = len(clips) - 1
    if not fixes:
        return plan, []
    # chuyển cảnh đánh số theo clip: dời theo vị trí mới; clip bị bỏ hẳn thì bỏ chuyển cảnh của nó
    trans = [t.model_copy(update={"after_clip": last_piece[t.after_clip]}) for t in plan.transitions
             if t.after_clip in last_piece and last_piece[t.after_clip] < len(clips) - 1]
    return plan.model_copy(update={"clips": clips, "transitions": trans}), fixes


def onscreen_texts(plan) -> list[str]:
    return [plan.title_top, plan.topic_label, *plan.titles_top, *plan.titles_bottom,
            *[e.text for e in plan.emphasis]]


def check_policy(plan, ranges: list[tuple[float, float]], language: str | None, cfg: dict | None = None) -> list[str]:
    errors = []
    if not plan.clips:
        errors.append("không còn clip nào sau khi cắt đoạn vi phạm chính sách TikTok — chọn đoạn footage khác")
    for c in plan.clips:
        if overlap_s(c.source_start, c.source_end, ranges) > 0.05:
            errors.append(f"clip {c.source_start}-{c.source_end} chứa đoạn vi phạm chính sách TikTok — phải bỏ đoạn đó")
    for t in onscreen_texts(plan):
        bad = find_forbidden(t, language, cfg)
        if bad:
            errors.append(f"chữ trên màn hình '{t}' có từ không được phép trên TikTok ({', '.join(bad)}) — viết lại")
    return errors
