"""Chế độ Review phim / hoạt hình (chủ dự án yêu cầu 09/10): tìm đoạn hay, mỗi đoạn một video 2:10–2:30 có lời review."""

import json
from pathlib import Path

from app import config
from app.director.fake import FakeDirector
from app.director.schemas import DubScript, EditPlan
from app.director.base import DirectorError
from app.director.tasks import check_review_script, make_dub, make_plan, make_segments, understand
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


def test_review_segments_prompt_and_limits(tmp_path):
    a = make_analysis(tmp_path, duration=200.0)
    u = understand(FakeDirector(), a)
    d = FakeDirector()
    make_segments(d, a, u, review=True)
    prompt = d.calls[0]["prompt"]
    rc = config.load("review")
    assert "REVIEW PHIM" in prompt and f"{rc['min_video_s']}–{rc['max_video_s']} giây" in prompt
    assert "NHIỀU video" in prompt and len(d.calls[0]["images"]) >= 10  # xem khung hình để tìm đoạn hay
    d2 = FakeDirector()
    make_segments(d2, a, u)
    assert "REVIEW PHIM" not in d2.calls[0]["prompt"] and not d2.calls[0]["images"]


def test_review_plan_length_and_short_clips(tmp_path):
    a = make_analysis(tmp_path, duration=400.0)
    u = understand(FakeDirector(), a)
    u = u.model_copy(update={"usable_range": u.usable_range.model_copy(update={"start": 0.0, "end": 400.0})})
    style = {"review": config.load("review")}
    too_long = _plan(1, _clips(1.0, 61))                                       # 152.5 giây > 150
    long_clip = _plan(1, [{"source_start": 1.0, "source_end": 9.5}, *_clips(10.0, 50)])  # một cảnh 8.5 giây
    good = _plan(1, _clips(1.0, 56))                                           # 140 giây (~2:20), cảnh 2.5 giây
    d = FakeDirector(responses={"plan": [too_long, long_clip, good]})
    plan = make_plan(d, a, u, style)
    assert len(d.calls) == 3 and len(plan.clips) == 56
    assert "REVIEW PHIM" in d.calls[0]["prompt"] and "CHUYỂN CẢNH RẤT NHANH" in d.calls[0]["prompt"]
    assert "vượt 150s" in d.calls[1]["prompt"] and "dài quá 6s" in d.calls[2]["prompt"]
    # cảnh nào cũng 5 giây (không cảnh nào quá 6s) nhưng nhịp chậm → bị yêu cầu chuyển cảnh nhanh hơn
    slow = _plan(1, _clips(1.0, 28, length=5.0))
    d2 = FakeDirector(responses={"plan": [slow, good]})
    make_plan(d2, a, u, style)
    assert len(d2.calls) == 2 and "chuyển cảnh nhanh hơn" in d2.calls[1]["prompt"]


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
    home = client.get("/").text
    assert "Review phim / hoạt hình" in home and "một video 2:10–2:30" in home and "1:00–1:30" not in home
    r = client.post("/jobs", data={"footage": str(f), "review": "on", "hype": "on", "target_language": "en"},
                    follow_redirects=False)
    job = Job.load(tmp_path / "jobs", r.headers["location"].rsplit("/", 1)[1])
    assert job.options.review and not job.options.hype and job.options.target_language == "en"
    bad = client.post("/jobs", data={"footage": str(f), "review": "on", "vi_sub": "on"})
    assert "Chọn một chế độ thôi" in bad.text


SENT = "이 장면 진짜 웃겨요. " + "그런데 그때 소년은 아무것도 몰랐습니다. " * 5  # 93 chữ ≈ 9.3 giây ở 10 chữ/giây


