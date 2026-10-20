"""Job = một lần xử lý footage. Trạng thái lưu ở jobs/<job_id>/job.json để dừng rồi chạy tiếp.

Luồng Giai đoạn 1 (mục 3 của CLAUDE.md):

    created → analyzing → understanding → [chờ xác nhận thể loại] → chia video → [chờ duyệt chia video]
    → hooks → [chờ chọn hook] → [chờ file voice] → planning → assets → writing → captions → done

Mỗi bước sau "chia video" chạy cho từng video của job (data["videos"]); không chia thì chỉ có video 1.

Các bước trong ngoặc vuông là điểm dừng chờ người dùng (status = "waiting").
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

# post / idea / films_wait / match: chỉ chế độ Content nhiều phim (14/10) — job thường bắt đầu từ "analyze"
STEPS = ["post", "idea", "films_wait", "analyze", "understand", "confirm_genre", "segment", "review_segments", "hooks",
         "choose_hook", "voice", "plan", "match", "dub", "dub_voice", "assets", "write", "captions", "done"]
FILMS_STEPS = ("post", "idea", "films_wait", "analyze", "match", "dub", "dub_voice", "write", "captions", "done")

WAIT_STEPS = {"post", "films_wait", "confirm_genre", "review_segments", "choose_hook", "voice", "dub_voice"}


class Status(str, Enum):
    pending = "pending"    # sẵn sàng chạy bước hiện tại
    running = "running"
    waiting = "waiting"    # dừng chờ người dùng
    error = "error"
    done = "done"
    stopped = "stopped"    # người dùng bấm Dừng; bấm Chạy tiếp để chạy lại từ bước đang dở


class JobOptions(BaseModel):
    client_id: str | None = None      # None = khách mới, AI tự chọn phong cách
    hook: bool = False                # ☐ Có hook
    split: bool = False               # ☐ Chia video dài
    reframe_per_scene: bool = False   # ☐ Đổi khung theo cảnh
    auto_download: bool = False       # ☐ Tự tải tài nguyên thiếu
    confirm_before_build: bool = False  # ☐ Xác nhận trước khi dựng
    target_language: str = ""         # Đổi ngôn ngữ: "" = giữ nguyên; ko/ja/en/de = thuyết minh + phụ đề tiếng đó
    voice_only: bool = False          # Chỉ thay tiếng (05/10): giữ nguyên hình, không cắt / đổi khung — cần target_language
    vi_sub: bool = False              # Phụ đề tiếng Việt (08/10): chỉ dịch lời sang tiếng Việt để xem hiểu, không dựng lại
    hype: bool = False                # Chuyển cảnh liên tục: cảnh gay cấn lên đầu (3–5s/cảnh), còn lại về sau (07/10)
    script_mode: str = ""             # Đổi ngôn ngữ: "rewrite" = AI xem video viết mới / "translate" = dịch; "" = theo config
    keep_bgm: bool = False            # (cùng voice_only) giữ nhạc nền gốc: tách giọng nói ra, chỉ thay lời thuyết minh
    review: bool = False              # Review phim / hoạt hình: 11/10 tóm gọn CẢ phim thành MỘT video, chỉ kể ý chính
    review_s: int = 0                 # Review (11/10): thời lượng video chủ dự án chọn (giây); 0 = default_s trong review.yaml
    char_dub: bool = False            # Lồng tiếng nhân vật (11/10): đoạn hay TikTok, thay giọng từng nhân vật, giữ nền gốc
    ai: str = ""                      # AI đạo diễn của job (11/10): "claude" | "gemini"; "" = default_ai trong config
    sell: bool = False                # Bán content (15/10): kịch bản mới + cảnh đảo theo lời, voice + nhạc mới, đóng gói CapCut
    sell_brief: str = ""              # Bán content: định hướng nội dung chủ dự án nhập
    sell_s: int = 0                   # Bán content: thời lượng mục tiêu (giây); 0 = default_s trong config/sell.yaml
    sell_auto: bool = False           # Bán content (20/10): AI TỰ CHỌN thời lượng theo nội dung (luôn > 60 giây)
    sell_variants: int = 1            # Bán content (17/10): số bản KHÁC NHAU làm từ cùng video (1–3)
    sell_voice: str = ""              # Bán content (17/10): giọng trong thư viện Voice Studio → OmniVoice tự đọc, khỏi thu tay
    cliff: bool = False               # Review bỏ lửng (14/10): đi CÙNG review=True — kể HẾT phim thành nhiều phần 1:30–2:00,
                                      #   mỗi phần mở bằng short kịch tính giữ nguyên, kết bỏ lửng (config/cliff.yaml)
    films: bool = False               # Content nhiều phim từ bài TikTok ảnh (14/10): AI viết content mới, hình cắt từ
                                      #   các file phim chủ dự án đưa, xen dừng hình (config/films.yaml)
    ideas: bool = False               # Ý tưởng từ video dài (17/10): đi CÙNG sell=True — video dài làm kho cảnh, AI nghĩ
                                      #   nhiều ý tưởng short, chủ dự án tick cái muốn làm (config/ideas.yaml)
    ideas_brief: str = ""             # Ý tưởng từ video dài: gợi ý chủ đề / khán giả (không bắt buộc)
    anim: bool = False                # Hoạt hình giữ âm thanh gốc (20/10): cốt truyện MỚI (khác ≥ 70%) từ chính các cảnh,
                                      #   giữ nhạc / tiếng động gốc, lồng voice + phụ đề chỗ nhân vật nói (config/anim.yaml)
    yt: bool = False                  # Bán content YouTube (19/10): đi CÙNG sell=True — video nguồn < 1h30 → video YouTube
                                      #   dài chia chương (config/youtube.yaml)
    yt_min: int = 0                   # Bán content YouTube: thời lượng (phút) chủ dự án chọn; 0 = AI tự chọn theo nội dung
    yt_pause: bool = False            # Bán content YouTube: dừng cho chủ dự án duyệt dàn ý (không tick = chạy thẳng)
    cliff_pov: str = ""               # Review bỏ lửng: ngôi kể "1" (người kể là nhân vật chính) | "3"; "" = default_pov


class HistoryEntry(BaseModel):
    at: str
    step: str
    status: Status
    message: str = ""


class Job(BaseModel):
    job_id: str
    footage: list[str]
    options: JobOptions = Field(default_factory=JobOptions)
    step: str = "analyze"        # chế độ Content nhiều phim bắt đầu từ "post"
    status: Status = Status.pending
    message: str = ""            # thông báo tiếng Việt hiển thị trên giao diện
    history: list[HistoryEntry] = Field(default_factory=list)
    data: dict = Field(default_factory=dict)  # kết quả nhỏ từng bước (tóm tắt, lựa chọn...)

    # ---------- lưu / nạp ----------

    @staticmethod
    def dir_for(jobs_root: Path, job_id: str) -> Path:
        return Path(jobs_root) / job_id

    def dir(self, jobs_root: Path) -> Path:
        return self.dir_for(jobs_root, self.job_id)

    def save(self, jobs_root: Path) -> Path:
        d = self.dir(jobs_root)
        d.mkdir(parents=True, exist_ok=True)
        path = d / "job.json"
        tmp = path.with_name("job.json.writing")
        tmp.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        _retry(lambda: os.replace(tmp, path))
        return path

    @classmethod
    def load(cls, jobs_root: Path, job_id: str) -> "Job":
        path = cls.dir_for(jobs_root, job_id) / "job.json"
        return cls.model_validate(json.loads(_retry(lambda: path.read_text(encoding="utf-8"))))

    @classmethod
    def create(cls, jobs_root: Path, footage: list[Path], options: JobOptions | None = None,
               job_id: str | None = None) -> "Job":
        job_id = job_id or new_job_id(jobs_root)
        job = cls(job_id=job_id, footage=[Path(f).as_posix() for f in footage], options=options or JobOptions())
        job._log("tạo job")
        job.save(jobs_root)
        return job

    # ---------- chuyển trạng thái ----------

    def _log(self, message: str) -> None:
        self.message = message
        self.history.append(HistoryEntry(at=_now(), step=self.step, status=self.status, message=message))

    def start(self) -> None:
        self.status = Status.running
        self._log(f"đang chạy bước {self.step}")

    def wait(self, message: str) -> None:
        self.status = Status.waiting
        self._log(message)

    def fail(self, message: str) -> None:
        self.status = Status.error
        self._log(message)

    def stop(self, message: str = "Đã dừng theo yêu cầu. Bấm Chạy tiếp để chạy lại từ bước này.") -> None:
        self.status = Status.stopped
        self._log(message)

    def advance(self, message: str = "") -> None:
        """Hoàn tất bước hiện tại, chuyển sang bước tiếp theo cần chạy (bỏ qua bước không áp dụng)."""
        idx = STEPS.index(self.step) + 1
        while idx < len(STEPS) and not self.applies(STEPS[idx]):
            idx += 1
        self.step = STEPS[min(idx, len(STEPS) - 1)]
        self.status = Status.done if self.step == "done" else Status.pending
        self._log(message or f"chuyển sang bước {self.step}")

    @property
    def use_hook(self) -> bool:
        """Có hook voice riêng. Review phim thì KHÔNG (câu mở đầu của bài lời đọc là hook; hook riêng làm đứt mạch kể)."""
        return (self.options.hook and not self.options.review and not self.options.char_dub and not self.options.sell
                and not self.options.anim)

    @property
    def picks_segments(self) -> bool:
        """Job có bước AI chọn / chia đoạn + bảng duyệt. Review phim KHÔNG (chủ dự án 11/10: tóm gọn cả phim thành MỘT
        video, không chia nhiều video); Review bỏ lửng CÓ (chia phim thành các phần liền nhau)."""
        return (self.options.split or self.options.char_dub or self.options.cliff or self.options.ideas
                or self.options.yt)

    def applies(self, step: str) -> bool:
        if self.options.films:
            return step in FILMS_STEPS
        if step in ("post", "idea", "films_wait", "match"):
            return False
        if self.options.vi_sub:  # chỉ phân tích (nhận dạng lời) rồi dịch + ghi phụ đề ở bước write
            return step in ("analyze", "write", "done")
        if step == "confirm_genre":
            return self.options.confirm_before_build
        if step in ("hooks", "choose_hook", "voice"):
            return self.use_hook
        if step == "review_segments":
            return self.picks_segments
        if step in ("dub", "dub_voice"):
            return bool(self.options.target_language) or self.options.review or self.options.sell
        return True

    def resume(self, message: str = "người dùng bấm Tiếp tục") -> None:
        """Người dùng đã xử lý xong điểm dừng (hoặc muốn chạy lại bước lỗi)."""
        if self.status == Status.waiting:
            self.advance(message)
        elif self.status in (Status.error, Status.stopped):
            self.status = Status.pending
            self._log(message)


def _retry(fn, attempts: int = 20, delay: float = 0.05):
    """Windows khóa file trong tích tắc khi một luồng đang ghi đè (os.replace) mà luồng khác đọc
    → PermissionError. Thử lại vài lần thay vì báo lỗi (tổng chờ tối đa ~1 giây)."""
    import time

    for i in range(attempts):
        try:
            return fn()
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(delay)


def new_job_id(jobs_root: Path) -> str:
    """Dạng 20260925_01, tăng dần trong ngày."""
    day = datetime.now().strftime("%Y%m%d")
    existing = [p.name for p in Path(jobs_root).glob(f"{day}_*")] if Path(jobs_root).exists() else []
    nums = [int(m.group(1)) for n in existing if (m := re.fullmatch(rf"{day}_(\d+)", n))]
    return f"{day}_{max(nums, default=0) + 1:02d}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
