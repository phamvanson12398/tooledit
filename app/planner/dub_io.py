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


def pending_path(job_dir: Path, video_index: int) -> Path:
    """Bản thuyết minh AI trả về lần cuối nhưng còn lỗi nhỏ — chờ người dùng quyết định có dùng không."""
    return Path(job_dir) / "plan" / f"pending_dub_video{video_index:02d}.json"


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


GAP_S = 0.12  # chừa tối thiểu giữa 2 câu thuyết minh liền nhau (lấy hơi)


def line_windows(script: DubScript, tmap) -> list[tuple[int, float, float] | None]:
    """Mỗi câu: (giây bắt đầu trên video µs, chỗ trống của câu (s), chỗ tối đa (s) = tới lúc câu sau bắt đầu).
    Video nói liên tục thì 2 số gần bằng nhau; câu nào cách câu sau một khoảng lặng thì voice được dài hơn chút
    mà không phải tăng tốc. None = câu nằm ngoài các clip được giữ."""
    spans = []
    for ln in script.lines:
        a, b = tmap.to_out(ln.source_start), tmap.to_out(ln.source_end)
        spans.append((a, b) if a is not None and b is not None and b > a else None)
    out: list[tuple[int, float, float] | None] = []
    for i, sp in enumerate(spans):
        if sp is None:
            out.append(None)
            continue
        a, b = sp
        nxt = next((x[0] for x in spans[i + 1:] if x is not None and x[0] >= a), tmap.end)
        room = max(b - a, nxt - a - int(GAP_S * 1e6))
        out.append((a, (b - a) / 1e6, room / 1e6))
    return out


def windows_for(job_dir: Path, video_index: int, script: DubScript) -> list:
    """line_windows theo kế hoạch dựng đã lưu (plan/edit_plan_videoNN.json); chưa có kế hoạch → []."""
    from app.director.schemas import EditPlan
    from app.planner.timeline import TimeMap

    p = Path(job_dir) / "plan" / f"edit_plan_video{video_index:02d}.json"
    if not p.is_file():
        return []
    plan = EditPlan.model_validate_json(p.read_text(encoding="utf-8"))
    return line_windows(script, TimeMap(plan.clips))


def voice_seconds(path: Path) -> float | None:
    """Độ dài file voice (giây): .wav đọc trực tiếp, loại khác hỏi ffprobe; không đọc được → None."""
    try:
        if Path(path).suffix.lower() == ".wav":
            import wave

            with wave.open(str(path), "rb") as w:
                return w.getnframes() / float(w.getframerate())
        from app.capcut_writer.media import probe_duration

        return probe_duration(Path(path)) / 1e6
    except Exception:
        return None


def split_upload(job_dir: Path, video_index: int, src: Path, *, exe: str | None = None) -> list[float]:
    """Một file voice cả bài → videoNN_dub01.wav, dub02.wav... theo chỗ trống từng câu. Trả độ dài từng đoạn."""
    from app.planner.voice_split import split_voice

    script = load_dub(job_dir, video_index)
    if script is None:
        raise ValueError("Video này chưa có kịch bản thuyết minh.")
    win = windows_for(job_dir, video_index, script)
    expected = [(w[1] if w else max(0.5, ln.source_end - ln.source_start)) for w, ln in
                zip(win or [None] * len(script.lines), script.lines)]
    vdir = Path(job_dir) / "voice"
    vdir.mkdir(parents=True, exist_ok=True)
    outs = [vdir / f"{line_name(video_index, i)}.wav" for i in range(1, len(script.lines) + 1)]
    tmp = [p.with_suffix(".part.wav") for p in outs]
    lengths = split_voice(src, expected, tmp, exe=exe)  # lỗi thì không đụng tới voice cũ
    for i, (t, o) in enumerate(zip(tmp, outs), 1):
        for old in vdir.glob(f"{line_name(video_index, i)}.*"):
            if old != t:
                old.unlink()
        t.replace(o)
    return lengths


def place_voices(windows: list, durations: dict[int, int], *, max_speed: float = 1.25, hard_max_speed: float = 1.4,
                 max_delay_s: float = 0.8, gap_s: float = GAP_S) -> dict[int, dict]:
    """Xếp voice thuyết minh lên timeline sao cho KHÔNG BAO GIỜ đè lên nhau (video gốc nói dày đặc).
    windows: line_windows(); durations: {số câu: độ dài voice µs}. Mỗi câu:
    1. bắt đầu đúng lúc câu gốc bắt đầu — trừ khi voice câu trước chưa nói xong: lùi lại chờ (trễ);
    2. được dùng chỗ tới lúc câu sau bắt đầu + chậm tối đa max_delay_s; dài hơn thì tăng tốc (≤ max_speed);
    3. vẫn không vừa thì tăng tốc thêm tới hard_max_speed; vẫn tràn thì câu sau lùi lại (ghi 'overflow' để báo).
    Trễ được "trả" dần ở các khoảng lặng phía sau nên lời không trôi xa hình.
    Trả {câu: {start, end, speed, delay_s, overflow_s}} (µs, trừ *_s)."""
    gap, max_delay = int(gap_s * 1e6), int(max_delay_s * 1e6)
    out: dict[int, dict] = {}
    prev_end = None
    for i, win in enumerate(windows, 1):
        if win is None or i not in durations:
            continue
        a, _slot_s, room_s = win
        v = durations[i]
        start = a if prev_end is None else max(a, prev_end + gap)
        limit = a + int(room_s * 1e6) + max_delay  # mốc phải nói xong (câu sau bắt đầu + chậm cho phép)
        avail = max(1, limit - start)
        speed = min(max_speed, max(1.0, v / avail))
        if v / speed > avail:
            speed = min(hard_max_speed, v / avail)
        speed = round(speed, 3)
        end = start + int(v / speed)  # tính theo tốc độ ĐÃ làm tròn: độ dài × tốc độ không vượt độ dài file voice
        out[i] = {"start": start, "end": end, "speed": speed, "delay_s": (start - a) / 1e6,
                  "overflow_s": max(0, end - limit) / 1e6}
        prev_end = end
    return out


