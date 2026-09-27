import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.jobs.cleanup import cleanup_jobs
from app.jobs.job import Job


def _age(root: Path, job_id: str, days: float) -> None:
    """Đẩy lần hoạt động gần nhất của job về quá khứ."""
    p = root / job_id / "job.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    at = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    for h in data["history"]:
        h["at"] = at
    p.write_text(json.dumps(data), encoding="utf-8")


def test_cleanup_removes_only_inactive_old_jobs(tmp_path):
    for j in ("old", "recent", "running"):
        Job.create(tmp_path, [Path("a.mp4")], job_id=j)
    _age(tmp_path, "old", 3)
    _age(tmp_path, "running", 5)
    _age(tmp_path, "recent", 1)
    removed = cleanup_jobs(tmp_path, 2, skip={"running"})
    assert removed == ["old"]
    assert not (tmp_path / "old").exists()
    assert (tmp_path / "recent").exists() and (tmp_path / "running").exists()  # đang chạy thì không xóa
    assert cleanup_jobs(tmp_path, 0) == []  # 0 = tắt
    (tmp_path / "khong_phai_job").mkdir()  # thư mục lạ không có job.json: không đụng
    cleanup_jobs(tmp_path, 0.0001)
    assert (tmp_path / "khong_phai_job").exists()


def test_old_job_with_new_activity_is_kept(tmp_path):
    job = Job.create(tmp_path, [Path("a.mp4")], job_id="j")
    _age(tmp_path, "j", 5)
    job = Job.load(tmp_path, "j")
    job._log("người dùng bấm Tiếp tục")  # vừa có hoạt động mới
    job.save(tmp_path)
    assert cleanup_jobs(tmp_path, 2) == []


def test_web_cleanup_setting(tmp_path):
    from app.web.server import create_app

    jobs = tmp_path / "jobs"
    Job.create(jobs, [Path("a.mp4")], job_id="cu")
    _age(jobs, "cu", 1.5)
    app = create_app(jobs, settings_path=tmp_path / "l.yaml", scan_fn=lambda d, k: None)
    client = TestClient(app)
    assert "Tự xóa job không hoạt động quá" in client.get("/").text
    assert (jobs / "cu").exists()  # mặc định 2 ngày: 1.5 ngày chưa xóa
    client.post("/settings/cleanup", data={"days": "1"})
    assert not (jobs / "cu").exists()
