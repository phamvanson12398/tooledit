"""Giọng AI bằng OmniVoice (chủ dự án yêu cầu 11/10): mỗi nhân vật một giọng, đọc vừa khít câu thoại gốc."""

import json
import os
import subprocess
import sys
import textwrap
import wave
from pathlib import Path

import numpy as np
import pytest

from app.director.fake import FakeDirector
from app.director.schemas import DubScript
from app.jobs.job import Job, JobOptions, Status
from app.planner import dub_io
from app.tts import voices as ov
from tests.test_char_dub import LINES, SEG, _script, _talk
from tests.test_director import make_analysis
from tests.test_planner import load
from tests.test_runner import make_runner

FAKE_OMNIVOICE = textwrap.dedent('''
    import numpy as np
    CALLS = []
    import json as _json
    class VoiceClonePrompt:  # giống bản thật 0.2.1: save / load
        def __init__(self, ref_audio, ref_text):
            self.ref_audio, self.ref_text = ref_audio, ref_text
        def save(self, path):
            open(path, "w", encoding="utf-8").write(_json.dumps([self.ref_audio, self.ref_text]))
        @classmethod
        def load(cls, path, map_location="cpu"):
            with open("calls.log", "a", encoding="utf-8") as f:
                f.write("LOADED_CACHE\\n")
            return cls(*_json.loads(open(path, encoding="utf-8").read()))
    _Prompt = VoiceClonePrompt
    class OmniVoice:
        sampling_rate = 24000
        @classmethod
        def from_pretrained(cls, name, device_map=None, dtype=None):
            m = cls(); m.device = device_map; return m
        def create_voice_clone_prompt(self, ref_audio, ref_text=None, preprocess_prompt=True):
            return _Prompt(ref_audio, ref_text if ref_text is not None else "AUTO_ASR")
        def generate(self, text, language=None, duration=None, instruct=None, voice_clone_prompt=None, speed=None,
                     normalize_text=False, **kwargs):
            secs = duration or 1.0
            with open("calls.log", "a", encoding="utf-8") as f:
                f.write(f"{text}|{language}|{duration}|{instruct}|{getattr(voice_clone_prompt, 'ref_text', None)}"
                        f"|{speed}|{normalize_text}|{_json.dumps(kwargs, sort_keys=True)}\\n")
            return [np.full(int(secs * self.sampling_rate), 0.1, dtype=np.float32)]
''')
FAKE_TORCH = textwrap.dedent('''
    float16, float32 = "f16", "f32"
    class cuda:
        @staticmethod
        def is_available(): return False
    class backends: pass
    def manual_seed(n):
        with open("calls.log", "a", encoding="utf-8") as f:
            f.write(f"SEED {n}\\n")
''')


def _fake_env(tmp_path: Path) -> dict:
    pkg = tmp_path / "fakepkgs"
    (pkg / "omnivoice").mkdir(parents=True, exist_ok=True)
    (pkg / "omnivoice" / "__init__.py").write_text(FAKE_OMNIVOICE, encoding="utf-8")
    (pkg / "torch.py").write_text(FAKE_TORCH, encoding="utf-8")
    return {**os.environ, "PYTHONPATH": str(pkg)}


def test_pick_reference_and_items():
    s = DubScript.model_validate(_script())
    assert ov.pick_reference(s.lines, "징징이") == (10.0, 14.0)            # câu gốc dài nhất trong 3–10 giây
    assert ov.pick_reference(s.lines, "Không ai") is None
    short = DubScript.model_validate(_script(lines=[dict(LINES[0], source_start=1.0, source_end=2.0),
                                                     dict(LINES[0], source_start=2.4, source_end=4.6)]))
    assert ov.pick_reference(short.lines, "징징이") == (1.0, 4.6)           # câu ngắn liền nhau → gộp cho đủ 3 giây
    items = ov.build_items(s, 1, Path("v"), "ko", [(0, 3.0, 3.5), None, (0, 4.0, 4.0), (0, 0.2, 1.0)], True, {1, 2, 3, 4})
    assert [it["duration"] for it in items] == [3.0, None, 4.0, None]      # đọc vừa khít thời lượng câu gốc
    assert items[0]["voice"] == "징징이" and items[0]["out"].endswith("video01_dub01.wav")
    nar = DubScript.model_validate({**_script(), "lines": [dict(LINES[0], speaker="")]})
    assert ov.voice_key(nar.lines[0]) == ov.NARRATOR                       # thuyết minh thường: một giọng "Người dẫn"


