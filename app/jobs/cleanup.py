"""Tự xóa job không hoạt động quá N ngày (chủ dự án yêu cầu 27/09: quá 2 ngày).

Tính theo lần hoạt động GẦN NHẤT của job (không phải ngày tạo) để không xóa job đang làm dở.
Không đụng job đang chạy / đang xếp hàng. Chỉ xóa thư mục jobs/<job_id> (footage gốc của khách và draft trong
CapCut KHÔNG bị xóa).
"""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.jobs.job import Job


def last_activity(job_dir: Path) -> datetime:
    try:
        job = Job.load(job_dir.parent, job_dir.name)
        if job.history:
            return datetime.fromisoformat(job.history[-1].at)
    except Exception:
        pass
    ref = job_dir / "job.json" if (job_dir / "job.json").is_file() else job_dir
    return datetime.fromtimestamp(ref.stat().st_mtime, tz=timezone.utc)


def cleanup_jobs(jobs_root: Path, keep_days: float, skip: set[str] | None = None,
                 now: datetime | None = None) -> list[str]:
    """Xóa job không hoạt động quá keep_days ngày. keep_days <= 0: tắt. Trả danh sách job đã xóa."""
    root = Path(jobs_root)
    if keep_days <= 0 or not root.is_dir():
        return []
    now = now or datetime.now(timezone.utc)
    limit = now - timedelta(days=keep_days)
    removed = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not (d / "job.json").is_file() or d.name in (skip or set()):
            continue
        if last_activity(d) < limit:
            shutil.rmtree(d, ignore_errors=True)
            removed.append(d.name)
    return removed
