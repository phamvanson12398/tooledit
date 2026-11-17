"""DỊCH CHỮ TRÊN MÀN HÌNH (chủ dự án yêu cầu 17/11 — thay chế độ "Chữ theo hành động" cùng ngày).

MỘT video, giữ NGUYÊN hình + tiếng gốc. MỘT lượt AI (`make_screen_texts`, prompt `textnote.md`) đọc các khung hình dày
(~1 giây / khung), chép MỌI chữ có sẵn trên màn hình (phụ đề cứng, chú thích, tiêu đề…) kèm vị trí (`box` trên khung gốc)
+ lúc hiện, và dịch sang ngôn ngữ đích. Máy chỉnh hộp / thời gian cho khít (`refine_items`, OpenCV trên khung đã trích).
Khi dựng: builder CHE chữ gốc bằng dải nền rồi viết chữ dịch đè lên (`build(screen_texts=…)`). Kế hoạch dựng tạo bằng code
(`textnote_plan`: cả video, tốc độ 1, không nhạc / chữ nhấn / phụ đề lời gốc).
"""

from __future__ import annotations

from pathlib import Path

from app import config
from app.director.base import Director


def textnote_cfg() -> dict:
    return config.load("textnote") or {}


def check_screen_texts(r, language: str, *, duration: float, cfg: dict) -> list[str]:
    from app.director.policy import find_forbidden
    from app.director.tasks import wrong_language

    errors = []
    min_box = float(cfg.get("min_box", 0.01))
    for k, it in enumerate(r.items, 1):
        if not (0 <= it.start < it.end <= duration + 0.5):
            errors.append(f"chữ {k} ({it.start}–{it.end}s) phải nằm trong video 0–{duration:.1f}s và end > start")
        l, t, rr, b = it.box
        if not (0 <= l < rr <= 1 and 0 <= t < b <= 1) or rr - l < min_box or b - t < min_box:
            errors.append(f"chữ {k}: `box` {it.box} sai — phải là [trái, trên, phải, dưới] trong 0..1, trái < phải, "
                          "trên < dưới, bao trọn dòng chữ gốc")
        if not it.text.strip() or not it.text_orig.strip():
            errors.append(f"chữ {k}: thiếu chữ gốc hoặc bản dịch (chữ rỗng)")
            continue
        same = it.text.strip() == it.text_orig.strip()  # tên riêng / số / thương hiệu giữ nguyên được
        if not same and wrong_language(it.text, language):
            errors.append(f"chữ {k}: bản dịch KHÔNG viết bằng ngôn ngữ đích ({language}) — `text` phải là ngôn ngữ đích, "
                          "nghĩa tiếng Việt ghi ở `text_vi`")
        bad = find_forbidden(it.text, language)
        if bad:
            errors.append(f"chữ {k}: có từ không được phép ({', '.join(bad[:3])}) — dịch nhẹ đi / bỏ")
    return errors


def _iou(a, b) -> float:
    l, t, r, bt = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, r - l) * max(0.0, bt - t)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def repair_screen_texts(r, duration: float, cfg: dict):
    """Tự sửa lỗi vặt: kẹp vào video / khung, sửa hộp ngược, xếp theo thời gian, GỘP các dòng giống hệt nhau nối tiếp
    (AI hay chép một phụ đề thành nhiều dòng theo từng khung), bỏ chữ hiện quá ngắn."""
    fixes, out = set(), []
    min_s = float(cfg.get("min_item_s", 0.5))
    for it in sorted(r.items, key=lambda x: x.start):
        l, t, rr, b = (min(1.0, max(0.0, float(v))) for v in it.box)
        box = [min(l, rr), min(t, b), max(l, rr), max(t, b)]
        if box != list(it.box):
            fixes.add("kẹp / sửa hộp chữ về trong khung")
        a, e = max(0.0, it.start), min(duration, it.end)
        if e <= a and it.end > it.start:
            continue
        cur = it.model_copy(update={"start": round(a, 2), "end": round(e, 2), "box": [round(v, 4) for v in box]})
        prev = out[-1] if out else None
        if prev and prev.text_orig.strip() == cur.text_orig.strip() and cur.start <= prev.end + 1.2 \
                and _iou(prev.box, cur.box) > 0.3:
            out[-1] = prev.model_copy(update={"end": max(prev.end, cur.end), "box": [
                min(prev.box[0], cur.box[0]), min(prev.box[1], cur.box[1]),
                max(prev.box[2], cur.box[2]), max(prev.box[3], cur.box[3])]})
            fixes.add("gộp các dòng chữ giống nhau nối tiếp")
            continue
        out.append(cur)
    kept = [x for x in out if x.end - x.start >= min_s - 1e-6]
    if len(kept) != len(out):
        fixes.add("bỏ chữ hiện quá ngắn")
    return r.model_copy(update={"items": kept}), sorted(fixes)


