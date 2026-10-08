"""Chuyển cảnh liên tục (cảnh gay cấn lên đầu) + ghép nhiều video thành một video mới (chủ dự án yêu cầu 07/10)."""

import json
import subprocess
from pathlib import Path

import pytest

from app.analysis.montage import build_montage, concat_args, part_of, parts_from, target_size
from app.director.schemas import EditPlan, check_hype, check_montage, reorder_hype, repair_montage
from tests.test_planner import load


def _plan(clips, transitions=()):
    return EditPlan.model_validate({**load("plan.json"), "clips": clips, "transitions": list(transitions),
                                    "zooms": [], "emphasis": [], "sfx": []})


def test_reorder_hype_puts_highlights_first():
    p = _plan([{"source_start": 1, "source_end": 5}, {"source_start": 10, "source_end": 14, "highlight": True},
               {"source_start": 20, "source_end": 24}, {"source_start": 30, "source_end": 34, "highlight": True}],
              [{"after_clip": 1, "name": "x"}])
    q, notes = reorder_hype(p)
    assert [c.source_start for c in q.clips] == [10, 30, 1, 20]  # gay cấn lên đầu (giữ thứ tự AI), còn lại theo thời gian
    assert q.transitions[0].after_clip == 0 and notes
    assert reorder_hype(q)[1] == []  # đã đúng thứ tự → không đổi


def test_check_hype_clip_lengths_and_highlights():
    clips = [{"source_start": float(t), "source_end": t + 4.0} for t in range(0, 40, 5)]
    assert any("highlight" in e for e in check_hype(_plan(clips)))
    clips[0]["highlight"] = clips[3]["highlight"] = True
    assert check_hype(_plan(clips)) == []
    clips[1]["source_end"] = clips[1]["source_start"] + 9
    assert any("chia nhỏ" in e for e in check_hype(_plan(clips)))


def test_montage_helpers():
    inputs = [{"path": Path("a.mp4"), "duration": 10.0, "has_audio": True},
              {"path": Path("b.mp4"), "duration": 5.5, "has_audio": False}]
    parts = parts_from(inputs)
    assert parts == [{"index": 1, "name": "a.mp4", "start": 0.0, "end": 10.0},
                     {"index": 2, "name": "b.mp4", "start": 10.0, "end": 15.5}]
    assert part_of(parts, 12.0) == 2 and part_of(parts, 15.5) == 2
    args = concat_args(inputs, Path("out.mp4"), (1920, 1080))
    fc = args[args.index("-filter_complex") + 1]
    assert "anullsrc" in " ".join(args) and "concat=n=2:v=1:a=1" in fc and "[2:a]" in fc  # video thiếu tiếng được bù lặng
    assert target_size([(1080, 1920), (720, 1280), (1920, 1080)]) == (1080, 1920)
    p = _plan([{"source_start": 8.0, "source_end": 12.0}, {"source_start": 11.0, "source_end": 14.0}])
    fixed, notes = repair_montage(p, parts)
    assert (fixed.clips[0].source_start, fixed.clips[0].source_end) == (8.0, 9.95) and notes  # không vắt qua 2 video
    assert check_montage(fixed, parts) == []
    assert check_montage(_plan([{"source_start": 1.0, "source_end": 5.0}]), parts)


def test_build_montage_real_ffmpeg(tmp_path):
    ff = pytest.importorskip("imageio_ffmpeg").get_ffmpeg_exe()
    from app.analysis import ffmpeg
    from app.capcut_writer.media import VideoSource

    a, b = tmp_path / "a.mp4", tmp_path / "b.mp4"
    subprocess.run([ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1:r=25",
                    "-f", "lavfi", "-i", "sine=d=1", "-shortest", "-pix_fmt", "yuv420p", str(a)], check=True)
    subprocess.run([ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=blue:s=240x320:d=1.5:r=30",
                    "-pix_fmt", "yuv420p", str(b)], check=True)  # khác cỡ, không có tiếng
    sizes = {a: (320, 240, 1.0, True), b: (240, 320, 1.5, False)}
    probe = lambda p: VideoSource(p, sizes[p][0], sizes[p][1], int(sizes[p][2] * 1e6), sizes[p][3])
    out = tmp_path / "source" / "montage.mp4"
    parts = build_montage([a, b], out, probe=probe, run=lambda args: ffmpeg.run(args, exe=ff))
    assert out.stat().st_size > 0 and parts[1]["start"] == 1.0 and parts[1]["end"] == 2.5


