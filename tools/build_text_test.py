"""Tạo draft "thử chữ" để chọn cỡ và kiểu trang trí chữ hook bằng mắt trên CapCut thật.

0–6s: cùng một câu ở các cỡ 15 / 20 / 25 / 30 / 40 / 50 (xếp chồng từ trên xuống).
6–12s: 5 kiểu trang trí A–E ở cỡ 30.

Chạy trên Windows (đóng CapCut trước):
    .venv\\Scripts\\python tools\\build_text_test.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.capcut_writer import SEC, DraftTemplate, DraftWriter, TextBackground, TextStyle, VideoSource  # noqa: E402
from app.capcut_writer.template import read_json  # noqa: E402

TEXT = "ライバルを病院へ!?"
YELLOW, WHITE, BLACK, RED = (1.0, 0.85, 0.0), (1.0, 1.0, 1.0), (0.0, 0.0, 0.0), (0.9, 0.15, 0.15)


def variants(tpl: DraftTemplate) -> list[tuple[str, TextStyle, list]]:
    anim = lambda kinds: [next(a for a in tpl.library if a.kind == "text_animation" and a.category == k)
                          for k in kinds if any(a.kind == "text_animation" and a.category == k for a in tpl.library)]
    return [
        ("A", TextStyle(size=30, color=YELLOW, stroke_color=BLACK, stroke_width=0.16), []),
        ("B", TextStyle(size=30, color=WHITE, background=TextBackground(color="#E53935", round_radius=0.3)), []),
        ("C", TextStyle(size=30, color=BLACK, background=TextBackground(color="#FFD600", round_radius=0.5)), []),
        ("D", TextStyle(size=30, color=WHITE, stroke_color=BLACK, stroke_width=0.2), anim(["in", "loop"])),
        ("E", TextStyle(size=30, color=RED, stroke_color=WHITE, stroke_width=0.16), anim(["in"])),
    ]


def build(template_dir: Path, drafts_root: Path, name: str) -> DraftWriter:
    tpl = DraftTemplate(template_dir)
    vids = tpl.timeline["materials"]["videos"]
    v = next(x for x in vids if x["height"] > x["width"])
    src = VideoSource(Path(v["path"]), v["width"], v["height"], v["duration"])
    w = DraftWriter(tpl, drafts_root, name)
    w.add_video(src, target_start=0, duration=12 * SEC, source_start=0)
    for i, size in enumerate((15, 20, 25, 30, 40, 50)):
        w.add_text(f"{size}: {TEXT}", start=0, duration=6 * SEC, y=0.8 - i * 0.3,
                   style=TextStyle(size=size, color=YELLOW, stroke_color=BLACK, stroke_width=0.12))
    for i, (label, style, anims) in enumerate(variants(tpl)):
        w.add_text(f"{label} {TEXT}", start=6 * SEC, duration=6 * SEC, y=0.75 - i * 0.35, style=style,
                   animations=anims)
    return w


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--template", type=Path, help="thư mục dự án mẫu (mặc định theo config/capcut.yaml)")
    parser.add_argument("--drafts-root", type=Path)
    parser.add_argument("--fold-root", help="(chỉ dùng khi tạo hộ) đường dẫn thư mục draft trên máy đích")
    args = parser.parse_args(argv)
    from app.jobs.runner import drafts_root, find_template

    root = args.drafts_root or drafts_root()
    template = args.template or find_template(root, config.load("capcut").get("template_name", "capcut_template"))
    w = build(Path(template), root, "test_chu_v1")
    dst = w.save(overwrite=True, check_capcut=not args.fold_root)
    if args.fold_root:
        meta = read_json(dst / "draft_meta_info.json")
        meta["draft_fold_path"] = args.fold_root.rstrip("/") + "/test_chu_v1"
        (dst / "draft_meta_info.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"Đã tạo draft: {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
