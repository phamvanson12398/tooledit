"""Hoạt hình — giữ âm thanh gốc (chủ dự án yêu cầu 20/10): cốt truyện mới khác ≥ 70%, xếp lại cảnh, lồng voice chỗ có lời."""

import json
from pathlib import Path

from app.director.anim import check_anim, order_diff
from app.director.fake import FakeDirector
from app.director.schemas import AnimScript
from app.jobs.job import JobOptions, Status
from tests.test_planner import _short_plan
from tests.test_runner import make_runner as _make_runner, prepare

FIX = json.loads((Path(__file__).parent / "fixtures" / "director" / "anim.json").read_text(encoding="utf-8"))
SEGS = [{"start": 1.0, "end": 3.0, "text": "こんにちは"}]
CFG = {"min_story_diff": 70, "min_order_diff": 0.7, "min_cover": 0.6}


def make_runner(tmp_path, jobs, anim=None):
    r = _make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan(), **({"anim": anim} if anim else {})})
    return r


def _check(data):
    return check_anim(AnimScript.model_validate(data), "ko", duration=60, segments=SEGS, cps=7.0, cfg=CFG)


def test_order_diff_and_checks():
    r = AnimScript.model_validate(FIX)
    assert order_diff(r.beats) == 1.0 and _check(FIX) == []
    same = {**FIX, "beats": sorted(FIX["beats"], key=lambda b: b["start"])}
    same["beats"] = [{**b, "start": float(10 * k), "end": float(10 * k + 9.5)} for k, b in enumerate(same["beats"])]
    assert any("thứ tự cảnh mới còn giống bản gốc" in e for e in _check(same))  # giữ nguyên thứ tự → bắt xếp lại
    no_line = {**FIX, "beats": [{**b, "line": None} if b["start"] == 0 else b for b in FIX["beats"]]}
    assert any("có 2.0s lời nói gốc" in e for e in _check(no_line))  # cảnh có lời gốc phải có lời thoại mới
    low = {**FIX, "story_diff": 50}
    assert any("chỉ khác 50%" in e for e in _check(low))
    assert not any("chỉ khác" in e for e in _check({**low, "feasible": False}))  # không thể → báo chủ dự án, không ép
    overlap = {**FIX, "beats": FIX["beats"] + [{"start": 41, "end": 45}]}
    assert any("chồng nhau" in e for e in _check(overlap))


def test_full_anim_job(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(anim=True, target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "dub_voice", job.message
    assert "anim" in [c["task"] for c in r.director.calls] and "plan" not in [c["task"] for c in r.director.calls]
    plan = json.loads((jobs / "j1" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    assert [c["source_start"] for c in plan["clips"]] == [40, 0, 20, 50, 10, 30]  # cảnh theo thứ tự cốt truyện mới
    dub = json.loads((jobs / "j1" / "plan" / "dub_video01.json").read_text(encoding="utf-8"))
    assert [ln["speaker"] for ln in dub["lines"]] == ["냥이", "멍이"]  # lồng tiếng theo nhân vật
    assert "khác ~80%" in dub["story_vi"]
    assert job.data["anim_report"]["story_diff"] == 80
    for n in (1, 2):
        (jobs / "j1" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    vids = {m["id"]: m for m in content["materials"]["videos"]}
    segs = [s for t in content["tracks"] if t["type"] == "video" for s in t["segments"]
            if vids.get(s["material_id"], {}).get("type") == "video"]
    assert segs[0]["source_timerange"]["start"] == 40_000_000
    assert all(s["volume"] > 0 for s in segs)  # chưa cài Demucs: giữ tiếng gốc (hạ nhỏ dưới voice), không tắt hẳn
    names = [m.get("name", "") for m in content["materials"]["audios"]]
    assert any("video01_dub01" in n for n in names)
    texts = [m.get("content", "") for m in content["materials"]["texts"]]
    assert any("선물" in t for t in texts)  # phụ đề lời thoại mới


def test_not_70_percent_stops_and_tells_owner(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(anim=True, target_language="ko", client_id="k"))
    bad = {**FIX, "story_diff": 45, "feasible": False, "diff_note_vi": "video chỉ có 2 cảnh liền mạch"}
    r = make_runner(tmp_path, jobs, anim=bad)
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "plan"
    assert "KHÔNG làm được cốt truyện khác ≥ 70%" in job.message and "2 cảnh liền mạch" in job.message
    job = r.resume(job)  # Tiếp tục = vẫn dựng bản này
    assert job.step == "dub_voice", job.message


def test_home_anim_mode(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    c = TestClient(app)
    assert "name='mode' value='anim'" in c.get("/").text
    res = c.post("/jobs", data={"footage": str(f), "mode": "anim", "target_language": "ko", "hook": "on"},
                 follow_redirects=False)
    job_id = res.headers["location"].rsplit("/", 1)[1]
    o = Job.load(tmp_path / "jobs", job_id).options
    assert o.anim and o.target_language == "ko" and not o.hook and not o.sell
    assert "🎨 Hoạt hình" in c.get(f"/jobs/{job_id}").text
    assert "Chưa chọn ngôn ngữ" in c.post("/jobs", data={"footage": str(f), "mode": "anim"}).text
