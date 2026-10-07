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
    if "dub" in responses:  # mặc định job viết mới (rewrite) → cùng câu trả lời cho cả 2 cách viết
        responses.setdefault("dub_rewrite", responses["dub"])
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
    r = client.post("/jobs", data={"footage": str(footage), "target_language": "ko", "hook": "",
                                   "script_mode": "translate"}, follow_redirects=False)
    jid = r.headers["location"].rsplit("/", 1)[1]
    wait_idle(app)
    job = Job.load(jobs, jid)
    assert job.options.target_language == "ko" and job.step == "dub_voice", job.message
    assert job.options.script_mode == "translate"
    page = client.get(f"/jobs/{jid}").text
    assert "Thu voice thuyết minh" in page and "video01_dub03" in page and "저 스모 선수" in page
    assert "dub-voice-all" in page and "chỗ 3.0s" in page  # ô một file cả bài + chỗ trống từng câu
    # chọn 3 file tên tùy ý một lượt → tự xếp theo thứ tự
    files = [("files", (f"{n}.wav", b"RIFF", "audio/wav")) for n in (1, 2, 3, 4, 5)]
    client.post(f"/jobs/{jid}/dub-voice", data={"video": "1"}, files=files, follow_redirects=False)
    wait_idle(app)
    assert (jobs / jid / "voice" / "video01_dub05.wav").is_file()
    job = Job.load(jobs, jid)
    assert job.status.value == "done", job.message
    assert "Voice thuyết minh" in client.get(f"/jobs/{jid}").text
    page = client.get(f"/jobs/{jid}").text
    assert "Phụ đề tiếng Việt để kiểm tra" in page and "đang BẬT" in page
    client.post(f"/jobs/{jid}/vi-subs", data={"on": "0"}, follow_redirects=False)  # tắt trước khi xuất
    wait_idle(app)
    job = Job.load(jobs, jid)
    assert job.data["vi_subs"] is False and job.status.value == "done", job.message
    assert "đang TẮT" in client.get(f"/jobs/{jid}").text


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
    # khoảng lặng chủ yếu là tiếng cười: còn giữ tiếng gốc → không đưa cho AI; tiếng gốc bị tắt → vẫn cần lời dẫn
    laugh = [{"start": 2, "end": 10, "kind": "laugh"}]
    assert silent_gaps(plan, segs, laugh, {**cfg, "mute_original": False}) == []
    assert len(silent_gaps(plan, segs, laugh, {**cfg, "mute_original": True})) == 1


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


