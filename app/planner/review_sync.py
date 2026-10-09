"""Review phim — DỰNG TỪ VOICE (chủ dự án chốt 09/10).

Quy trình: tool viết TRƯỚC một bài lời đọc kể chuyện liền mạch (mỗi câu ghi đoạn phim nó kể) → chủ dự án đọc CẢ BÀI vào
một file voice → tool tự cắt ra từng câu, đo độ dài thật, rồi cắt cảnh trong đoạn phim của từng câu sao cho tổng đúng
bằng câu đọc. Giọng chạy liền từ đầu tới cuối, video dài đúng bằng tổng giọng, đọc nhanh hay chậm đều khớp.
"""

from __future__ import annotations


def _keep_decor(plan, new_clips) -> dict:
    """Zoom / chữ nhấn / SFX / hiệu ứng / sticker / mũi tên chỉ giữ cái nằm trên cảnh còn dùng."""
    def inside(t: float) -> bool:
        return any(c.source_start - 1e-6 <= t <= c.source_end + 1e-6 for c in new_clips)

    upd = {"clips": new_clips, "transitions": []}
    for field, attr in (("zooms", "source_start"), ("emphasis", "source_time"), ("sfx", "source_time"),
                        ("effects", "source_time"), ("stickers", "source_time"), ("arrows", "source_time")):
        items = getattr(plan, field, None)
        if items:
            upd[field] = [x for x in items if inside(getattr(x, attr))]
    return upd


def build_from_voice(plan, script, voice_s: dict[int, float], scene_starts: list[float], *, cps: float,
                     gap_s: float = 0.12, cut_s: float = 2.0, min_cut_s: float = 1.0, min_speed: float = 0.8):
    """REVIEW — DỰNG TỪ VOICE (chủ dự án chốt 09/10): bài lời đọc viết trước, mỗi câu ghi đoạn phim nó kể; chủ dự án đọc
    cả bài → tool cắt cảnh từ đoạn phim của từng câu sao cho tổng đúng bằng độ dài câu đọc (+ `gap_s`):
    chia đoạn phim thành n khúc đều nhau (n ≈ độ dài câu / `cut_s`), mỗi khúc lấy 1 cảnh ở giữa (bám điểm đổi cảnh gần
    nhất nếu có) → cảnh chuyển nhanh, rải đều suốt đoạn phim mà câu kể. Đoạn phim ngắn hơn câu thì quay chậm nhẹ.
    Câu chưa có voice: ước lượng theo số chữ / `cps` (để dựng thử trước khi thu).
    Trả (plan mới — clip do tool tạo, giữ tiêu đề / nhạc / filter của kế hoạch AI —, script mới, ghi chú)."""
    from app.director.tasks import speech_chars

    base = plan.clips[0]
    clips, lines, notes, est_n = [], [], [], 0
    prev_end = 0.0
    for i, ln in enumerate(script.lines, 1):
        a, b = max(ln.source_start, prev_end), ln.source_end
        if b - a < 0.3:
            notes.append(f"câu {i}: đoạn phim {ln.source_start}-{ln.source_end}s trùng câu trước — bỏ qua")
            continue
        v = voice_s.get(i)
        if not v:
            v = max(1.0, speech_chars(ln.text) / max(cps, 1e-6))
            est_n += 1
        want = v + gap_s
        n = max(1, min(round(want / cut_s), int((b - a) / min_cut_s) or 1))
        seg, w = want / n, (b - a) / n
        pieces = []
        for k in range(n):
            sa, se = a + k * w, a + (k + 1) * w
            if w >= seg:  # đủ phim: lấy khúc ở giữa, bám điểm đổi cảnh gần nhất nếu nằm trong khoảng cho phép
                start = sa + (w - seg) / 2
                near = [s for s in scene_starts if sa <= s <= se - seg]
                if near:
                    start = min(near, key=lambda s: abs(s - start))
                pieces.append((start, start + seg, 1.0))
            else:  # thiếu phim: lấy cả khúc, quay chậm nhẹ
                pieces.append((sa, se, round(max(min_speed, w / seg), 3)))
        for pa, pb, sp in pieces:
            clips.append(base.model_copy(update={"source_start": round(pa, 3), "source_end": round(pb, 3), "speed": sp,
                                                 "ratio": None, "replay": False, "repeat": False}))
        lines.append(ln.model_copy(update={"source_start": round(pieces[0][0], 3),
                                           "source_end": round(pieces[-1][1], 3)}))
        prev_end = b
    if not clips:
        return plan, script, notes
    total = sum((c.source_end - c.source_start) / c.speed for c in clips)
    notes.insert(0, f"Dựng từ voice: {len(lines)} câu → {len(clips)} cảnh, dài {total:.1f}s"
                    + (f" ({est_n} câu chưa có voice — tạm tính theo số chữ, thu xong dựng lại)" if est_n else "") + ".")
    return (plan.model_copy(update=_keep_decor(plan, clips)), script.model_copy(update={"lines": lines}), notes)
