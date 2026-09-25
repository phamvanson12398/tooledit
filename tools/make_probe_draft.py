"""Tạo một draft "thăm dò" để biết CapCut 9.5.0 thực sự đọc file timeline nào.

CapCut 9.5.0 lưu cùng một timeline ở 5 chỗ (draft_content.json, template-2.tmp ở gốc và
trong Timelines/<id>/, cộng Timelines/<id>/attachment/patch/mini_draft.json). Script chép
draft mẫu thành draft mới, rồi ở MỖI file đổi chữ của lớp chữ đầu tiên thành một nhãn riêng
(ví dụ "GOC_CONTENT"). Mở draft mới trong CapCut: chữ hiện ra cho biết CapCut đã đọc file nào.

Vòng 1 (chỉ 4 file đầu) cho thấy CapCut vẫn hiện chữ gốc, tức là nó đọc mini_draft.json.
Vòng 2 tạo hai draft:
- <mẫu>_probe2: đổi chữ ở cả 5 file (mini_draft mang nhãn MINI_DRAFT);
- <mẫu>_probe3: đổi chữ ở 4 file và XÓA mini_draft.json, để xem CapCut có quay về đọc 4 file kia.

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
MINI_LABEL = "MINI_DRAFT"


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


def mini_draft_file(draft: Path) -> Path | None:
    """Bản sao thứ 5 của timeline (định dạng 'mini draft'), nằm trong attachment/patch/."""
    project = draft / "Timelines" / "project.json"
    if not project.is_file():
        return None
    main_id = json.loads(project.read_text(encoding="utf-8-sig"))["main_timeline_id"]
    path = draft / "Timelines" / main_id / "attachment" / "patch" / "mini_draft.json"
    return path if path.is_file() else None


def relabel_text_material(material: dict, label: str) -> None:
    content = json.loads(material["content"])
    content["text"] = label
    for style in content.get("styles", []):
        style["range"] = [0, len(label)]  # nhãn chỉ có ký tự ASCII
    material["content"] = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    if "base_content" in material:
        material["base_content"] = ""


def relabel_first_text(timeline: dict, label: str) -> str:
    """Đổi chữ của lớp chữ đầu tiên, trả về id vật liệu chữ đó."""
    texts = timeline["materials"]["texts"]
    if not texts:
        raise ValueError("Draft mẫu không có lớp chữ nào")
    relabel_text_material(texts[0], label)
    return texts[0]["id"]


def relabel_mini_draft(path: Path, material_id: str, label: str) -> bool:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    found = False
    for segment in data["mini_draft_data"].get("segments", []):
        material = segment.get("material") or {}
        if material.get("id") == material_id:
            relabel_text_material(material, label)
            found = True
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return found


def make_probe(src: Path, suffix: str = PROBE_SUFFIX, *, mini: str = "keep") -> Path:
    """mini: 'keep' giữ nguyên mini_draft.json, 'label' đổi chữ trong đó, 'remove' xóa nó."""
    dst = src.with_name(src.name + suffix)
    if dst.exists():
        raise FileExistsError(f"Đã có thư mục {dst}. Xóa nó trước rồi chạy lại.")
    shutil.copytree(src, dst)

    labels = []
    material_id = None
    for label, path in timeline_files(dst).items():
        timeline = json.loads(path.read_text(encoding="utf-8-sig"))
        material_id = relabel_first_text(timeline, label)
        path.write_text(json.dumps(timeline, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        labels.append(label)
        path.with_name(path.name + ".bak").unlink(missing_ok=True)

    mini_path = mini_draft_file(dst)
    if mini_path is not None:
        if mini == "label" and material_id and relabel_mini_draft(mini_path, material_id, MINI_LABEL):
            labels.append(MINI_LABEL)
        elif mini == "remove":
            shutil.rmtree(mini_path.parent.parent)  # cả thư mục attachment/
            labels.append("(đã xóa mini_draft)")

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
    # Vòng 2: đổi chữ cả trong mini_draft.json; và một bản đã xóa mini_draft.json.
    make_probe(args.draft_dir, "_probe2", mini="label")
    make_probe(args.draft_dir, "_probe3", mini="remove")
    return 0


if __name__ == "__main__":
    sys.exit(main())
