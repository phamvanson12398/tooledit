"""Tạo một draft "thăm dò" để biết CapCut 9.5.0 thực sự đọc file timeline nào.

CapCut 9.5.0 lưu cùng một timeline ở 4 chỗ (draft_content.json, template-2.tmp ở gốc và
trong Timelines/<id>/). Script chép draft mẫu thành một draft mới, rồi ở MỖI file đổi chữ
của lớp chữ đầu tiên thành một nhãn riêng (ví dụ "GOC_CONTENT"). Mở draft mới trong CapCut:
chữ hiện ra cho biết CapCut đã đọc file nào.

Chạy trên Windows (đóng CapCut trước):
    python tools\\make_probe_draft.py "%LOCALAPPDATA%\\CapCut\\User Data\\Projects\\com.lveditor.draft\\<thư_mục_mẫu>"
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from pathlib import Path

PROBE_SUFFIX = "_probe"


def timeline_files(draft: Path) -> dict[str, Path]:
    """Nhãn -> file timeline có trong draft."""
    files = {
        "GOC_CONTENT": draft / "draft_content.json",
        "GOC_TEMPLATE2": draft / "template-2.tmp",
    }
    project = draft / "Timelines" / "project.json"
    if project.is_file():
        main_id = json.loads(project.read_text(encoding="utf-8-sig"))["main_timeline_id"]
        nested = draft / "Timelines" / main_id
        files["TRONG_CONTENT"] = nested / "draft_content.json"
        files["TRONG_TEMPLATE2"] = nested / "template-2.tmp"
    return {label: path for label, path in files.items() if path.is_file()}


def relabel_first_text(timeline: dict, label: str) -> None:
    texts = timeline["materials"]["texts"]
    if not texts:
        raise ValueError("Draft mẫu không có lớp chữ nào")
    content = json.loads(texts[0]["content"])
    content["text"] = label
    for style in content.get("styles", []):
        style["range"] = [0, len(label)]  # nhãn chỉ có ký tự ASCII
    texts[0]["content"] = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    if "base_content" in texts[0]:
        texts[0]["base_content"] = ""


def make_probe(src: Path) -> Path:
    dst = src.with_name(src.name + PROBE_SUFFIX)
    if dst.exists():
        raise FileExistsError(f"Đã có thư mục {dst}. Xóa nó trước rồi chạy lại.")
    shutil.copytree(src, dst)

    labels = []
    for label, path in timeline_files(dst).items():
        timeline = json.loads(path.read_text(encoding="utf-8-sig"))
        relabel_first_text(timeline, label)
        path.write_text(json.dumps(timeline, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        labels.append(label)
        for bak in (path.with_name(path.name + ".bak"),):
            bak.unlink(missing_ok=True)

    meta_path = dst / "draft_meta_info.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        meta["draft_name"] = dst.name
        meta["draft_fold_path"] = dst.as_posix()
        meta["draft_id"] = str(uuid.uuid4()).upper()
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"Đã tạo: {dst}")
    print(f"Các nhãn đã ghi: {', '.join(labels)}")
    return dst


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("draft_dir", type=Path, help="thư mục draft mẫu do CapCut tạo")
    args = parser.parse_args(argv)
    if not args.draft_dir.is_dir():
        print(f"Không tìm thấy thư mục: {args.draft_dir}", file=sys.stderr)
        return 2
    make_probe(args.draft_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
