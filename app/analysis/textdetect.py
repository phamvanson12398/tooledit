"""Tìm vùng CHỮ IN SẴN trên footage (phụ đề cứng, tiêu đề, logo chữ) từ các khung hình đã trích ở bước phân tích.

Cách làm (OpenCV, không cần mô hình AI): chữ = nhiều cạnh dọc dày đặc xếp thành dòng ngang. Mỗi khung → bản đồ
"giống chữ" (Sobel ngang + đóng hình thái học theo chiều ngang); cộng dồn qua nhiều khung → vùng có chữ ở lại lâu
(phụ đề luôn ở cùng một dải, logo đứng yên). Chỉ chạy khi bước hiểu nội dung báo footage CÓ chữ in sẵn, và chỉ giữ vùng
nằm trong các dải AI đã báo (top / bottom / center / các góc) để tránh nhầm cảnh nhiều họa tiết.
"""

from __future__ import annotations

import numpy as np

# dải trên khung gốc (x0, y0, x1, y1) theo tên vùng mà AI báo trong burned_in_text.regions
REGION_ZONES = {
    "top": (0.0, 0.0, 1.0, 0.35), "bottom": (0.0, 0.62, 1.0, 1.0), "center": (0.0, 0.3, 1.0, 0.7),
    "top_left": (0.0, 0.0, 0.5, 0.35), "top_right": (0.5, 0.0, 1.0, 0.35),
    "bottom_left": (0.0, 0.62, 0.5, 1.0), "bottom_right": (0.5, 0.62, 1.0, 1.0),
}


def text_map(gray: np.ndarray) -> np.ndarray:
    """Bản đồ 0/1 các điểm 'giống chữ' của một khung xám."""
    import cv2

    h, w = gray.shape[:2]
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    mag = np.abs(gx)
    thr = max(40.0, float(np.percentile(mag, 92)))
    edges = (mag > thr).astype(np.uint8)
    k = max(3, w // 40)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, max(1, h // 120))))
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, max(2, h // 60))))
    return opened


def detect_text_boxes(frames: list[np.ndarray], regions: list[str], min_share: float = 0.25,
                      pad: float = 0.015) -> list[tuple[float, float, float, float]]:
    """Trả các hộp (trái, trên, phải, dưới) 0..1 trên khung gốc có chữ xuất hiện ở ≥ min_share số khung."""
    import cv2

    zones = [REGION_ZONES[r] for r in regions if r in REGION_ZONES]
    if not frames or not zones:
        return []
    h, w = frames[0].shape[:2]
    heat = np.zeros((h, w), np.float32)
    used = 0
    for g in frames:
        if g.shape[:2] != (h, w):
            g = cv2.resize(g, (w, h))
        heat += text_map(g)
        used += 1
    heat /= max(1, used)
    mask = (heat >= min_share).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    boxes = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if bw < 0.04 * w or bh < 0.012 * h or area < 0.0015 * w * h:
            continue
        box = (x / w, y / h, (x + bw) / w, (y + bh) / h)
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        if not any(z[0] <= cx <= z[2] and z[1] <= cy <= z[3] for z in zones):
            continue
        boxes.append((max(0.0, box[0] - pad), max(0.0, box[1] - pad), min(1.0, box[2] + pad), min(1.0, box[3] + pad)))
    return merge_boxes(boxes)


def merge_boxes(boxes: list[tuple[float, float, float, float]], gap: float = 0.02):
    """Gộp các hộp chồng / sát nhau (các chữ của cùng một dòng phụ đề)."""
    out = [list(b) for b in sorted(boxes)]
    changed = True
    while changed:
        changed = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a, b = out[i], out[j]
                if a[0] - gap <= b[2] and b[0] - gap <= a[2] and a[1] - gap <= b[3] and b[1] - gap <= a[3]:
                    out[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    del out[j]
                    changed = True
                    break
            if changed:
                break
    return [tuple(round(v, 4) for v in b) for b in out]


def presence_times(timed: list[tuple[float, np.ndarray]], box, density: float = 0.08,
                   gap_s: float | None = None) -> list[list[float]]:
    """Những khoảng thời gian (giây gốc) chữ thực sự HIỆN trong hộp — để chỉ che lúc có chữ, không che suốt video.
    timed: [(giây, khung xám)] theo thứ tự thời gian."""
    if not timed:
        return []
    ts = [t for t, _ in timed]
    step = gap_s if gap_s is not None else (max(0.5, float(np.median(np.diff(ts)))) if len(ts) > 1 else 1.0)
    on = []
    for t, g in timed:
        h, w = g.shape[:2]
        x0, y0, x1, y1 = int(box[0] * w), int(box[1] * h), max(int(box[2] * w), int(box[0] * w) + 1), \
            max(int(box[3] * h), int(box[1] * h) + 1)
        on.append(float(text_map(g)[y0:y1, x0:x1].mean()) >= density)
    out: list[list[float]] = []
    for i, (t, flag) in enumerate(zip(ts, on)):
        if not flag:
            continue
        s, e = max(0.0, t - step / 2), t + step / 2
        if out and s <= out[-1][1] + 1e-6:
            out[-1][1] = e
        else:
            out.append([round(s, 2), round(e, 2)])
    return [[round(a, 2), round(b, 2)] for a, b in out]


def _load(paths: list, size: int) -> list[np.ndarray]:
    import cv2

    frames = []
    for p in paths:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            frames.append(None)
            continue
        s = size / max(img.shape[:2])
        frames.append(cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s))) if s < 1 else img)
    return frames


def boxes_from_files(paths: list, regions: list[str], size: int = 480, times: list[float] | None = None,
                     sample: int = 40) -> list[dict]:
    """Dò hộp chữ (từ tối đa `sample` khung rải đều) + thời gian chữ hiện (từ mọi khung có mốc giây).
    Trả [{"box": [l, t, r, b], "times": [[giây đầu, giây cuối], ...] hoặc None = suốt video}]."""
    frames = _load(paths, size)
    valid = [(i, f) for i, f in enumerate(frames) if f is not None]
    if not valid:
        return []
    step = max(1, len(valid) // sample)
    boxes = detect_text_boxes([f for _, f in valid[::step]], regions)
    if times is None:
        return [{"box": list(b), "times": None} for b in boxes]
    timed = [(times[i], f) for i, f in valid]
    return [{"box": list(b), "times": presence_times(timed, b)} for b in boxes]
