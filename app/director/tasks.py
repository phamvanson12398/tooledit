"""Các nhiệm vụ của đạo diễn: chuẩn bị dữ liệu gửi đi (gọn để tiết kiệm hạn mức Pro) và kiểm tra kết quả."""

from __future__ import annotations

import json
from pathlib import Path

from app import config
from app.director.base import Director
from app.director.schemas import STYLES, Understanding, check_ranges


def load_analysis(analysis_dir: Path, footage: int = 0) -> dict:
    def pick(name: str) -> dict:
        items = json.loads((analysis_dir / name).read_text(encoding="utf-8"))
        return next(x for x in items if x.get("footage") == footage)

    frames = [f for f in json.loads((analysis_dir / "frames.json").read_text(encoding="utf-8"))
              if f.get("footage") == footage]
    return {"transcript": pick("transcript.json"), "scenes": pick("scenes.json"),
            "subjects": pick("subjects.json"), "frames": frames}


def format_transcript(segments: list[dict], max_chars: int = 12000) -> str:
    lines = [f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in segments]
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[:max_chars] + "\n...(cắt bớt)"


def pick_evenly(items: list, n: int) -> list:
    if len(items) <= n:
        return list(items)
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def understand(director: Director, analysis_dir: Path, client_style: str | None = None,
               footage: int = 0) -> Understanding:
    a = load_analysis(analysis_dir, footage)
    sc, tr = a["scenes"], a["transcript"]
    n_frames = config.load("director").get("frames", {}).get("understand", 12)
    frames = pick_evenly(a["frames"], n_frames)
    variables = {
        "styles": ", ".join(STYLES),
        "client_style": client_style or "chưa có (khách mới, bạn tự chọn)",
        "duration": f"{sc['duration']:.1f}",
        "width": sc["width"], "height": sc["height"], "scene_count": len(sc["scenes"]),
        "language": tr.get("language") or "không rõ",
        "scenes": "\n".join(f"- {s['start']:.1f}–{s['end']:.1f}" for s in sc["scenes"]),
        "transcript": format_transcript(tr.get("segments", [])) or "(không có thoại)",
        "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames),
    }
    images = [analysis_dir / f["file"] for f in frames]
    return director.run("understand", variables, Understanding, images,
                        extra_check=lambda r: check_ranges([*r.key_moments, r.usable_range], sc["duration"],
                                                           "mốc"))


def apply_name_corrections(text: str, corrections) -> str:
    """Thay tên nhận dạng sai bằng tên đúng (dùng cho phụ đề)."""
    for c in corrections:
        if c.wrong:
            text = text.replace(c.wrong, c.right)
    return text
