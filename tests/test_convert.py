"""Chế độ 🌐 Chuyển ngôn ngữ (chủ dự án yêu cầu 05/11): giữ nguyên hình, dịch lời gốc rồi AI biên tập lại từng câu cho
đúng cách người bản xứ nói (prompt dub_polish.md)."""

import json

from app.director.fake import FakeDirector
from app.director.schemas import DubScript
from app.jobs.job import Job, JobOptions
from tests.test_dub import FIX, make_runner
from tests.test_runner import prepare


def _dub_calls(r):
    return [c["task"] for c in r._director.calls if c["task"].startswith("dub")]


def test_convert_translates_then_polishes(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(target_language="ko", voice_only=True, convert=True,
                                              script_mode="translate"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.step == "dub_voice", job.message
    assert _dub_calls(r) == ["dub", "dub_polish"]  # dịch sát trước, rồi biên tập
    polish = next(c["prompt"] for c in r._director.calls if c["task"] == "dub_polish")
    assert "kính ngữ" in polish and "tiếng Hàn" in polish and "GIỮ ĐÚNG 5 câu" in polish  # mẹo tiếng Hàn + giữ số câu
    final = DubScript.model_validate_json((jobs / "j1" / "plan" / "dub_video01.json").read_text(encoding="utf-8"))
    assert final.lines[0].text.startswith("저 스모 선수 있잖아요")  # bản đã biên tập
    draft = json.loads((jobs / "j1" / "plan" / "dub_draft_video01.json").read_text(encoding="utf-8"))
    assert draft["lines"][0]["text"] == FIX["lines"][0]["text"]  # bản dịch nháp vẫn lưu để so


def test_convert_polish_keeps_timing_and_falls_back(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(target_language="ko", voice_only=True, convert=True,
                                              script_mode="translate"))
    moved = json.loads(json.dumps(FIX))
    for ln in moved["lines"]:  # AI lỡ đổi mốc giây / kind → code chép lại của bản dịch
        ln["source_start"] += 0.5
        ln["kind"] = "dub"
    r = make_runner(tmp_path, jobs, dub_polish=moved)
    job = r.run(job)
    final = DubScript.model_validate_json((jobs / "j1" / "plan" / "dub_video01.json").read_text(encoding="utf-8"))
    assert [(ln.source_start, ln.kind) for ln in final.lines] == [(x["source_start"], x.get("kind", "dub"))
                                                                  for x in FIX["lines"]]

    jobs2, job2 = prepare(tmp_path / "b", JobOptions(target_language="ko", voice_only=True, convert=True,
                                                      script_mode="translate"))
    r2 = make_runner(tmp_path / "b", jobs2, dub_polish={**FIX, "lines": FIX["lines"][:2]})  # sai số câu mãi
    logs = []
    r2.log = logs.append
    job2 = r2.run(job2)
    assert job2.step == "dub_voice", job2.message  # không dừng job
    final = DubScript.model_validate_json((jobs2 / "j1" / "plan" / "dub_video01.json").read_text(encoding="utf-8"))
    assert len(final.lines) == len(FIX["lines"]) and any("dùng bản dịch" in x for x in logs)


def test_voice_only_does_not_polish(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(target_language="ko", voice_only=True, script_mode="translate"))
    r = make_runner(tmp_path, jobs)
    r.run(job)
    assert "dub_polish" not in _dub_calls(r)


def test_home_convert_mode(tmp_path):
    from fastapi.testclient import TestClient

    from app.web.server import create_app, job_mode

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    c = TestClient(app)
    home = c.get("/").text
    assert "name='mode' value='convert'" in home and "Chuyển ngôn ngữ" in home
    assert 'name="keep_bgm" checked' in home
    assert "Chưa chọn ngôn ngữ" in c.post("/jobs", data={"footage": str(f), "mode": "convert"}).text
    res = c.post("/jobs", data={"footage": str(f), "mode": "convert", "target_language": "ko", "keep_bgm": "on",
                                "hook": "on", "split": "on"}, follow_redirects=False)
    job = Job.load(tmp_path / "jobs", res.headers["location"].rsplit("/", 1)[1])
    o = job.options
    assert o.convert and o.voice_only and o.keep_bgm and o.script_mode == "translate" and o.target_language == "ko"
    assert not o.hook and not o.split and job_mode(job) == "convert"
    assert "Chuyển ngôn ngữ" in c.get(f"/jobs/{job.job_id}").text
