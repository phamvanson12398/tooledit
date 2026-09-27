import threading
import time
from pathlib import Path

from app.jobs import limits
from app.jobs.job import Job, JobOptions, Status
from app.web.server import Worker


class FakeRunner:
    lock = threading.Lock()
    now = 0
    peak = 0
    done: list = []

    def __init__(self, root, log):
        self.root = root

    def run(self, job):
        with FakeRunner.lock:
            FakeRunner.now += 1
            FakeRunner.peak = max(FakeRunner.peak, FakeRunner.now)
        time.sleep(0.3)
        with FakeRunner.lock:
            FakeRunner.now -= 1
            FakeRunner.done.append(job.job_id)
        job.status = Status.done
        job.save(self.root)
        return job

    resume = run


def test_pool_runs_jobs_in_parallel_and_queues_extra(tmp_path):
    FakeRunner.now = FakeRunner.peak = 0
    FakeRunner.done = []
    for i in range(3):
        Job.create(tmp_path, [Path(f"v{i}.mp4")], JobOptions(), job_id=f"j{i}")
    w = Worker(tmp_path, FakeRunner, max_jobs=lambda: 2)
    assert w.start("j0") and w.start("j1") and w.start("j2")
    assert not w.start("j0")  # đang chạy thì không chạy trùng
    assert w.queued_ids() == ["j2"] and w.active == {"j0", "j1"}
    t = time.time()
    while (w.active or w.queue) and time.time() - t < 5:
        time.sleep(0.05)
    assert sorted(FakeRunner.done) == ["j0", "j1", "j2"]
    assert FakeRunner.peak == 2  # đúng 2 luồng cùng lúc, video thứ 3 đợi
    assert all(Job.load(tmp_path, f"j{i}").status == Status.done for i in range(3))


def test_remove_queued(tmp_path):
    for i in range(2):
        Job.create(tmp_path, [Path("v.mp4")], JobOptions(), job_id=f"k{i}")
    w = Worker(tmp_path, FakeRunner, max_jobs=lambda: 1)
    w.start("k0")
    w.start("k1")
    assert w.remove_queued("k1") and not w.queued_ids()
    t = time.time()
    while w.active and time.time() - t < 5:
        time.sleep(0.05)


def test_analyze_step_one_at_a_time_director_two(monkeypatch):
    from app import config

    monkeypatch.setattr(config, "load", lambda name: {"parallel": {"analyze": 1, "director": 2}} if name == "app" else {})
    limits.reset()
    peak = {"analyze": 0, "director": 0}
    now = {"analyze": 0, "director": 0}
    waits = []
    lk = threading.Lock()

    def work(step, group):
        with limits.slot(step, on_wait=waits.append):
            with lk:
                now[group] += 1
                peak[group] = max(peak[group], now[group])
            time.sleep(0.15)
            with lk:
                now[group] -= 1

    ts = [threading.Thread(target=work, args=("analyze", "analyze")) for _ in range(3)] + \
         [threading.Thread(target=work, args=("plan", "director")) for _ in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert peak == {"analyze": 1, "director": 2}
    assert "phân tích (GPU)" in waits  # có báo đợi lượt
    limits.reset()
