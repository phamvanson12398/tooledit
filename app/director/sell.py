"""BÁN CONTENT (chủ dự án yêu cầu 15/10): video gốc ~55–60 giây + định hướng nội dung → AI viết kịch bản MỚI (mở đầu thu
hút → nội dung mạch lạc → kêu gọi hành động khi cần) và chọn cảnh cho từng câu (được đảo thứ tự, được dùng lại cảnh).
Âm thanh gốc bỏ hết; voice + nhạc mới. Tool dựng cảnh theo voice thật (app/planner/sell_sync.py)."""

from __future__ import annotations

from pathlib import Path

from app import config
from app.director.base import Director


def sell_cfg() -> dict:
    return config.load("sell") or {}


def sell_target(cfg: dict, sell_s: float | int = 0) -> float:
    """Thời lượng mục tiêu (giây): chủ dự án chọn khi tạo job, mặc định default_s; luôn ≥ min_s (> 60 giây)."""
    s = float(sell_s or cfg.get("default_s", 65))
    return max(s, float(cfg.get("min_s", 60.5)))


def sell_cps(cfg: dict, language: str) -> float:
    """Tốc độ đọc dùng để tính độ dài bài. Chủ dự án 15/10 ("voice thiếu, không đủ ý"): đã đo được giọng thật của chế
    độ này (config/local.yaml → sell_voice_cps) thì dùng ĐÚNG tốc độ đó (nhanh hơn cũng theo) → bài đủ dài cho voice phủ
    kín video; chưa đo thì voice_cps của config/sell.yaml, không có nữa thì max_cps của config/dub.yaml."""
    from app.director.tasks import effective_cps

    dub = config.load("dub")
    return effective_cps({**dub, "max_cps": {**(dub.get("max_cps") or {}), **(cfg.get("voice_cps") or {})},
                          "measured_key": "sell_voice_cps", "measured_override": True}, language)


def _scene_of(t: float, scenes: list[dict]) -> dict | None:
    return next((s for s in scenes if s["start"] - 1e-6 <= t <= s["end"] + 1e-6), None)


def check_sell_script(r, language: str, *, duration: float, scenes: list[dict], cps: float, target_s: float,
                      cfg: dict, banned: list[tuple[float, float]] | None = None, title_max: int = 12,
                      video_index: int = 1) -> list[str]:
    from app.director.policy import find_forbidden, overlap_s
    from app.director.tasks import check_target_language, speech_chars

    errors = check_target_language(r, language)
    roles = [ln.role for ln in r.lines]
    if roles[0] != "hook":
        errors.append("câu 1 phải có role \"hook\" (câu mở đầu thu hút)")
    if "hook" in roles[1:]:
        errors.append("chỉ câu 1 là \"hook\" — các câu sau là \"body\" (hoặc \"cta\" ở cuối)")
    if "cta" in roles and any(x != "cta" for x in roles[roles.index("cta"):]):
        errors.append("câu \"cta\" (kêu gọi hành động) chỉ đặt ở CUỐI bài")
    lo, hi = (cfg.get("script_fill") or [0.92, 1.03])[:2]
    gap = float(cfg.get("voice_gap_s", 0.08)) * max(0, len(r.lines) - 1)
    want = max(1.0, (target_s - gap) * cps)
    chars = sum(speech_chars(ln.text) for ln in r.lines)
    if not lo * want <= chars <= hi * want:
        errors.append(f"cả bài có {chars} chữ (đọc ~{chars / cps:.0f}s) — cần {int(lo * want)}–{int(hi * want)} chữ để "
                      f"video dài ~{target_s:.0f}s ở tốc độ ~{cps:.1f} chữ/giây: "
                      + ("viết thêm ý / câu" if chars < lo * want else "viết gọn bớt"))
    min_cut = float(cfg.get("min_cut_s", 1.0))
    for i, ln in enumerate(r.lines, 1):
        for s in ln.shots:
            if s.end <= s.start:
                errors.append(f"câu {i}: cảnh {s.start}-{s.end} có end ≤ start")
                continue
            if s.end > duration + 0.3 or s.start < 0:
                errors.append(f"câu {i}: cảnh {s.start}-{s.end} nằm ngoài video gốc (0–{duration:.1f}s)")
                continue
            if s.end - s.start < min_cut - 0.05:
                errors.append(f"câu {i}: cảnh {s.start}-{s.end} ngắn hơn {min_cut:.0f} giây")
            sc = _scene_of((s.start + s.end) / 2, scenes)
            if sc and (s.start < sc["start"] - 0.3 or s.end > sc["end"] + 0.3):
                errors.append(f"câu {i}: cảnh {s.start}-{s.end} vắt qua điểm đổi cảnh ({sc['start']:.1f}–{sc['end']:.1f}s) "
                              "— lấy gọn trong MỘT cảnh")
            if banned and overlap_s(s.start, s.end, banned) > 0.05:
                errors.append(f"câu {i}: cảnh {s.start}-{s.end} chứa đoạn vi phạm chính sách TikTok — chọn cảnh khác")
        bad = find_forbidden(ln.text, language)
        if bad:
            errors.append(f"câu {i} có từ không được phép trên TikTok ({', '.join(bad)}) — viết lại")
    for t in r.titles_top:
        if len(t) > title_max:
            errors.append(f"tiêu đề '{t}' dài {len(t)} ký tự — tối đa {title_max}")
        bad = find_forbidden(t, language)
        if bad:
            errors.append(f"tiêu đề '{t}' có từ không được phép trên TikTok ({', '.join(bad)}) — viết lại")
    if r.video_index != video_index:
        errors.append(f"video_index phải là {video_index}")
    return errors