def test_runner_montage_job(tmp_path):
    from app.director.fake import FakeDirector
    from app.jobs.job import Job, JobOptions, Status
    from app.jobs.runner import Runner
    from tests.test_director import make_analysis
    from tests.test_planner import SAMPLE

    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [Path("C:/f/ep1.mp4"), Path("C:/f/ep2.mp4")], JobOptions(hype=True), job_id="m1")
    clips = [{"source_start": 32.0, "source_end": 36.0, "highlight": True},
             {"source_start": 2.0, "source_end": 6.0}, {"source_start": 8.0, "source_end": 12.0},
             {"source_start": 14.0, "source_end": 18.0, "highlight": True}, {"source_start": 40.0, "source_end": 44.0},
             {"source_start": 46.0, "source_end": 50.0}]
    plan = {**load("plan.json"), "clips": clips, "zooms": [], "emphasis": [], "sfx": [], "transitions": []}

    def fake_montage(paths, out):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"x")
        return [{"index": 1, "name": "ep1.mp4", "start": 0.0, "end": 30.0},
                {"index": 2, "name": "ep2.mp4", "start": 30.0, "end": 60.0}]

    def analyze(job, root, progress):
        make_analysis(root / job.job_id, duration=60.0)

    r = Runner(jobs, director=FakeDirector(responses={"plan": plan}), analyze_fn=analyze,
               probe_duration_fn=lambda p: 3_000_000, drafts_dir=tmp_path / "drafts", template_dir=SAMPLE,
               log=lambda m: None)
    r._montage_fn = fake_montage
    job = r.run(job)
    assert job.status == Status.done, job.message
    assert [Path(x).name for x in job.data["sources"]] == ["ep1.mp4", "ep2.mp4"]  # giữ danh sách video gốc
    assert job.footage[0].endswith("montage.mp4") and len(job.data["montage_parts"]) == 2
    saved = json.loads((jobs / "m1" / "plan" / "edit_plan_video01.json").read_text(encoding="utf-8"))
    starts = [c["source_start"] for c in saved["clips"]]
    assert starts[:2] == [32.0, 14.0] and starts[2:] == sorted(starts[2:])  # gay cấn lên đầu, còn lại theo thời gian
    prompt = next(c["prompt"] for c in r.director.calls if c["task"] == "plan")
    assert "GHÉP NHIỀU VIDEO" in prompt and "video 2 (ep2.mp4)" in prompt and "CHUYỂN CẢNH LIÊN TỤC" in prompt


def test_web_multi_video_form(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    a, b = tmp_path / "a.mp4", tmp_path / "b.mp4"
    a.write_bytes(b"x")
    b.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    client = TestClient(app)
    home = client.get("/").text
    assert "Ghép nhiều video" in home and "Chuyển cảnh liên tục" in home
    r = client.post("/jobs", data={"footage": f"{a}\n\"{b}\"\n", "split": "on"}, follow_redirects=False)
    job = Job.load(tmp_path / "jobs", r.headers["location"].rsplit("/", 1)[1])
    assert len(job.footage) == 2 and not job.options.hype and not job.options.split  # ghép = câu chuyện, không chia
    r = client.post("/jobs", data={"footage": f"{a}\n{b}", "voice_only": "on", "target_language": "ko"})
    assert "MỘT video" in r.text


def test_montage_story_mode_prompt_and_length(tmp_path):
    """Ghép nhiều video (không tick ⚡): kể thành câu chuyện ~2 phút, không xếp gay cấn lên đầu, giữ tiếng gốc."""
    from app.director.fake import FakeDirector
    from app.director.tasks import make_plan, understand
    from app.styles import load_style
    from tests.test_director import make_analysis

    a = make_analysis(tmp_path, duration=600.0)  # 600s footage gồm 4 video
    from app.director.schemas import TimeRange

    u = understand(FakeDirector(), a)
    u = u.model_copy(update={"usable_range": TimeRange(start=0.0, end=600.0)})  # ghép nhiều video: dùng toàn bộ footage
    parts = [{"index": i + 1, "name": f"ep{i + 1}.mp4", "start": i * 150.0, "end": (i + 1) * 150.0} for i in range(4)]
    style = {**load_style("jp_telop"), "montage_parts": parts}
    clips = [{"source_start": 10.0 + 150 * i, "source_end": 14.0 + 150 * i, "highlight": i == 3} for i in range(4)]
    short = {**load("plan.json"), "clips": clips, "zooms": [], "emphasis": [], "sfx": [], "transitions": []}
    long_clips = [{"source_start": 150 * (i % 4) + 5 * (i // 4) + 1, "source_end": 150 * (i % 4) + 5 * (i // 4) + 5}
                  for i in range(28)]
    good = {**short, "clips": sorted(long_clips, key=lambda c: c["source_start"])}  # 28 × 4s = 112s
    d = FakeDirector(responses={"plan": [short, good]})
    plan = make_plan(d, a, u, style)
    prompt = d.calls[0]["prompt"]
    assert "MỘT CÂU CHUYỆN" in prompt and "120 giây" in prompt and "video 4 (ep4.mp4)" in prompt
    assert "CHUYỂN CẢNH LIÊN TỤC" not in prompt  # không tick ⚡ → không ép gay cấn lên đầu
    assert "ngắn hơn 100" in d.calls[1]["prompt"]  # lần đầu chỉ 16s → bị yêu cầu làm lại cho đủ ~2 phút
    starts = [c.source_start for c in plan.clips]
    assert starts == sorted(starts)  # giữ mạch câu chuyện, code không đảo
