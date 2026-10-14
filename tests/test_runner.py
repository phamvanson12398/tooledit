import json
from pathlib import Path

import pytest

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
    assert job.status == Status.error and job.step == "plan"
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


def test_resolve_template_fallback_to_builtin(tmp_path, monkeypatch):
    import shutil

    from app import settings
    from app.jobs import runner as runner_mod

    shutil.copytree(SAMPLE, tmp_path / "drafts" / "0925")
    monkeypatch.setattr(runner_mod, "drafts_root", lambda: tmp_path / "drafts")
    local = tmp_path / "local.yaml"
    monkeypatch.setattr(settings, "LOCAL", local)
    monkeypatch.setattr(settings.load, "__defaults__", (local,))
    assert runner_mod.resolve_template() == tmp_path / "drafts" / "0925"  # theo config: capcut_template
    settings.save({"template_name": "da_bi_xoa"}, local)
    logs = []
    assert runner_mod.resolve_template(logs.append) == runner_mod.BUILTIN_TEMPLATE  # không dừng job
    assert "da_bi_xoa" in logs[0]
    settings.save({"template_name": runner_mod.BUILTIN}, local)
    assert runner_mod.resolve_template() == runner_mod.BUILTIN_TEMPLATE
    assert [n for _, n in runner_mod.list_drafts(tmp_path / "drafts")] == ["capcut_template"]


def test_style_choice_user_vs_auto(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions())
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.done and job.data["style_used"] == "jp_telop"  # đạo diễn đề xuất
    jobs2, job2 = prepare(tmp_path / "b", JobOptions())
    job2.data["style"] = "podcast"
    job2 = make_runner(tmp_path / "b", jobs2).run(job2)
    assert job2.data["style_used"] == "podcast"


def _split_director():
    import copy

    from tests.test_planner import load

    u = load("understand.json")
    u["usable_range"] = {"start": 0.0, "end": 200.0}
    h1 = load("hooks.json")
    h2 = copy.deepcopy(h1)
    h2["video_index"] = 2
    for o in h2["options"]:
        for k in ("footage", "source", "intro_footage"):
            o[k] = {"start": o[k]["start"] + 80, "end": o[k]["end"] + 80}
    base = {**load("plan.json"), "emphasis": [], "zooms": [], "sfx": [], "effects": [], "stickers": [],
            "transitions": [], "arrows": []}
    p1 = {**base, "clips": [{"source_start": 1.0, "source_end": 65.0}]}
    p2 = {**base, "video_index": 2, "clips": [{"source_start": 76.0, "source_end": 145.0}]}
    c1 = load("captions.json")
    c2 = {**c1, "video_index": 2}
    return FakeDirector(responses={"understand": u, "hooks": [h1, h2], "plan": [p1, p2], "captions": [c1, c2]})


