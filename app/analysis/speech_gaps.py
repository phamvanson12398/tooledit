"""Lồng tiếng nhân vật — bắt đủ câu + đúng giọng nhân vật (chủ dự án 11/10: "nó cứ bắt sót câu, sót ý; giọng của nhân vật
nào thì phải chuẩn").

1) `uncovered_speech`: trên phần GIỌNG NÓI Demucs đã tách khỏi nhạc, chỗ nào có tiếng người (đủ to so với giọng nói
   trong file) mà Whisper chưa có câu nào → trả các khoảng đó để nhận dạng lại riêng (không qua bộ lọc giọng nói VAD).
2) `voice_groups`: đo cao độ (F0) + âm sắc (MFCC) của TỪNG câu thoại gốc, gom các câu cùng một giọng thành nhóm G1, G2…
   → AI biết câu nào cùng một người nói (kèm giọng cao / trung / trầm) để ghi tên nhân vật đúng và thống nhất.
   Chỉ dùng numpy (không cần tải model). Đây là gợi ý cho AI, có thể nhầm với câu rất ngắn / 2 người nói chen.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

SR = 16_000
HOP_S = 0.01
# Câu Whisper hay "bịa" khi nghe đoạn không rõ lời (nhạc, tiếng thở) — bỏ nếu nhận dạng lại ra đúng mấy câu này
HALLUCINATIONS = ("ご視聴ありがとうございました", "チャンネル登録", "시청해 주셔서 감사합니다", "구독", "thank you for watching",
                  "thanks for watching", "subscribe", "字幕", "자막", "请不吝点赞", "MBC 뉴스")


def decode16k(path: Path, exe: str | None = None) -> np.ndarray:
    """File âm thanh → float32 mono 16 kHz (−1..1)."""
    from app.analysis.ffmpeg import ffmpeg_exe

    r = subprocess.run([exe or ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1",
                        "-ar", str(SR), "-f", "s16le", "-"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"Không đọc được {path.name}: {r.stderr.decode('utf-8', 'replace')[-200:]}")
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def frame_db(x: np.ndarray, hop_s: float = HOP_S) -> np.ndarray:
    hop = int(SR * hop_s)
    n = len(x) // hop
    if n == 0:
        return np.zeros(0)
    f = x[: n * hop].reshape(n, hop).astype(np.float64)
    return 20 * np.log10(np.sqrt((f ** 2).mean(axis=1)) + 1e-9)


def voiced_regions(x: np.ndarray, *, rel_db: float = 28.0, floor_db: float = -45.0, min_s: float = 0.3,
                   merge_s: float = 0.25) -> list[tuple[float, float]]:
    """Khoảng có tiếng người (giây): to hơn max(floor_db, mức giọng nói (phân vị 95) − rel_db), gộp khoảng hở < merge_s."""
    db = frame_db(x)
    if len(db) == 0:
        return []
    thr = max(floor_db, float(np.percentile(db, 95)) - rel_db)
    on = db > thr
    out: list[list[float]] = []
    start = None
    for i, v in enumerate([*on, False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            a, b = start * HOP_S, i * HOP_S
            if out and a - out[-1][1] < merge_s:
                out[-1][1] = b
            else:
                out.append([a, b])
            start = None
    return [(round(a, 2), round(b, 2)) for a, b in out if b - a >= min_s]


def uncovered_speech(regions: list[tuple[float, float]], covered: list[tuple[float, float]], *, pad: float = 0.15,
                     min_s: float = 0.45) -> list[tuple[float, float]]:
    """Phần của các khoảng có tiếng người mà không câu nào (nới ±pad) phủ tới, dài ≥ min_s."""
    cov = sorted((a - pad, b + pad) for a, b in covered)
    out = []
    for a, b in regions:
        pieces = [(a, b)]
        for ca, cb in cov:
            nxt = []
            for pa, pb in pieces:
                if cb <= pa or ca >= pb:
                    nxt.append((pa, pb))
                    continue
                if ca > pa:
                    nxt.append((pa, ca))
                if cb < pb:
                    nxt.append((cb, pb))
            pieces = nxt
        out += [(round(pa, 2), round(pb, 2)) for pa, pb in pieces if pb - pa >= min_s]
    return out


def is_hallucination(text: str) -> bool:
    t = (text or "").strip().lower()
    return not t or any(h.lower() in t for h in HALLUCINATIONS)


# ---------- nhóm giọng ----------

def _mel_filters(n_fft: int = 512, n_mels: int = 40, fmin: float = 80.0, fmax: float = 7600.0) -> np.ndarray:
    mel = lambda f: 2595 * np.log10(1 + f / 700.0)  # noqa: E731
    imel = lambda m: 700 * (10 ** (m / 2595.0) - 1)  # noqa: E731
    pts = imel(np.linspace(mel(fmin), mel(fmax), n_mels + 2))
    bins = np.floor((n_fft + 1) * pts / SR).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        a, c, b = bins[m - 1], bins[m], bins[m + 1]
        for k in range(a, c):
            fb[m - 1, k] = (k - a) / max(c - a, 1)
        for k in range(c, b):
            fb[m - 1, k] = (b - k) / max(b - c, 1)
    return fb


_FB = None


def mfcc(x: np.ndarray, n: int = 13) -> np.ndarray:
    """MFCC (bỏ hệ số 0) từng khung 25 ms / bước 10 ms → mảng [khung, n]."""
    global _FB
    if _FB is None:
        _FB = _mel_filters()
    win, hop, n_fft = int(0.025 * SR), int(HOP_S * SR), 512
    if len(x) < win:
        return np.zeros((0, n))
    k = 1 + (len(x) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(k)[:, None]
    frames = x[idx] * np.hamming(win)
    power = np.abs(np.fft.rfft(frames, n_fft)) ** 2
    logmel = np.log(power @ _FB.T + 1e-10)
    m = logmel.shape[1]
    dct = np.cos(np.pi / m * (np.arange(m)[None, :] + 0.5) * np.arange(n + 1)[:, None])
    return (logmel @ dct.T)[:, 1:]


def pitch_hz(x: np.ndarray, fmin: float = 70.0, fmax: float = 600.0) -> float | None:
    """Cao độ trung vị (Hz) của các khung có tiếng — tự tương quan, khung 40 ms."""
    win, hop = int(0.04 * SR), int(0.02 * SR)
    lo, hi = int(SR / fmax), int(SR / fmin)
    vals = []
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    for s in range(0, len(x) - win, hop):
        f = x[s:s + win]
        if np.sqrt((f ** 2).mean()) < 0.1 * peak + 1e-4:
            continue
        f = f - f.mean()
        ac = np.correlate(f, f, mode="full")[win - 1:]
        if ac[0] <= 0:
            continue
        seg = ac[lo:hi]
        if len(seg) == 0:
            continue
        lag = int(np.argmax(seg)) + lo
        if ac[lag] / ac[0] > 0.45:  # khung có cao độ rõ (không phải tiếng xì / ồn)
            vals.append(SR / lag)
    return float(np.median(vals)) if len(vals) >= 3 else None


def pitch_label(f0: float | None) -> str:
    if not f0:
        return "?"
    return "trầm" if f0 < 150 else ("trung" if f0 < 230 else "cao")


def line_features(x: np.ndarray) -> tuple[np.ndarray, float | None] | None:
    """Đặc trưng giọng của một câu: MFCC trung bình + độ lệch (khung đủ to) và cao độ. Câu < 0.4s có tiếng → None."""
    m = mfcc(x)
    db = frame_db(x)[: len(m)]
    if len(m) == 0 or len(db) == 0:
        return None
    keep = db > (db.max() - 30)
    if keep.sum() < 40:
        return None
    m = m[: len(keep)][keep]
    f0 = pitch_hz(x)
    return np.concatenate([m.mean(axis=0), m.std(axis=0)]), f0


def distance_matrix(timbre: list[np.ndarray], f0s: list[float | None], semitone_scale: float = 8.0) -> np.ndarray:
    """Khoảng cách 0..1 giữa từng cặp câu = ½ chênh cao độ (theo cung, bão hòa ở semitone_scale cung) + ½ khác âm sắc
    (cosine của MFCC trung bình đã trừ trung bình chung). Câu không đo được cao độ: chỉ dùng âm sắc."""
    V = np.array(timbre, dtype=np.float64)
    C = V - V.mean(axis=0)
    C = C / (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)
    T = (1 - C @ C.T) / 2
    n = len(V)
    D = np.empty((n, n))
    for i in range(n):
        for j in range(n):
            if f0s[i] and f0s[j]:
                p = min(1.0, abs(12 * np.log2(f0s[i] / f0s[j])) / semitone_scale)
                D[i, j] = 0.5 * p + 0.5 * T[i, j]
            else:
                D[i, j] = T[i, j]
    return D


def cluster(D: np.ndarray, threshold: float = 0.35) -> list[int]:
    """Gom nhóm liên kết trung bình tới khi 2 nhóm gần nhất cách nhau > threshold. Trả số nhóm từng phần tử."""
    n = len(D)
    if n == 0:
        return []
    groups = [[i] for i in range(n)]
    while len(groups) > 1:
        best, pair = None, None
        for a in range(len(groups)):
            for b in range(a + 1, len(groups)):
                d = float(D[np.ix_(groups[a], groups[b])].mean())
                if best is None or d < best:
                    best, pair = d, (a, b)
        if best is None or best > threshold:
            break
        a, b = pair
        groups[a] = groups[a] + groups[b]
        del groups[b]
    label = [0] * n
    for g in groups:
        for i in g:
            label[i] = min(g)
    order = {v: k for k, v in enumerate(sorted(set(label)))}
    return [order[v] for v in label]


def voice_groups(x: np.ndarray, spans: list[tuple[float, float] | None], *, threshold: float = 0.35) -> list[dict | None]:
    """spans = (giây bắt đầu, kết thúc) của từng câu TRONG mảng x (None = không có âm thanh). Trả cho từng câu
    {"group": "G1", "pitch": "cao", "f0": 260} hoặc None (câu quá ngắn / không đo được)."""
    timbre, idx, f0s = [], [], []
    for i, sp in enumerate(spans):
        if not sp:
            continue
        a, b = int(sp[0] * SR), int(sp[1] * SR)
        got = line_features(x[max(0, a):max(0, b)])
        if got is None:
            continue
        vec, f0 = got
        timbre.append(vec[: len(vec) // 2])  # MFCC trung bình
        idx.append(i)
        f0s.append(f0)
    out: list[dict | None] = [None] * len(spans)
    if not timbre:
        return out
    labels = cluster(distance_matrix(timbre, f0s), threshold) if len(timbre) > 1 else [0]
    first: dict[int, int] = {}
    for lab in labels:
        first.setdefault(lab, len(first) + 1)
    for i, lab, f0 in zip(idx, labels, f0s):
        out[i] = {"group": f"G{first[lab]}", "pitch": pitch_label(f0), "f0": int(round(f0)) if f0 else None}
    return out


def to_concat_time(t: float, layout: list[dict]) -> float | None:
    """Giây gốc của video → giây trong file giọng nói nối liền (ngược với separate.to_source_time)."""
    for seg in layout:
        if seg["start"] - 0.05 <= t <= seg["end"] + 0.05:
            return round(seg["offset"] + (t - seg["start"]), 3)
    return None
