"""Kiểu dựng trang điểm / làm đẹp (chủ dự án yêu cầu 03/10)."""

import json

from app.capcut_writer import SEC, DraftTemplate
from app.director.schemas import EditPlan, Understanding, check_plan
from app.planner.builder import build
from app.styles import available_styles, load_style, styles_for_prompt
from tests.test_planner import SAMPLE, _analysis, load


def test_makeup_style_offered_to_director():
    assert "makeup" in available_styles()
    assert "makeup: Trang điểm / làm đẹp" in styles_for_prompt()
    st = load_style("makeup")
    assert st["cold_open"] and st["arrows"] and "TUA NHANH" in st["director_brief"]


def test_makeup_plan_builds_cold_open_fast_steps_arrow_and_final_look(tmp_path):
    style = load_style("makeup")
    p = load("plan.json")
    p["clips"] = [
        {"source_start": 40.0, "source_end": 42.0, "repeat": True, "purpose_vi": "mở bằng look hoàn thiện"},
        {"source_start": 1.0, "source_end": 6.1, "purpose_vi": "mặt mộc"},
        {"source_start": 7.3, "source_end": 22.0, "speed": 2.0, "purpose_vi": "tán nền — tua nhanh"},
        {"source_start": 23.1, "source_end": 45.0, "purpose_vi": "kẻ mắt, môi"},
        {"source_start": 41.0, "source_end": 43.0, "speed": 0.5, "replay": True, "purpose_vi": "khoe kết quả"},
    ]
    p["arrows"] = [{"source_time": 25.0, "x": 0.6, "y": 0.4, "points": "left", "duration": 1.2}]
    plan = EditPlan.model_validate(p)
    assert check_plan(plan, 173.8, min_s=10) == []
    res = build(plan, Understanding.model_validate(load("understand.json")), _analysis(), DraftTemplate(SAMPLE),
                tmp_path, "makeup", style)
    tl = res.writer.build_timeline()
    videos = [s for t in tl["tracks"] if t["type"] == "video" for s in t["segments"]]
    assert any(v["speed"] == 2.0 for v in videos)  # đoạn tán tua nhanh
    final = [v for v in videos if v["speed"] == 0.5]
    assert final and final[0]["target_timerange"]["duration"] == round(2.0 / 0.5 * SEC)
    mats = {m["id"]: json.loads(m["content"])["text"] for m in tl["materials"]["texts"]}
    texts = [mats[s["material_id"]] for t in tl["tracks"] if t["type"] == "text" for s in t["segments"]]
    assert "完成" in texts  # nhãn kết quả (tiếng Nhật) trên clip quay chậm
    assert "→" in texts     # mũi tên chỉ vùng đang trang điểm
    arrow = next(m for m in tl["materials"]["texts"] if json.loads(m["content"])["text"] == "→")
    fill = json.loads(arrow["content"])["styles"][0]["fill"]["content"]["solid"]["color"]
    assert fill == [1, 0.45, 0.7]  # mũi tên màu hồng của kiểu makeup (không phải xanh thể thao)
