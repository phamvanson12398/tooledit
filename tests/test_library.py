"""Kho cảnh chung (chủ dự án yêu cầu 17/10): job Ý tưởng xong → cắt cảnh đẹp vào kho; Bán content / Ý tưởng thiếu cảnh thì
AI lấy cảnh kho (đúng thứ câu nói), không có thì dựng như cũ."""

import json
from pathlib import Path

from app import scene_library
from app.director.fake import FakeDirector
from app.director.schemas import Catalog, CatalogShot, SellScript, Shot
from app.director.sell import check_sell_script, sell_to_dub
from app.jobs.job import JobOptions, Status
from app.planner.sell_sync import build_sell
from tests.test_planner import _short_plan
from tests.test_runner import make_runner as _make_runner, prepare

FIX = Path(__file__).parent / "fixtures" / "director"
SELL = json.loads((FIX / "sell.json").read_text(encoding="utf-8"))
CAP = json.loads((FIX / "captions.json").read_text(encoding="utf-8"))


def fake_cut(args):
    Path(args[-1]).write_bytes(b"\x00" * 1000)


def _cat():
    return Catalog(shots=[CatalogShot(start=0, end=20, desc_vi="người nói", quality=2),
                          CatalogShot(start=20, end=60, desc_vi="phố ẩm thực, bát mì bốc khói", tags=["ẩm thực"], quality=5),
                          CatalogShot(start=60, end=66, desc_vi="biển hiệu có chữ", quality=5, text=True),
                          CatalogShot(start=66, end=67.5, desc_vi="cảnh vụt qua", quality=5)])


def _add(lib_id="L1", ratio="16:9", desc="bát mì bốc khói", job="khac", uses=None, duration=5.0):
    lib = scene_library.root()
    (lib / "clips").mkdir(parents=True, exist_ok=True)
    rel = f"clips/{lib_id}_{job}.mp4"
    (lib / rel).write_bytes(b"\x00" * 10)
    items = scene_library.load_index(lib)
    items.append({"id": lib_id, "file": rel, "desc_vi": desc, "tags": ["ẩm thực"], "quality": 5, "duration": duration,
                  "width": 1920, "height": 1080, "ratio": ratio, "job_id": job, "source": "a.mp4", "src_start": 0,
                  "src_end": duration, "added": "2026-10-17", "used_by": uses or []})
    scene_library.save_index(lib, items)


def test_picks_filters_and_trims():
    got = scene_library.picks(_cat().shots, [], {"min_quality": 4, "min_s": 2, "max_s": 12})
    assert [(a, b) for a, b, _ in got] == [(34.0, 46.0)]  # cảnh dài → đoạn giữa 12s; bỏ cảnh xấu / có chữ / quá ngắn
    assert scene_library.picks(_cat().shots, [(40, 41)], {"min_quality": 4}) == []  # chạm đoạn vi phạm chính sách


def test_harvest_index_dedupe_and_limit():
    n = scene_library.harvest("j9", Path("C:/v/long.mp4"), (1920, 1080), _cat(), cut_fn=fake_cut)
    lib = scene_library.root()
    items = scene_library.load_index(lib)
    assert n == 1 and items[0]["id"] == "L1" and items[0]["ratio"] == "16:9" and (lib / items[0]["file"]).is_file()
    assert items[0]["desc_vi"].startswith("phố ẩm thực") and items[0]["duration"] == 12.0
    assert scene_library.harvest("j9", Path("C:/v/long.mp4"), (1920, 1080), _cat(), cut_fn=fake_cut) == 0  # không trùng
    full = {**scene_library.cfg(), "max_gb": 0}
    logs = []
    assert scene_library.harvest("j10", Path("C:/v/x.mp4"), (1920, 1080), _cat(), cut_fn=fake_cut, c=full,
                                 log=logs.append) == 0 and "Kho cảnh đầy" in logs[0]


