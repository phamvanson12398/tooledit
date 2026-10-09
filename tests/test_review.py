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


def _clips(start: float, n: int, length: float = 2.5, gap: float = 0.2):
    """Cảnh ngắn 2.5 giây như video mẫu chủ dự án gửi (chuyển cảnh rất nhanh)."""
    return [{"source_start": start + k * (length + gap), "source_end": start + k * (length + gap) + length}
            for k in range(n)]


def _plan(index: int, clips: list[dict]) -> dict:
    from app.capcut_writer import DraftTemplate

    base = {**load("plan.json"), "emphasis": [], "zooms": [], "sfx": [], "effects": [], "stickers": [],
            "transitions": [], "arrows": [], "video_index": index, "clips": clips,
            "zooms": [{"source_start": c["source_start"] + 0.5, "source_end": c["source_start"] + 2, "kind": "punch"}
                      for c in clips[::2]]}
    base["filter"] = next(i.name for i in DraftTemplate(SAMPLE).library if i.kind == "filter")
    return base


def _review(index: int, clips: list[dict]) -> dict:
    """Lời review phủ ~90%: mỗi câu chạy liền qua 2 cảnh (cảnh chuyển nhanh, giọng kể không ngắt)."""
    lines = []
    for k in range(0, len(clips), 2):
        a = clips[k]["source_start"] + 0.1
        b = clips[k + 1]["source_end"] - 0.4 if k + 1 < len(clips) else clips[k]["source_end"] - 0.2
        text, vi = (("이 장면 진짜 웃겨요.", "Cảnh này hài thật.") if k % 4 == 0 else ("그런데 그때였죠.", "Nhưng đúng lúc đó."))
        lines.append({"source_start": round(a, 2), "source_end": round(b, 2), "text": text, "text_vi": vi,
                      "kind": "narration"})
    return {"video_index": index, "lines": lines, "editor_notes": "kể lại + bình luận",
            "story_vi": "Mở đầu: cậu bé mất con mèo. Mâu thuẫn: cả làng không ai giúp. Cao trào: cậu tự đi tìm trong rừng. "
                        "Kết: con mèo tự quay về."}


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
    too_long = _plan(1, _clips(1.0, 37))                                       # 92.5 giây > 90
    long_clip = _plan(1, [{"source_start": 1.0, "source_end": 9.5}, *_clips(10.0, 24)])  # một cảnh 8.5 giây
    good = _plan(1, _clips(1.0, 26))                                           # 65 giây, cảnh 2.5 giây
    d = FakeDirector(responses={"plan": [too_long, long_clip, good]})
    plan = make_plan(d, a, u, style)
    assert len(d.calls) == 3 and len(plan.clips) == 26
    assert "REVIEW PHIM" in d.calls[0]["prompt"] and "CHUYỂN CẢNH RẤT NHANH" in d.calls[0]["prompt"]
    assert "vượt 90s" in d.calls[1]["prompt"] and "dài quá 6s" in d.calls[2]["prompt"]
    # cảnh nào cũng 5 giây (không cảnh nào quá 6s) nhưng nhịp chậm → bị yêu cầu chuyển cảnh nhanh hơn
    slow = _plan(1, _clips(1.0, 14, length=5.0))
    d2 = FakeDirector(responses={"plan": [slow, good]})
    make_plan(d2, a, u, style)
    assert len(d2.calls) == 2 and "chuyển cảnh nhanh hơn" in d2.calls[1]["prompt"]


def test_review_dub_prompt_and_cover(tmp_path):
    a = make_analysis(tmp_path, duration=200.0)
    u = understand(FakeDirector(), a).dubbed_to("ko")
    clips = _clips(1.0, 26)
    plan = EditPlan.model_validate(_plan(1, clips))
    d = FakeDirector(responses={"dub_review": _review(1, clips)})
    s = make_dub(d, a, u, plan, mode="review")
    call = d.calls[-1]
    assert len(d.calls) == 1, d.calls[-1]["prompt"][-800:]
    assert call["task"] == "dub_review" and "MỘT CÂU CHUYỆN" in call["prompt"] and call["images"]
    assert "CHẠY LIỀN QUA NHIỀU CẢNH" in call["prompt"] and "~습니다" in call["prompt"]
    assert len(s.lines) == 13  # mỗi câu chạy qua 2 cảnh — không bị cắt về một cảnh
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
    c1, c2 = _clips(1.0, 25), _clips(76.0, 25)
    r._director = FakeDirector(responses={"understand": u, "plan": [_plan(1, c1), _plan(2, c2)],
                                          "dub_review": [_review(1, c1), _review(2, c2)],
                                          "captions": [load("captions.json"), {**load("captions.json"), "video_index": 2}]})
    job = r.run(job)
    assert job.step == "review_segments" and job.status == Status.waiting, job.message  # duyệt các đoạn hay
    r.apply_segments(job, json.loads((jobs / "rv" / "plan" / "segments.json").read_text(encoding="utf-8"))["videos"])
    job = r.resume(job)
    assert job.step == "dub_voice" and job.status == Status.waiting, job.message
    assert {c["task"] for c in r._director.calls} >= {"segment", "plan", "dub_review"}
    assert "📖 Câu chuyện: Mở đầu" in (jobs / "rv" / "dub_scripts.txt").read_text(encoding="utf-8")
    style = r._style(job)
    assert style["review"] and style["original_audio"]["mute"] is False and "hype" not in style
    assert style["layout"] == "review_story" and style["block_ratio"] == "9:10"  # bố cục như video mẫu
    # tiếng phim chỉ hạ nhỏ (không tắt hẳn) dưới lời review
    job.data["dub_skip"] = True
    job = r.resume(job)
    assert job.status == Status.done, job.message
    content = (Path(job.data["drafts"][0]["draft"]) / "draft_content.json").read_text(encoding="utf-8")
    assert "이 장면 진짜" in content and "이 장면 진짜 웃겨요." not in content  # phụ đề cụm ngắn (≤ 10 ký tự) như video mẫu
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


def test_review_must_be_a_story_not_scene_description(tmp_path):
    """Chủ dự án (09/10): review phải thành MỘT CÂU CHUYỆN, không thuật lại "người này đang làm gì"."""
    from app.director.tasks import check_story

    clips = _clips(1.0, 26)
    rcfg = config.load("review")
    good = DubScript.model_validate(_review(1, clips))
    assert check_story(good, rcfg) == []
    no_story = DubScript.model_validate({**_review(1, clips), "story_vi": ""})
    assert any("story_vi" in e for e in check_story(no_story, rcfg))
    data = _review(1, clips)
    for ln in data["lines"][:8]:
        ln["text_vi"] = "Cậu bé đang chạy, con mèo đang nhìn."
    errs = check_story(DubScript.model_validate(data), rcfg)
    assert any("TẢ CẢNH" in e for e in errs)

    # AI tả cảnh lần đầu → bị yêu cầu viết lại thành câu chuyện
    a = make_analysis(tmp_path, duration=200.0)
    u = understand(FakeDirector(), a).dubbed_to("ko")
    plan = EditPlan.model_validate(_plan(1, clips))
    d = FakeDirector(responses={"dub_review": [data, _review(1, clips)]})
    make_dub(d, a, u, plan, mode="review")
    assert len(d.calls) == 2 and "KỂ THÀNH CÂU CHUYỆN" in d.calls[1]["prompt"]
    assert "KỂ CHUYỆN, không phải thuyết minh" in d.calls[0]["prompt"]
    assert "Cả đời cậu bé chỉ mong một điều" in d.calls[0]["prompt"] and "소년의 소원은" in d.calls[0]["prompt"]
