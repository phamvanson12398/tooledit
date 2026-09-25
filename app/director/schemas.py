"""Khuôn (pydantic) cho kết quả của đạo diễn. Sai khuôn thì gọi lại kèm thông báo lỗi."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

STYLES = ("kr_variety", "jp_telop", "tiktok_retention", "storytelling", "healing", "professional")
Style = Literal["kr_variety", "jp_telop", "tiktok_retention", "storytelling", "healing", "professional"]
Language = Literal["ko", "ja", "en"]


class TimeRange(BaseModel):
    start: float = Field(ge=0, description="giây trong footage gốc")
    end: float = Field(gt=0, description="giây trong footage gốc")


class KeyMoment(TimeRange):
    why_vi: str = Field(description="vì sao khoảnh khắc này đáng chú ý (tiếng Việt)")


class Understanding(BaseModel):
    """Kết quả bước 'AI hiểu nội dung' (mục 3.3 CLAUDE.md)."""

    summary_vi: str = Field(description="tóm tắt một dòng bằng tiếng Việt")
    genre: str
    mood: str
    people_count: int = Field(ge=0)
    main_subject: str
    language: Language
    suggested_style: Style
    style_reason_vi: str
    key_moments: list[KeyMoment] = Field(min_length=1, max_length=12)
    editor_notes: str = Field(description="giải thích ngắn các nhận định chính (tiếng Việt)")


def check_ranges(ranges: list[TimeRange], duration: float, what: str = "mốc") -> list[str]:
    """Nguyên tắc cứng: mọi mốc giây phải nằm trong footage. Trả về danh sách lỗi (rỗng = hợp lệ)."""
    errors = []
    for i, r in enumerate(ranges):
        if r.end <= r.start:
            errors.append(f"{what} #{i + 1}: end ({r.end}) phải lớn hơn start ({r.start})")
        if r.end > duration + 0.5:
            errors.append(f"{what} #{i + 1}: {r.start}-{r.end}s vượt quá độ dài footage ({duration:.1f}s)")
    return errors


def compact_schema(model: type[BaseModel]) -> dict:
    """JSON Schema gửi qua --json-schema (giữ gọn vì dòng lệnh Windows giới hạn ~32k ký tự)."""
    return model.model_json_schema()
