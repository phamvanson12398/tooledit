"""Lấy tài nguyên (hiệu ứng, chuyển cảnh, filter, sticker, animation chữ, nhạc, SFX) từ MỘT dự án CapCut
vào kho — kể cả dự án ở máy khác (tải lên file .zip) hoặc dự án sau này bị xóa khỏi CapCut.

- Tài nguyên thư viện CapCut chỉ được THAM CHIẾU trong draft (không chép file nhạc/hiệu ứng từ cache CapCut ra ngoài).
  Chúng được lưu vào danh mục `assets/capcut_library.json`. Dùng được ngay nếu CapCut trên máy này đã tải về
  (file cache còn). Nếu chưa: chép dự án vào thư mục CapCut, mở nó 1 lần để CapCut tự tải, rồi quét lại.
- File âm thanh CỦA NGƯỜI DÙNG trong dự án (nhạc/voice tự thêm từ máy, không nằm trong cache CapCut) được chép
  vào kho assets/ và ghi sổ nguồn.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import date
from pathlib import Path

from app.capcut_writer.library import cached_on_disk
from app.capcut_writer.template import (
    SFX_MAX_US, LibraryItem, extract_library, key_values, main_timeline_path, read_json,
)

from . import ledger
from .freesound import slug
from .local import AUDIO_EXTS

STORE = "capcut_library.json"
KIND_VI = {"video_effect": "hiệu ứng", "transition": "chuyển cảnh", "filter": "filter", "sticker": "sticker",
           "text_animation": "animation chữ", "music": "nhạc", "sfx": "SFX"}


def store_path(assets_root: Path) -> Path:
    return Path(assets_root) / STORE


def load_store(assets_root: Path = ledger.ASSETS_ROOT) -> list[dict]:
    p = store_path(assets_root)
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("items", [])
    except (OSError, ValueError):
        return []


def load_imported(assets_root: Path = ledger.ASSETS_ROOT, require_cached: bool = True) -> list[LibraryItem]:
    """Tài nguyên đã nhập từ dự án CapCut (để gộp vào kho khi dựng). Mặc định chỉ lấy cái CapCut đã tải về máy."""
    out = []
    for d in load_store(assets_root):
        item = LibraryItem.from_json(d)
        if not require_cached or cached_on_disk(item):
            out.append(item)
    return out


def find_draft_dir(root: Path) -> Path | None:
    """Thư mục dự án CapCut bên trong root (nông nhất): có draft_content.json hoặc Timelines/project.json."""
    root = Path(root)
    cands = [p.parent for p in root.rglob("draft_content.json")] + \
        [p.parent.parent for p in root.rglob("project.json") if p.parent.name == "Timelines"]
    cands = [c for c in cands if (c / "draft_meta_info.json").is_file() or (c / "draft_content.json").is_file()]
    return min(cands, key=lambda c: len(c.parts)) if cands else None


def safe_extract(zip_path: Path, dest: Path) -> Path:
    """Giải nén .zip, chặn đường dẫn thoát ra ngoài thư mục đích (zip slip)."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            target = (dest / info.filename).resolve()
            if dest.resolve() not in target.parents and target != dest.resolve():
                raise ValueError(f"File zip có đường dẫn không an toàn: {info.filename}")
        z.extractall(dest)
    return dest


def project_name(draft_dir: Path) -> str:
    meta = Path(draft_dir) / "draft_meta_info.json"
    if meta.is_file():
        try:
            return read_json(meta).get("draft_name") or Path(draft_dir).name
        except (OSError, ValueError):
            pass
    return Path(draft_dir).name


def _is_capcut_cache(path: str) -> bool:
    p = path.replace("\\", "/").lower()
    return "/capcut/" in p and ("/cache/" in p or ("/user data/" in p and "/projects/" not in p))


def import_project(draft_dir: Path, assets_root: Path = ledger.ASSETS_ROOT, *, mood: str = "",
                   copy_to: Path | None = None) -> dict:
    """Đọc dự án → thêm tài nguyên vào danh mục + chép file âm thanh riêng của người dùng vào kho.
    copy_to: thư mục draft của CapCut — chép cả dự án vào đó (để mở 1 lần cho CapCut tải tài nguyên)."""
    draft_dir, assets_root = Path(draft_dir), Path(assets_root)
    name = project_name(draft_dir)
    timeline = read_json(main_timeline_path(draft_dir))
    items = extract_library(timeline, key_values(draft_dir))

    store = load_store(assets_root)
    index = {(d["kind"], d["resource_id"]): d for d in store}
    had = set(index)
    rows, added = [], 0
    for it in items:
        if mood and it.kind == "music":
            it.mood = mood
        d = {**it.to_json(), "from_project": name, "imported": date.today().isoformat()}
        key = (it.kind, it.resource_id)
        if key not in had:
            added += 1
        else:  # giữ nhãn cũ nếu lần này không ghi nhãn
            d["mood"] = it.mood or index[key].get("mood", "")
        index[key] = d
        rows.append({"kind": it.kind, "kind_vi": KIND_VI.get(it.kind, it.kind), "name": it.name,
                     "cached": cached_on_disk(it), "new": key not in had})
    p = store_path(assets_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"items": list(index.values())}, ensure_ascii=False, indent=2), encoding="utf-8")

    local_audio = []
    for mat in timeline.get("materials", {}).get("audios", []):
        path = mat.get("path") or ""
        if mat.get("music_id") or not path or _is_capcut_cache(path):
            continue  # nhạc thư viện CapCut / file cache: không chép ra ngoài
        src = Path(path)
        if not src.is_file() or src.suffix.lower() not in AUDIO_EXTS:
            continue
        kind = "sfx" if 0 < mat.get("duration", 0) <= SFX_MAX_US else "music"
        tag = slug(mood) if (mood and kind == "music") else "tu_du_an"
        dest = assets_root / kind / tag / f"{slug(src.stem)}_cc{src.suffix.lower()}"
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            ledger.add(assets_root, dest, source=f"Dự án CapCut: {name}", license="file người dùng tự thêm vào dự án",
                       duration_us=int(mat.get("duration", 0)), extra={"name": src.stem, "kind": kind, "tag": tag})
            local_audio.append(dest.name)

    copied_to = None
    if copy_to is not None:
        copy_to = Path(copy_to)
        if copy_to.resolve() not in draft_dir.resolve().parents:  # chưa nằm trong thư mục CapCut
            target = copy_to / slug(name)
            n = 2
            while target.exists():
                target = copy_to / f"{slug(name)}_{n}"
                n += 1
            shutil.copytree(draft_dir, target)
            copied_to = str(target)

    return {"project": name, "items": rows, "added": added, "local_audio": local_audio, "copied_to": copied_to,
            "ready": sum(1 for r in rows if r["cached"]), "need_download": sum(1 for r in rows if not r["cached"])}
