"""Dò sự kiện âm thanh (tiếng cười, tiếng hò reo/hét) và nhịp nhạc (beat) — chỉ dùng numpy, không cần mô hình AI.

Tiếng cười thường KHÔNG được Whisper ghi thành chữ, nên AI đọc transcript sẽ bỏ sót chỗ hài. Ở đây ta tìm:
- `laugh`: đoạn to đột ngột, không trùng lời thoại, âm lượng dao động nhịp nhàng 3–8 lần/giây (kiểu "ha-ha-ha");
- `cheer`: đoạn to đột ngột, không trùng lời thoại (vỗ tay, hò reo, khán giả);
- `shout`: đoạn to đột ngột trùng lời thoại (hét, nói to — thường là cao trào);
- `marker`: chữ đánh dấu Whisper tự ghi, ví dụ (笑) [Laughter] ㅋㅋ haha.
"""

from __future__ import annotations

import re
import wave
from pathlib import Path

import numpy as np

HOP_S = 0.05
MARKER_RE = re.compile(r"[（(\[]\s*(笑|笑い|拍手|laugh\w*|applause|cheer\w*|웃음|박수)\s*[)）\]]|ㅋㅋ+|ㅎㅎ+|w{3,}|"
                       r"\b(ha){2,}\b|\b(he){2,}\b|あはは|ははは|하하+", re.IGNORECASE)


def read_wav_mono(path: Path) -> tuple[np.ndarray, int]:
    """WAV PCM 16-bit (FFmpeg xuất) → mảng float32 −1..1, mono."""
    with wave.open(str(path), "rb") as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr


def rms_db(samples: np.ndarray, sr: int, hop_s: float = HOP_S) -> np.ndarray:
    hop = max(1, int(sr * hop_s))
    n = len(samples) // hop
    if n == 0:
        return np.zeros(0)
    frames = samples[: n * hop].reshape(n, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-9)


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


def _modulation(env: np.ndarray, hop_s: float = HOP_S) -> float:
    """Độ "nhịp nhàng" 3–8 Hz của đường âm lượng (tiếng cười ha-ha-ha) — tự tương quan chuẩn hóa, 0..1."""
    if len(env) < 8:
        return 0.0
    x = env - env.mean()
    denom = float((x * x).sum()) or 1.0
    lags = range(max(1, int(1 / (8 * hop_s))), int(1 / (3 * hop_s)) + 1)
    return max(float((x[:-lag] * x[lag:]).sum() / denom) for lag in lags if lag < len(x))


def detect_events(samples: np.ndarray, sr: int, speech: list[tuple[float, float]], *, rise_db: float = 10.0,
                  floor_db: float = -35.0, min_len_s: float = 0.4, merge_gap_s: float = 0.3,
                  laugh_mod: float = 0.25) -> list[dict]:
    """speech: khoảng có lời (giây). Trả [{start, end, kind, strength}] — strength = dB vượt nền."""
    db = rms_db(samples, sr)
    if len(db) == 0:
        return []
    base = float(np.median(db))
    loud = (db > base + rise_db) & (db > floor_db)
    gap = int(merge_gap_s / HOP_S)
    runs = _runs(loud)
    merged: list[list[int]] = []
    for a, b in runs:
        if merged and a - merged[-1][1] <= gap:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    events = []
    for a, b in merged:
        start, end = a * HOP_S, b * HOP_S
        if end - start < min_len_s:
            continue
        overlap = sum(max(0.0, min(end, e) - max(start, s)) for s, e in speech)
        in_speech = overlap / (end - start) > 0.5
        if in_speech:
            kind = "shout"
        else:
            kind = "laugh" if _modulation(db[a:b]) >= laugh_mod else "cheer"
        events.append({"start": round(start, 2), "end": round(end, 2), "kind": kind,
                       "strength": round(float(db[a:b].max()) - base, 1)})
    return events + quiet_laughs(db, speech, events, base, min_len_s=max(0.5, min_len_s), merge_gap=gap,
                                 laugh_mod=laugh_mod)