def test_split_job_two_videos(tmp_path):
    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/long.mp4")], JobOptions(split=True, hook=True, client_id="k"), job_id="j2")
    make_analysis(jobs / "j2", duration=200.0)
    r = make_runner(tmp_path, jobs)
    r._director = _split_director()
    job = r.run(job)
    assert job.step == "review_segments" and job.status == Status.waiting, job.message
    seg = json.loads((jobs / "j2" / "plan" / "segments.json").read_text(encoding="utf-8"))
    assert len(seg["videos"]) == 2 and seg["proposal"]["dropped"]

    # người dùng chỉnh điểm cắt video 2 rồi xác nhận
    rows = [dict(seg["videos"][0]), {**seg["videos"][1], "end": 148.0}]
    r.apply_segments(job, rows)
    job = r.resume(job)
    assert job.step == "choose_hook" and job.status == Status.waiting
    assert "=== VIDEO 02 ===" in job.message
    r.choose_hooks(job, {1: 1})
    job = r.resume(job)
    assert job.step == "choose_hook"  # còn thiếu lựa chọn cho video 2
    r.choose_hooks(job, {1: 1, 2: 3})
    job = r.resume(job)
    assert job.step == "voice" and "video02_hook.wav" in job.message
    for i in (1, 2):
        (jobs / "j2" / "voice" / f"video0{i}_hook.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    drafts = job.data["drafts"]
    assert [Path(d["draft"]).name for d in drafts] == ["k_j2_video01", "k_j2_video02"]
    assert all((jobs / "j2" / "deliver" / f"video0{i}_captions.txt").is_file() for i in (1, 2))
    assert (jobs / "j2" / "plan" / "edit_plan_video02.json").is_file()

    # chia lại → xóa hook / kế hoạch cũ, voice được cất đi
    r.redo(job, "segment")
    assert not (jobs / "j2" / "plan" / "segments.json").exists()
    assert not list((jobs / "j2" / "plan").glob("edit_plan_video*.json"))
    assert (jobs / "j2" / "voice" / "video02_hook_cu.wav").exists()


def test_apply_segments_validation(tmp_path):
    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/long.mp4")], JobOptions(split=True), job_id="j3")
    make_analysis(jobs / "j3", duration=100.0)
    r = make_runner(tmp_path, jobs)
    with pytest.raises(ValueError):
        r.apply_segments(job, [{"start": 10, "end": 5}])
    with pytest.raises(ValueError):
        r.apply_segments(job, [{"start": 0, "end": 60}, {"start": 50, "end": 99}])
    with pytest.raises(ValueError):
        r.apply_segments(job, [{"start": 0, "end": 160}])
    with pytest.raises(ValueError):
        r.apply_segments(job, [])


def test_vlog_uses_light_denoised_audio(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions())
    job.data["style"] = "vlog"
    audio = jobs / "j1" / "analysis" / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    for name in ("clean_00.wav", "light_00.wav"):
        (audio / name).write_bytes(b"RIFF")
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.done, job.message
    draft = Path(job.data["draft"])
    content = (draft / "draft_content.json").read_text(encoding="utf-8")
    assert "light_00.wav" in content and "clean_00.wav" not in content


def test_template_without_video_borrows_builtin(tmp_path):
    """Dự án mẫu người dùng chọn không có clip video → mượn khuôn từ mẫu có sẵn, không lỗi ở bước write."""
    import shutil

    from app.capcut_writer.template import main_timeline_path, timeline_copies

    tdir = tmp_path / "mau_khong_video"
    shutil.copytree(SAMPLE, tdir)
    for path in timeline_copies(tdir):
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            data["tracks"] = [t for t in data["tracks"] if t["type"] != "video"]
            path.write_text(json.dumps(data), encoding="utf-8")
    assert all(t["type"] != "video" for t in json.loads(main_timeline_path(tdir).read_text("utf-8"))["tracks"])

    jobs, job = prepare(tmp_path, JobOptions())
    logs = []
    r = make_runner(tmp_path, jobs)
    r._template_dir = tdir
    r.log = logs.append
    tpl = r._template()
    assert "video" in tpl.prototypes and "video" in tpl.track_prototypes
    assert any("mượn khuôn" in m for m in logs)
    job = r.run(job)
    assert job.status == Status.done, job.message


@pytest.mark.parametrize("ratio", ["4:5", "3:4", "9:10", "9:16"])
def test_new_frame_ratios_build(tmp_path, ratio):
    """Khung video mới (chủ dự án 11/10): job dựng xong, khối video đúng tỉ lệ đã chọn."""
    import json as _json

    jobs, job = prepare(tmp_path, JobOptions())
    job.data["default_ratio"] = ratio
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.done, job.message
    content = _json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    assert content["tracks"] and any(t["type"] == "video" and t["segments"] for t in content["tracks"])


def test_long_video_split_into_parts_in_parallel(tmp_path):
    """Chủ dự án 11/10: video dài > 10 phút → chia phần ở chỗ im lặng, AI chọn đoạn từng phần SONG SONG rồi gộp."""
    import re
    import threading
    import time

    from app.director.base import Director
    from app.director.fake import FakeDirector
    from app.director.tasks import long_parts, make_segments_long, understand

    segs = [{"start": t, "end": t + 8.0, "text": "x"} for t in range(0, 1500, 10)]
    segs = [s for s in segs if not 740 <= s["start"] < 770]          # khoảng lặng 30 giây quanh phút 12.5
    assert long_parts(segs, 0.0, 500.0) == [(0.0, 500.0)]            # ngắn → một phần
    parts = long_parts(segs, 0.0, 1500.0)
    assert len(parts) == 3 and abs(parts[0][1] - 500) <= 60 and abs(parts[1][1] - 1000) <= 60  # ~10 phút một phần
    assert all(not (sg["start"] < c < sg["end"]) for c in (parts[0][1], parts[1][1]) for sg in segs)  # không cắt giữa câu
    two = long_parts(segs, 0.0, 1500.0, {"split_over_s": 900, "max_parts": 4})
    assert len(two) == 2 and 738 <= two[0][1] <= 770                 # điểm chia rơi vào giữa khoảng lặng

    a = make_analysis(tmp_path, duration=1500.0)
    u = understand(FakeDirector(), a)
    u = u.model_copy(update={"usable_range": u.usable_range.model_copy(update={"start": 0.0, "end": 1500.0})})
    live, peak, lock = [0], [0], threading.Lock()

    class PartDirector(Director):  # trả một video ở đầu phần được giao, đo số lượt chạy cùng lúc
        def _complete(self, task, prompt, schema, images):
            with lock:
                live[0] += 1
                peak[0] = max(peak[0], live[0])
            time.sleep(0.2)
            with lock:
                live[0] -= 1
            lo, hi = map(float, re.search(r"đoạn dùng được ([\d.]+)–([\d.]+)", prompt).groups())
            return {"videos": [{"start": lo + 5, "end": lo + 100, "title_vi": f"phần {lo:.0f}", "summary_vi": "s",
                                "why_vi": "w"}], "dropped": [{"start": lo + 100, "end": lo + 120, "reason_vi": "nhạt"}],
                    "editor_notes": f"chọn ở {lo:.0f}"}

    logs = []
    sp = make_segments_long(PartDirector(), a, u, log=logs.append)
    assert len(sp.videos) == 3 and [v.start for v in sp.videos] == sorted(v.start for v in sp.videos)
    assert len(sp.dropped) == 3 and sp.editor_notes.count("Phần ") == 3
    assert peak[0] == 2                                              # parallel_calls: 2 lượt cùng lúc
    assert "chia 3 phần" in logs[0]


def test_plan_wrong_3_times_asks_to_use_last(tmp_path):
    """Chủ dự án 14/10: "Lỗi ở bước plan: Đạo diễn trả kết quả sai khuôn 3 lần" → cho chọn dùng bản gần nhất rồi làm tiếp."""
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    jobs, job = prepare(tmp_path, JobOptions())
    r = make_runner(tmp_path, jobs)
    bad = {**_short_plan(), "video_index": 7}  # luôn sai một lỗi nhỏ → AI sửa 3 lần không được
    r._director = FakeDirector(responses={"plan": bad})
    job = r.run(job)
    assert job.status == Status.error and job.step == "plan" and "sai khuôn 3 lần" in job.message
    pend = jobs / "j1" / "plan" / "pending_plan_video01.json"
    assert pend.is_file() and json.loads(pend.read_text(encoding="utf-8"))["problems"]
    page = TestClient(create_app(jobs, lambda root, log: None)).get("/jobs/j1").text
    assert "Có lấy kế hoạch dựng gần nhất không?" in page and "/jobs/j1/accept-plan" in page
    assert "video_index phải là 1" in page
    assert r.accept_pending_plan(job) == 1 and not pend.is_file()
    calls = len(r._director.calls)
    job = r.run(job)
    assert job.status == Status.done, job.message
    assert not any(c["task"] == "plan" for c in r._director.calls[calls:])   # không hỏi lại AI kế hoạch
