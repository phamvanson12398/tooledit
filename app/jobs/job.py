"""Job = một lần xử lý footage. Trạng thái lưu ở jobs/<job_id>/job.json để dừng rồi chạy tiếp.

Luồng Giai đoạn 1 (mục 3 của CLAUDE.md):

    created → analyzing → understanding → [chờ xác nhận thể loại] → hooks → [chờ chọn hook]
    → [chờ file voice] → planning → assets → writing → captions → done

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

STEPS = ["analyze", "understand", "confirm_genre", "hooks", "choose_hook", "voice", "plan", "assets", "write",
         "captions", "done"]

WAIT_STEPS = {"confirm_genre", "choose_hook", "voice"}


class Status(str, Enum):
    pending = "pending"    # sẵn sàng chạy bước hiện tại
    running = "running"
    waiting = "waiting"    # dừng chờ người dùng
    error = "error"
    done = "done"


class JobOptions(BaseModel):
    client_id: str | None = None      # None = khách mới, AI tự chọn phong cách
    hook: bool = False                # ☐ Có hook
    split: bool = False               # ☐ Chia video dài (Giai đoạn 2)
    reframe_per_scene: bool = False   # ☐ Đổi khung theo cảnh
    auto_download: bool = False       # ☐ Tự tải tài nguyên thiếu
    confirm_before_build: bool = False  # ☐ Xác nhận trước khi dựng


class HistoryEntry(BaseModel):
    at: str
    step: str
    status: Status
    message: str = ""


class Job(BaseModel):
    job_id: str
    footage: list[str]
    options: JobOptions = Field(default_factory=JobOptions)
    step: str = STEPS[0]
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
        os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, jobs_root: Path, job_id: str) -> "Job":
        path = cls.dir_for(jobs_root, job_id) / "job.json"
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))

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

    def advance(self, message: str = "") -> None:
        """Hoàn tất bước hiện tại, chuyển sang bước tiếp theo cần chạy (bỏ qua bước không áp dụng)."""
        idx = STEPS.index(self.step) + 1
        while idx < len(STEPS) and not self.applies(STEPS[idx]):
            idx += 1
        self.step = STEPS[min(idx, len(STEPS) - 1)]
        self.status = Status.done if self.step == "done" else Status.pending
        self._log(message or f"chuyển sang bước {self.step}")

    def applies(self, step: str) -> bool:
        if step == "confirm_genre":
            return self.options.confirm_before_build
        if step in ("hooks", "choose_hook", "voice"):
            return self.options.hook
        return True

    def resume(self, message: str = "người dùng bấm Tiếp tục") -> None:
        """Người dùng đã xử lý xong điểm dừng (hoặc muốn chạy lại bước lỗi)."""
        if self.status == Status.waiting:
            self.advance(message)
        elif self.status == Status.error:
            self.status = Status.pending
            self._log(message)


def new_job_id(jobs_root: Path) -> str:
    """Dạng 20260925_01, tăng dần trong ngày."""
    day = datetime.now().strftime("%Y%m%d")
    existing = [p.name for p in Path(jobs_root).glob(f"{day}_*")] if Path(jobs_root).exists() else []
    nums = [int(m.group(1)) for n in existing if (m := re.fullmatch(rf"{day}_(\d+)", n))]
    return f"{day}_{max(nums, default=0) + 1:02d}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
