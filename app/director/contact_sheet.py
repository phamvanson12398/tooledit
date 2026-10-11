"""Ghép nhiều khung hình thành ẢNH LƯỚI trước khi gửi đạo diễn AI (chủ dự án 11/10: "chậm quá").

Claude Code / Antigravity xem ảnh bằng công cụ đọc file — MỖI ảnh là một lượt đọc, nên 80 khung hình = 80 lượt, rất lâu.
Ghép 9 khung / ảnh (lưới 3×3, mỗi ô có nhãn = tên file gốc, vd "00_00012.50.jpg") thì 80 khung chỉ còn 9 lượt đọc.
Đề bài vẫn nhắc khung hình theo tên file như cũ; AI tìm ô có nhãn trùng tên.
"""

from __future__ import annotations

from pathlib import Path

SHEET_NOTE = """

## Khung hình đã được GHÉP THÀNH ẢNH LƯỚI (để xem nhanh)
Các khung hình nêu trong đề bài được ghép {per} ô mỗi ảnh vào các file: {names}.
Mỗi ô có nhãn trắng trên nền đen = TÊN FILE khung hình gốc (vd "00_00012.50.jpg" = khung ở giây 12.50). Đề bài nhắc
"mở <tên file> bằng Read" thì mở ảnh lưới rồi xem ô có nhãn đúng tên đó. Xem HẾT các ảnh lưới.
"""


def make_sheets(images: list[Path], out_dir: Path, per_sheet: int = 9, cols: int = 3, tile_width: int = 360,
                quality: int = 85) -> list[Path]:
    """Trả danh sách ảnh lưới đã ghi vào out_dir (sheet_01.jpg…). Ảnh đọc lỗi thì bỏ qua ô đó."""
    import cv2
    import numpy as np

    tiles = []
    for p in images:
        img = cv2.imread(str(p))
        if img is None:
            continue
        h, w = img.shape[:2]
        th = max(1, round(h * tile_width / w))
        img = cv2.resize(img, (tile_width, th), interpolation=cv2.INTER_AREA)
        bar = np.zeros((26, tile_width, 3), dtype=np.uint8)
        cv2.putText(bar, Path(p).name, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(np.vstack([bar, img]))
    sheets = []
    for k in range(0, len(tiles), per_sheet):
        group = tiles[k:k + per_sheet]
        cell_h = max(t.shape[0] for t in group)
        n_cols = min(cols, len(group))
        rows = -(-len(group) // n_cols)
        canvas = np.full((rows * cell_h + (rows - 1) * 4, n_cols * tile_width + (n_cols - 1) * 4, 3), 40, dtype=np.uint8)
        for i, t in enumerate(group):
            r, c = divmod(i, n_cols)
            y, x = r * (cell_h + 4), c * (tile_width + 4)
            canvas[y:y + t.shape[0], x:x + tile_width] = t
        dst = out_dir / f"sheet_{len(sheets) + 1:02d}.jpg"
        cv2.imwrite(str(dst), canvas, [cv2.IMWRITE_JPEG_QUALITY, quality])
        sheets.append(dst)
    return sheets


def pack(images: list[Path], workdir: Path, cfg: dict | None) -> tuple[list[str], str]:
    """Chép ảnh vào thư mục làm việc của AI. Nhiều ảnh (≥ min_images) thì ghép lưới.
    Trả (tên các file AI cần xem, ghi chú thêm vào đề bài)."""
    import shutil

    cfg = cfg or {}
    if not images:
        return [], ""
    if not cfg.get("enabled", True) or len(images) < int(cfg.get("min_images", 6)):
        for img in images:
            shutil.copy2(img, workdir / Path(img).name)
        return [Path(i).name for i in images], ""
    per = int(cfg.get("per_sheet", 9))
    try:
        sheets = make_sheets(images, workdir, per, int(cfg.get("cols", 3)), int(cfg.get("tile_width", 360)))
    except Exception:  # thiếu OpenCV / ảnh lạ → gửi từng ảnh như cũ
        sheets = []
    if not sheets:
        for img in images:
            shutil.copy2(img, workdir / Path(img).name)
        return [Path(i).name for i in images], ""
    names = [s.name for s in sheets]
    return names, SHEET_NOTE.format(per=per, names=", ".join(names))
