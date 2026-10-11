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


def _script(index: int = 1, lines=None) -> dict:
    return {"video_index": index, "lines": [dict(x, kind="dub") for x in (lines or LINES)], "editor_notes": "dịch thoại"}


def _u(a, lo=0.0, hi=60.0):
    u = understand(FakeDirector(), a).dubbed_to("ko")  # phim gốc tiếng Nhật → lồng tiếng Hàn
    return u.model_copy(update={"usable_range": u.usable_range.model_copy(update={"start": lo, "end": hi})})


def test_highlight_segments_for_tiktok(tmp_path):
    a = make_analysis(tmp_path, duration=400.0)
    d = FakeDirector()
    make_segments(d, a, understand(FakeDirector(), a), highlight=True)
    prompt = d.calls[0]["prompt"]
    assert "CHỌN ĐOẠN HAY CHO NGƯỜI XEM TIKTOK" in prompt and "rề rà" in prompt and d.calls[0]["images"]
    cc = config.load("char_dub")
    assert f"{cc['min_video_s']}–{cc['max_video_s']} giây" in prompt


def test_char_dub_script_needs_speaker_per_line(tmp_path):
    """AI dịch thoại + ghi tên nhân vật từng câu; thiếu tên nhân vật hoặc viết lời dẫn → bị yêu cầu sửa."""
    from tests.test_planner import _short_plan

    a = make_analysis(tmp_path, duration=60.0)
    plan = EditPlan.model_validate(_short_plan())
    bad = _script(lines=[dict(LINES[0], speaker=""), *LINES[1:]])
    narr = _script()
    narr["lines"][1]["kind"] = "narration"
    d = FakeDirector(responses={"dub_char": [bad, narr, _script()]})
    s = make_dub(d, a, _u(a), plan, mode="char")
    assert d.calls[0]["task"] == "dub_char" and "NHẬN DIỆN NHÂN VẬT" in d.calls[0]["prompt"].upper()
    assert "thiếu `speaker`" in d.calls[1]["prompt"] and "không có lời dẫn" in d.calls[2]["prompt"]
    assert [ln.speaker for ln in s.lines] == ["징징이", "스펀지밥", "징징이", "스펀지밥"]
    assert dub_io.speakers_of(s) == {"징징이": [1, 3], "스펀지밥": [2, 4]}


def test_char_plan_keeps_speed_and_length(tmp_path):
    from tests.test_review import _clips, _plan

    a = make_analysis(tmp_path, duration=400.0)
    u = _u(a, 0.0, 400.0)
    style = {"char_dub": config.load("char_dub")}
    fast = _plan(1, [dict(c, speed=1.5) for c in _clips(1.0, 40)])      # tua nhanh → không khớp miệng
    good = _plan(1, _clips(1.0, 40))                                      # 100 giây, tốc độ 1.0
    d = FakeDirector(responses={"plan": [fast, good]})
    make_plan(d, a, u, style)
    assert "LỒNG TIẾNG NHÂN VẬT" in d.calls[0]["prompt"] and "rề rà" in d.calls[0]["prompt"]
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
    from tests.test_review import _clips, _plan

    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/anime.mp4")], JobOptions(char_dub=True, target_language="ko", hook=True),
                     job_id="cd")
    assert not job.use_hook and job.applies("review_segments") and job.applies("dub")
    make_analysis(jobs / "cd", duration=400.0)
    r = make_runner(tmp_path, jobs)
    bgm_calls = []
    monkeypatch.setattr(type(r), "_bgm", lambda self, job, analysis: bgm_calls.append(job.job_id) or None)
    u = load("understand.json")
    u["usable_range"] = {"start": 0.0, "end": 400.0}
    seg = {"videos": [{"start": 1.0, "end": 150.0, "title_vi": "a", "summary_vi": "a", "why_vi": "cãi nhau rất hài"}],
           "dropped": [{"start": 150.0, "end": 400.0, "reason_vi": "rề rà"}], "editor_notes": "1 đoạn hay"}
    r._director = FakeDirector(responses={"understand": u, "segment": seg, "plan": _plan(1, _clips(1.0, 40)),
                                          "dub_char": _script(1, [dict(x, source_start=x["source_start"] - 1.0,
                                                                       source_end=x["source_end"] - 1.5)
                                                                  for x in LINES]),
                                          "captions": load("captions.json")})
    job = r.run(job)
    assert job.step == "review_segments" and job.status == Status.waiting, job.message
    assert "CHỌN ĐOẠN HAY CHO NGƯỜI XEM TIKTOK" in [c for c in r._director.calls if c["task"] == "segment"][0]["prompt"]
    r.apply_segments(job, json.loads((jobs / "cd" / "plan" / "segments.json").read_text(encoding="utf-8"))["videos"])
    job = r.resume(job)
    assert job.step == "dub_voice" and job.status == Status.waiting, job.message
    assert any(c["task"] == "dub_char" for c in r._director.calls)
    txt = (jobs / "cd" / "dub_scripts.txt").read_text(encoding="utf-8")
    assert "🎭 THU THEO NHÂN VẬT" in txt and "징징이: 2 câu" in txt
    style = r._style(job)
    assert style.get("char_dub") and not style.get("remix") and "mirror" not in style  # hình giữ tự nhiên
    from fastapi.testclient import TestClient

    from app.web.server import create_app

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
