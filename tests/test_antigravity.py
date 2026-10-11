"""AI đạo diễn Gemini Pro qua Antigravity CLI `agy` (chủ dự án 11/10: chọn AI cho từng job). Dữ liệu mẫu = output THẬT
của agy 1.3.3 trên máy chủ dự án (các lần thử TEST 3–5)."""

import json
import os
import stat
import sys
import textwrap
from pathlib import Path

import pytest

from app.director import get_director
from app.director.antigravity_cli import (PROMPT_FILE, SCHEMA_FILE, AntigravityDirector, build_command, find_exe,
                                          parse_output)
from app.director.base import DirectorError
from app.director.schemas import Understanding
from app.jobs.job import Job, JobOptions
from tests.test_director import make_analysis
from tests.test_planner import load

# output thật: TEST 4 (đề bài trong -p, --json-schema) và TEST 3 (AI định chạy lệnh → bị từ chối, response trống)
REAL_OK = ('{"conversation_id":"955327c7-8f5b-4169-8fa7-3f4f8d682bdb","status":"SUCCESS","response":"{\\"secret\\":4729,'
           '\\"toolAction\\":\\"Finishing task\\",\\"toolSummary\\":\\"Finish task\\"}\\n","duration_seconds":5.096185,'
           '"num_turns":1,"structured_output":{"secret":4729},"json_schema":{"type":"object","properties":{"secret":'
           '{"type":"integer"}},"required":["secret"]},"usage":{"input_tokens":12277,"output_tokens":274,'
           '"thinking_tokens":242,"cache_read_tokens":0,"total_tokens":12551}}')
REAL_DENIED = ('{"conversation_id":"bfcf29ad-c607-400e-b5b8-316c9002b069","status":"SUCCESS","response":"",'
               '"duration_seconds":3.8646477,"num_turns":1,"json_schema":{"type":"object","properties":{"text":'
               '{"type":"string"}},"required":["text"]},"usage":{"input_tokens":12256,"output_tokens":392,'
               '"thinking_tokens":317,"cache_read_tokens":0,"total_tokens":12648},"denied_actions":[{"action":"command",'
               '"display_name":"RunCommand"}]}')
REAL_DENIED_ERR = ('jetski: no output produced — a tool required the "command" permission that headless mode cannot '
                   'prompt for, so it was auto-denied.')

FAKE_AGY = textwrap.dedent('''
    import json, os, sys
    from pathlib import Path
    stdin = sys.stdin.read()
    Path(os.environ["AGY_LOG"]).write_text(json.dumps({"args": sys.argv[1:], "stdin": stdin,
        "files": sorted(os.listdir(".")), "prompt": Path("de_bai.md").read_text(encoding="utf-8"),
        "schema": json.loads(Path("schema.json").read_text(encoding="utf-8")), "cwd": os.getcwd()},
        ensure_ascii=False), encoding="utf-8")
    if os.environ.get("AGY_MODE") == "denied":
        sys.stderr.write(os.environ["AGY_DENIED_ERR"])
        print(os.environ["AGY_DENIED"])
        sys.exit(0)
    out = json.loads(Path(os.environ["AGY_ANSWER"]).read_text(encoding="utf-8"))
    print(json.dumps({"conversation_id": "x", "status": "SUCCESS", "response": json.dumps(out),
                      "structured_output": out, "usage": {}}))
''')


