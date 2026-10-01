"""Chế độ Đổi ngôn ngữ: thuyết minh + phụ đề ngôn ngữ đích, dựng lại khác bản gốc (giữ thứ tự cảnh)."""

import json
from pathlib import Path

from app.director.fake import FakeDirector
from app.director.schemas import DubScript, EditPlan, PlanClip, Understanding, check_remix
from app.director.tasks import check_dub, make_dub, translate_note, understand
from app.jobs.job import JobOptions, Status
from app.planner import dub_io
from tests.test_director import GOOD, make_analysis
from tests.test_planner import _short_plan, load
from tests.test_runner import make_runner as _make_runner, prepare
from tests.test_planner import SAMPLE


def _remix_plan():
    from app.capcut_writer import DraftTemplate

    p = _short_plan()
    p["filter"] = next(i.name for i in DraftTemplate(SAMPLE).library if i.kind == "filter")
    return p


def make_runner(tmp_path, jobs, **responses):
    r = _make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _remix_plan(), **responses})
    return r

FIX = json.loads((Path(__file__).parent / "fixtures" / "director" / "dub.json").read_text(encoding="utf-8"))


def test_understanding_dubbed_keeps_source():
    u = Understanding.model_validate(GOOD).dubbed_to("ko")
    assert u.language == "ko" and u.source_language == "ja"
    v = u.model_copy(update={"summary_vi": "x"})  # for_video dùng model_copy
    assert v.source_language == "ja"
    assert "tiếng Nhật → tiếng Hàn" in translate_note(u)
    assert translate_note(Understanding.model_validate(GOOD)) == ""
    assert Understanding.model_validate({**GOOD, "language": "zh"}).language == "zh"


def test_check_dub_rules():
    plan = EditPlan.model_validate(_short_plan())  # clip 1–45s
    script = DubScript.model_validate(FIX)
    assert check_dub(script, plan, "ko") == []
    bad = DubScript.model_validate({**FIX, "lines": [
        {"source_start": 40, "source_end": 50, "text": "a", "text_vi": "a"},  # ra ngoài clip
        {"source_start": 2, "source_end": 3, "text": "가" * 30, "text_vi": "x"},  # nói quá nhanh
        {"source_start": 1.5, "source_end": 3, "text": "유튜브 구독", "text_vi": "x"}]})  # chồng + nền tảng khác
    errs = check_dub(bad, plan, "ko")
    assert any("gọn trong MỘT clip" in e for e in errs) and any("ký tự/giây" in e for e in errs)
    assert any("chồng" in e for e in errs) and any("không được phép" in e for e in errs)


def test_check_remix():
    p = load("plan.json")
    plan = EditPlan.model_validate(p)
    assert check_remix(plan, have_filters=False) == []
    assert any("filter" in e for e in check_remix(plan, have_filters=True))
    rev = plan.model_copy(update={"clips": list(reversed(plan.clips))})
    assert any("thứ tự" in e for e in check_remix(rev, False))


def test_make_dub_prompt(tmp_path):
    a = make_analysis(tmp_path)
    u = understand(FakeDirector(), a).dubbed_to("ko")
    d = FakeDirector()
    s = make_dub(d, a, u, EditPlan.model_validate(_short_plan()))
    assert len(s.lines) == 3
    prompt = d.calls[0]["prompt"]
    assert "thuyết minh bằng **tiếng Hàn**" in prompt and "Footage gốc nói tiếng Nhật" in prompt
    assert "clip 0: 1.0–45.0s" in prompt


def test_split_and_spread():
    assert dub_io.split_text("짧은 문장", "ko", 16) == ["짧은 문장"]
    parts = dub_io.split_text("今日はとても楽しい一日でした。また来週も一緒に遊びましょうね！", "ja", 13)
    assert all(len(p) <= 13 for p in parts) and "".join(parts).startswith("今日は")
    cues = dub_io.spread_cues(["ab", "abcd"], 0, 600)
    assert cues == [(0, 200, "ab"), (200, 600, "abcd")]
    assert dub_io.match_uploads(["2.wav", "10.wav", "1.wav"], 1, 3) == [("1.wav", 1), ("2.wav", 2), ("10.wav", 3)]


