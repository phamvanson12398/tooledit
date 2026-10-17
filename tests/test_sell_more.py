"""Bán content — cải tiến 17/10: giọng Voice Studio tự đọc, nhiều bản, chữ nhấn + tiếng động, không đè chữ in sẵn, AV1."""

import json
import wave
from pathlib import Path

import pytest

from app.director.fake import FakeDirector
from app.director.schemas import SellScript
from app.director.sell import sell_to_dub, variant_brief
from app.jobs.job import JobOptions, Status
from app.planner.sell_sync import sell_fx
from tests.test_director import GOOD
from tests.test_planner import _short_plan
from tests.test_runner import make_runner as _make_runner, prepare

FIX = json.loads((Path(__file__).parent / "fixtures" / "director" / "sell.json").read_text(encoding="utf-8"))
N = len(FIX["lines"])


def _wav(path: Path, secs: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * int(8000 * secs))


@pytest.fixture
def settings_mem(monkeypatch):
    from app import settings

    saved = {}
    monkeypatch.setattr(settings, "load", lambda *a, **k: dict(saved))
    monkeypatch.setattr(settings, "save", lambda upd, *a, **k: saved.update(upd))
    return saved


CAP = json.loads((Path(__file__).parent / "fixtures" / "director" / "captions.json").read_text(encoding="utf-8"))


def make_runner(tmp_path, jobs, understand=None):
    r = _make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan(), "captions": [{**CAP, "video_index": i} for i in (1, 2)],
                                          **({"understand": understand} if understand else {})})
    return r


def _texts(draft: Path) -> list[str]:
    c = json.loads((draft / "draft_content.json").read_text(encoding="utf-8"))
    out = []
    for m in c["materials"]["texts"]:
        try:
            out.append(json.loads(m.get("content", "")).get("text", ""))
        except ValueError:
            out.append(m.get("content", ""))
    return out


def test_sell_fx_keywords_and_sfx():
    s = sell_to_dub(SellScript.model_validate(FIX))
    windows = [(i * 3_000_000, 2.8, 2.8) for i in range(N)]
    fx = sell_fx(s, windows, {"fx": {"sfx_min_gap_s": 2.5}})
    assert [e[2] for e in fx["emphasis"]] == ["완판", "몇 시간", "토핑", "팔로우"]
    assert fx["emphasis"][0][0] == 150_000  # hiện ngay sau khi câu bắt đầu
    assert fx["sfx"][0] == (0, "pop") and {k for _, k in fx["sfx"][1:]} == {"whoosh", "click", "swoosh"}
    assert [k for _, k in fx["sfx"][1:4]] == ["whoosh", "click", "swoosh"]  # đổi câu: luân phiên có cả click
    assert len(fx["sfx"]) == N  # mỗi lần đổi câu (cách ≥ 2.5s) một tiếng
    dense = sell_fx(s, [(i * 1_000_000, 0.9, 0.9) for i in range(N)], {"fx": {"sfx_min_gap_s": 2.5}})
    assert len(dense["sfx"]) < N  # câu ngắn liền nhau → bỏ bớt tiếng, không dồn dập
    assert not sell_fx(s, windows, {}, emphasis=False)["emphasis"]


def test_variant_brief_lists_previous():
    r = SellScript.model_validate(FIX)
    assert variant_brief((1, 1), []) == "(chỉ làm một bản)"
    b = variant_brief((2, 3), [r])
    assert "BẢN 2/3" in b and r.lines[0].text in b and "con số" in b


