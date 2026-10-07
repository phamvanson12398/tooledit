"""Ghép NHIỀU video thành một nguồn chung để chọn cảnh (chủ dự án yêu cầu 07/10).

Người dùng thả nhiều video (vd nhiều tập hoạt hình); tool nối chúng thành một file `source/montage.mp4` (cùng khung,
cùng 30 fps, cùng âm thanh 48 kHz stereo) và ghi lại mỗi video nằm ở giây nào. Mọi bước sau (phân tích, AI chọn cảnh,
dựng draft) chạy như với một footage — AI biết "video 3 nằm ở giây 120–185" để lấy mỗi video một chút.
"""

from __future__ import annotations

from pathlib import Path

CANVAS = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}


def target_size(sizes: list[tuple[int, int]]) -> tuple[int, int]:
    """Khung chung: theo hướng của đa số video (dọc → 1080×1920, ngang → 1920×1080)."""
    vertical = sum(1 for w, h in sizes if h > w)
    return CANVAS["vertical"] if vertical * 2 > len(sizes) else CANVAS["horizontal"]


def concat_args(inputs: list[dict], out: Path, size: tuple[int, int], fps: int = 30) -> list[str]:
    """inputs: [{path, duration (s), has_audio}]. Video thiếu tiếng được bù khoảng lặng để nối đều."""
    w, h = size
    args, filters, pairs = [], [], []
    for x in inputs:
        args += ["-i", str(x["path"])]
    n = len(inputs)
    extra = n
    for i, x in enumerate(inputs):
        filters.append(f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                       f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps},format=yuv420p[v{i}]")
        if x.get("has_audio", True):
            filters.append(f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]")
        else:
            args += ["-f", "lavfi", "-t", f"{float(x['duration']):.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            filters.append(f"[{extra}:a]aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]")
            extra += 1
        pairs.append(f"[v{i}][a{i}]")
    filters.append(f"{''.join(pairs)}concat=n={n}:v=1:a=1[v][a]")
    return [*args, "-filter_complex", ";".join(filters), "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k", str(out)]


def parts_from(inputs: list[dict]) -> list[dict]:
    """Mốc giây của từng video trong file ghép."""
    parts, t = [], 0.0
    for i, x in enumerate(inputs, 1):
        d = float(x["duration"])
        parts.append({"index": i, "name": Path(x["path"]).name, "start": round(t, 3), "end": round(t + d, 3)})
        t += d
    return parts


def build_montage(paths: list[Path], out: Path, *, probe=None, run=None) -> list[dict]:
    """Nối các video vào `out`; trả danh sách phần (index, name, start, end)."""
    if probe is None:
        from app.capcut_writer.media import probe_video as probe
    if run is None:
        from app.analysis.ffmpeg import run
    inputs = []
    for p in paths:
        v = probe(Path(p))
        inputs.append({"path": Path(p), "duration": v.duration / 1e6, "has_audio": v.has_audio,
                       "size": (v.width, v.height)})
    out.parent.mkdir(parents=True, exist_ok=True)
    run(concat_args(inputs, out, target_size([x["size"] for x in inputs])))
    return parts_from(inputs)


def parts_brief(parts: list[dict]) -> str:
    return "\n".join(f"- video {p['index']} ({p['name']}): giây {p['start']:.1f}–{p['end']:.1f}" for p in parts)


def part_of(parts: list[dict], t: float) -> int | None:
    for p in parts:
        if p["start"] - 1e-6 <= t < p["end"]:
            return p["index"]
    return parts[-1]["index"] if parts and abs(t - parts[-1]["end"]) < 1e-3 else None
