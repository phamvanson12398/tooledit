"""Cấu hình chung cho test: không test nào được ghi / đọc config/local.yaml thật của máy (tốc độ giọng đo được,
đường dẫn CapCut...) — mỗi test dùng một file local.yaml riêng trong thư mục tạm."""

import pytest


@pytest.fixture(autouse=True)
def _isolated_local_settings(tmp_path, monkeypatch):
    from app import settings

    local = tmp_path / "_local_settings.yaml"
    monkeypatch.setattr(settings, "LOCAL", local)
    monkeypatch.setattr(settings.load, "__defaults__", (local,))
    monkeypatch.setattr(settings.save, "__defaults__", (local,))


@pytest.fixture(autouse=True)
def _isolated_scene_library(tmp_path, monkeypatch):
    """Kho cảnh chung (library/) của test nằm trong thư mục tạm — không đụng kho thật của máy."""
    from app import config, scene_library

    real = config.load("library") or {}
    monkeypatch.setattr(scene_library, "cfg", lambda: {**real, "root": str(tmp_path / "_library")})