def test_original_audio_muted_in_dub_mode(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(target_language="ko", script_mode="translate"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    for n in range(1, 6):
        (jobs / "j1" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    videos = [s for t in content["tracks"] if t["type"] == "video" for s in t["segments"]]
    assert videos and all(s["volume"] == 0.0 for s in videos)  # hình gốc không còn tiếng
    audio_paths = [m.get("path", "") for m in content["materials"]["audios"]]
    assert not any("clean_" in p for p in audio_paths)  # không chèn lại bản tiếng gốc đã lọc ồn
    dub_prompt = next(c["prompt"] for c in r._director.calls if c["task"] == "dub")
    assert "TIẾNG GỐC BỊ TẮT HẲN" in dub_prompt


def test_repair_dub_clamps_and_merges():
    from app.director.tasks import repair_dub

    plan = EditPlan.model_validate({**_short_plan(), "clips": [{"source_start": 1.0, "source_end": 20.0},
                                                               {"source_start": 22.0, "source_end": 45.0}]})
    script = DubScript.model_validate({**FIX, "lines": [
        {"source_start": 18.0, "source_end": 24.0, "text": "다리 걸친 문장", "text_vi": "x"},  # vắt qua 2 clip
        {"source_start": 30.0, "source_end": 31.2, "text": "가" * 12, "text_vi": "câu ngắn"},  # quá nhiều chữ
        {"source_start": 31.3, "source_end": 34.0, "text": "나머지", "text_vi": "phần còn lại"},
        {"source_start": 46.0, "source_end": 50.0, "text": "밖", "text_vi": "ngoài"}]})          # ngoài mọi clip
    fixed, notes = repair_dub(script, plan, {"max_cps": {"ko": 7.0}, "max_speed": 1.25}, "ko")
    assert [(ln.source_start, ln.source_end) for ln in fixed.lines] == [(18.0, 20.0), (30.0, 34.0)]
    assert fixed.lines[1].text == "가" * 12 + " 나머지" and fixed.lines[1].text_vi == "câu ngắn phần còn lại"
    assert len(notes) == 3 and check_dub(fixed, plan, "ko", {"max_cps": {"ko": 7.0}, "line_s": [1.5, 9.0]}) == []


def test_check_dub_uses_room_before_next_line():
    plan = EditPlan.model_validate(_short_plan())
    s = DubScript.model_validate({**FIX, "lines": [
        {"source_start": 2.0, "source_end": 3.4, "text": "가" * 12, "text_vi": "x"},   # 1.4s nhưng lặng tới 6s → đọc kịp
        {"source_start": 6.0, "source_end": 9.0, "text": "나" * 10, "text_vi": "y"}]})
    assert check_dub(s, plan, "ko") == []


def test_web_accept_imperfect_dub(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app
    from tests.test_web import wait_idle

    jobs = tmp_path / "jobs"
    footage = tmp_path / "test.mp4"
    footage.write_bytes(b"x")
    bad = {**FIX, "lines": [{**FIX["lines"][0], "text": "가" * 120}, *FIX["lines"][1:]]}  # câu 1 quá nhiều chữ mãi

    def factory(root, log):
        r = make_runner(tmp_path, root, dub=bad)
        r.log = log
        return r

    app = create_app(jobs, factory)
    client = TestClient(app)
    orig_start = app.state.worker.start

    def start(job_id, action=None):
        if not (jobs / job_id / "analysis").exists():
            make_analysis(jobs / job_id, duration=60.0)
        return orig_start(job_id, action)

    app.state.worker.start = start
    r = client.post("/jobs", data={"footage": str(footage), "target_language": "ko", "hook": ""}, follow_redirects=False)
    jid = r.headers["location"].rsplit("/", 1)[1]
    wait_idle(app)
    job = Job.load(jobs, jid)
    assert job.status.value == "error" and job.step == "dub"
    page = client.get(f"/jobs/{jid}").text
    assert "Dùng bản này, bỏ qua lỗi còn lại" in page and "ký tự/giây" in page
    client.post(f"/jobs/{jid}/accept-dub", follow_redirects=False)
    wait_idle(app)
    job = Job.load(jobs, jid)
    assert job.step == "dub_voice" and job.status.value == "waiting", job.message
    assert not list((jobs / jid / "plan").glob("pending_dub_video*.json"))


def _wav(path: Path, seconds: float) -> None:
    import numpy as np

    from app.planner.voice_split import RATE, write_wav

    write_wav(path, (np.sin(np.arange(int(seconds * RATE)) / 20) * 8000).astype(np.int16))


def test_dense_note_and_measured_rate(monkeypatch):
    from app import settings
    from app.director.tasks import dense_note, effective_cps

    plan = EditPlan.model_validate(_short_plan())  # clip 1–45s
    dense = [{"start": float(t), "end": t + 0.9} for t in range(1, 45)]
    assert "NÓI DÀY ĐẶC" in dense_note(plan, dense, {})
    assert dense_note(plan, dense[:10], {}) == ""
    monkeypatch.setattr(settings, "load", lambda path=None: {"voice_cps": {"ko": 5.5}})
    assert effective_cps({"max_cps": {"ko": 7.0}}, "ko") == 5.5  # giọng thu thật đọc chậm hơn → dùng tốc độ đó
    assert effective_cps({"max_cps": {"ko": 7.0}, "use_measured_rate": False}, "ko") == 7.0


def test_shorten_long_dub_lines(tmp_path, monkeypatch):
    remembered = []
    monkeypatch.setattr(dub_io, "remember_voice_rate", lambda lang, rate: remembered.append((lang, rate)) or rate)
    jobs, job = prepare(tmp_path, JobOptions(target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.step == "dub_voice"
    vdir = jobs / "j1" / "voice"
    for n, secs in {1: 2.6, 2: 15.0, 3: 4.0, 4: 3.5, 5: 3.0}.items():  # câu 2: chỗ 6s, tối đa ~10.7s → voice 15s quá dài
        _wav(vdir / f"video01_dub{n:02d}.wav", secs)
    job = r.resume(job)
    assert job.status == Status.done, job.message
    assert remembered and remembered[0][0] == "ko"  # đã đo và nhớ tốc độ đọc của giọng thu
    assert dub_io.voice_rate(jobs / "j1", 1, dub_io.load_dub(jobs / "j1", 1))
    long = r.long_dub_lines(job)
    assert [i for i, _ in long[1]] == [2]
    assert r.shorten_dub(job) == 1
    script = dub_io.load_dub(jobs / "j1", 1)
    assert script.lines[1].text == "다들 그를 싫어했죠." and script.lines[0].text.startswith("저 스모")  # chỉ câu 2 đổi
    assert not (vdir / "video01_dub02.wav").exists() and (vdir / "video01_dub02_cu.wav").exists()
    assert job.step == "dub_voice" and job.status == Status.pending
    job = r.run(job)
    assert job.status == Status.waiting and "video01_dub02.wav" in job.message  # chờ thu lại đúng câu 2


def test_voice_only_mode_keeps_footage(tmp_path):
    """Chỉ thay tiếng: giữ nguyên toàn bộ video (không cắt / zoom / lật / đổi khung), chỉ voice + phụ đề + tiêu đề +
    nhạc nhẹ + hiệu ứng."""
    from app.director.schemas import EditPlan

    jobs, job = prepare(tmp_path, JobOptions(target_language="ko", voice_only=True))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.step == "dub_voice", job.message
    assert job.data["videos"][0]["start"] == 0 and job.data["videos"][0]["end"] == 60.0
    plan = EditPlan.model_validate_json((jobs / "j1" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    assert [(c.source_start, c.source_end, c.speed) for c in plan.clips] == [(0.0, 60.0, 1.0)]
    assert not plan.zooms and not plan.transitions and not plan.emphasis and plan.filter is None
    st = r._style(job)
    assert st["block_ratio"] == "16:9" and st["keep_footage"] and not st.get("mirror") and not st.get("motion")
    for n in range(1, 6):
        (jobs / "j1" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    vids = [m for m in content["materials"]["videos"] if m["type"] == "video"]
    assert all(m["crop"]["upper_left_x"] == 0 and m["crop"]["lower_right_x"] == 1 for m in vids)  # không cắt khung
    segs = [s for t in content["tracks"] if t["type"] == "video" for s in t["segments"]]
    assert all(s["speed"] == 1.0 and not s["clip"]["flip"]["horizontal"] and not s.get("common_keyframes")
               for s in segs)  # không tua, không lật, không zoom / chuyển động
    assert sum(s["target_timerange"]["duration"] for s in segs) == 60_000_000  # đúng độ dài gốc


def test_voice_only_vertical_overlay_layout():
    from app.capcut_writer.layout import nearest_ratio
    from app.styles import layout_for, load_style

    assert nearest_ratio(1080, 1920) == "9:16" and nearest_ratio(1920, 1080) == "16:9" and nearest_ratio(720, 720) == "1:1"
    lay = layout_for({**load_style("jp_telop"), "block_ratio": "9:16"})
    assert lay["title_rows"] == [0.11, 0.18, 0.67, 0.74] and lay["subtitle_row"] == 0.58  # chữ đè lên hình, tránh UI TikTok


def test_web_voice_only_needs_language(tmp_path):
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    footage = tmp_path / "v.mp4"
    footage.write_bytes(b"x")
    client = TestClient(create_app(tmp_path / "jobs", lambda root, log: make_runner(tmp_path, root)))
    assert "Chỉ thay tiếng" in client.get("/").text
    r = client.post("/jobs", data={"footage": str(footage), "voice_only": "on"}, follow_redirects=False)
    assert "Chưa chọn ngôn ngữ" in r.text


def test_separate_bgm_command_and_missing_demucs(tmp_path, monkeypatch):
    import pytest

    from app.analysis import separate

    cmd = separate.demucs_cmd(Path("a.wav"), Path("out"), "htdemucs", "cpu")
    assert cmd[1:] == ["-m", "demucs.separate", "--two-stems", "vocals", "-n", "htdemucs", "-o", "out",
                       "--filename", "{stem}.{ext}", "-d", "cpu", "a.wav"]
    monkeypatch.setattr(separate, "available", lambda: False)
    with pytest.raises(RuntimeError, match="requirements-bgm.txt"):
        separate.separate_bgm(Path("x.mp4"), tmp_path / "bgm.wav")

    ff = pytest.importorskip("imageio_ffmpeg").get_ffmpeg_exe()
    monkeypatch.setattr(separate, "available", lambda: True)
    src = tmp_path / "src.wav"
    _wav(src, 1.0)

    def fake_run(c, **kw):  # giả lập Demucs: ghi no_vocals.wav đúng chỗ demucs ghi
        out = Path(c[c.index("-o") + 1]) / "htdemucs" / "no_vocals.wav"
        out.parent.mkdir(parents=True)
        out.write_bytes(b"RIFF")
        return type("R", (), {"returncode": 0, "stderr": ""})()

    dst = separate.separate_bgm(src, tmp_path / "a" / "bgm.wav", ffmpeg_exe=ff, run=fake_run)
    assert dst.read_bytes() == b"RIFF"


def test_voice_only_keep_bgm(tmp_path):
    """Giữ nhạc nền gốc: dùng bản đã tách giọng nói, hạ nhỏ dưới voice, không thêm nhạc khác."""
    jobs, job = prepare(tmp_path, JobOptions(target_language="ko", voice_only=True, keep_bgm=True))
    r = make_runner(tmp_path, jobs)
    logs = []
    r.log = logs.append
    job = r.run(job)
    assert job.step == "dub_voice", job.message
    bgm = jobs / "j1" / "analysis" / "audio" / "bgm_00.wav"
    bgm.parent.mkdir(parents=True, exist_ok=True)
    bgm.write_bytes(b"RIFF")  # như đã tách xong (bước tách được lưu lại, chỉ làm một lần)
    for n in range(1, 6):
        (jobs / "j1" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    audios = {m["id"]: m for m in content["materials"]["audios"]}
    bgm_mats = [m for m in audios.values() if m.get("path", "").endswith("bgm_00.wav")]
    assert bgm_mats
    library_music = [m for m in audios.values() if m.get("music_id")]
    assert not library_music  # không thêm nhạc thư viện CapCut
    segs = [s for t in content["tracks"] if t["type"] == "audio" for s in t["segments"]
            if s["material_id"] in {m["id"] for m in bgm_mats}]
    assert segs and all(s.get("common_keyframes") for s in segs)  # nhạc gốc hạ nhỏ dưới voice


def test_keep_bgm_falls_back_without_demucs(tmp_path, monkeypatch):
    from app.analysis import separate

    monkeypatch.setattr(separate, "available", lambda: False)
    jobs, job = prepare(tmp_path, JobOptions(target_language="ko", voice_only=True, keep_bgm=True))
    r = make_runner(tmp_path, jobs)
    logs = []
    r.log = logs.append
    job = r.run(job)
    for n in range(1, 6):
        (jobs / "j1" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    assert any("Không giữ được nhạc nền gốc" in m and "Demucs" in m for m in logs)


def test_rewrite_mode_watches_video_and_writes_new(tmp_path):
    """Viết mới: AI được xem khung hình, prompt dặn không dịch; câu đầu phải cất lên ngay, không nói kín mít."""
    from app.director.tasks import check_rewrite

    a = make_analysis(tmp_path)
    u = understand(FakeDirector(), a).dubbed_to("ko")
    d = FakeDirector()
    s = make_dub(d, a, u, EditPlan.model_validate(_short_plan()), mode="rewrite")
    call = d.calls[-1]
    assert call["task"] == "dub_rewrite" and "VIẾT MỚI" in call["prompt"] and "KHÔNG dịch" in call["prompt"]
    assert len(call["images"]) >= 10  # gửi khung hình rải đều để AI xem
    assert s.lines[0].source_start == 1.2
    plan = EditPlan.model_validate(_short_plan())  # clip 1–45s
    late = DubScript.model_validate({**FIX, "lines": [{**FIX["lines"][0], "source_start": 6.0, "source_end": 9.0}]})
    assert any("giây đầu" in e for e in check_rewrite(late, plan, {}))
    full = DubScript.model_validate({**FIX, "lines": [
        {"source_start": float(t), "source_end": t + 4.8, "text": "가", "text_vi": "x"} for t in range(1, 41, 5)]})
    assert any("quá kín" in e for e in check_rewrite(full, plan, {"rewrite": {"max_cover": 0.8}}))  # 87% > 80%


def test_job_default_script_mode_is_rewrite(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(target_language="ko"))
    r = make_runner(tmp_path, jobs)
    assert r.script_mode(job) == "rewrite"
    job = r.run(job)
    assert job.step == "dub_voice"
    assert any(c["task"] == "dub_rewrite" for c in r._director.calls)
    job.options.script_mode = "translate"
    assert r.script_mode(job) == "translate"