def test_worker_runs_omnivoice_in_separate_process(tmp_path):
    """Chạy đúng file omnivoice_worker.py ở tiến trình riêng (OmniVoice giả) — clone / mô tả / tự chọn, đúng thời lượng."""
    env = _fake_env(tmp_path)
    out = tmp_path / "voice"
    req = {"model": "k2-fsa/OmniVoice", "device": "auto", "num_step": 16,
           "voices": {"A": {"mode": "clone", "ref_audio": "ref.wav", "ref_text": "こんにちは"},
                      "B": {"mode": "design", "instruct": "male, child"}, "C": {"mode": "auto"}},
           "items": [{"text": "안녕", "language": "ko", "voice": "A", "duration": 2.0, "out": str(out / "a.wav")},
                     {"text": "뭐야", "language": "ko", "voice": "B", "duration": None, "out": str(out / "b.wav")},
                     {"text": "좋아", "language": "ko", "voice": "C", "duration": 1.5, "out": str(out / "c.wav")}]}
    lines = []

    def run(cmd, **kw):
        return subprocess.Popen(cmd, **{**kw, "env": {**kw.get("env", {}), **env}, "cwd": tmp_path})

    ov.run_worker(req, tmp_path / "req.json", {"python": sys.executable}, lines.append, run=run)
    assert any(x.startswith("PROGRESS 3/3") for x in lines)
    with wave.open(str(out / "a.wav")) as w:
        assert w.getframerate() == 24000 and abs(w.getnframes() / 24000 - 2.0) < 0.01
    calls = (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines()
    assert calls[0].startswith("안녕|ko|2.0|None|こんにちは|") and calls[1].startswith("뭐야|ko|None|male, child|None|")
    assert calls[0].endswith('{"num_step": 16}')  # yêu cầu cũ (không có "gen") vẫn chạy như trước
    assert calls[2].startswith("좋아|ko|1.5|None|None")


def test_worker_reports_missing_omnivoice(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(tmp_path / "trong")}  # không có omnivoice
    with pytest.raises(RuntimeError, match="chưa cài OmniVoice"):
        ov.run_worker({"items": []}, tmp_path / "r.json", {"python": sys.executable}, lambda x: None,
                      run=lambda cmd, **kw: subprocess.Popen(cmd, **{**kw, "env": {**kw.get("env", {}), **env}}))


def _char_job(tmp_path):
    from tests.test_review import _clips, _plan

    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/anime.mp4")], JobOptions(char_dub=True, target_language="ko"), job_id="tv")
    _talk(make_analysis(jobs / "tv", duration=400.0), shift=(-1.0, -1.5))
    r = make_runner(tmp_path, jobs)
    u = load("understand.json")
    u["usable_range"] = {"start": 0.0, "end": 400.0}
    lines = [dict(x, source_start=x["source_start"] - 1.0, source_end=x["source_end"] - 1.5) for x in LINES]
    script = {**_script(1, lines), "cast": [{"speaker": "징징이", "instruct": "male, middle-aged, low pitch",
                                             "note_vi": "cáu kỉnh"},
                                            {"speaker": "스펀지밥", "instruct": "male, young adult, high pitch"}]}
    r._director = FakeDirector(responses={"understand": u, "segment": SEG, "plan": _plan(1, _clips(1.0, 40)),
                                          "dub_char": script, "captions": load("captions.json")})
    job = r.run(job)
    r.apply_segments(job, json.loads((jobs / "tv" / "plan" / "segments.json").read_text(encoding="utf-8"))["videos"])
    job = r.resume(job)
    assert job.step == "dub_voice" and job.status == Status.waiting, job.message
    return jobs, job, r


def test_runner_tts_generate_then_build(tmp_path, monkeypatch):
    """🤖 Cho OmniVoice đọc → voice từng câu, mỗi nhân vật một giọng; clone chỉ khi đã xác nhận quyền."""
    from app.planner.voice_split import write_wav

    jobs, job, r = _char_job(tmp_path)
    monkeypatch.setattr(type(r), "_bgm", lambda self, job, analysis: None)
    voices = r.tts_voices(job)
    assert voices["징징이"] == {"mode": "design", "instruct": "male, middle-aged, low pitch", "note_vi": "cáu kỉnh"}
    sent = []

    def fake_run(request, path, cfg, on_line):
        sent.append(request)
        for it in request["items"]:
            write_wav(Path(it["out"]), np.zeros(int((it["duration"] or 1.0) * 48000), dtype=np.int16))
        on_line(f"PROGRESS {len(request['items'])}/{len(request['items'])} xong")

    r._tts_run = fake_run
    # chọn clone cho 징징이 nhưng CHƯA tick xác nhận quyền → không clone
    r.save_tts_voices(job, {"징징이": {"mode": "clone", "instruct": "male, middle-aged"},
                            "스펀지밥": {"mode": "design", "instruct": "male, young adult, high pitch"}}, clone_ok=False)
    (jobs / "tv" / "voice" / "video01_dub02.wav").write_bytes(b"RIFF")  # câu 2 đã tự thu → không đọc lại
    n = r.tts_generate(job)
    assert n == 3 and sent[0]["voices"]["징징이"]["mode"] == "design" and "ref_audio" not in sent[0]["voices"]["징징이"]
    assert [it["voice"] for it in sent[0]["items"]] == ["징징이", "징징이", "스펀지밥"]
    assert sent[0]["items"][0]["language"] == "ko" and sent[0]["items"][0]["duration"]
    # tick xác nhận quyền → clone từ giọng gốc (cắt 3–10 giây quanh câu dài nhất của nhân vật)
    audio = jobs / "tv" / "analysis" / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    write_wav(audio / "clean_00.wav", (np.sin(np.arange(48000 * 30) / 30) * 8000).astype(np.int16))
    ff = pytest.importorskip("imageio_ffmpeg").get_ffmpeg_exe()
    from app.analysis import ffmpeg as ffm

    monkeypatch.setattr(ffm, "ffmpeg_exe", lambda *a, **k: ff)
    r.save_tts_voices(job, {"징징이": {"mode": "clone", "instruct": ""}}, clone_ok=True)
    r.tts_generate(job, only_missing=False)
    v = sent[1]["voices"]["징징이"]
    assert v["mode"] == "clone" and Path(v["ref_audio"]).is_file() and len(sent[1]["items"]) == 4
    job = r.run(job)  # đủ voice → dựng tiếp tới Xong
    assert job.status == Status.done, job.message


def test_web_tts_card_and_post(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    jobs, job, r = _char_job(tmp_path)
    app = create_app(jobs, lambda root, log: None)
    actions = []
    app.state.worker.start = lambda job_id, action=None: actions.append(action) or True
    client = TestClient(app)
    page = client.get("/jobs/tv").text
    assert "Hoặc để OmniVoice đọc thay" in page and "male, middle-aged, low pitch" in page and "CÓ QUYỀN" in page
    client.post("/jobs/tv/tts", data={"name_0": "징징이", "mode_0": "design", "instruct_0": "male, elderly",
                                      "name_1": "스펀지밥", "mode_1": "auto", "instruct_1": "", "video": "1"})
    called = []
    monkeypatch.setattr(type(r), "tts_generate", lambda self, job, video, only: called.append((video, only)) or 0)
    actions[-1](r, job)
    assert called == [(1, True)] and job.data["tts"]["voices"]["징징이"]["instruct"] == "male, elderly"
    assert job.data["tts"]["clone_ok"] is False


def test_worker_vietnamese_output_on_windows_codepage(tmp_path):
    """Lỗi chủ dự án gặp 11/10: Windows in ra ống bằng cp1252 → "UnicodeEncodeError: 'charmap'" khi worker báo lỗi
    tiếng Việt ("chưa cài omnivoice"). Giả lập bảng mã cp1252: vẫn nhận đúng câu báo lỗi tiếng Việt."""
    base = {**os.environ, "PYTHONPATH": str(tmp_path / "trong")}

    def run(cmd, **kw):  # tool truyền env ép UTF-8; python con mặc định cp1252 như Windows
        env = {**base, **{k: v for k, v in kw.pop("env", {}).items() if k.startswith("PYTHONIO") or k == "PYTHONUTF8"}}
        env.setdefault("PYTHONIOENCODING", "cp1252")
        return subprocess.Popen(cmd, env=env, **kw)

    with pytest.raises(RuntimeError, match="chưa cài OmniVoice"):
        ov.run_worker({"items": []}, tmp_path / "r.json", {"python": sys.executable}, lambda x: None, run=run)
    assert ov.utf8_env()["PYTHONIOENCODING"] == "utf-8"
    # kể cả khi env bị ép cp1252 (không có utf8_env), worker tự chuyển stdout sang UTF-8
    lines = []
    with pytest.raises(RuntimeError, match="chưa cài OmniVoice"):
        ov.run_worker({"items": []}, tmp_path / "r.json", {"python": sys.executable}, lines.append,
                      run=lambda cmd, **kw: subprocess.Popen(cmd, **{**kw, "env": {**base,
                                                                                     "PYTHONIOENCODING": "cp1252"}}))


def test_python_exe_finds_install_bat_env(tmp_path):
    """install_omnivoice.bat cài vào <tool>/omnivoice-env → tool tự dùng, không cần sửa config/tts.yaml."""
    assert ov.python_exe({}, tmp_path / "omnivoice-env") == sys.executable          # chưa cài → python của tool
    exe = tmp_path / "omnivoice-env" / "Scripts" / "python.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    assert ov.python_exe({"python": ""}, tmp_path / "omnivoice-env") == str(exe)    # đã cài → tự tìm thấy
    assert ov.python_exe({"python": "C:/khac/python.exe"}, tmp_path / "omnivoice-env") == "C:/khac/python.exe"
    with pytest.raises(RuntimeError, match="Không thấy python ở"):                  # đường dẫn trong config sai
        ov.run_worker({"items": []}, tmp_path / "r.json", {"python": str(tmp_path / "khong_co" / "python.exe")},
                      lambda x: None)


def test_missing_omnivoice_names_the_python_and_install_bat(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(tmp_path / "trong")}
    with pytest.raises(RuntimeError) as e:
        ov.run_worker({"items": []}, tmp_path / "r.json", {"python": sys.executable}, lambda x: None,
                      run=lambda cmd, **kw: subprocess.Popen(cmd, **{**kw, "env": {**kw.get("env", {}), **env}}))
    assert sys.executable in str(e.value) and "install_omnivoice.bat" in str(e.value)
    assert (Path(ov.ROOT) / "install_omnivoice.bat").is_file()


def test_review_voice_is_natural_length(tmp_path):
    """Review phim: hình chạy theo giọng → OmniVoice đọc tốc độ tự nhiên, không ép vào thời lượng cố định."""
    from app.jobs.runner import Runner

    rev = Job.create(tmp_path, [Path("C:/f/a.mp4")], JobOptions(review=True, target_language="ko"), job_id="r1")
    ch = Job.create(tmp_path, [Path("C:/f/a.mp4")], JobOptions(char_dub=True, target_language="ko"), job_id="c1")
    assert Runner._tts_fit(rev, {"fit_duration": True}) is False
    assert Runner._tts_fit(ch, {"fit_duration": True}) is True and Runner._tts_fit(ch, {"fit_duration": False}) is False


def test_uploaded_voice_sample(tmp_path, monkeypatch):
    """Chủ dự án 11/10: OmniVoice clone từ GIỌNG MẪU tải lên — cần tick quyền; file dài thì lấy 10 giây đầu, bỏ lời đọc."""
    import io
    import wave

    from fastapi.testclient import TestClient

    from app.analysis import ffmpeg as ffm
    from app.planner.voice_split import write_wav
    from app.web.server import create_app

    ff = pytest.importorskip("imageio_ffmpeg").get_ffmpeg_exe()
    monkeypatch.setattr(ffm, "ffmpeg_exe", lambda *a, **k: ff)
    jobs, job, r = _char_job(tmp_path)
    monkeypatch.setattr(type(r), "_bgm", lambda self, job, analysis: None)

    def wav_bytes(secs):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes((np.sin(np.arange(int(16000 * secs)) / 9) * 6000).astype(np.int16).tobytes())
        return buf.getvalue()

    app = create_app(jobs, lambda root, log: None)
    actions = []
    app.state.worker.start = lambda job_id, action=None: actions.append(action) or True
    client = TestClient(app)
    page = client.get("/jobs/tv").text
    assert "Giọng mẫu tải lên" in page and "name='sample_0'" in page and "multipart/form-data" in page
    client.post("/jobs/tv/tts", data={"name_0": "징징이", "mode_0": "upload", "instruct_0": "", "reftext_0": "안녕하세요",
                                      "name_1": "스펀지밥", "mode_1": "auto", "video": "1", "clone_ok": "on"},
                files={"sample_0": ("giong mau.wav", wav_bytes(5.0), "audio/wav")})
    sent = []

    def fake_run(request, path, cfg, on_line):
        sent.append(request)
        for it in request["items"]:
            write_wav(Path(it["out"]), np.zeros(int((it["duration"] or 1.0) * 48000), dtype=np.int16))

    r._tts_run = fake_run
    actions[-1](r, job)
    v = sent[0]["voices"]["징징이"]
    assert v["mode"] == "clone" and Path(v["ref_audio"]).is_file() and v["ref_text"] == "안녕하세요"
    saved = job.data["tts"]["voices"]["징징이"]
    assert saved["mode"] == "upload" and Path(saved["sample"]).is_file()
    from app.web.server import _tts_card

    assert "✅ đã có: tai_len_" in _tts_card(job, jobs / "tv")                   # lần sau khỏi tải lại

    # file dài 25 giây → chỉ lấy 10 giây đầu, bỏ lời đọc (không còn khớp)
    Path(saved["sample"]).write_bytes(wav_bytes(25.0))
    r.save_tts_voices(job, {"징징이": {"mode": "upload", "instruct": "", "ref_text": "안녕하세요"}}, clone_ok=True)
    r.tts_generate(job, only_missing=False)
    v = sent[1]["voices"]["징징이"]
    with wave.open(v["ref_audio"], "rb") as w:
        assert w.getnframes() / w.getframerate() <= 10.1
    assert v["ref_text"] == ""
    # chưa tick quyền → không dùng giọng mẫu
    r.save_tts_voices(job, {"징징이": {"mode": "upload", "instruct": "male, old"}}, clone_ok=False)
    r.tts_generate(job, only_missing=False)
    assert sent[2]["voices"]["징징이"]["mode"] == "design" and "ref_audio" not in sent[2]["voices"]["징징이"]


def test_choose_omnivoice_install_check_and_kill(tmp_path):
    """Chủ dự án 11/10: dùng đúng bản OmniVoice muốn (vd trong Voice Studio) — chọn python / model trên giao diện,
    nút kiểm tra; OmniVoice chạy quá lâu / bấm Dừng thì tiến trình bị tắt."""
    import time

    from fastapi.testclient import TestClient

    from app.web.server import create_app

    local = tmp_path / "local.yaml"
    client = TestClient(create_app(tmp_path / "jobs", lambda root, log: None, settings_path=local))
    assert "🤖 OmniVoice (giọng AI)" in client.get("/").text
    client.post("/settings/tts", data={"python": f'"{sys.executable}"', "model": "D:/VoiceStudio/models/omnivoice"})
    cfg = ov.load_cfg(local)
    assert cfg["python"] == sys.executable and cfg["model"] == "D:/VoiceStudio/models/omnivoice"
    page = client.post("/settings/tts-check", data={"python": sys.executable, "model": str(tmp_path)}).text
    assert "Kiểm tra OmniVoice" in page and "model_is_folder" in page and sys.executable in page
    r = ov.check_omnivoice({"python": sys.executable, "model": str(tmp_path)})
    assert r["python"] == sys.executable and r["model_is_folder"] is True
    assert "error" in ov.check_omnivoice({"python": str(tmp_path / "khong_co.exe")})

    slow = tmp_path / "slow.py"   # worker giả chạy mãi → bị tắt sau timeout_s
    slow.write_text("import time, sys\nprint('INFO bat dau', flush=True)\ntime.sleep(60)\n", encoding="utf-8")
    t0 = time.monotonic()
    with pytest.raises(RuntimeError, match="bị tắt"):
        ov.run_worker({"items": []}, tmp_path / "r.json", {"python": sys.executable, "timeout_s": 1}, lambda x: None,
                      run=lambda cmd, **kw: subprocess.Popen([cmd[0], str(slow)], **kw))
    assert time.monotonic() - t0 < 20

    class Stop(Exception):
        pass

    procs = []

    def popen(cmd, **kw):
        procs.append(subprocess.Popen([cmd[0], str(slow)], **kw))
        return procs[-1]

    with pytest.raises(Stop):  # bấm Dừng (on_line ném lỗi) → tiến trình OmniVoice bị tắt luôn
        ov.run_worker({"items": []}, tmp_path / "r.json", {"python": sys.executable}, lambda x: (_ for _ in ()).throw(Stop()),
                      run=popen)
    assert procs[0].wait(timeout=10) is not None
