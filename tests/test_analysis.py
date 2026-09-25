import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest

from app.analysis import ffmpeg
from app.analysis.scenes import Scene, detect_scenes, frame_times
from app.analysis.subjects import Box, FrameSubjects, detect_faces, main_subject_track
from app.analysis.transcribe import attempts, load_model, pick_language, transcribe

imageio_ffmpeg = pytest.importorskip("imageio_ffmpeg")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def test_audio_filter_uses_config():
    f = ffmpeg.audio_filter({"audio": {"target_lufs": -14, "true_peak": -1.5, "lra": 11, "denoise": "afftdn=nf=-25"}})
    assert f == "afftdn=nf=-25,loudnorm=I=-14:TP=-1.5:LRA=11"
    args = ffmpeg.clean_audio_args(Path("in.mp4"), Path("out.wav"), {"audio": {}})
    assert args[:3] == ["-i", "in.mp4", "-vn"] and "48000" in args


def test_frame_times_mixes_uniform_and_scene_starts():
    scenes = [Scene(index=0, start=0, end=5), Scene(index=1, start=5, end=12)]
    ts = frame_times(12, scenes, every_s=4)
    assert 0.2 in ts and 5.2 in ts and 2.0 in ts and 10.0 in ts
    assert all(b - a >= 0.5 for a, b in zip(ts, ts[1:]))
    assert len(frame_times(1000, scenes, every_s=1, max_frames=40)) == 40


def test_scene_detection_on_synthetic_video(tmp_path: Path):
    video = tmp_path / "v.mp4"
    subprocess.run([FFMPEG, "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=red:s=320x240:d=2:r=25",
                    "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2:r=25",
                    "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]",
                    "-pix_fmt", "yuv420p", str(video)], check=True)
    scenes = detect_scenes(video, duration=4.0)
    assert len(scenes) == 2 and scenes[1].start == pytest.approx(2.0, abs=0.1)
    ffmpeg.run(ffmpeg.frame_args(video, 1.0, tmp_path / "f.jpg", width=160), exe=FFMPEG)
    assert (tmp_path / "f.jpg").stat().st_size > 0


def test_detect_faces_on_blank_image():
    assert detect_faces(np.zeros((240, 320, 3), dtype=np.uint8)) == []


def test_subject_track_smooth_and_speed_limited():
    frames = [FrameSubjects(t=0.0, faces=[Box(x=0.1, y=0.4, w=0.1, h=0.2)]),
              FrameSubjects(t=0.5, faces=[]),
              FrameSubjects(t=1.0, faces=[Box(x=0.8, y=0.4, w=0.1, h=0.2), Box(x=0.0, y=0, w=0.05, h=0.05)])]
    track = main_subject_track(frames, smooth_window=1, max_pan_per_s=0.25)
    xs = [p[1] for p in track.points]
    assert xs[0] == pytest.approx(0.15) and xs[1] == pytest.approx(0.15)
    assert xs[2] == pytest.approx(0.15 + 0.125)  # bị giới hạn tốc độ lia
    assert track.face_count_max == 2


def test_pick_language():
    assert pick_language("ko", None, ["ko", "ja", "en"]) is None
    assert pick_language("zh", [("zh", 0.6), ("ja", 0.3), ("en", 0.1)], ["ko", "ja", "en"]) == "ja"


@dataclass
class FakeWord:
    start: float
    end: float
    word: str
    probability: float = 0.9


@dataclass
class FakeSeg:
    start: float
    end: float
    text: str
    words: list = field(default_factory=list)


@dataclass
class FakeInfo:
    language: str
    language_probability: float = 0.9
    duration: float = 3.0
    all_language_probs: list = field(default_factory=list)


class FakeModel:
    def __init__(self, name, device, compute_type):
        if device == "cuda":
            raise RuntimeError("CUDA không có")
        self.calls = []

    def transcribe(self, audio, language=None, **kw):
        self.calls.append(language)
        if language is None:
            return iter([]), FakeInfo("zh", all_language_probs=[("zh", 0.5), ("ja", 0.4)])
        return iter([FakeSeg(0, 1.2, " こんにちは", [FakeWord(0, 1.2, "こんにちは")])]), FakeInfo(language)


def test_transcribe_fallback_and_language_forcing():
    cfg = {"model": "large-v3", "device": "cuda", "compute_type": "int8_float32",
           "fallback": [{"device": "cpu", "model": "large-v3", "compute_type": "int8"}],
           "languages": ["ko", "ja", "en"]}
    assert len(attempts(cfg)) == 2
    model, used = load_model(cfg, FakeModel)
    assert used["device"] == "cpu"
    tr = transcribe(Path("a.wav"), cfg, FakeModel)
    assert tr.language == "ja" and tr.device == "cpu"
    assert tr.segments[0].text == "こんにちは" and tr.segments[0].words[0].word == "こんにちは"


def test_pipeline_end_to_end(tmp_path: Path, monkeypatch):
    from app.analysis import pipeline
    from app.analysis.transcribe import Segment, Transcript
    from app.capcut_writer.writer import VideoSource
    from app.jobs.job import Job

    video = tmp_path / "v.mp4"
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=320x240:d=6:r=25",
                    "-f", "lavfi", "-i", "sine=d=6", "-shortest", "-pix_fmt", "yuv420p", str(video)], check=True)
    monkeypatch.setattr(pipeline, "probe_video", lambda p, exe=None: VideoSource(p, 320, 240, 6_000_000, True))
    monkeypatch.setattr(ffmpeg, "ffmpeg_exe", lambda: FFMPEG)
    fake = lambda wav: Transcript(language="en", language_probability=1, duration=6, model="fake", device="cpu",
                                  segments=[Segment(start=0, end=1, text="hello")])
    job = Job.create(tmp_path / "jobs", [video], job_id="j1")
    result = pipeline.run_analysis(job, tmp_path / "jobs", transcribe_fn=fake)
    out = tmp_path / "jobs" / "j1" / "analysis"
    for name in ("transcript.json", "scenes.json", "subjects.json", "frames.json"):
        assert (out / name).is_file()
    assert (out / "audio" / "clean_00.wav").stat().st_size > 0
    assert not (out / "audio" / "whisper_00.wav").exists()
    assert result["frames"] and (out / result["frames"][0]["file"]).is_file()
    assert result["transcripts"][0]["segments"][0]["text"] == "hello"
