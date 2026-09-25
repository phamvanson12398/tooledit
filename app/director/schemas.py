"""Khuôn (pydantic) cho kết quả của đạo diễn. Sai khuôn thì gọi lại kèm thông báo lỗi."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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
    suggested_style: str = Field(description="tên preset phong cách, phải thuộc danh sách được cung cấp")
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


# ---------------- Hook (mục 5) ----------------

HookType = Literal["climax_first", "open_question", "contrast", "half_reveal", "odd_detail"]
HOOK_TYPES_VI = {
    "climax_first": "tua thẳng đến cao trào",
    "open_question": "câu hỏi bỏ lửng",
    "contrast": "tương phản",
    "half_reveal": "hé lộ một nửa",
    "odd_detail": "con số / chi tiết lạ",
}


class HookOption(BaseModel):
    hook_type: HookType
    line: str = Field(description="câu hook để thu voice, văn nói tự nhiên bằng NGÔN NGỮ CỦA VIDEO")
    line_vi: str = Field(description="bản dịch tiếng Việt")
    onscreen_text: str = Field(description="chữ lớn dải trên, từ khóa ngắn bằng ngôn ngữ của video")
    footage: TimeRange = Field(description="đoạn footage gốc chạy bên dưới hook (3–5 giây)")
    source: TimeRange = Field(description="đoạn footage chứng minh hook đúng sự thật (nguồn)")
    music_sfx_vi: str = Field(description="kiểu nhạc/hiệu ứng đi kèm")
    why_vi: str


class HookSet(BaseModel):
    video_index: int = Field(ge=1)
    options: list[HookOption] = Field(min_length=3, max_length=3)
    editor_notes: str


def check_hooks(hs: HookSet, duration: float, max_chars: int) -> list[str]:
    errors = []
    for i, o in enumerate(hs.options, 1):
        errors += check_ranges([o.footage, o.source], duration, f"hook {i}")
        span = o.footage.end - o.footage.start
        if not 2.0 <= span <= 6.0:
            errors.append(f"hook {i}: đoạn footage dài {span:.1f}s, cần khoảng 3–5 giây")
        if len(o.line) > max_chars:
            errors.append(f"hook {i}: câu hook dài {len(o.line)} ký tự, tối đa {max_chars} (phải đọc trong ~4 giây)")
    if len({o.hook_type for o in hs.options}) < 2:
        errors.append("3 phương án phải thuộc ít nhất 2 kiểu hook khác nhau")
    return errors


# ---------------- Kế hoạch dựng (mục 10) ----------------

Ratio = Literal["full", "4:3", "1:1"]


class PlanClip(BaseModel):
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)
    speed: float = Field(default=1.0, ge=0.25, le=2.0, description="<1 = quay chậm (replay), >1 = tua nhanh")
    replay: bool = Field(default=False, description="true = tua lại chậm một đoạn đã dùng (được phép lặp footage)")
    ratio: Ratio | None = Field(default=None, description="khung riêng cho clip; null = khung mặc định")
    purpose_vi: str = ""


class Emphasis(BaseModel):
    source_time: float = Field(ge=0, description="giây trong footage gốc lúc chữ xuất hiện")
    duration: float = Field(default=1.5, gt=0.3, le=4.0)
    text: str = Field(description="từ khóa ngắn bằng ngôn ngữ của video, đúng với lời thoại")
    position: Literal["top", "center"] = "center"


class Zoom(BaseModel):
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)
    kind: Literal["punch", "slow"]


class Sfx(BaseModel):
    source_time: float = Field(ge=0)
    kind: Literal["pop", "whoosh", "ding", "boom", "laugh", "swoosh", "record_scratch"]
    name: str | None = Field(default=None, description="tên SFX trong kho có sẵn (nếu có bài hợp), hoặc null")
    reason_vi: str = ""


class MusicChoice(BaseModel):
    name: str | None = Field(description="tên bài trong danh sách nhạc có sẵn, hoặc null nếu không hợp")
    mood_vi: str
    energy: Literal["low", "mid", "high"]


class EditPlan(BaseModel):
    video_index: int = Field(ge=1)
    title_top: str = Field(default="", description="tiêu đề cố định dải trên (ngôn ngữ video), có thể rỗng")
    default_ratio: Ratio
    clips: list[PlanClip] = Field(min_length=1)
    emphasis: list[Emphasis] = []
    zooms: list[Zoom] = []
    sfx: list[Sfx] = []
    music: MusicChoice
    editor_notes: str


def clips_duration(clips: list[PlanClip]) -> float:
    return sum((c.source_end - c.source_start) / c.speed for c in clips)


def check_plan(plan: EditPlan, duration: float, hook_s: float = 0.0, min_s: float = 60.0,
               max_s: float = 150.0) -> list[str]:
    errors = check_ranges([TimeRange(start=c.source_start, end=c.source_end) for c in plan.clips], duration, "clip")
    normal = [c for c in plan.clips if not c.replay]
    for a, b in zip(normal, normal[1:]):
        if b.source_start < a.source_end - 0.05 and b.source_end > a.source_start:
            errors.append(f"clip {a.source_start}-{a.source_end} và {b.source_start}-{b.source_end} chồng nhau")
    total = clips_duration(plan.clips) + hook_s
    usable = duration + hook_s
    if total > max_s:
        errors.append(f"tổng thời lượng {total:.1f}s (kể cả hook {hook_s:.1f}s) vượt {max_s:.0f}s — cắt gọn thêm")
    if total < min_s and usable >= min_s + 10:
        errors.append(f"tổng thời lượng {total:.1f}s ngắn hơn {min_s:.0f}s trong khi footage đủ dài")

    for c in plan.clips:
        if c.replay and c.speed >= 1.0:
            errors.append(f"clip replay {c.source_start}-{c.source_end} phải quay chậm (speed < 1)")
        if not c.replay and c.speed < 1.0:
            errors.append(f"clip {c.source_start}-{c.source_end}: chỉ clip replay mới được quay chậm")

    def inside(t: float) -> bool:
        return any(c.source_start - 0.05 <= t <= c.source_end + 0.05 for c in plan.clips)

    for e in plan.emphasis:
        if not inside(e.source_time):
            errors.append(f"chữ nhấn '{e.text}' ở {e.source_time}s không nằm trong clip nào được giữ")
    for z in plan.zooms:
        if not inside(z.source_start):
            errors.append(f"zoom ở {z.source_start}s không nằm trong clip nào được giữ")
    for s in plan.sfx:
        if not inside(s.source_time):
            errors.append(f"SFX ở {s.source_time}s không nằm trong clip nào được giữ")
    return errors


# ---------------- Caption / hashtag (mục 3.10) ----------------

class Captions(BaseModel):
    video_index: int = Field(ge=1)
    caption: str = Field(description="caption TikTok bằng ngôn ngữ của video, 1–3 câu, không bịa")
    caption_vi: str = Field(description="bản dịch tiếng Việt")
    hashtags: list[str] = Field(min_length=3, max_length=8, description="hashtag bằng ngôn ngữ video, có dấu #")
    hashtags_vi: list[str] = Field(description="nghĩa tiếng Việt của từng hashtag, cùng thứ tự")
    editor_notes: str


def check_captions(c: Captions) -> list[str]:
    errors = []
    if len(c.caption) > 300:
        errors.append(f"caption dài {len(c.caption)} ký tự, nên dưới 300")
    for h in c.hashtags:
        if not h.startswith("#") or " " in h or len(h) < 2:
            errors.append(f"hashtag '{h}' phải bắt đầu bằng # và không có dấu cách")
    if len(c.hashtags_vi) != len(c.hashtags):
        errors.append("hashtags_vi phải có cùng số phần tử với hashtags")
    return errors