def make_screen_texts(director: Director, analysis_dir: Path, u, language: str, *, feedback: str = ""):
    from app.director.schemas import ScreenTextScript
    from app.director.tasks import (
        LANGUAGE_NAMES,
        MARKETS,
        format_transcript,
        load_analysis,
        pick_evenly,
    )

    cfg = textnote_cfg()
    a = load_analysis(analysis_dir)
    duration = float(a["scenes"]["duration"])
    frames = pick_evenly(sorted(a["frames"], key=lambda f: f["t"]), int(cfg.get("frames", 120)))
    variables = {
        "language_name": LANGUAGE_NAMES.get(language, language), "market": MARKETS.get(language, "TikTok"),
        "summary": u.summary_vi, "duration": f"{duration:.0f}",
        "frames": "\n".join(f"- {Path(f['file']).name} — {f['t']:.1f}s" for f in frames) or "(không có)",
        "transcript": format_transcript(a["transcript"].get("segments", []), int(cfg.get("transcript_chars", 3000)))
        or "(không có lời nói)",
        "feedback": feedback.strip() or "(không có)"}
    return director.run("textnote", variables, ScreenTextScript, [analysis_dir / f["file"] for f in frames],
                        extra_check=lambda r: check_screen_texts(r, language, duration=duration, cfg=cfg),
                        repair=lambda r: repair_screen_texts(r, duration, cfg))


def refine_items(r, frames: list[tuple[float, Path]], cfg: dict):
    """Máy chỉnh cho khít: trong vùng AI báo (nới `refine_expand`) tìm đúng chỗ có nét chữ → hộp mới; rồi xem các khung
    quanh đó để biết lúc chữ THẬT SỰ hiện / tắt. Không có OpenCV / không thấy nét chữ thì giữ nguyên bản AI.
    Trả (bản đã chỉnh, số chữ được chỉnh)."""
    try:
        import numpy as np

        from app.analysis.textdetect import _load, presence_times, text_map
    except ImportError:
        return r, 0
    if not frames:
        return r, 0
    frames = sorted(frames)
    grays = _load([p for _, p in frames], 480)
    timed = [(t, g) for (t, _), g in zip(frames, grays) if g is not None]
    if not timed:
        return r, 0
    ex = float(cfg.get("refine_expand", 0.3))
    dens = float(cfg.get("refine_density", 0.08))
    out, changed = [], 0
    for it in r.items:
        inside = [g for t, g in timed if it.start - 0.01 <= t <= it.end + 0.01]
        box = list(it.box)
        if inside:
            h, w = inside[0].shape[:2]
            bw, bh = box[2] - box[0], box[3] - box[1]
            reg = [max(0.0, box[0] - bw * ex), max(0.0, box[1] - bh * ex),
                   min(1.0, box[2] + bw * ex), min(1.0, box[3] + bh * ex)]
            x0, y0, x1, y1 = int(reg[0] * w), int(reg[1] * h), max(int(reg[2] * w), int(reg[0] * w) + 1), \
                max(int(reg[3] * h), int(reg[1] * h) + 1)
            heat = np.mean([text_map(g if g.shape[:2] == (h, w) else _resize(g, w, h))[y0:y1, x0:x1]
                            for g in inside], axis=0)
            ys, xs = np.nonzero(heat >= 0.3)
            if len(xs):
                nb = [reg[0] + xs.min() / w - 0.01, reg[1] + ys.min() / h - 0.01,
                      reg[0] + (xs.max() + 1) / w + 0.01, reg[1] + (ys.max() + 1) / h + 0.01]
                nb = [round(min(1.0, max(0.0, v)), 4) for v in nb]
                area = (nb[2] - nb[0]) * (nb[3] - nb[1])
                if 0.3 * bw * bh <= area <= 3.0 * bw * bh:
                    box = nb
        window = [(t, g) for t, g in timed if it.start - 1.5 <= t <= it.end + 1.5]
        spans = [s for s in presence_times(window, box, density=dens) if s[0] < it.end + 0.5 and s[1] > it.start - 0.5]
        a, e = (min(s[0] for s in spans), max(s[1] for s in spans)) if spans else (it.start, it.end)
        new = it.model_copy(update={"box": box, "start": round(max(0.0, a), 2), "end": round(max(a + 0.3, e), 2)})
        changed += new != it
        out.append(new)
    return r.model_copy(update={"items": out}), changed


def _resize(g, w: int, h: int):
    import cv2

    return cv2.resize(g, (w, h))


def keep_ranges(duration: float, cuts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Cả video trừ các đoạn vi phạm chính sách (giữ nguyên thứ tự)."""
    out, t = [], 0.0
    for a, b in sorted((max(0.0, a), min(duration, b)) for a, b in cuts):
        if a > t + 0.05:
            out.append((round(t, 3), round(a, 3)))
        t = max(t, b)
    if duration > t + 0.05:
        out.append((round(t, 3), round(duration, 3)))
    return out


def textnote_plan(r, duration: float, cuts: list[tuple[float, float]], default_ratio: str = "16:9"):
    """Kế hoạch dựng: cả video nguyên vẹn, tốc độ 1 (chỉ bỏ đoạn vi phạm). Chữ dịch do builder vẽ (`screen_texts`)."""
    from app.director.schemas import EditPlan, MusicChoice, PlanClip

    ranges = keep_ranges(duration, cuts) or [(0.0, round(duration, 3))]
    clips = [PlanClip(source_start=a, source_end=b, purpose_vi="giữ nguyên video gốc") for a, b in ranges]
    return EditPlan(video_index=1, titles_top=[], default_ratio=default_ratio, clips=clips,
                    music=MusicChoice(name=None, mood_vi="giữ tiếng gốc", energy="low"),
                    editor_notes=f"Giữ nguyên video gốc, dịch + che {len(r.items)} chữ trên màn hình."
                                 + (f" {r.editor_notes}" if r.editor_notes else ""))


def screen_items(r) -> list[dict]:
    """Dữ liệu cho builder: [{start, end, box, text}] (giây gốc, hộp trên khung gốc)."""
    return [{"start": it.start, "end": it.end, "box": list(it.box), "text": it.text.strip()}
            for it in r.items if it.text.strip()]
