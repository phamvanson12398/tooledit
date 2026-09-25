"""Kho âm thanh local trong assets/ (nhạc, SFX), đưa vào danh mục cho đạo diễn chọn như tài nguyên CapCut.

Bố cục thư mục (thư mục con = nhãn):
    assets/sfx/<loại>/*.mp3      ví dụ assets/sfx/pop/, assets/sfx/whoosh/
    assets/music/<năng lượng>/   low | mid | high (hoặc tên tâm trạng bất kỳ)
File local được ghi vào draft như âm thanh trên máy (giống voice hook), không phải tài nguyên thư viện CapCut.
"""

from __future__ import annotations

from pathlib import Path

from app.capcut_writer.template import LibraryItem

from . import ledger

AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac")
KINDS = ("sfx", "music")


def probe_duration_us(path: Path) -> int:
    from app.capcut_writer.media import ffprobe_json

    info = ffprobe_json(Path(path))
    return int(round(float(info.get("format", {}).get("duration") or 0) * 1_000_000))


def scan_local(assets_root: Path = ledger.ASSETS_ROOT, probe=probe_duration_us) -> list[LibraryItem]:
    """Mọi file âm thanh trong assets/sfx và assets/music. Độ dài lấy từ sổ nguồn, không có thì đo bằng ffprobe."""
    assets_root = Path(assets_root)
    known = ledger.by_file(assets_root)
    items: list[LibraryItem] = []
    for kind in KINDS:
        base = assets_root / kind
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if f.suffix.lower() not in AUDIO_EXTS or not f.is_file():
                continue
            rel = f.relative_to(assets_root).as_posix()
            tag = f.parent.name if f.parent != base else ""
            duration = int(known.get(rel, {}).get("duration_us") or 0)
            if not duration:
                try:
                    duration = probe(f)
                except Exception:
                    continue  # không đo được (thiếu ffprobe / file hỏng) → bỏ qua
            items.append(LibraryItem(
                kind=kind, name=f"{tag}_{f.stem}" if tag else f.stem, resource_id=f"local:{rel}",
                material={"local": True, "path": str(f.resolve()), "duration": duration},
                category="local", mood=tag))
    return items


def is_local(item: LibraryItem) -> bool:
    return bool(item.material.get("local"))
