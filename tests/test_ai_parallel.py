"""Hỏi AI song song trong một job (app/jobs/parallel.py) — chủ dự án 11/10."""

import time

import pytest

from app.jobs import stop
from app.jobs.parallel import run_parallel


def test_order_errors_and_job_binding():
    seen, done = [], []

    def fn(x):
        seen.append(stop.current())          # luồng con vẫn biết đang chạy job nào (nút Dừng dùng cái này)
        time.sleep(0.05 * (3 - x))
        if x == 1:
            raise ValueError("video 2 lỗi")
        done.append(x)
        return x * 10

    stop.set_current("jobA")
    try:
        assert run_parallel(lambda x: x * 10, [3, 1, 2], 2) == [30, 10, 20]   # đúng thứ tự đầu vào
        with pytest.raises(ValueError, match="video 2 lỗi"):
            run_parallel(fn, [0, 1, 2], 3)
        assert sorted(done) == [0, 2]                                           # các video khác vẫn xong
        assert set(seen) == {"jobA"}
        assert run_parallel(lambda x: x, [1, 2], 1) == [1, 2]                   # 1 = lần lượt như cũ
    finally:
        stop.set_current(None)


def test_stop_wins_over_other_errors():
    def fn(x):
        if x == 0:
            raise RuntimeError("lỗi khác")
        raise stop.JobStopped("Đã dừng theo yêu cầu")

    with pytest.raises(stop.JobStopped):
        run_parallel(fn, [0, 1], 2)
