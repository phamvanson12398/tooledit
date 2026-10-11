"""FakeDirector: trả JSON mẫu cố định để test trong cloud (không gọi Claude Code)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from app.config import ROOT
from app.director.base import Director

FIXTURES = ROOT / "tests" / "fixtures" / "director"


_LOCK = threading.Lock()


def _for_video(value: list, prompt: str):
    """Danh sách trả lời cho NHIỀU video (video_index khác nhau): chọn đúng câu trả lời của "video số N" ghi ở dòng
    nhiệm vụ — runner hỏi các video song song nên thứ tự gọi không cố định (như AI thật đọc đề từng video)."""
    import re

    indexes = {v.get("video_index") for v in value if isinstance(v, dict)}
    m = re.search(r"#\s*Nhiệm vụ:[^\n]*?số\s+(\d+)", prompt)
    if not m or len(indexes) < 2:
        return None
    mine = [v for v in value if isinstance(v, dict) and v.get("video_index") == int(m.group(1))]
    if not mine:
        return None
    if len(mine) > 1:  # vài lượt cho cùng video (sai khuôn rồi sửa) → lần lượt
        value.remove(mine[0])
    return mine[0]


class FakeDirector(Director):
    def __init__(self, responses: dict[str, list[dict] | dict] | None = None, fixtures: Path = FIXTURES, **kwargs):
        super().__init__(**kwargs)
        self.responses = responses or {}
        self.fixtures = fixtures
        self.calls: list[dict] = []

    def _complete(self, task: str, prompt: str, schema: dict, images: list[Path]) -> dict:
        with _LOCK:  # runner có thể hỏi song song (app/jobs/parallel.py)
            self.calls.append({"task": task, "prompt": prompt, "images": list(images)})
            if task in self.responses:
                value = self.responses[task]
                if isinstance(value, list):
                    mine = _for_video(value, prompt)
                    if mine is not None:
                        return mine
                    # nhiều lượt trả lời lần lượt (để test gọi lại khi sai khuôn)
                    return value.pop(0) if len(value) > 1 else value[0]
                return value
        return json.loads((self.fixtures / f"{task}.json").read_text(encoding="utf-8"))
