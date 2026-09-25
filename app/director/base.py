"""Lớp Director: ghép prompt, gọi backend, validate bằng pydantic, gọi lại khi sai khuôn.

Backend chỉ cần cài `_complete(prompt, schema, images, workdir) -> dict`. Nhờ vậy sau này có thể thay
Claude Code bằng chế độ copy–paste thủ công hoặc mô hình local mà không sửa phần còn lại (mục 11).
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import ROOT

T = TypeVar("T", bound=BaseModel)
PROMPTS_DIR = ROOT / "prompts"


class DirectorError(RuntimeError):
    pass


def render_prompt(task: str, variables: dict, prompts_dir: Path = PROMPTS_DIR) -> str:
    """Ghép phần vai trò chung + template của nhiệm vụ; thay {{biến}} (không dùng str.format vì JSON có {})."""
    persona = (prompts_dir / "_editor_persona.md").read_text(encoding="utf-8")
    template = (prompts_dir / f"{task}.md").read_text(encoding="utf-8")

    def sub(match: re.Match) -> str:
        key = match.group(1)
        if key not in variables:
            raise KeyError(f"Template {task}.md cần biến {{{{{key}}}}} nhưng không được cung cấp")
        return str(variables[key])

    return persona.strip() + "\n\n" + re.sub(r"\{\{(\w+)\}\}", sub, template).strip() + "\n"


class Director(ABC):
    def __init__(self, max_attempts: int = 3, log: Callable[[str], None] = lambda m: None):
        self.max_attempts = max_attempts
        self.log = log

    @abstractmethod
    def _complete(self, task: str, prompt: str, schema: dict, images: list[Path]) -> dict:
        """Gửi prompt, trả về đối tượng JSON (chưa validate)."""

    def run(self, task: str, variables: dict, model: type[T], images: list[Path] | None = None,
            extra_check: Callable[[T], list[str]] | None = None) -> T:
        prompt = render_prompt(task, variables)
        schema = model.model_json_schema()
        feedback = ""
        for attempt in range(1, self.max_attempts + 1):
            raw = self._complete(task, prompt + feedback, schema, images or [])
            try:
                result = model.model_validate(raw)
                problems = extra_check(result) if extra_check else []
                if not problems:
                    return result
                message = "\n".join(problems)
            except ValidationError as exc:
                message = str(exc)
            self.log(f"Kết quả của đạo diễn chưa hợp lệ (lần {attempt}): {message.splitlines()[0]}")
            feedback = (
                "\n\n## Kết quả lần trước KHÔNG hợp lệ, hãy sửa và trả lại toàn bộ JSON\n"
                f"Lỗi:\n{message}\n\nJSON lần trước:\n{json.dumps(raw, ensure_ascii=False)[:4000]}\n"
            )
        raise DirectorError(f"Đạo diễn trả kết quả sai khuôn {self.max_attempts} lần liên tiếp ({task}).")
