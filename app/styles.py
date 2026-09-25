"""Nạp preset phong cách trong styles/*.yaml."""

from __future__ import annotations

import yaml

from app.config import ROOT


def load_style(name: str) -> dict:
    path = ROOT / "styles" / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Chưa có preset phong cách {name} (styles/{name}.yaml)")
    return yaml.safe_load(path.read_text(encoding="utf-8"))
