"""Đạo diễn AI (mục 11 CLAUDE.md)."""

from __future__ import annotations

from app import config
from app.director.base import Director, DirectorError


AI_NAMES = {"claude": "Claude (Claude Code)", "gemini": "Gemini Pro (Gemini CLI)"}


def get_director(cfg: dict | None = None, ai: str | None = None, **kwargs) -> Director:
    """ai: "claude" | "gemini" — AI chọn cho từng job (chủ dự án 11/10); None = `default_ai` trong config/director.yaml."""
    cfg = cfg or config.load("director")
    if cfg.get("backend") == "fake":
        from app.director.fake import FakeDirector

        return FakeDirector(**kwargs)
    if (ai or cfg.get("default_ai") or "claude") == "gemini":
        from app.director.gemini_cli import GeminiCliDirector

        return GeminiCliDirector(cfg, **kwargs)
    from app.director.claude_cli import ClaudeCodeDirector

    return ClaudeCodeDirector(cfg, **kwargs)


__all__ = ["AI_NAMES", "Director", "DirectorError", "get_director"]
