"""Bước "Phân tích" của job: làm sạch âm thanh, nhận dạng thoại, dò cảnh, trích khung, dò chủ thể.

Kết quả trong jobs/<job_id>/analysis/:
    audio/clean_NN.wav     âm thanh đã lọc ồn + chuẩn hóa (đưa vào CapCut thay tiếng gốc)
    audio/light_NN.wav     chỉ chuẩn hóa độ to, lọc ồn rất nhẹ — giữ âm thanh hiện trường (vlog)
    audio_events.json      [{footage, events[{start, end, kind: laugh|cheer|shout|marker, strength}]}]
    transcript.json        [{footage, language, segments[words]}]
    scenes.json            [{footage, duration, width, height, scenes[]}]
    frames/NN_ttt.jpg      khung hình nhỏ gửi cho đạo diễn
    subjects.json          [{footage, points[(t, cx, cy)], face_count_max, faces[[t, [[x,y,w,h,motion]...]]]}]
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
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


def _elapsed(t0: float) -> str:
    sec = int(time.monotonic() - t0)
    return f"{sec // 60}:{sec % 60:02d}"


def _in_thread(pool: ThreadPoolExecutor, fn, *args):
    """Chạy fn ở luồng phụ, gắn đúng job cho luồng đó (nút ⏹️ Dừng vẫn có tác dụng khi luồng ghi nhật ký)."""
    from app.jobs import stop

    job_id = stop.current()

    def call():
        stop.set_current(job_id)
        try:
            return fn(*args)
        finally:
            stop.set_current(None)

    return pool.submit(call)


def run_analysis(job: Job, jobs_root: Path, *, transcribe_fn: Callable = transcribe,
                 progress: Callable[[str], None] = lambda msg: None) -> dict:
    """Chủ dự án 11/10 "phân tích footage lâu": các phần độc lập chạy SONG SONG — nhận dạng thoại (GPU) chạy cùng lúc
    với dò cảnh + trích khung + dò mặt (CPU) và với 2 bản làm sạch âm thanh; khung hình trích nhiều cái một lúc.
    Mỗi phần ghi thời gian chạy vào nhật ký để biết chỗ nào chậm."""
    cfg = config.load("analysis")
    out = job.dir(jobs_root) / "analysis"
    (out / "audio").mkdir(parents=True, exist_ok=True)
    (out / "frames").mkdir(parents=True, exist_ok=True)
    transcripts, scenes_all, subjects_all, frames_all, events_all = [], [], [], [], []
    workers = max(1, int((cfg.get("parallel") or {}).get("frame_workers", 4)))

    for i, src in enumerate(job.footage):
        src = Path(src)
        tag = f"{i:02d}"
        progress(f"Đọc thông tin video {src.name}")
        info = probe_video(src, cfg.get("ffprobe") or None)
        duration = info.duration / 1_000_000
        t_all = time.monotonic()
        films = bool(getattr(job.options, "films", False))  # content nhiều phim: tiếng phim tắt hẳn
        fast = films and bool(config.load("films").get("fast", True))  # chế độ nhanh: không nghe thoại
        with ThreadPoolExecutor(max_workers=4) as pool:
            cleaning = []
            listen = info.has_audio and not fast
            if listen:
                whisper_wav = out / "audio" / f"whisper_{tag}.wav"
                wav_job = _in_thread(pool, ffmpeg.run, ffmpeg.whisper_audio_args(src, whisper_wav))
                progress("Làm sạch âm thanh (lọc ồn, chuẩn hóa độ to) — chạy nền")
                cleaning = [] if films else [_in_thread(pool, ffmpeg.run, ffmpeg.clean_audio_args(src, out / "audio" / f"clean_{tag}.wav", cfg)),
                            _in_thread(pool, ffmpeg.run, ffmpeg.clean_audio_args(src, out / "audio" / f"light_{tag}.wav",
                                                                               cfg, light=True))]
            fr = cfg.get("frames", {})
            max_frames = int(fr.get("max_frames_review", 80) if getattr(job.options, "review", False)
                             else fr.get("max_frames", 40))
            if films:  # AI tìm cảnh bằng mắt → nhiều khung hình mỗi phim
                max_frames = int(config.load("films").get("frames_per_film", 180))
            every_s = None
            if getattr(job.options, "sell", False):  # bán content (15/10): khung dày để AI đọc được phụ đề in trên hình
                scfg = config.load("sell") or {}
                max_frames, every_s = int(scfg.get("analysis_frames", 70)), float(scfg.get("frame_every_s", 1.0))
                if getattr(job.options, "ideas", False):  # ý tưởng từ video dài (17/10): khung rải cả video dài
                    icfg = config.load("ideas") or {}
                    max_frames, every_s = int(icfg.get("analysis_frames", 600)), float(icfg.get("frame_every_s", 5.0))
            o = job.options  # bỏ phần không cần cho chế độ này (chủ dự án 11/10: "chậm quá")
            need_scenes = not getattr(o, "vi_sub", False)             # phụ đề tiếng Việt: chỉ cần lời thoại
            need_faces = not (getattr(o, "vi_sub", False) or getattr(o, "voice_only", False) or films
                              or getattr(o, "ideas", False))  # giữ khung gốc
            video_job = _in_thread(pool, _video_part, src, i, tag, duration, info, out, cfg, workers, progress,
                                   max_frames if need_scenes else 6, need_scenes, need_faces, every_s)
            if listen:
                wav_job.result()
                tr, events = _audio_part(job, whisper_wav, transcribe_fn, cfg, progress)
                transcripts.append({"footage": i, **tr.model_dump()})
                events_all.append({"footage": i, "events": events})
                whisper_wav.unlink(missing_ok=True)
            else:
                transcripts.append({"footage": i, "language": None, "segments": []})
                events_all.append({"footage": i, "events": []})
            scenes, frames, subjects = video_job.result()
            for c in cleaning:
                c.result()
        scenes_all.append(scenes)
        frames_all.extend(frames)
        subjects_all.append(subjects)
        progress(f"Phân tích xong {src.name} sau {_elapsed(t_all)} (video dài {duration / 60:.1f} phút)")

    _write(out / "transcript.json", transcripts)
    _write(out / "scenes.json", scenes_all)
    _write(out / "subjects.json", subjects_all)
    _write(out / "frames.json", frames_all)
    _write(out / "audio_events.json", events_all)
    return {"transcripts": transcripts, "scenes": scenes_all, "subjects": subjects_all, "frames": frames_all}


def _audio_part(job: Job, whisper_wav: Path, transcribe_fn: Callable, cfg: dict, progress):
    from app.jobs.limits import group_slot

    def gpu_busy(what: str) -> None:
        progress(f"Đang đợi lượt {what} — video khác đang dùng GPU…")

    with group_slot("gpu", on_wait=gpu_busy):  # chỉ 1 video dùng GPU một lúc
        t0 = time.monotonic()
        progress("Nhận dạng thoại (có thể mất vài phút)")
        if getattr(job.options, "vi_sub", False):  # phụ đề tiếng Việt: nhận MỌI ngôn ngữ, không ép ko/ja/en
            tr = transcribe_fn(whisper_wav, cfg={**config.load("whisper"), "languages": []}, log=progress)
        else:
            tr = transcribe_fn(whisper_wav, log=progress)
        progress(f"Nhận dạng thoại xong sau {_elapsed(t0)} ({len(tr.segments)} câu, {tr.device or '?'})")
    progress("Dò tiếng cười / hò reo / cao trào trong âm thanh")
    try:
        from app.analysis.audio_events import analyze_audio_events

        events = analyze_audio_events(whisper_wav, tr.model_dump()["segments"], cfg.get("audio_events") or None)
    except Exception as exc:  # không để lỗi phụ làm hỏng cả bước phân tích
        progress(f"Bỏ qua dò sự kiện âm thanh: {exc}")
        events = []
    return tr, events


def _video_part(src: Path, i: int, tag: str, duration: float, info, out: Path, cfg: dict, workers: int, progress,
                max_frames: int = 40, need_scenes: bool = True, need_faces: bool = True, every_s: float | None = None):
    """Dò cảnh → trích khung (nhiều khung một lúc) → dò mặt. Chạy song song với nhận dạng thoại.
    need_scenes / need_faces = False: bỏ qua phần chế độ này không dùng (cả video là một cảnh / không dò mặt)."""
    from app.analysis.scenes import Scene

    t0 = time.monotonic()
    if need_scenes:
        progress("Dò cảnh")
        sc = cfg.get("scenes", {})
        scenes = detect_scenes(src, sc.get("threshold", 27.0), sc.get("min_scene_len_s", 0.6), duration,
                               frame_skip=int(sc.get("frame_skip", 1)), progress=progress)
        progress(f"Dò cảnh xong sau {_elapsed(t0)} ({len(scenes)} cảnh)")
    else:
        scenes = [Scene(index=0, start=0.0, end=duration)]
    scenes_rec = {"footage": i, "path": src.as_posix(), "duration": duration, "width": info.width,
                  "height": info.height, "scenes": [s.model_dump() for s in scenes]}

    progress("Trích khung hình")
    fr = cfg.get("frames", {})
    times = frame_times(duration, scenes, every_s or fr.get("every_s", 4.0), max_frames)

    def grab(t: float):
        dst = out / "frames" / f"{tag}_{t:08.2f}.jpg"
        ok = ffmpeg.extract_frame(src, t, dst, fr.get("width", 480), fr.get("jpeg_quality", 5))
        return t, dst, ok

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(grab, times))
    frames = [{"footage": i, "t": t, "file": dst.relative_to(out).as_posix()} for t, dst, ok in results if ok]
    skipped = [t for t, _, ok in results if not ok]
    if skipped:
        progress(f"Bỏ qua {len(skipped)} khung hình không trích được (giây {', '.join(f'{x:.1f}' for x in skipped[:5])}"
                 f"{'…' if len(skipped) > 5 else ''}) — thường do phần cuối file chỉ có tiếng, không có hình.")
    if not frames:
        raise RuntimeError(f"Không trích được khung hình nào từ {src.name}. File video có thể bị hỏng hoặc "
                           "dùng định dạng lạ — thử xuất lại file bằng CapCut / HandBrake (H.264 MP4) rồi chạy lại.")

    if not need_faces:
        return scenes_rec, frames, {"footage": i, "points": [], "face_count_max": 0, "faces": []}
    t1 = time.monotonic()
    progress("Dò khuôn mặt / chủ thể")
    sj = cfg.get("subjects", {})
    faces = scan_video(src, sj.get("sample_every_s", 0.5), sj.get("min_face_frac", 0.06), progress=progress)
    track = main_subject_track(faces, sj.get("smooth_window", 5), sj.get("max_pan_per_s", 0.25))
    progress(f"Dò khuôn mặt xong sau {_elapsed(t1)}")
    return scenes_rec, frames, {"footage": i, **track.model_dump(), "faces": faces_compact(faces)}
