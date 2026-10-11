"""Giọng AI bằng OmniVoice (chủ dự án yêu cầu 11/10): đọc thoại thay cho chủ dự án tự thu.

- Mỗi nhân vật (DubLine.speaker; không có thì "Người dẫn") một giọng:
  "design" = mô tả giọng (gender / age / pitch… — AI đề xuất trong `cast`), "auto" = OmniVoice tự chọn,
  "clone" = clone từ chính giọng nhân vật trong video gốc (3–10 giây, cắt từ phần giọng nói đã tách bằng Demucs) —
  CHỈ khi chủ dự án xác nhận có quyền dùng giọng đó.
- Mỗi câu đọc vừa khít thời lượng câu thoại gốc (`duration`) để khớp miệng; ghi thẳng voice/videoNN_dubMM.wav nên phần
  dựng phía sau chạy như voice tự thu.
- OmniVoice chạy ở tiến trình riêng (app/tts/omnivoice_worker.py) bằng python của môi trường đã cài omnivoice.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WORKER = Path(__file__).with_name("omnivoice_worker.py")
ROOT = Path(__file__).resolve().parents[2]
ENV_DIR = ROOT / "omnivoice-env"  # install_omnivoice.bat cài OmniVoice vào đây; tool tự tìm, không cần sửa config
NARRATOR = "Người dẫn"
INSTALL_HOW = ("Cách dễ nhất: tắt tool, nhấp đúp file install_omnivoice.bat trong thư mục tool (tự cài, 10–30 phút), "
               "rồi mở lại start.bat. Chi tiết: docs/SETUP_WINDOWS.md mục \"OmniVoice\".")
INSTALL_HINT = "Chưa chạy được OmniVoice. " + INSTALL_HOW


def voice_key(line) -> str:
    return (line.speaker or "").strip() or NARRATOR


def default_voices(scripts: dict, saved: dict | None = None) -> dict[str, dict]:
    """Giọng từng nhân vật: đã lưu (saved) hoặc theo đề xuất `cast` của AI (mô tả giọng), không có thì "auto"."""
    saved = saved or {}
    out: dict[str, dict] = {}
    for _, script in sorted(scripts.items()):
        cast = {c.speaker.strip(): c for c in script.cast}
        for ln in script.lines:
            k = voice_key(ln)
            if k in out:
                continue
            c = cast.get(k)
            out[k] = saved.get(k) or {"mode": "design" if c and c.instruct else "auto",
                                      "instruct": c.instruct if c else "", "note_vi": c.note_vi if c else ""}
    return out


def pick_reference(lines: list, speaker: str, min_s: float = 3.0, max_s: float = 10.0) -> tuple[float, float] | None:
    """Đoạn giọng gốc làm mẫu clone cho một nhân vật: câu thoại gốc dài nhất trong 3–10 giây; không có thì gộp các câu
    liền nhau của nhân vật đó cho đủ 3 giây; vẫn không đủ thì lấy câu dài nhất (cắt ≤ max_s)."""
    spans = sorted((ln.source_start, ln.source_end) for ln in lines if voice_key(ln) == speaker
                   and ln.source_end > ln.source_start)
    if not spans:
        return None
    good = [s for s in spans if min_s <= s[1] - s[0] <= max_s]
    if good:
        return max(good, key=lambda s: s[1] - s[0])
    for k in range(len(spans)):  # gộp các câu liền nhau (cách < 1 giây) cho đủ dài
        a, b = spans[k]
        for a2, b2 in spans[k + 1:]:
            if a2 - b > 1.0 or b2 - a > max_s:
                break
            b = b2
        if b - a >= min_s:
            return a, b
    a, b = max(spans, key=lambda s: s[1] - s[0])
    return a, min(b, a + max_s)


def ref_text(segments: list[dict], a: float, b: float) -> str:
    """Lời thoại gốc (transcript) trong đoạn giọng mẫu — đưa kèm để OmniVoice khỏi phải tự nhận dạng."""
    return " ".join(s["text"].strip() for s in segments if s["end"] > a + 0.05 and s["start"] < b - 0.05).strip()


def cut_reference(audio: Path, a: float, b: float, dst: Path, exe: str | None = None) -> Path:
    from app.analysis import ffmpeg

    dst.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg.run(["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(audio), "-vn", "-ac", "1", "-ar", "24000", str(dst)],
               exe=exe)
    return dst


def build_items(script, video_index: int, voice_dir: Path, language: str, windows: list | None,
                fit_duration: bool = True, only: set[int] | None = None) -> list[dict]:
    """Danh sách câu cần đọc: text, giọng (nhân vật), thời lượng mục tiêu (= chỗ trống câu gốc), file ra."""
    items = []
    for i, ln in enumerate(script.lines, 1):
        if only is not None and i not in only:
            continue
        win = windows[i - 1] if windows and i - 1 < len(windows) else None
        dur = round(float(win[1]), 2) if (fit_duration and win and win[1] > 0.3) else None
        items.append({"text": ln.text.strip(), "language": language, "voice": voice_key(ln), "duration": dur,
                      "out": str(voice_dir / f"video{video_index:02d}_dub{i:02d}.wav")})
    return items


def env_python(env_dir: Path = ENV_DIR) -> Path | None:
    """python của môi trường install_omnivoice.bat đã tạo (Windows: Scripts\\python.exe; Linux/Mac: bin/python)."""
    for p in (env_dir / "Scripts" / "python.exe", env_dir / "bin" / "python"):
        if p.is_file():
            return p
    return None


def python_exe(cfg: dict, env_dir: Path = ENV_DIR) -> str:
    """Ưu tiên: `python:` trong config/tts.yaml → môi trường omnivoice-env trong thư mục tool → python của tool."""
    configured = str(cfg.get("python") or "").strip().strip('"')
    if configured:
        return configured
    found = env_python(env_dir)
    return str(found) if found else sys.executable


def utf8_env() -> dict:
    """Windows: tiến trình con in ra ống (pipe) bằng bảng mã cũ (cp1252) → chữ Việt / Hàn / Nhật gây UnicodeEncodeError.
    Ép python con dùng UTF-8."""
    return {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def run_worker(request: dict, request_path: Path, cfg: dict, on_line=print, run=subprocess.Popen) -> None:
    """Chạy OmniVoice ở tiến trình riêng; mỗi dòng in ra được chuyển cho on_line (tiến độ). Lỗi → RuntimeError."""
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    exe = python_exe(cfg)
    if str(cfg.get("python") or "").strip() and not Path(exe).is_file() and not shutil.which(exe):
        raise RuntimeError(f"Không thấy python ở '{exe}' (dòng python: trong config\\tts.yaml) — sửa lại đường dẫn, hoặc "
                           "để trống python: \"\" và chạy install_omnivoice.bat.")
    try:
        proc = run([exe, str(WORKER), str(request_path)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                   text=True, encoding="utf-8", errors="replace", env=utf8_env())
    except OSError as exc:
        raise RuntimeError(f"{INSTALL_HINT} ({exc})") from exc
    last_error = ""
    for line in proc.stdout:
        line = line.rstrip()
        if line.startswith("ERROR"):
            last_error = line[5:].strip()
        if line:
            on_line(line)
    if proc.wait() != 0:
        if "chưa cài omnivoice" in last_error:  # nói rõ python nào đang thiếu để chủ dự án biết sửa chỗ nào
            raise RuntimeError(f"Python đang dùng ({exe}) chưa cài OmniVoice. {INSTALL_HOW}")
        raise RuntimeError(last_error or INSTALL_HINT)
