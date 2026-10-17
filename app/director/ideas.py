"""Ý TƯỞNG TỪ VIDEO DÀI (chủ dự án yêu cầu 17/10): một video dài (vlog, du lịch, lịch sử…) làm KHO CẢNH.

1. Danh mục cảnh (`make_catalog`): AI xem từng phần ~10 phút SONG SONG, ghi cảnh nào có gì → plan/catalog.json (dùng lại).
2. Ý tưởng (`make_ideas`): AI đọc danh mục + gợi ý chủ đề / khán giả (nếu có), đề xuất nhiều ý tưởng short hấp dẫn — không
   cần bám câu chuyện gốc; mỗi ý tưởng kèm các cảnh dùng được. Ý tưởng thiếu cảnh thì tool bỏ (ghi lý do).
3. Chủ dự án tick ý tưởng muốn làm (bảng duyệt) → mỗi ý tưởng một short dựng như "Bán content"
   (`app.director.sell.make_sell_script(idea=…)`: chỉ chọn cảnh trong các cảnh của ý tưởng, tránh cảnh short khác đã dùng).
"""

from __future__ import annotations

import json
from pathlib import Path

from app import config
from app.director.base import Director


def ideas_cfg() -> dict:
    return config.load("ideas") or {}


def chunks(duration: float, chunk_s: float) -> list[tuple[float, float]]:
    """Chia [0, duration] thành các phần ~chunk_s giây (phần cuối quá ngắn thì gộp vào phần trước)."""
    import math

    if chunk_s <= 0 or duration <= chunk_s * 1.25:
        return [(0.0, duration)]
    n = math.ceil(duration / chunk_s)
    if duration - (n - 1) * chunk_s < chunk_s * 0.25:
        n -= 1
    step = duration / n
    return [(round(k * step, 2), round(duration if k == n - 1 else (k + 1) * step, 2)) for k in range(n)]


def check_catalog_part(r, lo: float, hi: float, min_shot: float) -> list[str]:
    errors = []
    for i, s in enumerate(r.shots, 1):
        if s.end <= s.start:
            errors.append(f"cảnh {i}: end ≤ start")
        elif s.start < lo - 0.5 or s.end > hi + 0.5:
            errors.append(f"cảnh {i} ({s.start}-{s.end}) nằm ngoài phần này ({lo:.1f}–{hi:.1f}s)")
        elif s.end - s.start < min_shot - 0.05:
            errors.append(f"cảnh {i} ({s.start}-{s.end}) ngắn hơn {min_shot:.0f} giây — gộp với cảnh liền kề")
    return errors


def repair_catalog_part(r, lo: float, hi: float, min_shot: float):
    """Kẹp cảnh về trong phần, bỏ cảnh vụn, sắp theo thời gian, cảnh chồng nhau thì cắt đầu cảnh sau."""
    fixes, out = [], []
    for s in sorted(r.shots, key=lambda s: s.start):
        a, b = max(lo, s.start), min(hi, s.end)
        if out and a < out[-1].end:
            a = out[-1].end
        if b - a < min_shot - 0.05:
            fixes.append(f"bỏ cảnh vụn {s.start}-{s.end}")
            continue
        if (a, b) != (s.start, s.end):
            fixes.append(f"chỉnh cảnh {s.start}-{s.end} → {a:.1f}-{b:.1f}")
        out.append(s.model_copy(update={"start": round(a, 2), "end": round(b, 2)}))
    return r.model_copy(update={"shots": out or r.shots}), fixes


