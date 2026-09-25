"""Đạo diễn AI (mục 11 CLAUDE.md)."""

from __future__ import annotations

from app import config
from app.director.base import Director, DirectorError


def get_director(cfg: dict | None = None, **kwargs) -> Director:
    cfg = cfg or config.load("director")
    if cfg.get("backend") == "fake":
        from app.director.fake import FakeDirector

        return FakeDirector(**kwargs)
    from app.director.claude_cli import ClaudeCodeDirector

    return ClaudeCodeDirector(cfg, **kwargs)


__all__ = ["Director", "DirectorError", "get_director"]
