"""Chữ in sẵn trên footage sau khi cắt khung: tránh bằng cách cắt chặt hơn, không được thì che bằng dải nền tối.

- avoid_text: tìm khung cắt nhỏ hơn (cùng tỉ lệ, càng to càng tốt) nằm trong khung cũ mà không dính hộp chữ — phía
  trên / dưới / trái / phải hộp chữ. Chấp nhận nếu còn ≥ min_scale chiều rộng khung cũ (mất ít hình).
- cover_rect: hộp chữ còn lại → vị trí trên khung 9:16 để đặt dải che.
"""

from __future__ import annotations

from app.capcut_writer import Crop

Box = tuple[float, float, float, float]


def _overlap(c: Crop, b: Box) -> bool:
    return b[0] < c.right and b[2] > c.left and b[1] < c.bottom and b[3] > c.top


def _fit(c: Crop, x0: float, y0: float, x1: float, y1: float) -> Crop | None:
    """Khung lớn nhất cùng tỉ lệ với c nằm trong vùng (x0..x1, y0..y1), tâm gần tâm c nhất."""
    w0, h0 = c.right - c.left, c.bottom - c.top
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        return None
    s = min((x1 - x0) / w0, (y1 - y0) / h0, 1.0)
    w, h = w0 * s, h0 * s
    cx = min(max((c.left + c.right) / 2, x0 + w / 2), x1 - w / 2)
    cy = min(max((c.top + c.bottom) / 2, y0 + h / 2), y1 - h / 2)
    return Crop(left=cx - w / 2, top=cy - h / 2, right=cx + w / 2, bottom=cy + h / 2)


def avoid_text(crop: Crop | None, boxes: list[Box], min_scale: float = 0.8) -> tuple[Crop | None, list[Box]]:
    """Trả (khung cắt mới, các hộp chữ VẪN còn trong khung → cần che)."""
    c = crop or Crop()
    hits = [b for b in boxes if _overlap(c, b)]
    if not hits:
        return crop, []
    # vùng không dính chữ: phía trên hộp thấp nhất / dưới hộp cao nhất…, rồi chọn khung lớn nhất
    top_edge = min(b[1] for b in hits)
    bottom_edge = max(b[3] for b in hits)
    left_edge = min(b[0] for b in hits)
    right_edge = max(b[2] for b in hits)
    cands = [_fit(c, c.left, c.top, c.right, top_edge), _fit(c, c.left, bottom_edge, c.right, c.bottom),
             _fit(c, c.left, c.top, left_edge, c.bottom), _fit(c, right_edge, c.top, c.right, c.bottom)]
    cands = [x for x in cands if x is not None and not any(_overlap(x, b) for b in hits)]
    if cands:
        best = max(cands, key=lambda x: x.right - x.left)
        if (best.right - best.left) >= min_scale * (c.right - c.left) - 1e-9:
            return best, []
    return crop, hits


def cover_rect(box: Box, crop: Crop | None, ratio: str, mirrored: bool = False, pad: float = 0.25,
               canvas_w: int = 1080, canvas_h: int = 1920) -> tuple[float, float, float, float] | None:
    """Hộp chữ (khung gốc) → (tâm x, tâm y, nửa rộng, nửa cao) theo đơn vị nửa khung CapCut. None nếu ngoài khung."""
    from app.capcut_writer.layout import block_size

    c = crop or Crop()
    l, t, r, b = max(box[0], c.left), max(box[1], c.top), min(box[2], c.right), min(box[3], c.bottom)
    if r <= l or b <= t:
        return None
    w, h = c.right - c.left, c.bottom - c.top
    u0, u1 = (l - c.left) / w, (r - c.left) / w
    if mirrored:
        u0, u1 = 1 - u1, 1 - u0
    v0, v1 = (t - c.top) / h, (b - c.top) / h
    bw, bh = block_size(ratio, canvas_w)
    # nửa rộng / nửa cao theo đơn vị nửa khung (1 = nửa chiều rộng / nửa chiều cao khung 9:16), nới thêm `pad`
    hx = min((u1 - u0) * (1 + pad) * bw / canvas_w, bw / canvas_w)
    hy = (v1 - v0) * (1 + 2 * pad) * bh / canvas_h
    cx = ((u0 + u1) / 2 - 0.5) * 2 * bw / canvas_w
    cy = -((v0 + v1) / 2 - 0.5) * 2 * bh / canvas_h
    return cx, cy, hx, hy


def cover_glyphs(hx: float, hy: float, size: float, char_width_per_size: float,
                 canvas_w: int = 1080, canvas_h: int = 1920) -> tuple[str, float]:
    """Dải che dựng bằng chữ: một hàng ký tự khối "■" cùng màu nền + nền chữ cùng màu → (chuỗi, scale).
    Chiều rộng ký tự ước lượng theo char_width_per_size như dòng tiêu đề. [CẦN KIỂM TRA TRÊN MÁY]"""
    width_px, height_px = hx * canvas_w, hy * canvas_h  # toàn bộ chiều rộng / cao của dải (px)
    n = max(1, round(width_px / max(height_px, 1.0)))
    scale = (width_px / canvas_w) / (n * size * char_width_per_size)
    return "■" * n, round(scale, 3)
