"""Chế độ Đổi ngôn ngữ: thuyết minh + phụ đề ngôn ngữ đích, dựng lại khác bản gốc (giữ thứ tự cảnh)."""

import json
from pathlib import Path

from app.director.fake import FakeDirector
from app.director.schemas import DubScript, EditPlan, PlanClip, Understanding, check_remix
from app.director.tasks import check_dub, make_dub, translate_note, understand
from app.jobs.job import JobOptions, Status
from app.planner import dub_io
from tests.test_director import GOOD, make_analysis
from tests.test_planner import _short_plan, load
from tests.test_runner import make_runner as _make_runner, prepare
from tests.test_planner import SAMPLE


def _remix_plan():
    from app.capcut_writer import DraftTemplate

    p = _short_plan()
    p["filter"] = next(i.name for i in DraftTemplate(SAMPLE).library if i.kind == "filter")
    return p


def make_runner(tmp_path, jobs, **responses):
    r = _make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _remix_plan(), **responses})
    return r

FIX = json.loads((Path(__file__).parent / "fixtures" / "director" / "dub.json").read_text(encoding="utf-8"))


def test_understanding_dubbed_keeps_source():
    u = Understanding.model_validate(GOOD).dubbed_to("ko")
    assert u.language == "ko" and u.source_language == "ja"
    v = u.model_copy(update={"summary_vi": "x"})  # for_video dùng model_copy
    assert v.source_language == "ja"
    assert "tiếng Nhật → tiếng Hàn" in translate_note(u)
    assert translate_note(Understanding.model_validate(GOOD)) == ""
    assert Understanding.model_validate({**GOOD, "language": "zh"}).language == "zh"


def test_check_dub_rules():
    plan = EditPlan.model_validate(_short_plan())  # clip 1–45s
    script = DubScript.model_validate(FIX)
    assert check_dub(script, plan, "ko") == []
    bad = DubScript.model_validate({**FIX, "lines": [
        {"source_start": 40, "source_end": 50, "text": "a", "text_vi": "a"},  # ra ngoài clip
        {"source_start": 2, "source_end": 3, "text": "가" * 30, "text_vi": "x"},  # nói quá nhanh
        {"source_start": 1.5, "source_end": 3, "text": "유튜브 구독", "text_vi": "x"}]})  # chồng + nền tảng khác
    errs = check_dub(bad, plan, "ko")
    assert any("gọn trong MỘT clip" in e for e in errs) and any("ký tự/giây" in e for e in errs)
    assert any("chồng" in e for e in errs) and any("không được phép" in e for e in errs)


def test_check_remix():
    p = load("plan.json")
    plan = EditPlan.model_validate(p)
    assert check_remix(plan, have_filters=False) == []
    assert any("filter" in e for e in check_remix(plan, have_filters=True))
    rev = plan.model_copy(update={"clips": list(reversed(plan.clips))})
    assert any("thứ tự" in e for e in check_remix(rev, False))


def test_make_dub_prompt(tmp_path):
    a = make_analysis(tmp_path)
    u = understand(FakeDirector(), a).dubbed_to("ko")
    d = FakeDirector()
    s = make_dub(d, a, u, EditPlan.model_validate(_short_plan()))
    assert len(s.lines) == 5
    prompt = d.calls[0]["prompt"]
    assert "thuyết minh bằng **tiếng Hàn**" in prompt and "Footage gốc nói tiếng Nhật" in prompt
    assert "clip 0: 1.0–45.0s" in prompt


def test_split_and_spread():
    assert dub_io.split_text("짧은 문장", "ko", 16) == ["짧은 문장"]
    parts = dub_io.split_text("今日はとても楽しい一日でした。また来週も一緒に遊びましょうね！", "ja", 13)
    assert all(len(p) <= 13 for p in parts) and "".join(parts).startswith("今日は")
    cues = dub_io.spread_cues(["ab", "abcd"], 0, 600)
    assert cues == [(0, 200, "ab"), (200, 600, "abcd")]
    assert dub_io.match_uploads(["2.wav", "10.wav", "1.wav"], 1, 3) == [("1.wav", 1), ("2.wav", 2), ("10.wav", 3)]


