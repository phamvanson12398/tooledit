"""Phụ đề thoại từ transcript theo từ: cắt thành cụm ngắn theo giới hạn ký tự của từng ngôn ngữ.

- Tiếng Nhật không có dấu cách: nối token liền nhau, ngắt ở dấu câu 。、？！ hoặc khi đủ số ký tự.
- Tiếng Hàn, tiếng Anh: giữ dấu cách giữa các từ.
- Chỉ giữ từ nằm trong clip được dựng; thời gian đổi sang timeline qua TimeMap.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.planner.timeline import SEC, TimeMap

BREAK_AFTER = set("。、？！?!,.…")


@dataclass
class Cue:
    start: int  # µs trên timeline
    end: int
    text: str


def _join(tokens: list[str], lang: str) -> str:
    if lang == "ja":
        return "".join(t.strip() for t in tokens)
    return "".join(tokens).strip()


def build_cues(segments: list[dict], tmap: TimeMap, lang: str, max_chars: int, *,
               min_cue_s: float = 0.35, gap_merge_s: float = 0.15, corrections=()) -> list[Cue]:
    words = []
    for seg in segments:
        seg_words = seg.get("words") or [{"start": seg["start"], "end": seg["end"], "word": seg["text"]}]
        for w in seg_words:
            clip = tmap.clip_containing((w["start"] + w["end"]) / 2)
            if clip is None:  # từ nằm trong đoạn bị cắt bỏ
                continue
            start = tmap.to_out(min(max(w["start"], clip.source_start), clip.source_end))
            end = tmap.to_out(min(max(w["end"], clip.source_start), clip.source_end))
            words.append((start, end, w["word"]))

    cues: list[Cue] = []
    buf: list[tuple[int, int, str]] = []

    def flush():
        if buf:
            text = _join([w[2] for w in buf], lang)
            for c in corrections:
                if c.wrong:
                    text = text.replace(c.wrong, c.right)
            if text:
                cues.append(Cue(buf[0][0], buf[-1][1], text))
            buf.clear()

    for w in words:
        if buf:
            gap = w[0] - buf[-1][1]
            if len(_join([x[2] for x in buf] + [w[2]], lang)) > max_chars or gap > 0.6 * SEC:
                flush()
        buf.append(w)
        if w[2].strip() and w[2].strip()[-1] in BREAK_AFTER:
            flush()
    flush()

    # nối các cụm quá sát nhau, kéo dài cụm quá ngắn
    min_us, merge_us = round(min_cue_s * SEC), round(gap_merge_s * SEC)
    for i, c in enumerate(cues):
        nxt = cues[i + 1].start if i + 1 < len(cues) else None
        if nxt is not None and nxt - c.end <= merge_us:
            c.end = nxt
        if c.end - c.start < min_us:
            c.end = min(c.start + min_us, nxt) if nxt is not None else c.start + min_us
    return [c for c in cues if c.end > c.start]


def speech_intervals(cues: list[Cue], pad_us: int = 150_000) -> list[tuple[int, int]]:
    """Các khoảng có thoại (để hạ nhạc), đã gộp khoảng chồng/sát nhau."""
    out: list[list[int]] = []
    for c in cues:
        s, e = c.start - pad_us, c.end + pad_us
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([max(0, s), e])
    return [(s, e) for s, e in out]