def voice_rate(job_dir: Path, video_index: int, script: DubScript, min_lines: int = 3) -> float | None:
    """Tốc độ đọc THẬT của giọng bạn (ký tự / giây, trung vị các câu đã thu) — để lần sau AI viết câu vừa với giọng."""
    from statistics import median

    from app.director.tasks import speech_chars

    rates = []
    for i, ln in enumerate(script.lines, 1):
        f = find_line_voice(job_dir, video_index, i)
        secs = voice_seconds(f) if f else None
        n = speech_chars(ln.text)
        if secs and secs >= 1.0 and n >= 4:
            rates.append(n / secs)
    return round(median(rates), 2) if len(rates) >= min_lines else None


def remember_voice_rate(language: str, rate: float, key: str = "voice_cps") -> float:
    """Lưu tốc độ đọc đo được vào config/local.yaml (trung bình dần với lần trước). Trả giá trị đã lưu.
    key = "review_voice_cps" cho giọng review phim (tách riêng với giọng thuyết minh)."""
    from app import settings

    saved = dict(settings.load().get(key) or {})
    old = saved.get(language)
    new = round(rate if old is None else 0.6 * float(old) + 0.4 * rate, 2)
    saved[language] = new
    settings.save({key: saved})
    return new


def fit_status(voice_s: float, slot_s: float, room_s: float, max_speed: float) -> tuple[str, str]:
    """Voice so với chỗ trống: (mức, lời khuyên tiếng Việt). mức: ok | fast | long | short."""
    if voice_s > room_s * max_speed + 0.05:
        return "long", (f"Dài {voice_s:.1f}s, chỗ tối đa {room_s:.1f}s (kể cả tăng tốc {max_speed}x vẫn tràn) — "
                        f"thu lại nhanh hơn / gọn hơn, cần ≤ {room_s * max_speed:.1f}s")
    if voice_s > room_s + 0.05:
        return "fast", f"Dài {voice_s:.1f}s > {room_s:.1f}s — tool tự tăng tốc x{voice_s / room_s:.2f} (nghe vẫn ổn)"
    if voice_s < slot_s * 0.6:
        return "short", (f"Ngắn {voice_s:.1f}s so với chỗ {slot_s:.1f}s — sẽ có khoảng im; đọc chậm / tự nhiên hơn "
                         "nếu muốn kín")
    return "ok", f"Khớp ({voice_s:.1f}s / chỗ {slot_s:.1f}s)"


def missing_lines(job_dir: Path, scripts: dict[int, DubScript]) -> list[str]:
    return [f"{line_name(v, i)}.wav" for v, s in sorted(scripts.items()) for i in range(1, len(s.lines) + 1)
            if find_line_voice(job_dir, v, i) is None]


def write_dub_scripts(job_dir: Path, scripts: dict[int, DubScript], windows: dict[int, list] | None = None) -> Path:
    """dub_scripts.txt: từng câu cần thu + tên file, để thu một lượt (Voice Studio)."""
    lines = ["CÂU THUYẾT MINH CẦN THU — mỗi câu một file, đặt đúng tên (chấp nhận .wav / .mp3 / .m4a).",
             "Có thể chọn nhiều file cùng lúc khi tải lên. Thời lượng ghi bên cạnh là chỗ trống trên video:",
             "đọc vừa trong khoảng đó (dài hơn một chút thì tool tự tăng tốc nhẹ).", "",
             "CÁCH NHANH cho video nói liên tục (nhiều câu): đọc CẢ BÀI vào MỘT file theo đúng thứ tự dưới đây,",
             "NGHỈ khoảng 1 giây giữa các câu (không nghỉ giữa câu), rồi tải lên ở ô 'Một file cả bài' — tool tự cắt",
             "ra từng câu và báo câu nào dài quá cần thu lại.", ""]
    for v, s in sorted(scripts.items()):
        lines.append(f"=== VIDEO {v:02d} ===")
        if s.story_vi:  # review phim: đọc dàn ý câu chuyện trước để thu voice đúng giọng kể
            lines += [f"📖 Câu chuyện: {s.story_vi}", ""]
        for i, ln in enumerate(s.lines, 1):
            tag = f"  [LỜI DẪN — {ln.action_vi or 'chỗ không có giọng nói'}]" if ln.kind == "narration" else ""
            w = (windows or {}).get(v, [])
            win = w[i - 1] if i - 1 < len(w) else None
            when = (f"(chỗ trống {win[1]:.1f}s, tối đa {win[2]:.1f}s)" if win
                    else f"(~{ln.source_end - ln.source_start:.1f}s)")
            lines += [f"{line_name(v, i)}.wav  {when}{tag}", f"  Câu: {ln.text}",
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
