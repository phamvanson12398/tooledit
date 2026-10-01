"""So sánh video gốc với video đã edit: khác nhau bao nhiêu phần trăm (ước lượng).

Cách đo (chỉ numpy + OpenCV, chạy trên máy, không gửi video đi đâu):
- HÌNH: lấy mẫu khung hình đều (mặc định 2 khung/giây) ở cả hai video, tính "dấu vân tay ảnh" (dHash 64 bit).
  Mỗi khung của bản edit được so với MỌI khung của bản gốc, thử cả phần giữa khung (khối video 16:9 / 4:3 / 1:1 / 9:10
  nằm giữa màn 9:16) và cả bản lật ngang → lấy độ giống cao nhất. Khung "gần như trùng" khi giống ≥ ~80%.
- TIẾNG: đường âm lượng (100 ms/điểm), chia bản edit thành cửa sổ 3 giây, tìm đoạn khớp nhất trong bản gốc
  (tương quan). Cửa sổ "trùng" khi tương quan ≥ 0.8. Cần FFmpeg; không có thì bỏ qua phần tiếng.
- THỜI LƯỢNG: chênh lệch độ dài.
Điểm tổng = 60% hình + 30% tiếng + 10% thời lượng (không đo được tiếng thì hình 85% + thời lượng 15%).

Đây là ƯỚC LƯỢNG mức khác biệt về hình và tiếng để người dựng tự đánh giá bản edit; KHÔNG phải cách TikTok chấm
nội dung, không bảo đảm gì về việc video được phân phối hay không.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# vùng giữa khung để thử (tỉ lệ rộng/cao của khối video trong bản edit); None = cả khung
BLOCK_RATIOS = (None, 16 / 9, 4 / 3, 1.0, 0.9)
MATCH_BITS = 12          # dHash lệch ≤ 12/64 bit ≈ giống ≥ 81% → coi là cùng khung hình
AUDIO_MATCH_CORR = 0.8


@dataclass
class CompareResult:
    visual_diff: float               # % khác về hình (0–100)
    visual_matched: float            # % khung bản edit gần như trùng một khung gốc
    audio_diff: float | None         # % khác về tiếng; None = không đo được
    duration_diff: float             # % chênh thời lượng
    overall: float                   # % khác tổng hợp
    original_s: float
    edited_s: float
    mirrored_share: float = 0.0      # % khung trùng chỉ khi lật ngang (cảnh phản chiếu)
    notes: list[str] = field(default_factory=list)


# ---------------- hình ----------------

def dhash(gray: np.ndarray) -> int:
    """Dấu vân tay 64 bit: thu ảnh xám về 9x8, so sánh từng điểm với điểm bên phải."""
    import cv2

    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA).astype(np.int16)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def center_crop(gray: np.ndarray, ratio: float | None) -> np.ndarray:
    """Khối có tỉ lệ `ratio` (rộng/cao) nằm giữa khung, rộng tối đa bằng khung."""
    if ratio is None:
        return gray
    h, w = gray.shape[:2]
    bh = min(h, int(round(w / ratio)))
    bw = min(w, int(round(bh * ratio)))
    y0, x0 = (h - bh) // 2, (w - bw) // 2
    return gray[y0:y0 + bh, x0:x0 + bw]


def frame_hashes(frames: list[np.ndarray], variants: bool = False) -> list[list[tuple[int, bool]]]:
    """Mỗi khung → danh sách (hash, đã_lật). variants=True: thêm các vùng giữa khung và bản lật ngang."""
    out = []
    for g in frames:
        hs = []
        for r in (BLOCK_RATIOS if variants else (None,)):
            c = center_crop(g, r)
            if c.size == 0 or min(c.shape[:2]) < 8:
                continue
            hs.append((dhash(c), False))
            if variants:
                hs.append((dhash(c[:, ::-1]), True))
        out.append(hs)
    return out


def visual_similarity(orig: list[np.ndarray], edited: list[np.ndarray]) -> tuple[float, float, float]:
    """Trả (độ giống trung bình 0–1, tỉ lệ khung trùng 0–1, tỉ lệ khung chỉ trùng khi lật 0–1)."""
    if not orig or not edited:
        return 0.0, 0.0, 0.0
    o = np.array([h for hs in frame_hashes(orig) for h, _ in hs], dtype=np.uint64)
    sims, matched, mirrored = [], 0, 0
    for hs in frame_hashes(edited, variants=True):
        best, best_flip = 64, False
        for h, flipped in hs:
            d = int(min(_popcount(o ^ np.uint64(h))))
            if d < best or (d == best and not flipped):
                best, best_flip = d, flipped
        sims.append(1.0 - best / 64.0)
        if best <= MATCH_BITS:
            matched += 1
            mirrored += best_flip
    n = len(sims)
    return float(np.mean(sims)), matched / n, mirrored / n


def _popcount(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.uint64)
    count = np.zeros(x.shape, dtype=np.int64)
    for shift in range(0, 64, 8):
        count += _POP8[((x >> np.uint64(shift)) & np.uint64(0xFF)).astype(np.int64)]
    return count


_POP8 = np.array([bin(i).count("1") for i in range(256)], dtype=np.int64)


def read_frames(path: Path, fps: float = 2.0, max_frames: int = 1200, size: int = 192) -> tuple[list[np.ndarray], float]:
    """Khung xám lấy mẫu đều (OpenCV). Trả (khung, độ dài giây)."""
    import cv2

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Không mở được video: {path}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total / src_fps if total else 0.0
    step = max(1, int(round(src_fps / fps)))
    if total and total / step > max_frames:  # video rất dài: giãn mẫu để không quá chậm
        step = int(np.ceil(total / max_frames))
    frames, i = [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            ok, img = cap.retrieve()
            if ok:
                h, w = img.shape[:2]
                scale = size / max(h, w)
                img = cv2.resize(img, (max(9, int(w * scale)), max(8, int(h * scale))), interpolation=cv2.INTER_AREA)
                frames.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        i += 1
    cap.release()
    if not duration:
        duration = i / src_fps
    return frames, duration


# ---------------- tiếng ----------------

def envelope(samples: np.ndarray, sr: int, hop_s: float = 0.1) -> np.ndarray:
    hop = max(1, int(sr * hop_s))
    n = len(samples) // hop
    if n == 0:
        return np.zeros(0)
    rms = np.sqrt((samples[: n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-9)


def audio_similarity(orig_env: np.ndarray, edit_env: np.ndarray, win: int = 30) -> float | None:
    """Tỉ lệ cửa sổ 3 giây của bản edit tìm được đoạn khớp (tương quan ≥ 0.8) trong bản gốc. None nếu quá ngắn."""
    if len(orig_env) < win or len(edit_env) < win:
        return None
    windows = [edit_env[i:i + win] for i in range(0, len(edit_env) - win + 1, win)]
    # chuẩn hóa từng đoạn trượt của bản gốc
    from numpy.lib.stride_tricks import sliding_window_view

    segs = sliding_window_view(orig_env, win)
    segs = segs - segs.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(segs, axis=1) + 1e-9
    matched = 0
    for w in windows:
        w = w - w.mean()
        wn = np.linalg.norm(w)
        if wn < 1e-6:  # đoạn im lặng tuyệt đối: không kết luận được, coi như khác
            continue
        corr = segs @ w / (norms * wn)
        if corr.max() >= AUDIO_MATCH_CORR:
            matched += 1
    return matched / len(windows)


def read_audio_env(path: Path) -> np.ndarray:
    from app.analysis.audio_events import decode_mono

    sr = 8000
    return envelope(decode_mono(Path(path), sr), sr)


# ---------------- tổng hợp ----------------

def combine(visual_sim: float, visual_matched: float, audio_sim: float | None, orig_s: float, edit_s: float,
            mirrored: float = 0.0) -> CompareResult:
    # khác về hình: trung bình giữa "khung không trùng" và "độ giống trung bình", để một vài khung giống không kéo lệch
    vdiff = 100.0 * (0.5 * (1 - visual_matched) + 0.5 * (1 - visual_sim))
    adiff = None if audio_sim is None else 100.0 * (1 - audio_sim)
    ddiff = 100.0 * min(1.0, abs(orig_s - edit_s) / max(orig_s, edit_s, 1e-6))
    overall = (0.6 * vdiff + 0.3 * adiff + 0.1 * ddiff) if adiff is not None else (0.85 * vdiff + 0.15 * ddiff)
    notes = []
    if adiff is None:
        notes.append("Không đo được phần tiếng (thiếu FFmpeg hoặc video quá ngắn) — điểm tổng chỉ tính hình + thời lượng.")
    return CompareResult(visual_diff=round(vdiff, 1), visual_matched=round(100 * visual_matched, 1),
                         audio_diff=None if adiff is None else round(adiff, 1), duration_diff=round(ddiff, 1),
                         overall=round(overall, 1), original_s=round(orig_s, 1), edited_s=round(edit_s, 1),
                         mirrored_share=round(100 * mirrored, 1), notes=notes)


def compare_videos(original: Path, edited: Path, fps: float = 2.0, audio: bool = True) -> CompareResult:
    of, od = read_frames(original, fps)
    ef, ed = read_frames(edited, fps)
    vsim, vmatch, mirr = visual_similarity(of, ef)
    asim = None
    if audio:
        try:
            asim = audio_similarity(read_audio_env(original), read_audio_env(edited))
        except Exception:  # không có FFmpeg / video không có tiếng
            asim = None
    return combine(vsim, vmatch, asim, od, ed, mirr)
