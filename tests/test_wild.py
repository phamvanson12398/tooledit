"""Thế giới động vật (chủ dự án yêu cầu 20/10): giữ ĐỦ cảnh, AI chỉ đảo thứ tự + lời dẫn nói rồi nghỉ, giữ tiếng nền."""

import json
from pathlib import Path

from app.director.fake import FakeDirector
from app.director.schemas import WildScript
from app.director.wild import check_wild, order_diff, units
from app.jobs.job import JobOptions, Status
from tests.test_planner import _short_plan
from tests.test_runner import make_runner as _make_runner, prepare

FIX = json.loads((Path(__file__).parent / "fixtures" / "director" / "wild.json").read_text(encoding="utf-8"))
US = [{"id": 1, "start": 0.0, "end": 20.0}, {"id": 2, "start": 20.0, "end": 40.0}, {"id": 3, "start": 40.0, "end": 60.0}]
CFG = {"min_pause_s": 2.0, "max_talk_share": 0.55, "min_talk_share": 0.2, "max_line_s": 9, "first_line_s": 5}
PARTS = [{"index": 0, "start": 0, "end": 20}, {"index": 1, "start": 20, "end": 40}, {"index": 2, "start": 40, "end": 60}]


def _check(data):
    return check_wild(WildScript.model_validate(data), "ko", us=US, cps=7.0, cfg=CFG)


def test_units_split_at_files_and_merge_tiny():
    us = units([{"start": 0, "end": 12}, {"start": 12, "end": 12.2}, {"start": 12.2, "end": 30}], 30.0,
               [{"start": 0}, {"start": 20}], min_s=0.5)
    assert [(u["start"], u["end"]) for u in us] == [(0, 12.2), (12.2, 20), (20, 30)]  # cắt ở chỗ nối file, gộp cảnh vụn


def test_check_wild():
    assert _check(FIX) == []
    assert any("ĐỦ mọi cảnh" in e and "thiếu C2" in e for e in _check({**FIX, "order": [3, 1]}))  # không được bỏ cảnh
    same = {**FIX, "order": [1, 2, 3], "lines": [FIX["lines"][2], FIX["lines"][3], FIX["lines"][0], FIX["lines"][1]]}
    assert any("THEO KỊCH BẢN MỚI" in e for e in _check(same))  # giữ thứ tự cũ → bắt xếp cảnh theo kịch bản mới
    assert order_diff([3, 1, 2], US) == 0.5 and order_diff([3, 2, 1], US) == 1.0
    close = {**FIX, "lines": FIX["lines"][:1] + [{**FIX["lines"][1], "start": 46, "end": 50}] + FIX["lines"][2:]}
    assert any("nghỉ ít nhất 2s" in e for e in _check(close))  # nói rồi phải nghỉ
    late = {**FIX, "lines": FIX["lines"][1:]}
    assert any("5 giây đầu" in e for e in _check(late))
    chatty = {**FIX, "lines": [{"scene": 3, "start": 40 + 10 * k, "end": 40 + 10 * k + 7.5, "text": "사자", "text_vi": "x"}
                               for k in range(2)] + [{"scene": 1, "start": 10 * k, "end": 10 * k + 7.5, "text": "사자",
                                                      "text_vi": "x"} for k in range(2)]
              + [{"scene": 2, "start": 20 + 10 * k, "end": 20 + 10 * k + 7.5, "text": "사자", "text_vi": "x"}
                 for k in range(2)]}
    assert any("tối đa 55%" in e for e in _check(chatty))


def test_full_wild_job(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(wild=True, target_language="ko", client_id="k"))
    job.data["montage_parts"] = PARTS  # như khi thả 3 file ngắn
    job.save(jobs)
    r = _make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan()})
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "dub_voice", job.message
    tasks = [c["task"] for c in r.director.calls]
    assert "wild" in tasks and "plan" not in tasks
    plan = json.loads((jobs / "j1" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    assert [(c["source_start"], c["source_end"]) for c in plan["clips"]] == [(40, 60), (0, 20), (20, 40)]  # đủ cảnh
    dub = json.loads((jobs / "j1" / "plan" / "dub_video01.json").read_text(encoding="utf-8"))
    assert len(dub["lines"]) == 4 and all(ln["kind"] == "narration" for ln in dub["lines"])
    for n in range(1, 5):
        (jobs / "j1" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    vids = {m["id"]: m for m in content["materials"]["videos"]}
    segs = [s for t in content["tracks"] if t["type"] == "video" for s in t["segments"]
            if vids.get(s["material_id"], {}).get("type") == "video"]
    assert segs[0]["source_timerange"]["start"] == 40_000_000
    assert abs(sum(s["target_timerange"]["duration"] for s in segs) - 60_000_000) < 100_000  # không bớt giây nào
    assert all(s["volume"] > 0 for s in segs)  # không có giọng gốc (chưa cài Demucs) → giữ tiếng nền gốc
    texts = [m.get("content", "") for m in content["materials"]["texts"]]
    assert any("사자" in t for t in texts)  # phụ đề lời dẫn
    au = {m["id"]: m.get("name", "") for m in content["materials"]["audios"]}
    starts = sorted(s["target_timerange"]["start"] / 1e6 for t in content["tracks"] if t["type"] == "audio"
                    for s in t["segments"] if "video01_dub" in au.get(s["material_id"], ""))
    assert starts == [1.0, 12.0, 23.0, 45.0]  # voice theo vị trí cảnh trên video mới, có khoảng nghỉ


def test_home_wild_mode(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    files = []
    for i in range(2):
        f = tmp_path / f"v{i}.mp4"
        f.write_bytes(b"x")
        files.append(str(f))
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    c = TestClient(app)
    assert "name='mode' value='wild'" in c.get("/").text
    res = c.post("/jobs", data={"footage": "\n".join(files), "mode": "wild", "target_language": "ko", "hook": "on",
                                "split": "on"}, follow_redirects=False)
    job_id = res.headers["location"].rsplit("/", 1)[1]
    job = Job.load(tmp_path / "jobs", job_id)
    assert job.options.wild and len(job.footage) == 2 and not job.options.hook and not job.options.split
    assert "🦁 Thế giới động vật" in c.get(f"/jobs/{job_id}").text
    assert "Chưa chọn ngôn ngữ" in c.post("/jobs", data={"footage": files[0], "mode": "wild"}).text
