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
                      video_index: int = 1, pool_only: bool = False,
                      library: dict[str, float] | None = None, lib_share: float = 0.35, first: bool = True,
                      platform: str = "tiktok") -> list[str]:
    """pool_only (chế độ Ý tưởng từ video dài): `scenes` = các cảnh của ý tưởng — cảnh ngoài danh sách đó là lỗi.
    library = {mã cảnh kho chung: độ dài} AI được dùng (shot.lib); cảnh kho chiếm tối đa lib_share tổng cảnh.
    first=False (chương 2+ của Bán content YouTube): không có câu hook; platform="youtube": được nhắc YouTube / đăng ký."""
    from app.director.policy import find_forbidden, overlap_s
    from app.director.tasks import check_target_language, speech_chars

    errors = check_target_language(r, language)
    roles = [ln.role for ln in r.lines]
    if first and roles[0] != "hook":
        errors.append("câu 1 phải có role \"hook\" (câu mở đầu thu hút)")
    if "hook" in roles[1 if first else 0:]:
        errors.append(("chỉ câu 1 là \"hook\"" if first else "chương này không có câu \"hook\"")
                      + " — các câu là \"body\" (hoặc \"cta\" ở cuối)")
    if "cta" in roles and any(x != "cta" for x in roles[roles.index("cta"):]):
        errors.append("câu \"cta\" (kêu gọi hành động) chỉ đặt ở CUỐI bài")
    lo, hi = (cfg.get("script_fill") or [0.92, 1.03])[:2]
    gap = float(cfg.get("voice_gap_s", 0.08)) * max(0, len(r.lines) - 1)
    errors += check_inserts(r, language, duration=duration, target_s=target_s, cfg=cfg, banned=banned)
    ins_s = sum(max(0.0, x.end - x.start) for x in r.inserts)
    want = max(1.0, (target_s - ins_s - gap) * cps)
    chars = sum(speech_chars(ln.text) for ln in r.lines)
    if not lo * want <= chars <= hi * want:
        errors.append(f"cả bài có {chars} chữ (đọc ~{chars / cps:.0f}s) — cần {int(lo * want)}–{int(hi * want)} chữ để "
                      f"video dài ~{target_s:.0f}s ở tốc độ ~{cps:.1f} chữ/giây"
                      + (f" (đã trừ {ins_s:.0f}s đoạn giữ tiếng gốc)" if ins_s else "") + ": "
                      + ("viết thêm ý / câu" if chars < lo * want else "viết gọn bớt"))
    min_cut = float(cfg.get("min_cut_s", 1.0))
    lib_s = all_s = 0.0
    for i, ln in enumerate(r.lines, 1):
        for s in ln.shots:
            if s.end <= s.start:
                errors.append(f"câu {i}: cảnh {s.start}-{s.end} có end ≤ start")
                continue
            all_s += s.end - s.start
            if s.lib:  # cảnh lấy từ kho cảnh chung: giây tính trong cảnh kho
                lib_s += s.end - s.start
                if s.lib not in (library or {}):
                    errors.append(f"câu {i}: không có cảnh kho {s.lib} — chỉ dùng mã trong \"Kho cảnh chung\" (hoặc để "
                                  "lib rỗng, lấy cảnh video gốc)")
                elif s.end > library[s.lib] + 0.3:
                    errors.append(f"câu {i}: cảnh kho {s.lib} chỉ dài {library[s.lib]:.1f}s — {s.start}-{s.end} lố")
                elif s.end - s.start < min_cut - 0.05:
                    errors.append(f"câu {i}: cảnh kho {s.lib} {s.start}-{s.end} ngắn hơn {min_cut:.0f} giây")
                continue
            if s.end > duration + 0.3 or s.start < 0:
                errors.append(f"câu {i}: cảnh {s.start}-{s.end} nằm ngoài video gốc (0–{duration:.1f}s)")
                continue
            if s.end - s.start < min_cut - 0.05:
                errors.append(f"câu {i}: cảnh {s.start}-{s.end} ngắn hơn {min_cut:.0f} giây")
            sc = _scene_of((s.start + s.end) / 2, scenes)
            if pool_only and not sc:
                errors.append(f"câu {i}: cảnh {s.start}-{s.end} không nằm trong các cảnh của ý tưởng — chỉ lấy cảnh trong "
                              "danh sách \"Các cảnh dùng được\"")
                continue
            # video gốc cắt cảnh dày (game, montage: cảnh ~1s) thì cảnh vắt qua điểm cắt là tự nhiên — chỉ chặn ở cảnh dài
            if sc and sc["end"] - sc["start"] >= float(cfg.get("strict_scene_s", 2.5)) and \
                    (s.start < sc["start"] - 0.3 or s.end > sc["end"] + 0.3):
                errors.append(f"câu {i}: cảnh {s.start}-{s.end} vắt qua điểm đổi cảnh ({sc['start']:.1f}–{sc['end']:.1f}s) "
                              "— lấy gọn trong MỘT cảnh")
            if banned and overlap_s(s.start, s.end, banned) > 0.05:
                errors.append(f"câu {i}: cảnh {s.start}-{s.end} chứa đoạn vi phạm chính sách TikTok — chọn cảnh khác")
        bad = find_forbidden(ln.text, language, platform=platform)
        if bad:
            errors.append(f"câu {i} có từ không được phép ({', '.join(bad)}) — viết lại")
    if all_s and lib_s / all_s > lib_share + 1e-6:
        errors.append(f"cảnh từ kho chung chiếm {lib_s / all_s:.0%} tổng cảnh — tối đa {lib_share:.0%}: ưu tiên cảnh video "
                      "gốc, kho chỉ bù chỗ video gốc KHÔNG có cảnh khớp lời")
    for t in r.titles_top:
        if len(t) > title_max:
            errors.append(f"tiêu đề '{t}' dài {len(t)} ký tự — tối đa {title_max}")
        bad = find_forbidden(t, language, platform=platform)
        if bad:
            errors.append(f"tiêu đề '{t}' có từ không được phép ({', '.join(bad)}) — viết lại")
    if r.video_index != video_index:
        errors.append(f"video_index phải là {video_index}")
    return errors


