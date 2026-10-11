"""Chế độ "Lồng tiếng nhân vật" (chủ dự án yêu cầu 11/10): chọn đoạn hay TikTok, dịch thoại từng nhân vật (vd Nhật → Hàn),
thu voice theo nhân vật, giữ nhạc + tiếng nền gốc (chỉ thay tiếng nói)."""

import json
from pathlib import Path

import numpy as np
import pytest

from app import config
from app.director.fake import FakeDirector
from app.director.schemas import DubScript, EditPlan
from app.director.tasks import make_dub, make_plan, make_segments, understand
from app.jobs.job import Job, JobOptions, Status
from app.planner import dub_io
from tests.test_director import make_analysis
from tests.test_planner import load
from tests.test_runner import make_runner
from tests.test_voice_sync import _silence, _tone

LINES = [  # 4 câu thoại, 2 nhân vật — nằm trong clip 1–45s của _short_plan
    {"source_start": 2.0, "source_end": 5.0, "text": "야, 너 어디 가?", "text_vi": "Ê, cậu đi đâu đấy?", "speaker": "징징이"},
    {"source_start": 6.0, "source_end": 9.0, "text": "비밀이야!", "text_vi": "Bí mật!", "speaker": "스펀지밥"},
    {"source_start": 10.0, "source_end": 14.0, "text": "또 사고 치려고?", "text_vi": "Lại định gây chuyện à?",
     "speaker": "징징이"},
    {"source_start": 15.0, "source_end": 19.0, "text": "이번엔 진짜 아니야!", "text_vi": "Lần này thật sự không mà!",
     "speaker": "스펀지밥"},
]


MOMENTS = [{"start": 1.0, "end": 19.0, "note_vi": "cãi nhau"}, {"start": 30.0, "end": 45.0, "note_vi": "cú hài"},
           {"start": 50.0, "end": 65.0}, {"start": 70.0, "end": 85.0}, {"start": 90.0, "end": 105.0, "note_vi": "bất ngờ"}]
SEG = {"videos": [{"start": 1.0, "end": 105.0, "title_vi": "a", "summary_vi": "a", "why_vi": "cãi nhau rất hài",
                   "moments": MOMENTS}],
       "dropped": [{"start": 150.0, "end": 400.0, "reason_vi": "rề rà"}], "editor_notes": "1 video 5 tình huống"}


def _talk(analysis_dir: Path, lines=None, shift=(0.0, 0.0)) -> None:
    """Lời thoại gốc (Whisper) trùng các câu mẫu — mốc giờ câu lồng tiếng lấy từ đây."""
    segs = [{"start": x["source_start"] + shift[0], "end": x["source_end"] + shift[1], "text": f"台詞{i}", "words": []}
            for i, x in enumerate(lines or LINES, 1)]
    (analysis_dir / "transcript.json").write_text(json.dumps([{"footage": 0, "language": "ja", "segments": segs}]),
                                                  encoding="utf-8")


def _script(index: int = 1, lines=None) -> dict:
    return {"video_index": index, "lines": [dict(x, kind="dub") for x in (lines or LINES)], "editor_notes": "dịch thoại"}


def _u(a, lo=0.0, hi=60.0):
    u = understand(FakeDirector(), a).dubbed_to("ko")  # phim gốc tiếng Nhật → lồng tiếng Hàn
    return u.model_copy(update={"usable_range": u.usable_range.model_copy(update={"start": lo, "end": hi})})


def test_highlight_segments_are_short_situations(tmp_path):
    """Chủ dự án yêu cầu 11/10: chọn từng TÌNH HUỐNG 10–20 giây rồi ghép thành video, không lấy một khúc 80 giây liền."""
    a = make_analysis(tmp_path, duration=400.0)
    u = understand(FakeDirector(), a)
    u = u.model_copy(update={"usable_range": u.usable_range.model_copy(update={"start": 0.0, "end": 400.0})})
    one_block = {**SEG, "videos": [dict(SEG["videos"][0], moments=[{"start": 1.0, "end": 85.0}])]}
    no_moments = {**SEG, "videos": [{k: v for k, v in SEG["videos"][0].items() if k != "moments"}]}
    off = {**SEG, "videos": [dict(SEG["videos"][0], start=0.0, end=120.0)]}  # start/end lệch → tự sửa theo tình huống
    d = FakeDirector(responses={"segment": [one_block, no_moments, off]})
    sp = make_segments(d, a, u, highlight=True)
    prompt = d.calls[0]["prompt"]
    assert "CHỌN TÌNH HUỐNG HAY CHO NGƯỜI XEM TIKTOK" in prompt and "rề rà" in prompt and d.calls[0]["images"]
    cc = config.load("char_dub")
    assert f"{cc['min_video_s']}–{cc['max_video_s']} giây" in prompt and "10–20 giây" in prompt
    assert "dài 84s" in d.calls[1]["prompt"] and "thiếu `moments`" in d.calls[2]["prompt"]
    v = sp.videos[0]
    assert (v.start, v.end) == (1.0, 105.0) and len(v.moments) == 5


