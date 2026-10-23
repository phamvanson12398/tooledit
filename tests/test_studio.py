"""Tab 🎙️ Voice Studio (chủ dự án yêu cầu 16/10): giọng mẫu + chữ → OmniVoice đọc; thư viện giọng mẫu; đủ thông số."""

import json
import subprocess
import sys
import time
import wave
from pathlib import Path

import pytest

from app.tts import studio as st
from app.tts import voices as ov
from tests.test_tts import _fake_env


def _wav(path: Path, secs: float = 1.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00\x00" * int(24000 * secs))
    return path


def _prepare(src, dst, max_s):  # thay ffmpeg: chép nguyên file
    Path(dst).write_bytes(Path(src).read_bytes())
    return Path(dst), False


def test_clean_params_types_and_ranges():
    p = st.clean_params({"speed": "1.3", "num_step": "200", "guidance_scale": "abc", "denoise": "on", "seed": "42"},
                        base=st.defaults())
    assert p["speed"] == 1.3 and p["num_step"] == 64 and p["guidance_scale"] == 2.0  # kẹp max / sai → mặc định
    assert p["denoise"] is True and p["postprocess_output"] is False  # ô không tick = tắt
    assert p["seed"] == 42 and p["duration"] == 0.0
    assert {k for k, *_ in st.PARAMS} == set(p)


def test_voice_library_consent_and_design(tmp_path):
    src = _wav(tmp_path / "in.wav")
    with pytest.raises(ValueError, match="quyền"):
        st.save_voice("Nam trầm", sample=src, root=tmp_path, prepare=_prepare)
    v = st.save_voice("Nam trầm / kênh A", sample=src, ref_text="안녕하세요", language="ko", consent=True,
                      root=tmp_path, prepare=_prepare)
    assert v["slug"] == "Nam_trầm_kênh_A" and v["mode"] == "clone"
    d = st.save_voice("Bé gái", instruct="female, child, high pitch", root=tmp_path)
    assert d["mode"] == "design"
    lib = st.list_voices(tmp_path)
    assert {x["name"] for x in lib} == {"Nam trầm / kênh A", "Bé gái"}
    got = st.get_voice(v["slug"], tmp_path)
    assert got["sample_path"].endswith("sample.wav") and got["ref_text"] == "안녕하세요" and got["consent"]
    cut = st.save_voice("Dài", sample=src, ref_text="lời cả file", consent=True, root=tmp_path,
                        prepare=lambda s, d, m: (_prepare(s, d, m)[0], True))
    assert cut["ref_text"] == "" and cut["trimmed"]  # mẫu bị cắt bớt → bỏ lời đọc (không còn khớp)
    assert st.delete_voice(v["slug"], tmp_path) and st.get_voice(v["slug"], tmp_path) is None


def test_build_request(tmp_path):
    v = st.save_voice("A", sample=_wav(tmp_path / "in.wav"), consent=True, root=tmp_path, prepare=_prepare)
    v = st.get_voice(v["slug"], tmp_path)
    params = {**st.defaults(), "duration": 3.0, "seed": 7, "class_temperature": 0.3}
    req = st.build_request({"model": "M", "device": "cpu"}, voice=v, texts=st.split_texts("một\n\nhai", True),
                           language="auto", params=params, out_dir=tmp_path / "out", stamp="S")
    spec = req["voices"]["v"]
    assert spec["mode"] == "clone" and spec["prompt_cache"].endswith("prompt.pt")
    assert [it["text"] for it in req["items"]] == ["một", "hai"] and req["items"][0]["language"] is None
    assert req["items"][0]["duration"] == 3.0 and req["items"][1]["out"].endswith("S_A_02.wav")
    assert req["gen"]["seed"] == 7 and req["gen"]["class_temperature"] == 0.3
    assert "duration" not in req["gen"] and "preprocess_prompt" not in req["gen"]
    auto = st.build_request({}, voice=None, texts=["x"], language="ja", params=st.defaults(), out_dir=tmp_path,
                            stamp="S", instruct="male, elderly")
    assert auto["voices"]["v"] == {"mode": "design", "instruct": "male, elderly"} and auto["items"][0]["language"] == "ja"


def test_worker_full_params_and_prompt_cache(tmp_path):
    """Chạy omnivoice_worker.py thật (OmniVoice giả giống API 0.2.1): đủ tham số sinh, seed, cache giọng mẫu."""
    env = _fake_env(tmp_path)
    req = {"model": "M", "device": "auto",
           "voices": {"v": {"mode": "clone", "ref_audio": "ref.wav", "ref_text": "",
                            "prompt_cache": str(tmp_path / "prompt.pt")}},
           "items": [{"text": "안녕", "language": "ko", "voice": "v", "duration": None, "out": str(tmp_path / "a.wav")}],
           "gen": {"num_step": 20, "guidance_scale": 3.0, "class_temperature": 0.2, "denoise": False, "speed": 1.2,
                   "normalize_text": True, "seed": 5, "bogus": 1}}

    def go():
        lines = []
        ov.run_worker(req, tmp_path / "req.json", {"python": sys.executable}, lines.append,
                      run=lambda cmd, **kw: subprocess.Popen(cmd, **{**kw, "env": env, "cwd": tmp_path}))
        return lines

    lines = go()
    assert any("tự nhận dạng" in x and "AUTO_ASR" in x for x in lines)  # không có lời mẫu → OmniVoice tự nhận dạng
    calls = (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines()
    assert calls[0] == "SEED 5"
    text, lang, dur, instr, ref, speed, norm, kw = calls[1].split("|", 7)
    assert (text, ref, speed, norm) == ("안녕", "AUTO_ASR", "1.2", "True")
    assert json.loads(kw) == {"num_step": 20, "guidance_scale": 3.0, "class_temperature": 0.2, "denoise": False}
    assert (tmp_path / "prompt.pt").is_file() and (tmp_path / "a.wav").is_file()
    go()  # lần 2: nạp lại giọng mẫu đã xử lý, không tạo lại
    assert "LOADED_CACHE" in (tmp_path / "calls.log").read_text(encoding="utf-8")


def test_studio_page_flow(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    monkeypatch.setattr(ov, "prepare_sample", _prepare)
    monkeypatch.setattr(ov, "load_cfg", lambda *a, **k: {"model": "M", "num_step": 32})
    seen = []

    def fake_worker(request, request_path, cfg, on_line):
        seen.append(request)
        for it in request["items"]:
            _wav(Path(it["out"]), 0.5)
            on_line(f"PROGRESS 1/1 {Path(it['out']).name}")

    settings = tmp_path / "local.yaml"
    settings.write_text("{}", encoding="utf-8")
    app = create_app(tmp_path / "jobs", lambda root, log: None, studio_root=tmp_path / "studio",
                     studio_worker=fake_worker, settings_path=settings)
    c = TestClient(app)
    assert "Voice Studio" in c.get("/").text  # tab trên thanh đầu trang
    page = c.get("/studio").text
    assert "Thư viện giọng mẫu" in page and "guidance_scale" in page and "class_temperature" in page
    sample = _wav(tmp_path / "mau.wav").read_bytes()
    r = c.post("/studio/generate", data={"text": "안녕하세요", "language": "ko", "new_name": "Giọng A"},
               files={"sample": ("mau.wav", sample, "audio/wav")}, follow_redirects=False)
    assert "msg=" in r.headers["location"] and not seen  # chưa tick quyền → không clone
    r = c.post("/studio/generate", data={"text": "안녕하세요\n두 번째", "language": "ko", "new_name": "Giọng A",
                                         "consent": "on", "per_line": "on", "speed": "1.1", "remember": "on",
                                         "denoise": "on"},
               files={"sample": ("mau.wav", sample, "audio/wav")}, follow_redirects=False)
    for _ in range(50):
        if not c.get("/studio/status").json()["running"]:
            break
        time.sleep(0.05)
    s = c.get("/studio/status").json()
    assert not s["error"] and len(s["outputs"]) == 2, s
    assert seen[0]["gen"]["speed"] == 1.1 and seen[0]["voices"]["v"]["mode"] == "clone"
    assert "speed: 1.1" in settings.read_text(encoding="utf-8")  # lưu làm mặc định
    page = c.get("/studio").text
    assert "Giọng A" in page and s["outputs"][0] in page  # giọng đã vào thư viện + file nằm trong lịch sử
    assert c.get(f"/studio/file/outputs/{s['outputs'][0]}").status_code == 200
    assert c.get("/studio/file/outputs/../../jobs/x.wav").status_code == 404
    slug = st.list_voices(tmp_path / "studio")[0]["slug"]
    c.post("/studio/generate", data={"text": "다시", "voice": slug}, follow_redirects=False)  # dùng lại giọng đã lưu
    for _ in range(50):
        if not c.get("/studio/status").json()["running"]:
            break
        time.sleep(0.05)
    assert len(seen) == 2 and seen[1]["voices"]["v"]["ref_audio"].endswith("sample.wav")


def test_download_all_numbered_from_one(tmp_path):
    """Chủ dự án 23/10: "tải 1 phát hết các file âm thanh và đánh số theo thứ tự từ 1"."""
    import io
    import zipfile

    from fastapi.testclient import TestClient

    from app.web.server import create_app

    out = tmp_path / "studio" / "outputs"
    out.mkdir(parents=True)
    for stamp, n, text in (("20261023_101500", 2, "câu hai"), ("20261023_090000", 1, "lượt cũ"),
                           ("20261023_101500", 10, "câu mười"), ("20261023_101500", 1, "câu một")):
        f = out / f"{stamp}_giong_a_{n:02d}.wav"
        f.write_bytes(f"{stamp}-{n}".encode())
        f.with_suffix(".json").write_text(json.dumps({"text": text}, ensure_ascii=False), encoding="utf-8")
    app = create_app(tmp_path / "jobs", lambda root, log: None, studio_root=tmp_path / "studio")
    c = TestClient(app)
    page = c.get("/studio").text
    assert "Tải tất cả (4 file" in page and "batch=20261023_101500" in page

    z = zipfile.ZipFile(io.BytesIO(c.get("/studio/download-all").content))
    assert z.read("1.wav") == b"20261023_090000-1"  # lượt cũ trước, rồi theo thứ tự dòng
    assert [z.read(f"{i}.wav") for i in (2, 3, 4)] == [b"20261023_101500-1", b"20261023_101500-2",
                                                        b"20261023_101500-10"]
    assert "4.wav\tcâu mười" in z.read("danh_sach.txt").decode("utf-8")

    z = zipfile.ZipFile(io.BytesIO(c.get("/studio/download-all?batch=20261023_101500").content))
    assert sorted(n for n in z.namelist() if n.endswith(".wav")) == ["1.wav", "2.wav", "3.wav"]
    assert z.read("1.wav") == b"20261023_101500-1"
    assert c.get("/studio/download-all?batch=../x").status_code == 400
