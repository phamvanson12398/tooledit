"""Backend gọi Antigravity CLI (`agy`, Google) ở chế độ không tương tác — AI đạo diễn "Gemini Pro" của từng job.

Vì sao Antigravity: từ 18/06/2026 Google ngừng cho tài khoản cá nhân / Google AI Pro đăng nhập Gemini CLI bằng "Sign in
with Google" và chuyển sang Antigravity (chủ dự án gặp lỗi "This client is no longer supported…" ngày 11/10 rồi chọn
chuyển sang Antigravity CLI). Đăng nhập bằng tài khoản Google có gói AI Pro, KHÔNG dùng API key.

Cờ lệnh + hành vi đối chiếu với `agy --help` và các lần chạy thử THẬT trên máy chủ dự án (agy 1.3.3, Windows, 11/10):
- `-p/--print "<lời nhắn>"`: chạy một lượt không tương tác. Nội dung đưa qua stdin KHÔNG được đọc (thử 2 lần: AI không
  thấy nội dung, đi chạy lệnh để tìm) → đề bài ghi vào file `de_bai.md` trong thư mục làm việc, lời nhắn `-p` bảo AI đọc
  file đó (đề bài dài, cũng không nhét được vào dòng lệnh Windows).
- AI tự đọc được file chữ + file ảnh trong thư mục làm việc mà không cần xin quyền (thử: đọc yeucau.txt rồi xem anh.jpg,
  chép đúng chữ "CON MEO 58").
- `--output-format json`: một đối tượng JSON {conversation_id, status: "SUCCESS", response, structured_output,
  json_schema, usage, denied_actions?}. `--json-schema <chuỗi | đường dẫn file>` ép khuôn kết quả → nằm ở
  `structured_output` (thử: {"secret": 4729}).
- Công cụ cần xin quyền (chạy lệnh "RunCommand") ở chế độ này tự bị TỪ CHỐI (ghi vào `denied_actions`, stderr báo
  "jetski: no output produced…") → AI không làm gì trên máy. KHÔNG dùng `--dangerously-skip-permissions`.
- Ghi kết quả ra file / ống (không phải màn hình) vẫn có đủ JSON (thử bằng `> out.txt`).
- `agy` tự cập nhật ngầm (không ghim được bản) → nếu sau này đổi định dạng, lỗi được báo rõ bằng tiếng Việt.
- Cài ở `%LOCALAPPDATA%\\agy\\bin\\agy.exe`, có thể chưa có trong PATH → tool tự tìm ở đó.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from app import config
from app.director.base import DirectorError
from app.director.claude_cli import ClaudeCodeDirector, _run_stoppable

PROMPT_FILE = "de_bai.md"
SCHEMA_FILE = "schema.json"
# lời nhắn -p để chữ không dấu (dòng lệnh Windows) — toàn bộ đề bài nằm trong file
PRINT_MESSAGE = (f"Doc file {PROMPT_FILE} trong thu muc hien tai va lam dung theo yeu cau trong do. "
                 "Chi doc file trong thu muc nay, khong chay lenh nao. Tra ket qua dung khuon JSON schema.")

IMAGE_NOTE = """