def test_full_dub_job(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "dub_voice", job.message
    assert "video01_dub01.wav" in job.message
    assert job.data["source_language"] == "ja"
    script = (jobs / "j1" / "dub_scripts.txt").read_text(encoding="utf-8")
    assert "저 스모 선수" in script and "video01_dub03.wav" in script
    vdir = jobs / "j1" / "voice"
    for n in (1, 2, 3, 4, 5):
        (vdir / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    draft = Path(job.data["draft"])
    content = json.loads((draft / "draft_content.json").read_text(encoding="utf-8"))
    audio_paths = [m.get("path", "") for m in content["materials"]["audios"]]
    assert sum("video01_dub" in p for p in audio_paths) == 5
    texts = " ".join(m.get("content", "") for m in content["materials"]["texts"])
    assert "스모" in texts and "こんにちは" not in texts  # phụ đề là câu dịch, không phải lời gốc
    plan = json.loads((jobs / "j1" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    assert plan["clips"]


def test_dub_skip_and_redo(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(target_language="en"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.step == "dub_voice"
    (jobs / "j1" / "voice" / "video01_dub01.wav").write_bytes(b"RIFF")
    job.data["dub_skip"] = True
    job = r.resume(job)
    assert job.status == Status.done, job.message
    missing = json.loads((jobs / "j1" / "missing_assets.json").read_text(encoding="utf-8"))
    assert sum(m["kind"] == "voice" for m in missing) == 4
    r.redo(job, "dub")
    assert not list((jobs / "j1" / "plan").glob("dub_video*.json"))
    assert (jobs / "j1" / "voice" / "video01_dub01_cu.wav").is_file()


def test_same_language_target_only_remixes(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(target_language="ja"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.done and job.data.get("dub_same")
    assert not list((jobs / "j1" / "plan").glob("dub_video*.json"))


def test_chinese_source_requires_target(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions())
    r = make_runner(tmp_path, jobs, understand={**GOOD, "language": "zh"})
    job = r.run(job)
    assert job.status == Status.error and "Đổi ngôn ngữ" in job.message


def test_web_dub_flow(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app
    from tests.test_web import wait_idle

    jobs = tmp_path / "jobs"
    footage = tmp_path / "test.mp4"
    footage.write_bytes(b"x")

    def factory(root, log):
        r = make_runner(tmp_path, root)
        r.log = log
        return r

    app = create_app(jobs, factory)
    client = TestClient(app)
    assert "Đổi sang tiếng Hàn" in client.get("/").text
    orig_start = app.state.worker.start

    def start(job_id, action=None):
        if not (jobs / job_id / "analysis").exists():
            make_analysis(jobs / job_id, duration=60.0)
        return orig_start(job_id, action)

    app.state.worker.start = start
    r = client.post("/jobs", data={"footage": str(footage), "target_language": "ko", "hook": ""},
                    follow_redirects=False)
    jid = r.headers["location"].rsplit("/", 1)[1]
    wait_idle(app)
    job = Job.load(jobs, jid)
    assert job.options.target_language == "ko" and job.step == "dub_voice", job.message
    page = client.get(f"/jobs/{jid}").text
    assert "Thu voice thuyết minh" in page and "video01_dub03" in page and "저 스모 선수" in page
    # chọn 3 file tên tùy ý một lượt → tự xếp theo thứ tự
    files = [("files", (f"{n}.wav", b"RIFF", "audio/wav")) for n in (1, 2, 3, 4, 5)]
    client.post(f"/jobs/{jid}/dub-voice", data={"video": "1"}, files=files, follow_redirects=False)
    wait_idle(app)
    assert (jobs / jid / "voice" / "video01_dub05.wav").is_file()
    job = Job.load(jobs, jid)
    assert job.status.value == "done", job.message
    assert "Voice thuyết minh" in client.get(f"/jobs/{jid}").text


def test_silent_gaps_and_narration_check():
    from app.director.tasks import check_narration, silent_gaps

    plan = EditPlan.model_validate({**_short_plan(), "clips": [
        {"source_start": 0, "source_end": 10}, {"source_start": 20, "source_end": 30},
        {"source_start": 25, "source_end": 27, "speed": 0.5, "replay": True}]})
    segs = [{"start": 0, "end": 2, "text": "a", "words": [{"start": 0.0, "end": 2.0, "word": "a"}]},
            {"start": 21, "end": 29, "text": "b", "words": [{"start": 21.0, "end": 29.0, "word": "b"}]}]
    cfg = {"narration": {"min_gap_s": 2.0, "max_cover_ratio": 0.6, "keep_reactions": True}}
    gaps = silent_gaps(plan, segs, [], cfg)
    # 2–10s clip 1 + 20–21s clip 2 liền nhau trên video = 9s lặng; cuối clip 2 chỉ 1s; replay không tính
    assert len(gaps) == 1 and gaps[0]["pieces"] == [(2.0, 10.0), (20.0, 21.0)]

    def script(*lines):
        return DubScript.model_validate({"video_index": 1, "editor_notes": "", "lines": [
            {"kind": "narration", "text": "x", "text_vi": "x", "action_vi": act, "source_start": a, "source_end": b}
            for a, b, act in lines]})

    # chỉ nói ở 1 hành động đáng chú ý, không lấp hết chỗ trống → hợp lệ
    assert check_narration(script((4, 6.5, "thêm gia vị")), plan, gaps, cfg) == []
    assert check_narration(DubScript.model_validate({"video_index": 1, "editor_notes": "", "lines": [
        {"source_start": 0, "source_end": 2, "text": "a", "text_vi": "a"}]}), plan, gaps, cfg) == []  # im cũng được
    errs = check_narration(script((4, 6.5, "")), plan, gaps, cfg)
    assert any("action_vi" in e for e in errs)
    assert any("đè lên lời thoại" in e for e in check_narration(script((21, 24, "x")), plan, gaps, cfg))
    assert any("quá dày" in e for e in check_narration(script((2, 5, "a"), (5, 8, "b")), plan, gaps, cfg))
    # khoảng lặng chủ yếu là tiếng cười → không đưa cho AI
    assert silent_gaps(plan, segs, [{"start": 2, "end": 10, "kind": "laugh"}], cfg) == []


def test_dub_prompt_lists_silent_gaps(tmp_path):
    a = make_analysis(tmp_path)
    u = understand(FakeDirector(), a).dubbed_to("ko")
    d = FakeDirector()
    make_dub(d, a, u, EditPlan.model_validate(_short_plan()))
    prompt = d.calls[0]["prompt"]
    assert "CẢNH HAY / HÀNH ĐỘNG" in prompt and "giây gốc 3.0–45.0" in prompt and "thêm gia vị" in prompt
    assert d.calls[0]["images"]  # gửi khung hình ở chỗ lặng để thấy hành động
    bad = json.loads(json.dumps(FIX))
    bad["lines"][3]["action_vi"] = ""  # lời dẫn không nói rõ hành động → gọi lại
    d2 = FakeDirector(responses={"dub": [bad, FIX]})
    make_dub(d2, a, u, EditPlan.model_validate(_short_plan()))
    assert len(d2.calls) == 2 and "action_vi" in d2.calls[1]["prompt"]


def test_silent_opening_requires_cooking_style_narration(tmp_path):
    from app.director.tasks import check_narration, opening_gap, silent_gaps

    a = make_analysis(tmp_path)  # lời thoại duy nhất ở 1–3s
    u = understand(FakeDirector(), a).dubbed_to("ko")
    plan = EditPlan.model_validate({**_short_plan(), "clips": [{"source_start": 3.0, "source_end": 45.0}]})
    segs = [{"start": 1.0, "end": 3.0, "text": "こんにちは", "words": []}]
    gaps = silent_gaps(plan, segs, [])
    assert opening_gap(gaps) is not None  # mở đầu im lặng (show món)
    no_open = DubScript.model_validate({**FIX, "lines": FIX["lines"][3:]})  # lời dẫn chỉ ở 30s, 38s
    assert any("mở đầu im lặng" in e for e in check_narration(no_open, plan, gaps))
    opened = no_open.model_copy(update={"lines": [no_open.lines[0].model_copy(update={
        "source_start": 3.2, "source_end": 6.0, "text": "와, 이 윤기 좀 보세요.", "action_vi": "show món thành phẩm"}),
        *no_open.lines]})
    assert check_narration(opened, plan, gaps) == []
    # qua đạo diễn: lần đầu thiếu lời dẫn mở đầu → bị gọi lại, prompt có hướng dẫn giọng video nấu ăn
    d = FakeDirector(responses={"dub": [no_open.model_dump(), opened.model_dump()]})
    make_dub(d, a, u, plan)
    assert len(d.calls) == 2 and "MỞ ĐẦU IM LẶNG" in d.calls[0]["prompt"] and "gợi tò mò cách làm" in d.calls[0]["prompt"]
    # mở đầu có thoại → không bắt buộc
    assert opening_gap(silent_gaps(EditPlan.model_validate(_short_plan()), segs, [])) is None


def test_localized_for_target_country(tmp_path):
    from app.director.tasks import localize_brief, localize_violations

    u = Understanding.model_validate(GOOD)  # gốc tiếng Nhật
    assert localize_brief(u) == ""  # không đổi ngôn ngữ → không cần
    ko = u.dubbed_to("ko")
    brief = localize_brief(ko)
    assert "khán giả TikTok Hàn Quốc" in brief and "해요체" in brief and "원" in brief
    assert "BẢN ĐỊA HÓA" in translate_note(ko)  # hook / kế hoạch dựng / caption cũng nhận hướng dẫn này
    assert localize_violations("3마일 정도 걸었어요", "ko") == ["마일"]
    assert localize_violations("about 3 miles", "en") == []
    # kịch bản thuyết minh: prompt có phần bản địa hóa; dùng đơn vị lạ → bị gọi lại
    a = make_analysis(tmp_path)
    uk = understand(FakeDirector(), a).dubbed_to("ko")
    bad = json.loads(json.dumps(FIX))
    bad["lines"][0]["text"] = "3마일이나 걸었대요."
    d = FakeDirector(responses={"dub": [bad, FIX]})
    make_dub(d, a, uk, EditPlan.model_validate(_short_plan()))
    assert "khán giả TikTok Hàn Quốc" in d.calls[0]["prompt"] and "adapt_vi" in d.calls[0]["prompt"]
    assert len(d.calls) == 2 and "không quen với khán giả" in d.calls[1]["prompt"]
