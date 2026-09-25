"""Kiểm tra một thư mục dự án CapCut (draft) để viết báo cáo tương thích.

Chạy:  python tools/inspect_draft.py <thư_mục_draft> [--json]

Script chỉ ĐỌC, không sửa gì. Nó cho biết:
- file timeline nào có trong thư mục (gốc và Timelines/<id>/), file nào parse được JSON
  (không parse được = nhiều khả năng bị mã hóa);
- phiên bản CapCut ghi trong draft (platform, last_modified_platform, version, new_version);
- các tài nguyên tham chiếu bằng effect_id / resource_id (hiệu ứng, chuyển cảnh, filter,
  animation chữ, sticker, âm thanh/nhạc từ thư viện) và đường dẫn file của chúng.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TIMELINE_FILES = ("draft_content.json", "draft_info.json", "draft_meta_info.json", "template-2.tmp")

# Các nhóm vật liệu trong "materials" có tham chiếu tới tài nguyên của CapCut.
RESOURCE_KINDS = (
    "video_effects",
    "effects",
    "transitions",
    "filters",
    "material_animations",
    "stickers",
    "audios",
    "audio_effects",
    "text_templates",
)

ID_KEYS = ("effect_id", "resource_id", "music_id", "third_resource_id", "category_id", "category_name")


def read_json(path: Path) -> tuple[Any | None, str]:
    """Trả về (dữ liệu, trạng thái). Trạng thái: 'json', 'encrypted?' hoặc 'broken-json'."""
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace").lstrip()
    if not text.startswith("{"):
        return None, "encrypted?"
    try:
        return json.loads(text), "json"
    except json.JSONDecodeError:
        return None, "broken-json"


def find_timeline(data: Any) -> dict | None:
    """Timeline có thể nằm ở gốc hoặc bọc trong một object/chuỗi JSON."""
    if isinstance(data, dict):
        if "tracks" in data and "materials" in data:
            return data
        for value in data.values():
            if isinstance(value, str) and value.lstrip().startswith("{"):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    continue
            if isinstance(value, dict) and "tracks" in value and "materials" in value:
                return value
    return None


def summarize_timeline(tl: dict) -> dict:
    materials = tl.get("materials", {}) or {}
    resources: dict[str, list[dict]] = {}
    for kind in RESOURCE_KINDS:
        items = materials.get(kind) or []
        rows = []
        for item in items:
            if not isinstance(item, dict):
                continue
            row = {k: item[k] for k in ("name", "type", "path", *ID_KEYS) if item.get(k) not in (None, "")}
            # animation lưu danh sách con trong "animations"
            if kind == "material_animations":
                row["animations"] = [
                    {k: a.get(k) for k in ("name", "type", "id", "resource_id") if a.get(k)}
                    for a in item.get("animations", [])
                ]
            rows.append(row)
        if rows:
            resources[kind] = rows
    canvas = tl.get("canvas_config", {}) or {}
    return {
        "version": tl.get("version"),
        "new_version": tl.get("new_version"),
        "platform": tl.get("platform"),
        "last_modified_platform": tl.get("last_modified_platform"),
        "canvas": {k: canvas.get(k) for k in ("width", "height", "ratio")},
        "duration_us": tl.get("duration"),
        "tracks": [
            {"type": t.get("type"), "segments": len(t.get("segments", []))} for t in tl.get("tracks", [])
        ],
        "material_counts": {k: len(v) for k, v in materials.items() if isinstance(v, list) and v},
        "resources": resources,
    }


def inspect(draft_dir: Path) -> dict:
    report: dict = {"draft_dir": str(draft_dir), "files": []}
    candidates = [draft_dir / name for name in TIMELINE_FILES]
    timelines_dir = draft_dir / "Timelines"
    if timelines_dir.is_dir():
        candidates += sorted([*timelines_dir.rglob("*.json"), *timelines_dir.rglob("*.tmp")])
    for path in candidates:
        if not path.is_file():
            continue
        data, status = read_json(path)
        entry: dict = {
            "file": str(path.relative_to(draft_dir)),
            "size": path.stat().st_size,
            "status": status,
        }
        tl = find_timeline(data) if data is not None else None
        if tl is not None:
            entry["timeline"] = summarize_timeline(tl)
        elif isinstance(data, dict):
            entry["top_level_keys"] = sorted(data.keys())[:40]
        report["files"].append(entry)
    return report


def print_human(report: dict) -> None:
    print(f"Thư mục: {report['draft_dir']}")
    if not report["files"]:
        print("  Không thấy file timeline nào. Kiểm tra lại đường dẫn.")
    for f in report["files"]:
        status = {
            "json": "đọc được (JSON, KHÔNG mã hóa)",
            "encrypted?": "KHÔNG đọc được - có thể bị MÃ HÓA",
            "broken-json": "bắt đầu bằng '{' nhưng lỗi JSON - có thể hỏng",
        }[f["status"]]
        print(f"\n- {f['file']} ({f['size']} byte): {status}")
        tl = f.get("timeline")
        if not tl:
            if "top_level_keys" in f:
                print(f"    (không phải timeline) khóa: {', '.join(f['top_level_keys'])}")
            continue
        print(f"    version={tl['version']} new_version={tl['new_version']}")
        print(f"    platform={tl['platform']}")
        print(f"    last_modified_platform={tl['last_modified_platform']}")
        print(f"    canvas={tl['canvas']} duration_us={tl['duration_us']}")
        print(f"    tracks={tl['tracks']}")
        for kind, rows in tl["resources"].items():
            print(f"    [{kind}]")
            for row in rows:
                print(f"      {json.dumps(row, ensure_ascii=False)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("draft_dir", type=Path)
    parser.add_argument("--json", action="store_true", help="in kết quả dạng JSON")
    args = parser.parse_args(argv)
    if not args.draft_dir.is_dir():
        print(f"Không tìm thấy thư mục: {args.draft_dir}", file=sys.stderr)
        return 2
    report = inspect(args.draft_dir)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
