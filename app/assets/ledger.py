"""Sổ nguồn assets/ledger.json: mọi file tải về / thêm vào kho đều ghi nguồn, URL, giấy phép, ngày thêm."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from app.config import ROOT

ASSETS_ROOT = ROOT / "assets"


def ledger_path(assets_root: Path = ASSETS_ROOT) -> Path:
    return Path(assets_root) / "ledger.json"


def load(assets_root: Path = ASSETS_ROOT) -> list[dict]:
    path = ledger_path(assets_root)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data.get("items", []) if isinstance(data, dict) else []


def add(assets_root: Path, file: Path, *, source: str, url: str = "", license: str = "", author: str = "",
        duration_us: int = 0, extra: dict | None = None) -> dict:
    """Ghi (hoặc cập nhật) một mục; `file` là đường dẫn trong assets_root."""
    assets_root = Path(assets_root)
    rel = Path(file).resolve().relative_to(assets_root.resolve()).as_posix()
    items = [i for i in load(assets_root) if i.get("file") != rel]
    entry = {"file": rel, "source": source, "url": url, "license": license, "author": author,
             "added": date.today().isoformat(), "duration_us": int(duration_us), **(extra or {})}
    items.append(entry)
    path = ledger_path(assets_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("ledger.json.writing")
    tmp.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return entry


def by_file(assets_root: Path = ASSETS_ROOT) -> dict[str, dict]:
    return {i["file"]: i for i in load(assets_root) if i.get("file")}
