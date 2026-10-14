"""Chế độ "REVIEW BỎ LỬNG" (chủ dự án yêu cầu 14/10) — tính năng RIÊNG, chế độ Review phim cũ giữ nguyên.

Phim dài được kể HẾT, không bỏ cảnh: chia thành nhiều PHẦN liền nhau (phần sau nối đúng chỗ phần trước dừng), mỗi phần
một video 1:30–2:00 (tính cả short mở đầu). Đầu mỗi video là một đoạn SHORT 5–15 giây kịch tính cắt từ chính phần đó,
giữ nguyên hình + tiếng gốc; sau đó là lời review (ngôi thứ 1 hoặc thứ 3) kể phủ kín đoạn phim của phần, phần nào (trừ
phần cuối) cũng kết BỎ LỬNG. Cấu hình: config/cliff.yaml (phần còn lại dùng chung config/review.yaml).
"""

from __future__ import annotations

import re
from pathlib import Path

from app import config
from app.director.base import Director


def load_cfg() -> dict:
    return config.load("cliff")


def cliff_target(rcfg: dict, ccfg: dict | None = None) -> dict:
    """Cấu hình review cho một phần: độ dài video 1:30–2:00 (tính cả short), kể tới cuối phần (min_reach)."""
    c = load_cfg() if ccfg is None else ccfg
    lo, hi = float(c.get("min_video_s", 90)), float(c.get("max_video_s", 120))
    return {**rcfg, "target_s": hi, "min_video_s": lo, "max_video_s": hi, "plan_min_s": round(lo * 0.9, 1),
            "min_reach": float(c.get("min_reach", 0.95)), "cliff": c}


def hook_bounds(cfg: dict | None = None) -> tuple[float, float]:
    c = load_cfg() if cfg is None else cfg
    lo, hi = (float(x) for x in (c.get("hook_s") or [5, 15]))
    return lo, hi


# ---------------- chia phần ----------------

def repair_parts(cp, lo: float, hi: float, cfg: dict):
    """Nối khít các phần (AI hay để hở / chồng vài giây): phần đầu bắt đầu ở lo, phần cuối kết thúc ở hi, phần sau bắt
    đầu đúng chỗ phần trước dừng. Hở / chồng lớn hơn snap_gap_s thì để kiểm tra báo lỗi."""
    snap = float(cfg.get("snap_gap_s", 8))
    parts, fixes = sorted(cp.parts, key=lambda p: p.start), []
    out = []
    for k, p in enumerate(parts):
        a = lo if k == 0 and abs(p.start - lo) <= snap else p.start
        if out and abs(a - out[-1].end) <= snap:
            a = out[-1].end
        b = hi if k == len(parts) - 1 and abs(p.end - hi) <= snap else p.end
        if (a, b) != (p.start, p.end):
            fixes.append(f"phần {p.start:.1f}–{p.end:.1f}s → {a:.1f}–{b:.1f}s (nối khít, không bỏ cảnh)")
            p = p.model_copy(update={"start": round(a, 2), "end": round(b, 2)})
        out.append(p)
    return cp.model_copy(update={"parts": out}), fixes