def check_inserts(r, language: str, *, duration: float, target_s: float, cfg: dict,
                  banned: list[tuple[float, float]] | None = None) -> list[str]:
    """Đoạn GIỮ TIẾNG GỐC (chủ dự án 20/10): độ dài min_s–max_s, trong video, không chạm đoạn vi phạm, tổng ≤ max_share,
    phụ đề bằng ngôn ngữ đích."""
    from app.director.policy import overlap_s
    from app.director.tasks import wrong_language

    if not r.inserts:
        return []
    oc = cfg.get("orig_audio") or {}
    lo, hi = float(oc.get("min_s", 1.5)), float(oc.get("max_s", 10))
    errors = []
    for k, x in enumerate(r.inserts, 1):
        d = x.end - x.start
        if x.after_line > len(r.lines):
            errors.append(f"đoạn tiếng gốc {k}: after_line {x.after_line} > số câu ({len(r.lines)})")
        if x.end <= x.start or x.end > duration + 0.3:
            errors.append(f"đoạn tiếng gốc {k} ({x.start}-{x.end}) nằm ngoài video gốc (0–{duration:.1f}s)")
        elif not lo - 0.05 <= d <= hi + 0.05:
            errors.append(f"đoạn tiếng gốc {k} dài {d:.1f}s — mỗi đoạn {lo:.0f}–{hi:.0f} giây")
        if banned and overlap_s(x.start, x.end, banned) > 0.05:
            errors.append(f"đoạn tiếng gốc {k} chứa đoạn vi phạm chính sách TikTok — chọn đoạn khác")
        if x.text.strip() and wrong_language(x.text, language):
            errors.append(f"đoạn tiếng gốc {k}: phụ đề `text` phải DỊCH sang ngôn ngữ đích (không để nguyên lời gốc)")
    total = sum(max(0.0, x.end - x.start) for x in r.inserts)
    share = float(oc.get("max_share", 0.4))
    if total > share * target_s + 0.5:
        errors.append(f"các đoạn tiếng gốc dài {total:.0f}s — tối đa {share:.0%} thời lượng (~{share * target_s:.0f}s): "
                      "bớt đoạn, giọng đọc vẫn là chính")
    return errors


