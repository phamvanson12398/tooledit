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


def detect_faces(image, min_face_frac: float = 0.06) -> list[Box]:
    """image: ảnh BGR (numpy) như cv2.imread. Dùng Haar cascade kèm sẵn trong OpenCV 4.x."""
    import cv2

    cascade = _cascade()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    min_side = max(12, int(h * min_face_frac))
    rects = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(min_side, min_side))
    return [Box(x=x / w, y=y / h, w=bw / w, h=bh / h) for (x, y, bw, bh) in rects]


_CASCADE = None


def _cascade():
    global _CASCADE
    if _CASCADE is None:
        import cv2

        _CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return _CASCADE


def scan_video(video: Path, every_s: float = 0.5, min_face_frac: float = 0.06) -> list[FrameSubjects]:
    import cv2

    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, int(round(fps * every_s)))
    out = []
    for idx in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            break
        out.append(FrameSubjects(t=idx / fps, faces=detect_faces(frame, min_face_frac)))
    cap.release()
    return out


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
