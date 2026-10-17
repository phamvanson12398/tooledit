"""Chế độ Bán content: kịch bản mới + cảnh đảo theo lời, voice + nhạc mới, đóng gói đủ file vào dự án CapCut."""

import json
from pathlib import Path

from app.director.fake import FakeDirector
from app.director.schemas import DubScript, SellScript
from app.director.sell import check_sell_script, sell_plan, sell_target, sell_to_dub
from app.jobs.job import JobOptions, Status
from app.planner.sell_sync import build_sell
from tests.test_planner import _short_plan
from tests.test_runner import make_runner as _make_runner, prepare

FIX = json.loads((Path(__file__).parent / "fixtures" / "director" / "sell.json").read_text(encoding="utf-8"))
CFG = {"voice_gap_s": 0.08, "cut_s": 2.2, "min_cut_s": 1.0, "max_cut_s": 4.0, "min_speed": 0.85, "min_s": 60.5,
       "reuse_gap": 2, "reuse_mirror": True, "script_fill": [0.97, 1.08]}
SCENES = [{"start": 0.0, "end": 60.0}]


def _check(r, **kw):
    args = {"duration": 60.0, "scenes": SCENES, "cps": 10.0, "target_s": 65.0, "cfg": CFG, "title_max": 12}
    return check_sell_script(r, "ko", **{**args, **kw})


def test_sell_target_always_over_60():
    assert sell_target({"default_s": 65, "min_s": 60.5}) == 65
    assert sell_target({"default_s": 65, "min_s": 60.5}, 30) == 60.5
    assert sell_target({"default_s": 65, "min_s": 60.5}, 70) == 70


def test_check_sell_script():
    r = SellScript.model_validate(FIX)
    assert _check(r) == []
    lines = FIX["lines"]
    bad = SellScript.model_validate({**FIX, "lines": [{**lines[1], "role": "body"}, *lines[1:-1],
                                                      {**lines[-1], "shots": [{"start": 58, "end": 64}]}]})
    errs = _check(bad)
    assert any("câu 1 phải có role" in e for e in errs) and any("ngoài video gốc" in e for e in errs)
    assert any("cần" in e and "chữ" in e for e in _check(SellScript.model_validate({**FIX, "lines": lines[:4]})))
    two = [{"start": 0.0, "end": 31.0}, {"start": 31.0, "end": 60.0}]
    assert any("vắt qua điểm đổi cảnh" in e for e in _check(r, scenes=two))
    jp = SellScript.model_validate({**FIX, "lines": [{**lines[0], "text": "この店が一日で完売した理由、知っていますか？"},
                                                     *lines[1:]]})
    assert any("KHÔNG viết bằng" in e for e in _check(jp))
    cta_mid = SellScript.model_validate({**FIX, "lines": [lines[0], lines[-1], *lines[1:-1]]})
    assert any("CUỐI" in e for e in _check(cta_mid))


def test_sell_to_dub_and_plan():
    r = SellScript.model_validate(FIX)
    s = sell_to_dub(r)
    assert isinstance(s, DubScript) and len(s.lines) == len(r.lines) and s.story_vi  # cả bài đọc liền một mạch
    assert s.lines[0].role == "hook" and s.lines[0].shots[0].start == 30
    plan = sell_plan(r)
    assert plan.titles_top == ["하루 만에 완판", "이 집의 비밀"] and len(plan.clips) == sum(len(x.shots) for x in r.lines)


def test_build_sell_fits_voice_and_reuses_with_mirror():
    s = sell_to_dub(SellScript.model_validate(FIX))
    voice = {i: 4.5 for i in range(1, len(s.lines) + 1)}  # mỗi câu đọc 4.5s
    sc = [{"start": float(a), "end": float(a + 6)} for a in range(0, 60, 6)]
    clips, windows, notes = build_sell(s, voice, sc, 60.0, cps=7.0, cfg=CFG)
    total = sum((c.source_end - c.source_start) / c.speed for c in clips)
    assert total >= 60.5 and len(windows) == len(s.lines)
    starts = [w[0] for w in windows]
    assert starts == sorted(starts) and starts[0] == 0
    for a, b in zip(starts, starts[1:]):  # câu sau bắt đầu sau khi câu trước đọc xong + nghỉ
        assert b - a >= round((4.5 + 0.08) * 1e6) - 2
    assert all(c.speed >= 0.85 - 1e-6 for c in clips)
    assert all((c.source_end - c.source_start) / c.speed <= 4.0 * 1.3 for c in clips)
    assert any(c.mirror for c in clips)  # câu cuối dùng lại cảnh của câu 1 → phản chiếu ngang
    assert "Dựng theo voice" in notes[0]
    clips2, _, _ = build_sell(s, voice, sc, 60.0, cps=7.0, cfg=CFG, allow_mirror=False)
    assert not any(c.mirror for c in clips2)