def test_char_dub_script_needs_speaker_per_line(tmp_path):
    """Mỗi câu gốc đúng một câu lồng tiếng (không gộp / bỏ câu → không có chỗ nhân vật mở miệng mà im lặng), mốc giờ
    lấy đúng câu gốc (khớp miệng) dù AI ghi lệch, câu nào cũng có tên nhân vật."""
    from tests.test_planner import _short_plan

    a = make_analysis(tmp_path, duration=60.0)
    _talk(a)
    plan = EditPlan.model_validate(_short_plan())
    bad = _script(lines=[dict(LINES[0], speaker=""), *LINES[1:]])
    merged = _script(lines=LINES[:3])                                      # AI gộp / bỏ một câu
    off = _script(lines=[dict(x, source_start=x["source_start"] + 0.7, source_end=x["source_end"] - 0.4) for x in LINES])
    off["lines"][1]["kind"] = "narration"
    d = FakeDirector(responses={"dub_char": [bad, merged, off]})
    s = make_dub(d, a, _u(a), plan, mode="char")
    assert d.calls[0]["task"] == "dub_char" and "NHẬN DIỆN NHÂN VẬT" in d.calls[0]["prompt"].upper()
    assert "4 câu thoại gốc cần dịch" in d.calls[0]["prompt"] and "1. [2.00–5.00s, 3.0s] 台詞1" in d.calls[0]["prompt"]
    assert "thiếu `speaker`" in d.calls[1]["prompt"] and "trả ĐÚNG 4 câu" in d.calls[2]["prompt"]
    assert [(ln.source_start, ln.source_end) for ln in s.lines] == [(x["source_start"], x["source_end"]) for x in LINES]
    assert all(ln.kind == "dub" for ln in s.lines)
    assert [ln.speaker for ln in s.lines] == ["징징이", "스펀지밥", "징징이", "스펀지밥"]
    assert dub_io.speakers_of(s) == {"징징이": [1, 3], "스펀지밥": [2, 4]}


def test_source_lines_from_transcript():
    """Câu gốc: theo clip được giữ, câu dài tách ở chỗ ngắt, câu vắt mép clip bị cắt theo clip."""
    from app.director.schemas import PlanClip
    from app.planner.char_lines import source_lines

    words = [{"start": 10.0 + k * 0.5, "end": 10.4 + k * 0.5, "word": w} for k, w in enumerate("ああああ、いいいいいい")]
    words[5]["start"] += 0.8  # khoảng lặng sau dấu phẩy
    segs = [{"start": 1.0, "end": 3.0, "text": "おい", "words": []},
            {"start": 10.0, "end": words[-1]["end"], "text": "ああああ、いいいいいい", "words": words},
            {"start": 29.0, "end": 32.0, "text": "またね", "words": []},
            {"start": 50.0, "end": 52.0, "text": "（ngoài clip）", "words": []}]
    clips = [PlanClip(source_start=0.5, source_end=20.0), PlanClip(source_start=30.0, source_end=40.0)]
    got = source_lines(segs, clips, max_s=4.0)
    assert got[0] == {"start": 1.0, "end": 3.0, "text": "おい"}
    assert [x["text"] for x in got[1:3]] == ["ああああ、", "いいいいいい"]          # tách ở dấu phẩy + khoảng lặng
    assert got[3] == {"start": 30.0, "end": 32.0, "text": "またね"} and len(got) == 4  # cắt theo mép clip


