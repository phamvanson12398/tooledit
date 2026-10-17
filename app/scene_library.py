"""KHO CẢNH CHUNG (chủ dự án yêu cầu 17/10).

- Lưu (`harvest`): job "Ý tưởng từ video dài" xong → cắt các cảnh ĐẸP của danh mục cảnh (quality ≥ min_quality, không có
  chữ in sẵn, không chạm đoạn vi phạm chính sách) ra file nhỏ H.264 không tiếng trong `library/clips/`, ghi
  `library/index.json` (mô tả, nhãn, tỉ lệ khung, nguồn, các job đã dùng). Kho chung cho mọi khách (chủ dự án chốt).
- Dùng (`candidates` → AI chọn trong kịch bản Bán content / Ý tưởng khi video gốc thiếu cảnh khớp lời): chỉ cảnh CÙNG tỉ lệ
  khung với video đang dựng (giữ khung gốc, không cắt), chưa dùng quá `max_uses` video, xếp theo độ hợp chủ đề.
- File kho được chép vào dự án CapCut khi đóng gói (`pack_media`) → xóa kho không làm hỏng dự án cũ.
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path

from app import config

_LOCK = threading.Lock()


def cfg() -> dict:
    return config.load("library") or {}


def root(c: dict | None = None) -> Path:
    r = Path((c if c is not None else cfg()).get("root") or "library")
    return r if r.is_absolute() else config.ROOT / r


def load_index(lib: Path) -> list[dict]:
    try:
        return json.loads((lib / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def save_index(lib: Path, items: list[dict]) -> None:
    lib.mkdir(parents=True, exist_ok=True)
    tmp = lib / "index.json.writing"
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, lib / "index.json")


def _size(lib: Path, items: list[dict]) -> int:
    total = 0
    for it in items:
        try:
            total += (lib / it["file"]).stat().st_size
        except OSError:
            pass
    return total


def picks(shots, banned: list[tuple[float, float]], c: dict) -> list[tuple[float, float, object]]:
    """Cảnh danh mục → các đoạn sẽ lưu (đầu, cuối, cảnh): đẹp, không chữ, đủ dài, không chạm đoạn vi phạm chính sách;
    cảnh dài thì lấy đoạn giữa dài max_s."""
    from app.director.policy import overlap_s

    min_q, lo_s, hi_s = int(c.get("min_quality", 4)), float(c.get("min_s", 2.0)), float(c.get("max_s", 12.0))
    out = []
    for s in shots:
        if s.quality < min_q or getattr(s, "text", False) or s.end - s.start < lo_s:
            continue
        a, b = s.start, s.end
        if b - a > hi_s:
            mid = (a + b) / 2
            a, b = mid - hi_s / 2, mid + hi_s / 2
        if banned and overlap_s(a, b, banned) > 0.05:
            continue
        out.append((round(a, 2), round(b, 2), s))
    return out


def harvest(job_id: str, source: Path, size: tuple[int, int], catalog, *, banned=None, log=lambda m: None,
            cut_fn=None, c: dict | None = None) -> int:
    """Cắt cảnh đẹp của `catalog` (video `source`, khung `size`) vào kho. Trả số cảnh mới lưu. Đã lưu từ job này thì bỏ
    qua đoạn trùng (chạy lại không nhân đôi)."""
    from app.analysis import ffmpeg
    from app.capcut_writer.layout import nearest_ratio

    c = c if c is not None else cfg()
    if not c.get("enabled", True):
        return 0
    lib = root(c)
    (lib / "clips").mkdir(parents=True, exist_ok=True)
    cut_fn = cut_fn or ffmpeg.run
    limit = float(c.get("max_gb", 10)) * 1024 ** 3
    ratio = nearest_ratio(*size)
    with _LOCK:
        items = load_index(lib)
    have = {(it.get("job_id"), round(it["src_start"], 1), round(it["src_end"], 1)) for it in items}
    used = _size(lib, items)
    added = []
    n0 = max((int(it["id"][1:]) for it in items if re.fullmatch(r"L\d+", it.get("id", ""))), default=0)
    for a, b, s in picks(catalog.shots, banned or [], c):
        if (job_id, round(a, 1), round(b, 1)) in have:
            continue
        if used >= limit:
            log(f"⚠️ Kho cảnh đầy ({c.get('max_gb', 10)} GB) — ngừng lưu thêm. Xóa bớt trong thư mục library\\clips "
                "hoặc tăng max_gb trong config/library.yaml.")
            break
        n0 += 1
        cid = f"L{n0}"
        rel = f"clips/{cid}_{job_id}.mp4"
        dst = lib / rel
        try:
            cut_fn(["-ss", f"{a:.3f}", "-i", str(source), "-t", f"{b - a:.3f}", "-map", "0:v:0", "-an", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", str(int(c.get("crf", 20))), "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(dst)])
        except Exception as exc:  # một cảnh lỗi không làm hỏng cả job
            log(f"⚠️ Không cắt được cảnh {a:.1f}–{b:.1f}s vào kho: {exc}")
            continue
        try:
            used += dst.stat().st_size
        except OSError:
            pass
        added.append({"id": cid, "file": rel, "desc_vi": s.desc_vi, "tags": list(s.tags), "quality": s.quality,
                      "duration": round(b - a, 2), "width": size[0], "height": size[1], "ratio": ratio,
                      "job_id": job_id, "source": source.name, "src_start": a, "src_end": b,
                      "added": datetime.now().strftime("%Y-%m-%d"), "used_by": []})
    if added:
        with _LOCK:  # nạp lại rồi gộp (job khác có thể vừa ghi)
            items = load_index(lib)
            taken = {it["id"] for it in items}
            for it in added:
                if it["id"] in taken:  # trùng mã do job khác ghi cùng lúc → đổi mã (giữ tên file)
                    n = max(int(x["id"][1:]) for x in items if re.fullmatch(r"L\d+", x["id"])) + 1
                    it["id"] = f"L{n}"
                items.append(it)
                taken.add(it["id"])
            save_index(lib, items)
    return len(added)


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", (text or "").lower()) if len(w) > 1}


def candidates(ratio: str, query: str, *, exclude_job: str = "", c: dict | None = None,
               items: list[dict] | None = None) -> list[dict]:
    """Cảnh kho AI được chọn cho video này: cùng tỉ lệ khung, chưa dùng quá max_uses video (job này đã dùng thì vẫn được
    — dựng lại / viết lại), file còn, không phải cảnh lấy từ chính job này; xếp theo số từ trùng với chủ đề."""
    c = c if c is not None else cfg()
    if not c.get("enabled", True):
        return []
    lib = root(c)
    items = load_index(lib) if items is None else items
    max_uses = int(c.get("max_uses", 3))
    q = _words(query)
    pool = [it for it in items if it.get("ratio") == ratio and it.get("job_id") != exclude_job
            and (len(it.get("used_by") or []) < max_uses or exclude_job in (it.get("used_by") or []))
            and (lib / it["file"]).is_file()]
    pool.sort(key=lambda it: (-len(q & _words(it.get("desc_vi", "") + " " + " ".join(it.get("tags") or []))),
                              len(it.get("used_by") or []), -int(it.get("quality", 3))))
    return pool[: int(c.get("prompt_max", 60))]


def prompt_text(cands: list[dict]) -> str:
    if not cands:
        return "(kho trống hoặc không có cảnh cùng khung — KHÔNG dùng `lib`)"
    return "\n".join(f"- {it['id']} [{it['duration']:.1f}s] {it.get('desc_vi', '')}"
                     + (f" ({', '.join(it['tags'])})" if it.get("tags") else "") for it in cands)


def sources(ids, c: dict | None = None) -> dict[str, dict]:
    """Mã cảnh kho → {path, width, height, duration} (để builder thêm nguồn video)."""
    lib = root(c)
    want = set(ids)
    return {it["id"]: {"path": str((lib / it["file"]).resolve()), "width": it["width"], "height": it["height"],
                       "duration": it["duration"]} for it in load_index(lib) if it["id"] in want}


def mark_used(ids, job_id: str, c: dict | None = None) -> None:
    want = set(ids)
    if not want:
        return
    lib = root(c)
    with _LOCK:
        items = load_index(lib)
        for it in items:
            if it["id"] in want and job_id not in (it.get("used_by") or []):
                it.setdefault("used_by", []).append(job_id)
        save_index(lib, items)
