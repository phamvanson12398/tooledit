"""Ghi dự án CapCut 9.5.0 bằng cách nhân bản dự án mẫu và thay nội dung timeline.

Cách dùng (tóm tắt):

    tpl = DraftTemplate(Path(".../com.lveditor.draft/capcut_template"))
    w = DraftWriter(tpl, drafts_root, "khach_job01_video01")
    w.add_video(VideoSource(path, 1080, 1920, 60_000_000), target_start=0, duration=3_000_000)
    w.add_text("안녕하세요", start=0, duration=2_000_000, y=-0.6)
    w.save()

Thời gian luôn tính bằng micro giây. Vị trí x/y tính theo nửa khung hình (1.0 = mép phải/trên),
trục y hướng lên. Scale 1.0 = vừa khung (CapCut tự fit).
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .template import DraftTemplate, LibraryItem, Prototype, read_json, timeline_copies

SEC = 1_000_000

# Các danh sách vật liệu do writer quản lý: xóa sạch rồi điền lại từ khuôn.
MANAGED_MATERIALS = (
    "videos", "audios", "texts", "stickers", "video_effects", "effects", "transitions",
    "material_animations", "speeds", "canvases", "placeholder_infos", "sound_channel_mappings",
    "material_colors", "vocal_separations", "beats", "audio_fades",
)

TRACK_ORDER = ("video", "effect", "filter", "text", "sticker", "audio")
BASE_RENDER_INDEX = {"video": 0, "audio": 0, "effect": 11000, "filter": 10000, "text": 14000, "sticker": 14000}


def new_id() -> str:
    return str(uuid.uuid4()).upper()


def utf16_len(text: str) -> int:
    """CapCut đo range của style chữ bằng đơn vị UTF-16 (xem capcut-cli #85)."""
    return len(text.encode("utf-16-le")) // 2


def hex_color(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


@dataclass
class VideoSource:
    """Thông tin một file video trên máy (lấy bằng app.capcut_writer.media.probe)."""

    path: Path
    width: int
    height: int
    duration: int  # micro giây
    has_audio: bool = True


@dataclass
class Keyframe:
    """Keyframe cho segment. time: micro giây tính từ đầu segment.

    prop: "scale" (đều hai trục), "x", "y", "rotation", "alpha", "volume".
    """

    prop: str
    time: int
    value: float


KEYFRAME_TYPES = {
    "scale": "KFTypeScaleX",  # CapCut 9.5.0 dùng KFTypeScaleX khi bật uniform_scale
    "x": "KFTypePositionX",
    "y": "KFTypePositionY",
    "rotation": "KFTypeRotation",
    "alpha": "KFTypeAlpha",
    "volume": "KFTypeVolume",
}


@dataclass
class Crop:
    """Vùng cắt trên khung hình gốc, tọa độ 0..1 (trái, trên, phải, dưới)."""

    left: float = 0.0
    top: float = 0.0
    right: float = 1.0
    bottom: float = 1.0

    def to_json(self) -> dict:
        return {
            "upper_left_x": self.left, "upper_left_y": self.top,
            "upper_right_x": self.right, "upper_right_y": self.top,
            "lower_left_x": self.left, "lower_left_y": self.bottom,
            "lower_right_x": self.right, "lower_right_y": self.bottom,
        }


@dataclass
class TextBackground:
    """Khung nền sau chữ (định dạng theo pyCapCut TextBackground; CapCut: Văn bản → Nền)."""

    color: str = "#E53935"        # '#RRGGBB'
    alpha: float = 1.0
    round_radius: float = 0.2     # 0..1
    style: int = 1                # 1 hoặc 2 (hai kiểu nền của CapCut)
    width: float = 0.14           # độ rộng đệm, 0..1
    height: float = 0.14


@dataclass
class TextStyle:
    size: float = 15.0            # 15 = cỡ mặc định của CapCut
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    bold: bool = False
    stroke_color: tuple[float, float, float] | None = None
    stroke_width: float = 0.08  # đơn vị nội bộ CapCut (pyCapCut: thang 0–100 của CapCut /100*0.2; 40 → 0.08)
    background: TextBackground | None = None


@dataclass
class _Placed:
    track_type: str
    start: int
    end: int
    segment: dict


@dataclass
class DraftWriter:
    template: DraftTemplate
    drafts_root: Path
    name: str
    _placed: list[_Placed] = field(default_factory=list)
    _materials: dict[str, list] = field(default_factory=dict)
    _videos: list[VideoSource] = field(default_factory=list)

    # ---------- phần chung ----------

    def _add_material(self, kind: str, material: dict) -> None:
        self._materials.setdefault(kind, []).append(material)

    def _instantiate(self, proto: Prototype) -> tuple[dict, dict]:
        """Gán id mới cho segment, vật liệu chính và vật liệu phụ; đăng ký các vật liệu."""
        seg, mat = proto.segment, proto.material
        mat["id"] = new_id()
        seg["id"] = new_id()
        seg["material_id"] = mat["id"]
        refs = []
        for kind, extra in proto.extras:
            extra["id"] = new_id()
            self._add_material(kind, extra)
            refs.append(extra["id"])
        seg["extra_material_refs"] = refs
        seg["common_keyframes"] = []
        self._add_material(proto.material_kind, mat)
        return seg, mat

    def _extra(self, seg: dict, kind: str) -> dict | None:
        for ref in seg["extra_material_refs"]:
            for mat in self._materials.get(kind, []):
                if mat["id"] == ref:
                    return mat
        return None

    def _place(self, track_type: str, seg: dict, start: int, duration: int) -> dict:
        seg["target_timerange"] = {"start": int(start), "duration": int(duration)}
        self._placed.append(_Placed(track_type, int(start), int(start + duration), seg))
        return seg

    @staticmethod
    def _set_clip(seg: dict, *, x: float = 0.0, y: float = 0.0, scale: float = 1.0, rotation: float = 0.0) -> None:
        clip = seg.get("clip") or {}
        clip.update({
            "scale": {"x": scale, "y": scale},
            "rotation": rotation,
            "transform": {"x": x, "y": y},
            "flip": clip.get("flip", {"vertical": False, "horizontal": False}),
            "alpha": clip.get("alpha", 1.0),
        })
        seg["clip"] = clip
        if isinstance(seg.get("uniform_scale"), dict):
            seg["uniform_scale"] = {"on": True, "value": 1.0}

    @staticmethod
    def _set_keyframes(seg: dict, keyframes: list[Keyframe]) -> None:
        by_prop: dict[str, list[Keyframe]] = {}
        for kf in keyframes:
            if kf.prop not in KEYFRAME_TYPES:
                raise ValueError(f"Không hỗ trợ keyframe {kf.prop!r}")
            by_prop.setdefault(kf.prop, []).append(kf)
        seg["common_keyframes"] = [
            {
                "id": new_id(),
                "material_id": "",
                "property_type": KEYFRAME_TYPES[prop],
                "keyframe_list": [
                    {
                        "id": new_id(),
                        "curveType": "Line",
                        "time_offset": int(kf.time),
                        "left_control": {"x": 0.0, "y": 0.0},
                        "right_control": {"x": 0.0, "y": 0.0},
                        "values": [float(kf.value)],
                        "string_value": "",
                        "graphID": "",
                    }
                    for kf in sorted(items, key=lambda k: k.time)
                ],
            }
            for prop, items in by_prop.items()
        ]

    # ---------- video ----------

    def add_video(
        self,
        source: VideoSource,
        *,
        target_start: int,
        duration: int,
        source_start: int = 0,
        speed: float = 1.0,
        x: float = 0.0,
        y: float = 0.0,
        scale: float = 1.0,
        crop: Crop | None = None,
        volume: float = 1.0,
        keyframes: list[Keyframe] | None = None,
        transition: LibraryItem | None = None,
        transition_duration: int | None = None,
        background_blur: float | None = None,
        background_color: str | None = None,
    ) -> dict:
        """Thêm một clip. background_blur (0–1): lấp phần trống bằng bản mờ của chính video;
        background_color ('#RRGGBBAA'): lấp bằng màu trơn (theo định dạng BackgroundFilling của pyCapCut). duration là thời lượng trên timeline; nguồn dùng duration*speed."""
        source_duration = round(duration * speed)
        if source_start < 0 or source_start + source_duration > source.duration:
            raise ValueError(
                f"Đoạn {source_start}-{source_start + source_duration}µs vượt quá độ dài file "
                f"{source.path} ({source.duration}µs)"
            )
        seg, mat = self._instantiate(self.template.prototype("video"))
        mat.update({
            "path": Path(source.path).as_posix(),
            "material_name": Path(source.path).name,
            "width": source.width,
            "height": source.height,
            "duration": source.duration,
            "has_audio": source.has_audio,
            "crop": (crop or Crop()).to_json(),
            "local_material_id": "",
        })
        seg["source_timerange"] = {"start": int(source_start), "duration": int(source_duration)}
        seg["speed"] = speed
        seg["volume"] = volume
        speed_mat = self._extra(seg, "speeds")
        if speed_mat is not None:
            speed_mat["speed"] = speed
        self._set_clip(seg, x=x, y=y, scale=scale)
        canvas = self._extra(seg, "canvases")
        if canvas is not None and (background_blur is not None or background_color is not None):
            if background_blur is not None:
                canvas.update({"type": "canvas_blur", "blur": float(background_blur)})
            else:
                canvas.update({"type": "canvas_color", "color": background_color, "blur": 0.0})
        if keyframes:
            self._set_keyframes(seg, keyframes)
        if transition is not None:
            trans = copy.deepcopy(transition.material)
            trans["id"] = new_id()
            if transition_duration is not None:
                trans["duration"] = int(transition_duration)
            self._add_material("transitions", trans)
            seg["extra_material_refs"].append(trans["id"])
        if source not in self._videos:
            self._videos.append(source)
        return self._place("video", seg, target_start, duration)

    # ---------- âm thanh ----------

    def add_music(
        self, music: LibraryItem, *, target_start: int, duration: int, source_start: int = 0, volume: float = 1.0,
        keyframes: list[Keyframe] | None = None,
    ) -> dict:
        """Nhạc/âm thanh từ thư viện CapCut (đã có trong cache máy)."""
        seg, mat = self._instantiate(self.template.prototype("audio"))
        keep_id = mat["id"]
        mat.clear()
        mat.update(copy.deepcopy(music.material))
        mat["id"] = keep_id
        return self._finish_audio(seg, mat, target_start, duration, source_start, volume, keyframes)

    def add_local_audio(
        self, path: Path, file_duration: int, *, target_start: int, duration: int, source_start: int = 0,
        volume: float = 1.0, keyframes: list[Keyframe] | None = None, speed: float = 1.0,
    ) -> dict:
        """File âm thanh trên máy (ví dụ voice hook). Các trường khớp đúng với vật liệu âm thanh local mà
        CapCut 9.5.0 tự ghi (mẫu lần 3, file kkk2.wav): type extract_music, category_name local, app_id 0,
        check_flag 1, music_id / local_material_id / category_id rỗng."""
        seg, mat = self._instantiate(self.template.prototype("audio"))
        keep_id = mat["id"]
        for key, value in list(mat.items()):  # bỏ dấu vết của bài nhạc thư viện trong khuôn
            if isinstance(value, str):
                mat[key] = ""
        mat.update({
            "id": keep_id,
            "type": "extract_music",
            "name": Path(path).name,
            "path": Path(path).as_posix(),
            "duration": int(file_duration),
            "category_name": "local",
            "app_id": 0,
            "check_flag": 1,
            "copyright_limit_type": "none",
        })
        return self._finish_audio(seg, mat, target_start, duration, source_start, volume, keyframes, speed)

    def _finish_audio(self, seg, mat, target_start, duration, source_start, volume, keyframes,
                      speed: float = 1.0) -> dict:
        source_duration = round(duration * speed)
        if source_start + source_duration > mat.get("duration", 0) + 1000:
            raise ValueError(f"Đoạn âm thanh vượt quá độ dài file {mat.get('name')}")
        seg["source_timerange"] = {"start": int(source_start), "duration": int(source_duration)}
        seg["speed"] = speed
        speed_mat = self._extra(seg, "speeds")
        if speed_mat is not None:
            speed_mat["speed"] = speed
        seg["volume"] = volume
        if keyframes:
            self._set_keyframes(seg, keyframes)
        return self._place("audio", seg, target_start, duration)

    # ---------- chữ ----------

    def add_text(
        self,
        text: str,
        *,
        start: int,
        duration: int,
        x: float = 0.0,
        y: float = 0.0,
        scale: float = 1.0,
        style: TextStyle | None = None,
        animations: list[LibraryItem] | None = None,
        keyframes: list[Keyframe] | None = None,
    ) -> dict:
        style = style or TextStyle()
        seg, mat = self._instantiate(self.template.prototype("text"))
        content = json.loads(mat["content"])
        base_style = copy.deepcopy(content["styles"][0]) if content.get("styles") else {}
        base_style["range"] = [0, utf16_len(text)]
        base_style["size"] = style.size
        base_style["bold"] = style.bold
        base_style["fill"] = {
            "alpha": 1.0,
            "content": {"render_type": "solid", "solid": {"alpha": 1.0, "color": list(style.color)}},
        }
        check_flag = 7
        if style.stroke_color is not None:
            base_style["strokes"] = [
                {"content": {"solid": {"alpha": 1.0, "color": list(style.stroke_color)}}, "width": style.stroke_width}
            ]
            check_flag |= 8
            mat["border_color"] = hex_color(style.stroke_color)
            mat["border_width"] = style.stroke_width
        else:
            base_style.pop("strokes", None)
        if style.background is not None:
            bg = style.background
            check_flag |= 16
            mat.update({
                "background_style": bg.style, "background_color": bg.color, "background_alpha": bg.alpha,
                "background_round_radius": bg.round_radius, "background_height": bg.height,
                "background_width": bg.width, "background_horizontal_offset": 0.0,
                "background_vertical_offset": 0.0,
            })
        mat["content"] = json.dumps({"text": text, "styles": [base_style]}, ensure_ascii=False, separators=(",", ":"))
        mat["base_content"] = ""
        mat["check_flag"] = check_flag
        mat["font_size"] = style.size
        mat["text_size"] = round(style.size * 2)
        mat["text_color"] = hex_color(style.color)
        self._set_clip(seg, x=x, y=y, scale=scale)
        if animations:
            anim_mat = self._extra(seg, "material_animations")
            if anim_mat is None:
                raise ValueError("Khuôn chữ không có vật liệu animation")
            anim_mat["animations"] = []
            for item in animations:
                anim = copy.deepcopy(item.material)
                anim["start"] = 0 if anim.get("type") != "out" else max(0, duration - anim.get("duration", 0))
                anim_mat["animations"].append(anim)
        if keyframes:
            self._set_keyframes(seg, keyframes)
        return self._place("text", seg, start, duration)

    # ---------- sticker, hiệu ứng, filter ----------

    def add_sticker(self, sticker: LibraryItem, *, start: int, duration: int, x=0.0, y=0.0, scale=1.0) -> dict:
        seg, mat = self._instantiate(self.template.prototype("sticker"))
        keep_id = mat["id"]
        mat.clear()
        mat.update(copy.deepcopy(sticker.material))
        mat["id"] = keep_id
        self._set_clip(seg, x=x, y=y, scale=scale)
        return self._place("sticker", seg, start, duration)

    def add_effect(self, effect: LibraryItem, *, start: int, duration: int) -> dict:
        return self._add_library_segment("effect", effect, start, duration)

    def add_filter(self, flt: LibraryItem, *, start: int, duration: int) -> dict:
        return self._add_library_segment("filter", flt, start, duration)

    def _add_library_segment(self, track_type: str, item: LibraryItem, start: int, duration: int) -> dict:
        seg, mat = self._instantiate(self.template.prototype(track_type))
        keep_id = mat["id"]
        mat.clear()
        mat.update(copy.deepcopy(item.material))
        mat["id"] = keep_id
        return self._place(track_type, seg, start, duration)

    # ---------- ghi ra đĩa ----------

    @property
    def draft_dir(self) -> Path:
        return Path(self.drafts_root) / self.name

    def duration(self) -> int:
        return max((p.end for p in self._placed), default=0)

    def build_timeline(self) -> dict:
        timeline = copy.deepcopy(self.template.timeline)
        for kind in MANAGED_MATERIALS:
            if kind in timeline["materials"]:
                timeline["materials"][kind] = []
        for kind, items in self._materials.items():
            timeline["materials"].setdefault(kind, []).extend(items)

        tracks: list[dict] = []
        for ttype in TRACK_ORDER:
            placed = sorted((p for p in self._placed if p.track_type == ttype), key=lambda p: p.start)
            lanes: list[list[_Placed]] = []
            for item in placed:  # xếp vào làn đầu tiên không chồng thời gian
                for lane in lanes:
                    if lane[-1].end <= item.start:
                        lane.append(item)
                        break
                else:
                    lanes.append([item])
            for lane in lanes:
                track = copy.deepcopy(self.template.track_prototypes.get(ttype, {"type": ttype, "flag": 0,
                                                                                   "attribute": 0, "is_default_name": True, "name": ""}))
                track["id"] = new_id()
                track["segments"] = [p.segment for p in lane]
                tracks.append(track)

        render = dict(BASE_RENDER_INDEX)
        for index, track in enumerate(tracks):
            for seg in track["segments"]:
                seg["track_render_index"] = index
                base = BASE_RENDER_INDEX.get(track["type"], 0)
                if base:
                    seg["render_index"] = render[track["type"]]
                    render[track["type"]] += 1
        # chữ và sticker dùng chung dải render 14000+
        timeline["tracks"] = tracks
        timeline["duration"] = self.duration()
        return timeline

    def save(self, *, overwrite: bool = False, check_capcut: bool = True) -> Path:
        if check_capcut and capcut_is_running():
            raise RuntimeError("CapCut đang mở. Hãy đóng CapCut rồi chạy lại để tránh CapCut ghi đè.")
        dst = self.draft_dir
        if dst.exists():
            if not overwrite:
                raise FileExistsError(f"Đã có draft {dst}")
            shutil.rmtree(dst)
        shutil.copytree(self.template.draft_dir, dst, ignore=shutil.ignore_patterns("*.bak", "draft_cover.jpg"))

        timeline = self.build_timeline()
        data = json.dumps(timeline, ensure_ascii=False, separators=(",", ":"))
        for path in timeline_copies(dst):
            if path.exists() or path.parent.exists():
                atomic_write(path, data)
        # mini_draft.json là bản cache; xóa để CapCut không dùng bản cũ (đã thử: vẫn mở được).
        for patch_dir in (dst / "Timelines").glob("*/attachment/patch"):
            shutil.rmtree(patch_dir)
        self._update_meta(dst, timeline)
        return dst

    def _update_meta(self, dst: Path, timeline: dict) -> None:
        meta_path = dst / "draft_meta_info.json"
        if not meta_path.is_file():
            return
        meta = read_json(meta_path)
        meta["draft_name"] = self.name
        meta["draft_fold_path"] = dst.as_posix()
        meta["draft_id"] = new_id()
        meta["draft_cover"] = ""
        if "tm_duration" in meta:
            meta["tm_duration"] = timeline["duration"]
        # danh sách media trong bảng "Nhập" của CapCut
        for group in meta.get("draft_materials", []):
            if group.get("type") == 0:
                proto = next((v for v in group.get("value", []) if v.get("metetype") == "video"), None)
                if proto is None:
                    continue
                entries = []
                for src in self._videos:
                    entry = copy.deepcopy(proto)
                    entry.update({
                        "id": str(uuid.uuid4()),
                        "file_Path": Path(src.path).as_posix(),
                        "extra_info": Path(src.path).name,
                        "width": src.width,
                        "height": src.height,
                        "duration": src.duration,
                        "roughcut_time_range": {"duration": src.duration, "start": 0},
                    })
                    entries.append(entry)
                group["value"] = entries
        atomic_write(meta_path, json.dumps(meta, ensure_ascii=False, separators=(",", ":")))


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".writing")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def capcut_is_running() -> bool:
    """Chỉ kiểm tra được trên Windows; nơi khác luôn trả False."""
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/NH"], capture_output=True, text=True, timeout=10
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return "capcut.exe" in out.lower()
