"""CẮT ĐOẠN HAY THEO CHỦ ĐỀ (chủ dự án yêu cầu 14/11).

MỘT video dài → (1) AI tìm các ĐOẠN HAY từng phần ~`chunk_s` SONG SONG (prompt `topics_moments.md`, lưu
plan/topic_parts/NN.json, dùng lại cho các lần sau) → (2) AI gom đoạn thành CHỦ ĐỀ tự đặt (prompt `topics_group.md`) →
chủ dự án tick chủ đề → mỗi chủ đề MỘT video: các đoạn nối theo thứ tự AI chọn, GIỮ NGUYÊN hình + tiếng gốc, phụ đề lời gốc
(kế hoạch dựng tạo bằng code — `topic_plan`). Độ dài tự do (chủ dự án tự edit tiếp).
"""

from __future__ import annotations

import json
from pathlib import Path

from app import config
from app.director.base import Director


def topics_cfg() -> dict:
    return config.load("topics") or {}


def snap(t: float, segs: list[dict], key: str, within: float) -> float:
    """Kéo điểm cắt về đúng đầu câu (key="start") / cuối câu (key="end") gần nhất trong `within` giây."""
    near = [s[key] for s in segs if abs(s[key] - t) <= within]
    return min(near, key=lambda x: abs(x - t)) if near else t


def check_moments(r, lo: float, hi: float, min_s: float) -> list[str]:
    errors = []
    prev_end = None
    for k, m in enumerate(sorted(r.moments, key=lambda m: m.start), 1):
        if not (lo - 0.5 <= m.start < m.end <= hi + 0.5):
            errors.append(f"đoạn {k} ({m.start}–{m.end}s) phải nằm trong {lo:.1f}–{hi:.1f}s và end > start")
        elif m.end - m.start < min_s - 0.05:
            errors.append(f"đoạn {k} ({m.start}–{m.end}s) ngắn hơn {min_s:.0f} giây — gộp với ý liền kề hoặc bỏ")
        if prev_end is not None and m.start < prev_end - 0.3:
            errors.append(f"đoạn {k} ({m.start}–{m.end}s) chồng lên đoạn trước")
        prev_end = m.end
    return errors


def repair_moments(r, lo: float, hi: float, segs: list[dict], within: float):
    """Kẹp đoạn vào trong phần; điểm cắt lệch đầu / cuối câu chút ít thì kéo về đúng đầu / cuối câu (không cắt ngang)."""
    fixes, out = [], []
    for m in r.moments:
        a = max(lo, snap(m.start, segs, "start", within))
        b = min(hi, snap(m.end, segs, "end", within))
        if (a, b) != (m.start, m.end):
            fixes.append("kéo điểm cắt về đúng đầu / cuối câu")
        out.append(m.model_copy(update={"start": round(a, 2), "end": round(b, 2)}) if b > a else m)
    return r.model_copy(update={"moments": sorted(out, key=lambda m: m.start)}), sorted(set(fixes))


def make_moments(director: Director, analysis_dir: Path, plan_dir: Path, u, log=lambda m: None) -> list:
    """Mọi đoạn hay của cả video (theo thời gian). Mỗi phần lưu riêng → lỗi giữa chừng chạy lại chỉ hỏi phần còn thiếu."""
    from app.director.ideas import chunks
    from app.director.schemas import TopicMoments
    from app.director.tasks import (
        _segments_in,
        format_transcript,
        load_analysis,
        pick_evenly,
    )
    from app.jobs.parallel import run_parallel

    cfg = topics_cfg()
    a = load_analysis(analysis_dir)
    duration = float(a["scenes"]["duration"])
    segs = a["transcript"].get("segments", [])
    parts = chunks(duration, float(cfg.get("chunk_s", 600)))
    min_s = float(cfg.get("min_moment_s", 5))
    within = float(cfg.get("snap_s", 1.5))
    pdir = plan_dir / "topic_parts"
    pdir.mkdir(parents=True, exist_ok=True)
    log(f"AI xem video ({duration / 60:.0f} phút) theo {len(parts)} phần để tìm đoạn hay…")

    def one(item):
        k, (lo, hi) = item
        f = pdir / f"{k:02d}.json"
        if f.is_file():
            return TopicMoments.model_validate_json(f.read_text(encoding="utf-8"))
        frames = pick_evenly([x for x in a["frames"] if lo - 0.01 <= x["t"] <= hi + 0.01], int(cfg.get("frames", 40)))
        variables = {
            "part": f"{k}/{len(parts)}", "lo": f"{lo:.1f}", "hi": f"{hi:.1f}", "min_s": f"{min_s:.0f}",
            "summary": u.summary_vi,
            "frames": "\n".join(f"- {Path(x['file']).name} — {x['t']:.1f}s" for x in frames) or "(không có)",
            "transcript": format_transcript(_segments_in(segs, lo, hi), int(cfg.get("transcript_chars", 9000)))
            or "(không có lời nói)"}
        r = director.run("topics_moments", variables, TopicMoments, [analysis_dir / x["file"] for x in frames],
                         extra_check=lambda r: check_moments(r, lo, hi, min_s),
                         repair=lambda r: repair_moments(r, lo, hi, segs, within))
        f.write_text(r.model_dump_json(indent=2), encoding="utf-8")
        log(f"Phần {k}/{len(parts)} ({lo / 60:.1f}–{hi / 60:.1f} phút): {len(r.moments)} đoạn hay.")
        return r

    results = run_parallel(one, list(enumerate(parts, 1)))
    return sorted((m for r in results for m in r.moments), key=lambda m: m.start)


