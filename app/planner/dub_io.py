"""Thuyết minh (chế độ Đổi ngôn ngữ): lưu kịch bản, xuất dub_scripts.txt, quét file voice từng câu, chia phụ đề.

Tên file voice: jobs/<job>/voice/video01_dub01.wav, video01_dub02.wav... (nhận .wav/.mp3/.m4a).
"""

from __future__ import annotations

import re
from pathlib import Path

from app.director.schemas import DubScript
from app.planner.hook_io import VOICE_EXTS

BREAKS = "。、？！?!,.…，"


def dub_path(job_dir: Path, video_index: int) -> Path:
    return Path(job_dir) / "plan" / f"dub_video{video_index:02d}.json"


def load_dub(job_dir: Path, video_index: int) -> DubScript | None:
    p = dub_path(job_dir, video_index)
    return DubScript.model_validate_json(p.read_text(encoding="utf-8")) if p.is_file() else None


def line_name(video_index: int, line_no: int) -> str:
    return f"video{video_index:02d}_dub{line_no:02d}"


def find_line_voice(job_dir: Path, video_index: int, line_no: int) -> Path | None:
    for ext in VOICE_EXTS:
        p = Path(job_dir) / "voice" / f"{line_name(video_index, line_no)}{ext}"
        if p.is_file():
            return p
    return None


def missing_lines(job_dir: Path, scripts: dict[int, DubScript]) -> list[str]:
    return [f"{line_name(v, i)}.wav" for v, s in sorted(scripts.items()) for i in range(1, len(s.lines) + 1)
            if find_line_voice(job_dir, v, i) is None]


def write_dub_scripts(job_dir: Path, scripts: dict[int, DubScript]) -> Path:
    """dub_scripts.txt: từng câu cần thu + tên file, để thu một lượt (Voice Studio)."""
    lines = ["CÂU THUYẾT MINH CẦN THU — mỗi câu một file, đặt đúng tên (chấp nhận .wav / .mp3 / .m4a).",
             "Có thể chọn nhiều file cùng lúc khi tải lên. Thời lượng ghi bên cạnh là chỗ trống trên video:",
             "đọc vừa trong khoảng đó (dài hơn một chút thì tool tự tăng tốc nhẹ).", ""]
    for v, s in sorted(scripts.items()):
        lines.append(f"=== VIDEO {v:02d} ===")
        for i, ln in enumerate(s.lines, 1):
            tag = f"  [LỜI DẪN — {ln.action_vi or 'chỗ không có giọng nói'}]" if ln.kind == "narration" else ""
            lines += [f"{line_name(v, i)}.wav  (~{ln.source_end - ln.source_start:.1f}s){tag}", f"  Câu: {ln.text}",
                      f"  Nghĩa: {ln.text_vi}"]
            lines += ([f"  Bản địa hóa: {ln.adapt_vi}"] if ln.adapt_vi else []) + [""]
    path = Path(job_dir) / "dub_scripts.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    (Path(job_dir) / "voice").mkdir(exist_ok=True)
    return path


def match_uploads(names: list[str], video_index: int, n_lines: int) -> list[tuple[str, int]]:
    """Tên file người dùng tải lên → số câu. Đúng tên videoNN_dubMM thì theo tên; còn lại xếp theo thứ tự tên file
    vào các câu chưa có, lần lượt từ câu 1 (để chọn nhiều file 001.wav, 002.wav… một lượt)."""
    out, rest, taken = [], [], set()
    for n in names:
        m = re.search(r"video(\d+)_dub(\d+)", Path(n).stem, re.IGNORECASE)
        if m and int(m.group(1)) == video_index and 1 <= int(m.group(2)) <= n_lines:
            out.append((n, int(m.group(2))))
            taken.add(int(m.group(2)))
        else:
            rest.append(n)
    free = [i for i in range(1, n_lines + 1) if i not in taken]
    out += list(zip(sorted(rest, key=_natural), free))
    return out


def _natural(name: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def split_text(text: str, lang: str, max_chars: int) -> list[str]:
    """Chia câu thành các cụm phụ đề ≤ max_chars: ưu tiên ngắt ở dấu câu, rồi dấu cách (ko/en), rồi theo số ký tự."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    parts, buf = [], ""
    for ch in text:
        buf += ch
        if ch in BREAKS and len(buf.strip()) >= max(2, max_chars // 3):
            parts.append(buf.strip())
            buf = ""
    if buf.strip():
        parts.append(buf.strip())
    out = []
    for p in parts:
        if len(p) > max_chars and (lang in ("ja", "zh") or " " not in p):
            n = -(-len(p) // max_chars)  # chia đều thành n cụm (tránh cụm cuối chỉ còn 1–2 ký tự)
            size = -(-len(p) // n)
            out += [p[k:k + size] for k in range(0, len(p), size)]
            continue
        while len(p) > max_chars:
            cut = p.rfind(" ", 0, max_chars + 1)
            cut = cut if cut > max_chars // 3 else max_chars
            out.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            out.append(p)
    return out


def spread_cues(chunks: list[str], start: int, end: int) -> list[tuple[int, int, str]]:
    """Rải các cụm phụ đề trên [start, end] theo tỉ lệ số ký tự."""
    total = sum(max(1, len(c)) for c in chunks) or 1
    out, t = [], start
    for c in chunks:
        d = round((end - start) * max(1, len(c)) / total)
        out.append((t, min(end, t + d), c))
        t += d
    return out
