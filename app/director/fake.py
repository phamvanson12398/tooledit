"""FakeDirector: trả JSON mẫu cố định để test trong cloud (không gọi Claude Code)."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import ROOT
from app.director.base import Director

FIXTURES = ROOT / "tests" / "fixtures" / "director"


class FakeDirector(Director):
    def __init__(self, responses: dict[str, list[dict] | dict] | None = None, fixtures: Path = FIXTURES, **kwargs):
        super().__init__(**kwargs)
        self.responses = responses or {}
        self.fixtures = fixtures
        self.calls: list[dict] = []

    def _complete(self, task: str, prompt: str, schema: dict, images: list[Path]) -> dict:
        self.calls.append({"task": task, "prompt": prompt, "images": list(images)})
        if task in self.responses:
            value = self.responses[task]
            if isinstance(value, list):  # nhiều lượt trả lời lần lượt (để test gọi lại khi sai khuôn)
                return value.pop(0) if len(value) > 1 else value[0]
            return value
        return json.loads((self.fixtures / f"{task}.json").read_text(encoding="utf-8"))