def _fake_exe(tmp_path: Path) -> str:
    script = tmp_path / "fake_agy.py"
    script.write_text(FAKE_AGY, encoding="utf-8")
    if os.name == "nt":
        exe = tmp_path / "agy.cmd"
        exe.write_text(f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
    else:
        exe = tmp_path / "agy"
        exe.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return str(exe)


UNDERSTAND_VARS = {k: "x" for k in ("styles", "client_style", "duration", "width", "height", "scene_count", "language",
                                    "scenes", "transcript", "frames")}


def test_command_and_parse_real_outputs():
    cmd = build_command("agy", "gemini-x", "high")
    assert cmd[:2] == ["agy", "-p"] and PROMPT_FILE in cmd[2] and cmd[cmd.index("--output-format") + 1] == "json"
    assert cmd[cmd.index("--json-schema") + 1] == SCHEMA_FILE and "--dangerously-skip-permissions" not in cmd
    assert cmd[-4:] == ["--model", "gemini-x", "--effort", "high"] and "--model" not in build_command("agy")
    assert all(ord(ch) < 128 for ch in cmd[2])            # lời nhắn trên dòng lệnh Windows không dấu
    assert parse_output(REAL_OK) == {"secret": 4729}      # lấy structured_output
    with pytest.raises(DirectorError, match="RunCommand"):
        parse_output(REAL_DENIED, REAL_DENIED_ERR, 0)
    with pytest.raises(DirectorError, match="chưa đăng nhập"):
        parse_output("", "Error: please sign in (run agy to login)", 1)
    with pytest.raises(DirectorError, match="hết hạn mức"):
        parse_output("", "429 quota exceeded", 1)


def test_find_exe_in_localappdata(tmp_path, monkeypatch):
    """agy cài bằng trình cài chính thức nằm ở %LOCALAPPDATA%\\agy\\bin\\agy.exe, có thể chưa có trong PATH."""
    monkeypatch.setenv("PATH", str(tmp_path / "trong"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert find_exe("agy") == "agy"
    exe = tmp_path / "agy" / "bin" / "agy.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    assert find_exe("agy") == str(exe) and find_exe(None) == str(exe)


def test_director_writes_task_file_and_images(tmp_path, monkeypatch):
    a = make_analysis(tmp_path / "job")
    answer = tmp_path / "answer.json"
    answer.write_text(json.dumps(load("understand.json"), ensure_ascii=False), encoding="utf-8")
    log = tmp_path / "log.json"
    for k, v in {"AGY_LOG": log, "AGY_ANSWER": answer, "AGY_DENIED": REAL_DENIED, "AGY_DENIED_ERR": REAL_DENIED_ERR}.items():
        monkeypatch.setenv(k, str(v))
    d = AntigravityDirector({"agy_exe": _fake_exe(tmp_path), "workspace": str(tmp_path / "ws"), "max_attempts": 2})
    imgs = sorted((a / "frames").glob("*.jpg"))[:2]
    u = d.run("understand", UNDERSTAND_VARS, Understanding, imgs)
    assert isinstance(u, Understanding)
    got = json.loads(log.read_text(encoding="utf-8"))
    assert got["stdin"] == ""                                          # agy không đọc stdin → đề bài nằm trong file
    assert set(got["files"]) == {PROMPT_FILE, SCHEMA_FILE} | {i.name for i in imgs}
    assert "# Nhiệm vụ: hiểu nội dung" in got["prompt"] and imgs[0].name in got["prompt"].rsplit("## Khung hình", 1)[1]
    assert got["schema"] == Understanding.model_json_schema()
    assert not Path(got["cwd"]).exists()                               # dọn thư mục tạm
    monkeypatch.setenv("AGY_MODE", "denied")                           # AI định chạy lệnh → bị chặn → hỏi lại, rồi báo lỗi
    with pytest.raises(DirectorError):
        d.run("understand", UNDERSTAND_VARS, Understanding, imgs)


def test_ai_choice_per_job(tmp_path, monkeypatch):
    from app.jobs.runner import Runner

    assert type(get_director({"backend": "claude_cli"}, ai="gemini")).__name__ == "AntigravityDirector"
    assert type(get_director({"backend": "claude_cli"}, ai="claude")).__name__ == "ClaudeCodeDirector"
    assert type(get_director({"backend": "claude_cli", "default_ai": "gemini"})).__name__ == "AntigravityDirector"
    made = []
    monkeypatch.setattr("app.director.get_director", lambda ai=None, **kw: made.append(ai) or object())
    r = Runner(tmp_path)
    r.use_ai(Job.create(tmp_path, [Path("C:/a.mp4")], JobOptions(ai="gemini"), job_id="g"))
    r.director
    r.use_ai(Job.create(tmp_path, [Path("C:/a.mp4")], JobOptions(ai="claude"), job_id="c"))
    r.director
    assert made == ["gemini", "claude"]


def test_web_ai_select_and_switch(tmp_path):
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    client = TestClient(app)
    home = client.get("/").text
    assert "AI đạo diễn" in home and "value='gemini'" in home and "Antigravity" in home
    r = client.post("/jobs", data={"footage": str(f), "ai": "gemini"}, follow_redirects=False)
    jid = r.headers["location"].rsplit("/", 1)[1]
    assert Job.load(tmp_path / "jobs", jid).options.ai == "gemini"
    assert "AI: <b>Gemini Pro" in client.get(f"/jobs/{jid}").text
    client.post(f"/jobs/{jid}/ai", data={"ai": "claude"})
    assert Job.load(tmp_path / "jobs", jid).options.ai == "claude"


def test_frames_packed_into_contact_sheets(tmp_path):
    """Chủ dự án 11/10 "chậm quá": nhiều khung hình → ghép ảnh lưới 3×3 có nhãn tên file, AI đọc ít file hơn."""
    import cv2
    import numpy as np

    from app.director.contact_sheet import pack

    imgs = []
    for k in range(20):
        p = tmp_path / f"00_{k * 4.0:08.2f}.jpg"
        cv2.imwrite(str(p), np.full((270, 480, 3), k * 10, dtype=np.uint8))
        imgs.append(p)
    work = tmp_path / "w"
    work.mkdir()
    names, note = pack(imgs, work, {"min_images": 6, "per_sheet": 9, "cols": 3, "tile_width": 360})
    assert names == ["sheet_01.jpg", "sheet_02.jpg", "sheet_03.jpg"] and "ẢNH LƯỚI" in note
    sheet = cv2.imread(str(work / "sheet_01.jpg"))
    assert sheet.shape[1] == 3 * 360 + 2 * 4 and sheet.shape[0] > 3 * 202
    few = tmp_path / "few"
    few.mkdir()
    names, note = pack(imgs[:3], few, {"min_images": 6})                 # ít ảnh: gửi từng ảnh như cũ
    assert names == [p.name for p in imgs[:3]] and note == "" and (few / imgs[0].name).is_file()
    off = tmp_path / "off"
    off.mkdir()
    assert pack(imgs, off, {"enabled": False})[1] == ""


def test_agy_task_files_use_contact_sheets(tmp_path, monkeypatch):
    import cv2
    import numpy as np

    from app.director import antigravity_cli as ag

    imgs = []
    for k in range(7):
        p = tmp_path / f"f{k}.jpg"
        cv2.imwrite(str(p), np.zeros((90, 160, 3), dtype=np.uint8))
        imgs.append(p)
    d = ag.AntigravityDirector({"workspace": str(tmp_path / "ws"), "agy_exe": "agy"})
    seen = {}

    def fake_run(cmd, stdin, workdir, timeout):
        seen["prompt"] = (Path(workdir) / ag.PROMPT_FILE).read_text(encoding="utf-8")
        seen["files"] = sorted(x.name for x in Path(workdir).iterdir())

        class P:
            stdout = '{"status": "SUCCESS", "structured_output": {"ok": 1}}'
            stderr = ""
            returncode = 0
        return P()

    monkeypatch.setattr(ag, "_run_stoppable", fake_run)
    assert d._complete("understand", "Đề bài", {"type": "object"}, imgs) == {"ok": 1}
    assert "sheet_01.jpg" in seen["files"] and "f0.jpg" not in seen["files"]
    assert "ẢNH LƯỚI" in seen["prompt"] and "sheet_01.jpg" in seen["prompt"]
