"""Giới hạn tài nguyên khi nhiều video (job) chạy song song.

Mỗi bước của job thuộc một nhóm; mỗi nhóm có số "chỗ" (config/app.yaml → parallel). Riêng GPU chỉ khóa đúng
lúc nhận dạng thoại (Whisper): video A đang nhận dạng thoại thì video B đợi GPU, nhưng B vẫn dò cảnh / dò mặt (CPU)
hoặc hỏi đạo diễn AI cùng lúc.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager

from app import config

# Chủ dự án 15/10 "đợi lượt hỏi đạo diễn AI lâu quá": trước đây CẢ BƯỚC (plan, dub, segment…) giữ một chỗ "hỏi AI" kể
# cả lúc bước đó đang làm việc khác (tách nhạc Demucs, nhận dạng lại thoại…) → job khác phải chờ dù không ai đang hỏi AI.
# Giờ giới hạn đặt đúng ở TỪNG LƯỢT HỎI AI (ai_slot, gọi trong Director.run) — số lượt cùng lúc trên MỌI job đổi được
# trên giao diện (config/local.yaml → parallel_ai, mặc định config/app.yaml → parallel.director).
STEP_GROUP = {"analyze": "analyze", "write": "write"}
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
    from app.jobs import stop

    sem = _sem(group)
    if not sem.acquire(blocking=False):
        if on_wait:
            on_wait(GROUP_VI.get(group, group))
        while not sem.acquire(timeout=0.5):  # đang đợi lượt mà người dùng bấm Dừng → thôi đợi
            stop.check()
    try:
        yield
    finally:
        sem.release()


def ai_limit(path=None) -> int:
    """Số lượt hỏi AI cùng lúc trên mọi job: chỉnh trên giao diện (config/local.yaml → parallel_ai), không thì theo
    config/app.yaml → parallel.director. Đọc lại mỗi lần nên đổi trên giao diện là có tác dụng ngay."""
    from app import settings

    try:
        local = (settings.load(path) if path else settings.load()).get("parallel_ai")
    except Exception:
        local = None
    return max(1, int(local or (config.load("app").get("parallel") or {}).get("director", 3)))


class _AiCounter:
    def __init__(self):
        self.n = 0
        self.cv = threading.Condition()


_AI = _AiCounter()


def ai_busy() -> int:
    return _AI.n


@contextmanager
def ai_slot(on_wait=None, limit=None):
    """Giữ một lượt hỏi AI trong lúc gọi Claude / Gemini; hết lượt thì gọi on_wait(số lượt đang chạy) rồi đợi (bấm Dừng
    vẫn thoát được)."""
    from app.jobs import stop

    get = limit or ai_limit
    with _AI.cv:
        if _AI.n >= get() and on_wait:
            on_wait(_AI.n)
        while _AI.n >= get():
            _AI.cv.wait(0.5)
            stop.check()
        _AI.n += 1
    try:
        yield
    finally:
        with _AI.cv:
            _AI.n -= 1
            _AI.cv.notify_all()


def reset() -> None:
    """(cho test) tạo lại các semaphore theo config hiện tại."""
    with _LOCK:
        _SEMS.clear()