ONSCREEN_YES = """CÓ chữ in trên hình (vùng: {regions}; {note}).
1. ĐỌC chữ trên TỪNG khung hình theo thứ tự thời gian (mở hết các file khung hình). Nếu đó là PHỤ ĐỀ / chữ thuyết minh
   (dòng chữ đổi theo lời / theo cảnh) thì đó là NỘI DUNG CHÍNH của video gốc: chép lại từng dòng (đúng chữ gốc, kèm giây
   khung hình đầu tiên thấy dòng đó) vào `onscreen_text`, không lặp dòng trùng.
2. Viết kịch bản BÁM SÁT phụ đề: đủ MỌI ý của phụ đề, đúng thứ tự (viết lại tự nhiên bằng ngôn ngữ đích, bản địa hóa,
   không dịch từng chữ), KHÔNG bỏ ý → bài đọc dài tương ứng nội dung phụ đề; vẫn thiếu so với thời lượng mục tiêu thì
   thêm chi tiết THẤY trong hình. Câu nói về ý của dòng phụ đề nào thì `shots` lấy đúng đoạn dòng đó hiện trên màn hình.
3. Chữ chỉ là logo / watermark / tên kênh (không đổi theo nội dung) thì bỏ qua, `onscreen_text` để rỗng, viết theo hình."""
ONSCREEN_NO = """KHÔNG có phụ đề trên hình → viết theo HÌNH ẢNH (và lời nói gốc nếu có): mỗi cảnh làm gì, có gì đáng nói,
đủ chi tiết để bài đọc đạt thời lượng mục tiêu. `onscreen_text` để rỗng."""


def _lines_text(previous) -> str:
    return "\n".join(f"{i}. [{ln.role}] {ln.text} ({ln.text_vi})" for i, ln in enumerate(previous.lines, 1))


