"""Cops US (chủ dự án yêu cầu 16/11): video cảnh sát Mỹ dài < 1h → short < 3 phút, kịch bản theo hướng khác hẳn, xen
đoạn voice với đoạn giữ nguyên tiếng gốc."""

import json
from pathlib import Path

from app.director.fake import FakeDirector
from app.jobs.job import JobOptions, Status
from tests.test_planner import _short_plan
from tests.test_runner import make_runner, prepare

SELL = json.loads((Path(__file__).parent / "fixtures" / "director" / "sell.json").read_text(encoding="utf-8"))
N = len(SELL["lines"])
CATALOG = {"shots": [{"start": 0, "end": 60, "desc_vi": "bodycam: cảnh sát chặn xe", "tags": ["bodycam"], "quality": 4}],
           "editor_notes": ""}


def _runner(tmp_path, script):
    jobs, job = prepare(tmp_path, JobOptions(sell=True, cops=True, target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan(), "ideas_catalog": CATALOG, "cops": script})
    return jobs, job, r


def test_cops_job_new_script_with_original_audio(tmp_path):
    script = {**SELL, "target_s": 70, "inserts": [{"after_line": 2, "start": 40, "end": 45, "text": "정말 맛있어요!",
                                                    "text_vi": "Câu thoại gốc", "why_vi": "câu đắt"}]}
    jobs, job, r = _runner(tmp_path, script)
    job = r.run(job)
    assert job.step == "dub_voice", job.message
    tasks = [c["task"] for c in r.director.calls]
    assert "ideas_catalog" in tasks and "cops" in tasks and "sell" not in tasks  # xem hết video dài → prompt riêng
    prompt = next(c["prompt"] for c in r.director.calls if c["task"] == "cops")
    assert "KHÁC VIDEO GỐC" in prompt and "GIỮ NGUYÊN TIẾNG GỐC" in prompt and "DƯỚI 3 phút" in prompt
    assert "60–175" in prompt and "bodycam: cảnh sát chặn xe" in prompt
    for n in range(1, N + 1):
        (jobs / "j1" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    vids = {m["id"]: m for m in content["materials"]["videos"]}
    segs = [s for t in content["tracks"] if t["type"] == "video" for s in t["segments"]
            if vids.get(s["material_id"], {}).get("type") == "video"]
    loud = [s for s in segs if s["volume"] > 0]
    assert len(loud) == 1 and loud[0]["source_timerange"]["start"] == 40_000_000  # đoạn giữ tiếng gốc
    assert r._style(job)["mirror"]["share"] == 0.4  # phản chiếu một phần cảnh cho khác bản gốc


def test_home_cops_mode(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    c = TestClient(app)
    assert "name='mode' value='cops'" in c.get("/").text
    res = c.post("/jobs", data={"footage": str(f), "mode": "cops", "target_language": "en", "sell_s": "-1",
                                "sell_variants": "3"}, follow_redirects=False)
    job_id = res.headers["location"].rsplit("/", 1)[1]
    o = Job.load(tmp_path / "jobs", job_id).options
    assert o.cops and o.sell and o.target_language == "en" and o.sell_variants == 1 and not o.sell_auto
    assert "🚓 Cops US" in c.get(f"/jobs/{job_id}").text
    assert "Chưa chọn ngôn ngữ" in c.post("/jobs", data={"footage": str(f), "mode": "cops"}).text
    assert "dùng cho MỘT video" in c.post("/jobs", data={"footage": f"{f}\n{f}", "mode": "cops",
                                                          "target_language": "en"}).text
