"""Chọn nhạc nền khi tạo job (không chọn = AI tự chọn) và đổi nhạc sau khi dựng."""

import json
from pathlib import Path

from app.capcut_writer import DraftTemplate
from app.jobs.job import JobOptions, Status
from tests.test_planner import SAMPLE
from tests.test_runner import make_runner, prepare


def _other_music():
    music = [m.name for m in DraftTemplate(SAMPLE).library if m.kind == "music"]
    return next(n for n in music if n != "Keep It High")  # bài khác bài AI (FakeDirector) chọn


def test_user_music_choice_used(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions())
    r = make_runner(tmp_path, jobs)
    pick = _other_music()
    job.data["music_choice"] = pick
    job = r.run(job)
    assert job.status == Status.done, job.message
    plan = json.loads((jobs / "j1" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    assert plan["music"]["name"] == pick
    prompt = next(c["prompt"] for c in r._director.calls if c["task"] == "plan")
    assert pick in prompt and "Keep It High" not in prompt.split("## Nhạc")[-1][:2000]  # chỉ đưa bài đã chọn


def test_no_choice_means_ai_picks(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions())
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    plan = json.loads((jobs / "j1" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    assert plan["music"]["name"] == "Keep It High"


def test_change_music_after_done_without_ai(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions())
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    n_calls = len(r._director.calls)
    pick = _other_music()
    assert r.set_music(job, pick) == 1
    job = r.run(job)
    assert job.status == Status.done
    plan = json.loads((jobs / "j1" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    assert plan["music"]["name"] == pick and job.data["music_choice"] == pick
    assert len(r._director.calls) == n_calls  # không hỏi lại AI


def test_home_has_music_select_and_upload(tmp_path):
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    jobs = tmp_path / "jobs"
    footage = tmp_path / "f.mp4"
    footage.write_bytes(b"x")
    app = create_app(jobs, lambda root, log: None, assets_root=tmp_path / "assets")
    app.state.worker.start = lambda job_id, action=None: True  # không chạy thật
    client = TestClient(app)
    home = client.get("/").text
    assert "AI tự chọn theo nội dung" in home and "name='music_file'" in home
    r = client.post("/jobs", data={"footage": str(footage), "music": "Keep It High"}, follow_redirects=False)
    jid = r.headers["location"].rsplit("/", 1)[1]
    from app.jobs.job import Job

    assert Job.load(jobs, jid).data["music_choice"] == "Keep It High"
    r = client.post("/jobs", data={"footage": str(footage)},
                    files={"music_file": ("Bai Cua Toi.mp3", b"ID3", "audio/mpeg")}, follow_redirects=False)
    jid = r.headers["location"].rsplit("/", 1)[1]
    choice = Job.load(jobs, jid).data["music_choice"]
    assert choice.startswith("tu_chon_") and list((tmp_path / "assets" / "music" / "tu_chon").glob("*.mp3"))
    r = client.post("/jobs", data={"footage": str(footage)}, follow_redirects=False)
    jid = r.headers["location"].rsplit("/", 1)[1]
    assert "music_choice" not in Job.load(jobs, jid).data
