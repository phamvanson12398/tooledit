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


class NameCorrection(BaseModel):
    wrong: str = Field(description="chữ nhận dạng sai trong transcript")
    right: str = Field(description="cách viết đúng")
    evidence_vi: str = Field(description="căn cứ (ví dụ chữ trên khung hình nào)")


class BurnedInText(BaseModel):
    present: bool = Field(description="footage gốc đã có chữ in sẵn (テロップ, tiêu đề, logo)?")
    regions: list[Literal["top", "center", "bottom", "top_left", "top_right", "bottom_left", "bottom_right"]] = []
    note_vi: str = ""


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
    usable_range: TimeRange = Field(description="đoạn chứa mạch nội dung chính, bỏ phần thừa đầu/cuối")
    name_corrections: list[NameCorrection] = Field(default_factory=list)
    burned_in_text: BurnedInText
    sensitive_notes_vi: list[str] = Field(
        default_factory=list, description="điều KHÔNG được viết/ám chỉ trên màn hình hay trong hook")
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
