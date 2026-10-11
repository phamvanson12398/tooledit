"""Lồng tiếng nhân vật (chủ dự án báo 11/10: "có đoạn không khớp", "nhân vật đang nói mà không có tiếng"):
mốc thời gian của từng câu lồng tiếng lấy THẲNG từ câu thoại gốc (Whisper), không để AI tự chọn — mỗi câu gốc trong
các tình huống được giữ thành đúng MỘT câu lồng tiếng, nên voice đặt đúng lúc nhân vật mở miệng và không sót câu nào.
Câu gốc quá dài được tách ở chỗ ngắt (dấu câu / khoảng lặng giữa các từ) cho giọng lồng bám miệng sát hơn."""

from __future__ import annotations

PUNCT = tuple("。！？!?.,、，…")


def _split_words(words: list[dict], max_s: float) -> list[tuple[float, float, str]]:
    """Tách một câu dài theo từ: cắt ở chỗ ngắt tốt nhất (dấu câu, khoảng lặng lớn) cho tới khi mỗi phần ≤ max_s."""
    if not words:
        return []
    if words[-1]["end"] - words[0]["start"] <= max_s or len(words) < 2:
        return [(words[0]["start"], words[-1]["end"], "".join(w.get("word", "") for w in words).strip())]
    best, score = None, -1.0
    t0, t1 = words[0]["start"], words[-1]["end"]
    for k in range(1, len(words)):
        gap = words[k]["start"] - words[k - 1]["end"]
        punct = words[k - 1].get("word", "").strip().endswith(PUNCT)
        balance = 1.0 - abs((words[k]["start"] - t0) - (t1 - words[k]["start"])) / max(t1 - t0, 1e-6)
        s = gap + (0.6 if punct else 0.0) + 0.3 * balance
        if s > score:
            best, score = k, s
    return _split_words(words[:best], max_s) + _split_words(words[best:], max_s)


def source_lines(segments: list[dict], clips: list, *, max_s: float = 7.0, min_s: float = 0.25) -> list[dict]:
    """Câu thoại gốc nằm trong các clip được giữ, theo thứ tự: [{start, end, text}] (giây gốc).
    Câu vắt qua mép clip được cắt theo clip (phần ngoài clip không có trên video)."""
    out: list[dict] = []
    for c in clips:
        if getattr(c, "replay", False) or getattr(c, "repeat", False):
            continue
        a, b = c.source_start, c.source_end
        for sg in segments:
            if sg["end"] <= a or sg["start"] >= b or not (sg.get("text") or "").strip():
                continue
            words = [w for w in sg.get("words") or [] if w["end"] > a and w["start"] < b]
            pieces = _split_words(words, max_s) if words else [(sg["start"], sg["end"], sg["text"].strip())]
            for s, e, text in pieces:
                s, e = max(s, a), min(e, b)
                if e - s >= min_s and text:
                    out.append({"start": round(s, 2), "end": round(e, 2), "text": text})
    out.sort(key=lambda x: x["start"])
    fixed: list[dict] = []
    for ln in out:  # Whisper đôi khi cho 2 câu chồng nhau vài phần giây → lùi đầu câu sau
        if fixed and ln["start"] < fixed[-1]["end"]:
            ln = {**ln, "start": fixed[-1]["end"]}
            if ln["end"] - ln["start"] < min_s:
                fixed[-1] = {**fixed[-1], "end": max(fixed[-1]["end"], ln["end"]),
                             "text": f"{fixed[-1]['text']} {ln['text']}".strip()}
                continue
        fixed.append(ln)
    return fixed
