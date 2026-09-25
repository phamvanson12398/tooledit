import json
from pathlib import Path

from app.director.fake import FakeDirector
from app.jobs.job import Job, JobOptions, Status
from app.jobs.runner import Runner
from tests.test_director import make_analysis
from tests.test_planner import SAMPLE, _short_plan


def make_runner(tmp_path, jobs):
    return Runner(jobs, director=FakeDirector(responses={"plan": _short_plan()}),
                  analyze_fn=lambda job, root, progress: None, probe_duration_fn=lambda p: 3_000_000,
                  drafts_dir=tmp_path / "drafts", template_dir=SAMPLE, log=lambda m: None)


def prepare(tmp_path, options):
    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/test.mp4")], options, job_id="j1")
    make_analysis(jobs / "j1", duration=60.0)  # giả như đã phân tích
    return jobs, job


def test_full_job_with_hook_and_waits(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(hook=True, client_id="khachA"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "choose_hook" and "=== VIDEO 01 ===" in job.message

    r.choose_hooks(job, {1: 1})
    job = r.resume(job)
    assert job.status == Status.waiting and job.step == "voice" and "video01_hook.wav" in job.message
    assert (jobs / "j1" / "hook_scripts.txt").is_file()

    job = r.resume(job)  # vẫn thiếu voice → vẫn chờ
    assert job.step == "voice" and job.status == Status.waiting

    (jobs / "j1" / "voice" / "video01_hook.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    draft = Path(job.data["draft"])
    assert draft.name == "khachA_j1_video01" and (draft / "draft_meta_info.json").is_file()
    assert (jobs / "j1" / "plan" / "edit_plan_video01.json").is_file()
    missing = json.loads((jobs / "j1" / "missing_assets.json").read_text(encoding="utf-8"))
    assert [m["kind"] for m in missing] == ["sfx"]
    assert Job.load(jobs, "j1").status == Status.done
    cap = (jobs / "j1" / "deliver" / "video01_captions.txt").read_text(encoding="utf-8")
    assert "#相撲" in cap and "DỊCH TIẾNG VIỆT" in cap


def test_job_without_hook_and_error_recovery(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(confirm_before_build=True))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.step == "confirm_genre" and job.status == Status.waiting
    r._template_dir = tmp_path / "khong_co"  # lỗi: không có dự án mẫu
    job = r.resume(job)
    assert job.status == Status.error and "dự án mẫu" in job.message and job.step == "plan"
    r._template_dir = SAMPLE
    job = r.resume(job)
    assert job.status == Status.done, job.message


def test_find_template_by_display_name(tmp_path):
    import shutil

    from app.jobs.runner import find_template

    shutil.copytree(SAMPLE, tmp_path / "0925")
    (tmp_path / "khac").mkdir()
    assert find_template(tmp_path, "capcut_template") == tmp_path / "0925"
    assert find_template(tmp_path, "khong_co") is None


def test_style_choice_user_vs_auto(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions())
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.done and job.data["style_used"] == "jp_telop"  # đạo diễn đề xuất
    jobs2, job2 = prepare(tmp_path / "b", JobOptions())
    job2.data["style"] = "podcast"
    job2 = make_runner(tmp_path / "b", jobs2).run(job2)
    assert job2.data["style_used"] == "podcast"
