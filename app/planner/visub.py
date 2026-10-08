"""Chế độ "Phụ đề tiếng Việt" (chủ dự án yêu cầu 08/10): dịch lời của video nước ngoài sang tiếng Việt để XEM HIỂU.

Không dựng lại gì: video + tiếng gốc giữ nguyên; tool chỉ
1. dịch từng câu thoại (Whisper đã nhận dạng, mọi ngôn ngữ) sang tiếng Việt bằng đạo diễn AI, theo từng lô;
2. xuất file phụ đề `deliver/<tên>_vi.srt` (mở video gốc bằng VLC / PotPlayer / trình phát Windows + file .srt là xem được ngay);
3. ghi một draft CapCut: video gốc nguyên vẹn + phụ đề tiếng Việt (để xuất mp4 có chữ sẵn nếu muốn).
"""

from __future__ import annotations

from pathlib import Path

from app.director.base import Director

SEC = 1_000_000


def _fmt(t: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:04.1f}"


def translate(director: Director, segments: list[dict], language: str, batch: int = 60) -> list[str]:
    """Câu dịch tiếng Việt cho từng đoạn thoại (cùng thứ tự). Mỗi lô gửi kèm vài câu trước / sau làm bối cảnh."""
    from app.director.schemas import ViSubs

    out: list[str] = []
    for b in range(0, len(segments), batch):
        chunk = segments[b:b + batch]
        idx = list(range(b + 1, b + len(chunk) + 1))

        def show(seq, start):
            return "\n".join(f"[{start + k}] ({_fmt(s['start'])}) {s['text'].strip()}" for k, s in enumerate(seq))

        variables = {"language": language or "không rõ",
                     "lines": show(chunk, b + 1),
                     "before": show(segments[max(0, b - 3):b], max(0, b - 3) + 1) or "(đầu video)",
                     "after": show(segments[b + batch:b + batch + 3], b + batch + 1) or "(hết video)"}

        def extra(r, idx=idx) -> list[str]:
            got = {x.i for x in r.lines if x.vi.strip()}
            miss = [i for i in idx if i not in got]
            return [f"thiếu câu dịch cho số {', '.join(map(str, miss[:20]))}"] if miss else []

        r = director.run("subtitle_vi", variables, ViSubs, extra_check=extra)
        by_i = {x.i: x.vi.strip() for x in r.lines}
        out += [by_i.get(i, "") for i in idx]
    return out


def cues(segments: list[dict], vi: list[str], max_chars: int = 42, max_cue_s: float = 6.0) -> list[tuple[int, int, str]]:
    """Cụm phụ đề (µs): câu dài chia nhỏ theo dấu câu / dấu cách, rải trên thời gian của câu gốc."""
    from app.planner.dub_io import split_text, spread_cues

    out = []
    for seg, text in zip(segments, vi):
        if not text:
            continue
        a, b = round(seg["start"] * SEC), round(seg["end"] * SEC)
        if b <= a:
            continue
        chunks = split_text(text, "en", max_chars)
        n_min = max(1, round((b - a) / (max_cue_s * SEC)))  # câu rất dài mà ít chữ: vẫn tách để không đứng quá lâu
        if len(chunks) < n_min and len(text) > max_chars // 2:
            chunks = split_text(text, "en", max(12, len(text) // n_min + 1))
        out += spread_cues(chunks, a, b)
    return out


def srt(cue_list: list[tuple[int, int, str]]) -> str:
    def ts(us: int) -> str:
        ms = us // 1000
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    return "\n".join(f"{n}\n{ts(a)} --> {ts(b)}\n{t}\n" for n, (a, b, t) in enumerate(cue_list, 1))


def subtitle_y(width: int, height: int) -> float:
    """Vị trí phụ đề trên khung 9:16 (nửa khung, y hướng lên): ngay dưới video ngang; video dọc thì ở 1/4 dưới."""
    h = (1080 * height / width) / 1920
    if h >= 0.9:
        return -0.55
    return max(-0.8, -h - 0.07)


def build_draft(template, drafts_root: Path, name: str, src, cue_list, size: float = 11.0):
    """Draft CapCut: toàn bộ video gốc (tiếng gốc giữ nguyên) + phụ đề tiếng Việt chữ trắng viền đen."""
    from app.capcut_writer import DraftWriter
    from app.capcut_writer.writer import TextStyle

    w = DraftWriter(template, Path(drafts_root), name)
    w.add_video(src, target_start=0, duration=src.duration)
    style = TextStyle(size=size, color=(1, 1, 1), bold=True, stroke_color=(0, 0, 0), stroke_width=0.12)
    y = subtitle_y(src.width, src.height)
    for a, b, t in cue_list:
        if b > a and a < src.duration:
            w.add_text(t, start=a, duration=min(b, src.duration) - a, x=0.0, y=y, style=style)
    return w
