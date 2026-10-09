"""Chế độ Review phim / hoạt hình (chủ dự án yêu cầu 09/10): tìm đoạn hay, mỗi đoạn một video 60–90s có lời review."""

import json
from pathlib import Path

from app import config
from app.director.fake import FakeDirector
from app.director.schemas import DubScript, EditPlan
from app.director.tasks import check_rewrite, make_dub, make_plan, make_segments, understand
from app.jobs.job import Job, JobOptions, Status
from tests.test_director import make_analysis
from tests.test_planner import SAMPLE, load
from tests.test_runner import make_runner


def _clips(start: float, n: int, length: float = 11.0, gap: float = 1.0):
    return [{"source_start": start + k * (length + gap), "source_end": start + k * (length + gap) + length}
            for k in range(n)]


def _plan(index: int, clips: list[dict]) -> dict:
    from app.capcut_writer import DraftTemplate

    base = {**load("plan.json"), "emphasis": [], "zooms": [], "sfx": [], "effects": [], "stickers": [],
            "transitions": [], "arrows": [], "video_index": index, "clips": clips,
            "zooms": [{"source_start": c["source_start"] + 2, "source_end": c["source_start"] + 4, "kind": "punch"}
                      for c in clips[::2]]}
    base["filter"] = next(i.name for i in DraftTemplate(SAMPLE).library if i.kind == "filter")
    return base


def _review(index: int, clips: list[dict]) -> dict:
    """Lời review phủ ~90% mỗi clip: 2 câu 5 giây / clip 11 giây."""
    lines = []
    for c in clips:
        a = c["source_start"]
        lines += [{"source_start": a + 0.2, "source_end": a + 5.2, "text": "이 장면 진짜 웃겨요.", "text_vi": "Cảnh này hài thật.",
                   "kind": "narration"},
                  {"source_start": a + 5.5, "source_end": a + 10.5, "text": "표정 좀 보세요.", "text_vi": "Nhìn mặt kìa.",
                   "kind": "narration"}]
    return {"video_index": index, "lines": lines, "editor_notes": "kể lại + bình luận"}


def test_review_segments_prompt_and_limits(tmp_path):
    a = make_analysis(tmp_path, duration=200.0)
    u = understand(FakeDirector(), a)
    d = FakeDirector()
    make_segments(d, a, u, review=True)
    prompt = d.calls[0]["prompt"]
    assert "REVIEW PHIM" in prompt and "60–90 giây" in prompt
    assert "NHIỀU video" in prompt and len(d.calls[0]["images"]) >= 10  # xem khung hình để tìm đoạn hay
    d2 = FakeDirector()
    make_segments(d2, a, u)
    assert "REVIEW PHIM" not in d2.calls[0]["prompt"] and not d2.calls[0]["images"]


def test_review_plan_60_to_90s_and_short_clips(tmp_path):
    a = make_analysis(tmp_path, duration=200.0)
    u = understand(FakeDirector(), a)
    u = u.model_copy(update={"usable_range": u.usable_range.model_copy(update={"start": 0.0, "end": 200.0})})
    style = {"review": config.load("review")}
    too_long = _plan(1, _clips(1.0, 9))                                        # 99 giây > 90
    long_clip = _plan(1, [{"source_start": 1.0, "source_end": 30.0}, *_clips(31.0, 4)])  # clip 29 giây
    good = _plan(1, _clips(1.0, 6))                                            # 66 giây
    d = FakeDirector(responses={"plan": [too_long, long_clip, good]})
    plan = make_plan(d, a, u, style)
    assert len(d.calls) == 3 and len(plan.clips) == 6
    assert "REVIEW PHIM" in d.calls[0]["prompt"]
    assert "vượt 90s" in d.calls[1]["prompt"] and "dài quá 12s" in d.calls[2]["prompt"]


def test_review_dub_prompt_and_cover(tmp_path):
    a = make_analysis(tmp_path, duration=200.0)
    u = understand(FakeDirector(), a).dubbed_to("ko")
    clips = _clips(1.0, 6)
    plan = EditPlan.model_validate(_plan(1, clips))
    d = FakeDirector(responses={"dub_review": _review(1, clips)})
    s = make_dub(d, a, u, plan, mode="review")
    call = d.calls[-1]
    assert call["task"] == "dub_review" and "LỜI REVIEW" in call["prompt"] and call["images"]
    assert len(s.lines) == 12
    sparse = DubScript.model_validate({**_review(1, clips), "lines": _review(1, clips)["lines"][:3]})
    assert any("chỉ phủ" in e for e in check_rewrite(sparse, plan, {}, config.load("review")))
    assert check_rewrite(s, plan, {}, config.load("review")) == []


def test_review_job_end_to_end(tmp_path):
    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/phim.mp4")], JobOptions(review=True, target_language="ko"), job_id="rv")
    make_analysis(jobs / "rv", duration=200.0)
    r = make_runner(tmp_path, jobs)
    u = load("understand.json")
    u["usable_range"] = {"start": 0.0, "end": 200.0}
    c1, c2 = _clips(1.0, 6), _clips(76.0, 6)
    r._director = FakeDirector(responses={"understand": u, "plan": [_plan(1, c1), _plan(2, c2)],
                                          "dub_review": [_review(1, c1), _review(2, c2)],
                                          "captions": [load("captions.json"), {**load("captions.json"), "video_index": 2}]})
    job = r.run(job)
    assert job.step == "review_segments" and job.status == Status.waiting, job.message  # duyệt các đoạn hay
    r.apply_segments(job, json.loads((jobs / "rv" / "plan" / "segments.json").read_text(encoding="utf-8"))["videos"])
    job = r.resume(job)
    assert job.step == "dub_voice" and job.status == Status.waiting, job.message
    assert {c["task"] for c in r._director.calls} >= {"segment", "plan", "dub_review"}
    style = r._style(job)
    assert style["review"] and style["original_audio"]["mute"] is False and "hype" not in style
    # tiếng phim chỉ hạ nhỏ (không tắt hẳn) dưới lời review
    job.data["dub_skip"] = True
    job = r.resume(job)
    assert job.status == Status.done, job.message
    content = (Path(job.data["drafts"][0]["draft"]) / "draft_content.json").read_text(encoding="utf-8")
    assert "이 장면 진짜 웃겨요" in content
    assert len(job.data["drafts"]) == 2


def test_review_job_same_language_still_writes_review(tmp_path):
    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/anime.mp4")], JobOptions(review=True), job_id="rs")
    r = make_runner(tmp_path, jobs)
    job.data["dub_same"] = True
    assert r._dubbing(job) and job.applies("dub") and job.applies("review_segments")
    assert not Job.create(jobs, [Path("a.mp4")], JobOptions(), job_id="x").applies("review_segments")


def test_web_form_review(tmp_path):
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    client = TestClient(app)
    assert "Review phim / hoạt hình" in client.get("/").text
    r = client.post("/jobs", data={"footage": str(f), "review": "on", "hype": "on", "target_language": "en"},
                    follow_redirects=False)
    job = Job.load(tmp_path / "jobs", r.headers["location"].rsplit("/", 1)[1])
    assert job.options.review and not job.options.hype and job.options.target_language == "en"
    bad = client.post("/jobs", data={"footage": str(f), "review": "on", "vi_sub": "on"})
    assert "Chọn một chế độ thôi" in bad.text
