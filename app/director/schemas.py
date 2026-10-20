"""Khuôn (pydantic) cho kết quả của đạo diễn. Sai khuôn thì gọi lại kèm thông báo lỗi."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr

Language = Literal["ko", "ja", "en", "de", "zh"]  # zh: chỉ làm tiếng GỐC ở chế độ Đổi ngôn ngữ; de: thêm 18/10


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


PolicyCategory = Literal[
    "violence", "dangerous_acts", "self_harm", "sexual", "minor_safety", "hate", "harassment", "profanity",
    "illegal", "drugs_alcohol_tobacco", "gambling", "weapons", "misinformation", "privacy", "other_platform", "other"]
POLICY_VI = {
    "violence": "bạo lực / máu me", "dangerous_acts": "hành vi nguy hiểm, dễ bị bắt chước",
    "self_harm": "tự hại / tự tử", "sexual": "khiêu dâm / gợi dục", "minor_safety": "an toàn trẻ vị thành niên",
    "hate": "phát ngôn thù ghét, kỳ thị", "harassment": "quấy rối, lăng mạ, bắt nạt", "profanity": "chửi thề / từ tục",
    "illegal": "hoạt động phạm pháp", "drugs_alcohol_tobacco": "ma túy / rượu bia / thuốc lá",
    "gambling": "cờ bạc", "weapons": "vũ khí", "misinformation": "thông tin sai lệch gây hại",
    "privacy": "lộ thông tin cá nhân (số điện thoại, địa chỉ, biển số...)",
    "other_platform": "nhắc tới nền tảng khác ngoài TikTok (YouTube, Instagram...)", "other": "khác",
}


class PolicyIssue(TimeRange):
    """Đoạn footage vi phạm Nguyên tắc cộng đồng TikTok → bị cắt khỏi mọi video (không dùng cả trong hook)."""

    category: PolicyCategory
    reason_vi: str = Field(description="vi phạm gì, ngắn gọn (tiếng Việt)")
    auto: bool = Field(default=False, description="true = máy tự dò (từ tục trong transcript), không phải đạo diễn")


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
    mirror_ok: bool = Field(default=True, description="false nếu hình có nhiều chữ / logo / bảng hiệu / nhãn sản phẩm "
                                                      "(phản chiếu sẽ thành chữ ngược)")
    sensitive_notes_vi: list[str] = Field(
        default_factory=list, description="điều KHÔNG được viết/ám chỉ trên màn hình hay trong hook")
    policy_issues: list[PolicyIssue] = Field(
        default_factory=list, description="đoạn vi phạm Nguyên tắc cộng đồng TikTok — sẽ bị CẮT BỎ (mốc giây gốc)")
    editor_notes: str = Field(description="giải thích ngắn các nhận định chính (tiếng Việt)")
    # Chế độ Đổi ngôn ngữ: tool đổi `language` thành ngôn ngữ ĐÍCH (để hook/chữ/caption viết bằng tiếng đó)
    # và giữ tiếng gốc của footage ở đây. Không phải trường của đạo diễn.
    _source_language: str = PrivateAttr(default="")

    @property
    def source_language(self) -> str:
        return self._source_language or self.language

    def dubbed_to(self, target: str) -> "Understanding":
        u = self.model_copy(update={"language": target})
        u._source_language = self.source_language
        return u


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


# ---------------- Chia video dài (mục 4) ----------------

class Situation(TimeRange):
    note_vi: str = Field(default="", description="tình huống gì (tiếng Việt, ngắn): cãi nhau, cú hài, pha bất ngờ...")


class SegmentVideo(TimeRange):
    title_vi: str = Field(description="tên ngắn của video (tiếng Việt) để người dùng nhận ra")
    summary_vi: str = Field(description="tóm tắt nội dung video: mở – diễn biến – kết (tiếng Việt)")
    why_vi: str = Field(description="vì sao đoạn này đứng được một mình và đáng thành video")
    moments: list[Situation] = Field(default_factory=list, description=(
        "chế độ lồng tiếng nhân vật: các TÌNH HUỐNG ngắn ghép thành video này (giây gốc, theo thứ tự)"))


class DroppedPart(TimeRange):
    reason_vi: str = Field(description="vì sao bỏ (nhạt, trùng, quá ngắn không ghép được...)")


class SegmentPlan(BaseModel):
    videos: list[SegmentVideo] = Field(min_length=1)
    dropped: list[DroppedPart] = Field(default_factory=list)
    editor_notes: str


def check_segments(sp: SegmentPlan, duration: float, usable: TimeRange, min_raw: float, max_raw: float) -> list[str]:
    """Mỗi video là một đoạn footage liền, không chồng nhau, độ dài hợp lý; mốc nằm trong footage."""
    errors = check_ranges(sp.videos, duration, "video") + check_ranges(sp.dropped, duration, "đoạn bỏ")
    vids = sorted(sp.videos, key=lambda v: v.start)
    for a, b in zip(vids, vids[1:]):
        if b.start < a.end - 0.5:
            errors.append(f"video {a.start:.1f}–{a.end:.1f}s và {b.start:.1f}–{b.end:.1f}s chồng nhau")
    whole_short = usable.end - usable.start < min_raw
    for v in sp.videos:
        span = v.end - v.start
        if span < min_raw and not whole_short:
            errors.append(f"video {v.start:.1f}–{v.end:.1f}s chỉ {span:.0f}s footage, cần ≥ {min_raw:.0f}s "
                          "(ghép với đoạn liền kề cùng chủ đề hoặc bỏ và ghi lý do)")
        if span > max_raw:
            errors.append(f"video {v.start:.1f}–{v.end:.1f}s dài {span:.0f}s footage, tối đa {max_raw:.0f}s "
                          "(tách thành hai video độc lập)")
    return errors


def check_moments(sp: SegmentPlan, situation_s: tuple[float, float], min_s: float, max_s: float,
                  whole_short: bool = False) -> list[str]:
    """Lồng tiếng nhân vật (chủ dự án yêu cầu 11/10): mỗi video ghép từ vài TÌNH HUỐNG ngắn (~10–20 giây), theo thứ tự,
    không chồng nhau, nằm trong đoạn của video; tổng thời lượng trong giới hạn video."""
    lo, hi = situation_s
    errors = []
    for v in sp.videos:
        name = f"video {v.start:.1f}–{v.end:.1f}s"
        if not v.moments:
            errors.append(f"{name}: thiếu `moments` — liệt kê các tình huống {lo:.0f}–{hi:.0f} giây ghép thành video")
            continue
        for m in v.moments:
            span = m.end - m.start
            if span < lo * 0.7 or span > hi * 1.5:
                errors.append(f"{name}: tình huống {m.start:.1f}–{m.end:.1f}s dài {span:.0f}s — mỗi tình huống "
                              f"{lo:.0f}–{hi:.0f} giây (dài thì tách, ngắn thì nối với câu liền kề)")
            if m.start < v.start - 0.5 or m.end > v.end + 0.5:
                errors.append(f"{name}: tình huống {m.start:.1f}–{m.end:.1f}s nằm ngoài video "
                              "(start/end của video = đầu tình huống đầu / cuối tình huống cuối)")
        ms = sorted(v.moments, key=lambda m: m.start)
        if ms != list(v.moments):
            errors.append(f"{name}: các tình huống phải theo đúng thứ tự thời gian")
        for a, b in zip(ms, ms[1:]):
            if b.start < a.end - 0.2:
                errors.append(f"{name}: tình huống {a.start:.1f}–{a.end:.1f}s và {b.start:.1f}–{b.end:.1f}s chồng nhau")
        total = sum(m.end - m.start for m in v.moments)
        if total > max_s + 1 or (total < min_s - 1 and not whole_short):
            errors.append(f"{name}: tổng các tình huống {total:.0f}s — cần {min_s:.0f}–{max_s:.0f} giây "
                          "(thêm / bớt tình huống)")
    return errors


# ---------------- Review bỏ lửng (chủ dự án yêu cầu 14/10) ----------------

class CliffHook(TimeRange):
    why_vi: str = Field(description="vì sao đoạn này kịch tính, giữ người xem (tiếng Việt, ngắn)")


class CliffPart(TimeRange):
    title_vi: str = Field(description="tên ngắn của phần (tiếng Việt) để người dùng nhận ra")
    summary_vi: str = Field(description="phần này kể chuyện gì: mở – diễn biến – chỗ dừng (tiếng Việt)")
    hook: CliffHook = Field(description="đoạn SHORT 5–15 giây kịch tính nhất NẰM TRONG phần này, đặt lên đầu video, giữ "
                                        "nguyên hình + tiếng gốc")
    cliff_vi: str = Field(description="phần dừng BỎ LỬNG ở chỗ nào, người xem đang thắc mắc gì (phần cuối: phim kết ra sao)")


class HookSubLine(BaseModel):
    i: int = Field(ge=1, description="số thứ tự câu thoại gốc trong short")
    text: str = Field(description="câu phụ đề bằng NGÔN NGỮ ĐÍCH, gọn, tự nhiên như phụ đề phim bản xứ")
    text_vi: str = Field(default="", description="nghĩa tiếng Việt")


class HookSubs(BaseModel):
    lines: list[HookSubLine] = Field(default_factory=list)


class CliffPlan(BaseModel):
    narrator_vi: str = Field(description="tên nhân vật chính (người kể nếu review ở ngôi thứ nhất), đúng tên trong phim")
    parts: list[CliffPart] = Field(min_length=1)
    editor_notes: str


# ---------------- Content nhiều phim từ bài TikTok ảnh (chủ dự án yêu cầu 14/10) ----------------

class FilmRef(BaseModel):
    key: str = Field(description="mã phim: phim1, phim2… theo thứ tự xuất hiện trong video")
    title: str = Field(description="tên phim CHÍNH THỨC ở thị trường của ngôn ngữ video (hiện trên màn hình)")
    title_vi: str = Field(description="tên phim tiếng Việt / tên gốc để chủ dự án tìm đúng file phim")
    year: str = Field(default="", description="năm phát hành nếu biết chắc, không thì để trống")
    characters: list[str] = Field(default_factory=list, description="nhân vật được nhắc trong video (tên tiếng Việt / gốc)")


class FilmLine(BaseModel):
    film: str = Field(description="mã phim (key) mà câu này nói tới — hình của câu lấy từ phim đó")
    shot: Literal["video", "freeze"] = Field(description="video = cảnh phim chạy; freeze = video chạy rồi DỪNG HÌNH ở "
                                                          "khoảnh khắc đắt (tên nhân vật hiện lên)")
    text: str = Field(description="câu đọc bằng NGÔN NGỮ VIDEO, văn nói tự nhiên của người bản xứ")
    text_vi: str = Field(description="nghĩa tiếng Việt")
    want_vi: str = Field(description="cảnh cần tìm trong phim (tiếng Việt, cụ thể: ai, làm gì, khoảnh khắc nào)")
    label: str = Field(default="", description="(freeze) chữ hiện khi dừng hình: tên nhân vật, ngôn ngữ video, ngắn")


class FilmsIdea(BaseModel):
    topic_vi: str = Field(description="bài gốc nói về gì (tiếng Việt, 1–2 câu)")
    films: list[FilmRef] = Field(min_length=1)
    story_vi: str = Field(description="dàn ý content MỚI bằng tiếng Việt: mở – từng phim / nhân vật – kết")
    lines: list[FilmLine] = Field(min_length=3)
    titles_top: list[str] = Field(min_length=1, max_length=2, description="2 dòng tiêu đề trên (ngôn ngữ video)")
    music: MusicChoice
    caption: str = Field(description="caption TikTok bằng ngôn ngữ video, 1–3 câu")
    caption_vi: str
    hashtags: list[str] = Field(min_length=3, max_length=8)
    hashtags_vi: list[str]
    editor_notes: str


class FilmPick(BaseModel):
    line: int = Field(ge=1, description="số câu (theo danh sách được giao)")
    start: float = Field(ge=0, description="giây bắt đầu đoạn phim cho câu này")
    end: float = Field(gt=0, description="giây kết thúc")
    freeze_t: float | None = Field(default=None, description="(câu dừng hình) giây đứng hình — khoảnh khắc đắt, nằm "
                                                              "trong start–end, thấy rõ nhân vật")
    why_vi: str = Field(default="", description="khung hình nào cho thấy cảnh này (tên file) — ngắn")


class FilmMatch(BaseModel):
    picks: list[FilmPick] = Field(min_length=1)
    editor_notes: str


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
    intro: str = Field(default="", description="1–2 câu ĐỜI THƯỜNG dẫn vào trước câu hook (ngôn ngữ của video), "
                                               "nói như kể chuyện với bạn bè")
    intro_vi: str = Field(default="", description="bản dịch tiếng Việt của intro")
    intro_footage: TimeRange | None = Field(default=None, description="footage chạy dưới phần intro (3–6 giây), "
                                                                      "cảnh bối cảnh / đời thường")
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


def _sentences(text: str) -> int:
    import re

    return len([s for s in re.split(r"[.!?。！？…]+", text) if s.strip()])


def check_hooks(hs: HookSet, duration: float, max_chars: int, intro_max_chars: int | None = None) -> list[str]:
    """intro_max_chars: bật yêu cầu 1–2 câu đời thường trước câu hook (chủ dự án chốt 01/10)."""
    errors = []
    for i, o in enumerate(hs.options, 1):
        errors += check_ranges([o.footage, o.source], duration, f"hook {i}")
        if intro_max_chars:
            if not o.intro.strip() or o.intro_footage is None:
                errors.append(f"hook {i}: thiếu `intro` (1–2 câu đời thường trước câu hook) hoặc `intro_footage`")
            else:
                errors += check_ranges([o.intro_footage], duration, f"hook {i} intro")
                ispan = o.intro_footage.end - o.intro_footage.start
                if not 2.0 <= ispan <= 8.0:
                    errors.append(f"hook {i}: intro_footage dài {ispan:.1f}s, cần khoảng 3–6 giây")
                if len(o.intro) > intro_max_chars:
                    errors.append(f"hook {i}: intro dài {len(o.intro)} ký tự, tối đa {intro_max_chars} (1–2 câu ngắn)")
                if _sentences(o.intro) > 2:
                    errors.append(f"hook {i}: intro chỉ 1–2 câu")
        span = o.footage.end - o.footage.start
        if not 2.0 <= span <= 6.0:
            errors.append(f"hook {i}: đoạn footage dài {span:.1f}s, cần khoảng 3–5 giây")
        if len(o.line) > max_chars:
            errors.append(f"hook {i}: câu hook dài {len(o.line)} ký tự, tối đa {max_chars} (phải đọc trong ~4 giây)")
    if len({o.hook_type for o in hs.options}) < 2:
        errors.append("3 phương án phải thuộc ít nhất 2 kiểu hook khác nhau")
    return errors


# ---------------- Kế hoạch dựng (mục 10) ----------------

Ratio = Literal["full", "16:9", "4:3", "1:1"]


class PlanClip(BaseModel):
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)
    speed: float = Field(default=1.0, ge=0.25, le=2.0, description="<1 = quay chậm (replay), >1 = tua nhanh")
    replay: bool = Field(default=False, description="true = tua lại chậm một đoạn đã dùng (được phép lặp footage)")
    repeat: bool = Field(default=False, description="true = lặp lại đoạn đã/sẽ dùng ở tốc độ thường (cold open mở đầu, "
                                                    "nhắc lại câu chốt) — được phép trùng footage")
    ratio: Ratio | None = Field(default=None, description="khung riêng cho clip; null = khung mặc định")
    highlight: bool = Field(default=False, description="true = cảnh GAY CẤN / đắt giá (kiểu chuyển cảnh liên tục: "
                                                       "code xếp các cảnh này lên đầu video)")
    mirror: bool | None = Field(default=None, description="(tool đặt) phản chiếu ngang clip này; null = theo kiểu dựng")
    lib: str = Field(default="", description="(tool đặt) mã cảnh kho chung — clip lấy từ file trong kho, giây tính trong "
                                             "file đó; rỗng = video gốc")
    keep_audio: bool = Field(default=False, description="(tool đặt) đoạn giữ TIẾNG GỐC (bán content nửa thuyết minh)")
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
    kind: Literal["pop", "whoosh", "ding", "boom", "laugh", "swoosh", "record_scratch", "click"]
    name: str | None = Field(default=None, description="tên SFX trong kho có sẵn (nếu có bài hợp), hoặc null")
    reason_vi: str = ""


class EffectUse(BaseModel):
    source_time: float = Field(ge=0)
    duration: float = Field(default=0.8, gt=0.2, le=4.0)
    name: str = Field(description="tên hiệu ứng hình trong kho")


class StickerUse(BaseModel):
    source_time: float = Field(ge=0)
    duration: float = Field(default=1.5, gt=0.3, le=5.0)
    name: str = Field(description="tên sticker trong kho")
    position: Literal["top_left", "top_right", "center", "bottom_left", "bottom_right"] = "top_right"


class TransitionUse(BaseModel):
    after_clip: int = Field(ge=0, description="chỉ số clip (từ 0) mà chuyển cảnh nằm ở cuối")
    name: str = Field(description="tên chuyển cảnh trong kho")


ArrowDir = Literal["right", "left", "up", "down", "up_right", "up_left", "down_right", "down_left"]


class Arrow(BaseModel):
    source_time: float = Field(ge=0, description="giây trong footage gốc lúc mũi tên hiện")
    duration: float = Field(default=1.2, ge=0.4, le=3.0)
    x: float = Field(ge=0, le=1, description="vị trí điểm cần chỉ trong KHUNG HÌNH GỐC, 0 = trái, 1 = phải")
    y: float = Field(ge=0, le=1, description="0 = trên, 1 = dưới")
    points: ArrowDir = Field(description="hướng mũi tên chỉ tới (mũi tên nằm phía ngược lại của điểm)")
    reason_vi: str = ""


class MusicChoice(BaseModel):
    name: str | None = Field(description="tên bài trong danh sách nhạc có sẵn, hoặc null nếu không hợp")
    mood_vi: str
    energy: Literal["low", "mid", "high"]


class EditPlan(BaseModel):
    video_index: int = Field(ge=1)
    title_top: str = Field(default="", description="tiêu đề cố định dải trên (ngôn ngữ video), có thể rỗng")
    titles_top: list[str] = Field(default_factory=list, max_length=2,
                                  description="2 dòng tiêu đề lớn phía trên khối video, cố định suốt video")
    titles_bottom: list[str] = Field(default_factory=list, max_length=2,
                                     description="2 dòng tiêu đề lớn phía dưới khối video, cố định suốt video")
    topic_label: str = Field(default="", description="nhãn chủ đề nhỏ góc trên phải khối video, có thể rỗng")
    default_ratio: Ratio
    clips: list[PlanClip] = Field(min_length=1)
    emphasis: list[Emphasis] = []
    zooms: list[Zoom] = []
    sfx: list[Sfx] = []
    effects: list[EffectUse] = []
    stickers: list[StickerUse] = []
    transitions: list[TransitionUse] = []
    arrows: list[Arrow] = Field(default_factory=list, description="mũi tên chỉ chi tiết (kiểu thể thao)")
    filter: str | None = Field(default=None, description="tên filter màu cho cả video, hoặc null")
    music: MusicChoice
    editor_notes: str


def clips_duration(clips: list[PlanClip]) -> float:
    return sum((c.source_end - c.source_start) / c.speed for c in clips)


def repair_plan(plan: EditPlan, duration: float, max_fix_overlap: float = 1.0) -> tuple[EditPlan, list[str]]:
    """Sửa các lỗi vặt mà không cần hỏi lại đạo diễn. Lỗi thật (chồng nhau nhiều, sai thời lượng) vẫn để kiểm tra bắt."""
    fixes: list[str] = []
    clips = [c.model_copy() for c in plan.clips]
    for c in clips:
        if c.source_end > duration:
            fixes.append(f"clip {c.source_start}-{c.source_end}: cắt đuôi về hết footage ({duration:.1f}s)")
            c.source_end = round(duration, 2)
        if c.replay and c.speed >= 1.0:
            fixes.append(f"clip replay {c.source_start}-{c.source_end}: đặt tốc độ 0.5 (quay chậm)")
            c.speed = 0.5
        if not c.replay and c.speed < 1.0:
            fixes.append(f"clip {c.source_start}-{c.source_end}: không phải replay → tốc độ 1.0")
            c.speed = 1.0
    for i, c in enumerate(clips):  # clip nằm gọn trong clip khác = cold open / nhắc lại → đánh dấu repeat
        if c.replay or c.repeat:
            continue
        if any(j != i and not o.replay and not o.repeat and o.source_start - 0.05 <= c.source_start
               and c.source_end <= o.source_end + 0.05 and (o.source_end - o.source_start) > (c.source_end - c.source_start)
               for j, o in enumerate(clips)):
            fixes.append(f"clip {c.source_start}-{c.source_end} lặp lại đoạn có trong clip khác → đánh dấu repeat "
                         "(mở đầu / nhắc lại)")
            c.repeat = True
    normal = sorted((c for c in clips if not c.replay and not c.repeat), key=lambda c: c.source_start)
    for a, b in zip(normal, normal[1:]):  # chồng nhau chút ít: cắt đầu clip sau cho khớp
        ov = a.source_end - b.source_start
        if 0.05 < ov <= max_fix_overlap and b.source_end - a.source_end >= 0.5:
            fixes.append(f"clip {b.source_start}-{b.source_end} chồng {ov:.2f}s lên clip trước → bắt đầu từ {a.source_end}")
            b.source_start = a.source_end
    clips = [c for c in clips if c.source_end - c.source_start >= 0.2]

    def inside(t: float) -> bool:
        return any(c.source_start - 0.05 <= t <= c.source_end + 0.05 for c in clips)

    upd: dict = {"clips": clips}
    for field, attr, label in (("emphasis", "source_time", "chữ nhấn"), ("zooms", "source_start", "zoom"),
                               ("sfx", "source_time", "SFX"), ("effects", "source_time", "hiệu ứng"),
                               ("stickers", "source_time", "sticker"), ("arrows", "source_time", "mũi tên")):
        items = getattr(plan, field)
        kept = [x for x in items if inside(getattr(x, attr))]
        if len(kept) < len(items):
            fixes.append(f"bỏ {len(items) - len(kept)} {label} nằm ngoài các clip được giữ")
        upd[field] = kept
    trans = [t for t in plan.transitions if t.after_clip < len(clips) - 1]
    if len(trans) < len(plan.transitions):
        fixes.append(f"bỏ {len(plan.transitions) - len(trans)} chuyển cảnh đặt sau clip cuối")
    upd["transitions"] = trans
    return plan.model_copy(update=upd), fixes


def check_reorder(plan: EditPlan, min_share: float = 0.25, max_clip_s: float | None = None) -> list[str]:
    """Kiểu giải trí "đảo lung tung": đủ nhiều lần nhảy ngược thời gian, clip ngắn."""
    errors = []
    normal = [c for c in plan.clips if not c.replay and not c.repeat]
    cuts = max(1, len(normal) - 1)
    backs = sum(1 for a, b in zip(normal, normal[1:]) if b.source_start < a.source_start)
    need = max(2, round(min_share * cuts))
    if len(normal) >= 4 and backs < need:
        errors.append(f"cần ĐẢO THỨ TỰ nhiều hơn: mới có {backs} lần nhảy ngược thời gian, cần ≥ {need} "
                      "(mở bằng khoảnh khắc đắt nhất, xen kẽ trước–sau, lặp lại câu chốt bằng replay)")
    if max_clip_s:
        for c in normal:
            if (c.source_end - c.source_start) / c.speed > max_clip_s + 0.5:
                errors.append(f"clip {c.source_start}-{c.source_end} dài quá {max_clip_s:.0f}s — chia nhỏ, xen cảnh khác vào")
    return errors


def reorder_hype(plan: EditPlan) -> tuple[EditPlan, list[str]]:
    """Kiểu "chuyển cảnh liên tục" (chủ dự án yêu cầu 07/10): cảnh gay cấn (highlight) lên ĐẦU theo thứ tự AI chọn,
    cảnh còn lại xếp SAU theo thời gian. Chuyển cảnh (after_clip) được dời theo."""
    idx = list(range(len(plan.clips)))
    hi = [i for i in idx if plan.clips[i].highlight and not plan.clips[i].replay]
    rest = sorted((i for i in idx if i not in hi), key=lambda i: (plan.clips[i].source_start, i))
    order = hi + rest
    if order == idx:
        return plan, []
    new_pos = {old: new for new, old in enumerate(order)}
    trans = [t.model_copy(update={"after_clip": new_pos[t.after_clip]}) for t in plan.transitions
             if t.after_clip in new_pos]
    return (plan.model_copy(update={"clips": [plan.clips[i] for i in order], "transitions": trans}),
            [f"xếp {len(hi)} cảnh gay cấn lên đầu, {len(rest)} cảnh còn lại về sau"])


def check_hype(plan: EditPlan, min_clip_s: float = 2.0, max_clip_s: float = 5.5) -> list[str]:
    """Chuyển cảnh liên tục: clip ngắn (≈3–5s), có cảnh gay cấn được đánh dấu."""
    errors = []
    normal = [c for c in plan.clips if not c.replay and not c.repeat]
    for c in normal:
        d = (c.source_end - c.source_start) / c.speed
        if d > max_clip_s + 0.3:
            errors.append(f"clip {c.source_start}-{c.source_end} dài {d:.1f}s — chia nhỏ (mỗi cảnh ≤ {max_clip_s:.0f}s)")
        elif d < min_clip_s - 0.2:
            errors.append(f"clip {c.source_start}-{c.source_end} chỉ {d:.1f}s — quá ngắn (≥ {min_clip_s:.0f}s)")
    if len(normal) >= 6 and sum(c.highlight for c in normal) < 2:
        errors.append("đánh dấu ít nhất 2 cảnh gay cấn nhất bằng \"highlight\": true (code xếp chúng lên đầu)")
    return errors


def repair_montage(plan: EditPlan, parts: list[dict]) -> tuple[EditPlan, list[str]]:
    """Nhiều video ghép: clip vắt qua ranh giới 2 video → thu về video chứa phần lớn clip."""
    fixes, clips = [], []
    for c in plan.clips:
        best = max(parts, key=lambda p: min(c.source_end, p["end"]) - max(c.source_start, p["start"]))
        a, b = max(c.source_start, best["start"]), min(c.source_end, best["end"] - 0.05)
        if (a, b) != (c.source_start, c.source_end):
            if b - a < 0.5:
                fixes.append(f"bỏ clip {c.source_start}-{c.source_end} (nằm giữa 2 video)")
                continue
            fixes.append(f"clip {c.source_start}-{c.source_end} vắt qua 2 video → thu về video {best['index']}")
            c = c.model_copy(update={"source_start": round(a, 2), "source_end": round(b, 2)})
        clips.append(c)
    return (plan.model_copy(update={"clips": clips}) if clips else plan), fixes


def check_montage(plan: EditPlan, parts: list[dict], min_share: float = 0.8) -> list[str]:
    """Nhiều video ghép: phần lớn video đều góp cảnh (mỗi video lấy một chút)."""
    import math

    used = set()
    for c in plan.clips:
        for p in parts:
            if min(c.source_end, p["end"]) - max(c.source_start, p["start"]) > 0.3:
                used.add(p["index"])
    need = min(len(parts), max(2, math.ceil(min_share * len(parts))))
    if len(used) < need:
        miss = [str(p["index"]) for p in parts if p["index"] not in used]
        return [f"mới lấy cảnh từ {len(used)}/{len(parts)} video — cần ít nhất {need}; thêm cảnh hay từ video "
                + ", ".join(miss[:8])]
    return []


def check_remix(plan: EditPlan, have_filters: bool, keep_order: bool = True) -> list[str]:
    """Bản dựng lại (Đổi ngôn ngữ): giữ thứ tự thời gian, có filter màu, có điểm nhấn zoom."""
    errors = []
    normal = [c for c in plan.clips if not c.replay and not c.repeat]
    if keep_order and any(b.source_start < a.source_start for a, b in zip(normal, normal[1:])):
        errors.append("bản dựng lại phải giữ đúng thứ tự thời gian của các clip (không đảo cảnh)")
    if have_filters and not plan.filter:
        errors.append("bản dựng lại phải chọn một filter màu cho cả video (để khác bản gốc)")
    if len(normal) >= 4 and not plan.zooms:
        errors.append("bản dựng lại cần vài zoom ở điểm nhấn (zooms đang rỗng)")
    return errors


def check_titles(plan: EditPlan, max_chars: int, bottom: bool = True) -> list[str]:
    """Bố cục dòng tiêu đề: đủ 2 dòng trên (+ 2 dòng dưới nếu bottom), mỗi dòng ngắn để chữ to."""
    errors = []
    if len([t for t in plan.titles_top if t.strip()]) != 2:
        errors.append("titles_top phải có đúng 2 dòng không rỗng")
    if bottom and len([t for t in plan.titles_bottom if t.strip()]) != 2:
        errors.append("bố cục 4 dòng: titles_bottom phải có đúng 2 dòng không rỗng")
    for t in plan.titles_top + (plan.titles_bottom if bottom else []):
        if len(t) > max_chars:
            errors.append(f"dòng tiêu đề '{t}' dài {len(t)} ký tự, tối đa {max_chars}")
        if "\n" in t:
            errors.append(f"dòng tiêu đề '{t}' không được xuống dòng")
    return errors


def check_plan(plan: EditPlan, duration: float, hook_s: float = 0.0, min_s: float = 60.0,
               max_s: float = 150.0, available: float | None = None) -> list[str]:
    """available: số giây footage dành cho video này (mặc định = duration); dùng cho luật tối thiểu 60s."""
    errors = check_ranges([TimeRange(start=c.source_start, end=c.source_end) for c in plan.clips], duration, "clip")
    normal = [c for c in plan.clips if not c.replay and not c.repeat]
    for i, a in enumerate(normal):  # mọi cặp (kể cả khi đảo thứ tự), trừ clip replay được phép lặp
        for b in normal[i + 1:]:
            if b.source_start < a.source_end - 0.05 and b.source_end > a.source_start + 0.05:
                errors.append(f"clip {a.source_start}-{a.source_end} và {b.source_start}-{b.source_end} chồng nhau")
    total = clips_duration(plan.clips) + hook_s
    usable = (duration if available is None else available) + hook_s
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
    for e in plan.effects:
        if not inside(e.source_time):
            errors.append(f"hiệu ứng '{e.name}' ở {e.source_time}s không nằm trong clip nào được giữ")
    for st in plan.stickers:
        if not inside(st.source_time):
            errors.append(f"sticker '{st.name}' ở {st.source_time}s không nằm trong clip nào được giữ")
    for a in plan.arrows:
        if not inside(a.source_time):
            errors.append(f"mũi tên ở {a.source_time}s không nằm trong clip nào được giữ")
    for t in plan.transitions:
        if t.after_clip >= len(plan.clips) - 1:
            errors.append(f"chuyển cảnh after_clip={t.after_clip} phải nhỏ hơn số clip - 1 ({len(plan.clips) - 1})")
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


# ---------------- Thuyết minh (chế độ Đổi ngôn ngữ) ----------------

class Shot(BaseModel):
    start: float = Field(ge=0, description="giây GỐC bắt đầu cảnh")
    end: float = Field(gt=0, description="giây GỐC kết thúc cảnh")
    lib: str = Field(default="", description="mã cảnh trong KHO CẢNH CHUNG (L1, L2…) khi lấy cảnh từ kho; khi đó start / "
                                             "end tính TRONG cảnh kho (0 → độ dài cảnh). Rỗng = cảnh trong video gốc")


class DubLine(BaseModel):
    kind: Literal["dub", "narration"] = Field(
        default="dub", description="dub = dịch lời thoại gốc; narration = lời dẫn viết thêm cho chỗ KHÔNG có giọng nói")
    source_start: float = Field(ge=0, description="giây GỐC bắt đầu đoạn thoại được thuyết minh (nằm trong clip được giữ)")
    source_end: float = Field(gt=0, description="giây GỐC kết thúc")
    text: str = Field(description="câu thuyết minh bằng NGÔN NGỮ ĐÍCH, văn nói tự nhiên của người bản xứ")
    text_vi: str = Field(description="nghĩa tiếng Việt")
    action_vi: str = Field(default="", description="với lời dẫn: cảnh / hành động đáng nói đang diễn ra (tiếng Việt)")
    adapt_vi: str = Field(default="", description="nếu câu được BẢN ĐỊA HÓA (đổi ví dụ, đơn vị, cách đùa…): đổi gì, vì sao")
    speaker: str = Field(default="", description="(lồng tiếng nhân vật) TÊN nhân vật nói câu này — viết thống nhất")
    role: str = Field(default="", description="(bán content) hook / body / cta")
    keyword: str = Field(default="", description="(bán content) chữ nhấn của câu")
    shots: list["Shot"] = Field(default_factory=list, description="(bán content) các cảnh chạy dưới câu, theo thứ tự hiện")


class ShortLine(BaseModel):
    no: int = Field(ge=1, description="số thứ tự câu trong kịch bản")
    text: str = Field(description="câu viết lại NGẮN HƠN, ngôn ngữ đích")
    text_vi: str = Field(description="nghĩa tiếng Việt")


class DubShorten(BaseModel):
    lines: list[ShortLine] = Field(min_length=1)


class CastVoice(BaseModel):
    speaker: str = Field(description="tên nhân vật, đúng như trong `speaker` của các câu")
    instruct: str = Field(description="mô tả giọng cho OmniVoice bằng thuộc tính tiếng Anh, cách nhau dấu phẩy: "
                                      "male/female, child/teenager/young adult/middle-aged/elderly, "
                                      "very low pitch/low pitch/moderate pitch/high pitch/very high pitch, whisper")
    note_vi: str = Field(default="", description="tính cách / chất giọng nhân vật (tiếng Việt, ngắn)")


class DubScript(BaseModel):
    video_index: int = Field(ge=1)
    lines: list[DubLine] = Field(min_length=1)
    editor_notes: str
    story_vi: str = Field(default="", description="(review phim) dàn ý CÂU CHUYỆN bằng tiếng Việt: mở đầu – mâu thuẫn – "
                                                  "cao trào – kết, viết TRƯỚC rồi mới viết lời")
    cast: list[CastVoice] = Field(default_factory=list, description="(lồng tiếng nhân vật) giọng đề xuất cho mỗi nhân vật")


# ---------------- Bán content (chủ dự án yêu cầu 15/10) ----------------

class SellLine(BaseModel):
    role: Literal["hook", "body", "cta"] = Field(description="hook = câu mở đầu thu hút; body = nội dung; cta = kêu gọi "
                                                             "hành động (chỉ ở cuối, khi cần)")
    text: str = Field(description="câu đọc bằng NGÔN NGỮ ĐÍCH, văn nói tự nhiên của người bản xứ")
    text_vi: str = Field(description="nghĩa tiếng Việt")
    shots: list[Shot] = Field(min_length=1, description="1–3 cảnh (giây gốc) chạy dưới câu này, theo thứ tự hiện trên "
                                                        "màn hình — được lấy cảnh ở BẤT KỲ đâu trong video gốc")
    shots_vi: str = Field(default="", description="các cảnh đó có gì (tiếng Việt, ngắn) — để chủ dự án đối chiếu")
    keyword: str = Field(default="", description="CHỮ NHẤN: 1 từ / cụm ngắn đắt nhất của câu (ngôn ngữ đích, có trong câu), "
                                                 "hiện chữ to giữa màn khi đọc câu; rỗng nếu câu không cần nhấn")


class OnscreenLine(BaseModel):
    t: float = Field(ge=0, description="giây gốc lúc dòng chữ xuất hiện")
    text: str = Field(description="dòng phụ đề / chữ in trên hình, chép đúng chữ gốc")


class OrigInsert(BaseModel):
    after_line: int = Field(ge=0, description="đặt đoạn này NGAY SAU câu số mấy (0 = trước câu 1, mở video bằng tiếng gốc)")
    start: float = Field(ge=0, description="giây GỐC bắt đầu — GIỮ NGUYÊN hình + tiếng gốc")
    end: float = Field(gt=0, description="giây GỐC kết thúc (không cắt giữa câu nói)")
    text: str = Field(default="", description="phụ đề: lời nói gốc trong đoạn DỊCH sang ngôn ngữ đích (rỗng nếu chỉ là "
                                              "tiếng động / tiếng cười, không có lời)")
    text_vi: str = Field(default="", description="nghĩa tiếng Việt")
    why_vi: str = Field(default="", description="vì sao giữ tiếng gốc ở đây (tiếng Việt)")


class SellScript(BaseModel):
    video_index: int = Field(ge=1)
    onscreen_text: list[OnscreenLine] = Field(default_factory=list, description="phụ đề in trên hình AI đọc được, theo "
                                                                                 "thứ tự (rỗng nếu không có)")
    outline_vi: str = Field(description="dàn ý tiếng Việt viết TRƯỚC: mở đầu thu hút → nội dung → (kêu gọi hành động)")
    titles_top: list[str] = Field(default_factory=list, max_length=2,
                                  description="2 dòng tiêu đề lớn phía trên khối video, ngôn ngữ đích")
    music: MusicChoice
    lines: list[SellLine] = Field(min_length=3)
    target_s: float = Field(default=0, description="(chỉ khi chủ dự án để AI tự chọn thời lượng) số giây video bạn chọn")
    inserts: list[OrigInsert] = Field(default_factory=list, description="(chỉ Bán content) các đoạn GIỮ TIẾNG GỐC xen "
                                                                        "giữa lời đọc — bạn tự quyết có / bao nhiêu")
    editor_notes: str


# ---------------- Ý tưởng từ video dài (chủ dự án yêu cầu 17/10) ----------------

class CatalogShot(BaseModel):
    start: float = Field(ge=0, description="giây GỐC bắt đầu cảnh")
    end: float = Field(gt=0, description="giây GỐC kết thúc cảnh")
    desc_vi: str = Field(description="cảnh THẤY gì (tiếng Việt, ngắn, cụ thể: nơi chốn, vật, người, hành động)")
    tags: list[str] = Field(default_factory=list, description="vài nhãn ngắn tiếng Việt: địa điểm, chủ đề, không khí")
    quality: int = Field(default=3, ge=1, le=5, description="độ đẹp / dùng được để dựng short: 1 (mờ, rung) .. 5 (rất đẹp)")
    text: bool = Field(default=False, description="true = trên hình có chữ / phụ đề / logo / watermark in sẵn")


class Catalog(BaseModel):
    shots: list[CatalogShot] = Field(min_length=1)
    editor_notes: str = ""


class IdeaItem(BaseModel):
    title_vi: str = Field(description="tên ý tưởng (tiếng Việt), vd \"Nhật Bản có gì đẹp?\"")
    angle_vi: str = Field(description="góc kể / video nói gì, vì sao người xem muốn xem hết (tiếng Việt)")
    hook_vi: str = Field(description="câu mở đầu gợi ý (tiếng Việt)")
    kind_vi: str = Field(default="", description="kiểu video: top list, mẹo, cảm xúc, kiến thức, so sánh…")
    shots: list[str] = Field(min_length=1, description="mã cảnh trong danh mục (S1, S2…) dùng cho video này")
    why_vi: str = Field(default="", description="vì sao ý tưởng này hút người xem TikTok")


class IdeaList(BaseModel):
    ideas: list[IdeaItem] = Field(min_length=1)
    editor_notes: str


# ---------------- Bán content YouTube (chủ dự án yêu cầu 19/10) ----------------

class YtChapter(BaseModel):
    title: str = Field(description="tên chương bằng NGÔN NGỮ ĐÍCH (ngắn, hiện trên màn hình + mốc chương ở mô tả)")
    title_vi: str = Field(description="nghĩa tiếng Việt")
    summary_vi: str = Field(description="chương này nói gì, theo mạch nào, kết bằng gì để dẫn sang chương sau (tiếng Việt)")
    seconds: float = Field(gt=0, description="thời lượng chương (giây)")
    shots: list[str] = Field(min_length=1, description="mã cảnh trong danh mục (S1, S2…) dùng cho chương này")


class YtOutline(BaseModel):
    angle_vi: str = Field(description="góc làm video: content MỚI hay xào nấu lại content gốc, nói gì, vì sao người xem "
                                      "xem hết (tiếng Việt)")
    target_min: float = Field(gt=0, description="thời lượng đề xuất (phút)")
    titles: list[str] = Field(min_length=1, max_length=5, description="tiêu đề YouTube (ngôn ngữ đích), hay nhất trước")
    titles_vi: list[str] = Field(default_factory=list, description="nghĩa tiếng Việt từng tiêu đề")
    titles_top: list[str] = Field(default_factory=list, max_length=2,
                                  description="2 dòng chữ to phía trên video (ngôn ngữ đích, ngắn)")
    description: str = Field(description="đoạn mô tả YouTube (ngôn ngữ đích), 2–4 câu, KHÔNG ghi mốc chương (tool tự thêm)")
    tags: list[str] = Field(default_factory=list, description="10–15 tag (ngôn ngữ đích)")
    thumbnails_vi: list[str] = Field(default_factory=list, description="3 ý tưởng ảnh bìa (tiếng Việt): cảnh nào + chữ gì")
    chapters: list[YtChapter] = Field(min_length=2)
    editor_notes: str


# ---------------- Hoạt hình giữ âm thanh gốc (chủ dự án yêu cầu 20/10) ----------------

class AnimLine(BaseModel):
    speaker: str = Field(description="tên nhân vật nói câu này (viết thống nhất)")
    text: str = Field(description="lời thoại MỚI theo cốt truyện mới, bằng NGÔN NGỮ ĐÍCH, văn nói tự nhiên")
    text_vi: str = Field(description="nghĩa tiếng Việt")


class AnimBeat(BaseModel):
    start: float = Field(ge=0, description="giây GỐC bắt đầu cảnh")
    end: float = Field(gt=0, description="giây GỐC kết thúc cảnh")
    what_vi: str = Field(default="", description="cảnh này thấy gì / đóng vai gì trong cốt truyện mới (tiếng Việt)")
    line: AnimLine | None = Field(default=None, description="câu lồng tiếng trong cảnh này (cảnh có nhân vật nói)")


class AnimScript(BaseModel):
    original_story_vi: str = Field(description="tóm tắt cốt truyện GỐC (tiếng Việt)")
    new_story_vi: str = Field(description="cốt truyện MỚI (tiếng Việt): mở đầu – diễn biến – kết")
    story_diff: int = Field(ge=0, le=100, description="cốt truyện mới khác bản gốc bao nhiêu % (tự đánh giá thật thà)")
    feasible: bool = Field(default=True, description="false nếu KHÔNG THỂ làm khác ≥ 70% với các cảnh có sẵn")
    diff_note_vi: str = Field(default="", description="khác ở đâu; không đạt thì vì sao (tiếng Việt)")
    titles_top: list[str] = Field(default_factory=list, max_length=2, description="2 dòng tiêu đề (ngôn ngữ đích)")
    beats: list[AnimBeat] = Field(min_length=3, description="các cảnh THEO THỨ TỰ MỚI")
    editor_notes: str


# ---------------- Phụ đề tiếng Việt (chế độ "xem hiểu video nước ngoài") ----------------

class ViLine(BaseModel):
    i: int = Field(ge=1, description="số thứ tự câu gốc")
    vi: str = Field(description="câu dịch tiếng Việt tự nhiên, gọn để làm phụ đề")


class ViSubs(BaseModel):
    lines: list[ViLine] = Field(min_length=1)


FilmsIdea.model_rebuild()  # MusicChoice khai báo phía dưới FilmsIdea
