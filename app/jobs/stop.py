"""Dừng job đang chạy (nút ⏹️ Dừng trên giao diện).

Python không "giết" được một luồng giữa chừng, nên dừng theo kiểu hợp tác:
- giao diện gọi request(job_id) → đánh dấu;
- luồng của job kiểm tra dấu ở các điểm an toàn: trước mỗi bước, khi đang đợi lượt tài nguyên, mỗi lần ghi nhật ký
  tiến trình (phân tích), và trong lúc chờ đạo diễn AI trả lời (tiến trình `claude` bị tắt ngay);
- gặp dấu → ném JobStopped → runner lưu job ở trạng thái "đã dừng" (bấm Chạy tiếp để chạy lại từ bước đang dở).
"""

from __future__ import annotations

import threading

_requested: set[str] = set()
_lock = threading.Lock()
_local = threading.local()


class JobStopped(Exception):
    pass


def request(job_id: str) -> None:
    with _lock:
        _requested.add(job_id)


def clear(job_id: str) -> None:
    with _lock:
        _requested.discard(job_id)


def requested(job_id: str | None) -> bool:
    with _lock:
        return job_id is not None and job_id in _requested


def set_current(job_id: str | None) -> None:
    """Gắn job cho luồng hiện tại (để code sâu bên trong — đạo diễn AI, đợi lượt — biết đang chạy job nào)."""
    _local.job_id = job_id


def current() -> str | None:
    return getattr(_local, "job_id", None)


def check() -> None:
    """Ném JobStopped nếu job của luồng hiện tại đã được yêu cầu dừng."""
    if requested(current()):
        raise JobStopped("Đã dừng theo yêu cầu")