def make_sell_script(director: Director, analysis_dir: Path, u, *, brief: str, sell_s: float | int = 0,
                     music_items: list | None = None, video_index: int = 1, feedback: str = "", previous=None):
    """AI xem khung hình + lời nói gốc, TỰ chọn góc kể theo nội dung gốc (chủ dự án 15/10 bỏ ô định hướng; `brief` chỉ còn
    cho job cũ đã nhập) → SellScript (lời + cảnh từng câu + tiêu đề + nhạc)."""
    from app.director.policy import cut_ranges
    from app.director.schemas import SellScript
    from app.director.tasks import (LANGUAGE_NAMES, MARKETS, _segments_in, _shared_context, load_analysis,
                                    localize_brief, pick_evenly)

    cfg = sell_cfg()
    a = load_analysis(analysis_dir)
    sc = a["scenes"]
    duration = float(sc["duration"])
    scenes = sc.get("scenes") or [{"start": 0.0, "end": duration}]
    target = sell_target(cfg, sell_s)
    cps = sell_cps(cfg, u.language)
    title_max = int((cfg.get("title_max_chars") or {}).get(u.language, 12))
    subs = bool(u.burned_in_text.present)
    # có chữ / phụ đề in trên hình → gửi DÀY khung (ghép ảnh lưới nên không tốn) để AI đọc đủ từng dòng phụ đề
    n = int(cfg.get("subtitle_frames", 70) if subs else cfg.get("frames", 40))
    firsts = {min(a["frames"], key=lambda f, t=s["start"]: abs(f["t"] - t))["file"]: None for s in scenes} \
        if a["frames"] else {}
    chosen = {f["file"]: f for f in a["frames"] if f["file"] in firsts}
    for f in pick_evenly(a["frames"], max(0, n - len(chosen))):
        chosen.setdefault(f["file"], f)
    frames = sorted(chosen.values(), key=lambda f: f["t"])[: max(n, 1)]
    segs = _segments_in(a["transcript"].get("segments", []), 0.0, duration)
    gap = float(cfg.get("voice_gap_s", 0.08))
    lo, hi = (cfg.get("script_fill") or [0.92, 1.03])[:2]
    music_lines = [f"- {m.name}{' (' + m.mood + ')' if m.mood else ''}, {m.material.get('duration', 0) / 1e6:.0f}s"
                   for m in (music_items or [])[:60]]
    ctx = _shared_context(u, segs, a.get("events"))
    variables = {**ctx, "video_index": video_index,
                 "language_name": LANGUAGE_NAMES.get(u.language, u.language),
                 "market": MARKETS.get(u.language, "TikTok"), "localize_brief": localize_brief(u),
                 "source_s": f"{duration:.0f}", "target_s": f"{target:.0f}", "cps": f"{cps:.1f}",
                 "target_chars": f"{int(lo * (target - gap * 12) * cps)}–{int(hi * target * cps)}",
                 "title_max": title_max,
                 "onscreen": (ONSCREEN_YES.format(regions=", ".join(u.burned_in_text.regions) or "không rõ",
                                                  note=u.burned_in_text.note_vi or "") if subs else ONSCREEN_NO),
                 "brief": (f"Chủ dự án có ghi thêm (ưu tiên làm theo): {brief.strip()}" if (brief or "").strip()
                           else "Chủ dự án không ghi gì thêm — bạn tự quyết hoàn toàn theo nội dung gốc."),
                 "music_list": "\n".join(music_lines) or "(không có bài nào — đặt name = null)",
                 "scenes": "\n".join(f"- C{i}: {s['start']:.1f}–{s['end']:.1f}s" for i, s in enumerate(scenes, 1)),
                 "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) or "(không có)",
                 "feedback": (f"Sửa ĐÚNG theo góp ý này, giữ cái hay của bản trước:\n{feedback.strip()}\n\nBản trước:\n"
                              f"{_lines_text(previous)}" if feedback.strip() and previous
                              else feedback.strip() or "(không có)")}
    banned = cut_ranges(u)
    names = {m.name for m in (music_items or [])}

    def repair(r):
        fixes = []
        if r.music.name and r.music.name not in names:
            fixes.append(f"bài nhạc '{r.music.name}' không có trong kho → để tool chọn theo không khí")
            r = r.model_copy(update={"music": r.music.model_copy(update={"name": None})})
        lines = []
        for i, ln in enumerate(r.lines, 1):  # cảnh lố đuôi video vài phần giây → cắt về hết video
            shots = [s.model_copy(update={"end": min(s.end, duration)}) for s in ln.shots if s.start < duration - 0.3]
            if len(shots) != len(ln.shots) or any(s.end != o.end for s, o in zip(shots, ln.shots)):
                fixes.append(f"câu {i}: cắt cảnh lố đuôi video về {duration:.1f}s")
            lines.append(ln.model_copy(update={"shots": shots or ln.shots}))
        return r.model_copy(update={"lines": lines}), fixes

    def extra(r) -> list[str]:
        return check_sell_script(r, u.language, duration=duration, scenes=scenes, cps=cps, target_s=target, cfg=cfg,
                                 banned=banned, title_max=title_max, video_index=video_index)

    return director.run("sell", variables, SellScript, [analysis_dir / f["file"] for f in frames],
                        extra_check=extra, repair=repair)


