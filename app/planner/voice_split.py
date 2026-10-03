"""Thu voice thuyết minh CẢ BÀI một file rồi tự cắt ra từng câu (chủ dự án yêu cầu 03/10).

Video nói liên tục (hướng dẫn trang điểm, review...) có rất nhiều câu; thu từng file một rất mất công. Chủ dự án đọc
cả kịch bản một lượt trong Voice Studio, NGHỈ khoảng 1 giây giữa các câu, tải lên một file. Tool:
1. giải mã file về PCM (FFmpeg), đo độ to từng 20 ms;
2. tìm các khoảng lặng (ứng viên điểm cắt);
3. chọn đúng (số câu - 1) điểm cắt sao cho độ dài từng đoạn sát nhất với chỗ trống của từng câu trên video
   (quy hoạch động — nên dấu phẩy ngắt hơi trong câu không bị nhầm là hết câu), ưu tiên khoảng lặng dài;
4. ghi từng đoạn thành videoNN_dubMM.wav (đã cắt bớt lặng đầu/cuối).
"""

from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

RATE = 48_000
FRAME_S = 0.02


def decode(path: Path, exe: str | None = None) -> np.ndarray:
    """File âm thanh bất kỳ (.wav/.mp3/.m4a) → mảng int16 mono 48 kHz."""
    from app.analysis.ffmpeg import ffmpeg_exe

    cmd = [exe or ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1",
           "-ar", str(RATE), "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"Không đọc được file voice: {r.stderr.decode('utf-8', 'replace')[-300:]}")
    return np.frombuffer(r.stdout, dtype=np.int16)


def frame_db(pcm: np.ndarray) -> np.ndarray:
    n = int(RATE * FRAME_S)
    k = len(pcm) // n
    if k == 0:
        return np.zeros(0)
    x = pcm[:k * n].astype(np.float64).reshape(k, n) / 32768.0
    rms = np.sqrt((x ** 2).mean(axis=1)) + 1e-9
    return 20 * np.log10(rms)


def find_pauses(db: np.ndarray, min_pause_s: float = 0.3, floor_db: float = 30.0) -> list[tuple[float, float]]:
    """Khoảng lặng (giây đầu, giây cuối): thấp hơn mức giọng nói (phân vị 90) quá floor_db, dài ≥ min_pause_s."""
    if len(db) == 0:
        return []
    voiced = float(np.percentile(db, 90))
    silent = db < max(voiced - floor_db, -60.0)
    out, start = [], None
    for i, s in enumerate([*silent, False]):
        if s and start is None:
            start = i
        elif not s and start is not None:
            if (i - start) * FRAME_S >= min_pause_s:
                out.append((start * FRAME_S, i * FRAME_S))
            start = None
    return out


def choose_cuts(pauses: list[tuple[float, float]], total: float, expected: list[float],
                pause_weight: float = 0.15) -> list[float] | None:
    """Chọn len(expected)-1 khoảng lặng làm điểm cắt (trả giây giữa mỗi khoảng). Không đủ khoảng lặng → None.
    Chi phí = lệch tỉ lệ độ dài từng đoạn so với chỗ trống dự kiến, trừ điểm thưởng cho khoảng lặng dài."""
    n = len(expected)
    if n == 1:
        return []
    inner = [p for p in pauses if p[0] > 0.05 and p[1] < total - 0.05]  # bỏ lặng đầu / cuối file
    m = len(inner)
    if m < n - 1:
        return None
    mids = [(a + b) / 2 for a, b in inner]
    exp_total = sum(expected) or 1.0
    want = [e / exp_total * total for e in expected]
    longest = max(b - a for a, b in inner) or 1.0
    bonus = [pause_weight * (b - a) / longest for a, b in inner]

    def cost(seg_len: float, k: int) -> float:
        return ((seg_len - want[k]) / max(want[k], 0.5)) ** 2

    inf = float("inf")
    # best[k][j]: đoạn 0..k xong, điểm cắt thứ k là khoảng lặng j
    best = [[inf] * m for _ in range(n - 1)]
    back = [[-1] * m for _ in range(n - 1)]
    for j in range(m):
        best[0][j] = cost(mids[j], 0) - bonus[j]
    for k in range(1, n - 1):
        for j in range(k, m):
            for i in range(k - 1, j):
                if best[k - 1][i] == inf:
                    continue
                c = best[k - 1][i] + cost(mids[j] - mids[i], k) - bonus[j]
                if c < best[k][j]:
                    best[k][j], back[k][j] = c, i
    last = min(range(m), key=lambda j: best[n - 2][j] + cost(total - mids[j], n - 1))
    if best[n - 2][last] == inf:
        return None
    cuts, j = [], last
    for k in range(n - 2, -1, -1):
        cuts.append(mids[j])
        j = back[k][j]
    return sorted(cuts)


def _trim(piece: np.ndarray, db: np.ndarray, start_frame: int, voiced: float, keep_s: float = 0.08) -> np.ndarray:
    """Bỏ lặng ở đầu / cuối đoạn, chừa lại keep_s cho tự nhiên."""
    n = int(RATE * FRAME_S)
    frames = len(piece) // n
    loud = [i for i in range(frames) if start_frame + i < len(db) and db[start_frame + i] >= voiced - 30.0]
    if not loud:
        return piece
    keep = int(keep_s / FRAME_S)
    a = max(0, loud[0] - keep) * n
    b = min(frames, loud[-1] + 1 + keep) * n
    return piece[a:b]


def write_wav(path: Path, pcm: np.ndarray) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.astype(np.int16).tobytes())


def split_voice(src: Path, expected: list[float], out_paths: list[Path], *, exe: str | None = None,
                min_pause_s: float = 0.3) -> list[float]:
    """Cắt một file voice cả bài thành len(expected) file. Trả độ dài (giây) từng đoạn. Lỗi rõ ràng nếu không cắt được."""
    pcm = decode(src, exe)
    total = len(pcm) / RATE
    db = frame_db(pcm)
    pauses = find_pauses(db, min_pause_s)
    cuts = choose_cuts(pauses, total, expected)
    if cuts is None:
        found = len([p for p in pauses if p[0] > 0.05 and p[1] < total - 0.05])
        raise ValueError(f"File voice chỉ có {found} chỗ nghỉ, cần {len(expected) - 1} (kịch bản có {len(expected)} câu). "
                         "Thu lại và NGHỈ khoảng 1 giây giữa các câu, hoặc tải từng câu một file.")
    voiced = float(np.percentile(db, 90)) if len(db) else 0.0
    bounds = [0.0, *cuts, total]
    lengths = []
    for k, path in enumerate(out_paths):
        a, b = int(bounds[k] * RATE), int(bounds[k + 1] * RATE)
        piece = _trim(pcm[a:b], db, int(bounds[k] / FRAME_S), voiced)
        write_wav(path, piece)
        lengths.append(len(piece) / RATE)
    return lengths
