"""Tách NHẠC NỀN khỏi GIỌNG NÓI của video gốc (chế độ "Chỉ thay tiếng" + "Giữ nhạc nền gốc", chủ dự án yêu cầu 07/10).

Dùng Demucs (https://github.com/facebookresearch/demucs, giấy phép MIT, chạy trên máy). Lệnh đã đối chiếu với mã nguồn
demucs 4.1.0 (demucs/separate.py): `python -m demucs.separate --two-stems vocals -n htdemucs -o OUT
--filename "{stem}.{ext}" FILE` → OUT/htdemucs/vocals.wav + OUT/htdemucs/no_vocals.wav (no_vocals = nhạc + tiếng nền).
Lần đầu Demucs tự tải model (~80 MB). Không có GPU vẫn chạy được trên CPU (chậm hơn, vài phút cho video 1–2 phút).
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

INSTALL_HINT = ("Chưa cài Demucs (công cụ tách nhạc nền khỏi giọng nói). Cài một lần trong PowerShell: "
                ".\\.venv\\Scripts\\python -m pip install -r requirements-bgm.txt  (xem docs/SETUP_WINDOWS.md).")


def available() -> bool:
    return importlib.util.find_spec("demucs") is not None


def demucs_cmd(audio: Path, out_dir: Path, model: str = "htdemucs", device: str = "auto") -> list[str]:
    cmd = [sys.executable, "-m", "demucs.separate", "--two-stems", "vocals", "-n", model, "-o", str(out_dir),
           "--filename", "{stem}.{ext}"]
    if device and device != "auto":
        cmd += ["-d", device]
    return cmd + [str(audio)]


def separate_bgm(src: Path, dst: Path, *, model: str = "htdemucs", device: str = "auto", ffmpeg_exe: str | None = None,
                 run=subprocess.run) -> Path:
    """Ghi nhạc nền (đã bỏ giọng nói) của video src ra dst (.wav). Lỗi → RuntimeError có lời nhắn tiếng Việt."""
    if not available():
        raise RuntimeError(INSTALL_HINT)
    from app.analysis import ffmpeg

    with tempfile.TemporaryDirectory(prefix="bgm_") as tmp:
        tmp = Path(tmp)
        raw = tmp / "goc.wav"  # âm thanh gốc chưa lọc ồn / chuẩn hóa (giữ nguyên chất nhạc)
        ffmpeg.run(["-i", str(src), "-vn", "-ac", "2", "-ar", "44100", str(raw)], exe=ffmpeg_exe)
        r = run(demucs_cmd(raw, tmp / "out", model, device), capture_output=True, text=True, encoding="utf-8",
                errors="replace")
        out = tmp / "out" / model / "no_vocals.wav"
        if getattr(r, "returncode", 1) != 0 or not out.is_file():
            raise RuntimeError(f"Demucs không tách được nhạc nền: {(getattr(r, 'stderr', '') or '')[-400:]}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out), str(dst))
    return dst
