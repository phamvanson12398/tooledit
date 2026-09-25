from pathlib import Path

from app.jobs.job import Job, JobOptions, Status, new_job_id


def test_job_flow_without_hook(tmp_path: Path):
    job = Job.create(tmp_path, [Path("C:/f/a.mp4")], job_id="20260925_01")
    assert (tmp_path / "20260925_01" / "job.json").is_file()
    job.start()
    job.advance()
    assert job.step == "understand"
    job.advance()
    assert job.step == "plan"  # không xác nhận, không hook → nhảy thẳng
    job.save(tmp_path)
    again = Job.load(tmp_path, "20260925_01")
    assert again.step == "plan" and again.footage == ["C:/f/a.mp4"]


def test_job_flow_with_hook_and_waits(tmp_path: Path):
    job = Job.create(tmp_path, [Path("a.mp4")], JobOptions(hook=True, confirm_before_build=True), job_id="j")
    steps = [job.step]
    for _ in range(3):
        job.advance()
        steps.append(job.step)
    assert steps == ["analyze", "understand", "confirm_genre", "hooks"]
    job.advance()
    job.wait("Chọn 1 trong 3 hook cho mỗi video")
    assert job.status == Status.waiting and job.step == "choose_hook"
    job.resume()
    assert job.step == "voice" and job.status == Status.pending
    job.fail("Thiếu file voice")
    job.resume()
    assert job.status == Status.pending and job.step == "voice"


def test_new_job_id_increments(tmp_path: Path):
    first = new_job_id(tmp_path)
    (tmp_path / first).mkdir()
    second = new_job_id(tmp_path)
    assert first.endswith("_01") and second.endswith("_02") and first[:8] == second[:8]


def test_load_retries_when_file_is_briefly_locked(tmp_path, monkeypatch):
    """Giả lập Windows: lần đọc đầu bị PermissionError (đang bị ghi đè), lần sau đọc được."""
    job = Job.create(tmp_path, [Path("a.mp4")], job_id="j")
    real_read = Path.read_text
    calls = {"n": 0}

    def flaky(self, *a, **k):
        if self.name == "job.json" and calls["n"] < 2:
            calls["n"] += 1
            raise PermissionError(13, "Permission denied")
        return real_read(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", flaky)
    assert Job.load(tmp_path, "j").job_id == "j" and calls["n"] == 2
    job.save(tmp_path)