def test_char_plan_clips_are_the_situations(tmp_path):
    """Kế hoạch dựng ghép ĐÚNG các tình huống đã duyệt (mỗi tình huống một clip, tốc độ 1.0), dù AI viết clip khác."""
    from tests.test_review import _clips, _plan

    a = make_analysis(tmp_path, duration=400.0)
    u = _u(a, 1.0, 105.0)
    d = FakeDirector(responses={"plan": _plan(1, _clips(1.0, 40))})
    plan = make_plan(d, a, u, {"char_dub": config.load("char_dub")}, moments=MOMENTS)
    assert [(c.source_start, c.source_end, c.speed) for c in plan.clips] == \
        [(m["start"], m["end"], 1.0) for m in MOMENTS]
    assert "CÁC TÌNH HUỐNG ĐÃ DUYỆT" in d.calls[0]["prompt"] and "30.0–45.0s (15s) — cú hài" in d.calls[0]["prompt"]


def test_char_plan_keeps_speed_and_length(tmp_path):
    from tests.test_review import _clips, _plan

    a = make_analysis(tmp_path, duration=400.0)
    u = _u(a, 0.0, 400.0)
    style = {"char_dub": config.load("char_dub")}
    fast = _plan(1, [dict(c, speed=1.5) for c in _clips(1.0, 40)])      # tua nhanh → không khớp miệng
    good = _plan(1, _clips(1.0, 40))                                      # 100 giây, tốc độ 1.0
    d = FakeDirector(responses={"plan": [fast, good]})
    make_plan(d, a, u, style)
    assert "LỒNG TIẾNG NHÂN VẬT" in d.calls[0]["prompt"] and "CHỈ CHỌN ĐOẠN HAY, KHÔNG EDIT" in d.calls[0]["prompt"]
    assert len(d.calls) == 2 and "không dùng replay / tua nhanh" in d.calls[1]["prompt"]


def test_upload_one_file_per_character(tmp_path):
    """Mỗi nhân vật một file (đọc hết câu của nhân vật đó, nghỉ ~1 giây) → tool cắt đúng vào các câu của nhân vật."""
    ff = pytest.importorskip("imageio_ffmpeg").get_ffmpeg_exe()
    from tests.test_planner import _short_plan
    from app.planner.voice_split import write_wav

    d = tmp_path / "job"
    (d / "plan").mkdir(parents=True)
    dub_io.dub_path(d, 1).write_text(json.dumps(_script()), encoding="utf-8")
    (d / "plan" / "edit_plan_video01.json").write_text(json.dumps(_short_plan()), encoding="utf-8")
    src = tmp_path / "squid.wav"
    write_wav(src, np.concatenate([_tone(2.0), _silence(1.0), _tone(3.0, 330), _silence(0.5)]))
    got = dub_io.split_upload_speaker(d, 1, "징징이", src, exe=ff)
    assert len(got) == 2
    assert (d / "voice" / "video01_dub01.wav").is_file() and (d / "voice" / "video01_dub03.wav").is_file()
    assert not (d / "voice" / "video01_dub02.wav").exists()             # câu của 스펀지밥 chưa thu
    assert abs(dub_io.voice_seconds(d / "voice" / "video01_dub03.wav") - 3.0) < 0.3
    with pytest.raises(ValueError):
        dub_io.split_upload_speaker(d, 1, "Không có ai", src, exe=ff)
    assert dub_io.set_speakers(d, 1, {2: "뚱이"}) == 1                 # AI đoán nhầm → sửa tên nhân vật
    assert dub_io.speakers_of(dub_io.load_dub(d, 1))["뚱이"] == [2]


