"""Chép một thư mục draft CapCut sang chỗ khác, bỏ media và xóa thông tin định danh máy.

Chạy:  python tools/sanitize_draft.py <draft_nguồn> <thư_mục_đích>

- Chỉ chép file văn bản (JSON, .tmp, .extra...), bỏ ảnh/video/âm thanh và file .bak.
- Thay tên user Windows trong đường dẫn (C:/Users/<tên>/) bằng <USER>.
- Xóa giá trị device_id, mac_address, hard_disk_id.
Nội dung được thay bằng chuỗi, không parse lại JSON, để giữ nguyên bố cục file gốc.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

SKIP_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bak",
    ".mp4", ".mov", ".mkv", ".avi", ".webm",
    ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg",
}

# C:/Users/ten/  hoặc  C:\\Users\\ten\\  (dạng escape trong JSON)
USER_PATH = re.compile(r"(?i)([A-Z]:(?:/|\\\\|\\)Users(?:/|\\\\|\\))([^/\\\"]+)")
MACHINE_IDS = re.compile(r'("(?:device_id|mac_address|hard_disk_id)"\s*:\s*")[^"]*(")')


def sanitize_text(text: str) -> str:
    text = USER_PATH.sub(r"\1<USER>", text)
    return MACHINE_IDS.sub(r"\1\2", text)


def sanitize_draft(src: Path, dst: Path) -> list[Path]:
    written = []
    for path in sorted(src.rglob("*")):
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        target = dst / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            shutil.copyfile(path, target)
        else:
            target.write_bytes(sanitize_text(text).encode("utf-8"))
        written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("src", type=Path)
    parser.add_argument("dst", type=Path)
    args = parser.parse_args(argv)
    if not args.src.is_dir():
        print(f"Không tìm thấy thư mục: {args.src}", file=sys.stderr)
        return 2
    for path in sanitize_draft(args.src, args.dst):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
