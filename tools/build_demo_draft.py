"""Tạo một draft demo từ dự án mẫu để thử bộ ghi draft trên CapCut thật.

Dùng lại chính các clip có trong dự án mẫu (khỏi cần ffprobe). Demo gồm:
zoom chậm bằng keyframe, khối 4:3 và 1:1 cho clip ngang, lia khung bằng keyframe vị trí,
phụ đề có viền, chữ có animation, sticker, hiệu ứng, filter, chuyển cảnh, nhạc thư viện
với keyframe âm lượng (ducking), và âm thanh local 0–4s (giả làm voice hook) nếu mẫu có.

Chạy trên Windows (đóng CapCut trước):
    python tools\\build_demo_draft.py "%LOCALAPPDATA%\\CapCut\\User Data\\Projects\\com.lveditor.draft\\capcut_template"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.capcut_writer import (  # noqa: E402
    SEC, DraftTemplate, DraftWriter, Keyframe, TextStyle, VideoSource, block_crop,
)
from app.capcut_writer.layout import band_centers  # noqa: E402
from app.capcut_writer.template import read_json  # noqa: E402

YELLOW, WHITE, BLACK = (1.0, 0.85, 0.0), (1.0, 1.0, 1.0), (0.0, 0.0, 0.0)


def template_videos(tpl: DraftTemplate) -> tuple[VideoSource, VideoSource]:
    vids = [
        VideoSource(Path(v["path"]), v["width"], v["height"], v["duration"], v.get("has_audio", True))
        for v in tpl.timeline["materials"]["videos"]
    ]
    vertical = next(v for v in vids if v.height > v.width)
    wide = next((v for v in vids if v.width > v.height), None)
    if wide is None:
        raise SystemExit("Dự án mẫu cần có ít nhất một clip ngang (16:9).")
    return vertical, wide


def build(template_dir: Path, drafts_root: Path, name: str) -> DraftWriter:
    tpl = DraftTemplate(template_dir)
    vert, wide = template_videos(tpl)
    w = DraftWriter(tpl, drafts_root, name)
    trans = tpl.find("transition")
    top43, bottom43 = band_centers("4:3")
    top11, bottom11 = band_centers("1:1")
    sub = TextStyle(size=11, color=WHITE, stroke_color=BLACK)

    # 0–4s: clip dọc, zoom chậm 1.0 → 1.25
    w.add_video(vert, target_start=0, duration=4 * SEC, source_start=min(10 * SEC, vert.duration - 4 * SEC),
                keyframes=[Keyframe("scale", 0, 1.0), Keyframe("scale", 4 * SEC, 1.25)], transition=trans)
    # 4–8s: clip ngang → khối 4:3 giữa màn
    w.add_video(wide, target_start=4 * SEC, duration=4 * SEC, crop=block_crop(wide.width, wide.height, "4:3"))
    # 8–11s: clip ngang → khối 1:1, bám bên trái khung
    w.add_video(wide, target_start=8 * SEC, duration=3 * SEC, source_start=min(4 * SEC, wide.duration - 3 * SEC),
                crop=block_crop(wide.width, wide.height, "1:1", center_x=0.3))
    # 11–15s: clip dọc phóng 1.3, lia khung từ trái sang phải
    w.add_video(vert, target_start=11 * SEC, duration=4 * SEC, source_start=min(20 * SEC, vert.duration - 4 * SEC),
                scale=1.3, keyframes=[Keyframe("scale", 0, 1.3), Keyframe("x", 0, -0.15), Keyframe("x", 4 * SEC, 0.15)])

    anims = [a for a in tpl.library if a.kind == "text_animation"]
    w.add_text("TEST 1: zoom chậm", start=0, duration=4 * SEC, y=0.75,
               style=TextStyle(size=14, color=YELLOW, stroke_color=BLACK), animations=anims)
    w.add_text("이게 1조짜리입니다", start=0, duration=2 * SEC, y=-0.62, style=sub)
    w.add_text("地獄の合図は深い", start=2 * SEC, duration=2 * SEC, y=-0.62, style=sub)
    w.add_text("TEST 2: khối 4:3", start=4 * SEC, duration=4 * SEC, y=top43,
               style=TextStyle(size=14, color=YELLOW, stroke_color=BLACK))
    w.add_text("Subtitle in the bottom band", start=4 * SEC, duration=4 * SEC, y=bottom43, style=sub)
    w.add_text("TEST 3: khối 1:1", start=8 * SEC, duration=3 * SEC, y=top11,
               style=TextStyle(size=14, color=YELLOW, stroke_color=BLACK))
    w.add_text("TEST 4: lia khung trái → phải", start=11 * SEC, duration=4 * SEC, y=0.75,
               style=TextStyle(size=12, color=WHITE, stroke_color=BLACK))

    w.add_sticker(tpl.find("sticker"), start=2 * SEC, duration=2 * SEC, x=0.55, y=0.35, scale=0.7)
    w.add_effect(tpl.find("video_effect"), start=0, duration=SEC)
    w.add_filter(tpl.find("filter"), start=4 * SEC, duration=4 * SEC)
    music = next((m for m in tpl.library if m.kind == "music" and not m.is_vip), tpl.find("music"))
    w.add_music(music, target_start=0, duration=15 * SEC, volume=1.0,
                keyframes=[Keyframe("volume", 0, 1.0), Keyframe("volume", 4 * SEC, 1.0),
                           Keyframe("volume", 4 * SEC + 300_000, 0.2), Keyframe("volume", 15 * SEC, 0.2)])
    # Âm thanh local (giả làm voice hook) nếu mẫu có: dùng lại file CapCut đã nhập trong mẫu
    local = next((a for a in tpl.timeline["materials"]["audios"] if a.get("type") == "extract_music"), None)
    if local:
        w.add_local_audio(Path(local["path"]), local["duration"], target_start=0,
                          duration=min(4 * SEC, local["duration"]), volume=1.0)
    return w


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("template_dir", type=Path)
    parser.add_argument("--name", default="demo_tool_v2")
    parser.add_argument("--drafts-root", type=Path, help="mặc định: thư mục chứa dự án mẫu")
    parser.add_argument("--fold-root", help="(chỉ dùng khi tạo hộ) đường dẫn thư mục draft trên máy đích")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    drafts_root = args.drafts_root or args.template_dir.parent
    w = build(args.template_dir, drafts_root, args.name)
    dst = w.save(overwrite=args.overwrite, check_capcut=not args.fold_root)
    if args.fold_root:
        meta_path = dst / "draft_meta_info.json"
        meta = read_json(meta_path)
        meta["draft_fold_path"] = args.fold_root.rstrip("/") + "/" + args.name
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Đã tạo draft: {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
