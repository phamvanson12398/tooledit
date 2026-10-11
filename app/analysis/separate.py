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


def torch_device() -> str | None:
    """Demucs chạy bằng gì: "cuda" (GPU) / "cpu" / None (chưa cài torch). pip install demucs trên Windows kéo về PyTorch
    bản CHỈ CPU → tách nhạc rất chậm; install_gpu_torch.bat đổi sang bản GPU."""
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return None


def demucs_cmd(audio: Path, out_dir: Path, model: str = "htdemucs", device: str = "auto", shifts: int = 0) -> list[str]:
    """shifts > 1: Demucs tách nhiều lần với độ lệch ngẫu nhiên rồi lấy trung bình — sạch hơn, chậm hơn ~shifts lần
    (cờ --shifts, đối chiếu demucs 4.1.0)."""
    cmd = [sys.executable, "-m", "demucs.separate", "--two-stems", "vocals", "-n", model, "-o", str(out_dir),
           "--filename", "{stem}.{ext}"]
    if device and device != "auto":
        cmd += ["-d", device]
    if shifts and shifts > 1:
        cmd += ["--shifts", str(int(shifts))]
    return cmd + [str(audio)]


def separate_bgm(src: Path, dst: Path, *, model: str = "htdemucs", device: str = "auto", ffmpeg_exe: str | None = None,
                 run=subprocess.run, vocals_dst: Path | None = None) -> Path:
    """Ghi nhạc nền (đã bỏ giọng nói) của video src ra dst (.wav). vocals_dst: giữ luôn phần GIỌNG NÓI sạch (làm giọng
    mẫu cho OmniVoice clone). Lỗi → RuntimeError có lời nhắn tiếng Việt."""
    if not available():
        raise RuntimeError(INSTALL_HINT)
    from app.analysis import ffmpeg

    with tempfile.TemporaryDirectory(prefix="bgm_") as tmp:
        tmp = Path(tmp)
        raw = tmp / "goc.wav"  # âm thanh gốc chưa lọc ồn / chuẩn hóa (giữ nguyên chất nhạc)
        ffmpeg.run(["-i", str(src), "-vn", "-ac", "2", "-ar", "44100", str(raw)], exe=ffmpeg_exe)
        from app.tts.voices import utf8_env

        r = run(demucs_cmd(raw, tmp / "out", model, device), capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=utf8_env())
        out = tmp / "out" / model / "no_vocals.wav"
        if getattr(r, "returncode", 1) != 0 or not out.is_file():
            raise RuntimeError(f"Demucs không tách được nhạc nền: {(getattr(r, 'stderr', '') or '')[-400:]}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out), str(dst))
        voc = tmp / "out" / model / "vocals.wav"
        if vocals_dst is not None and voc.is_file():
            shutil.move(str(voc), str(vocals_dst))
    return dst


RATE = 44100


def _decode_stereo(src: Path, ffmpeg_exe: str | None = None, start: float | None = None, dur: float | None = None):
    """Âm thanh (một đoạn) của video → int16 stereo 44.1 kHz; chỉ đọc đúng đoạn cần, không nạp cả phim vào bộ nhớ."""
    import numpy as np

    from app.analysis.ffmpeg import ffmpeg_exe as find

    seek = (["-ss", f"{start:.3f}"] if start else []) + (["-t", f"{dur:.3f}"] if dur else [])
    r = subprocess.run([ffmpeg_exe or find(), "-hide_banner", "-loglevel", "error", *seek, "-i", str(src), "-vn",
                        "-ac", "2", "-ar", str(RATE), "-f", "s16le", "-"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"Không đọc được âm thanh video: {r.stderr.decode('utf-8', 'replace')[-300:]}")
    return np.frombuffer(r.stdout, dtype=np.int16).reshape(-1, 2)


def _write_stereo(path: Path, pcm) -> None:
    import wave

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.astype("int16").tobytes())


def _read_stereo(path: Path):
    import wave

    import numpy as np

    with wave.open(str(path), "rb") as w:
        ch, width, n = w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if width != 2:
        raise RuntimeError(f"Demucs ghi wav {width * 8}-bit, tool cần 16-bit (mặc định của demucs 4.1.0)")
    pcm = np.frombuffer(raw, dtype=np.int16).reshape(-1, ch)
    return pcm if ch == 2 else np.repeat(pcm, 2, axis=1)


def _write_placed(path: Path, sep, layout: list[dict], total_s: float) -> None:
    """Ghi file dài bằng video: im lặng, chỉ các đoạn trong layout là tiếng đã tách — ghi dần, không giữ cả file."""
    import wave

    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    chunk = np.zeros((RATE * 10, 2), dtype=np.int16).tobytes()  # 10 giây im lặng

    def silence(w, frames: int) -> None:
        while frames > 0:
            k = min(frames, RATE * 10)
            w.writeframes(chunk[:k * 4])
            frames -= k

    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        pos = 0
        for seg in layout:
            a, o = int(seg["start"] * RATE), int(seg["offset"] * RATE)
            piece = sep[o:o + int((seg["end"] - seg["start"]) * RATE)]
            silence(w, a - pos)
            w.writeframes(piece.astype(np.int16).tobytes())
            pos = a + len(piece)
        silence(w, int(total_s * RATE) - pos)


def merge_ranges(ranges: list[tuple[float, float]], join_s: float = 1.0) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for a, b in sorted(ranges):
        if out and a <= out[-1][1] + join_s:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(round(a, 3), round(b, 3)) for a, b in out]