def _script(index: int, start: float, n: int = 15) -> dict:
    """Bài lời đọc viết TRƯỚC: 15 câu ~9.3 giây (≈ 140 giây), mỗi câu gắn 1 đoạn phim 10 giây, theo thứ tự."""
    lines = [{"source_start": round(start + k * 10.5, 2), "source_end": round(start + k * 10.5 + 10.0, 2),
              "text": SENT.strip(), "text_vi": "Cảnh này hài thật. Nhưng lúc đó cậu bé chẳng hay biết gì.",
              "action_vi": "cảnh trong phim", "kind": "narration"} for k in range(n)]
    return {"video_index": index, "lines": lines, "editor_notes": "kể lại + bình luận",
            "story_vi": "Mở đầu: cậu bé mất con mèo. Mâu thuẫn: cả làng không ai giúp. Cao trào: cậu tự đi tìm trong rừng. "
                        "Kết: con mèo tự quay về."}


def _u(a, lo=0.0, hi=200.0, lang="ko"):
    u = understand(FakeDirector(), a).dubbed_to(lang)
    return u.model_copy(update={"usable_range": u.usable_range.model_copy(update={"start": lo, "end": hi})})


def test_review_script_is_written_first(tmp_path):
    """Chủ dự án chốt 09/10: tool viết TRƯỚC một bài lời đọc liền mạch (không phụ thuộc cảnh đã chọn), xem hết khung hình."""
    a = make_analysis(tmp_path, duration=200.0)
    u = _u(a)
    d = FakeDirector(responses={"dub_review": _script(1, 1.0)})
    s = make_dub(d, a, u, plan=None, mode="review")
    call = d.calls[0]
    assert len(d.calls) == 1, call["prompt"][-600:]
    assert call["task"] == "dub_review" and "VIẾT TRƯỚC bài lời đọc" in call["prompt"]
    assert "Tiếng phim TẮT HẲN" in call["prompt"] and "~습니다" in call["prompt"] and "Cả đời cậu bé" in call["prompt"]
    assert "giây" in call["prompt"] and "chữ" in call["prompt"] and len(call["images"]) >= 10
    assert len(s.lines) == 15


def test_review_script_checks():
    from app.director.schemas import Understanding
    from tests.test_director import GOOD

    rcfg = config.load("review")
    from app.director.tasks import review_dub_cfg
    cfg = {**review_dub_cfg(config.load("dub")), "use_measured_rate": False}
    u = Understanding.model_validate(GOOD).dubbed_to("ko")
    u = u.model_copy(update={"usable_range": u.usable_range.model_copy(update={"start": 0.0, "end": 200.0})})
    assert check_review_script(DubScript.model_validate(_script(1, 1.0)), u, cfg, rcfg) == []
    short = DubScript.model_validate(_script(1, 1.0, n=6))                     # ~56 giây < 130
    assert any("viết THÊM" in e for e in check_review_script(short, u, cfg, rcfg))
    data = _script(1, 1.0)
    data["lines"][2]["source_end"] = data["lines"][2]["source_start"] + 3.0    # câu 9 giây mà phim chỉ 3 giây
    data["lines"][5]["source_start"] = data["lines"][4]["source_start"]        # chồng đoạn phim câu trước
    data["lines"][7]["source_end"] = 250.0                                     # ra ngoài đoạn phim của video
    errs = check_review_script(DubScript.model_validate(data), u, cfg, rcfg)
    assert any("đoạn phim chỉ 3.0s" in e for e in errs) and any("chồng" in e for e in errs)
    assert any("phải nằm trong" in e for e in errs)


