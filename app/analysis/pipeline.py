"""Bước "Phân tích" của job: làm sạch âm thanh, nhận dạng thoại, dò cảnh, trích khung, dò chủ thể.

Kết quả trong jobs/<job_id>/analysis/:
    audio/clean_NN.wav     âm thanh đã lọc ồn + chuẩn hóa (đưa vào CapCut thay tiếng gốc)
    transcript.json        [{footage, language, segments[words]}]
    scenes.json            [{footage, duration, width, height, scenes[]}]
    frames/NN_ttt.jpg      khung hình nhỏ gửi cho đạo diễn
    subjects.json          [{footage, points[(t, cx, cy)], face_count_max, faces[[t, [[x,y,w,h,motion]...]]]}]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from app import config
from app.analysis import ffmpeg
from app.analysis.scenes import detect_scenes, frame_times
from app.analysis.subjects import faces_compact, main_subject_track, scan_video
from app.analysis.transcribe import transcribe
from app.capcut_writer.media import probe_video
from app.jobs.job import Job


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_analysis(job: Job, jobs_root: Path, *, transcribe_fn: Callable = transcribe,
                 progress: Callable[[str], None] = lambda msg: None) -> dict:
    cfg = config.load("analysis")
    out = job.dir(jobs_root) / "analysis"
    (out / "audio").mkdir(parents=True, exist_ok=True)
    (out / "frames").mkdir(parents=True, exist_ok=True)
    transcripts, scenes_all, subjects_all, frames_all = [], [], [], []

    for i, src in enumerate(job.footage):
        src = Path(src)
        tag = f"{i:02d}"
        progress(f"Đọc thông tin video {src.name}")
        info = probe_video(src, cfg.get("ffprobe") or None)
        duration = info.duration / 1_000_000

        if info.has_audio:
            progress("Làm sạch âm thanh (lọc ồn, chuẩn hóa độ to)")
            ffmpeg.run(ffmpeg.clean_audio_args(src, out / "audio" / f"clean_{tag}.wav", cfg))
            whisper_wav = out / "audio" / f"whisper_{tag}.wav"
            ffmpeg.run(ffmpeg.whisper_audio_args(src, whisper_wav))
            progress("Nhận dạng thoại (có thể mất vài phút)")
            tr = transcribe_fn(whisper_wav, log=progress)
            transcripts.append({"footage": i, **tr.model_dump()})
            whisper_wav.unlink(missing_ok=True)
        else:
            transcripts.append({"footage": i, "language": None, "segments": []})

        progress("Dò cảnh")
        sc = cfg.get("scenes", {})
        scenes = detect_scenes(src, sc.get("threshold", 27.0), sc.get("min_scene_len_s", 0.6), duration)
        scenes_all.append({"footage": i, "path": src.as_posix(), "duration": duration, "width": info.width,
                           "height": info.height, "scenes": [s.model_dump() for s in scenes]})

        progress("Trích khung hình")
        fr = cfg.get("frames", {})
        for t in frame_times(duration, scenes, fr.get("every_s", 4.0), fr.get("max_frames", 40)):
            dst = out / "frames" / f"{tag}_{t:08.2f}.jpg"
            ffmpeg.run(ffmpeg.frame_args(src, t, dst, fr.get("width", 480), fr.get("jpeg_quality", 5)))
            frames_all.append({"footage": i, "t": t, "file": dst.relative_to(out).as_posix()})

        progress("Dò khuôn mặt / chủ thể")
        sj = cfg.get("subjects", {})
        faces = scan_video(src, sj.get("sample_every_s", 0.5), sj.get("min_face_frac", 0.06))
        track = main_subject_track(faces, sj.get("smooth_window", 5), sj.get("max_pan_per_s", 0.25))
        subjects_all.append({"footage": i, **track.model_dump(), "faces": faces_compact(faces)})

    _write(out / "transcript.json", transcripts)
    _write(out / "scenes.json", scenes_all)
    _write(out / "subjects.json", subjects_all)
    _write(out / "frames.json", frames_all)
    return {"transcripts": transcripts, "scenes": scenes_all, "subjects": subjects_all, "frames": frames_all}
