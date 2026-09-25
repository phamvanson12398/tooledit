"""Nạp preset phong cách trong styles/*.yaml."""

from __future__ import annotations

import yaml

from app.config import ROOT

STYLES_DIR = ROOT / "styles"


def load_style(name: str) -> dict:
    path = STYLES_DIR / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Chưa có preset phong cách {name} (styles/{name}.yaml)")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def available_styles() -> dict[str, dict]:
    """Tên preset → {name_vi, fits_vi, description_vi}."""
    out = {}
    for path in sorted(STYLES_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        out[path.stem] = {k: data.get(k, "") for k in ("name_vi", "fits_vi", "description_vi")}
    return out


def styles_for_prompt() -> str:
    return "\n".join(f"- {k}: {v['name_vi']} — hợp với: {v['fits_vi']}" for k, v in available_styles().items())


def layout_for(style: dict) -> dict | None:
    """Bố cục của kiểu dựng: khóa `layout` trong style, không có thì theo preset của config/layout.yaml.
    Trả None cho bố cục cũ (classic), còn lại là dict cấu hình kèm "name"."""
    from app import config

    lay = config.load("layout")
    name = style.get("layout") or lay.get("preset", "four_titles")
    if name == "classic" or not isinstance(lay.get(name), dict):
        return None
    return {**lay[name], "name": name}