def test_two_variants_two_drafts_with_keyword_text(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(sell=True, target_language="ko", client_id="k", sell_variants=2))
    r = make_runner(tmp_path, jobs, understand={**GOOD, "burned_in_text": {"present": False, "regions": []}})
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "dub_voice", job.message
    prompts = [c["prompt"] for c in r.director.calls if c["task"] == "sell"]
    assert len(prompts) == 2 and "BẢN 2/2" in prompts[1] and FIX["lines"][0]["text"] in prompts[1]
    for v in (1, 2):
        for n in range(1, N + 1):
            (jobs / "j1" / "voice" / f"video{v:02d}_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    assert [Path(d["draft"]).name for d in job.data["drafts"]] == ["k_j1_video01", "k_j1_video02"]
    texts = _texts(Path(job.data["drafts"][0]["draft"]))
    assert "완판" in texts and "토핑" in texts  # chữ nhấn của câu
    assert any("하루 만에 완판" in t for t in texts)  # có tiêu đề (video không có chữ in sẵn)


def test_burned_in_text_skips_titles_and_subtitles(tmp_path):
    und = {**GOOD, "burned_in_text": {"present": True, "regions": ["top", "bottom"], "note_vi": "tiêu đề + phụ đề"}}
    jobs, job = prepare(tmp_path, JobOptions(sell=True, target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs, understand=und)
    job = r.run(job)
    for n in range(1, N + 1):
        (jobs / "j1" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    texts = _texts(Path(job.data["draft"]))
    assert not any("하루 만에 완판" in t for t in texts)  # không tiêu đề
    assert not any(FIX["lines"][1]["text"][:6] in t for t in texts)  # không phụ đề
    assert "완판" in texts  # chữ nhấn vẫn còn (chữ in sẵn ở trên / dưới, không ở giữa)


def _studio_voice(tmp_path, monkeypatch, consent=True):
    from app.tts import studio

    root = tmp_path / "studio"
    monkeypatch.setattr(studio, "STUDIO", root)
    src = tmp_path / "mau.wav"
    _wav(src, 4.0)
    return studio.save_voice("Giọng A", sample=src, consent=consent, root=root,
                             prepare=lambda s, d, m: (Path(d).write_bytes(Path(s).read_bytes()) and Path(d), False))


def test_studio_voice_reads_automatically(tmp_path, monkeypatch, settings_mem):
    v = _studio_voice(tmp_path, monkeypatch)
    settings_mem["studio_params"] = {"speed": 1.15, "seed": 3}
    jobs, job = prepare(tmp_path, JobOptions(sell=True, target_language="ko", client_id="k", sell_voice=v["slug"]))
    r = make_runner(tmp_path, jobs)
    reqs = []

    def fake_tts(request, request_path, cfg, on_line):
        reqs.append(request)
        for it in request["items"]:
            _wav(Path(it["out"]), 4.0)  # 18 câu × 4s → đủ dài

    r._tts_run = fake_tts
    job = r.run(job)
    assert job.status == Status.done, job.message  # không phải dừng chờ thu voice
    spec = reqs[0]["voices"]["Người dẫn"]
    assert spec["mode"] == "clone" and spec["ref_audio"].endswith("sample.wav") and spec["prompt_cache"].endswith(".pt")
    assert reqs[0]["gen"]["speed"] == 1.15 and reqs[0]["gen"]["seed"] == 3 and len(reqs[0]["items"]) == N


def test_studio_voice_without_consent_waits(tmp_path, monkeypatch, settings_mem):
    v = _studio_voice(tmp_path, monkeypatch, consent=True)
    meta = tmp_path / "studio" / "voices" / v["slug"] / "meta.json"
    m = json.loads(meta.read_text(encoding="utf-8"))
    meta.write_text(json.dumps({**m, "consent": False}), encoding="utf-8")
    jobs, job = prepare(tmp_path, JobOptions(sell=True, target_language="ko", client_id="k", sell_voice=v["slug"]))
    r = make_runner(tmp_path, jobs)
    r._tts_run = lambda *a, **k: pytest.fail("không được clone khi chưa xác nhận quyền")
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "dub_voice" and "chưa xác nhận" in job.data["auto_tts_error"]


def test_studio_voice_short_auto_lengthen_once(tmp_path, monkeypatch, settings_mem):
    from app.director import sell as sell_mod

    v = _studio_voice(tmp_path, monkeypatch)
    jobs, job = prepare(tmp_path, JobOptions(sell=True, target_language="ko", client_id="k", sell_voice=v["slug"]))
    r = make_runner(tmp_path, jobs)
    calls = []

    def fake_tts(request, request_path, cfg, on_line):
        calls.append(len(request["items"]))
        for it in request["items"]:
            _wav(Path(it["out"]), 1.5)  # giọng đọc nhanh → cả bài chỉ ~27s

    r._tts_run = fake_tts
    monkeypatch.setattr(sell_mod, "check_sell_script", lambda *a, **k: [])
    job = r.run(job)
    assert calls == [N, N]  # đọc → tự viết dài thêm → đọc lại (đúng một lần)
    assert len([c for c in r.director.calls if c["task"] == "sell"]) == 2
    assert job.status == Status.waiting and "Voice chưa đủ dài" in job.message  # vẫn ngắn → hỏi bạn
    assert settings_mem["sell_voice_cps"]["ko"] > 15


def test_av1_source_converted_once(tmp_path, monkeypatch):
    from app.analysis import ffmpeg
    from app.jobs.runner import Runner

    src = tmp_path / "game.mp4"
    src.write_bytes(b"x")
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    runs = []
    monkeypatch.setattr(ffmpeg, "video_codec", lambda p, exe=None: "av1")
    monkeypatch.setattr(ffmpeg, "run", lambda args, exe=None: (runs.append(args), Path(args[-1]).write_bytes(b"h264")))
    r = Runner(tmp_path / "jobs", log=lambda m: None)
    out = r._capcut_source(analysis, src)
    assert out.name == "capcut_src_00.mp4" and out.read_bytes() == b"h264" and "libx264" in runs[0]
    assert r._capcut_source(analysis, src) == out and len(runs) == 1  # đã đổi rồi thì dùng lại
    monkeypatch.setattr(ffmpeg, "video_codec", lambda p, exe=None: "h264")
    (analysis / "capcut_src_00.mp4").unlink()
    assert r._capcut_source(analysis, src) is None  # H.264 sẵn → giữ file gốc


def test_video_codec_parses_ffmpeg_output(monkeypatch):
    import subprocess

    from app.analysis import ffmpeg

    class R:
        stderr = "  Stream #0:0[0x1](und): Video: av1 (libdav1d) (Main) (av01 / 0x31307661), yuv420p, 720x1280"
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: R())
    assert ffmpeg.video_codec(Path("x.mp4"), exe="ffmpeg") == "av1"


def test_burned_in_corner_logo_keeps_titles(tmp_path):
    from app.jobs.runner import Runner

    r = Runner(tmp_path, log=lambda m: None)

    class U:
        def __init__(self, present, regions):
            self.burned_in_text = type("B", (), {"present": present, "regions": regions})()
    for regions, want in ((["top_left"], {"no_titles": False, "no_subtitles": False, "no_emphasis": False}),
                          (["top", "bottom"], {"no_titles": True, "no_subtitles": True, "no_emphasis": False}),
                          ([], {"no_titles": True, "no_subtitles": True})):
        r._understanding = lambda job, rg=regions: U(True, rg)
        assert r._burned_in_skip(None, {}) == want
    r._understanding = lambda job: U(False, ["top"])
    assert r._burned_in_skip(None, {}) == {}


def test_home_sell_variants_and_voice(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.tts import studio
    from app.web.server import create_app

    v = _studio_voice(tmp_path, monkeypatch)
    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None, studio_root=tmp_path / "studio")
    app.state.worker.start = lambda job_id, action=None: True
    c = TestClient(app)
    home = c.get("/").text
    assert "name=\"sell_variants\"" in home and "Giọng A" in home and studio.get_voice(v["slug"])
    r = c.post("/jobs", data={"footage": str(f), "mode": "sell", "target_language": "ja", "sell_variants": "3",
                              "sell_voice": v["slug"]}, follow_redirects=False)
    o = Job.load(tmp_path / "jobs", r.headers["location"].rsplit("/", 1)[1]).options
    assert o.sell_variants == 3 and o.sell_voice == v["slug"]
    assert "3 bản" in c.get(r.headers["location"]).text


def test_click_when_keyword_pops_alone():
    """Chủ dự án 17/10: "thêm cả âm thanh click" — chữ nhấn bật lên lúc không có tiếng nào khác thì kêu click."""
    s = sell_to_dub(SellScript.model_validate(FIX))
    dense = sell_fx(s, [(i * 1_000_000, 0.9, 0.9) for i in range(N)], {"fx": {"sfx_min_gap_s": 2.5}})
    clicks = [t for t, k in dense["sfx"] if k == "click"]
    em_times = {e[0] for e in dense["emphasis"]}
    assert any(t in em_times for t in clicks)  # click đúng lúc chữ nhấn hiện
    times = [t for t, _ in dense["sfx"]]
    assert times == sorted(times) and all(b - a >= 500_000 for a, b in zip(times, times[1:]))  # không chồng tiếng
    none = sell_fx(s, [(i * 1_000_000, 0.9, 0.9) for i in range(N)], {"fx": {"emphasis_sfx": "", "line_sfx": []}})
    assert [k for _, k in none["sfx"]] == ["pop"]


def test_fallback_finds_click_sound():
    from types import SimpleNamespace as NS

    from app.planner.builder import _fallback_sfx

    capcut = NS(kind="sfx", name="Mouse Click 2", mood="", material={})
    local = NS(kind="sfx", name="tick.wav", mood="click", material={"local": True})
    assert _fallback_sfx([capcut], "click") is capcut
    assert _fallback_sfx([capcut, local], "click") is local  # file trong assets/sfx/click/ được ưu tiên