ORIG_NOTE = """BẠN TỰ QUYẾT có xen các đoạn GIỮ NGUYÊN TIẾNG GỐC hay không (kiểu "nửa thuyết minh, nửa tiếng gốc"): chỗ nào
lời / tiếng gốc ĐẮT hơn mọi lời kể (câu nói hay, câu chốt, phản ứng hài, tiếng hét / cười, cao trào, câu khách hàng khen
thật…) thì để người xem nghe thật — ghi vào `inserts`: `after_line` (đặt ngay sau câu đọc số mấy; 0 = mở video bằng tiếng
gốc), `start`–`end` giây gốc ({lo:.0f}–{hi:.0f} giây/đoạn, không cắt giữa câu nói), `text` = phụ đề DỊCH lời gốc sang ngôn
ngữ đích (rỗng nếu chỉ là tiếng động), `text_vi`, `why_vi`.
- Câu đọc TRƯỚC đoạn đó dẫn vào ("và đây là phản ứng của anh ấy…"), câu SAU nói tiếp ý — KHÔNG đọc lại điều nhân vật vừa
  nói. Tổng các đoạn ≤ {share:.0%} thời lượng; giọng đọc vẫn là chính. Video không có đoạn nào đắt thì để `inserts` rỗng.
- Thời lượng các đoạn tiếng gốc được TRỪ vào bài đọc (bài đọc ngắn lại tương ứng — tool tính số chữ sau khi trừ)."""


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


HOOK_STYLES = ["câu hỏi gây tò mò (người xem phải xem tiếp mới biết đáp án)",
               "con số / chi tiết lạ, gây sốc nhẹ ngay câu đầu",
               "tương phản / hé lộ kết quả trước rồi quay lại kể vì sao"]


def variant_brief(variant: tuple[int, int], others: list) -> str:
    i, n = variant
    if n <= 1:
        return "(chỉ làm một bản)"
    out = [f"Đây là BẢN {i}/{n} làm từ CÙNG video gốc — mỗi bản đăng riêng như một video khác, nên bản này phải KHÁC HẲN "
           f"các bản kia: góc kể khác, câu mở đầu kiểu khác, thứ tự cảnh khác, tiêu đề khác (vẫn đúng sự thật).",
           f"- Câu mở đầu bản này nên theo kiểu: {HOOK_STYLES[(i - 1) % len(HOOK_STYLES)]}."]
    for k, o in enumerate(others, 1):
        out.append(f"- Bản đã viết #{k}: mở đầu \"{o.lines[0].text}\" · tiêu đề {' / '.join(o.titles_top)} · dàn ý: "
                   f"{o.outline_vi[:160]} → KHÔNG lặp lại.")
    return "\n".join(out)


def _lines_text(previous) -> str:
    return "\n".join(f"{i}. [{ln.role}] {ln.text} ({ln.text_vi})" for i, ln in enumerate(previous.lines, 1))


