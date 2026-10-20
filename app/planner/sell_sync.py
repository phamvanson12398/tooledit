"""BÁN CONTENT — dựng cảnh theo voice (chủ dự án yêu cầu 15/10).

Mỗi câu của kịch bản có các cảnh AI chọn (giây gốc, được đảo thứ tự). Tool đo độ dài voice THẬT của câu rồi cắt cảnh
cho dài đúng bằng câu + khoảng nghỉ:
- đủ phim: lấy khúc ở giữa từng cảnh (chia theo tỉ lệ độ dài), mỗi khúc ~`cut_s`, cảnh chuyển nhanh;
- thiếu ít: làm chậm nhẹ (≥ `min_speed`);
- thiếu nhiều: thêm cảnh khác — ưu tiên phần footage CHƯA dùng; phải dùng lại thì lấy khúc khác của cảnh và phản chiếu
  ngang (nếu được phép) cho khỏi lộ lặp, không đặt lại một cảnh trong vòng `reuse_gap` cảnh liền kề.
Video luôn dài ≥ `min_s` (> 60 giây): thiếu thì thêm cảnh sau câu cuối (nhạc chạy tiếp).
Cảnh AI lấy từ KHO CẢNH CHUNG (shot.lib, giây tính trong file kho — chủ dự án 17/10) đặt như cảnh thường nhưng không tính
vào phần footage gốc đã dùng; cảnh bù khi thiếu vẫn chỉ lấy trong video gốc.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SEC = 1_000_000


@dataclass
class _Usage:
    """Phần footage đã dùng (giây gốc) + thứ tự cảnh đã đặt — để chọn khúc chưa dùng, tránh lặp liền kề."""
    scenes: list[tuple[float, float]]
    used: list[tuple[float, float]] = field(default_factory=list)
    order: list[int] = field(default_factory=list)

    def scene_id(self, t: float) -> int:
        for i, (a, b) in enumerate(self.scenes):
            if a - 1e-6 <= t <= b + 1e-6:
                return i
        return -1

    def overlap(self, a: float, b: float) -> float:
        return sum(max(0.0, min(b, y) - max(a, x)) for x, y in self.used)

    def free(self, a: float, b: float) -> float:
        return (b - a) - min(b - a, self.overlap(a, b))

    def add(self, a: float, b: float) -> None:
        self.used.append((a, b))
        self.order.append(self.scene_id((a + b) / 2))


def _best_start(lo: float, hi: float, length: float, usage: _Usage) -> float:
    """Chỗ đặt một khúc dài `length` trong [lo, hi] ít trùng phần đã dùng nhất (ưu tiên giữa khoảng)."""
    if hi - lo <= length + 1e-6:
        return lo
    span = hi - lo - length
    cands = [lo + span * k / 4 for k in (2, 1, 3, 0, 4)]
    return min(cands, key=lambda s: (round(usage.overlap(s, s + length), 3), abs(s - (lo + span / 2))))


def build_sell(script, voice_s: dict[int, float], scenes: list[dict], duration: float, *, cps: float,
               cfg: dict | None = None, allow_mirror: bool = True, inserts: list | None = None,
               insert_out: list | None = None):
    """Trả (clips: list[PlanClip] theo thứ tự trên màn hình, windows: [(µs bắt đầu câu, giây, giây)] cho từng câu,
    ghi chú). Câu chưa có voice: tạm tính theo số chữ / cps (dựng thử trước khi thu).
    inserts (chủ dự án 20/10, nửa thuyết minh): các đoạn GIỮ TIẾNG GỐC (OrigInsert) đặt ngay sau câu `after_line` — hình +
    tiếng gốc nguyên vẹn (tốc độ 1, không lật, `keep_audio`), các câu sau lùi lại; insert_out nhận
    {"start", "end" (µs), "text", "text_vi"} để builder viết phụ đề dịch lời gốc."""
    from app.director.schemas import PlanClip
    from app.director.tasks import speech_chars

    cfg = cfg or {}
    gap = float(cfg.get("voice_gap_s", 0.08))
    cut_s = float(cfg.get("cut_s", 2.2))
    min_cut = float(cfg.get("min_cut_s", 1.0))
    max_cut = float(cfg.get("max_cut_s", 4.0))
    min_speed = float(cfg.get("min_speed", 0.85))
    min_total = float(cfg.get("min_s", 60.5))
    reuse_gap = int(cfg.get("reuse_gap", 2))
    mirror_ok = allow_mirror and bool(cfg.get("reuse_mirror", True))
    sc = [(float(s["start"]), float(s["end"])) for s in scenes if s["end"] - s["start"] >= 0.3] or [(0.0, duration)]
    usage = _Usage(sc)
    clips: list = []
    windows: list = []
    notes: list[str] = []
    est_n = n_slow = n_fill = n_reuse = 0
    t = 0.0

    lib_usage: dict[str, _Usage] = {}

    def put(a: float, b: float, speed: float, purpose: str, lib: str = "") -> float:
        """Đặt một khúc; dùng lại phần đã dùng → phản chiếu ngang. Trả thời lượng trên màn hình."""
        nonlocal n_reuse
        if lib:  # cảnh kho chung: file riêng, không đụng phần footage gốc đã dùng
            clips.append(PlanClip(source_start=round(a, 3), source_end=round(b, 3), speed=round(speed, 3), repeat=True,
                                  lib=lib, purpose_vi=purpose))
            lib_usage.setdefault(lib, _Usage([(a, b)])).used.append((a, b))
            return (b - a) / speed
        reused = usage.overlap(a, b) > 0.5 * (b - a)
        n_reuse += reused
        clips.append(PlanClip(source_start=round(a, 3), source_end=round(b, 3), speed=round(speed, 3), repeat=True,
                              mirror=True if (reused and mirror_ok) else None, purpose_vi=purpose))
        usage.add(a, b)
        return (b - a) / speed

    def put_span(a: float, b: float, speed: float, purpose: str, lib: str = "") -> float:
        """Một cảnh dài → chia thành nhiều khúc ~cut_s trên màn hình (không để một cảnh đứng quá max_cut)."""
        k = max(1, round((b - a) / speed / cut_s))
        w = (b - a) / k
        return sum(put(a + j * w, a + (j + 1) * w, speed, purpose, lib) for j in range(k))

    def filler(need: float, avoid: set[int], purpose: str) -> float:
        """Thêm cảnh khác cho đủ `need` giây: phần chưa dùng nhiều nhất trước, không lặp cảnh vừa đặt."""
        nonlocal n_fill
        if need <= 0.05:
            return 0.0
        need = max(need, min_cut)  # không thêm khúc vụn < min_cut (lố chút ít cũng được)
        got = 0.0
        guard = 0
        while need - got > 0.05 and guard < 50:
            guard += 1
            recent = set(usage.order[-reuse_gap:]) if reuse_gap > 0 else set()
            pool = [i for i, (a, b) in enumerate(sc) if b - a >= min_cut and i not in recent and i not in avoid] or \
                   [i for i, (a, b) in enumerate(sc) if b - a >= min_cut and i not in recent] or \
                   [i for i, (a, b) in enumerate(sc) if b - a >= min_cut] or list(range(len(sc)))
            i = max(pool, key=lambda k: (round(usage.free(*sc[k]), 2), -usage.order.count(k)))
            a, b = sc[i]
            rest = need - got
            length = min(rest if rest < max_cut else cut_s, b - a)
            if rest - length < min_cut and rest <= b - a:  # khúc cuối còn lẻ quá ngắn → gộp vào khúc này
                length = rest
            speed = 1.0
            if length < min(rest, cut_s) - 1e-6 and (b - a) / min_speed >= min(rest, cut_s):  # cảnh ngắn → chậm nhẹ
                speed = max(min_speed, (b - a) / min(rest, cut_s))
                length = b - a
            s = _best_start(a, b, length, usage)
            got += put(s, s + length, speed, purpose)
            n_fill += 1
        return got

    by_after: dict[int, list] = {}
    for x in inserts or []:
        by_after.setdefault(int(x.after_line), []).append(x)

    def put_inserts(after: int) -> float:
        got = 0.0
        for x in by_after.get(after, []):
            a, b = max(0.0, float(x.start)), min(duration, float(x.end))
            if b - a < 0.3:
                continue
            t0 = t + got
            clips.append(PlanClip(source_start=round(a, 3), source_end=round(b, 3), speed=1.0, repeat=True,
                                  keep_audio=True, purpose_vi=("🔊 tiếng gốc: " + (x.text_vi or x.why_vi))[:60]))
            usage.add(a, b)
            got += b - a
            if insert_out is not None:
                insert_out.append({"start": round(t0 * SEC), "end": round((t0 + b - a) * SEC), "text": x.text,
                                   "text_vi": x.text_vi})
        return got

    t += put_inserts(0)
    for no, ln in enumerate(script.lines, 1):
        v = voice_s.get(no)
        if not v:
            v = max(1.0, speech_chars(ln.text) / max(cps, 1e-6))
            est_n += 1
        slot = v + gap
        windows.append((round(t * SEC), v, v))
        shots = [(max(0.0, s.start), s.end if getattr(s, "lib", "") else min(duration, s.end), getattr(s, "lib", ""))
                 for s in (ln.shots or [])]
        shots = [x for x in shots if x[1] - x[0] >= 0.3] or \
            [(max(0.0, ln.source_start), min(duration, ln.source_end), "")]
        shots = [x for x in shots if x[1] - x[0] >= 0.3]
        total_src = sum(b - a for a, b, _ in shots)
        purpose = (ln.action_vi or ln.text_vi)[:60]
        got = 0.0
        if total_src >= slot:  # đủ phim: lấy khúc theo tỉ lệ từng cảnh, mỗi khúc ~cut_s
            for a, b, lib in shots:
                take = slot * (b - a) / total_src
                k = max(1, min(round(take / cut_s), int(take / min_cut) or 1))
                piece = take / k
                win = (b - a) / k
                for j in range(k):
                    lo, hi = a + j * win, a + (j + 1) * win
                    s = _best_start(lo, hi, piece, lib_usage.get(lib) or _Usage([]) if lib else usage)
                    got += put(s, s + piece, 1.0, purpose, lib)
        elif total_src / min_speed >= slot:  # thiếu ít: chậm nhẹ cả câu
            speed = total_src / slot
            n_slow += 1
            for a, b, lib in shots:
                got += put_span(a, b, speed, purpose, lib)
        else:  # thiếu nhiều: cảnh của câu ở tốc độ chậm nhẹ + thêm cảnh khác
            n_slow += 1
            for a, b, lib in shots:
                got += put_span(a, b, min_speed, purpose, lib)
            avoid = {usage.scene_id((a + b) / 2) for a, b, lib in shots if not lib}
            got += filler(slot - got, avoid, purpose)
        t += got
        t += put_inserts(no)
    if t < min_total:  # luôn dài hơn 60 giây: thêm cảnh sau câu cuối (nhạc chạy tiếp)
        add = filler(min_total - t, set(), "cảnh kết (nhạc chạy tiếp)")
        notes.append(f"Bài đọc dài {t:.1f}s < {min_total:.0f}s — thêm {add:.1f}s cảnh kết sau câu cuối.")
        t += add
    n_ins = sum(1 for c in clips if c.keep_audio)
    notes.insert(0, f"Dựng theo voice: {len(script.lines)} câu → {len(clips)} cảnh, dài {t:.1f}s"
                    + (f"; {n_ins} đoạn giữ tiếng gốc" if n_ins else "")
                    + (f"; {n_slow} câu làm chậm nhẹ" if n_slow else "")
                    + (f"; thêm {n_fill} cảnh cho đủ thời lượng" if n_fill else "")
                    + (f"; {n_reuse} cảnh dùng lại" + (" (đã phản chiếu ngang)" if mirror_ok else "") if n_reuse else "")
                    + (f" ({est_n} câu chưa có voice — tạm tính theo số chữ, thu xong dựng lại)" if est_n else "") + ".")
    return clips, windows, notes


def sell_fx(script, windows: list, cfg: dict | None = None, *, emphasis: bool = True) -> dict:
    """Chữ nhấn + tiếng động theo voice (chủ dự án 17/10: video bớt "trơn", không zoom / cắt khung):
    - chữ nhấn `keyword` của câu hiện to giữa màn ngay sau khi câu bắt đầu (`emphasis_delay_s`), dài ~`emphasis_s`;
    - tiếng "pop" ở câu mở đầu, whoosh / click / swoosh luân phiên mỗi lần đổi câu (bỏ các câu quá ngắn để khỏi dồn dập);
    - "click" khi chữ nhấn bật lên nếu lúc đó không có tiếng nào khác (chủ dự án 17/10: "thêm cả âm thanh click").
    windows = [(µs bắt đầu câu, giây đọc, …)] từ build_sell. Trả {"emphasis": [(µs, µs, chữ)], "sfx": [(µs, loại)]}."""
    cfg = cfg or {}
    fx = cfg.get("fx") or {}
    delay = round(float(fx.get("emphasis_delay_s", 0.15)) * SEC)
    em_s = float(fx.get("emphasis_s", 1.4))
    kinds = list(fx.get("line_sfx") if fx.get("line_sfx") is not None else ["whoosh", "click", "swoosh"])
    em_sfx = fx.get("emphasis_sfx", "click")
    min_gap = round(float(fx.get("sfx_min_gap_s", 2.5)) * SEC)
    out = {"emphasis": [], "sfx": []}
    last_sfx = None
    for no, (ln, win) in enumerate(zip(script.lines, windows), 1):
        if not win:
            continue
        start, secs = int(win[0]), float(win[1])
        kw = (getattr(ln, "keyword", "") or "").strip()
        if emphasis and kw:
            out["emphasis"].append((start + delay, round(min(em_s, max(0.6, secs - 0.2)) * SEC), kw))
        if no == 1 and fx.get("opening_sfx", "pop"):
            out["sfx"].append((start, fx.get("opening_sfx", "pop")))
            last_sfx = start
        elif kinds and (last_sfx is None or start - last_sfx >= min_gap):
            out["sfx"].append((max(0, start - round(0.12 * SEC)), kinds[(len(out["sfx"]) - 1) % len(kinds)]))
            last_sfx = start
    if em_sfx:  # "click" khi chữ nhấn bật lên — trừ khi sát một tiếng khác (khỏi chồng tiếng)
        near = round(0.6 * SEC)
        for t, _, _ in out["emphasis"]:
            if all(abs(t - s0) >= near for s0, _ in out["sfx"]):
                out["sfx"].append((t, em_sfx))
        out["sfx"].sort()
    return out