def test_build_sell_order_follows_script_not_source():
    s = sell_to_dub(SellScript.model_validate(FIX))
    clips, _, _ = build_sell(s, {i: 3.0 for i in range(1, 13)}, SCENES, 60.0, cps=7.0, cfg=CFG)
    assert 30 <= clips[0].source_start < 34  # câu hook chạy trên cảnh AI chọn (giây 30), không phải đầu video


def make_runner(tmp_path, jobs):
    r = _make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan()})
    return r


def test_full_sell_job_packs_media_and_separate_audio_tracks(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(sell=True, target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "dub_voice", job.message
    calls = [c["task"] for c in r.director.calls]
    assert "sell" in calls and "plan" not in calls  # một lượt AI ra cả kịch bản + cảnh + tiêu đề + nhạc
    prompt = next(c["prompt"] for c in r.director.calls if c["task"] == "sell")
    assert "tự quyết hoàn toàn theo nội dung gốc" in prompt and "65 giây" in prompt  # 15/10: không còn ô định hướng
    script = (jobs / "j1" / "dub_scripts.txt").read_text(encoding="utf-8")
    assert "BÀI LỜI ĐỌC" in script and "video01_dub12.wav" in script
    vdir = jobs / "j1" / "voice"
    for n in range(1, 19):
        (vdir / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    draft = Path(job.data["draft"])
    assert job.data["duration_s"] >= 60.5
    content = json.loads((draft / "draft_content.json").read_text(encoding="utf-8"))
    audios = {m["id"]: m for m in content["materials"]["audios"]}
    voice_paths = [m["path"] for m in audios.values() if "video01_dub" in m.get("name", "")]
    assert len(voice_paths) == 18
    assert all(Path(p).parent == draft / "media" for p in voice_paths)  # voice đã chép vào thư mục dự án
    assert (draft / "media" / "video01_dub01.wav").is_file()
    tracks = [t for t in content["tracks"] if t["type"] == "audio"]
    voice_tracks = [t for t in tracks if any("video01_dub" in audios[s["material_id"]].get("name", "")
                                             for s in t["segments"])]
    assert len(voice_tracks) == 1  # voice nằm trên MỘT track riêng
    assert all("video01_dub" in audios[s["material_id"]].get("name", "") for s in voice_tracks[0]["segments"])
    vids = {m["id"]: m for m in content["materials"]["videos"]}
    assert all(s["volume"] == 0.0 for t in content["tracks"] if t["type"] == "video" for s in t["segments"]
               if vids.get(s["material_id"], {}).get("type") == "video")  # âm thanh gốc tắt hẳn


def test_writer_tolerates_tiny_overrun(tmp_path):
    from app.capcut_writer import DraftTemplate, VideoSource
    from app.capcut_writer.writer import DraftWriter
    from tests.test_planner import SAMPLE

    w = DraftWriter(DraftTemplate(SAMPLE), tmp_path, "x")
    src = VideoSource(Path("C:/f/cctv.mp4"), 1920, 1080, 184_227_120)
    seg = w.add_video(src, target_start=0, duration=58_980_000, source_start=125_250_000)  # lố 3 ms
    assert seg["source_timerange"]["start"] + seg["source_timerange"]["duration"] <= 184_227_120


def test_voice_and_music_on_separate_audio_tracks(tmp_path):
    from app.capcut_writer import DraftTemplate
    from app.capcut_writer.writer import DraftWriter
    from tests.test_planner import SAMPLE

    w = DraftWriter(DraftTemplate(SAMPLE), tmp_path, "x")
    f = tmp_path / "a.wav"
    f.write_bytes(b"RIFF")
    w.add_local_audio(f, 10_000_000, target_start=0, duration=10_000_000, lane="music")
    w.add_local_audio(f, 2_000_000, target_start=10_000_000, duration=2_000_000, lane="voice")  # không chồng nhạc
    w.add_local_audio(f, 2_000_000, target_start=12_000_000, duration=2_000_000, lane="voice")
    tracks = [t for t in w.build_timeline()["tracks"] if t["type"] == "audio"]
    assert [len(t["segments"]) for t in tracks] == [1, 2]  # nhạc một track, voice một track — dù không chồng nhau


def test_home_sell_mode(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    client = TestClient(app)
    home = client.get("/").text
    assert "name='mode' value='sell'" in home and "65 giây (mặc định)" in home
    assert "sell_brief" not in home  # chủ dự án 15/10: bỏ ô định hướng — AI tự viết theo nội dung gốc
    import re

    from app.web.server import MODES

    box = re.search(r'<div data-modes="([^"]+)">\s*<h3>Chọn video</h3>', home)
    assert box and set(box.group(1).split()) == set(MODES) - {"films"}  # mọi chế độ (trừ nhiều phim) đều có ô chọn file
    r = client.post("/jobs", data={"footage": str(f), "mode": "sell", "target_language": "ja", "hook": "on",
                                   "split": "on", "sell_s": "70"}, follow_redirects=False)
    o = Job.load(tmp_path / "jobs", r.headers["location"].rsplit("/", 1)[1]).options
    assert o.sell and not o.sell_brief and o.sell_s == 70 and o.target_language == "ja"
    assert not o.hook and not o.split
    assert "Chưa chọn ngôn ngữ" in client.post("/jobs", data={"footage": str(f), "mode": "sell"}).text
    page = client.get(r.headers["location"]).text
    assert "💰 Bán content" in page and "1:10" in page


def _wav(path, secs):
    import wave

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * int(8000 * secs))


def test_short_voice_stops_and_lengthen_rewrites(tmp_path, monkeypatch):
    """Chủ dự án 15/10: voice thiếu (chỉ phủ nửa video) → không chèn cảnh câm im lặng, dừng hỏi viết dài thêm."""
    from app import settings

    saved = {}
    monkeypatch.setattr(settings, "load", lambda: dict(saved))
    monkeypatch.setattr(settings, "save", lambda upd: saved.update(upd))
    jobs, job = prepare(tmp_path, JobOptions(sell=True, target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    vdir = jobs / "j1" / "voice"
    for n in range(1, 19):
        _wav(vdir / f"video01_dub{n:02d}.wav", 1.8)  # cả bài ~33s, giọng đọc nhanh hơn dự tính
    job = r.resume(job)
    assert job.status == Status.waiting and job.step == "dub_voice" and "Voice chưa đủ dài" in job.message
    short = r.sell_short_voice(job)[1]
    assert 30 < short["voice_s"] < 36 and short["rate"] > 15 and short["extra_chars"] > 300
    from app.director import sell as sell_mod

    monkeypatch.setattr(sell_mod, "check_sell_script", lambda *a, **k: [])  # độ dài đã có test riêng
    r.sell_lengthen(job, 1)
    assert saved["sell_voice_cps"]["ko"] > 15  # nhớ tốc độ giọng thật → lần viết sau đủ chữ
    sell_prompts = [c["prompt"] for c in r.director.calls if c["task"] == "sell"]
    assert len(sell_prompts) == 2 and "Viết DÀI HƠN" in sell_prompts[1] and "cần viết THÊM khoảng" in sell_prompts[1]
    assert (vdir / "video01_dub01_cu.wav").is_file() and not (vdir / "video01_dub01.wav").exists()
    for n in range(1, 19):
        _wav(vdir / f"video01_dub{n:02d}.wav", 1.8)
    job.data["sell_accept_short"] = True  # nút "Vẫn dựng với voice này"
    job = r.resume(job)
    assert job.status == Status.done, job.message


def test_subtitles_on_screen_prompt(tmp_path):
    """Có phụ đề in trên hình → AI đọc từng dòng, viết bám sát; không có → viết theo hình ảnh."""
    from app.director.schemas import Understanding
    from app.director.sell import make_sell_script
    from tests.test_director import GOOD, make_analysis

    a = make_analysis(tmp_path)
    for subs, want in ((True, "BÁM SÁT phụ đề"), (False, "viết theo HÌNH ẢNH")):
        u = Understanding.model_validate({**GOOD, "burned_in_text": {"present": subs, "regions": ["bottom"]}}
                                         ).dubbed_to("ko")
        d = FakeDirector()
        make_sell_script(d, a, u, brief="", music_items=[])
        assert want in d.calls[0]["prompt"]


def test_many_scenes_no_division_by_zero(tmp_path):
    """Chủ dự án 17/10: "Lỗi ở bước plan: division by zero" — video game cắt cảnh gần như mỗi giây: khung đầu mỗi cảnh đã
    nhiều hơn số khung gửi AI → trước đây xin thêm 0 khung và chia cho 0."""
    from app.director.schemas import Understanding
    from app.director.sell import make_sell_script
    from app.director.tasks import pick_evenly
    from tests.test_director import GOOD, make_analysis

    assert pick_evenly([1, 2, 3], 0) == [] and pick_evenly([1, 2, 3], -2) == []
    a = make_analysis(tmp_path)
    sc = json.loads((a / "scenes.json").read_text(encoding="utf-8"))
    sc[0]["scenes"] = [{"index": i, "start": i * 1.0, "end": i + 1.0} for i in range(60)]  # 60 cảnh / 60 giây
    (a / "scenes.json").write_text(json.dumps(sc), encoding="utf-8")
    u = Understanding.model_validate(GOOD).dubbed_to("ko")
    d = FakeDirector()
    make_sell_script(d, a, u, brief="", music_items=[])
    times = [float(Path(p).stem.split("_")[1]) for p in d.calls[0]["images"]]
    assert len(times) <= 40 and max(times) > 50  # rải đều tới cuối video, không chỉ phần đầu
