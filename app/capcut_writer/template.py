"""Đọc dự án mẫu do CapCut 9.5.0 tạo và rút ra các "khuôn" (prototype) để nhân bản.

Xem docs/CAPCUT_COMPAT.md. Điểm then chốt:
- CapCut 9.5.0 đọc `Timelines/<main_timeline_id>/draft_content.json`.
- Mỗi segment tham chiếu một vật liệu chính (`material_id`) và nhiều vật liệu phụ
  (`extra_material_refs`: speeds, canvases, placeholder_infos, ...). Khuôn giữ nguyên cả bộ đó,
  nên draft sinh ra có đúng đủ trường như CapCut tự ghi.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main_timeline_path(draft_dir: Path) -> Path:
    project = draft_dir / "Timelines" / "project.json"
    if project.is_file():
        main_id = read_json(project)["main_timeline_id"]
        path = draft_dir / "Timelines" / main_id / "draft_content.json"
        if path.is_file():
            return path
    return draft_dir / "draft_content.json"


def timeline_copies(draft_dir: Path) -> list[Path]:
    """Các file chứa bản sao timeline (cần giữ giống file chính)."""
    main = main_timeline_path(draft_dir)
    candidates = [
        main,
        main.with_name("template-2.tmp"),
        draft_dir / "draft_content.json",
        draft_dir / "template-2.tmp",
    ]
    seen, result = set(), []
    for path in candidates:
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


@dataclass
class Prototype:
    """Một segment mẫu cùng vật liệu chính và các vật liệu phụ của nó."""

    segment: dict
    material_kind: str
    material: dict
    extras: list[tuple[str, dict]] = field(default_factory=list)

    def clone(self) -> "Prototype":
        return copy.deepcopy(self)


@dataclass
class LibraryItem:
    """Một tài nguyên thư viện CapCut (hiệu ứng, filter, chuyển cảnh, sticker, nhạc, animation chữ)."""

    kind: str  # video_effect | filter | transition | sticker | music | text_animation
    name: str
    resource_id: str
    material: dict
    is_vip: bool = False
    category: str = ""

    def to_json(self) -> dict:
        return {
            "kind": self.kind,
            "name": self.name,
            "resource_id": self.resource_id,
            "is_vip": self.is_vip,
            "category": self.category,
            "material": self.material,
        }

    @classmethod
    def from_json(cls, data: dict) -> "LibraryItem":
        return cls(
            kind=data["kind"],
            name=data["name"],
            resource_id=data["resource_id"],
            material=data["material"],
            is_vip=data.get("is_vip", False),
            category=data.get("category", ""),
        )


class DraftTemplate:
    """Dự án mẫu đã nạp: timeline, khuôn segment, và các tài nguyên thư viện có trong đó."""

    PROTOTYPE_KINDS = ("video", "audio", "text", "sticker", "effect", "filter")

    def __init__(self, draft_dir: Path):
        self.draft_dir = Path(draft_dir)
        self.timeline_path = main_timeline_path(self.draft_dir)
        self.timeline = read_json(self.timeline_path)
        self._index = self._index_materials(self.timeline)
        self.prototypes: dict[str, Prototype] = {}
        self.track_prototypes: dict[str, dict] = {}
        self._extract_prototypes()
        self.library = self._extract_library()

    # ---------- đọc ----------

    @staticmethod
    def _index_materials(timeline: dict) -> dict[str, tuple[str, dict]]:
        index = {}
        for kind, items in timeline["materials"].items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and "id" in item:
                        index[item["id"]] = (kind, item)
        return index

    def _prototype_from_segment(self, segment: dict, skip_extra: tuple[str, ...] = ()) -> Prototype:
        kind, material = self._index[segment["material_id"]]
        extras = []
        for ref in segment.get("extra_material_refs", []):
            if ref in self._index:
                extra_kind, extra = self._index[ref]
                if extra_kind not in skip_extra:
                    extras.append((extra_kind, extra))
        return Prototype(copy.deepcopy(segment), kind, copy.deepcopy(material), copy.deepcopy(extras))

    def _extract_prototypes(self) -> None:
        for track in self.timeline["tracks"]:
            ttype = track["type"]
            if ttype not in self.PROTOTYPE_KINDS or not track["segments"]:
                continue
            self.track_prototypes.setdefault(ttype, {**copy.deepcopy(track), "segments": []})
            if ttype in self.prototypes:
                continue
            segments = track["segments"]
            if ttype == "text":
                # ưu tiên lớp chữ không có animation làm khuôn sạch
                segments = sorted(segments, key=lambda s: self._animation_count(s))
            proto = self._prototype_from_segment(segments[0], skip_extra=("transitions",))
            proto.segment["common_keyframes"] = []
            for extra_kind, extra in proto.extras:
                if extra_kind == "material_animations":
                    extra["animations"] = []
                if extra_kind == "beats":
                    _blank_beats(extra)
            self.prototypes[ttype] = proto

    def _animation_count(self, segment: dict) -> int:
        count = 0
        for ref in segment.get("extra_material_refs", []):
            kind, material = self._index.get(ref, ("", {}))
            if kind == "material_animations":
                count += len(material.get("animations", []))
        return count

    def _key_values(self) -> dict:
        path = self.draft_dir / "key_value.json"
        if not path.is_file():
            return {}
        by_material = {}
        for entry in read_json(path).values():
            if isinstance(entry, dict) and entry.get("materialId"):
                by_material.setdefault(entry["materialId"], entry)
        return by_material

    def _extract_library(self) -> list[LibraryItem]:
        kv = self._key_values()
        m = self.timeline["materials"]
        items: list[LibraryItem] = []

        def add(kind: str, material: dict, resource_id: str, name: str, category: str = "") -> None:
            meta = kv.get(resource_id, {})
            items.append(
                LibraryItem(
                    kind=kind,
                    name=name,
                    resource_id=resource_id,
                    material=copy.deepcopy(material),
                    is_vip=str(meta.get("is_vip", "0")) == "1",
                    category=category or meta.get("materialThirdcategory", ""),
                )
            )

        for mat in m.get("video_effects", []):
            add("video_effect", mat, mat["resource_id"], mat.get("name", ""), mat.get("category_name", ""))
        for mat in m.get("effects", []):
            if mat.get("type") == "filter":
                add("filter", mat, mat["resource_id"], mat.get("name", ""), mat.get("category_name", ""))
        for mat in m.get("transitions", []):
            add("transition", mat, mat["resource_id"], mat.get("name", ""), mat.get("category_name", ""))
        for mat in m.get("stickers", []):
            add("sticker", mat, mat["resource_id"], mat.get("name", ""), mat.get("category_name", ""))
        for mat in m.get("audios", []):
            if mat.get("music_id"):
                add("music", mat, mat["music_id"], mat.get("name", ""), mat.get("category_name", ""))
        seen = set()
        for mat in m.get("material_animations", []):
            for anim in mat.get("animations", []):
                if anim.get("resource_id") in seen:
                    continue
                seen.add(anim.get("resource_id"))
                add("text_animation", anim, anim["resource_id"], anim.get("name", ""), anim.get("type", ""))
        return items

    # ---------- tra cứu ----------

    def find(self, kind: str, name: str | None = None) -> LibraryItem:
        for item in self.library:
            if item.kind == kind and (name is None or item.name == name):
                return item
        raise KeyError(f"Không có tài nguyên {kind!r} tên {name!r} trong dự án mẫu")

    def prototype(self, kind: str) -> Prototype:
        if kind not in self.prototypes:
            raise KeyError(f"Dự án mẫu thiếu khuôn cho loại {kind!r}")
        return self.prototypes[kind].clone()


def _blank_beats(beats: dict) -> None:
    ai = beats.get("ai_beats")
    if isinstance(ai, dict):
        for key, value in ai.items():
            if isinstance(value, str):
                ai[key] = ""
    beats["user_beats"] = []
