"""Nút Dừng job: dừng ở điểm an toàn, tắt tiến trình AI đang chạy, chạy tiếp được."""

import sys
import threading
import time

import pytest

from app.jobs import stop
from app.jobs.job import JobOptions, Status
from tests.test_runner import make_runner, prepare


def test_stop_before_step_then_resume(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions())
    r = make_runner(tmp_path, jobs)
    stop.request(job.job_id)
    job = r.run(job)
    assert job.status == Status.stopped and job.step == "analyze"
    assert not stop.requested(job.job_id)  # dấu dừng được xóa sau khi dừng
    job = r.resume(job)  # Chạy tiếp
    assert job.status == Status.done, job.message


def test_stop_requested_while_ai_working(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions())
    r = make_runner(tmp_path, jobs)
    inner = r._director.run

    def run_and_press_stop(task, *a, **kw):  # người dùng bấm Dừng trong lúc AI đang trả lời
        out = inner(task, *a, **kw)
        if task == "understand":
            stop.request(stop.current())
        return out

    r._director.run = run_and_press_stop
    job = r.run(job)
    # bước AI vừa trả lời xong được giữ kết quả; job dừng trước bước kế tiếp
    assert job.status == Status.stopped and job.step == "segment"
    assert (jobs / "j1" / "plan" / "understanding.json").is_file()
    assert r.resume(job).status == Status.done


def test_ai_process_killed_on_stop(tmp_path):
    from app.director.claude_cli import _run_stoppable

    stop.set_current("jx")
    threading.Timer(0.3, lambda: stop.request("jx")).start()
    t0 = time.monotonic()
    with pytest.raises(stop.JobStopped):
        _run_stoppable([sys.executable, "-c", "import time; time.sleep(30)"], "", tmp_path, 60)
    assert time.monotonic() - t0 < 5
    stop.clear("jx")
    stop.set_current(None)
    done = _run_stoppable([sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"], "abc", tmp_path, 30)
    assert done.stdout.strip() == "ABC" and done.returncode == 0


def test_waiting_for_slot_can_be_stopped():
    from app.jobs import limits

    limits.reset()
    sem = limits._sem("director")
    taken = []
    while sem.acquire(blocking=False):
        taken.append(1)
    stop.set_current("jw")
    threading.Timer(0.3, lambda: stop.request("jw")).start()
    with pytest.raises(stop.JobStopped):
        with limits.slot("plan"):
            pass
    for _ in taken:
        sem.release()
    stop.clear("jw")
    stop.set_current(None)
    limits.reset()


def test_web_stop_queued_job(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [tmp_path / "a.mp4"], JobOptions(), job_id="q1")
    app = create_app(jobs, lambda root, log: None)
    w = app.state.worker
    w.queue.append(("q1", None))
    client = TestClient(app)
    client.post("/jobs/q1/stop", follow_redirects=False)
    assert "q1" not in w.queued_ids()
    assert Job.load(jobs, "q1").status == Status.stopped
    page = client.get("/jobs/q1").text
    assert "Đã dừng" in page and "Chạy tiếp từ bước này" in page
    assert w.stop("q1") == "idle"
