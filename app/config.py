"""Nạp cấu hình YAML trong thư mục config/."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"


@lru_cache(maxsize=None)
def load(name: str) -> dict:
    """Đọc config/<name>.yaml; không có file thì trả {}."""
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