def check_parts(cp, lo: float, hi: float, cfg: dict, banned: list[tuple[float, float]] | None = None) -> list[str]:
    """Các phần phủ KÍN lo–hi theo thứ tự (không hở, không chồng — không bỏ cảnh), độ dài phim mỗi phần hợp lý,
    short mở đầu 5–15 giây nằm trong phần, không chạm đoạn vi phạm chính sách."""
    from app.director.policy import overlap_s

    errors = []
    h_lo, h_hi = hook_bounds(cfg)
    min_raw, max_raw = float(cfg.get("min_raw_s", 150)), float(cfg.get("max_raw_s", 480))
    last_min = float(cfg.get("last_min_raw_s", 30))
    parts = sorted(cp.parts, key=lambda p: p.start)
    if parts != list(cp.parts):
        errors.append("các phần phải theo đúng thứ tự thời gian của phim")
    if parts and abs(parts[0].start - lo) > 0.5:
        errors.append(f"phần đầu phải bắt đầu ở {lo:.1f}s (kể từ đầu, không bỏ cảnh)")
    if parts and abs(parts[-1].end - hi) > 0.5:
        errors.append(f"phần cuối phải kết thúc ở {hi:.1f}s (kể tới hết, không bỏ cảnh)")
    for a, b in zip(parts, parts[1:]):
        if abs(b.start - a.end) > 0.5:
            errors.append(f"phần {a.start:.1f}–{a.end:.1f}s và {b.start:.1f}–{b.end:.1f}s "
                          + ("bị hở — phần sau phải bắt đầu ĐÚNG chỗ phần trước dừng (không bỏ cảnh)"
                             if b.start > a.end else "chồng nhau"))
    whole = hi - lo
    for k, p in enumerate(parts):
        name = f"phần {p.start:.1f}–{p.end:.1f}s"
        span = p.end - p.start
        tail = k == len(parts) - 1
        if span < (last_min if tail else min_raw) and whole >= min_raw:
            errors.append(f"{name} chỉ {span:.0f}s phim — mỗi phần {min_raw:.0f}–{max_raw:.0f}s phim (gộp với phần "
                          "liền kề)")
        if span > max_raw + 1:
            errors.append(f"{name} dài {span:.0f}s phim, tối đa {max_raw:.0f}s — tách làm 2 phần (vẫn kể hết, không bỏ)")
        h = p.hook
        hs = h.end - h.start
        if h.start < p.start - 0.3 or h.end > p.end + 0.3:
            errors.append(f"{name}: short mở đầu {h.start:.1f}–{h.end:.1f}s phải nằm TRONG phần này")
        if hs < h_lo - 0.3 or hs > h_hi + 0.3:
            errors.append(f"{name}: short mở đầu dài {hs:.1f}s — cần {h_lo:.0f}–{h_hi:.0f} giây")
        if banned and overlap_s(h.start, h.end, banned) > 0:
            errors.append(f"{name}: short mở đầu {h.start:.1f}–{h.end:.1f}s chạm đoạn vi phạm chính sách TikTok — "
                          "chọn khoảnh khắc kịch tính khác")
        if not p.cliff_vi.strip():
            errors.append(f"{name}: thiếu `cliff_vi` (phần dừng bỏ lửng ở đâu)")
    return errors


def merge_short(parts: list[dict], cfg: dict) -> list[dict]:
    """Gộp phần quá ngắn (thường ở chỗ nối các lượt hỏi song song của phim dài) vào phần trước nếu không quá dài."""
    min_raw, max_raw = float(cfg.get("min_raw_s", 150)), float(cfg.get("max_raw_s", 480))
    out: list[dict] = []
    for k, p in enumerate(parts):
        short = p["end"] - p["start"] < min_raw and k < len(parts) - 1
        if out and short and p["end"] - out[-1]["start"] <= max_raw * 1.3:
            prev = out[-1]
            out[-1] = {**prev, "end": p["end"], "summary_vi": f"{prev['summary_vi']} {p['summary_vi']}".strip(),
                       "cliff_vi": p["cliff_vi"]}
            continue
        out.append(p)
    return out


SEGMENT_FRAMES_NOTE = """Phim / hoạt hình ít thoại: XEM CÁC KHUNG HÌNH dưới đây (mở bằng Read) để thấy diễn biến và pha
kịch tính.
{frames}"""


