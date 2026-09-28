"""Dò cảnh (PySceneDetect) và chọn mốc trích khung hình."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class Scene(BaseModel):
    index: int
    start: float
    end: float


def detect_scenes(video: Path, threshold: float = 27.0, min_scene_len_s: float = 0.6,
                  duration: float | None = None, *, frame_skip: int = 0,
                  progress=None, chunk_s: float = 60.0) -> list[Scene]:
    """Dò theo từng đoạn chunk_s giây để báo tiến độ (%) — video dài dò cảnh mất vài phút.
    frame_skip=1: chỉ xét 1/2 số khung (nhanh gần gấp đôi, vẫn đủ bắt điểm cắt cảnh)."""
    from scenedetect import ContentDetector, SceneManager, open_video

    stream = open_video(str(video))
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=threshold, min_scene_len=f"{min_scene_len_s}s"))
    total = duration or 0.0
    last_pct = 0
    while True:
        n = sm.detect_scenes(stream, duration=chunk_s, frame_skip=frame_skip)
        if progress and total > 0:
            pct = min(100, int(_seconds(stream.position) / total * 100))
            if pct // 10 > last_pct // 10 and pct < 100:
                progress(f"Dò cảnh… {pct}%")
                last_pct = pct
        if n == 0 or (total and _seconds(stream.position) >= total - 0.05):
            break
    found = sm.get_scene_list()
    scenes = [Scene(index=i, start=_seconds(a), end=_seconds(b)) for i, (a, b) in enumerate(found)]
    if not scenes:  # không có điểm cắt → cả video là một cảnh
        scenes = [Scene(index=0, start=0.0, end=duration or 0.0)]
    return scenes


def frame_times(duration: float, scenes: list[Scene], every_s: float = 4.0, max_frames: int = 40,
                min_gap_s: float = 0.5) -> list[float]:
    """Mốc rải đều + khung đầu mỗi cảnh; bỏ mốc quá gần nhau; nếu quá nhiều thì lấy thưa đều."""
    if duration <= 0:
        return []
    times = {round(min(s.start + 0.2, (s.start + s.end) / 2), 3) for s in scenes}
    t = every_s / 2
    while t < duration:
        times.add(round(t, 3))
        t += every_s
    ordered = []
    for x in sorted(times):
        if 0 <= x < duration and (not ordered or x - ordered[-1] >= min_gap_s):
            ordered.append(x)
    if len(ordered) > max_frames:
        step = len(ordered) / max_frames
        ordered = [ordered[int(i * step)] for i in range(max_frames)]
    return ordered


def _seconds(tc) -> float:
    """PySceneDetect 0.7 dùng thuộc tính .seconds, bản 0.6 dùng get_seconds()."""
    value = getattr(tc, "seconds", None)
    return float(value) if isinstance(value, (int, float)) else float(tc.get_seconds())
