"""Bán content YouTube (chủ dự án yêu cầu 19/10): video nguồn dài → video YouTube chia chương, gói đăng YouTube."""

import json
from pathlib import Path

import pytest

from app.director import youtube
from app.director.fake import FakeDirector
from app.director.policy import find_forbidden
from app.director.schemas import YtOutline
from app.jobs.job import JobOptions, Status
from tests.test_planner import _short_plan
from tests.test_runner import make_runner as _make_runner, prepare

FIX = Path(__file__).parent / "fixtures" / "director"
N = len(json.loads((FIX / "yt_chapter.json").read_text(encoding="utf-8"))["lines"])


@pytest.fixture
def small_yt(monkeypatch):
    """Video thử chỉ 60 giây → cho AI tự chọn thời lượng ngắn (thật thì 5–20 phút)."""
    real = youtube.yt_cfg()
    monkeypatch.setattr(youtube, "yt_cfg", lambda: {**real, "auto_min": [0.5, 20], "min_chapter_s": 10})


def make_runner(tmp_path, jobs, **kw):
    r = _make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan()})
    return r


def _calls(r, task):
    return [c for c in r.director.calls if c["task"] == task]


def test_normalize_fits_chosen_minutes():
    o = YtOutline.model_validate_json((FIX / "yt_outline.json").read_text(encoding="utf-8"))
    n = youtube.normalize(o, 10, {"min_chapter_s": 45, "max_chapter_s": 400})
    assert abs(sum(c.seconds for c in n.chapters) - 600) < 1 and n.target_min == 10
    capped = youtube.normalize(o, 20, {"min_chapter_s": 45, "max_chapter_s": 240})
    assert all(c.seconds <= 240 for c in capped.chapters)  # 2 chương không đủ chứa 20 phút → kẹp ở max
    auto = youtube.normalize(o, 0, {"auto_min": [5, 20], "min_chapter_s": 45, "max_chapter_s": 240})
    assert abs(sum(c.seconds for c in auto.chapters) - 300) < 1  # AI đề xuất 1 phút → kẹp lên 5 phút


def test_youtube_platform_words():
    assert find_forbidden("구독과 좋아요 부탁드려요", "ko") != []  # TikTok: cấm
    assert find_forbidden("구독과 좋아요 부탁드려요", "ko", platform="youtube") == []  # YouTube: được
    assert find_forbidden("틱톡에서 봐요", "ko", platform="youtube") == ["틱톡"]


def test_package_text_has_chapter_timestamps():
    o = YtOutline.model_validate_json((FIX / "yt_outline.json").read_text(encoding="utf-8"))
    t = youtube.package_text(o, [(0.4, "완판의 시작"), (95.0, "비밀의 국물"), (3725.0, "끝")])
    assert "00:00 완판의 시작" in t and "01:35 비밀의 국물" in t and "1:02:05 끝" in t
    assert "하루 만에 완판된 라멘집의 비밀" in t and "라멘, 맛집" in t


def test_full_youtube_job(tmp_path, small_yt):
    jobs, job = prepare(tmp_path, JobOptions(sell=True, yt=True, target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "dub_voice", job.message  # không tick dừng → chạy thẳng
    assert len(_calls(r, "yt_outline")) == 1 and len(_calls(r, "yt_chapter")) == 2
    prompts = sorted(c["prompt"] for c in _calls(r, "yt_chapter"))
    assert any("chương 1/2" in p and "MỞ ĐẦU" in p for p in prompts)
    assert any("chương 2/2" in p and "CUỐI" in p for p in prompts)
    plan = jobs / "j1" / "plan"
    merged = json.loads((plan / "sell_video01.json").read_text(encoding="utf-8"))
    assert len(merged["lines"]) == 2 * N and merged["lines"][N]["role"] == "body"  # chương 2 không mở bằng hook
    chapters = json.loads((plan / "yt_chapters_video01.json").read_text(encoding="utf-8"))
    assert [c["first_line"] for c in chapters] == [0, N]
    for n in range(1, 2 * N + 1):
        (jobs / "j1" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    pkg = (jobs / "j1" / "deliver" / "youtube_video01.txt").read_text(encoding="utf-8")
    assert "00:00 완판의 시작" in pkg and "비밀의 국물" in pkg and "=== TAG ===" in pkg
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    assert any("비밀의 국물" in m.get("content", "") for m in content["materials"]["texts"])  # tên chương trên màn hình
    assert not _calls(r, "captions")  # gói YouTube viết cùng dàn ý, không hỏi AI caption TikTok


def test_pause_review_and_redo_outline(tmp_path, small_yt):
    jobs, job = prepare(tmp_path, JobOptions(sell=True, yt=True, yt_pause=True, target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "review_segments" and "dàn ý" in job.message
    r.redo_yt_outline(job, "thêm chương về giá cả")
    job = r.run(job)
    assert job.step == "review_segments" and len(_calls(r, "yt_outline")) == 2
    assert len(_calls(r, "ideas_catalog")) == 1  # danh mục cảnh giữ nguyên
    assert "thêm chương về giá cả" in _calls(r, "yt_outline")[1]["prompt"]
    r.apply_yt_outline(job)
    job = r.resume(job)
    assert job.step == "dub_voice", job.message


def test_source_too_long(tmp_path):
    from app.jobs.runner import Runner

    jobs, job = prepare(tmp_path, JobOptions(sell=True, yt=True, target_language="ko", client_id="k"))
    (jobs / "j1" / "analysis" / "frames.json").unlink()
    r = Runner(jobs, director=FakeDirector(), analyze_fn=lambda *a, **k: None,
               probe_duration_fn=lambda p: 100 * 60 * 1_000_000, log=lambda m: None)
    job = r.run(job)
    assert job.status == Status.error and "dưới 90 phút" in job.message


def test_home_youtube_mode(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    c = TestClient(app)
    home = c.get("/").text
    assert "name='mode' value='yt'" in home and "AI tự chọn theo nội dung" in home and "yt_pause" in home
    res = c.post("/jobs", data={"footage": str(f), "mode": "yt", "target_language": "de", "yt_min": "15",
                                "yt_pause": "on", "sell_variants": "3"}, follow_redirects=False)
    job_id = res.headers["location"].rsplit("/", 1)[1]
    o = Job.load(tmp_path / "jobs", job_id).options
    assert o.yt and o.sell and o.yt_min == 15 and o.yt_pause and o.sell_variants == 1 and o.target_language == "de"
    page = c.get(f"/jobs/{job_id}").text
    assert "▶️ Bán content YouTube" in page and "15 phút" in page
    # trang duyệt dàn ý
    jobs = tmp_path / "jobs"
    (jobs / job_id / "plan").mkdir(parents=True, exist_ok=True)
    (jobs / job_id / "plan" / "yt_outline.json").write_text((FIX / "yt_outline.json").read_text(encoding="utf-8"),
                                                            encoding="utf-8")
    (jobs / job_id / "plan" / "segments.json").write_text(json.dumps({"yt": True, "videos": [], "confirmed": False}),
                                                          encoding="utf-8")
    job = Job.load(jobs, job_id)
    job.step, job.status = "review_segments", Status.waiting
    job.save(jobs)
    page = c.get(f"/jobs/{job_id}").text
    assert "Duyệt dàn ý video YouTube" in page and "yt-approve" in page and "비밀의 국물" in page
