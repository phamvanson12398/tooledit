"""Review phim: HÌNH CHẠY THEO GIỌNG (chủ dự án yêu cầu 09/10).

Chế độ thuyết minh thường cho mỗi câu một "chỗ trống" cố định trên video rồi bắt voice khớp vào. Với review thì ngược
lại: chủ dự án đọc LIỀN MẠCH theo nhịp của mình (vd câu 22 chữ đọc mất 2 giây, không phải 4.5 giây), nên tool đo độ dài
voice THẬT của từng câu rồi co / giãn các cảnh minh họa câu đó cho vừa khít:

- câu i được đặt ngay sau câu i-1 (cách `gap_s` để lấy hơi) → giọng chạy liền từ đầu tới cuối, không khoảng im;
- các cảnh nằm trong [source_start, source_end] của câu được giữ nguyên SỐ LẦN CẮT (nhịp chuyển cảnh nhanh), mỗi cảnh
  co lại (voice ngắn hơn) hoặc kéo dài thêm phần phim liền sau (voice dài hơn) theo cùng tỉ lệ;
- cảnh nào co còn dưới `min_clip_s` thì bỏ bớt (câu quá ngắn so với số cảnh), cảnh kéo dài không lấn sang cảnh sau;
  phim không còn chỗ để kéo thì quay chậm nhẹ (tới `min_speed`), vẫn thiếu thì để voice tự tăng tốc như thường.

Câu chưa có file voice: giữ nguyên độ dài cũ (để dựng thử trước khi thu).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Piece:
    a: float
    b: float
    speed: float
    parent: int  # chỉ số clip gốc trong kế hoạch

    @property
    def out(self) -> float:
        return (self.b - self.a) / self.speed


def _pieces_for(line, clips) -> list[_Piece]:
    out = []
    for k, c in enumerate(clips):
        a, b = max(c.source_start, line.source_start), min(c.source_end, line.source_end)
        if b - a > 0.05:
            out.append(_Piece(a, b, c.speed, k))
    return out


def fit_to_voice(plan, script, voice_s: dict[int, float], footage_s: float, *, gap_s: float = 0.12,
                 min_clip_s: float = 0.4, min_speed: float = 0.8):
    """Trả (plan mới, script mới, ghi chú). voice_s: {số câu (1-based): độ dài voice giây}."""
    clips = [c for c in plan.clips if not c.replay and not c.repeat]
    starts = sorted(c.source_start for c in clips)
    new_clips, new_lines, notes = [], [], []
    shrunk = grown = dropped = 0
    for i, ln in enumerate(script.lines, 1):
        pieces = _pieces_for(ln, clips)
        if not pieces:
            notes.append(f"câu {i} không nằm trên cảnh nào được giữ — bỏ qua")
            continue
        have = sum(p.out for p in pieces)
        want = (voice_s[i] + gap_s) if voice_s.get(i) else have
        if want < have - 0.05:  # voice ngắn hơn → co cảnh, bỏ bớt cảnh quá ngắn
            shrunk += 1
            while len(pieces) > 1 and want / len(pieces) < min_clip_s:
                pieces.remove(min(pieces, key=lambda p: p.out))
                dropped += 1
            f = want / sum(p.out for p in pieces)
            for p in pieces:
                p.b = p.a + p.out * f * p.speed
        elif want > have + 0.05:  # voice dài hơn → kéo dài từng cảnh bằng phần phim liền sau
            grown += 1
            f = want / have
            for p in pieces:
                limit = min([s for s in starts if s > p.a + 1e-6] + [footage_s])
                p.b = min(p.a + p.out * f * p.speed, max(p.b, limit))
            short = want - sum(p.out for p in pieces)
            if short > 0.05:  # hết phim để kéo → quay chậm nhẹ
                total = sum(p.b - p.a for p in pieces)
                speed = max(min_speed, total / want) if want > 0 else 1.0
                for p in pieces:
                    p.speed = min(p.speed, round(speed, 3))
        for p in pieces:
            src = clips[p.parent]
            new_clips.append(src.model_copy(update={"source_start": round(p.a, 3), "source_end": round(p.b, 3),
                                                    "speed": p.speed}))
        new_lines.append(ln.model_copy(update={"source_start": round(pieces[0].a, 3),
                                               "source_end": round(pieces[-1].b, 3)}))
    if not new_clips:
        return plan, script, notes

    def inside(t: float) -> bool:
        return any(c.source_start - 1e-6 <= t <= c.source_end + 1e-6 for c in new_clips)

    upd = {"clips": new_clips, "transitions": []}  # chuyển cảnh theo chỉ số clip cũ không còn đúng → bỏ
    for field, attr in (("zooms", "source_start"), ("emphasis", "source_time"), ("sfx", "source_time"),
                        ("effects", "source_time"), ("stickers", "source_time"), ("arrows", "source_time")):
        items = getattr(plan, field, None)
        if items:
            upd[field] = [x for x in items if inside(getattr(x, attr))]
    if shrunk or grown:
        notes.insert(0, f"Hình chạy theo giọng: {shrunk} câu co cảnh, {grown} câu kéo dài cảnh"
                        + (f", bỏ {dropped} cảnh quá ngắn" if dropped else "") + " để khớp đúng độ dài voice đã thu.")
    return plan.model_copy(update=upd), script.model_copy(update={"lines": new_lines}), notes
