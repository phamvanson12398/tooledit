"""Hỏi đạo diễn AI song song trong MỘT job (chủ dự án 11/10: "Gemini hơi chậm — video dài thì chia ra làm rồi gộp").

Dùng cho: chọn đoạn của video dài (mỗi phần một lượt hỏi), lập kế hoạch / viết thoại khi job ra nhiều video.
Số lượt cùng lúc: `parallel_calls` trong config/director.yaml (hạn mức Claude Pro / Google AI Pro có giới hạn tần suất —
để 2 là vừa). Mỗi luồng con được gắn đúng job (nút ⏹️ Dừng vẫn tắt được tiến trình AI đang chạy).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, TypeVar

from app import config

T = TypeVar("T")
R = TypeVar("R")


def workers() -> int:
    return max(1, int(config.load("director").get("parallel_calls", 2) or 1))


def run_parallel(fn: Callable[[T], R], items: Iterable[T], n: int | None = None) -> list[R]:
    """Chạy fn(item) cho từng item, tối đa n lượt cùng lúc; trả kết quả ĐÚNG thứ tự items. Một lượt lỗi thì các lượt
    khác vẫn chạy xong (kết quả của chúng đã được lưu ra đĩa trong fn) rồi mới ném lỗi đầu tiên."""
    from app.jobs import stop

    items = list(items)
    n = workers() if n is None else max(1, n)
    if n <= 1 or len(items) <= 1:
        return [fn(x) for x in items]
    job_id = stop.current()

    def call(x):
        stop.set_current(job_id)
        try:
            return fn(x)
        finally:
            stop.set_current(None)

    with ThreadPoolExecutor(max_workers=min(n, len(items))) as pool:
        futures = [pool.submit(call, x) for x in items]
    errors = [f.exception() for f in futures if f.exception() is not None]
    if errors:
        stopped = [e for e in errors if isinstance(e, stop.JobStopped)]
        raise (stopped or errors)[0]
    return [f.result() for f in futures]