def test_full_dub_job(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "dub_voice", job.message
    assert "video01_dub01.wav" in job.message
    assert job.data["source_language"] == "ja"
    script = (jobs / "j1" / "dub_scripts.txt").read_text(encoding="utf-8")
    assert "저 스모 선수" in script and "video01_dub03.wav" in script
    vdir = jobs / "j1" / "voice"
    for n in (1, 2, 3):
        (vdir / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    draft = Path(job.data["draft"])
    content = json.loads((draft / "draft_content.json").read_text(encoding="utf-8"))
    audio_paths = [m.get("path", "") for m in content["materials"]["audios"]]
    assert sum("video01_dub" in p for p in audio_paths) == 3
    texts = " ".join(m.get("content", "") for m in content["materials"]["texts"])
    assert "스모" in texts and "こんにちは" not in texts  # phụ đề là câu dịch, không phải lời gốc
    plan = json.loads((jobs / "j1" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    assert plan["clips"]


def test_dub_skip_and_redo(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(target_language="en"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.step == "dub_voice"
    (jobs / "j1" / "voice" / "video01_dub01.wav").write_bytes(b"RIFF")
    job.data["dub_skip"] = True
    job = r.resume(job)
    assert job.status == Status.done, job.message
    missing = json.loads((jobs / "j1" / "missing_assets.json").read_text(encoding="utf-8"))
    assert sum(m["kind"] == "voice" for m in missing) == 2
    r.redo(job, "dub")
    assert not list((jobs / "j1" / "plan").glob("dub_video*.json"))
    assert (jobs / "j1" / "voice" / "video01_dub01_cu.wav").is_file()


def test_same_language_target_only_remixes(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(target_language="ja"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.done and job.data.get("dub_same")
    assert not list((jobs / "j1" / "plan").glob("dub_video*.json"))


def test_chinese_source_requires_target(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions())
    r = make_runner(tmp_path, jobs, understand={**GOOD, "language": "zh"})
    job = r.run(job)
    assert job.status == Status.error and "Đổi ngôn ngữ" in job.message


def test_web_dub_flow(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app
    from tests.test_web import wait_idle

    jobs = tmp_path / "jobs"
    footage = tmp_path / "test.mp4"
    footage.write_bytes(b"x")

    def factory(root, log):
        r = make_runner(tmp_path, root)
        r.log = log
        return r

    app = create_app(jobs, factory)
    client = TestClient(app)
    assert "Đổi sang tiếng Hàn" in client.get("/").text
    orig_start = app.state.worker.start

    def start(job_id, action=None):
        if not (jobs / job_id / "analysis").exists():
            make_analysis(jobs / job_id, duration=60.0)
        return orig_start(job_id, action)

    app.state.worker.start = start
    r = client.post("/jobs", data={"footage": str(footage), "target_language": "ko", "hook": ""},
                    follow_redirects=False)
    jid = r.headers["location"].rsplit("/", 1)[1]
    wait_idle(app)
    job = Job.load(jobs, jid)
    assert job.options.target_language == "ko" and job.step == "dub_voice", job.message
    page = client.get(f"/jobs/{jid}").text
    assert "Thu voice thuyết minh" in page and "video01_dub03" in page and "저 스모 선수" in page
    # chọn 3 file tên tùy ý một lượt → tự xếp theo thứ tự
    files = [("files", (f"{n}.wav", b"RIFF", "audio/wav")) for n in (1, 2, 3)]
    client.post(f"/jobs/{jid}/dub-voice", data={"video": "1"}, files=files, follow_redirects=False)
    wait_idle(app)
    assert (jobs / jid / "voice" / "video01_dub03.wav").is_file()
    job = Job.load(jobs, jid)
    assert job.status.value == "done", job.message
    assert "Voice thuyết minh" in client.get(f"/jobs/{jid}").text
