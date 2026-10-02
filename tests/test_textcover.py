"""Chữ in sẵn trên footage: dò vùng chữ, cắt chặt hơn để tránh, không được thì che."""

import json

import cv2
import numpy as np

from app.analysis.textdetect import detect_text_boxes, merge_boxes
from app.capcut_writer import Crop
from app.planner.textcover import avoid_text, cover_glyphs, cover_rect


def _scene(seed: int, text: str | None, where: str = "bottom") -> np.ndarray:
    rng = np.random.default_rng(seed)
    g = cv2.GaussianBlur((rng.random((270, 480)) * 255).astype(np.uint8), (31, 31), 0)
    if text:
        y = 250 if where == "bottom" else 140
        cv2.putText(g, text, (60, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 255, 3, cv2.LINE_AA)
        cv2.putText(g, text, (60, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 1, cv2.LINE_AA)
    return g


def test_detect_burned_subtitles_in_reported_region():
    frames = [_scene(i, f"SUBTITLE LINE {i % 3}") for i in range(12)]
    boxes = detect_text_boxes(frames, ["bottom"])
    assert len(boxes) == 1
    l, t, r, b = boxes[0]
    assert t > 0.75 and b <= 1.0 and l < 0.2 and r > 0.5  # dải phụ đề phía dưới
    assert detect_text_boxes(frames, ["top"]) == []  # chỉ giữ vùng AI đã báo
    assert detect_text_boxes([_scene(i, None) for i in range(12)], ["bottom", "center"]) == []  # cảnh không chữ
    assert merge_boxes([(0.1, 0.8, 0.3, 0.9), (0.31, 0.8, 0.6, 0.9)]) == [(0.1, 0.8, 0.6, 0.9)]


def test_avoid_by_tighter_crop_or_cover():
    c = Crop(left=0.125, top=0.0, right=0.875, bottom=1.0)  # khung 4:3 trên footage 16:9
    new, left = avoid_text(c, [(0.1, 0.86, 0.9, 0.97)])  # phụ đề sát mép dưới → cắt bớt phía dưới
    assert not left and new.bottom <= 0.86 + 1e-9
    assert abs((new.right - new.left) / (new.bottom - new.top) - 0.75) < 1e-6  # giữ đúng tỉ lệ khung
    same, left = avoid_text(c, [(0.1, 0.4, 0.9, 0.6)])  # chữ giữa khung → không tránh được → che
    assert same is c and left
    rect = cover_rect(left[0], c, "4:3")
    assert abs(rect[1]) < 1e-9 and rect[2] > 0 and rect[3] > 0
    flipped = cover_rect((0.2, 0.4, 0.4, 0.6), c, "4:3", mirrored=True)
    assert flipped[0] > 0 > cover_rect((0.2, 0.4, 0.4, 0.6), c, "4:3")[0]  # cảnh lật → dải che lật theo
    glyphs, scale = cover_glyphs(rect[2], rect[3], 15, 0.0017)
    assert set(glyphs) == {"■"} and scale > 0
    assert avoid_text(c, [(0.0, 0.0, 0.05, 0.05)]) == (c, [])  # chữ ngoài khung cắt → không làm gì


def test_build_avoids_and_covers(tmp_path):
    from app.capcut_writer import DraftTemplate
    from app.director.schemas import EditPlan, Understanding
    from app.planner.builder import build
    from app.styles import load_style
    from tests.test_planner import SAMPLE, _analysis, load

    plan = EditPlan.model_validate(load("plan.json"))
    u = Understanding.model_validate(load("understand.json"))
    style = {**load_style("jp_telop"), "block_ratio": "4:3"}
    an = _analysis()
    an["text_boxes"] = [[0.1, 0.88, 0.9, 0.97]]  # phụ đề cứng sát đáy → tránh được bằng cách cắt
    res = build(plan, u, an, DraftTemplate(SAMPLE), tmp_path, "tc1", style)
    tl = res.writer.build_timeline()
    assert all(v["crop"]["lower_left_y"] <= 0.88 + 1e-6 for v in tl["materials"]["videos"] if v["type"] == "video")
    assert any("cắt chặt hơn để tránh ở" in n for n in res.notes)
    an["text_boxes"] = [[0.2, 0.45, 0.8, 0.55]]  # chữ giữa khung → phải che
    res = build(plan, u, an, DraftTemplate(SAMPLE), tmp_path, "tc2", style)
    tl = res.writer.build_timeline()
    texts = [json.loads(m["content"])["text"] for m in tl["materials"]["texts"]]
    covers = [m for m in tl["materials"]["texts"] if json.loads(m["content"])["text"].startswith("■")]
    assert covers and all(m["background_color"] == "#000000" and m["background_alpha"] == 0.6 for m in covers)
    assert any("che ở" in n for n in res.notes) and texts


def test_presence_times_only_when_text_shows():
    from app.analysis.textdetect import presence_times

    timed = [(float(t), _scene(t, "HELLO SUBS" if 4 <= t < 8 else None)) for t in range(12)]
    box = (0.08, 0.8, 0.7, 0.98)
    assert presence_times(timed, box) == [[3.5, 7.5]]  # chữ hiện ở các khung giây 4–7


def test_cover_only_while_text_visible_and_snapped(tmp_path):
    from app.capcut_writer import DraftTemplate
    from app.director.schemas import EditPlan, Understanding
    from app.planner.builder import build
    from app.styles import load_style
    from tests.test_planner import SAMPLE, _analysis, load

    plan = EditPlan.model_validate({**load("plan.json"), "clips": [{"source_start": 1.0, "source_end": 21.0}],
                                    "emphasis": [], "zooms": [], "sfx": []})
    u = Understanding.model_validate(load("understand.json"))
    style = {**load_style("jp_telop"), "block_ratio": "4:3"}
    an = _analysis()
    # chữ giữa khung (không tránh được), chỉ hiện từ giây 5 tới 9
    an["text_boxes"] = [{"box": [0.2, 0.45, 0.8, 0.55], "times": [[5.0, 9.0]]}]
    res = build(plan, u, an, DraftTemplate(SAMPLE), tmp_path, "tc3", style)
    tl = res.writer.build_timeline()
    mats = {m["id"]: m for m in tl["materials"]["texts"]}
    segs = [s for t in tl["tracks"] if t["type"] == "text" for s in t["segments"]
            if json.loads(mats[s["material_id"]]["content"])["text"].startswith("■")]
    assert len(segs) == 1
    assert segs[0]["target_timerange"]["start"] == 4_000_000 and segs[0]["target_timerange"]["duration"] == 4_000_000
    # chữ ngoài thời gian của clip → không cắt chặt, không che
    an["text_boxes"] = [{"box": [0.2, 0.45, 0.8, 0.55], "times": [[40.0, 45.0]]}]
    res = build(plan, u, an, DraftTemplate(SAMPLE), tmp_path, "tc4", style)
    assert not any(json.loads(m["content"])["text"].startswith("■") for m in res.writer.build_timeline()["materials"]["texts"])
    # chữ cứng gần hàng phụ đề → dải che đặt đúng hàng phụ đề (thành thanh phụ đề)
    from app.planner.builder import four_title_positions, layout_for

    sub_y = four_title_positions(layout_for(style))["bottom"]
    an["text_boxes"] = [{"box": [0.15, 0.72, 0.85, 0.80], "times": None}]
    res = build(plan, u, an, DraftTemplate(SAMPLE), tmp_path, "tc5", style)
    tl = res.writer.build_timeline()
    mats = {m["id"]: m for m in tl["materials"]["texts"]}
    covers = [s for t in tl["tracks"] if t["type"] == "text" for s in t["segments"]
              if json.loads(mats[s["material_id"]]["content"])["text"].startswith("■")]
    assert covers and all(abs(s["clip"]["transform"]["y"] - sub_y) < 1e-6 for s in covers)
    assert any("thanh phụ đề" in n for n in res.notes)
