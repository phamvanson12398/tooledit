"""Bảng hook: lưu phương án + lựa chọn, xuất hook_scripts.txt, quét file voice (mục 5)."""

from __future__ import annotations

import json
from pathlib import Path

from app.director.schemas import HOOK_TYPES_VI, HookSet

VOICE_EXTS = (".wav", ".mp3", ".m4a")


def hooks_path(job_dir: Path) -> Path:
    return Path(job_dir) / "plan" / "hooks.json"


def save_hooks(job_dir: Path, sets: list[HookSet], choices: dict[int, int] | None = None) -> Path:
    path = hooks_path(job_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"sets": [s.model_dump() for s in sets], "choices": {str(k): v for k, v in (choices or {}).items()}}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_hooks(job_dir: Path) -> tuple[list[HookSet], dict[int, int]]:
    data = json.loads(hooks_path(job_dir).read_text(encoding="utf-8"))
    return [HookSet.model_validate(s) for s in data["sets"]], {int(k): v for k, v in data.get("choices", {}).items()}


def voice_name(video_index: int) -> str:
    return f"video{video_index:02d}_hook"


def find_voice(job_dir: Path, video_index: int) -> Path | None:
    for ext in VOICE_EXTS:
        p = Path(job_dir) / "voice" / f"{voice_name(video_index)}{ext}"
        if p.is_file():
            return p
    return None


def missing_voices(job_dir: Path, choices: dict[int, int]) -> list[str]:
    return [f"{voice_name(v)}.wav" for v in sorted(choices) if find_voice(job_dir, v) is None]


def hook_table(sets: list[HookSet]) -> str:
    """Bảng chọn hook dạng chữ (tất cả phương án của mọi video trong một bảng)."""
    lines = []
    for s in sets:
        lines.append(f"=== VIDEO {s.video_index:02d} ===")
        for i, o in enumerate(s.options, 1):
            lines += [
                f"[{i}] ({HOOK_TYPES_VI[o.hook_type]}) {o.line}",
                f"    Dịch: {o.line_vi}",
                f"    Chữ trên màn: {o.onscreen_text} | Footage: {o.footage.start:.1f}–{o.footage.end:.1f}s"
                f" | Nguồn: {o.source.start:.1f}–{o.source.end:.1f}s",
                f"    Nhạc/SFX: {o.music_sfx_vi} | Vì sao: {o.why_vi}",
            ]
        lines.append(f"Ghi chú editor: {s.editor_notes}\n")
    return "\n".join(lines)


def write_hook_scripts(job_dir: Path, sets: list[HookSet], choices: dict[int, int]) -> Path:
    """hook_scripts.txt: câu cần thu + tên file tương ứng, để thu voice một lượt."""
    by_index = {s.video_index: s for s in sets}
    lines = ["CÂU HOOK CẦN THU (thả file vào thư mục voice\\ của job, chấp nhận .wav / .mp3 / .m4a)", ""]
    for v in sorted(choices):
        o = by_index[v].options[choices[v] - 1]
        lines += [f"{voice_name(v)}.wav", f"  Câu: {o.line}", f"  Nghĩa: {o.line_vi}", ""]
    path = Path(job_dir) / "hook_scripts.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    (Path(job_dir) / "voice").mkdir(exist_ok=True)
    return path
