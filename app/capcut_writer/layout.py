"""Tính bố cục khung dọc 9:16: khối 4:3 / 1:1 cho footage ngang, dải chữ trên/dưới."""

from __future__ import annotations

from .writer import Crop

CANVAS_W, CANVAS_H = 1080, 1920
RATIOS = {"4:3": 4 / 3, "1:1": 1.0, "9:16": 9 / 16}


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


def band_centers(ratio: str, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H) -> tuple[float, float]:
    """Tâm dải trên và dải dưới (đơn vị nửa khung, y hướng lên) khi khối nằm giữa màn hình."""
    _, block_h = block_size(ratio, canvas_w)
    edge = block_h / canvas_h  # mép khối, tính theo nửa khung
    top = (edge + 1.0) / 2
    return top, -top