def make_sell_script(director: Director, analysis_dir: Path, u, *, brief: str, sell_s: float | int = 0,
                     music_items: list | None = None, video_index: int = 1, feedback: str = "", previous=None,
                     variant: tuple[int, int] = (1, 1), others: list | None = None, idea: dict | None = None,
                     library: list[dict] | None = None):
    """AI xem khung hình + lời nói gốc, TỰ chọn góc kể theo nội dung gốc (chủ dự án 15/10 bỏ ô định hướng; `brief` chỉ còn
    cho job cũ đã nhập) → SellScript (lời + cảnh từng câu + tiêu đề + nhạc).
    variant = (bản thứ i, tổng n) — chủ dự án 17/10: một video gốc ra 2–3 bản KHÁC NHAU; others = SellScript các bản đã
    viết (bản này phải khác góc kể / câu mở đầu / thứ tự cảnh).
    idea = video của chế độ Ý tưởng từ video dài (app/director/ideas.py: {idea, pool, …}) — chỉ dùng cảnh trong `pool`
    (khung hình + lời nói gốc cũng chỉ lấy trong đó), others = short khác đã viết (tránh lặp cảnh).
    library = cảnh kho chung AI được bù khi video gốc thiếu cảnh khớp lời (app/scene_library.candidates).
    idea có khóa "chapter" (Bán content YouTube, app/director/youtube.chapter_job): viết lời MỘT chương — độ dài = giây
    chương, chỉ cảnh của chương, prompt yt_chapter.md, chương 2+ không có hook, được nhắc YouTube / kêu gọi đăng ký."""
    from app.director.policy import cut_ranges
    from app.director.schemas import SellScript
    from app.director.tasks import (LANGUAGE_NAMES, MARKETS, _segments_in, _shared_context, load_analysis,
                                    localize_brief, pick_evenly)

    cfg = sell_cfg()
    a = load_analysis(analysis_dir)
    sc = a["scenes"]
    duration = float(sc["duration"])
    scenes = sc.get("scenes") or [{"start": 0.0, "end": duration}]
    pool = [p for p in (idea or {}).get("pool") or [] if p["end"] > p["start"]]
    if idea is not None and pool:  # ý tưởng từ video dài: kho cảnh = các cảnh của ý tưởng
        scenes = [{"start": float(p["start"]), "end": float(p["end"]), "desc_vi": p.get("desc_vi", "")} for p in pool]
    chapter = (idea or {}).get("chapter")
    target = float(idea["seconds"]) if chapter else sell_target(cfg, sell_s)
    cps = sell_cps(cfg, u.language)
    title_max = int((cfg.get("title_max_chars") or {}).get(u.language, 12))
    subs = bool(u.burned_in_text.present)
    # có chữ / phụ đề in trên hình → gửi DÀY khung (ghép ảnh lưới nên không tốn) để AI đọc đủ từng dòng phụ đề
    n = int(cfg.get("subtitle_frames", 70) if subs else cfg.get("frames", 40))
    all_frames = a["frames"]
    if idea is not None and pool:
        from app.director.ideas import ideas_cfg

        n = int(ideas_cfg().get("script_frames", 40))
        if chapter:
            from app.director.youtube import yt_cfg

            n = int(yt_cfg().get("chapter_frames", 40))
        all_frames = [f for f in all_frames if _scene_of(f["t"], scenes)] or all_frames
    firsts = {min(all_frames, key=lambda f, t=s["start"]: abs(f["t"] - t))["file"]: None for s in scenes} \
        if all_frames else {}
    chosen = {f["file"]: f for f in all_frames if f["file"] in firsts}
    for f in pick_evenly(all_frames, max(0, n - len(chosen))):
        chosen.setdefault(f["file"], f)
    # video cắt cảnh dày (game, montage) → khung đầu cảnh nhiều hơn n: lấy rải đều CẢ video, không cắt cụt phần cuối
    frames = pick_evenly(sorted(chosen.values(), key=lambda f: f["t"]), max(n, 1))
    segs = _segments_in(a["transcript"].get("segments", []), 0.0, duration)
    if idea is not None and pool:
        segs = [x for x in segs if any(x["end"] > p["start"] and x["start"] < p["end"] for p in scenes)]
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
                 "title_max": title_max, "variants": variant_brief(variant, others or []),
                 "onscreen": (ONSCREEN_YES.format(regions=", ".join(u.burned_in_text.regions) or "không rõ",
                                                  note=u.burned_in_text.note_vi or "") if subs else ONSCREEN_NO),
                 "brief": (f"Chủ dự án có ghi thêm (ưu tiên làm theo): {brief.strip()}" if (brief or "").strip()
                           else "Chủ dự án không ghi gì thêm — bạn tự quyết hoàn toàn theo nội dung gốc."),
                 "music_list": "\n".join(music_lines) or "(không có bài nào — đặt name = null)",
                 "scenes": "\n".join(f"- C{i}: {s['start']:.1f}–{s['end']:.1f}s"
                                     + (f" — {s['desc_vi']}" if s.get("desc_vi") else "") for i, s in enumerate(scenes, 1)),
                 "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) or "(không có)",
                 "feedback": (f"Sửa ĐÚNG theo góp ý này, giữ cái hay của bản trước:\n{feedback.strip()}\n\nBản trước:\n"
                              f"{_lines_text(previous)}" if feedback.strip() and previous
                              else feedback.strip() or "(không có)")}
    from app.scene_library import cfg as lib_cfg, prompt_text

    lib_map = {it["id"]: float(it["duration"]) for it in library or []}
    lib_share = float(lib_cfg().get("max_share", 0.35))
    variables.update({"library": prompt_text(library or []), "lib_share": f"{lib_share:.0%}"})
    oc = cfg.get("orig_audio") or {}
    use_orig = idea is None and bool(oc.get("enabled", True))  # chỉ Bán content (không Ý tưởng / YouTube)
    variables["orig"] = (ORIG_NOTE.format(lo=float(oc.get("min_s", 1.5)), hi=float(oc.get("max_s", 10)),
                                          share=float(oc.get("max_share", 0.4)))
                         if use_orig else "(không dùng — `inserts` để rỗng)")
    task = "sell"
    if idea is not None:
        from app.director.ideas import idea_brief, used_text

        task = "ideas_script"
        variables.update({"used": used_text(others or []),
                          "footage_s": f"{sum(s['end'] - s['start'] for s in scenes):.0f}"})
        if chapter:
            from app.director.youtube import chapter_brief

            task = "yt_chapter"
            variables.update({"chapter": chapter_brief(idea), "brief": brief.strip() or "(không có)",
                              "target_chars": f"{int(lo * (target - gap * (target / 4)) * cps)}–{int(hi * target * cps)}"})
        else:
            variables["idea"] = idea_brief(idea, brief)
    banned = cut_ranges(u)
    names = {m.name for m in (music_items or [])}

    def repair(r):
        fixes = []
        if r.video_index != video_index:  # AI ghi nhầm số bản → tool sửa (không bắt hỏi lại)
            r = r.model_copy(update={"video_index": video_index})
        if chapter and chapter > 1 and any(ln.role == "hook" for ln in r.lines):  # chương giữa / cuối không có hook
            fixes.append("chương này không mở bằng hook → đổi câu \"hook\" thành \"body\"")
            r = r.model_copy(update={"lines": [ln.model_copy(update={"role": "body"}) if ln.role == "hook" else ln
                                               for ln in r.lines]})
        if r.music.name and r.music.name not in names:
            fixes.append(f"bài nhạc '{r.music.name}' không có trong kho → để tool chọn theo không khí")
            r = r.model_copy(update={"music": r.music.model_copy(update={"name": None})})
        lines = []
        for i, ln in enumerate(r.lines, 1):  # cảnh lố đuôi video vài phần giây → cắt về hết video
            shots = []
            for s in ln.shots:
                lib = s.lib.strip().upper()
                if lib:  # cảnh kho: lố đuôi cảnh kho vài phần giây → cắt về hết cảnh
                    shots.append(s.model_copy(update={"lib": lib, "end": min(s.end, lib_map.get(lib, s.end))}))
                elif s.start < duration - 0.3:
                    shots.append(s.model_copy(update={"end": min(s.end, duration)}))
            if len(shots) != len(ln.shots) or any(s.end != o.end for s, o in zip(shots, ln.shots)):
                fixes.append(f"câu {i}: cắt cảnh lố đuôi video về {duration:.1f}s")
            lines.append(ln.model_copy(update={"shots": shots or ln.shots}))
        inserts = []
        if use_orig:
            for x in sorted(r.inserts, key=lambda x: (x.after_line, x.start)):
                x = x.model_copy(update={"end": min(x.end, duration), "after_line": min(x.after_line, len(lines))})
                if x.end - x.start >= 0.5:
                    inserts.append(x)
        elif r.inserts:
            fixes.append("chế độ này không giữ tiếng gốc — bỏ các đoạn `inserts`")
        return r.model_copy(update={"lines": lines, "inserts": inserts}), fixes

    def extra(r) -> list[str]:
        return check_sell_script(r, u.language, duration=duration, scenes=scenes, cps=cps, target_s=target, cfg=cfg,
                                 banned=banned, title_max=title_max, video_index=video_index,
                                 pool_only=idea is not None and bool(pool), library=lib_map, lib_share=lib_share,
                                 first=not chapter or chapter == 1, platform="youtube" if chapter else "tiktok")

    return director.run(task, variables, SellScript, [analysis_dir / f["file"] for f in frames],
                        extra_check=extra, repair=repair)


