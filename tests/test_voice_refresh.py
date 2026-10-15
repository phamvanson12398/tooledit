"""Chủ dự án 14/10: "nhiều khi tool có voice rồi nhưng không thêm vào dự án CapCut".
(1) job đã xong rồi mới tải / thu lại voice (hoặc OmniVoice đọc) → trước đây không dựng lại; (2) voice tải lên đúng lúc job
đang chạy → lượt chạy đó bỏ qua, không ai chạy lại."""

import json
import os
import threading
import time
from pathlib import Path

from app.director.fake import FakeDirector
from app.jobs.job import Job, JobOptions, Status
from tests.test_director import make_analysis
from tests.test_planner import load
from tests.test_review import _clips, _plan, _script
from tests.test_runner import make_runner


def _done_review_job(tmp_path, n_voice: int):
    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/phim.mp4")], JobOptions(review=True, target_language="ko", review_s=150),
                     job_id="vr")
    make_analysis(jobs / "vr", duration=200.0)
    r = make_runner(tmp_path, jobs)
    u = load("understand.json")
    u["usable_range"] = {"start": 0.0, "end": 200.0}
    r._director = FakeDirector(responses={"understand": u, "plan": _plan(1, _clips(1.0, 56)),
                                          "dub_review": _script(1, 1.0), "review_polish": _script(1, 1.0),
                                          "captions": load("captions.json")})
    job = r.run(job)
    for n in range(1, n_voice + 1):
        (jobs / "vr" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job.data["dub_skip"] = True  # dựng trước, chưa đủ voice (nút "Bỏ qua, dựng luôn")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    return jobs, job, r


def _voice_segments(draft: str) -> int:
    content = json.loads((Path(draft) / "draft_content.json").read_text(encoding="utf-8"))
    return sum(1 for a in content["materials"]["audios"] if "video01_dub" in a.get("path", ""))


def test_voice_added_after_done_is_written_to_capcut(tmp_path):
    jobs, job, r = _done_review_job(tmp_path, n_voice=10)
    draft = job.data["drafts"][0]["draft"]
    assert _voice_segments(draft) == 10
    job = r.resume(job)  # không có voice mới → không ghi đè draft (giữ chỉnh tay trong CapCut)
    assert "Đã cập nhật voice" not in job.message
    later = time.time() + 5
    for n in range(11, 16):  # thu nốt 5 câu sau khi job đã xong
        f = jobs / "vr" / "voice" / f"video01_dub{n:02d}.wav"
        f.write_bytes(b"RIFF")
        os.utime(f, (later, later))
    job = r.resume(job)
    assert job.status == Status.done and "Đã cập nhật voice mới vào dự án CapCut: video 01" in job.message
    assert _voice_segments(draft) == 15
    assert "Đã cập nhật voice" in Job.load(jobs, "vr").message


def test_voice_uploaded_while_job_running_runs_again(tmp_path):
    from app.web.server import Worker

    Job.create(tmp_path, [Path("v.mp4")], JobOptions(), job_id="w1")
    gate, runs = threading.Event(), []

    class R:
        def __init__(self, root, log):
            pass

        def run(self, job):
            runs.append(job.job_id)
            if len(runs) == 1:
                gate.wait(5)
            return job

        resume = run

    w = Worker(tmp_path, R, max_jobs=lambda: 2)
    assert w.start("w1")
    acted = []
    assert w.start_or_later("w1", action=lambda runner, job: acted.append(1))  # đang chạy → nhớ để chạy lại
    gate.set()
    t = time.time()
    while (len(runs) < 2 or w.active) and time.time() - t < 5:
        time.sleep(0.05)
    assert runs == ["w1", "w1"] and acted == [1]