def test_candidates_ratio_uses_and_rank():
    _add("L1", desc="cảnh núi tuyết")
    _add("L2", desc="bát mì bốc khói")
    _add("L3", ratio="9:16", desc="bát mì dọc")
    _add("L4", desc="bát mì", uses=["a", "b", "c"])
    _add("L5", desc="bát mì của chính job", job="j1")
    got = [x["id"] for x in scene_library.candidates("16:9", "quán mì, bát mì nóng", exclude_job="j1")]
    assert got == ["L2", "L1"]  # cùng khung, chưa dùng quá 3 video, không lấy cảnh của chính job; hợp chủ đề lên trước
    assert "L4" in [x["id"] for x in scene_library.candidates("16:9", "", exclude_job="c")]  # job đã dùng → dựng lại được


def test_check_and_build_with_library_shot():
    r = SellScript.model_validate(SELL)
    lines = list(r.lines)
    lines[1] = lines[1].model_copy(update={"shots": [Shot(start=0, end=3, lib="L2")]})
    r2 = r.model_copy(update={"lines": lines})
    kw = dict(duration=60.0, scenes=[{"start": 0.0, "end": 60.0}], cps=10.0, target_s=65, cfg={"script_fill": [0.9, 1.1]})
    assert not check_sell_script(r2, "ko", library={"L2": 5.0}, **kw)
    assert any("không có cảnh kho L2" in e for e in check_sell_script(r2, "ko", library={}, **kw))
    assert any("chiếm" in e for e in check_sell_script(r2, "ko", library={"L2": 5.0}, lib_share=0.01, **kw))
    clips, _, _ = build_sell(sell_to_dub(r2), {}, [{"start": 0, "end": 60}], 60.0, cps=10.0)
    lib = [c for c in clips if c.lib]
    assert lib and all(c.lib == "L2" and 0 <= c.source_start < c.source_end <= 3.0 + 1e-6 for c in lib)


def test_sell_job_uses_library_and_ideas_job_harvests(tmp_path, monkeypatch):
    _add("L1", desc="bát mì bốc khói")
    script = json.loads(json.dumps(SELL))
    script["lines"][1]["shots"] = [{"start": 0, "end": 3, "lib": "L1"}]
    jobs, job = prepare(tmp_path, JobOptions(sell=True, target_language="ko", client_id="k"))
    r = _make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan(), "sell": script})
    job = r.run(job)
    assert job.step == "dub_voice", job.message
    prompt = next(c["prompt"] for c in r.director.calls if c["task"] == "sell")
    assert "- L1 [5.0s] bát mì bốc khói" in prompt
    for n in range(1, len(script["lines"]) + 1):
        (jobs / "j1" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    draft = Path(job.data["draft"])
    content = json.loads((draft / "draft_content.json").read_text(encoding="utf-8"))
    paths = [m["path"] for m in content["materials"]["videos"]]
    assert any(Path(p).name == "L1_khac.mp4" and Path(p).parent == draft / "media" for p in paths)  # chép vào dự án
    assert scene_library.load_index(scene_library.root())[0]["used_by"] == ["j1"]

    # job Ý tưởng xong → cảnh đẹp vào kho
    from app.analysis import ffmpeg

    monkeypatch.setattr(ffmpeg, "run", lambda args, exe=None: fake_cut(args))
    jobs2, job2 = prepare(tmp_path / "b", JobOptions(sell=True, ideas=True, target_language="ko", client_id="k"))
    r2 = _make_runner(tmp_path / "b", jobs2)
    r2._director = FakeDirector(responses={"plan": _short_plan(), "captions": [{**CAP, "video_index": i} for i in (1, 2)]})
    job2 = r2.run(job2)
    r2.apply_ideas(job2, [2])
    job2 = r2.resume(job2)
    n = len(json.loads((FIX / "ideas_script.json").read_text(encoding="utf-8"))["lines"])
    for k in range(1, n + 1):
        (jobs2 / "j1" / "voice" / f"video01_dub{k:02d}.wav").write_bytes(b"RIFF")
    job2 = r2.resume(job2)
    assert job2.status == Status.done, job2.message
    items = scene_library.load_index(scene_library.root())
    assert [(x["id"], x["src_start"], x["src_end"]) for x in items[1:]] == [("L2", 34.0, 46.0)]
    assert job2.data["library_added"] == 1
