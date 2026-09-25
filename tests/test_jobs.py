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
