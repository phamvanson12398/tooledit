"""Cắt theo nhịp nhạc: dời điểm cắt giữa hai clip về đúng beat gần nhất của bài nhạc nền.

Nguồn beat:
- nhạc trong kho assets/ (file của người dùng / Freesound CC0): tự dò bằng numpy (app/analysis/audio_events.py);
- nhạc thư viện CapCut: đọc file nhịp `.beat` CapCut tự tạo trong cache (chỉ đọc MỐC THỜI GIAN, không đụng tới
  file nhạc — nhạc CapCut vẫn chỉ được tham chiếu trong draft). Định dạng file .beat chưa được xác minh
  [CẦN KIỂM TRA TRÊN MÁY]: đọc được thì dùng, không thì bỏ qua (không cắt theo nhịp cho bài đó).

Luật an toàn khi dời điểm cắt (±tolerance giây):
- Cắt sớm hơn (bỏ bớt đuôi clip): chỉ khi phần bị bỏ KHÔNG có lời nói (không cắt mất chữ).
- Cắt muộn hơn (kéo dài đuôi clip): chỉ khi không lấn sang footage của clip khác, không vượt footage,
  và điểm cắt mới không rơi giữa một từ.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def looped_beats(beats: list[float], music_len_s: float, total_s: float) -> list[float]:
    """Nhạc nền lặp lại từ đầu mỗi music_len_s giây (như bộ dựng đặt nhạc) → beat trên cả video."""
    if not beats or music_len_s <= 0:
        return []
    out, k = [], 0
    while k * music_len_s < total_s:
        out += [b + k * music_len_s for b in beats if b < music_len_s and b + k * music_len_s <= total_s]
        k += 1
    return out


def _word_inside(words: list[tuple[float, float]], a: float, b: float) -> bool:
    return any(s < b and e > a for s, e in words)


def _word_straddles(words: list[tuple[float, float]], t: float, margin: float = 0.03) -> bool:
    return any(s + margin < t < e - margin for s, e in words)


def snap_cuts(clips: list[dict], hook_s: float, beats: list[float], words: list[tuple[float, float]],
              footage_s: float, tolerance: float = 0.3, min_clip_s: float = 0.6) -> tuple[list[dict], int]:
    """clips: [{source_start, source_end, speed, replay}] (giây gốc). Trả (clips đã chỉnh, số điểm cắt đã dời)."""
    clips = [dict(c) for c in clips]
    if not beats or len(clips) < 2:
        return clips, 0
    t_out, snapped = hook_s, 0
    for i in range(len(clips) - 1):
        c = clips[i]
        speed = c.get("speed", 1.0) or 1.0
        cut = t_out + (c["source_end"] - c["source_start"]) / speed
        best = None
        for b in beats:
            d = b - cut
            if abs(d) > tolerance or abs(d) < 0.02:
                continue
            new_end = c["source_end"] + d * speed
            if d < 0:  # cắt sớm hơn
                ok = (new_end - c["source_start"]) / speed >= min_clip_s and \
                    not _word_inside(words, new_end, c["source_end"])
            else:  # kéo dài
                others = [o for j, o in enumerate(clips) if j != i and not o.get("replay") and not o.get("repeat")]
                ok = new_end <= footage_s and not _word_straddles(words, new_end) and not any(
                    o["source_start"] < new_end and o["source_end"] > c["source_end"] for o in others)
            if ok and (best is None or abs(d) < abs(best[0])):
                best = (d, new_end)
        if best is not None:
            c["source_end"] = round(best[1], 3)
            snapped += 1
        t_out += (c["source_end"] - c["source_start"]) / speed
    return clips, snapped


def nearest_beat(t: float, beats: list[float], tolerance: float) -> float | None:
    near = [b for b in beats if abs(b - t) <= tolerance]
    return min(near, key=lambda b: abs(b - t)) if near else None


# ---------------- nguồn beat ----------------

def parse_beat_file(path: Path) -> list[float]:
    """Đọc file nhịp .beat của CapCut. Chưa có mẫu để xác minh định dạng → thử JSON rồi thử văn bản số.
    Trả danh sách giây tăng dần, hoặc [] nếu không đọc được."""
    try:
        raw = Path(path).read_bytes()
    except OSError:
        return []
    text = raw.decode("utf-8", errors="ignore")
    candidates: list[list[float]] = []
    try:
        data = json.loads(text)

        def walk(x):
            if isinstance(x, list) and len(x) >= 4 and all(isinstance(v, (int, float)) for v in x):
                candidates.append([float(v) for v in x])
            elif isinstance(x, list):
                for v in x:
                    walk(v)
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)
        walk(data)
    except ValueError:
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
        if len(nums) >= 4:
            candidates.append(nums)
    best: list[float] = []
    for c in candidates:
        inc = [v for a, v in zip([float("-inf")] + c, c) if v > a]
        if len(inc) >= 0.9 * len(c) and len(inc) > len(best):
            best = inc
    if not best:
        return []
    top = max(best)
    scale = 1e-6 if top > 1e6 else (1e-3 if top > 2000 else 1.0)  # µs / ms / giây
    return [round(v * scale, 3) for v in best if v >= 0]


def beats_for_music(item, cache: bool = True) -> list[float]:
    """Beat của bài nhạc (giây, tính từ đầu bài). Nhạc local: tự dò (lưu kèm file .beats.json);
    nhạc CapCut: file .beat trong cache CapCut."""
    mat = item.material
    if mat.get("local"):
        path = Path(mat["path"])
        side = path.with_name(path.name + ".beats.json")
        if cache and side.is_file():
            try:
                return json.loads(side.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        from app.analysis.audio_events import decode_mono, detect_beats

        sr = 11025
        beats = detect_beats(decode_mono(path, sr), sr)
        if cache:
            try:
                side.write_text(json.dumps(beats), encoding="utf-8")
            except OSError:
                pass
        return beats
    bp = getattr(item, "beats_path", "")
    return parse_beat_file(Path(bp)) if bp else []