def test_build_from_voice_cuts_scenes_to_voice():
    """Bạn đọc cả bài → tool cắt cảnh từ đoạn phim của từng câu, dài đúng bằng câu đọc, câu nối liền không khoảng im."""
    from app.planner.review_sync import build_from_voice
    from app.planner.timeline import TimeMap

    plan = EditPlan.model_validate(_plan(1, _clips(1.0, 56)))   # kế hoạch AI (tiêu đề, nhạc…) — cảnh sẽ do tool cắt lại
    script = DubScript.model_validate(_script(1, 1.0))
    voice = {i: 2.0 for i in range(1, 16)}
    voice[3] = 7.0
    p2, s2, notes = build_from_voice(plan, script, voice, scene_starts=[23.5, 24.0], cps=10.0, gap_s=0.1, cut_s=2.0)
    tmap = TimeMap(p2.clips)
    outs = [(tmap.to_out(ln.source_start), tmap.to_out(ln.source_end)) for ln in s2.lines]
    lens = [(b - a) / 1e6 for a, b in outs]
    assert abs(lens[0] - 2.1) < 0.02 and abs(lens[2] - 7.1) < 0.02            # cảnh dài đúng bằng voice (+ nghỉ 0.1s)
    assert all(abs(outs[k + 1][0] - outs[k][1]) < 20_000 for k in range(14))   # câu nối liền, không khoảng im
    assert abs(tmap.end / 1e6 - sum(v + 0.1 for v in voice.values())) < 0.1
    third = [c for c in p2.clips if 22.0 <= c.source_start and c.source_end <= 32.0]
    assert len(third) == 4 and all(abs((c.source_end - c.source_start) - 7.1 / 4) < 0.01 for c in third)  # 4 cảnh ~1.8s
    assert all(script.lines[k].source_start - 1e-6 <= s2.lines[k].source_start
               and s2.lines[k].source_end <= script.lines[k].source_end + 1e-6 for k in range(15))  # đúng đoạn phim câu kể
    assert p2.titles_top == plan.titles_top and p2.music == plan.music        # giữ tiêu đề / nhạc của kế hoạch AI
    assert notes and "Dựng từ voice" in notes[0]
    # chưa thu voice: tạm tính theo số chữ (93 chữ / 10 = 9.3s mỗi câu) để dựng thử
    p3, _, n3 = build_from_voice(plan, script, {}, [], cps=10.0, gap_s=0.1)
    assert abs(TimeMap(p3.clips).end / 1e6 - 15 * 9.4) < 0.5 and "chưa có voice" in n3[0]


