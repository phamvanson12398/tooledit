"""File .bat chạy trên Windows của chủ dự án — không chạy thử được ở cloud, nên kiểm tra các lỗi cú pháp hay gặp.

Lỗi thật 11/10: `echo ... (khoang 3 GB) ...` nằm trong khối `if ( ... ) else ( ... )` — dấu `)` trong chữ bị cmd hiểu là
đóng khối → "... was unexpected at this time" → cửa sổ install_omnivoice.bat tự tắt sau bước 2."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BATS = sorted(ROOT.glob("*.bat"))


def _echo_text(line: str) -> str | None:
    m = re.match(r"\s*echo(?:\.|\s+)(.*)$", line, re.I)
    if not m:
        return None
    return re.sub(r"\s*\d?>\s*nul\b.*$", "", m.group(1), flags=re.I)  # bỏ phần chuyển hướng >nul có chủ đích


@pytest.mark.parametrize("bat", BATS, ids=lambda p: p.name)
def test_echo_lines_have_no_cmd_special_chars(bat):
    bad = [f"dòng {i}: {ln.strip()}" for i, ln in enumerate(bat.read_text(encoding="utf-8").splitlines(), 1)
           if (t := _echo_text(ln)) is not None and re.search(r"[()&|<>]", t)]
    assert not bad, "dòng echo có ký tự đặc biệt của cmd (dùng dấu - thay cho ngoặc):\n" + "\n".join(bad)


@pytest.mark.parametrize("bat", BATS, ids=lambda p: p.name)
def test_blocks_are_balanced(bat):
    depth = 0
    for i, ln in enumerate(bat.read_text(encoding="utf-8").splitlines(), 1):
        code = re.sub(r'"[^"]*"', "", ln)  # chữ trong ngoặc kép không tính
        if _echo_text(code) is not None or re.match(r"\s*(rem\b|::)", code, re.I):
            continue
        depth += code.count("(") - code.count(")")
        assert depth >= 0, f"{bat.name} dòng {i}: dư dấu )"
    assert depth == 0, f"{bat.name}: khối ( ... ) chưa đóng"


def test_scripts_exist():
    assert {"install.bat", "install_omnivoice.bat", "start.bat"} <= {p.name for p in BATS}


@pytest.mark.parametrize("bat", BATS, ids=lambda p: p.name)
def test_cmd_scripts_are_called(bat):
    """npm / gemini là file .cmd: gọi không có `call` thì cmd chuyển hẳn sang đó và KHÔNG quay lại file .bat."""
    bad = [f"dòng {i}: {ln.strip()}" for i, ln in enumerate(bat.read_text(encoding="utf-8").splitlines(), 1)
           if re.match(r"\s*(npm|npx|gemini)\b", ln, re.I)]
    assert not bad, "thiếu `call` trước lệnh .cmd:\n" + "\n".join(bad)


def test_gpu_torch_bat_does_not_require_torchaudio():
    """Chủ dự án 11/10: máy có demucs 4.1 nhưng không có torchaudio → file cài báo "No module named 'torchaudio'"."""
    text = (ROOT / "install_gpu_torch.bat").read_text(encoding="utf-8")
    read_line = next(ln for ln in text.splitlines() if "torch_ver.txt', 'w'" in ln)
    assert "torchaudio" not in read_line                                    # đọc phiên bản chỉ cần torch
    assert 'import torchaudio" 2>nul' in text and "if not errorlevel 1 set AUDIO=" in text  # có thì đổi luôn
    assert "torch==%TV%+cu126 %AUDIO%" in text and "call :fallback" in text
