"""Tính bố cục khung dọc 9:16: khối 16:9 / 4:3 / 1:1 cho footage, dải chữ trên/dưới."""

from __future__ import annotations

from .writer import Crop

CANVAS_W, CANVAS_H = 1080, 1920
RATIOS = {"16:9": 16 / 9, "4:3": 4 / 3, "9:10": 0.9, "4:5": 0.8, "3:4": 3 / 4, "1:1": 1.0, "9:16": 9 / 16}


def nearest_ratio(width: int, height: int) -> str:
    """Tỉ lệ khung có sẵn gần nhất với video (chế độ chỉ thay tiếng: giữ nguyên khung gốc, cắt gần như 0)."""
    import math

    aspect = width / height
    return min(RATIOS, key=lambda k: abs(math.log(RATIOS[k] / aspect)))


def block_size(ratio: str, canvas_w: int = CANVAS_W) -> tuple[int, int]:
    """Kích thước khối (px) khi khối rộng bằng khung: 4:3 → 1080×810, 1:1 → 1080×1080."""
    r = RATIOS[ratio]
    return canvas_w, round(canvas_w / r)


def block_crop(src_w: int, src_h: int, ratio: str, center_x: float = 0.5, center_y: float = 0.5) -> Crop:
    """Vùng cắt trên khung gốc để ra đúng tỉ lệ khối, bám quanh tâm (center_x, center_y) 0..1.

    Ví dụ footage 16:9 → khối 4:3: giữ nguyên chiều cao, lấy 75% chiều rộng.
    """
    target = RATIOS[ratio]
    src = src_w / src_h
    if src > target:  # nguồn rộng hơn → cắt hai bên
        w = target / src
        left = min(max(center_x - w / 2, 0.0), 1.0 - w)
        return Crop(left=left, top=0.0, right=left + w, bottom=1.0)
    h = src / target  # nguồn cao hơn → cắt trên dưới
    top = min(max(center_y - h / 2, 0.0), 1.0 - h)
    return Crop(left=0.0, top=top, right=1.0, bottom=top + h)


def sub_crop(crop, ratio: str, src_w: int, src_h: int, center_x: float | None = None):
    """Vùng lớn nhất có tỉ lệ `ratio` (rộng/cao trên MÀN) nằm trong vùng cắt `crop`, tâm ngang theo center_x.
    Dùng để lấy khung 3:4 cố định từ vùng crop người dùng chọn (4:3 / 1:1 / 16:9)."""
    from .writer import Crop

    c = crop or Crop()
    w, h = c.right - c.left, c.bottom - c.top
    target = RATIOS[ratio] * src_h / src_w  # tỉ lệ rộng/cao theo tọa độ 0..1 của khung gốc
    if w / h > target:  # vùng crop rộng hơn → cắt thêm hai bên
        nw = h * target
        cx = c.left + w / 2 if center_x is None else center_x
        left = min(max(cx - nw / 2, c.left), c.right - nw)
        return Crop(left=left, top=c.top, right=left + nw, bottom=c.bottom)
    nh = w / target
    top = c.top + (h - nh) / 2
    return Crop(left=c.left, top=top, right=c.right, bottom=top + nh)


def band_centers(ratio: str, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H) -> tuple[float, float]:
    """Tâm dải trên và dải dưới (đơn vị nửa khung, y hướng lên) khi khối nằm giữa màn hình."""
    _, block_h = block_size(ratio, canvas_w)
    edge = block_h / canvas_h  # mép khối, tính theo nửa khung
    top = (edge + 1.0) / 2
    return top, -top


def row_to_y(row: float) -> float:
    """Vị trí theo phần chiều cao từ trên xuống (0..1) → y của CapCut (nửa khung, hướng lên)."""
    return 1.0 - 2.0 * row


def text_units(text: str) -> float:
    """Độ rộng tương đối của chuỗi: ký tự CJK/toàn khoảng = 1, ký tự Latin/số/nửa khoảng ≈ 0.55."""
    import unicodedata

    return sum(1.0 if unicodedata.east_asian_width(ch) in ("W", "F") else 0.55 for ch in text if ch != "\n")


def fit_scale(text: str, size: float, width: float, char_width_per_size: float, max_scale: float = 2.2) -> float:
    """Scale để một dòng chữ cỡ `size` rộng khoảng `width` (phần chiều ngang khung)."""
    natural = text_units(text) * size * char_width_per_size
    if natural <= 0:
        return 1.0
    return max(0.3, min(max_scale, width / natural))
