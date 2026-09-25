"""Backend gọi Claude Code ở chế độ không tương tác (claude -p).

Cờ lệnh đối chiếu với `claude --help` (bản 2.1.282) và https://code.claude.com/docs/en/headless:
- `-p` chạy không tương tác; prompt đưa qua stdin (tránh giới hạn độ dài dòng lệnh Windows).
- `--output-format json` + `--json-schema <schema>` → kết quả khuôn nằm ở trường `structured_output`.
- `--tools Read` chỉ cho phép đọc file (xem khung hình); `--permission-mode dontAsk` và
  `--permission-prompts none` để không bao giờ treo chờ hỏi quyền.
- `--no-session-persistence` không lưu phiên; `--strict-mcp-config` bỏ qua MCP server.
- KHÔNG dùng `--bare` vì nó không đọc đăng nhập gói Pro.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from app import config
from app.director.base import Director, DirectorError


def default_workspace() -> Path:
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "tooledit" / "director"
    return Path.home() / ".cache" / "tooledit" / "director"


def build_command(exe: str, schema: dict, model: str | None = None, effort: str | None = None,
                  with_images: bool = False) -> list[str]:
    cmd = [exe, "-p", "--output-format", "json",
           "--json-schema", json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
           "--tools", "Read" if with_images else "",
           "--permission-mode", "dontAsk", "--permission-prompts", "none",
           "--no-session-persistence", "--strict-mcp-config", "--disable-slash-commands"]
    if model:
        cmd += ["--model", model]
    if effort:
        cmd += ["--effort", effort]
    return cmd


def parse_output(stdout: str) -> dict:
    """Lấy structured_output; nếu thiếu thì thử đọc JSON trong trường result."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise DirectorError(f"Claude Code không trả JSON: {stdout[:500]}") from exc
    if data.get("is_error") or (data.get("subtype") not in (None, "success")):
        message = str(data.get("result"))
        if "not logged in" in message.lower() or "/login" in message:
            raise DirectorError(
                "Claude Code chưa đăng nhập. Mở PowerShell, gõ `claude`, gõ `/login`, đăng nhập tài khoản "
                "Claude Pro trên trình duyệt, rồi gõ `/exit` và chạy lại. (Thông báo gốc: " + message[:200] + ")")
        raise DirectorError(f"Claude Code báo lỗi: {message[:800]}")
    if isinstance(data.get("structured_output"), dict):
        return data["structured_output"]
    text = str(data.get("result", "")).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise DirectorError(f"Không tìm thấy JSON trong kết quả: {text[:500]}")


class ClaudeCodeDirector(Director):
    def __init__(self, cfg: dict | None = None, **kwargs):
        cfg = cfg or config.load("director")
        super().__init__(max_attempts=cfg.get("max_attempts", 3), **kwargs)
        self.cfg = cfg
        self.exe = shutil.which(cfg.get("claude_exe") or "claude") or cfg.get("claude_exe") or "claude"
        self.workspace = Path(cfg.get("workspace") or default_workspace())

    def _prepare_workdir(self, task: str, images: list[Path]) -> Path:
        workdir = self.workspace / task
        if workdir.exists():
            shutil.rmtree(workdir)
        workdir.mkdir(parents=True)
        for img in images:
            shutil.copy2(img, workdir / Path(img).name)
        return workdir

    def _complete(self, task: str, prompt: str, schema: dict, images: list[Path]) -> dict:
        workdir = self._prepare_workdir(task, images)
        cmd = build_command(self.exe, schema, self.cfg.get("model"), self.cfg.get("effort"), bool(images))
        self.log(f"Đang hỏi đạo diễn AI ({task})...")
        try:
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", cwd=workdir, timeout=self.cfg.get("timeout_s", 900))
        except FileNotFoundError as exc:
            raise DirectorError("Không tìm thấy lệnh `claude`. Cài Claude Code (docs/SETUP_WINDOWS.md mục 5).") from exc
        except subprocess.TimeoutExpired as exc:
            raise DirectorError(f"Đạo diễn không trả lời sau {self.cfg.get('timeout_s', 900)} giây.") from exc
        if proc.returncode != 0 and not proc.stdout.strip():
            raise DirectorError(f"Claude Code lỗi (mã {proc.returncode}): {proc.stderr.strip()[:800]}")
        return parse_output(proc.stdout)
