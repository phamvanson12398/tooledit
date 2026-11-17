"""Dịch chữ trên màn hình (chủ dự án yêu cầu 17/11): giữ NGUYÊN video gốc; tool thấy chữ có sẵn trên màn hình, dịch sang
ngôn ngữ đã chọn, che chữ gốc bằng dải nền rồi đè bản dịch lên đúng chỗ."""

import json
from pathlib import Path

from app.director.schemas import ScreenTextScript
from app.director.textnote import (
    check_screen_texts,
    keep_ranges,
    refine_items,
    repair_screen_texts,
    screen_items,
    textnote_plan,
)
from app.jobs.job import JobOptions, Status
from app.planner.textcover import fit_text_scale
from tests.test_runner import make_runner as _make_runner
from tests.test_runner import prepare

FIX = json.loads((Path(__file__).parent / "fixtures" / "director" / "textnote.json").read_text(encoding="utf-8"))
CFG = {"min_item_s": 0.5, "min_box": 0.01}


def _r(data):
    return ScreenTextScript.model_validate(data)


def test_check_screen_texts():
    assert check_screen_texts(_r(FIX), "ko", duration=60.0, cfg=CFG) == []
    it = FIX["items"][0]
    bad_box = {**FIX, "items": [{**it, "box": [0.9, 0.8, 0.1, 0.9]}]}
    assert any("`box`" in e for e in check_screen_texts(_r(bad_box), "ko", duration=60.0, cfg=CFG))
    wrong = {**FIX, "items": [{**it, "text": "today tomato eggs"}]}
    assert any("ngôn ngữ đích" in e for e in check_screen_texts(_r(wrong), "ko", duration=60.0, cfg=CFG))
    brand = {**FIX, "items": [{**it, "text_orig": "iPhone 15", "text": "iPhone 15"}]}  # tên riêng giữ nguyên được
    assert check_screen_texts(_r(brand), "ko", duration=60.0, cfg=CFG) == []
    late = {**FIX, "items": [{**it, "start": 70, "end": 72}]}
    assert any("trong video" in e for e in check_screen_texts(_r(late), "ko", duration=60.0, cfg=CFG))


def test_repair_merges_repeats():
    r, fixes = repair_screen_texts(_r(FIX), 60.0, CFG)
    assert [(x.start, x.end) for x in r.items] == [(2.0, 9.0), (20.0, 24.0)] and fixes  # 2 dòng trùng nối tiếp → 1
    short = {**FIX, "items": [{**FIX["items"][2], "end": 20.2}]}
    assert repair_screen_texts(_r(short), 60.0, CFG)[0].items == []  # hiện chưa tới 0.5s → bỏ


def test_refine_items_snaps_box_and_time(tmp_path):
    import cv2
    import numpy as np

    frames = []
    for k in range(10):  # chữ trắng ở dải dưới từ giây 3 tới giây 6
        img = np.full((360, 640, 3), 40, np.uint8)
        if 3 <= k <= 6:
            cv2.putText(img, "SUBTITLE TEXT HERE", (120, 310), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        p = tmp_path / f"f{k}.jpg"
        cv2.imwrite(str(p), img)
        frames.append((float(k), p))
    r = _r({"items": [{"start": 2.0, "end": 8.0, "box": [0.15, 0.78, 0.85, 0.92], "text_orig": "x", "text": "자막"}],
            "editor_notes": ""})
    out, n = refine_items(r, frames, {"refine_expand": 0.3, "refine_density": 0.08})
    it = out.items[0]
    assert n == 1 and 2.4 <= it.start <= 3.0 and 6.0 <= it.end <= 7.0  # đúng lúc chữ thật sự hiện
    assert it.box[0] < 0.2 and it.box[2] > 0.75 and 0.75 < it.box[1] < it.box[3] < 0.95


def test_plan_and_scale():
    assert keep_ranges(60.0, [(10, 12)]) == [(0.0, 10.0), (12.0, 60.0)]
    plan = textnote_plan(_r(FIX), 60.0, [])
    assert [(c.source_start, c.source_end, c.speed) for c in plan.clips] == [(0.0, 60.0, 1.0)] and plan.emphasis == []
    assert screen_items(_r(FIX))[2] == {"start": 20.0, "end": 24.0, "box": [0.3, 0.1, 0.7, 0.18], "text": "소금 5g"}
    # chữ dài → thu nhỏ cho vừa chiều ngang dải; chữ ngắn → theo chiều cao dải
    assert fit_text_scale("가" * 30, 0.5, 0.03, 15, 0.0017) < fit_text_scale("가나", 0.5, 0.03, 15, 0.0017)


def test_full_textnote_job(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(textnote=True, target_language="ko", client_id="k"))
    r = _make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.done, job.message
    tasks = [c["task"] for c in r.director.calls]
    assert "textnote" in tasks and "plan" not in tasks and "dub" not in tasks
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    vids = {m["id"]: m for m in content["materials"]["videos"]}
    segs = [s for t in content["tracks"] if t["type"] == "video" for s in t["segments"]
            if vids.get(s["material_id"], {}).get("type") == "video"]
    assert abs(sum(s["target_timerange"]["duration"] for s in segs) - 60_000_000) < 100_000  # không cắt giây nào
    texts = [m.get("content", "") for m in content["materials"]["texts"]]
    assert sum("토마토" in t for t in texts) == 1 and any("소금 5g" in t for t in texts)  # bản dịch (đã gộp dòng trùng)
    assert sum("■" in t for t in texts) == 2  # mỗi chữ một dải che chữ gốc
    assert not any("こんにちは" in t for t in texts)  # không phụ đề lời gốc


def test_home_textnote_mode(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    c = TestClient(app)
    home = c.get("/").text
    assert "name='mode' value='textnote'" in home and "Dịch chữ trên màn hình" in home
    res = c.post("/jobs", data={"footage": str(f), "mode": "textnote", "target_language": "ja", "hook": "on"},
                 follow_redirects=False)
    job = Job.load(tmp_path / "jobs", res.headers["location"].rsplit("/", 1)[1])
    assert job.options.textnote and not job.options.hook and job.options.target_language == "ja"
    assert "🔤 Dịch chữ trên màn hình" in c.get(f"/jobs/{job.job_id}").text
    assert "Chưa chọn ngôn ngữ" in c.post("/jobs", data={"footage": str(f), "mode": "textnote"}).text