def quiet_laughs(db: np.ndarray, speech: list[tuple[float, float]], taken: list[dict], base: float, *,
                 min_len_s: float = 0.5, merge_gap: int = 6, laugh_mod: float = 0.25,
                 below_speech_db: float = 4.0) -> list[dict]:
    """Tiếng cười KHÔNG to hơn lời nói (cười trong lúc trò chuyện): âm thanh trong khoảng giữa các từ đã nhận dạng,
    to xấp xỉ giọng nói, dao động nhịp nhàng kiểu ha-ha-ha. Cần mốc thời gian từng từ (speech)."""
    if not speech:
        return []
    n = len(db)
    in_speech = np.zeros(n, dtype=bool)
    for s, e in speech:
        in_speech[max(0, int((s - 0.1) / HOP_S)): min(n, int((e + 0.1) / HOP_S) + 1)] = True
    if not in_speech.any():
        return []
    level = float(np.median(db[in_speech]))
    cand = (~in_speech) & (db > level - below_speech_db) & (db > base)
    merged: list[list[int]] = []
    for a, b in _runs(cand):
        if merged and a - merged[-1][1] <= merge_gap:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    out = []
    for a, b in merged:
        start, end = a * HOP_S, b * HOP_S
        if end - start < min_len_s or _modulation(db[a:b]) < laugh_mod:
            continue
        if any(t["start"] < end and t["end"] > start for t in taken):
            continue
        out.append({"start": round(start, 2), "end": round(end, 2), "kind": "laugh",
                    "strength": round(float(db[a:b].max()) - base, 1)})
    return out


def transcript_markers(segments: list[dict]) -> list[dict]:
    """Chữ đánh dấu tiếng cười / vỗ tay mà Whisper ghi sẵn trong lời thoại."""
    return [{"start": s["start"], "end": s["end"], "kind": "marker", "strength": 0.0}
            for s in segments if MARKER_RE.search(s.get("text", ""))]


def analyze_audio_events(wav: Path, segments: list[dict], cfg: dict | None = None) -> list[dict]:
    samples, sr = read_wav_mono(wav)
    speech = [(w["start"], w["end"]) for s in segments for w in (s.get("words") or [])] or \
        [(s["start"], s["end"]) for s in segments]
    ev = detect_events(samples, sr, speech, **(cfg or {})) + transcript_markers(segments)
    return sorted(ev, key=lambda e: e["start"])


KIND_VI = {"laugh": "tiếng cười", "cheer": "hò reo / vỗ tay", "shout": "nói to / hét (cao trào)",
           "marker": "đánh dấu cười/vỗ tay trong lời thoại"}


def events_for_prompt(events: list[dict], start: float = 0.0, end: float = 1e9, limit: int = 60) -> str:
    rows = [e for e in events if e["end"] > start and e["start"] < end]
    rows = sorted(rows, key=lambda e: -e["strength"])[:limit]  # quá nhiều thì giữ các sự kiện mạnh nhất

    def line(e: dict) -> str:
        strength = f" (mạnh +{e['strength']:.0f} dB)" if e["strength"] else ""
        return f"- {e['start']:.1f}–{e['end']:.1f}s: {KIND_VI.get(e['kind'], e['kind'])}{strength}"

    return "\n".join(line(e) for e in sorted(rows, key=lambda e: e["start"])) or "(không phát hiện)"


# ---------------- nhịp nhạc (beat) ----------------

def detect_beats(samples: np.ndarray, sr: int, bpm_range: tuple[float, float] = (70, 180),
                 hop_s: float = 0.01) -> list[float]:
    """Ước lượng nhịp: đường "onset" (năng lượng tăng) → tự tương quan tìm tempo → căn pha → danh sách giây."""
    hop = max(1, int(sr * hop_s))
    n = len(samples) // hop
    if n < 50:
        return []
    frames = samples[: n * hop].reshape(n, hop)
    energy = np.log1p(100 * (frames ** 2).mean(axis=1))
    onset = np.maximum(0.0, np.diff(energy, prepend=energy[0]))
    onset = onset - onset.mean()
    lo, hi = int(60 / bpm_range[1] / hop_s), int(60 / bpm_range[0] / hop_s)
    ac = [float((onset[:-lag] * onset[lag:]).sum()) for lag in range(lo, min(hi, n - 1) + 1)]
    if not ac:
        return []
    period = lo + int(np.argmax(ac))
    phases = [float(onset[p::period].sum()) for p in range(period)]
    phase = int(np.argmax(phases))
    return [round((phase + k * period) * hop_s, 3) for k in range((n - phase) // period + 1)]


def decode_mono(path: Path, sr: int = 11025) -> np.ndarray:
    """Giải mã file âm thanh bằng FFmpeg (chỉ dùng cho file trong kho assets/ của người dùng)."""
    import subprocess

    from app.analysis.ffmpeg import ffmpeg_exe

    out = subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-i", str(path), "-ac", "1",
                          "-ar", str(sr), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.int16).astype(np.float32) / 32768.0