def test_char_dub_job_end_to_end(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.web.server import create_app
    from tests.test_review import _clips, _plan

    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/anime.mp4")], JobOptions(char_dub=True, target_language="ko", hook=True),
                     job_id="cd")
    assert not job.use_hook and job.applies("review_segments") and job.applies("dub")
    _talk(make_analysis(jobs / "cd", duration=400.0), shift=(-1.0, -1.5))
    r = make_runner(tmp_path, jobs)
    bgm_calls = []
    monkeypatch.setattr(type(r), "_bgm", lambda self, job, analysis: bgm_calls.append(job.job_id) or None)
    u = load("understand.json")
    u["usable_range"] = {"start": 0.0, "end": 400.0}
    r._director = FakeDirector(responses={"understand": u, "segment": SEG, "plan": _plan(1, _clips(1.0, 40)),
                                          "dub_char": _script(1, [dict(x, source_start=x["source_start"] - 1.0,
                                                                       source_end=x["source_end"] - 1.5)
                                                                  for x in LINES]),
                                          "captions": load("captions.json")})
    job = r.run(job)
    assert job.step == "review_segments" and job.status == Status.waiting, job.message
    assert "CHỌN TÌNH HUỐNG HAY" in [c for c in r._director.calls if c["task"] == "segment"][0]["prompt"]
    page = TestClient(create_app(jobs, lambda root, log: None)).get("/jobs/cd").text
    assert "5 tình huống" in page and "30.0–45.0s" in page and "cú hài" in page   # bảng duyệt hiện từng tình huống
    rows = json.loads((jobs / "cd" / "plan" / "segments.json").read_text(encoding="utf-8"))["videos"]
    r.apply_segments(job, [{k: v for k, v in rows[0].items() if k != "moments"}])  # form web không gửi tình huống
    assert len(job.data["videos"][0]["moments"]) == 5                              # → vẫn giữ tình huống AI chọn
    job = r.resume(job)
    plan = EditPlan.model_validate_json((jobs / "cd" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    assert [(c.source_start, c.source_end) for c in plan.clips] == [(m["start"], m["end"]) for m in MOMENTS]
    assert job.step == "dub_voice" and job.status == Status.waiting, job.message
    assert any(c["task"] == "dub_char" for c in r._director.calls)
    txt = (jobs / "cd" / "dub_scripts.txt").read_text(encoding="utf-8")
    assert "🎭 THU THEO NHÂN VẬT" in txt and "징징이: 2 câu" in txt
    style = r._style(job)
    assert style.get("char_dub") and not style.get("remix") and "mirror" not in style  # hình giữ tự nhiên
    page = TestClient(create_app(jobs, lambda root, log: None)).get("/jobs/cd").text
    assert "Thu voice theo nhân vật" in page and "Tải giọng 징징이" in page and "Sửa tên người nói" in page
    for n in range(1, 5):
        (jobs / "cd" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    assert bgm_calls  # có tách nhạc + tiếng nền gốc (Demucs) để giữ, chỉ thay tiếng nói


def test_web_char_dub(tmp_path):
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    client = TestClient(app)
    assert "Lồng tiếng nhân vật" in client.get("/").text
    assert "Chưa chọn ngôn ngữ" in client.post("/jobs", data={"footage": str(f), "char_dub": "on"}).text
    r = client.post("/jobs", data={"footage": str(f), "char_dub": "on", "target_language": "ko", "hook": "on"},
                    follow_redirects=False)
    job = Job.load(tmp_path / "jobs", r.headers["location"].rsplit("/", 1)[1])
    assert job.options.char_dub and job.options.target_language == "ko" and not job.use_hook
    page = client.get(f"/jobs/{job.job_id}").text
    assert "🎭 Lồng tiếng nhân vật" in page and "AI dịch thoại + nhận diện nhân vật" in page


def test_char_dub_keeps_original_voice_where_not_dubbed_and_no_edits(tmp_path, monkeypatch):
    """Chủ dự án 11/10: (1) chỗ nhân vật mở miệng mà không có câu lồng (tiếng cười, hét…) giữ GIỌNG GỐC, tắt đúng trong
    các câu lồng tiếng; (2) chế độ này chỉ chọn đoạn hay — tool bỏ chữ nhấn / filter / zoom / SFX AI lỡ thêm."""
    from fastapi.testclient import TestClient  # noqa: F401  (giữ cùng môi trường với test end-to-end)

    from app.planner.voice_split import write_wav
    from tests.test_review import _clips, _plan

    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/anime.mp4")], JobOptions(char_dub=True, target_language="ko"), job_id="cv")
    a = make_analysis(jobs / "cv", duration=400.0)
    _talk(a, shift=(-1.0, -1.5))
    audio = a / "audio"
    audio.mkdir(parents=True)
    write_wav(audio / "bgm_00.wav", np.zeros(48000, dtype=np.int16))
    write_wav(audio / "vocals_00.wav", np.zeros(48000, dtype=np.int16))
    r = make_runner(tmp_path, jobs)
    monkeypatch.setattr(type(r), "_bgm", lambda self, job, analysis: (analysis / "audio" / "bgm_00.wav").resolve())
    monkeypatch.setattr(type(r), "_transcribe", lambda self, *a: (_ for _ in ()).throw(RuntimeError("không có model")))
    u = load("understand.json")
    u["usable_range"] = {"start": 0.0, "end": 400.0}
    busy = {**_plan(1, _clips(1.0, 40)), "emphasis": [{"source_time": 31.0, "text": "와"}], "filter": "Film"}
    r._director = FakeDirector(responses={"understand": u, "segment": SEG, "plan": busy,
                                          "dub_char": _script(1, [dict(x, source_start=x["source_start"] - 1.0,
                                                                       source_end=x["source_end"] - 1.5)
                                                                  for x in LINES]),
                                          "captions": load("captions.json")})
    job = r.run(job)
    r.apply_segments(job, json.loads((jobs / "cv" / "plan" / "segments.json").read_text(encoding="utf-8"))["videos"])
    job = r.resume(job)
    plan = EditPlan.model_validate_json((jobs / "cv" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    assert not plan.emphasis and plan.filter is None and not plan.zooms and not plan.sfx and not plan.effects
    for n in range(1, 5):
        write_wav(jobs / "cv" / "voice" / f"video01_dub{n:02d}.wav", np.zeros(48000 * 2, dtype=np.int16))
    job = r.resume(job)
    assert job.status == Status.done, job.message
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    voc = {m["id"] for m in content["materials"]["audios"] if m.get("path", "").endswith("vocals_00.wav")}
    segs = [s for t in content["tracks"] if t["type"] == "audio" for s in t["segments"] if s["material_id"] in voc]
    assert len(segs) == len(MOMENTS)                                     # mỗi tình huống một đoạn giọng gốc
    first = segs[0]["common_keyframes"][0]["keyframe_list"]
    assert min(k["values"][0] for k in first) == 0.0 and max(k["values"][0] for k in first) > 0.9  # tắt trong câu lồng


def test_retranscribe_on_separated_vocals(tmp_path, monkeypatch):
    """Chủ dự án 11/10: "nhiều khi không bắt được tiếng gốc" → nhận dạng lại trên giọng đã tách nhạc, VAD nhạy hơn."""
    from app.analysis import transcribe as tr_mod
    from app.analysis.transcribe import Segment, Transcript
    from app.planner.voice_split import write_wav

    calls = []

    class FakeModel:
        def transcribe(self, audio, **kw):
            calls.append(kw)

            class Info:
                language, language_probability, duration = "ja", 0.99, 60.0
            return iter([type("S", (), {"start": 1.0, "end": 2.0, "text": " え？", "words": []})()]), Info()

    t = tr_mod.transcribe(Path("v.wav"), cfg={"model": "x", "device": "cpu"}, factory=lambda *a, **k: FakeModel(),
                          options=config.load("char_dub")["whisper_options"], language="ja")
    assert calls[0]["vad_parameters"]["threshold"] == 0.3 and calls[0]["language"] == "ja"
    assert calls[0]["condition_on_previous_text"] is False and t.segments[0].text == "え？"

    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/anime.mp4")], JobOptions(char_dub=True, target_language="ko"), job_id="rv")
    a = make_analysis(jobs / "rv", duration=400.0)
    _talk(a)                                   # lời thoại cũ: 4 câu trong 2–19s (nằm trong tình huống 1–19s)
    job.data["videos"] = [{"index": 1, "start": 1.0, "end": 45.0,
                           "moments": [{"start": 1.0, "end": 19.0}, {"start": 30.0, "end": 45.0}]}]
    r = make_runner(tmp_path, jobs)
    logs = []
    r.log = logs.append

    def fake_bgm(self, job, analysis):         # như separate_ranges: file giọng nối liền + bố cục
        (analysis / "audio").mkdir(exist_ok=True)
        write_wav(analysis / "audio" / "vocals_concat.wav", np.zeros(4800, dtype=np.int16))
        job.data["bgm_layout"] = [{"start": 1.0, "end": 19.0, "offset": 1.0},
                                  {"start": 30.0, "end": 45.0, "offset": 21.6}]
        return analysis / "audio" / "bgm_00.wav"

    monkeypatch.setattr(type(r), "_bgm", fake_bgm)
    got = []
    concat_segs = [(1.5, 2.0, "え？"), (3.0, 5.0, "台詞A"), (8.0, 9.0, "うわっ"), (12.0, 14.0, "台詞B"),
                   (19.9, 20.4, "đệm"), (22.0, 24.0, "台詞C")]   # 19.9–20.4 = khoảng lặng giữa 2 đoạn → bỏ
    monkeypatch.setattr(type(r), "_transcribe", lambda self, audio, options, language: got.append((audio, language))
                        or Transcript(language="ja", language_probability=1.0, duration=40.0, model="m",
                                      device="cpu", segments=[Segment(start=x, end=y, text=t)
                                                              for x, y, t in concat_segs]))
    r._vocals_transcript(job, a, "ja")
    segs = json.loads((a / "transcript.json").read_text(encoding="utf-8"))[0]["segments"]
    assert got[0][0].name == "vocals_concat.wav" and got[0][1] == "ja"
    assert [(sg["start"], sg["end"], sg["text"]) for sg in segs] == [
        (1.5, 2.0, "え？"), (3.0, 5.0, "台詞A"), (8.0, 9.0, "うわっ"), (12.0, 14.0, "台詞B"), (30.4, 32.4, "台詞C")]
    assert len(json.loads((a / "transcript_mix.json").read_text(encoding="utf-8"))[0]["segments"]) == 4  # bản cũ
    assert any("4 → 5 câu" in m for m in logs)
    r._vocals_transcript(job, a, "ja")
    assert len(got) == 1                                                       # cùng tình huống → làm một lần thôi
    job.data["videos"][0]["moments"].append({"start": 60.0, "end": 70.0})
    r._vocals_transcript(job, a, "ja")
    assert len(got) == 2                                                       # đổi tình huống → làm lại


def test_separate_only_selected_ranges(tmp_path, monkeypatch):
    """Chủ dự án 11/10: tách nhạc cả phim "lâu cực" → chỉ tách các tình huống đã duyệt, đặt lại đúng giây gốc."""
    import shutil
    import wave

    from app.analysis import separate

    ff = pytest.importorskip("imageio_ffmpeg").get_ffmpeg_exe()
    rate = separate.RATE
    t = np.arange(rate * 30) / rate
    src_pcm = (np.sin(2 * np.pi * 440 * t) * 8000).astype(np.int16)
    src = tmp_path / "phim.wav"
    separate._write_stereo(src, np.stack([src_pcm, src_pcm], axis=1))
    monkeypatch.setattr(separate, "available", lambda: True)
    seen = []

    def fake_demucs(cmd, **kw):  # "Demucs" giả: chép nguyên vào cả 2 phần
        joined, out = Path(cmd[-1]), Path(cmd[cmd.index("-o") + 1]) / "htdemucs"
        out.mkdir(parents=True)
        with wave.open(str(joined)) as w:
            seen.append(w.getnframes() / rate)
        shutil.copyfile(joined, out / "no_vocals.wav")
        shutil.copyfile(joined, out / "vocals.wav")
        return type("R", (), {"returncode": 0, "stderr": ""})()

    layout = separate.separate_ranges(src, [(5.0, 8.0), (20.0, 22.0), (8.5, 9.0)], tmp_path / "bgm.wav",
                                      tmp_path / "voc.wav", concat_vocals_dst=tmp_path / "concat.wav", total_s=30.0,
                                      ffmpeg_exe=ff, run=fake_demucs, pad_s=1.0, gap_s=0.5)
    assert [(x["start"], x["end"]) for x in layout] == [(5.0, 9.0), (20.0, 22.0)]  # đoạn sát nhau được gộp
    assert seen[0] < 12.0                                                    # chỉ ~10 giây được tách, không phải 30
    bgm = separate._read_stereo(tmp_path / "bgm.wav")
    assert abs(len(bgm) / rate - 30.0) < 0.01                                # dài bằng video
    loud = lambda a, b: float(np.abs(bgm[int(a * rate):int(b * rate)]).mean())  # noqa: E731
    assert loud(5.2, 8.8) > 2000 and loud(20.2, 21.8) > 2000                 # đúng giây gốc có tiếng
    assert loud(0, 4.9) == 0 and loud(9.1, 19.9) == 0 and loud(22.1, 30) == 0  # ngoài tình huống: im lặng
    whole = np.stack([src_pcm, src_pcm], 1)
    assert np.array_equal(bgm[int(6 * rate):int(7 * rate)], whole[int(6 * rate):int(7 * rate)])  # không lệch giây
    assert separate.to_source_time(layout[1]["offset"] + 0.5, layout) == 20.5
    assert separate.to_source_time(layout[0]["offset"] + 4.3, layout) is None  # phần đệm / khoảng lặng giữa đoạn
