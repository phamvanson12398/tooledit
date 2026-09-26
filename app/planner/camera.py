"""Góc máy tự động cho video nói chuyện (podcast / phỏng vấn): cắt cận người đang nói, đổi cỡ cảnh.

Footage podcast thường chỉ có một góc máy. Như một editor, ta "giả lập nhiều máy quay" bằng cách cắt các cỡ cảnh
khác nhau từ cùng một khung hình:
- `close`  cận mặt người đang nói (phóng to ~2 lần),
- `medium` trung cảnh người đang nói (~1.4 lần),
- `wide`   toàn cảnh (khung gốc) — mở đầu video, khi không rõ ai nói, và thỉnh thoảng để người xem định vị.

Ai đang nói: mỗi mốc 0.5 giây, bước phân tích lưu các khuôn mặt kèm độ cử động vùng miệng (subjects.json → faces).
Mặt được gom thành "người" theo vị trí ngang; trong mỗi câu thoại, người có miệng cử động nhiều nhất là người nói.
Cắt cảnh đúng lúc đổi người nói (đầu câu), câu dài thì đổi cận ↔ trung để hình không đứng yên.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.capcut_writer import Crop
from app.capcut_writer.layout import RATIOS


@dataclass
class Person:
    cx: float   # vị trí ngang trung bình của mặt (0..1)
    cy: float
    h: float    # chiều cao mặt trung bình (phần khung)


@dataclass
class Shot:
    start: float  # giây trong footage gốc
    end: float
    kind: str     # close | medium | wide
    person: int | None = None


def persons_from_faces(faces: list, min_share: float = 0.05, gap: float = 0.12) -> list[Person]:
    """Gom mặt thành người theo vị trí ngang (người ngồi yên một chỗ trong podcast)."""
    boxes = [b for _, bs in faces for b in bs]
    if not boxes:
        return []
    boxes.sort(key=lambda b: b[0] + b[2] / 2)
    groups, cur = [], [boxes[0]]
    for b in boxes[1:]:
        if (b[0] + b[2] / 2) - (cur[-1][0] + cur[-1][2] / 2) > gap:
            groups.append(cur)
            cur = [b]
        else:
            cur.append(b)
    groups.append(cur)
    samples = len(faces)
    people = []
    for g in groups:
        if len(g) < max(2, min_share * samples):
            continue  # mặt thoáng qua / nhận nhầm
        n = len(g)
        mean_cx = sum(b[0] + b[2] / 2 for b in g) / n
        spread = (sum((b[0] + b[2] / 2 - mean_cx) ** 2 for b in g) / n) ** 0.5
        motion = sum(b[4] if len(b) > 4 else 0.0 for b in g) / n
        if n > 5 and spread < 0.005 and motion < 0.002:
            continue  # đứng im tuyệt đối, miệng không cử động: logo / hình vẽ in sẵn, không phải người
        people.append(Person(cx=sum(b[0] + b[2] / 2 for b in g) / n, cy=sum(b[1] + b[3] / 2 for b in g) / n,
                             h=sum(b[3] for b in g) / n))
    return people


def nearest(people: list[Person], box) -> int:
    cx = box[0] + box[2] / 2
    return min(range(len(people)), key=lambda i: abs(people[i].cx - cx))


def active_person(faces: list, people: list[Person], start: float, end: float,
                  min_motion: float = 0.004) -> int | None:
    """Người có miệng cử động nhiều nhất trong [start, end]; None nếu không đo được."""
    if not people:
        return None
    score = [0.0] * len(people)
    for t, bs in faces:
        if start - 0.25 <= t <= end + 0.25:
            best: dict[int, float] = {}
            for b in bs:
                i = nearest(people, b)
                best[i] = max(best.get(i, 0.0), b[4] if len(b) > 4 else 0.0)
            for i, m in best.items():
                score[i] += m
    i = max(range(len(people)), key=lambda k: score[k])
    if score[i] <= min_motion:
        return 0 if len(people) == 1 else None
    return i


def merge_reactions(speech: list[dict], events: list[dict],
                    kinds: tuple[str, ...] = ("laugh", "cheer", "marker")) -> list[dict]:
    """Chèn các đoạn cười / hò reo vào danh sách câu thoại (không chồng nhau): trong lúc cười, cảnh cắt sang người
    đang cười (người có miệng cử động nhiều nhất) — cảnh phản ứng kiểu show giải trí."""
    reacts = sorted(({"start": e["start"], "end": e["end"]} for e in events if e.get("kind") in kinds),
                    key=lambda x: x["start"])
    if not reacts:
        return speech
    out: list[dict] = []
    for s in sorted(speech, key=lambda x: x["start"]):
        pieces = [(s["start"], s["end"])]
        for r in reacts:  # khoét phần trùng với đoạn cười ra khỏi câu thoại
            nxt = []
            for a, b in pieces:
                if r["end"] <= a or r["start"] >= b:
                    nxt.append((a, b))
                    continue
                if r["start"] > a:
                    nxt.append((a, r["start"]))
                if r["end"] < b:
                    nxt.append((r["end"], b))
            pieces = nxt
        out += [{"start": a, "end": b} for a, b in pieces if b - a > 0.05]
    return sorted(out + reacts, key=lambda x: x["start"])


def plan_shots(clip_start: float, clip_end: float, speech: list[dict], faces: list, people: list[Person],
               cfg: dict, opening: bool = False, since_wide: float = 0.0) -> tuple[list[Shot], float]:
    """Chia một clip thành các cảnh. speech: câu thoại [{start, end}] (giây gốc).
    Trả (danh sách cảnh, số giây kể từ cảnh toàn gần nhất) để clip sau nối tiếp nhịp."""
    min_shot = cfg.get("min_shot_s", 1.2)
    max_hold = cfg.get("max_hold_s", 5.0)
    wide_open = cfg.get("wide_open_s", 2.0)
    wide_every = cfg.get("wide_every_s", 20.0)

    # 1) lượt nói: mỗi câu → người nói; câu liền nhau cùng người thì gộp; cắt ở đầu câu
    turns: list[list] = []  # [start, end, person]
    for s in speech:
        a, b = max(clip_start, s["start"]), min(clip_end, s["end"])
        if b - a <= 0:
            continue
        p = active_person(faces, people, a, b)
        if turns and (turns[-1][2] == p or p is None):
            turns[-1][1] = b
        else:
            turns.append([a, b, p])
    if not turns:
        turns = [[clip_start, clip_end, active_person(faces, people, clip_start, clip_end)]]
    turns[0][0] = clip_start
    for x, y in zip(turns, turns[1:]):  # khoảng lặng giữa hai lượt thuộc về lượt trước
        x[1] = y[0]
    turns[-1][1] = clip_end
    merged: list[list] = []
    for t in turns:  # xen ngắn (ừ, à...) không đáng cắt cảnh → gộp vào lượt trước
        if merged and t[1] - t[0] < min_shot:
            merged[-1][1] = t[1]
        else:
            merged.append(t)
    if len(merged) > 1 and merged[0][1] - merged[0][0] < min_shot:
        merged[1][0] = merged[0][0]
        merged.pop(0)

    # 2) mỗi lượt → các cảnh: mở đầu toàn cảnh; lượt dài đổi cận ↔ trung; lâu không có toàn cảnh thì chèn
    shots: list[Shot] = []
    for a, b, p in merged:
        if p is None or not people:
            shots.append(Shot(a, b, "wide"))
            since_wide = 0.0
            continue
        cursor, kind = a, "close"
        if opening and not shots and b - a > wide_open + min_shot:
            shots.append(Shot(a, a + wide_open, "wide"))
            cursor, since_wide = a + wide_open, 0.0
        while cursor < b - 1e-6:
            piece_end = b if b - cursor <= max_hold + min_shot else cursor + max_hold
            piece_kind = kind
            if since_wide >= wide_every and piece_kind == "medium":
                piece_kind, since_wide = "wide", 0.0
            shots.append(Shot(cursor, piece_end, piece_kind, None if piece_kind == "wide" else p))
            since_wide += piece_end - cursor
            cursor = piece_end
            kind = "medium" if kind == "close" else "close"
    return shots, since_wide


def shot_crop(shot: Shot, people: list[Person], block_ratio: str, src_w: int, src_h: int, cfg: dict,
              fallback_cx: float = 0.5) -> Crop:
    """Vùng cắt cùng tỉ lệ với khối video, phóng theo cỡ cảnh, mặt người nói ở khoảng 40% từ trên xuống."""
    target = RATIOS.get(block_ratio, 16 / 9)
    src = src_w / src_h
    cw, ch = (target / src, 1.0) if src > target else (1.0, src / target)  # khung đầy đủ (cỡ toàn)
    if shot.kind == "wide" or shot.person is None or shot.person >= len(people):
        left = min(max(fallback_cx - cw / 2, 0.0), 1.0 - cw)
        return Crop(left=left, top=(1.0 - ch) / 2, right=left + cw, bottom=(1.0 - ch) / 2 + ch)
    person = people[shot.person]
    zoom = cfg.get("close_zoom", 2.0) if shot.kind == "close" else cfg.get("medium_zoom", 1.4)
    # mặt không được to quá khung: chiều cao mặt ≤ face_max của chiều cao khung cắt
    zoom = max(1.0, min(zoom, ch * cfg.get("face_max", 0.45) / max(person.h, 1e-3)))
    cw, ch = cw / zoom, ch / zoom
    left = min(max(person.cx - cw / 2, 0.0), 1.0 - cw)
    top = min(max(person.cy - 0.4 * ch, 0.0), 1.0 - ch)
    return Crop(left=left, top=top, right=left + cw, bottom=top + ch)
