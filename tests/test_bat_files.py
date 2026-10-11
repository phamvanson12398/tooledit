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