def moments_text(moments: list) -> str:
    return "\n".join(f"- M{i} [{m.start:.1f}–{m.end:.1f}s, {m.end - m.start:.0f}s] ({m.topic_vi or '?'}) {m.summary_vi}"
                     + (f" — hay vì: {m.why_vi}" if m.why_vi else "") for i, m in enumerate(moments, 1))


def check_topics(r, n: int) -> list[str]:
    errors, seen = [], {}
    for t, g in enumerate(r.topics, 1):
        for i in g.moments:
            if not 1 <= i <= n:
                errors.append(f"chủ đề {t}: không có đoạn M{i} (chỉ có M1–M{n})")
            elif i in seen:
                errors.append(f"đoạn M{i} nằm ở cả chủ đề {seen[i]} và {t} — mỗi đoạn chỉ thuộc MỘT chủ đề")
            else:
                seen[i] = t
    return errors


def repair_topics(r, max_topics: int):
    fixes = []
    topics = []
    for g in r.topics:  # mã lặp trong CÙNG một chủ đề → giữ lần đầu
        ids = list(dict.fromkeys(g.moments))
        if ids != g.moments:
            fixes.append("bỏ mã đoạn lặp trong một chủ đề")
        topics.append(g.model_copy(update={"moments": ids}))
    if len(topics) > max_topics:
        fixes.append(f"chỉ giữ {max_topics} chủ đề đầu")
        topics = topics[:max_topics]
    return r.model_copy(update={"topics": topics}), fixes


def make_topics(director: Director, moments: list, u, *, feedback: str = "", previous: list[dict] | None = None):
    from app.director.schemas import TopicList

    cfg = topics_cfg()
    max_topics = int(cfg.get("max_topics", 15))
    prev = "\n".join(f"- {p.get('title_vi', '')}: {p.get('summary_vi', '')}" for p in previous or []) or "(không có)"
    variables = {"summary": u.summary_vi, "moments": moments_text(moments), "max_topics": max_topics,
                 "feedback": feedback.strip() or "(không có)", "previous": prev}
    return director.run("topics_group", variables, TopicList,
                        extra_check=lambda r: check_topics(r, len(moments)),
                        repair=lambda r: repair_topics(r, max_topics))


def proposal(r, moments: list) -> list[dict]:
    """Đề xuất hiện trên bảng tick: mỗi chủ đề kèm các đoạn (giây gốc) theo thứ tự dựng."""
    out = []
    for g in r.topics:
        ms = [moments[i - 1] for i in g.moments if 1 <= i <= len(moments)]
        if not ms:
            continue
        out.append({"title_vi": g.title_vi, "summary_vi": g.summary_vi, "why_vi": g.why_vi,
                    "moments": [{"start": m.start, "end": m.end, "note": m.summary_vi} for m in ms],
                    "seconds": round(sum(m.end - m.start for m in ms), 1)})
    return out


def save_proposal(plan_dir: Path, topics: list[dict], moments: list, notes: str) -> None:
    data = {"topics": True, "proposal": {"topics": topics, "editor_notes": notes,
                                         "moments": [m.model_dump() for m in moments]},
            "videos": [], "confirmed": False}
    (plan_dir / "segments.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def topic_videos(chosen: list[dict]) -> list[dict]:
    """Chủ đề đã tick → video: start / end = đoạn sớm / muộn nhất (để các bước khác dùng), `moments` = thứ tự dựng."""
    return [{"index": i, "start": min(m["start"] for m in t["moments"]), "end": max(m["end"] for m in t["moments"]),
             "title_vi": t["title_vi"], "summary_vi": t["summary_vi"], "moments": t["moments"]}
            for i, t in enumerate(chosen, 1)]


def topic_plan(video: dict, default_ratio: str = "16:9"):
    """Kế hoạch dựng: các đoạn nối theo thứ tự chủ đề, nguyên vẹn, tốc độ 1 — không hiệu ứng / nhạc / chữ thêm."""
    from app.director.schemas import EditPlan, MusicChoice, PlanClip

    clips = [PlanClip(source_start=m["start"], source_end=m["end"], purpose_vi=m.get("note", "")[:120])
             for m in video["moments"]]
    return EditPlan(video_index=video["index"], titles_top=[], default_ratio=default_ratio, clips=clips,
                    music=MusicChoice(name=None, mood_vi="giữ tiếng gốc", energy="low"),
                    editor_notes=f"Chủ đề: {video.get('title_vi', '')} — giữ nguyên hình + tiếng gốc, nối "
                                 f"{len(clips)} đoạn hay.")


def package_text(videos: list[dict]) -> str:
    """deliver/chu_de.txt: danh sách video + chủ đề + các đoạn (giây gốc) để chủ dự án edit tiếp."""
    def ts(t: float) -> str:
        t = round(t)
        return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"

    out = []
    for v in videos:
        total = sum(m["end"] - m["start"] for m in v["moments"])
        out.append(f"=== VIDEO {v['index']:02d} — {v.get('title_vi', '')} ({ts(total)}) ===")
        if v.get("summary_vi"):
            out.append(v["summary_vi"])
        out += [f"  {k}. {ts(m['start'])}–{ts(m['end'])}  {m.get('note', '')}" for k, m in enumerate(v["moments"], 1)]
        out.append("")
    return "\n".join(out)
