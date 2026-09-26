"""Nhập cả thư mục âm thanh tải tay (Pixabay, Mixkit, YouTube Audio Library, Incompetech...) vào kho assets/.

Tự xếp loại theo tên thư mục — khớp cả tên kiểu README của chủ dự án (SFX/ChuyenCanh, Nhac/TaiLieu_BiAn...),
tên nhóm tiếng Việt có dấu, lẫn từ khóa tiếng Anh (whoosh, epic...). Mỗi file được ghi sổ nguồn + CREDITS.csv.
"""

from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path

from app import config

from . import ledger
from .freesound import slug
from .local import AUDIO_EXTS

SOURCE_PREFIX = {"pixabay": "pb", "mixkit": "mk", "youtube_audio": "yt", "incompetech": "ic", "own": "own",
                 "other": "x"}


def norm(text: str) -> str:
    """Bỏ dấu, chữ thường, bỏ khoảng trắng/gạch: 'Chuyển cảnh' / 'ChuyenCanh' / 'chuyen_canh' → 'chuyencanh'."""
    t = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", t.lower())


def infer_kind(parts: list[str], default: str) -> str:
    joined = " ".join(norm(p) for p in parts)
    if any(k in joined for k in ("sfx", "soundeffect", "hieuung", "amthanh")):
        return "sfx"
    if any(k in joined for k in ("nhac", "music", "bgm")):
        return "music"
    return default


def infer_tag(parts: list[str], kind: str, cfg: dict | None = None) -> str:
    """Nhóm (tag) từ tên các thư mục cha, thư mục gần file nhất được ưu tiên. Không khớp → 'khac'."""
    cfg = cfg or config.load("assets")
    groups = cfg.get("sfx_groups" if kind == "sfx" else "music_groups") or {}
    names = {tag: [norm(tag), norm(g.get("vi", ""))] + [norm(k) for k in g.get("keywords", [])]
             for tag, g in groups.items()}
    for part in reversed(parts):
        p = norm(part)
        if not p:
            continue
        for tag, keys in names.items():  # khớp đúng tên
            if p in keys[:2]:
                return tag
        for tag, keys in names.items():  # tên thư mục bắt đầu / chứa tên nhóm (ThoiGian_Tua, TruyenCamHung)
            if any(k and (p.startswith(k) or (len(k) >= 5 and k in p)) for k in keys[:2]):
                return tag
        for tag, keys in names.items():  # từ khóa tiếng Anh (whoosh, epic...)
            if any(k and len(k) >= 3 and k in p for k in keys[2:]):
                return tag
    return "khac"


def import_folder(src_dir: Path, assets_root: Path = ledger.ASSETS_ROOT, *, kind: str = "auto",
                  source: str = "other", license: str = "", author: str = "", cfg: dict | None = None) -> dict:
    """Chép mọi file âm thanh trong src_dir (kể cả thư mục con) vào assets/<sfx|music>/<nhóm>/ và ghi sổ nguồn."""
    cfg = cfg or config.load("assets")
    src_dir, assets_root = Path(src_dir), Path(assets_root)
    if not src_dir.is_dir():
        raise ValueError(f"Không thấy thư mục {src_dir}")
    info = (cfg.get("manual_sources") or {}).get(source, {})
    lic = license.strip() or info.get("license", "")
    credit = bool(info.get("credit", False))
    prefix = SOURCE_PREFIX.get(source, "x")
    imported, skipped = [], []
    root_abs = assets_root.resolve()
    for f in sorted(src_dir.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in AUDIO_EXTS:
            continue
        if root_abs in f.resolve().parents:
            skipped.append({"file": str(f), "why": "đã nằm trong kho"})
            continue
        parts = list(f.relative_to(src_dir).parent.parts) or [src_dir.name]
        if kind == "auto":  # theo tên thư mục; không có gợi ý thì theo dung lượng (SFX nhỏ, bài nhạc lớn)
            k = infer_kind([src_dir.name, *parts], "music" if f.stat().st_size > 1_200_000 else "sfx")
        else:
            k = kind
        tag = infer_tag([src_dir.name, *parts], k, cfg)
        dest = assets_root / k / tag / f"{slug(f.stem)}_{prefix}{f.suffix.lower()}"
        if dest.exists():
            skipped.append({"file": str(f), "why": "đã có trong kho"})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        entry = ledger.add(assets_root, dest, source=info.get("vi", source), license=lic, author=author,
                           credit_required=credit, extra={"original_name": f.name, "kind": k, "tag": tag,
                                                          "name": f.stem})
        imported.append(entry)
    return {"imported": imported, "skipped": skipped, "credit_required": credit}
