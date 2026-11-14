"""Cắt đoạn hay theo chủ đề (chủ dự án yêu cầu 14/11): video dài → đoạn hay trọn ý → gom chủ đề AI tự đặt → chủ dự án
tick → mỗi chủ đề một video GIỮ NGUYÊN tiếng gốc, độ dài tự do."""

import json
from pathlib import Path

from app.director.fake import FakeDirector
from app.director.schemas import TopicList, TopicMoments
from app.director.topics import check_moments, check_topics, repair_moments
from app.jobs.job import JobOptions, Status
from tests.test_planner import _short_plan
from tests.test_runner import make_runner, prepare

FIX = Path(__file__).parent / "fixtures" / "director"
SEGS = [{"start": 1.0, "end": 3.0}, {"start": 3.2, "end": 19.6}]


def test_moments_snap_to_sentences_and_checks():
    r = TopicMoments.model_validate({"moments": [{"start": 1.6, "end": 20.5, "summary_vi": "x"}]})
    r, fixes = repair_moments(r, 0, 60, SEGS, 1.5)
    assert (r.moments[0].start, r.moments[0].end) == (1.0, 19.6) and fixes  # không cắt ngang câu
    bad = TopicMoments.model_validate({"moments": [{"start": 10, "end": 12, "summary_vi": "x"},
                                                   {"start": 11, "end": 30, "summary_vi": "y"}]})
    errs = check_moments(bad, 0, 60, 5)
    assert any("ngắn hơn 5" in e for e in errs) and any("chồng" in e for e in errs)


def test_topics_check_unique_moments():
    r = TopicList.model_validate({"topics": [{"title_vi": "A", "summary_vi": "a", "moments": [1, 2]},
                                             {"title_vi": "B", "summary_vi": "b", "moments": [2, 9]}]})
    errs = check_topics(r, 3)
    assert any("M2" in e and "MỘT chủ đề" in e for e in errs) and any("M9" in e for e in errs)


def test_full_topics_job(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(topics=True, client_id="k"))  # video tiếng Nhật, không chọn ngôn ngữ
    r = make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan()})
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "review_segments", job.message
    data = json.loads((jobs / "j1" / "plan" / "segments.json").read_text(encoding="utf-8"))
    topics = data["proposal"]["topics"]
    assert [t["title_vi"] for t in topics] == ["Đi Nhật lần đầu", "Mẹo đổi tiền"]
    assert [(m["start"], m["end"]) for m in topics[0]["moments"]] == [(45, 58), (1.0, 20)]  # thứ tự AI chọn, snap đầu câu

    r.apply_topics(job, [1])  # chỉ làm chủ đề 1
    job = r.resume(job)
    assert job.status == Status.done, job.message
    tasks = [c["task"] for c in r.director.calls]
    assert tasks.count("topics_moments") == 1 and "plan" not in tasks and "captions" not in tasks
    plan = json.loads((jobs / "j1" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    assert [(c["source_start"], c["source_end"], c["speed"]) for c in plan["clips"]] == [(45, 58, 1.0), (1.0, 20, 1.0)]
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    vids = {m["id"]: m for m in content["materials"]["videos"]}
    segs = [s for t in content["tracks"] if t["type"] == "video" for s in t["segments"]
            if vids.get(s["material_id"], {}).get("type") == "video"]
    assert segs[0]["source_timerange"]["start"] == 45_000_000 and all(s["volume"] > 0 for s in segs)  # tiếng gốc
    assert not [a for a in content["materials"]["audios"] if "music" in (a.get("type") or "")]  # không nhạc mới
    txt = (jobs / "j1" / "deliver" / "chu_de.txt").read_text(encoding="utf-8")
    assert "Đi Nhật lần đầu" in txt and "0:45–0:58" in txt


def test_redo_topics_keeps_moments(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(topics=True, client_id="k"))
    r = make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan()})
    job = r.run(job)
    r.redo_topics(job, "gộp hết làm một")
    job = r.run(job)
    assert job.step == "review_segments"
    tasks = [c["task"] for c in r.director.calls]
    assert tasks.count("topics_moments") == 1 and tasks.count("topics_group") == 2  # không xem lại video
    assert "gộp hết làm một" in r.director.calls[-1]["prompt"]


def test_home_topics_mode(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    c = TestClient(app)
    assert "name='mode' value='topics'" in c.get("/").text
    res = c.post("/jobs", data={"footage": str(f), "mode": "topics", "target_language": "ko", "hook": "on"},
                 follow_redirects=False)
    job_id = res.headers["location"].rsplit("/", 1)[1]
    job = Job.load(tmp_path / "jobs", job_id)
    assert job.options.topics and not job.options.target_language and not job.options.hook and job.options.split is False
    assert "🎯 Cắt đoạn hay theo chủ đề" in c.get(f"/jobs/{job_id}").text
    two = c.post("/jobs", data={"footage": f"{f}\n{f}", "mode": "topics"}).text
    assert "dùng cho MỘT video" in two


def test_topics_panel_on_job_page(tmp_path):
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    jobs, job = prepare(tmp_path, JobOptions(topics=True, client_id="k"))
    r = make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan()})
    r.run(job)
    app = create_app(jobs, lambda root, log: None)
    picked = []
    app.state.worker.start = lambda job_id, action=None: picked.append(action) or True
    c = TestClient(app)
    page = c.get("/jobs/j1").text
    assert "Chọn chủ đề muốn cắt" in page and "Đi Nhật lần đầu" in page and "0:45–0:58" in page
    c.post("/jobs/j1/topics", data={"pick_2": "on"})
    assert picked
