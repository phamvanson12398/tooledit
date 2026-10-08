"""Chế độ Phụ đề tiếng Việt: dịch lời video nước ngoài để xem hiểu (chủ dự án yêu cầu 08/10)."""

import json
from pathlib import Path

from app.director.fake import FakeDirector
from app.planner import visub


def _segs(n):
    return [{"start": 2.0 * k, "end": 2.0 * k + 1.8, "text": f"line {k + 1}"} for k in range(n)]


def test_translate_in_batches_with_context():
    segs = _segs(5)
    d = FakeDirector(responses={"subtitle_vi": [
        {"lines": [{"i": 1, "vi": "một"}, {"i": 2, "vi": "hai"}]},          # lô 1 thiếu câu 3 → bị yêu cầu làm lại
        {"lines": [{"i": 1, "vi": "một"}, {"i": 2, "vi": "hai"}, {"i": 3, "vi": "ba"}]},
        {"lines": [{"i": 4, "vi": "bốn"}, {"i": 5, "vi": "năm"}]}]})
    vi = visub.translate(d, segs, "ko", batch=3)
    assert vi == ["một", "hai", "ba", "bốn", "năm"]
    tasks = [c for c in d.calls if c["task"] == "subtitle_vi"]
    assert len(tasks) == 3 and "thiếu câu dịch cho số 3" in tasks[1]["prompt"]
    assert "[4] (00:06.0) line 4" in tasks[0]["prompt"]  # câu sau lô làm bối cảnh
    assert "[3] (00:04.0) line 3" in tasks[2]["prompt"]  # câu trước lô làm bối cảnh


def test_cues_srt_and_position():
    segs = [{"start": 1.0, "end": 3.0, "text": "a"}, {"start": 4.0, "end": 12.0, "text": "b"}]
    long_vi = "Đây là một câu tiếng Việt khá dài, cần chia thành nhiều dòng phụ đề cho dễ đọc nhé các bạn ơi"
    cl = visub.cues(segs, ["Xin chào.", long_vi])
    assert cl[0] == (1_000_000, 3_000_000, "Xin chào.") and len(cl) >= 3
    assert all(len(t) <= 42 for _, _, t in cl) and cl[-1][1] == 12_000_000
    out = visub.srt(cl[:1])
    assert out.startswith("1\n00:00:01,000 --> 00:00:03,000\nXin chào.\n")
    assert visub.subtitle_y(1920, 1080) < -0.3 and visub.subtitle_y(1080, 1920) == -0.55


def test_vi_sub_job_end_to_end(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import JobOptions, Status
    from app.web.server import create_app
    from tests.test_runner import make_runner, prepare

    jobs, job = prepare(tmp_path, JobOptions(vi_sub=True))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.done, job.message
    called = [c["task"] for c in r.director.calls]
    assert called == ["subtitle_vi"]  # không hỏi AI hiểu nội dung / kế hoạch dựng / caption — chỉ dịch
    srt = Path(job.data["srt"])
    assert "Xin chào mọi người." in srt.read_text(encoding="utf-8-sig")
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    texts = [json.loads(m["content"])["text"] for m in content["materials"]["texts"]]
    assert texts == ["Xin chào mọi người."]
    vids = [s for t in content["tracks"] if t["type"] == "video" for s in t["segments"]]
    assert len(vids) == 1 and vids[0]["volume"] == 1.0 and vids[0]["target_timerange"]["duration"] == 60_000_000

    client = TestClient(create_app(jobs, lambda root, log: r))
    page = client.get("/jobs/j1").text
    assert "Tải file .srt" in page
    dl = client.get("/jobs/j1/srt")
    assert dl.status_code == 200 and "Xin chào" in dl.content.decode("utf-8-sig")


def test_web_form_vi_sub(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    client = TestClient(app)
    assert "Chỉ phụ đề tiếng Việt" in client.get("/").text
    r = client.post("/jobs", data={"footage": str(f), "vi_sub": "on"}, follow_redirects=False)
    job = Job.load(tmp_path / "jobs", r.headers["location"].rsplit("/", 1)[1])
    assert job.options.vi_sub and not job.applies("understand") and job.applies("write")
