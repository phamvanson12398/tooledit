"""Cài đặt riêng của máy (API key...) lưu ở config/local.yaml — bị gitignore, không commit."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.config import CONFIG_DIR

LOCAL = CONFIG_DIR / "local.yaml"


def load(path: Path = LOCAL) -> dict:
    if not Path(path).is_file():
        return {}
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def save(values: dict, path: Path = LOCAL) -> None:
    data = {**load(path), **values}
    Path(path).write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
