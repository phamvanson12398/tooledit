"""Gọi FFmpeg: làm sạch âm thanh và trích khung hình."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app import config


def ffmpeg_exe() -> str:
    exe = config.load("analysis").get("ffmpeg") or "ffmpeg"
    found = shutil.which(exe) or (exe if Path(exe).is_file() else None)
    if not found:
        raise RuntimeError("Không tìm thấy FFmpeg. Cài FFmpeg và thêm vào PATH (xem docs/SETUP_WINDOWS.md).")
    return found


def run(args: list[str], exe: str | None = None) -> None:
    cmd = [exe or ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg lỗi: {result.stderr.strip()[-800:]}")


def audio_filter(cfg: dict | None = None, denoise_key: str = "denoise") -> str:
    a = (cfg or config.load("analysis")).get("audio", {})
    denoise = a.get(denoise_key, "afftdn=nf=-25" if denoise_key == "denoise" else "")
    loud = f"loudnorm=I={a.get('target_lufs', -14)}:TP={a.get('true_peak', -1.5)}:LRA={a.get('lra', 11)}"
    return ",".join(x for x in (denoise, loud) if x)


def clean_audio_args(src: Path, dst: Path, cfg: dict | None = None, light: bool = False) -> list[str]:
    """Âm thanh đã lọc ồn + chuẩn hóa độ to, WAV 48 kHz stereo để đưa vào CapCut.
    light=True: lọc ồn rất nhẹ (hoặc không), giữ âm thanh hiện trường — dùng cho vlog / du lịch."""
    af = audio_filter(cfg, "denoise_light" if light else "denoise")
    return ["-i", str(src), "-vn", "-af", af, "-ar", "48000", "-ac", "2", str(dst)]


def whisper_audio_args(src: Path, dst: Path) -> list[str]:
    """WAV 16 kHz mono cho nhận dạng thoại."""
    return ["-i", str(src), "-vn", "-ar", "16000", "-ac", "1", str(dst)]


def frame_args(src: Path, at_s: float, dst: Path, width: int = 480, quality: int = 5) -> list[str]:
    return ["-ss", f"{at_s:.3f}", "-i", str(src), "-frames:v", "1", "-vf", f"scale={width}:-2",
            "-q:v", str(quality), str(dst)]