def make_catalog(director: Director, analysis_dir: Path, plan_dir: Path, u, log=lambda m: None):
    """Danh mục cảnh của cả video (Catalog). Mỗi phần lưu riêng plan/catalog_parts/NN.json → lỗi giữa chừng chạy lại chỉ
    hỏi các phần còn thiếu; xong cả video ghi plan/catalog.json."""
    from app.director.schemas import Catalog
    from app.director.tasks import _segments_in, format_transcript, load_analysis, pick_evenly
    from app.jobs.parallel import run_parallel

    path = plan_dir / "catalog.json"
    if path.is_file():
        return Catalog.model_validate_json(path.read_text(encoding="utf-8"))
    cfg = ideas_cfg()
    a = load_analysis(analysis_dir)
    duration = float(a["scenes"]["duration"])
    scenes = a["scenes"].get("scenes") or [{"start": 0.0, "end": duration}]
    parts = chunks(duration, float(cfg.get("chunk_s", 600)))
    min_shot = float(cfg.get("min_shot_s", 1.0))
    n_frames = int(cfg.get("catalog_frames", 80))
    pdir = plan_dir / "catalog_parts"
    pdir.mkdir(parents=True, exist_ok=True)
    log(f"AI xem video ({duration / 60:.0f} phút) theo {len(parts)} phần để ghi danh mục cảnh…")

    def one(item):
        k, (lo, hi) = item
        f = pdir / f"{k:02d}.json"
        if f.is_file():
            return Catalog.model_validate_json(f.read_text(encoding="utf-8"))
        frames = pick_evenly([x for x in a["frames"] if lo - 0.01 <= x["t"] <= hi + 0.01], n_frames)
        sc = [s for s in scenes if s["end"] > lo and s["start"] < hi]
        variables = {
            "part": f"{k}/{len(parts)}", "lo": f"{lo:.1f}", "hi": f"{hi:.1f}", "min_shot": f"{min_shot:.0f}",
            "summary": u.summary_vi,
            "scenes": "\n".join(f"- {max(lo, s['start']):.1f}–{min(hi, s['end']):.1f}s" for s in sc) or "(không dò được)",
            "frames": "\n".join(f"- {Path(x['file']).name} — {x['t']:.1f}s" for x in frames) or "(không có)",
            "transcript": format_transcript(_segments_in(a["transcript"].get("segments", []), lo, hi), 6000)
            or "(không có lời nói)"}
        r = director.run("ideas_catalog", variables, Catalog, [analysis_dir / x["file"] for x in frames],
                         extra_check=lambda r: check_catalog_part(r, lo, hi, min_shot),
                         repair=lambda r: repair_catalog_part(r, lo, hi, min_shot))
        f.write_text(r.model_dump_json(indent=2), encoding="utf-8")
        log(f"Danh mục cảnh phần {k}/{len(parts)} ({lo / 60:.1f}–{hi / 60:.1f} phút): {len(r.shots)} cảnh.")
        return r

    results = run_parallel(one, list(enumerate(parts, 1)))
    cat = Catalog(shots=sorted((s for r in results for s in r.shots), key=lambda s: s.start),
                  editor_notes=" | ".join(r.editor_notes for r in results if r.editor_notes))
    path.write_text(cat.model_dump_json(indent=2), encoding="utf-8")
    return cat


def shot_id(i: int) -> str:
    return f"S{i}"


def catalog_text(cat, max_chars: int = 40000) -> str:
    lines = [f"- {shot_id(i)} [{s.start:.1f}–{s.end:.1f}s, {s.end - s.start:.0f}s, đẹp {s.quality}/5] {s.desc_vi}"
             + (f" ({', '.join(s.tags)})" if s.tags else "") for i, s in enumerate(cat.shots, 1)]
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[:max_chars] + "\n...(cắt bớt)"


def _footage_s(ranges: list[tuple[float, float]]) -> float:
    """Tổng giây KHÁC NHAU (gộp phần chồng nhau)."""
    total, end = 0.0, -1.0
    for a, b in sorted(ranges):
        if b <= end:
            continue
        total += b - max(a, end)
        end = b
    return total


def screen_ideas(r, cat, cfg: dict) -> tuple[list[dict], list[dict]]:
    """Ý tưởng → (giữ, bỏ). Giữ = có đủ min_footage_s giây cảnh khác nhau (cảnh đẹp ≥ min_quality)."""
    ids = {shot_id(i): s for i, s in enumerate(cat.shots, 1)}
    min_q = int(cfg.get("min_quality", 2))
    need = float(cfg.get("min_footage_s", 30))
    keep, drop = [], []
    for it in r.ideas:
        pool = [ids[x] for x in dict.fromkeys(x.strip().upper() for x in it.shots) if x in ids]
        pool = [s for s in pool if s.quality >= min_q] or pool
        secs = _footage_s([(s.start, s.end) for s in pool])
        row = {**it.model_dump(), "footage_s": round(secs, 1),
               "pool": [{"start": s.start, "end": s.end, "desc_vi": s.desc_vi} for s in sorted(pool, key=lambda s: s.start)]}
        if secs < need:
            drop.append({**row, "reason_vi": f"chỉ có {secs:.0f}s cảnh phù hợp (cần ≥ {need:.0f}s) — dễ lặp cảnh, video nhạt"})
        else:
            keep.append(row)
    return keep, drop


