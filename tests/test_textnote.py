"""Chữ theo hành động (chủ dự án yêu cầu 17/11): giữ NGUYÊN video gốc, thỉnh thoảng có hành động thì hiện một dòng chữ;
tùy chọn giọng nói ngôi thứ nhất (đọc chính các dòng đó, chữ = phụ đề)."""

import json
from pathlib import Path

from app.director.schemas import TextNoteScript
from app.director.textnote import (
    check_textnote,
    keep_ranges,
    repair_textnote,
    textnote_plan,
)
from app.jobs.job import JobOptions, Status
from tests.test_runner import make_runner as _make_runner
from tests.test_runner import prepare

FIX = json.loads((Path(__file__).parent / "fixtures" / "director" / "textnote.json").read_text(encoding="utf-8"))
CFG = {"min_note_s": 1.2, "max_note_s": 4.0, "min_gap_s": 3.0, "max_share": 0.35, "max_chars": {"ko": 18},
       "voice": {"max_line_s": 7, "min_gap_s": 2.0, "max_share": 0.5, "line_fill": 1.15, "max_speech_overlap": 0.5}}


def _check(data, voice=False, segs=None):
    return check_textnote(TextNoteScript.model_validate(data), "ko", duration=60.0, cfg=CFG, voice=voice, cps=7.0,
                          segs=segs)


def test_check_textnote():
    assert _check(FIX) == []
    n = FIX["notes"]
    assert any("cách ít nhất 3" in e for e in _check({**FIX, "notes": [n[0], {**n[1], "start": 9, "end": 11}]}))
    assert any("tối đa 18 ký tự" in e for e in _check({**FIX, "notes": [{**n[0], "text": "가" * 25}]}))
    assert any("ngôn ngữ đích" in e for e in _check({**FIX, "notes": [{**n[0], "text": "add the eggs now"}]}))
    assert any("phải 1.2–4" in e for e in _check({**FIX, "notes": [{**n[0], "end": 12}]}))
    many = {**FIX, "notes": [{**n[0], "start": 7 * k, "end": 7 * k + 4} for k in range(8)]}
    assert any("tối đa 35%" in e for e in _check(many))  # chỉ "thỉnh thoảng", không dày đặc


def test_voice_rules():
    n = FIX["notes"]
    long = {**FIX, "notes": [{**n[0], "text": "지금 계란을 넣고 천천히 저어줄 거예요 정말 맛있겠죠 여러분도 꼭 해보세요"}]}
    assert any("viết ngắn lại" in e for e in _check(long, voice=True))  # câu đọc không kịp
    assert not any("ký tự" in e for e in _check(long, voice=True))     # có giọng nói: chữ = phụ đề, không giới hạn 1 dòng
    talk = [{"start": 4.0, "end": 9.0, "text": "x"}]
    assert any("lời nói gốc" in e for e in _check(FIX, voice=True, segs=talk))  # câu đọc phải nằm ở chỗ lặng


def test_repair_and_plan():
    n = FIX["notes"]
    r, fixes = repair_textnote(TextNoteScript.model_validate(
        {**FIX, "notes": [n[1], {**n[0], "end": 11}, {**n[2], "start": 21, "end": 24}]}), 60.0, CFG, False)
    assert _check(r.model_dump()) == [] and fixes
    assert [x.start for x in r.notes] == [5.0, 20.0]  # xếp lại + rút dòng dài; dòng sát quá không lùi được thì bỏ…
    assert keep_ranges(60.0, [(10, 12), (30, 31)]) == [(0.0, 10.0), (12.0, 30.0), (31.0, 60.0)]
    plan = textnote_plan(TextNoteScript.model_validate(FIX), 60.0, [], CFG, voice=False)
    assert [(c.source_start, c.source_end, c.speed) for c in plan.clips] == [(0.0, 60.0, 1.0)]  # giữ nguyên video
    assert [e.text for e in plan.emphasis] == ["계란 투입!", "소금 한 꼬집", "완성 ✨"] and plan.emphasis[0].position == "top"
    assert textnote_plan(TextNoteScript.model_validate(FIX), 60.0, [], CFG, voice=True).emphasis == []


def test_full_textnote_job_no_voice(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(textnote=True, target_language="ko", client_id="k"))
    r = _make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.done, job.message
    tasks = [c["task"] for c in r.director.calls]
    assert "textnote" in tasks and "plan" not in tasks and "dub" not in tasks
    assert not (jobs / "j1" / "plan" / "dub_video01.json").exists()
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    vids = {m["id"]: m for m in content["materials"]["videos"]}
    segs = [s for t in content["tracks"] if t["type"] == "video" for s in t["segments"]
            if vids.get(s["material_id"], {}).get("type") == "video"]
    assert abs(sum(s["target_timerange"]["duration"] for s in segs) - 60_000_000) < 100_000  # không cắt giây nào
    texts = [m.get("content", "") for m in content["materials"]["texts"]]
    assert any("계란 투입" in t for t in texts) and not any("こんにちは" in t for t in texts)  # chữ, không phụ đề gốc
    assert not [m for m in content["materials"]["audios"] if "music" in m.get("type", "")]  # không thêm nhạc


def test_full_textnote_job_with_voice(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(textnote=True, textnote_voice=True, target_language="ko", client_id="k"))
    r = _make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "dub_voice", job.message
    dub = json.loads((jobs / "j1" / "plan" / "dub_video01.json").read_text(encoding="utf-8"))
    assert [ln["text"] for ln in dub["lines"]] == ["계란 투입!", "소금 한 꼬집", "완성 ✨"]
    assert "NGÔI THỨ NHẤT" in next(c["prompt"] for c in r.director.calls if c["task"] == "textnote")
    for k in range(1, 4):
        (jobs / "j1" / "voice" / f"video01_dub{k:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message


def test_home_textnote_mode(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    c = TestClient(app)
    home = c.get("/").text
    assert "name='mode' value='textnote'" in home and "name=\"textnote_voice\"" in home
    res = c.post("/jobs", data={"footage": str(f), "mode": "textnote", "target_language": "ja", "textnote_voice": "on",
                                "hook": "on"}, follow_redirects=False)
    job = Job.load(tmp_path / "jobs", res.headers["location"].rsplit("/", 1)[1])
    assert job.options.textnote and job.options.textnote_voice and not job.options.hook
    assert job.options.target_language == "ja"
    assert "✍️ Chữ theo hành động" in c.get(f"/jobs/{job.job_id}").text
    assert "Chưa chọn ngôn ngữ" in c.post("/jobs", data={"footage": str(f), "mode": "textnote"}).text
