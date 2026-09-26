"""Dò khuôn mặt/chủ thể để crop thông minh, và làm mượt đường lia khung."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class Box(BaseModel):
    """Hộp chuẩn hóa 0..1 theo khung hình gốc."""

    x: float
    y: float
    w: float
    h: float
    motion: float = 0.0  # độ chuyển động vùng miệng (0..1) — cao = đang nói

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


class FrameSubjects(BaseModel):
    t: float
    faces: list[Box] = []


class SubjectTrack(BaseModel):
    """Tâm chủ thể chính theo thời gian (đã làm mượt), dùng để đặt crop và keyframe lia khung."""

    points: list[tuple[float, float, float]]  # (t, cx, cy)
    face_count_max: int = 0


def detect_faces(image, min_face_frac: float = 0.06, profiles: bool = True) -> list[Box]:
    """image: ảnh BGR (numpy) như cv2.imread. Dùng Haar cascade kèm sẵn trong OpenCV 4.x.
    Ngoài mặt nhìn thẳng còn dò mặt nghiêng (hai phía) — trong podcast người nói hay quay sang nhau."""
    import cv2

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    min_side = max(12, int(h * min_face_frac))
    kw = {"scaleFactor": 1.1, "minNeighbors": 5, "minSize": (min_side, min_side)}
    boxes = [Box(x=x / w, y=y / h, w=bw / w, h=bh / h) for (x, y, bw, bh) in _cascade("frontalface_default")
             .detectMultiScale(gray, **kw)]
    if profiles:
        prof = _cascade("profileface")
        boxes += [Box(x=x / w, y=y / h, w=bw / w, h=bh / h) for (x, y, bw, bh) in prof.detectMultiScale(gray, **kw)]
        flipped = cv2.flip(gray, 1)  # cascade chỉ dò mặt quay một phía → lật ảnh để dò phía còn lại
        boxes += [Box(x=1 - (x + bw) / w, y=y / h, w=bw / w, h=bh / h)
                  for (x, y, bw, bh) in prof.detectMultiScale(flipped, **kw)]
    return merge_boxes(boxes)


def merge_boxes(boxes: list[Box], iou_min: float = 0.3) -> list[Box]:
    """Bỏ hộp trùng (cùng một mặt bị dò bởi nhiều cascade), giữ hộp lớn hơn."""
    def iou(a: Box, b: Box) -> float:
        ix = max(0.0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
        iy = max(0.0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
        inter = ix * iy
        return inter / (a.w * a.h + b.w * b.h - inter) if inter else 0.0

    kept: list[Box] = []
    for b in sorted(boxes, key=lambda b: b.w * b.h, reverse=True):
        if all(iou(b, k) < iou_min for k in kept):
            kept.append(b)
    return kept


_CASCADES: dict = {}


def _cascade(name: str = "frontalface_default"):
    if name not in _CASCADES:
        import cv2

        _CASCADES[name] = cv2.CascadeClassifier(cv2.data.haarcascades + f"haarcascade_{name}.xml")
    return _CASCADES[name]


def mouth_motion(gray_a, gray_b, box: Box) -> float:
    """Chênh lệch trung bình (0..1) vùng miệng (1/3 dưới của mặt) giữa hai khung liền nhau."""
    h, w = gray_a.shape[:2]
    x0, x1 = int((box.x + 0.2 * box.w) * w), int((box.x + 0.8 * box.w) * w)
    y0, y1 = int((box.y + 0.62 * box.h) * h), int(min(1.0, box.y + 0.98 * box.h) * h)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return 0.0
    a = gray_a[y0:y1, x0:x1].astype("float32")
    b = gray_b[y0:y1, x0:x1].astype("float32")
    return float(abs(a - b).mean() / 255.0)


def scan_video(video: Path, every_s: float = 0.5, min_face_frac: float = 0.06,
               max_width: int = 640, motion_gap: int = 3) -> list[FrameSubjects]:
    """Đọc video tuần tự (grab bỏ qua khung không cần, nhanh hơn nhiều so với tua từng mốc)
    và thu nhỏ khung về tối đa max_width trước khi dò mặt. Tọa độ trả về vẫn chuẩn hóa 0..1.
    Mỗi mốc đọc thêm một khung cách `motion_gap` khung để đo miệng ai đang cử động (người đang nói)."""
    import cv2

    def small(frame):
        h, w = frame.shape[:2]
        if w > max_width:
            frame = cv2.resize(frame, (max_width, round(h * max_width / w)), interpolation=cv2.INTER_AREA)
        return frame

    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(motion_gap + 1, int(round(fps * every_s)))
    out = []
    idx = 0
    while True:
        if idx % step == 0:
            t = idx / fps
            ok, frame = cap.read()
            if not ok:
                break
            idx += 1
            frame = small(frame)
            faces = detect_faces(frame, min_face_frac)
            if faces:  # đọc thêm khung sau motion_gap khung để đo cử động miệng
                for _ in range(motion_gap - 1):
                    cap.grab()
                    idx += 1
                ok2, frame2 = cap.read()
                idx += 1
                if ok2:
                    ga = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gb = cv2.cvtColor(small(frame2), cv2.COLOR_BGR2GRAY)
                    faces = [f.model_copy(update={"motion": round(mouth_motion(ga, gb, f), 4)}) for f in faces]
            out.append(FrameSubjects(t=t, faces=faces))
            # nhảy tới mốc kế tiếp: bỏ qua các khung còn lại của bước này
            while idx % step != 0:
                if not cap.grab():
                    cap.release()
                    return out
                idx += 1
            continue
        if not cap.grab():
            break
        idx += 1
    cap.release()
    return out


def faces_compact(frames: list[FrameSubjects]) -> list:
    """[[t, [[x, y, w, h, motion], ...]], ...] — gọn để lưu vào subjects.json (dùng cho góc máy theo người nói)."""
    return [[round(f.t, 2), [[round(b.x, 3), round(b.y, 3), round(b.w, 3), round(b.h, 3), b.motion] for b in f.faces]]
            for f in frames if f.faces]


def main_subject_track(frames: list[FrameSubjects], smooth_window: int = 5,
                       max_pan_per_s: float = 0.25) -> SubjectTrack:
    """Chọn mặt lớn nhất mỗi mốc; mốc không có mặt thì giữ vị trí trước (mặc định giữa khung);
    làm mượt bằng trung bình trượt rồi giới hạn tốc độ lia để khung không giật."""
    raw: list[tuple[float, float, float]] = []
    last = (0.5, 0.5)
    for f in frames:
        if f.faces:
            big = max(f.faces, key=lambda b: b.w * b.h)
            last = (big.cx, big.cy)
        raw.append((f.t, *last))
    if not raw:
        return SubjectTrack(points=[])

    half = max(0, smooth_window // 2)
    smoothed = []
    for i, (t, _, _) in enumerate(raw):
        win = raw[max(0, i - half): i + half + 1]
        smoothed.append((t, sum(p[1] for p in win) / len(win), sum(p[2] for p in win) / len(win)))

    limited = [smoothed[0]]
    for t, cx, cy in smoothed[1:]:
        pt, px, py = limited[-1]
        max_d = max_pan_per_s * max(t - pt, 1e-6)
        limited.append((t, px + _clamp(cx - px, max_d), py + _clamp(cy - py, max_d)))
    return SubjectTrack(points=limited, face_count_max=max((len(f.faces) for f in frames), default=0))


def _clamp(v: float, limit: float) -> float:
    return max(-limit, min(limit, v))