def sell_to_dub(r):
    """SellScript → DubScript (dùng chung trang voice / OmniVoice / dub_scripts.txt với các chế độ thuyết minh).
    story_vi = dàn ý → trang voice hiện cả bài để đọc liền một mạch (như review)."""
    from app.director.schemas import DubLine, DubScript

    def own(ln):  # giây gốc chỉ tính cảnh của video gốc (cảnh kho chung có giây riêng)
        return [s for s in ln.shots if not s.lib] or ln.shots

    lines = [DubLine(kind="narration", source_start=min(s.start for s in own(ln)),
                     source_end=max(s.end for s in own(ln)), text=ln.text, text_vi=ln.text_vi,
                     action_vi=ln.shots_vi, role=ln.role, shots=ln.shots, keyword=ln.keyword.strip())
             for ln in r.lines]
    story = r.outline_vi.strip() or "Bán content"
    if r.inserts:  # nửa thuyết minh: báo chủ dự án chỗ nào giữ tiếng gốc (không cần thu voice ở đó)
        story += "\n🔊 Giữ tiếng gốc (không cần đọc): " + "; ".join(
            f"sau câu {x.after_line} — {x.start:.1f}–{x.end:.1f}s" + (f" ({x.text_vi})" if x.text_vi else "")
            for x in r.inserts)
    return DubScript(video_index=r.video_index, lines=lines, editor_notes=r.editor_notes, story_vi=story)


