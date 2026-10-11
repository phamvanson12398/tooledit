"""Backend gọi Gemini CLI (Google) ở chế độ không tương tác — chủ dự án chọn thêm Gemini Pro ngày 11/10, chọn AI cho
từng job. Đăng nhập bằng tài khoản Google có gói Google AI Pro ("Sign in with Google"), KHÔNG dùng API key.

Đối chiếu mã nguồn + tài liệu đi kèm gói npm `@google/gemini-cli` bản 0.63.0 (bundle/docs/cli/headless.md,
get-started/authentication.mdx, reference/policy-engine.md, reference/commands.md):
- `-p/--prompt`: chạy headless; nội dung stdin được ghép TRƯỚC prompt của `-p` (stdin + "\\n\\n" + prompt).
- `-o json`: in MỘT đối tượng JSON {response, stats, error?}. Gemini CLI không có cờ ép JSON Schema như Claude Code →
  schema được đưa vào prompt, kết quả validate bằng pydantic như mọi backend (sai thì Director gọi lại).
- `@<tên file>` trong prompt: CLI đọc file và gửi kèm (ảnh được gửi khi ghi ĐÚNG tên file) — cả ở chế độ headless
  (runNonInteractive gọi handleAtCommand). Đường dẫn sau `@` không tồn tại → CLI dừng với lỗi, nên mọi ký tự `@` khác
  trong nội dung (lời thoại, tên tài khoản…) được đổi thành `＠`.
- Công cụ cần hỏi quyền (chạy lệnh, ghi file) ở chế độ headless bị coi là `deny` → Gemini chỉ trả lời, không làm gì
  trên máy. `--skip-trust` tin thư mục làm việc tạm (chỉ chứa ảnh khung hình) cho phiên này.
- Đăng nhập: headless dùng thông tin đăng nhập đã lưu — chạy `gemini` một lần, chọn "Sign in with Google".
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from app import config
from app.director.base import DirectorError
from app.director.claude_cli import ClaudeCodeDirector, _run_stoppable

SAFE_AT = "＠"  # chữ @ toàn chiều rộng: Gemini CLI không coi là tham chiếu file

ANSWER_RULES = """

## CÁCH TRẢ LỜI (bắt buộc)
- Chỉ trả về MỘT đối tượng JSON đúng JSON Schema dưới đây — không giải thích, không markdown, không bọc trong ```.
- Không dùng công cụ nào (không chạy lệnh, không đọc / ghi file khác). Các khung hình đã được ĐÍNH KÈM ở cuối đề bài;
  chỗ nào đề bài nói "mở bằng Read" nghĩa là xem ảnh đính kèm có đúng tên file đó.

### JSON Schema
{schema}
"""


def _escape_ref(name: str) -> str:
    return name.replace("\\", "/").replace(" ", "\\ ")


def build_prompt(prompt: str, schema: dict, image_names: list[str]) -> str:
    """Đề bài + luật trả lời JSON + tham chiếu ảnh `@tên_file` (chỉ các @ này là thật)."""
    body = (prompt + ANSWER_RULES.format(schema=json.dumps(schema, ensure_ascii=False))).replace("@", SAFE_AT)
    if image_names:
        body += "\n## Khung hình đính kèm\n" + "\n".join(f"{n}: @{_escape_ref(n)}" for n in image_names) + "\n"
    return body


def build_command(exe: str, model: str | None = None) -> list[str]:
    cmd = [exe, "-p", "Làm đúng yêu cầu ở trên và chỉ trả về JSON.", "-o", "json", "--skip-trust"]
    if model:
        cmd += ["-m", model]
    return cmd


def _friendly(message: str) -> str:
    low = message.lower()
    if any(k in low for k in ("auth", "login", "sign in", "credential", "gemini_api_key")):
        return ("Gemini CLI chưa đăng nhập. Mở PowerShell, gõ `gemini`, chọn **Sign in with Google**, đăng nhập tài khoản "
                "Google có gói AI Pro trên trình duyệt, rồi gõ `/quit` và chạy lại job. (Thông báo gốc: "
                + message[:200] + ")")
    if any(k in low for k in ("quota", "429", "resource_exhausted", "rate limit")):
        return ("Gemini đã hết hạn mức tạm thời của gói (quota). Đợi một lúc rồi bấm Tiếp tục, hoặc đổi job này sang "
                "Claude ở trang job. (Thông báo gốc: " + message[:200] + ")")
    return f"Gemini CLI báo lỗi: {message[:800]}"


def extract_json(text: str) -> dict:
    """Lấy đối tượng JSON trong câu trả lời (bỏ ```json … ``` nếu model lỡ bọc)."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    raise DirectorError(f"Không tìm thấy JSON trong câu trả lời của Gemini: {text[:500]}")


def parse_output(stdout: str, stderr: str = "", returncode: int = 0) -> dict:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        # Gemini CLI 0.63.0 (đã chạy thử): lỗi ở chế độ -o json được in thành JSON {error: {message, code}} ra STDERR,
        # stdout trống (vd chưa đăng nhập → mã thoát 41)
        msg = (stderr or stdout or "").strip() or f"mã thoát {returncode}"
        try:
            err = json.loads(stderr).get("error") or {}
            msg = str(err.get("message") or msg) if isinstance(err, dict) else str(err)
        except (json.JSONDecodeError, AttributeError):
            pass
        raise DirectorError(_friendly(msg)) from None
    if not isinstance(data, dict):
        raise DirectorError(f"Gemini CLI trả kết quả lạ: {stdout[:300]}")
    err = data.get("error")
    if err:
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise DirectorError(_friendly(str(msg or err)))
    return extract_json(str(data.get("response") or ""))


class GeminiCliDirector(ClaudeCodeDirector):
    """Dùng chung thư mục làm việc tạm + nút Dừng với backend Claude; chỉ khác lệnh gọi và cách đọc kết quả."""

    def __init__(self, cfg: dict | None = None, **kwargs):
        cfg = cfg or config.load("director")
        super().__init__(cfg, **kwargs)
        name = cfg.get("gemini_exe") or "gemini"
        self.exe = shutil.which(name) or name

    def _complete(self, task: str, prompt: str, schema: dict, images: list[Path]) -> dict:
        workdir = self._prepare_workdir(task, images)
        cmd = build_command(self.exe, self.cfg.get("gemini_model"))
        full = build_prompt(prompt, schema, [Path(i).name for i in images])
        self.log(f"Đang hỏi đạo diễn AI Gemini ({task})...")
        timeout = self.cfg.get("timeout_s", 900)
        try:
            proc = _run_stoppable(cmd, full, workdir, timeout)
        except FileNotFoundError as exc:
            raise DirectorError("Không tìm thấy lệnh `gemini`. Cài Gemini CLI: nhấp đúp install_gemini.bat "
                                "(docs/SETUP_WINDOWS.md mục Gemini).") from exc
        except subprocess.TimeoutExpired as exc:
            raise DirectorError(f"Gemini không trả lời sau {timeout} giây.") from exc
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        return parse_output(proc.stdout, proc.stderr, proc.returncode)
