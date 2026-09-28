"""Giới hạn tài nguyên khi nhiều video (job) chạy song song.

Mỗi bước của job thuộc một nhóm; mỗi nhóm có số "chỗ" (config/app.yaml → parallel). Riêng GPU chỉ khóa đúng
lúc nhận dạng thoại (Whisper): video A đang nhận dạng thoại thì video B đợi GPU, nhưng B vẫn dò cảnh / dò mặt (CPU)
hoặc hỏi đạo diễn AI cùng lúc.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager

from app import config

STEP_GROUP = {"analyze": "analyze", "understand": "director", "segment": "director", "hooks": "director",
              "plan": "director", "captions": "director", "write": "write"}
GROUP_VI = {"analyze": "phân tích", "gpu": "GPU (nhận dạng thoại)", "director": "hỏi đạo diễn AI", "write": "ghi draft CapCut"}
_SEMS: dict[str, threading.Semaphore] = {}
_LOCK = threading.Lock()


def _sem(group: str) -> threading.Semaphore:
    with _LOCK:
        if group not in _SEMS:
            n = int((config.load("app").get("parallel") or {}).get(group, 1))
            _SEMS[group] = threading.Semaphore(max(1, n))
        return _SEMS[group]


@contextmanager
def slot(step: str, on_wait=None):
    """Giữ một chỗ của nhóm tài nguyên trong lúc chạy bước; hết chỗ thì gọi on_wait() rồi đợi."""
    with group_slot(STEP_GROUP.get(step), on_wait):
        yield


@contextmanager
def group_slot(group: str | None, on_wait=None):
    if group is None:
        yield
        return
    sem = _sem(group)
    if not sem.acquire(blocking=False):
        if on_wait:
            on_wait(GROUP_VI.get(group, group))
        sem.acquire()
    try:
        yield
    finally:
        sem.release()


def reset() -> None:
    """(cho test) tạo lại các semaphore theo config hiện tại."""
    with _LOCK:
        _SEMS.clear()
