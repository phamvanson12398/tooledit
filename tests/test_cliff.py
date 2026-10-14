"""Chế độ "Review bỏ lửng" (chủ dự án yêu cầu 14/10): kể HẾT phim thành nhiều phần liền nhau, mỗi phần mở bằng short
kịch tính giữ nguyên, lời review ngôi 1 hoặc 3, kết bỏ lửng. Review phim cũ giữ nguyên (tests/test_review.py)."""

import json
from pathlib import Path

from app import config
from app.director.cliff import check_coverage, check_parts, cliff_target, merge_short, repair_parts
from app.director.fake import FakeDirector
from app.director.schemas import CliffPlan, DubScript
from app.director.tasks import check_story
from app.jobs.job import Job, JobOptions, Status
from tests.test_director import make_analysis
from tests.test_planner import load
from tests.test_review import SENT, _clips, _plan
from tests.test_runner import make_runner

CFG = config.load("cliff")


def _part(a, b, ha, hb, cliff="Liệu cậu bé có kịp mở cửa?"):
    return {"start": a, "end": b, "title_vi": f"phần {a:.0f}", "summary_vi": f"đoạn {a:.0f}–{b:.0f}",
            "hook": {"start": ha, "end": hb, "why_vi": "pha rượt đuổi"}, "cliff_vi": cliff}


def _cp(*parts):
    return CliffPlan.model_validate({"narrator_vi": "Minho", "parts": list(parts), "editor_notes": "chia ở chỗ gay cấn"})


def test_parts_must_cover_whole_film_without_gaps():
    ok = _cp(_part(0, 200, 50, 60), _part(200, 400, 250, 262))
    assert check_parts(ok, 0, 400, CFG) == []
    # hở 5 giây giữa 2 phần + phần đầu lệch 3 giây → tool tự nối khít
    fixed, fixes = repair_parts(_cp(_part(3, 200, 50, 60), _part(205, 400, 250, 262)), 0, 400, CFG)
    assert [(p.start, p.end) for p in fixed.parts] == [(0, 200), (200, 400)] and len(fixes) == 2
    # hở lớn (bỏ cảnh) → báo lỗi, không tự nối
    gap, _ = repair_parts(_cp(_part(0, 180, 50, 60), _part(220, 400, 250, 262)), 0, 400, CFG)
    assert any("bị hở" in e for e in check_parts(gap, 0, 400, CFG))
    # short ngoài phần / quá dài / chạm đoạn vi phạm chính sách
    bad = _cp(_part(0, 200, 195, 210), _part(200, 400, 250, 280))
    errs = check_parts(bad, 0, 400, CFG, banned=[(255.0, 258.0)])
    assert any("nằm TRONG" in e for e in errs) and any("dài 30.0s" in e for e in errs)
    assert any("chính sách" in e for e in errs)
    # phần quá dài phim → tách
    assert any("tách làm 2 phần" in e for e in check_parts(_cp(_part(0, 900, 50, 60)), 0, 900, CFG))


def test_merge_short_part_at_chunk_join():
    parts = [{**_part(0, 300, 10, 20), "index": 1}, {**_part(300, 340, 310, 320, "B"), "index": 2},
             {**_part(340, 600, 350, 360, "C"), "index": 3}]
    out = merge_short(parts, CFG)
    assert [(p["start"], p["end"]) for p in out] == [(0, 300 + 40), (340, 600)] and out[0]["cliff_vi"] == "B"


def _script(index: int, start: float, n: int = 10, step: float = 20.0, text: str = SENT.strip(),
            text_vi: str = "Cảnh này hài thật. Nhưng lúc đó cậu bé chẳng hay biết gì.") -> dict:
    """10 câu ~9.3 giây (≈ 93 giây lời + short ~10 giây ≈ 1:43), đoạn phim các câu nối nhau phủ kín phần."""
    lines = [{"source_start": round(start + k * step, 2), "source_end": round(start + (k + 1) * step, 2),
              "text": text, "text_vi": text_vi, "action_vi": "cảnh trong phim", "kind": "narration"} for k in range(n)]
    return {"video_index": index, "lines": lines, "editor_notes": "kể phủ kín phần",
            "story_vi": "Mở đầu: cậu bé mất con mèo. Mâu thuẫn: cả làng không ai giúp. Cao trào: cậu tự đi tìm trong rừng. "
                        "Dừng: cánh cửa bí ẩn."}


def test_coverage_no_skipped_scenes():
    s = DubScript.model_validate(_script(1, 0.0))
    assert check_coverage(s, 0, 200, CFG) == []
    skip = _script(1, 0.0)
    skip["lines"] = skip["lines"][:4] + skip["lines"][6:]  # bỏ trống 80–120s
    errs = check_coverage(DubScript.model_validate(skip), 0, 200, CFG)
    assert any("nhảy qua 40s" in e for e in errs) and any("phủ 80%" in e for e in errs)
    late = _script(1, 30.0, n=8, step=21.25)  # bắt đầu kể từ giây 30
    assert any("ĐẦU phần" in e for e in check_coverage(DubScript.model_validate(late), 0, 200, CFG))