def make_parts(director: Director, analysis_dir: Path, u, footage: int = 0, restrict: tuple[float, bool] | None = None):
    """Một lượt hỏi AI chia đoạn u.usable_range thành các phần liền nhau. restrict = (độ dài cả phim, phần này có
    phải đoạn CUỐI phim không) khi phim dài được chia nhiều lượt hỏi song song."""
    from app.director.policy import cut_ranges
    from app.director.schemas import CliffPlan, check_ranges
    from app.director.tasks import (_segments_in, _shared_context, apply_name_corrections, format_transcript_spread,
                                    load_analysis, pick_evenly)

    cfg = load_cfg()
    a = load_analysis(analysis_dir, footage)
    duration = a["scenes"]["duration"]
    lo, hi = u.usable_range.start, u.usable_range.end
    segs = _segments_in(a["transcript"].get("segments", []), lo, hi)
    pool = sorted((f for f in a["frames"] if lo <= f["t"] <= hi), key=lambda f: f["t"]) or a["frames"]
    frames = pick_evenly(pool, int(cfg.get("segment_frames", 40)))
    h_lo, h_hi = hook_bounds(cfg)
    final = restrict is None or restrict[1]
    variables = {**_shared_context(u, segs, a.get("events")), "duration": f"{duration:.1f}",
                 "min_raw_s": cfg.get("min_raw_s", 150), "max_raw_s": cfg.get("max_raw_s", 480),
                 "min_video_s": cfg.get("min_video_s", 90), "max_video_s": cfg.get("max_video_s", 120),
                 "hook_lo": f"{h_lo:.0f}", "hook_hi": f"{h_hi:.0f}",
                 "chunk_note": "" if restrict is None else (
                     f"\n**Phim dài được chia cho nhiều người cùng làm**: bạn chỉ lo đoạn {lo:.1f}–{hi:.1f}s (phim dài "
                     f"{restrict[0]:.0f}s). Các phần của bạn phải phủ kín ĐÚNG đoạn này."
                     + ("" if final else " Đoạn của bạn CHƯA phải hết phim — phần cuối của bạn cũng kết bỏ lửng.")),
                 "frames": SEGMENT_FRAMES_NOTE.format(
                     frames="\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) or "(không có)"),
                 "scenes": "\n".join(f"- {s['start']:.1f}–{s['end']:.1f}" for s in a["scenes"]["scenes"]
                                     if s["end"] > lo and s["start"] < hi) or "(không có)",
                 "transcript": format_transcript_spread(
                     [{**s, "text": apply_name_corrections(s["text"], u.name_corrections)} for s in segs],
                     int(cfg.get("transcript_max_chars", 30000))) or "(không có thoại)"}
    banned = cut_ranges(u)

    def extra(r) -> list[str]:
        return (check_ranges(r.parts, duration, "phần") + check_ranges([p.hook for p in r.parts], duration, "short")
                + check_parts(r, lo, hi, cfg, banned))

    return director.run("cliff_segment", variables, CliffPlan, [analysis_dir / f["file"] for f in frames],
                        extra_check=extra, repair=lambda r: repair_parts(r, lo, hi, cfg))


def make_parts_long(director: Director, analysis_dir: Path, u, footage: int = 0, log=lambda m: None) -> dict:
    """Chia cả phim thành các phần. Phim dài (> long_video.split_over_s) thì chia vài đoạn (ở chỗ lặng), hỏi AI song
    song rồi GỘP — các đoạn nối khít nhau nên các phần vẫn phủ kín cả phim. Trả {narrator_vi, videos, editor_notes}."""
    from app.director.schemas import TimeRange
    from app.director.tasks import load_analysis, long_parts
    from app.jobs.parallel import run_parallel

    cfg = load_cfg()
    a = load_analysis(analysis_dir, footage)
    lo, hi = u.usable_range.start, u.usable_range.end
    chunks = long_parts(a["transcript"].get("segments", []), lo, hi)
    if len(chunks) == 1:
        results = [make_parts(director, analysis_dir, u, footage)]
    else:
        log(f"Phim dài {(hi - lo) / 60:.0f} phút → chia {len(chunks)} đoạn "
            f"({', '.join(f'{x / 60:.1f}–{y / 60:.1f} phút' for x, y in chunks)}) cho AI chia phần song song rồi nối lại.")

        def one(chunk):
            x, y = chunk
            up = u.model_copy(update={"usable_range": TimeRange(start=x, end=y),
                                      "key_moments": [m for m in u.key_moments if m.end > x and m.start < y]
                                      or u.key_moments[:1]})
            return make_parts(director, analysis_dir, up, footage, restrict=(hi - lo, abs(y - hi) < 0.01))

        results = run_parallel(one, chunks)
    parts = [{"start": p.start, "end": p.end, "title_vi": p.title_vi, "summary_vi": p.summary_vi,
              "cliff_vi": p.cliff_vi, "hook": {"start": p.hook.start, "end": p.hook.end, "why_vi": p.hook.why_vi}}
             for r in results for p in sorted(r.parts, key=lambda p: p.start)]
    parts = merge_short(parts, cfg)
    videos = [{"index": k, **p, "last": k == len(parts)} for k, p in enumerate(parts, 1)]
    narrator = next((r.narrator_vi for r in results if r.narrator_vi.strip()), "")
    notes = " | ".join(r.editor_notes for r in results) if len(results) > 1 else results[0].editor_notes
    return {"narrator_vi": narrator, "videos": videos, "editor_notes": notes}


# ---------------- phụ đề cho short mở đầu (chủ dự án yêu cầu 14/10) ----------------

def hook_lines(segments: list[dict], a: float, b: float, corrections=()) -> list[dict]:
    """Câu thoại gốc (Whisper) nằm trong short a–b, mốc cắt gọn vào trong short."""
    from app.director.tasks import apply_name_corrections

    out = []
    for s in segments:
        s0, s1 = max(a, float(s["start"])), min(b, float(s["end"]))
        text = apply_name_corrections(str(s.get("text", "")).strip(), corrections)
        if s1 - s0 >= 0.2 and text:
            out.append({"start": round(s0, 3), "end": round(s1, 3), "src": text})
    return out


def make_hook_subs(director: Director, analysis_dir: Path, u, hook: tuple[float, float], video_index: int = 1,
                   footage: int = 0) -> list[dict]:
    """Phụ đề cho short: lời thoại gốc trong short dịch sang ngôn ngữ đích (người xem nghe tiếng gốc, đọc phụ đề).
    Tiếng gốc = tiếng đích thì dùng nguyên lời gốc, không hỏi AI. Trả [{start, end, text, text_vi}] (giây gốc)."""
    from app.director.policy import find_forbidden
    from app.director.schemas import HookSubs
    from app.director.tasks import LANG_SCRIPT_VI, LANGUAGE_NAMES, MARKETS, load_analysis, wrong_language

    a = load_analysis(analysis_dir, footage)
    lines = hook_lines(a["transcript"].get("segments", []), hook[0], hook[1], u.name_corrections)
    if not lines:
        return []
    if u.source_language == u.language:
        return [{**ln, "text": ln["src"], "text_vi": ""} for ln in lines]
    variables = {"video_index": video_index, "language_name": LANGUAGE_NAMES.get(u.language, u.language),
                 "source_name": LANGUAGE_NAMES.get(u.source_language, u.source_language),
                 "market": MARKETS.get(u.language, "TikTok"), "summary": u.summary_vi,
                 "name_corrections": "\n".join(f"- {c.wrong} → {c.right}" for c in u.name_corrections) or "(không có)",
                 "lines": "\n".join(f"[{i}] ({ln['start']:.1f}–{ln['end']:.1f}s) {ln['src']}"
                                    for i, ln in enumerate(lines, 1))}

    def extra(r) -> list[str]:
        got = {x.i for x in r.lines}
        errors = [f"thiếu câu {', '.join(map(str, sorted(set(range(1, len(lines) + 1)) - got)))} — mỗi câu gốc một câu "
                  "phụ đề"] if got != set(range(1, len(lines) + 1)) else []
        bad = [x.i for x in r.lines if wrong_language(x.text, u.language)]
        if bad:
            errors.append(f"câu {', '.join(map(str, bad))}: phải viết bằng {LANG_SCRIPT_VI.get(u.language, u.language)}")
        for x in r.lines:
            if find_forbidden(x.text, u.language):
                errors.append(f"câu {x.i} có từ không được phép trên TikTok — viết nhẹ đi")
        return errors

    r = director.run("cliff_hook_subs", variables, HookSubs, extra_check=extra)
    by = {x.i: x for x in r.lines}
    return [{**ln, "text": by[i].text.strip(), "text_vi": by[i].text_vi.strip()}
            for i, ln in enumerate(lines, 1) if i in by and by[i].text.strip()]


# ---------------- lời review từng phần ----------------

# Người kể xưng ngôi thứ nhất (bỏ qua phần trong ngoặc kép — lời nhân vật khác).
SELF_WORDS = [
    re.compile(r"(?<![가-힣])(나는|난|내가|나를|나도|나한테|내|저는|제가|저도|저를|저한테|제|저희|우리는|우리가|우리)(?![가-힣])"),
    re.compile(r"(私|僕|俺|わたし|ぼく|あたし|おれ)"),
    re.compile(r"\b(I|I'm|I've|I'd|I'll|me|my|mine|myself)\b"),
]


def self_words(text: str) -> list[str]:
    from app.director.tasks import QUOTED

    plain = QUOTED.sub(" ", text or "")
    return [m.group(0) for rx in SELF_WORDS for m in rx.finditer(plain)]


def check_first_person(script, min_share: float = 0.25) -> list[str]:
    """Ngôi thứ nhất: người kể LÀ nhân vật chính, phải xưng tôi trong lời kể (ít nhất ~1/4 số câu)."""
    lines = [ln for ln in script.lines if ln.text.strip()]
    if len(lines) < 4:
        return []
    have = sum(1 for ln in lines if self_words(ln.text))
    if have / len(lines) >= min_share:
        return []
    return [f"review NGÔI THỨ NHẤT: chỉ {have}/{len(lines)} câu người kể xưng 'tôi' — người kể LÀ nhân vật chính, kể "
            "chuyện của chính mình (한국어 나는/내가/저는…, 日本語 俺/僕/私…, English I/me/my); đừng gọi nhân vật chính "
            "bằng tên hay 'anh ta / cô ấy'"]


def check_coverage(script, lo: float, hi: float, cfg: dict) -> list[str]:
    """KHÔNG BỎ CẢNH: các câu kể phủ gần kín đoạn phim của phần, bắt đầu từ đầu phần, không nhảy cóc quá xa."""
    lines = sorted(script.lines, key=lambda ln: ln.source_start)
    span = hi - lo
    if not lines or span <= 0:
        return []
    errors = []
    if (lines[0].source_start - lo) / span > float(cfg.get("start_within", 0.05)) + 1e-6:
        errors.append(f"câu đầu kể từ {lines[0].source_start:.1f}s — phải kể từ ĐẦU phần ({lo:.1f}s), không bỏ cảnh")
    covered, end = 0.0, lo
    max_skip = float(cfg.get("max_skip_s", 30))
    for i, ln in enumerate(lines, 1):
        a, b = max(ln.source_start, end), min(ln.source_end, hi)
        if a - end > max_skip:
            errors.append(f"câu {i}: nhảy qua {a - end:.0f}s phim ({end:.1f}–{a:.1f}s) — tối đa {max_skip:.0f}s, "
                          "kể lướt đoạn đó bằng 1 câu chứ không bỏ")
        covered += max(0.0, b - a)
        end = max(end, b)
    need = float(cfg.get("min_cover", 0.85))
    if covered / span < need:
        errors.append(f"các câu mới kể phủ {covered / span:.0%} đoạn phim của phần — cần ≥ {need:.0%} (KHÔNG bỏ cảnh: "
                      "đoạn phim của câu sau nối tiếp câu trước, chỗ ít quan trọng kể lướt)")
    return errors


POV_RULE = {
    "1": """NGÔI THỨ NHẤT (chủ dự án chọn): người kể LÀ nhân vật chính "{narrator}" — kể chuyện của CHÍNH MÌNH, xưng "tôi"
  (한국어 나는 / 내가 hoặc 저는 / 제가 — chọn MỘT kiểu, giữ suốt bài; 日本語 俺 / 僕 / 私 hợp tính nhân vật; English I / me /
  my). Gọi nhân vật khác bằng tên / quan hệ với mình (bố tôi, cô ấy…). Được nói suy nghĩ, cảm xúc của mình — nhưng chỉ
  khi phim cho thấy rõ. Cảnh nhân vật chính không có mặt: kể như điều "tôi" biết được / nghe kể lại, không bịa.
  Giọng kể quá khứ như đang hồi tưởng (한국어 ~었다 / ~었어요 hoặc ~었죠; 日本語 〜た / 〜んだ; English past tense).""",
    "3": """NGÔI THỨ BA (chủ dự án chọn): người kể là người NGOÀI kể về nhân vật — gọi tên nhân vật / anh ta / cô ấy…, KHÔNG
  xưng tôi / mình / chúng ta (저는·제가·저희·내가·우리는 / 私·僕·俺 / I·me·my·we·us), không nói chuyện với người xem; bình
  luận cũng ở ngôi 3 ("Ai mà ngờ được…"). Giọng kể quá khứ (한국어 ~습니다 / ~었죠; 日本語 〜でした / 〜んです).""",
}


def part_brief(info: dict, language_name: str) -> dict:
    """Biến cho prompt dub_cliff / cliff_polish."""
    k, n = int(info.get("index", 1)), int(info.get("total", 1))
    hook = info.get("hook")
    prev = info.get("prev") or []
    last = bool(info.get("last"))
    return {
        "part": f"{k}/{n}",
        "pov_rule": POV_RULE["1" if info.get("pov") == "1" else "3"].format(narrator=info.get("narrator") or
                                                                          "nhân vật chính"),
        "hook_clip": (f"giây gốc {hook[0]:.1f}–{hook[1]:.1f} ({hook[1] - hook[0]:.0f}s) — người xem VỪA xem đoạn này "
                      "(tiếng gốc) trước khi bạn cất lời" if hook else "(không có)"),
        "prev_parts": "\n".join(f"- Phần {i}: {s}" for i, s in enumerate(prev, 1)) or "(đây là phần đầu tiên)",
        "ending_rule": (
            f"Đây là PHẦN CUỐI: kể tới KẾT phim, câu cuối khép lại câu chuyện có dư âm. Phim kết: {info.get('cliff_vi', '')}"
            if last else
            "Phần này CHƯA hết phim → kết BỎ LỬNG: câu cuối dừng NGAY TRƯỚC lúc lộ kết quả, để người xem thắc mắc "
            f"({info.get('cliff_vi', '')}). Có thể là một câu hỏi treo hoặc câu bị ngắt giữa chừng kiểu \"Và rồi…\". KHÔNG "
            "nói \"xem phần sau / part 2 / follow / theo dõi\" (TikTok tự gợi ý phần tiếp), không tóm tắt phần sau."),
        "recap_rule": ("" if k == 1 else
                       "Người xem có thể CHƯA xem phần trước: 1–2 câu đầu nhắc nhanh bối cảnh (ai, đang trong hoàn cảnh "
                       "gì) bằng chính đoạn phim đầu phần, rồi kể tiếp — không lặp lại chi tiết phần trước."),
    }
