"""Nút "Quét tài nguyên": gom kho từ CapCut + assets/, tìm cái còn thiếu, tải bổ sung từ Freesound (CC0).

Thứ tự mục 7: (1) danh mục CapCut (quét mọi draft) → (2) kho local assets/ → (3) internet, chỉ khi người dùng
bật và có key, chỉ CC0 → (4) còn thiếu thì báo trên giao diện để người dùng tự thêm.
Không tải được tài nguyên của thư viện online CapCut bằng code: CapCut chỉ tải khi người dùng dùng nó trong app.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app import config

from . import freesound, ledger
from .local import scan_local

# từ khóa nhận ra SFX trong kho CapCut theo tên (tên bài CapCut thường là tiếng Anh)
SFX_KEYWORDS = {
    "pop": ("pop", "bubble", "ポン"), "whoosh": ("whoosh", "woosh"), "ding": ("ding", "bell", "chime"),
    "boom": ("boom", "impact", "hit"), "laugh": ("laugh", "haha", "笑"), "swoosh": ("swoosh", "swish"),
    "record_scratch": ("scratch",),
}
ENERGY_VI = {"low": "nhẹ nhàng", "mid": "vừa", "high": "sôi động"}


@dataclass
class ScanReport:
    capcut: dict[str, int] = field(default_factory=dict)
    local: dict[str, int] = field(default_factory=dict)
    needs: list[dict] = field(default_factory=list)       # {kind, tag, label, why, status, have}
    downloaded: list[dict] = field(default_factory=list)  # mục sổ nguồn vừa thêm
    errors: list[str] = field(default_factory=list)
    jobs_to_redo: list[str] = field(default_factory=list)
    download_enabled: bool = False


def job_missing(jobs_root: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Từ missing_assets.json của các job: loại SFX / mức nhạc còn thiếu → các job cần."""
    sfx, music = {}, {}
    root = Path(jobs_root)
    if not root.is_dir():
        return sfx, music
    for f in sorted(root.glob("*/missing_assets.json")):
        try:
            items = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for m in items:
            if m.get("kind") == "sfx":
                sfx.setdefault(str(m.get("what")), set()).add(f.parent.name)
            elif m.get("kind") == "music":
                music.setdefault(str(m.get("energy") or "mid"), set()).add(f.parent.name)
    return sfx, music


def scan_resources(drafts_root: Path, jobs_root: Path, assets_root: Path = ledger.ASSETS_ROOT, *,
                   download: bool = False, api_key: str = "", client=None, probe=None,
                   capcut_items: list | None = None) -> ScanReport:
    cfg = config.load("assets")
    fs = cfg.get("freesound", {})
    rep = ScanReport(download_enabled=bool(download and api_key))

    if capcut_items is None:
        from app.capcut_writer.library import scan_drafts

        capcut_items = scan_drafts(drafts_root, use_cache=False)  # quét mới, bỏ bộ nhớ đệm 60 giây
    for i in capcut_items:
        rep.capcut[i.kind] = rep.capcut.get(i.kind, 0) + 1

    def local_items():
        return scan_local(assets_root, probe) if probe else scan_local(assets_root)

    local = local_items()
    for i in local:
        rep.local[i.kind] = rep.local.get(i.kind, 0) + 1

    sfx_need_jobs, music_need_jobs = job_missing(jobs_root)
    capcut_sfx = [i.name.lower() for i in capcut_items if i.kind == "sfx"]
    capcut_music = sum(1 for i in capcut_items if i.kind == "music")

    def have_sfx(kind: str) -> int:
        n = sum(1 for i in local if i.kind == "sfx" and i.mood == kind)
        return n + sum(1 for name in capcut_sfx if any(k.lower() in name for k in SFX_KEYWORDS.get(kind, (kind,))))

    def have_music(energy: str) -> int:
        return sum(1 for i in local if i.kind == "music" and i.mood == energy)

    for kind, query in (cfg.get("sfx_queries") or {}).items():
        have = have_sfx(kind)
        jobs = sorted(sfx_need_jobs.get(kind, ()))
        why = f"job {', '.join(jobs)} đang thiếu" if jobs else "loại SFX đạo diễn hay dùng"
        rep.needs.append({"kind": "sfx", "tag": kind, "query": query, "label": f"SFX {kind}", "why": why,
                          "have": have, "status": "có sẵn" if have else "còn thiếu", "jobs": jobs})
    for energy, query in (cfg.get("music_queries") or {}).items():
        have = have_music(energy)
        jobs = sorted(music_need_jobs.get(energy, ()))
        needed = not have and (jobs or capcut_music < 5)
        rep.needs.append({"kind": "music", "tag": energy, "query": query,
                          "label": f"Nhạc nền {ENERGY_VI.get(energy, energy)}",
                          "why": f"job {', '.join(jobs)} đang thiếu" if jobs else f"kho CapCut có {capcut_music} bài",
                          "have": have + (capcut_music if not jobs else 0),
                          "status": "còn thiếu" if needed else "có sẵn", "jobs": jobs})

    if rep.download_enabled:
        for need in rep.needs:
            if need["status"] != "còn thiếu":
                continue
            is_sfx = need["kind"] == "sfx"
            lo, hi = fs.get("sfx_seconds", [0.1, 3.0]) if is_sfx else fs.get("music_seconds", [30, 180])
            count = int(fs.get("sfx_per_kind", 2) if is_sfx else fs.get("music_per_mood", 1))
            try:
                sounds = freesound.search(api_key, need["query"], min_s=lo, max_s=hi, count=count, client=client)
                for s in sounds:
                    path = freesound.download(s, Path(assets_root) / need["kind"] / need["tag"], client=client)
                    rep.downloaded.append(ledger.add(
                        assets_root, path, source="freesound", url=s.get("url", ""), license=s.get("license", ""),
                        author=s.get("username", ""), duration_us=int(float(s.get("duration") or 0) * 1_000_000),
                        extra={"name": s.get("name", ""), "tag": need["tag"], "kind": need["kind"]}))
            except freesound.FreesoundError as exc:
                rep.errors.append(str(exc))
                if "401" in str(exc):
                    break
                continue
            if sounds:
                need["status"] = "đã tải"
                need["have"] += len(sounds)
                rep.jobs_to_redo += need["jobs"]
            else:
                rep.errors.append(f"Freesound không có file CC0 phù hợp cho '{need['query']}'")
        if rep.downloaded:
            rep.local = {}
            for i in local_items():
                rep.local[i.kind] = rep.local.get(i.kind, 0) + 1
    rep.jobs_to_redo = sorted(set(rep.jobs_to_redo))
    return rep