def test_first_person_or_third_person():
    third = DubScript.model_validate(_script(1, 0.0))
    first = DubScript.model_validate(_script(1, 0.0, text="그날 나는 아무것도 몰랐다. " + SENT.strip(),
                                             text_vi="Hôm đó tôi chẳng biết gì."))
    assert not check_story(third, {}, "3") and not check_story(first, {}, "1")
    assert any("NGÔI THỨ NHẤT" in e for e in check_story(third, {}, "1"))
    assert any("NGÔI THỨ 3" in e for e in check_story(first, {}, "3"))


def test_target_counts_short_in_video_length():
    t = cliff_target(config.load("review"))
    assert (t["min_video_s"], t["max_video_s"]) == (90.0, 120.0) and t["min_reach"] == 0.95


def _run_job(tmp_path, pov="3"):
    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/phim.mp4")], JobOptions(review=True, cliff=True, cliff_pov=pov,
                                                                 target_language="ko"), job_id="cl")
    a = make_analysis(jobs / "cl", duration=400.0)
    tr = json.loads((a / "transcript.json").read_text(encoding="utf-8"))
    tr[0]["segments"].append({"start": 52.0, "end": 55.0, "text": "待て！逃げるな！", "words": []})  # thoại trong short
    (a / "transcript.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    r = make_runner(tmp_path, jobs)
    u = load("understand.json")
    u["usable_range"] = {"start": 0.0, "end": 400.0}
    parts = {"narrator_vi": "Minho", "editor_notes": "chia ở chỗ gay cấn",
             "parts": [_part(0, 200, 50, 60), _part(200, 400, 250, 262, "Minho tìm thấy mèo, cả nhà đoàn tụ.")]}
    r._director = FakeDirector(responses={
        "understand": u, "cliff_segment": parts,
        "plan": [_plan(1, _clips(1.0, 30)), _plan(2, _clips(201.0, 30))],
        "dub_cliff": [_script(1, 0.0), _script(2, 200.0)], "cliff_polish": [_script(1, 0.0), _script(2, 200.0)],
        "captions": [load("captions.json"), {**load("captions.json"), "video_index": 2}],
        "cliff_hook_subs": {"lines": [{"i": 1, "text": "거기 서! 도망가지 마!", "text_vi": "Đứng lại! Đừng chạy!"}]}})
    return jobs, job, r


def test_cliff_job_end_to_end(tmp_path):
    jobs, job, r = _run_job(tmp_path)
    job = r.run(job)
    assert job.step == "review_segments" and job.status == Status.waiting, job.message  # bảng duyệt các phần
    seg = json.loads((jobs / "cl" / "plan" / "segments.json").read_text(encoding="utf-8"))
    vids = seg["videos"]
    assert [(v["start"], v["end"]) for v in vids] == [(0, 200), (200, 400)] and vids[1]["last"]
    assert job.data["cliff_narrator"] == "Minho"
    seg_prompt = next(c for c in r._director.calls if c["task"] == "cliff_segment")["prompt"]
    assert "KHÔNG BỎ CẢNH" in seg_prompt and "5–15 giây" in seg_prompt
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    page = TestClient(create_app(jobs, lambda root, log: None)).get("/jobs/cl").text
    assert "Duyệt các phần" in page and "name='hstart_v2' value='250.0'" in page and "🏁 Kết phim" in page
    assert "🧨 Bỏ lửng" in page and "AI chia phim thành các phần" in page
    # người dùng dời short của phần 2 trên bảng duyệt
    rows = [{**v, "hook_start": None, "hook_end": None} for v in vids]
    rows[1].update(hook_start="270", hook_end="281.5")
    r.apply_segments(job, rows)
    job = r.resume(job)
    assert job.step == "dub_voice" and job.status == Status.waiting, job.message
    assert r.videos(job)[1]["hook"]["start"] == 270.0 and r.videos(job)[1]["cliff_vi"].startswith("Minho")
    calls = {c["prompt"].split("(video số ")[1][0]: c["prompt"] for c in r._director.calls if c["task"] == "dub_cliff"}
    assert "phần 1/2" in calls["1"] and "BỎ LỬNG" in calls["1"] and "đây là phần đầu tiên" in calls["1"]
    assert "PHẦN CUỐI" in calls["2"] and "Phần 1: đoạn 0–200" in calls["2"] and "nhắc nhanh bối cảnh" in calls["2"]
    assert "NGÔI THỨ BA" in calls["1"] and "270.0–281.5" in calls["2"]
    assert "short" in calls["1"].lower() and "90–120" in calls["1"]
    style = r._style(job)
    assert style["review"]["max_video_s"] == 120 and style["original_audio"]["mute"] is True
    for i in (1, 2):
        for n in range(1, 11):
            (jobs / "cl" / "voice" / f"video{i:02d}_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    gap = config.load("review")["voice_gap_s"]
    d1, d2 = job.data["drafts"]
    assert abs(d1["duration_s"] - (10 + 10 * (3.0 + gap))) < 0.5      # short 10s + lời review
    assert abs(d2["duration_s"] - (11.5 + 10 * (3.0 + gap))) < 0.5
    content = json.loads((Path(d1["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    video = next(t for t in content["tracks"] if t["type"] == "video")
    first = min(video["segments"], key=lambda s: s["target_timerange"]["start"])
    assert first["source_timerange"]["start"] == 50_000_000 and first["target_timerange"]["duration"] == 10_000_000
    assert first["volume"] == 1.0                                       # short giữ nguyên tiếng gốc
    rest = [s for s in video["segments"] if s is not first]
    assert rest and all(s["volume"] == 0.0 for s in rest)                # phần review: tiếng phim tắt
    texts = {m["id"]: m for m in content["materials"]["texts"]}
    segs = [s for t in content["tracks"] if t["type"] == "text" for s in t["segments"]]
    in_short = [texts[s["material_id"]]["content"] for s in segs if s["target_timerange"]["start"] < 10_000_000]
    # trên short CHỈ có phụ đề (dịch lời thoại gốc 52–55s → giây 2–5 của video), tiêu đề vào sau short
    shown = [json.loads(c)["text"] for c in in_short]
    assert shown[:2] == ["거기 서!", "도망가지 마!"], shown
    assert set(shown[2:]) <= {"Đứng lại! Đừng chạy!"}                       # + chữ vàng tiếng Việt để kiểm tra (nếu bật)
    first_sub = min(s["target_timerange"]["start"] for s in segs if s["target_timerange"]["start"] < 10_000_000)
    assert first_sub == 2_000_000
    sub_call = [c for c in r._director.calls if c["task"] == "cliff_hook_subs"]
    assert len(sub_call) == 1 and "待て！逃げるな！" in sub_call[0]["prompt"]    # phần 2: short không có thoại
    saved = json.loads((jobs / "cl" / "plan" / "hook_subs_video01.json").read_text(encoding="utf-8"))
    assert saved["hook"] == [50.0, 60.0] and saved["lines"][0]["text"].startswith("거기")


def test_hook_subs_same_language_and_lines(tmp_path):
    from app.director.cliff import hook_lines, make_hook_subs
    from app.director.tasks import understand

    segs = [{"start": 48.0, "end": 51.0, "text": "a"}, {"start": 52.0, "end": 55.0, "text": "b"},
            {"start": 59.0, "end": 63.0, "text": "c"}, {"start": 70.0, "end": 71.0, "text": "d"}]
    assert [(x["start"], x["end"], x["src"]) for x in hook_lines(segs, 50, 60)] == \
        [(50, 51.0, "a"), (52.0, 55.0, "b"), (59.0, 60, "c")]                 # cắt gọn vào trong short
    a = make_analysis(tmp_path, duration=60.0)
    u = understand(FakeDirector(), a)                                            # phim tiếng Nhật, review tiếng Nhật
    d = FakeDirector()
    out = make_hook_subs(d, a, u, (0.0, 10.0))
    assert out[0]["text"] == "こんにちは" and not d.calls                       # cùng tiếng: dùng nguyên lời gốc


def test_cliff_first_person_prompt(tmp_path):
    jobs, job, r = _run_job(tmp_path, pov="1")
    first = "그날 나는 아무것도 몰랐다. " + SENT.strip()
    r._director.responses["dub_cliff"] = [_script(1, 0.0, text=first), _script(2, 200.0, text=first)]
    r._director.responses["cliff_polish"] = [_script(1, 0.0, text=first), _script(2, 200.0, text=first)]
    job = r.run(job)
    r.apply_segments(job, json.loads((jobs / "cl" / "plan" / "segments.json").read_text(encoding="utf-8"))["videos"])
    job = r.resume(job)
    assert job.step == "dub_voice", job.message
    prompt = next(c for c in r._director.calls if c["task"] == "dub_cliff")["prompt"]
    assert "NGÔI THỨ NHẤT" in prompt and '"Minho"' in prompt


def test_web_form_cliff(tmp_path):
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    client = TestClient(app)
    home = client.get("/").text
    assert "Review bỏ lửng" in home and 'name="cliff_pov"' in home
    r = client.post("/jobs", data={"footage": str(f), "mode": "cliff", "cliff_pov": "1", "target_language": "ja",
                                   "review_s": "90", "hook": "on"}, follow_redirects=False)
    job = Job.load(tmp_path / "jobs", r.headers["location"].rsplit("/", 1)[1])
    o = job.options
    assert o.review and o.cliff and o.cliff_pov == "1" and o.target_language == "ja" and o.review_s == 0
    assert job.picks_segments and not job.use_hook and not o.split
    page = client.get(f"/jobs/{job.job_id}").text
    assert "Review bỏ lửng · ngôi thứ 1" in page
    # chế độ Review cũ không bị ảnh hưởng
    r2 = client.post("/jobs", data={"footage": str(f), "mode": "review", "review_s": "90"}, follow_redirects=False)
    old = Job.load(tmp_path / "jobs", r2.headers["location"].rsplit("/", 1)[1])
    assert old.options.review and not old.options.cliff and not old.picks_segments and old.options.review_s == 90