def sell_to_dub(r):
    """SellScript → DubScript (dùng chung trang voice / OmniVoice / dub_scripts.txt với các chế độ thuyết minh).
    story_vi = dàn ý → trang voice hiện cả bài để đọc liền một mạch (như review)."""
    from app.director.schemas import DubLine, DubScript

    lines = [DubLine(kind="narration", source_start=min(s.start for s in ln.shots),
                     source_end=max(s.end for s in ln.shots), text=ln.text, text_vi=ln.text_vi,
                     action_vi=ln.shots_vi, role=ln.role, shots=ln.shots) for ln in r.lines]
    return DubScript(video_index=r.video_index, lines=lines, editor_notes=r.editor_notes,
                     story_vi=r.outline_vi.strip() or "Bán content")


def sell_plan(r, default_ratio: str = "16:9"):
    """Kế hoạch dựng tối giản (không hỏi AI thêm lượt nào): tiêu đề + nhạc do AI chọn trong kịch bản; clip = các cảnh
    theo thứ tự câu (tool dựng lại theo voice khi ghi CapCut)."""
    from app.director.schemas import EditPlan, PlanClip

    clips = [PlanClip(source_start=s.start, source_end=s.end, repeat=True, purpose_vi=ln.shots_vi)
             for ln in r.lines for s in ln.shots]
    return EditPlan(video_index=r.video_index, titles_top=r.titles_top[:2], default_ratio=default_ratio, clips=clips,
                    music=r.music, editor_notes=r.editor_notes)


def short_voice(job_dir: Path, scripts: dict, sell_s: float | int = 0) -> dict[int, dict]:
    """Chủ dự án 15/10 ("voice thiếu, không đủ ý"): video nào có voice cả bài ngắn hơn short_voice_ratio × min_s →
    {video: {voice_s, need_s, target_s, rate, extra_chars}}. Còn thiếu file / không đọc được độ dài thì bỏ qua."""
    from app.planner import dub_io

    cfg = sell_cfg()
    need = float(cfg.get("min_s", 60.5))
    target = sell_target(cfg, sell_s)
    gap = float(cfg.get("voice_gap_s", 0.08))
    out = {}
    for i, script in scripts.items():
        secs = [dub_io.voice_seconds(f) if (f := dub_io.find_line_voice(job_dir, i, n)) else None
                for n in range(1, len(script.lines) + 1)]
        if not secs or any(x is None for x in secs):
            continue
        total = sum(secs) + gap * (len(secs) - 1)
        if total < need * float(cfg.get("short_voice_ratio", 0.95)):
            rate = dub_io.voice_rate(job_dir, i, script, min_lines=1) or 0.0
            out[i] = {"voice_s": total, "need_s": need, "target_s": target, "rate": rate,
                      "extra_chars": int(max(0.0, target - total) * rate) if rate else 0}
    return out
