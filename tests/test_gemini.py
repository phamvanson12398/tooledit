"""AI đạo diễn Gemini Pro qua Gemini CLI (chủ dự án 11/10: chọn AI cho từng job)."""

import json
import os
import stat
import sys
import textwrap
from pathlib import Path

import pytest

from app.director import get_director
from app.director.base import DirectorError
from app.director.gemini_cli import GeminiCliDirector, build_command, build_prompt, extract_json, parse_output
from app.director.schemas import Understanding
from app.jobs.job import Job, JobOptions
from tests.test_director import make_analysis
from tests.test_planner import load

FAKE_GEMINI = textwrap.dedent('''
    import json, os, sys
    from pathlib import Path
    data = sys.stdin.read()
    args = sys.argv[1:]
    Path(os.environ["GEMINI_LOG"]).write_text(json.dumps({"args": args, "stdin": data, "cwd": os.getcwd(),
        "files": sorted(os.listdir("."))}, ensure_ascii=False), encoding="utf-8")
    mode = os.environ.get("GEMINI_MODE", "ok")
    if mode == "auth":
        print(json.dumps({"response": "", "error": {"message": "Please set an Auth method"}}))
        sys.exit(1)
    answer = Path(os.environ["GEMINI_ANSWER"]).read_text(encoding="utf-8")
    print(json.dumps({"response": "```json\\n" + answer + "\\n```", "stats": {}}))
''')


def _fake_exe(tmp_path: Path) -> str:
    """Chương trình `gemini` giả: ghi lại lệnh + stdin, trả JSON như Gemini CLI thật (-o json)."""
    script = tmp_path / "fake_gemini.py"
    script.write_text(FAKE_GEMINI, encoding="utf-8")
    if os.name == "nt":
        exe = tmp_path / "gemini.cmd"
        exe.write_text(f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
    else:
        exe = tmp_path / "gemini"
        exe.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return str(exe)


def test_prompt_and_command():
    p = build_prompt("Lời thoại: liên hệ @abc nhé", {"type": "object"}, ["00_0003.00.jpg", "my frame.jpg"])
    assert "＠abc" in p and "@abc" not in p                      # @ lạ không bị Gemini CLI hiểu là tên file
    assert "@00_0003.00.jpg" in p and "@my\\ frame.jpg" in p     # chỉ tham chiếu ảnh là @ thật
    assert "JSON Schema" in p and '"type": "object"' in p
    cmd = build_command("gemini", "gemini-2.5-pro")
    assert cmd[:2] == ["gemini", "-p"] and cmd[cmd.index("-o") + 1] == "json" and "--skip-trust" in cmd
    assert cmd[cmd.index("-m") + 1] == "gemini-2.5-pro" and "-m" not in build_command("gemini", None)


def test_parse_output():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Đây là kết quả: {"a": {"b": 2}} xong') == {"a": {"b": 2}}
    assert parse_output(json.dumps({"response": '{"x": 1}', "stats": {}})) == {"x": 1}
    with pytest.raises(DirectorError, match="Sign in with Google"):
        parse_output(json.dumps({"response": "", "error": {"message": "Please set an Auth method"}}), "", 1)
    real = ('{\n  "session_id": "ff58",\n  "error": {\n    "type": "Error",\n    "message": "Please set an Auth method in '
            'your ~/.gemini/settings.json or specify one of the following environment variables before running: '
            'GEMINI_API_KEY, GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_GENAI_USE_GCA",\n    "code": 41\n  }\n}')
    with pytest.raises(DirectorError) as e:  # đúng output của Gemini CLI 0.63.0 thật khi chưa đăng nhập
        parse_output("", real, 41)
    assert "Sign in with Google" in str(e.value) and '"session_id"' not in str(e.value)
    with pytest.raises(DirectorError, match="hết hạn mức"):
        parse_output("", "429 RESOURCE_EXHAUSTED quota", 1)


def test_gemini_director_runs_cli_with_images(tmp_path, monkeypatch):
    a = make_analysis(tmp_path / "job")
    answer = tmp_path / "answer.json"
    answer.write_text(json.dumps(load("understand.json"), ensure_ascii=False), encoding="utf-8")
    log = tmp_path / "log.json"
    monkeypatch.setenv("GEMINI_LOG", str(log))
    monkeypatch.setenv("GEMINI_ANSWER", str(answer))
    d = GeminiCliDirector({"gemini_exe": _fake_exe(tmp_path), "gemini_model": "gemini-2.5-pro",
                           "workspace": str(tmp_path / "ws"), "max_attempts": 1})
    imgs = sorted((a / "frames").glob("*.jpg"))[:2]
    u = d.run("understand", {k: "x" for k in ("styles", "client_style", "duration", "width", "height", "scene_count",
                                              "language", "scenes", "transcript", "frames")}, Understanding, imgs)
    assert isinstance(u, Understanding)
    got = json.loads(log.read_text(encoding="utf-8"))
    assert got["args"][:1] == ["-p"] and "json" in got["args"] and "gemini-2.5-pro" in got["args"]
    assert f"@{imgs[0].name}" in got["stdin"] and set(got["files"]) == {i.name for i in imgs}  # ảnh có trong thư mục
    assert not Path(got["cwd"]).exists()                                                       # dọn thư mục tạm
    monkeypatch.setenv("GEMINI_MODE", "auth")
    with pytest.raises(DirectorError, match="Sign in with Google"):
        d.run("understand", {k: "x" for k in ("styles", "client_style", "duration", "width", "height", "scene_count",
                                              "language", "scenes", "transcript", "frames")}, Understanding, imgs)


def test_ai_choice_per_job(tmp_path, monkeypatch):
    from app.jobs.runner import Runner

    assert type(get_director({"backend": "claude_cli"}, ai="gemini")).__name__ == "GeminiCliDirector"
    assert type(get_director({"backend": "claude_cli"}, ai="claude")).__name__ == "ClaudeCodeDirector"
    assert type(get_director({"backend": "claude_cli", "default_ai": "gemini"})).__name__ == "GeminiCliDirector"
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
    assert "AI đạo diễn" in home and "value='gemini'" in home and "Gemini Pro" in home
    r = client.post("/jobs", data={"footage": str(f), "ai": "gemini"}, follow_redirects=False)
    jid = r.headers["location"].rsplit("/", 1)[1]
    assert Job.load(tmp_path / "jobs", jid).options.ai == "gemini"
    assert "AI: <b>Gemini Pro" in client.get(f"/jobs/{jid}").text
    client.post(f"/jobs/{jid}/ai", data={"ai": "claude"})
    assert Job.load(tmp_path / "jobs", jid).options.ai == "claude"