def make_ideas(director: Director, analysis_dir: Path, cat, u, *, brief: str = "", language: str = "ko",
               feedback: str = "", previous: list[dict] | None = None):
    """AI đề xuất ý tưởng short → (giữ, bỏ, editor_notes)."""
    from app.director.schemas import IdeaList
    from app.director.tasks import LANGUAGE_NAMES, MARKETS, load_analysis, pick_evenly

    cfg = ideas_cfg()
    a = load_analysis(analysis_dir)
    n = int(cfg.get("n_ideas", 8))
    # khung gửi kèm: khung gần giữa các cảnh ĐẸP nhất, rải đều cả video
    best = sorted(cat.shots, key=lambda s: -s.quality)[: int(cfg.get("idea_frames", 36)) * 2]
    picks = {}
    for s in sorted(best, key=lambda s: s.start):
        if a["frames"]:
            f = min(a["frames"], key=lambda f, t=(s.start + s.end) / 2: abs(f["t"] - t))
            picks[f["file"]] = f
    frames = pick_evenly(sorted(picks.values(), key=lambda f: f["t"]), int(cfg.get("idea_frames", 36)))
    ids = {shot_id(i) for i in range(1, len(cat.shots) + 1)}
    variables = {
        "n_ideas": n, "language_name": LANGUAGE_NAMES.get(language, language),
        "market": MARKETS.get(language, "TikTok"), "summary": u.summary_vi,
        "duration_min": f"{float(a['scenes']['duration']) / 60:.0f}",
        "min_footage_s": f"{float(cfg.get('min_footage_s', 30)):.0f}",
        "brief": (f"Chủ dự án gợi ý (ưu tiên bám theo): {brief.strip()}" if brief.strip()
                  else "Chủ dự án không gợi ý gì — bạn tự chọn chủ đề / khán giả hợp kho cảnh nhất."),
        "feedback": ((f"Chủ dự án góp ý về các ý tưởng lần trước — làm ĐÚNG theo góp ý:\n{feedback.strip()}\n\n"
                      "Các ý tưởng lần trước:\n" + "\n".join(f"- {p['title_vi']}: {p['angle_vi']}" for p in previous or []))
                     if feedback.strip() else "(không có)"),
        "catalog": catalog_text(cat),
        "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) or "(không có)"}

    def repair(r):
        fixes, ideas = [], []
        for k, it in enumerate(r.ideas, 1):
            good = [x.strip().upper() for x in it.shots if x.strip().upper() in ids]
            if len(good) != len(it.shots):
                fixes.append(f"ý tưởng {k}: bỏ mã cảnh không có trong danh mục")
            if good:
                ideas.append(it.model_copy(update={"shots": good}))
        return r.model_copy(update={"ideas": ideas or r.ideas}), fixes

    def extra(r) -> list[str]:
        keep, drop = screen_ideas(r, cat, cfg)
        if keep:
            return []
        return ["không ý tưởng nào đủ cảnh: " + "; ".join(f"{d['title_vi']}: {d['reason_vi']}" for d in drop)
                + " — chọn chủ đề hợp kho cảnh hơn, gom đủ cảnh cho mỗi ý tưởng"]

    r = director.run("ideas_list", variables, IdeaList, [analysis_dir / f["file"] for f in frames],
                     extra_check=extra, repair=repair)
    keep, drop = screen_ideas(r, cat, cfg)
    return keep, drop, r.editor_notes


def idea_videos(ideas: list[dict], duration: float) -> list[dict]:
    """Ý tưởng đã chọn → danh sách video của job (mỗi ý tưởng một video, cả video gốc là kho cảnh)."""
    return [{"index": i, "start": 0.0, "end": duration, "title_vi": it["title_vi"], "summary_vi": it["angle_vi"],
             "idea": {k: it[k] for k in ("title_vi", "angle_vi", "hook_vi", "kind_vi", "why_vi") if k in it},
             "pool": it["pool"], "footage_s": it.get("footage_s", 0)} for i, it in enumerate(ideas, 1)]


def idea_brief(v: dict, user_brief: str = "") -> str:
    it = v.get("idea") or {}
    out = [f"- Tên ý tưởng: {it.get('title_vi', v.get('title_vi', ''))}",
           f"- Góc kể: {it.get('angle_vi', v.get('summary_vi', ''))}",
           f"- Câu mở đầu gợi ý (viết lại tự nhiên bằng ngôn ngữ đích, được đổi cho hay hơn): {it.get('hook_vi', '')}"]
    if it.get("kind_vi"):
        out.append(f"- Kiểu video: {it['kind_vi']}")
    if user_brief.strip():
        out.append(f"- Gợi ý chủ đề / khán giả của chủ dự án: {user_brief.strip()}")
    return "\n".join(out)


def used_text(others: list) -> str:
    """Cảnh các short khác (cùng job) đã dùng → short này tránh lặp."""
    ranges = sorted({(s.start, s.end) for o in others for ln in o.lines for s in ln.shots})
    if not ranges:
        return "(chưa short nào — dùng thoải mái)"
    return ", ".join(f"{a:.1f}–{b:.1f}s" for a, b in ranges[:120])


def save_proposal(plan_dir: Path, keep: list[dict], drop: list[dict], notes: str) -> dict:
    data = {"ideas": True, "proposal": {"ideas": keep, "dropped": drop, "editor_notes": notes}, "videos": [],
            "confirmed": False}
    (plan_dir / "segments.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