def test_review_job_end_to_end(tmp_path):
    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/phim.mp4")], JobOptions(review=True, target_language="ko"), job_id="rv")
    make_analysis(jobs / "rv", duration=400.0)
    r = make_runner(tmp_path, jobs)
    u = load("understand.json")
    u["usable_range"] = {"start": 0.0, "end": 400.0}
    c1, c2 = _clips(1.0, 56), _clips(201.0, 56)
    seg = {"videos": [{"start": 1.0, "end": 190.0, "title_vi": "a", "summary_vi": "a", "why_vi": "a"},
                      {"start": 200.0, "end": 390.0, "title_vi": "b", "summary_vi": "b", "why_vi": "b"}],
           "dropped": [], "editor_notes": "2 đoạn hay"}
    r._director = FakeDirector(responses={"understand": u, "segment": seg, "plan": [_plan(1, c1), _plan(2, c2)],
                                          "dub_review": [_script(1, 1.0), _script(2, 201.0)],
                                          "captions": [load("captions.json"), {**load("captions.json"), "video_index": 2}]})
    job = r.run(job)
    assert job.step == "review_segments" and job.status == Status.waiting, job.message  # duyệt các đoạn hay
    r.apply_segments(job, json.loads((jobs / "rv" / "plan" / "segments.json").read_text(encoding="utf-8"))["videos"])
    job = r.resume(job)
    assert job.step == "dub_voice" and job.status == Status.waiting, job.message
    txt = (jobs / "rv" / "dub_scripts.txt").read_text(encoding="utf-8")
    assert "📖 Câu chuyện: Mở đầu" in txt and "📜 BÀI LỜI ĐỌC" in txt
    style = r._style(job)
    assert style["review"] and style["original_audio"]["mute"] is True and "hype" not in style  # tiếng phim tắt hẳn
    assert style["layout"] == "review_story" and style["block_ratio"] == "9:10"
    for v in (1, 2):  # thu đủ voice: mỗi câu 3 giây (máy đo giả 3s) → cảnh cắt đúng 3 giây mỗi câu
        for n in range(1, 16):
            (jobs / "rv" / "voice" / f"video{v:02d}_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    assert abs(job.data["drafts"][0]["duration_s"] - 15 * (3.0 + 0.12)) < 1.0  # video dài đúng bằng tổng giọng
    content = (Path(job.data["drafts"][0]["draft"]) / "draft_content.json").read_text(encoding="utf-8")
    assert "이 장면 진짜" in content and "이 장면 진짜 웃겨요." not in content  # phụ đề cụm ngắn như video mẫu
    assert len(job.data["drafts"]) == 2


def test_review_must_be_a_story_not_scene_description(tmp_path):
    """Chủ dự án (09/10): review phải thành MỘT CÂU CHUYỆN, không thuật lại "người này đang làm gì"."""
    from app.director.tasks import check_story

    rcfg = config.load("review")
    assert check_story(DubScript.model_validate(_script(1, 1.0)), rcfg) == []
    assert any("story_vi" in e for e in check_story(DubScript.model_validate({**_script(1, 1.0), "story_vi": ""}), rcfg))
    data = _script(1, 1.0)
    for ln in data["lines"][:8]:
        ln["text_vi"] = "Cậu bé đang chạy, con mèo đang nhìn."
    assert any("TẢ CẢNH" in e for e in check_story(DubScript.model_validate(data), rcfg))
    a = make_analysis(tmp_path, duration=200.0)
    d = FakeDirector(responses={"dub_review": [data, _script(1, 1.0)]})
    make_dub(d, a, _u(a), plan=None, mode="review")
    assert len(d.calls) == 2 and "KỂ THÀNH CÂU CHUYỆN" in d.calls[1]["prompt"]


def test_review_voice_speed_is_separate(tmp_path, monkeypatch):
    """Giọng review có tốc độ riêng (chủ dự án đo 09/10: 22 chữ / 2 giây ≈ 11 → 10), sau đó theo đúng giọng thật."""
    from app import settings
    from app.director.tasks import effective_cps, review_dub_cfg

    dub = config.load("dub")
    monkeypatch.setattr(settings, "load", lambda: {"voice_cps": {"ko": 6.0}})
    assert effective_cps(dub, "ko") == 6.0
    assert effective_cps(review_dub_cfg(dub), "ko") == 10.0
    monkeypatch.setattr(settings, "load", lambda: {"review_voice_cps": {"ko": 12.0}})
    assert effective_cps(review_dub_cfg(dub), "ko") == 12.0     # nhanh hơn cũng theo giọng thật
    a = make_analysis(tmp_path, duration=200.0)
    d = FakeDirector(responses={"dub_review": _script(1, 1.0)})
    try:
        make_dub(d, a, _u(a), plan=None, mode="review")
    except DirectorError:
        pass
    assert "~12.0 chữ/giây" in d.calls[0]["prompt"]           # AI viết độ dài bài theo tốc độ giọng thật


def test_review_film_audio_muted_and_no_replay(tmp_path):
    rcfg = config.load("review")
    assert rcfg["original_audio"]["mute"] is True
    a2 = make_analysis(tmp_path, duration=400.0)
    u2 = _u(a2, 0.0, 400.0, lang="ja")
    with_replay = _plan(1, [*_clips(1.0, 56), {"source_start": 5.0, "source_end": 6.0, "speed": 0.5, "replay": True}])
    d2 = FakeDirector(responses={"plan": [with_replay, _plan(1, _clips(1.0, 56))]})
    make_plan(d2, a2, u2.model_copy(update={"language": "ja"}), {"review": rcfg})
    assert len(d2.calls) == 2 and "không dùng replay" in d2.calls[1]["prompt"]
