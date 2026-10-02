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
    # format=yuvj420p: bộ mã JPEG của FFmpeg mới từ chối ảnh "dải màu hẹp" / 10-bit HDR (điện thoại) nếu không đổi
    return ["-ss", f"{at_s:.3f}", "-i", str(src), "-frames:v", "1", "-an", "-sn",
            "-vf", f"scale={width}:-2:out_range=full,format=yuvj420p", "-q:v", str(quality), str(dst)]


def extract_frame(src: Path, at_s: float, dst: Path, width: int = 480, quality: int = 5,
                  exe: str | None = None) -> bool:
    """Trích 1 khung hình; mốc rơi sau khung hình cuối (tiếng dài hơn hình, file quay điện thoại...) thì lùi lại
    vài lần. Trả False nếu không lấy được (bỏ qua khung này, không làm hỏng cả bước phân tích)."""
    dst.unlink(missing_ok=True)
    last_err = None
    for back in (0.0, 0.5, 1.5, 4.0):
        t = max(0.0, at_s - back)
        try:
            run(frame_args(src, t, dst, width, quality), exe=exe)
        except RuntimeError as exc:
            last_err = exc
        if dst.is_file() and dst.stat().st_size > 0:
            return True
        if t == 0.0:
            break
    if last_err is not None and at_s < 1.0:  # lỗi ngay từ đầu video → không phải do mốc cuối, báo thật
        raise last_err
    return False