def separate_ranges(src: Path, ranges: list[tuple[float, float]], bgm_dst: Path, vocals_dst: Path, *,
                    total_s: float, concat_vocals_dst: Path | None = None, model: str = "htdemucs",
                    device: str = "auto", ffmpeg_exe: str | None = None, run=subprocess.run, pad_s: float = 1.0,
                    gap_s: float = 0.6, shifts: int = 0) -> list[dict]:
    """Chỉ tách nhạc ở các ĐOẠN cần dùng (chủ dự án 11/10: "tách nhạc nền lâu cực") — vd các tình huống đã duyệt của
    lồng tiếng nhân vật, thay vì cả bộ phim. Các đoạn (thêm pad_s mỗi bên làm ngữ cảnh) nối thành MỘT file, tách một
    lần, rồi đặt lại đúng giây gốc trong bgm_dst / vocals_dst dài bằng video (total_s; ngoài các đoạn là im lặng) → phần
    dựng phía sau dùng như bản tách cả video. concat_vocals_dst: giữ file giọng nói nối liền (ngắn) để nhận dạng lại thoại.
    Trả bố cục [{start, end, offset}] (offset = giây trong file nối ứng với `start`)."""
    import numpy as np

    if not available():
        raise RuntimeError(INSTALL_HINT)
    layout, parts, pos = [], [], 0
    gap = np.zeros((int(gap_s * RATE), 2), dtype=np.int16)
    for a, b in merge_ranges([(max(0.0, x), min(total_s, y)) for x, y in ranges if y > x]):
        pa = max(0.0, a - pad_s)
        piece = _decode_stereo(src, ffmpeg_exe, pa, (b + pad_s) - pa)
        if not len(piece):
            continue
        b = min(b, pa + len(piece) / RATE)
        layout.append({"start": a, "end": round(b, 3), "offset": round((pos + int((a - pa) * RATE)) / RATE, 4)})
        parts += [piece, gap]
        pos += len(piece) + len(gap)
    if not layout:
        raise RuntimeError("Không có đoạn nào cần tách nhạc")
    from app.tts.voices import utf8_env

    with tempfile.TemporaryDirectory(prefix="bgm_") as tmp:
        tmp = Path(tmp)
        joined = tmp / "doan.wav"
        _write_stereo(joined, np.concatenate(parts))
        r = run(demucs_cmd(joined, tmp / "out", model, device, shifts), capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=utf8_env())
        out_bgm, out_voc = tmp / "out" / model / "no_vocals.wav", tmp / "out" / model / "vocals.wav"
        if getattr(r, "returncode", 1) != 0 or not out_bgm.is_file():
            raise RuntimeError(f"Demucs không tách được nhạc nền: {(getattr(r, 'stderr', '') or '')[-400:]}")
        _write_placed(bgm_dst, _read_stereo(out_bgm), layout, total_s)
        if out_voc.is_file():
            _write_placed(vocals_dst, _read_stereo(out_voc), layout, total_s)
            if concat_vocals_dst is not None:
                concat_vocals_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(out_voc, concat_vocals_dst)
    return layout


def to_source_time(t: float, layout: list[dict]) -> float | None:
    """Giây trong file nối (concat_vocals_dst) → giây gốc của video; nằm ngoài các đoạn (phần đệm / khoảng lặng) → None."""
    for seg in layout:
        if seg["offset"] - 0.05 <= t <= seg["offset"] + (seg["end"] - seg["start"]) + 0.05:
            return round(seg["start"] + (t - seg["offset"]), 3)
    return None

