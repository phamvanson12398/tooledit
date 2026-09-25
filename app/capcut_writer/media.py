"""Đọc thông tin file media bằng ffprobe (đi kèm FFmpeg)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .writer import VideoSource


def ffprobe_json(path: Path, ffprobe: str | None = None) -> dict:
    exe = ffprobe or shutil.which("ffprobe")
    if not exe:
        raise RuntimeError("Không tìm thấy ffprobe. Cài FFmpeg và thêm vào PATH (xem docs/SETUP_WINDOWS.md).")
    out = subprocess.run(
        [exe, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=True, encoding="utf-8",
    ).stdout
    return json.loads(out)


def video_source_from_probe(path: Path, info: dict) -> VideoSource:
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError(f"{path} không có luồng video")
    width, height = int(video["width"]), int(video["height"])
    rotation = _rotation(video)
    if rotation in (90, 270):
        width, height = height, width
    duration = float(info.get("format", {}).get("duration") or video.get("duration") or 0)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    return VideoSource(Path(path), width, height, int(round(duration * 1_000_000)), has_audio)


def _rotation(stream: dict) -> int:
    tags = stream.get("tags") or {}
    if "rotate" in tags:
        return abs(int(float(tags["rotate"]))) % 360
    for side in stream.get("side_data_list", []) or []:
        if "rotation" in side:
            return abs(int(float(side["rotation"]))) % 360
    return 0


def probe_video(path: Path, ffprobe: str | None = None) -> VideoSource:
    return video_source_from_probe(Path(path), ffprobe_json(Path(path), ffprobe))


def probe_duration(path: Path, ffprobe: str | None = None) -> int:
    info = ffprobe_json(Path(path), ffprobe)
    return int(round(float(info["format"]["duration"]) * 1_000_000))