## Khung hình
Các khung hình là file ảnh nằm ngay trong thư mục hiện tại (đúng tên file ghi trong đề bài): {names}.
Chỗ nào đề bài nói "mở bằng Read" nghĩa là dùng công cụ đọc file của bạn để XEM ảnh đó. Không chạy lệnh nào.
"""


def find_exe(name: str | None = None) -> str:
    """`agy` trong PATH, không có thì chỗ trình cài đặt chính thức để file (%LOCALAPPDATA%\\agy\\bin\\agy.exe)."""
    name = name or "agy"
    found = shutil.which(name)
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local and Path(name).name in ("agy", "agy.exe"):
        p = Path(local) / "agy" / "bin" / "agy.exe"
        if p.is_file():
            return str(p)
    return name


def build_command(exe: str, model: str | None = None, effort: str | None = None) -> list[str]:
    cmd = [exe, "-p", PRINT_MESSAGE, "--output-format", "json", "--json-schema", SCHEMA_FILE]
    if model:
        cmd += ["--model", model]
    if effort:
        cmd += ["--effort", effort]
    return cmd


def write_task_files(workdir: Path, prompt: str, schema: dict, image_names: list[str]) -> None:
    text = prompt + (IMAGE_NOTE.format(names=", ".join(image_names)) if image_names else "")
    (workdir / PROMPT_FILE).write_text(text, encoding="utf-8")
    (workdir / SCHEMA_FILE).write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")


def _friendly(message: str) -> str:
    low = message.lower()
    if any(k in low for k in ("login", "log in", "sign in", "signin", "auth", "credential", "unauthenticated")):
        return ("Antigravity CLI chưa đăng nhập. Mở PowerShell, gõ `agy`, đăng nhập tài khoản Google có gói AI Pro, "
                "thấy giao diện chat thì thoát (`/quit`), rồi bấm Chạy tiếp. (Thông báo gốc: " + message[:200] + ")")
    if any(k in low for k in ("quota", "429", "resource_exhausted", "rate limit", "usage limit")):
        return ("Gemini (Antigravity) đã hết hạn mức tạm thời của gói. Đợi một lúc rồi bấm Chạy tiếp, hoặc đổi job này "
                "sang Claude ở trang job. (Thông báo gốc: " + message[:200] + ")")
    return f"Antigravity CLI báo lỗi: {message[:800]}"


def _json_in(text: str) -> dict | None:
    text = (text or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def parse_output(stdout: str, stderr: str = "", returncode: int = 0) -> dict:
    try:
        data = json.loads((stdout or "").strip())
    except json.JSONDecodeError:
        msg = (stderr or stdout or "").strip() or f"mã thoát {returncode}"
        raise DirectorError(_friendly(msg)) from None
    if not isinstance(data, dict):
        raise DirectorError(f"Antigravity CLI trả kết quả lạ: {str(stdout)[:300]}")
    if isinstance(data.get("structured_output"), dict) and data["structured_output"]:
        return data["structured_output"]
    status = str(data.get("status") or "")
    if status and status.upper() != "SUCCESS":
        err = data.get("error") or data.get("response") or stderr or status
        raise DirectorError(_friendly(str(err.get("message") if isinstance(err, dict) else err)))
    found = _json_in(str(data.get("response") or ""))
    if found is not None:
        return found
    denied = ", ".join(str(d.get("display_name") or d.get("action")) for d in data.get("denied_actions") or []
                       if isinstance(d, dict))
    if denied:
        raise DirectorError(f"Gemini (Antigravity) không trả lời vì định dùng công cụ bị chặn ({denied}) — tool sẽ hỏi lại."
                            + (f" Chi tiết: {stderr.strip()[:300]}" if stderr.strip() else ""))
    raise DirectorError(_friendly(stderr.strip() or "không có kết quả (response trống)"))


class AntigravityDirector(ClaudeCodeDirector):
    """Dùng chung thư mục làm việc tạm (mỗi lần gọi một thư mục, chứa khung hình) + nút Dừng với backend Claude."""

    def __init__(self, cfg: dict | None = None, **kwargs):
        cfg = cfg or config.load("director")
        super().__init__(cfg, **kwargs)
        self.exe = find_exe(cfg.get("agy_exe"))

    def _complete(self, task: str, prompt: str, schema: dict, images: list[Path]) -> dict:
        workdir = self._prepare_workdir(task, images)
        names, note = self._packed_info()  # nhiều khung hình → đã ghép ảnh lưới
        write_task_files(workdir, prompt + note, schema, names)
        cmd = build_command(self.exe, self.cfg.get("agy_model"), self.cfg.get("agy_effort"))
        self.log(f"Đang hỏi đạo diễn AI Gemini qua Antigravity ({task})...")
        timeout = self.cfg.get("timeout_s", 900)
        try:
            proc = _run_stoppable(cmd, "", workdir, timeout)
        except FileNotFoundError as exc:
            raise DirectorError("Không tìm thấy Antigravity CLI (`agy`). Cài theo docs/SETUP_WINDOWS.md mục Gemini "
                                "(Antigravity), hoặc nhấp đúp install_antigravity.bat.") from exc
        except subprocess.TimeoutExpired as exc:
            raise DirectorError(f"Gemini (Antigravity) không trả lời sau {timeout} giây.") from exc
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        return parse_output(proc.stdout, proc.stderr, proc.returncode)
