"""Tự quét kho tài nguyên từ MỌI dự án trong thư mục draft của CapCut.

Mọi nhạc, SFX, hiệu ứng, chuyển cảnh, filter, sticker, animation chữ mà người dùng từng dùng trong CapCut
đều nằm trong các draft (kèm id + đường dẫn cache). Tool gom lại, bỏ trùng, và chỉ giữ tài nguyên mà file
cache còn trên máy (để CapCut mở draft không phải tải lại). Không chép file nào ra ngoài CapCut.
"""

from __future__ import annotations

import time
from pathlib import Path

from .template import LibraryItem, extract_library, key_values, main_timeline_path, read_json

_CACHE: dict[str, tuple[float, list[LibraryItem]]] = {}
CACHE_SECONDS = 60


def draft_dirs(drafts_root: Path) -> list[Path]:
    root = Path(drafts_root)
    if not root.is_dir():
        return []
    return [d for d in sorted(root.iterdir()) if d.is_dir() and (d / "draft_meta_info.json").is_file()]


def cached_on_disk(item: LibraryItem) -> bool:
    """Tài nguyên có đường dẫn cache thì file phải còn; tài nguyên không có đường dẫn (animation) thì giữ."""
    path = item.material.get("path") or ""
    return not path or Path(path).exists()


def scan_drafts(drafts_root: Path, *, require_cached: bool = True, use_cache: bool = True) -> list[LibraryItem]:
    key = f"{Path(drafts_root)}|{require_cached}"
    if use_cache and key in _CACHE and time.time() - _CACHE[key][0] < CACHE_SECONDS:
        return list(_CACHE[key][1])
    items: list[LibraryItem] = []
    seen: set[tuple[str, str]] = set()
    for d in draft_dirs(drafts_root):
        try:
            timeline = read_json(main_timeline_path(d))
        except (OSError, ValueError):
            continue  # draft hỏng / đang ghi / bị mã hóa → bỏ qua
        for item in extract_library(timeline, key_values(d)):
            k = (item.kind, item.resource_id)
            if k in seen or (require_cached and not cached_on_disk(item)):
                continue
            seen.add(k)
            items.append(item)
    _CACHE[key] = (time.time(), items)
    return list(items)