def sell_plan(r, default_ratio: str = "16:9"):
    """Kế hoạch dựng tối giản (không hỏi AI thêm lượt nào): tiêu đề + nhạc do AI chọn trong kịch bản; clip = các cảnh
    theo thứ tự câu (tool dựng lại theo voice khi ghi CapCut)."""
    from app.director.schemas import EditPlan, PlanClip

    clips = [PlanClip(source_start=s.start, source_end=s.end, repeat=True, lib=s.lib, purpose_vi=ln.shots_vi)
             for ln in r.lines for s in ln.shots]
    return EditPlan(video_index=r.video_index, titles_top=r.titles_top[:2], default_ratio=default_ratio, clips=clips,
                    music=r.music, editor_notes=r.editor_notes)


def short_voice(job_dir: Path, scripts: dict, sell_s: float | int = 0, *, need_s: float | None = None,
                target_s: float | None = None, ratio: float | None = None,
                extra_s: dict[int, float] | None = None) -> dict[int, dict]:
    """Chủ dự án 15/10 ("voice thiếu, không đủ ý"): video nào có voice cả bài ngắn hơn short_voice_ratio × min_s →
    {video: {voice_s, need_s, target_s, rate, extra_chars}}. Còn thiếu file / không đọc được độ dài thì bỏ qua."""
    from app.planner import dub_io

    cfg = sell_cfg()
    need = float(need_s if need_s is not None else cfg.get("min_s", 60.5))
    target = float(target_s) if target_s is not None else sell_target(cfg, sell_s)
    gap = float(cfg.get("voice_gap_s", 0.08))
    out = {}
    for i, script in scripts.items():
        secs = [dub_io.voice_seconds(f) if (f := dub_io.find_line_voice(job_dir, i, n)) else None
                for n in range(1, len(script.lines) + 1)]
        if not secs or any(x is None for x in secs):
            continue
        total = sum(secs) + gap * (len(secs) - 1) + float((extra_s or {}).get(i, 0.0))  # + đoạn giữ tiếng gốc
        if total < need * float(ratio if ratio is not None else cfg.get("short_voice_ratio", 0.95)):
            rate = dub_io.voice_rate(job_dir, i, script, min_lines=1) or 0.0
            out[i] = {"voice_s": total, "need_s": need, "target_s": target, "rate": rate,
                      "extra_chars": int(max(0.0, target - total) * rate) if rate else 0}
    return out
