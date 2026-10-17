"""Ý tưởng từ video dài (chủ dự án yêu cầu 17/10): kho cảnh → ý tưởng → tick → mỗi ý tưởng một short kiểu Bán content."""

import json
from pathlib import Path

from app.director.fake import FakeDirector
from app.director.ideas import chunks, idea_videos, screen_ideas
from app.director.schemas import Catalog, IdeaList, SellScript, Shot
from app.director.sell import check_sell_script
from app.jobs.job import JobOptions, Status
from tests.test_planner import _short_plan
from tests.test_runner import make_runner as _make_runner, prepare

FIX = Path(__file__).parent / "fixtures" / "director"
CAP = json.loads((FIX / "captions.json").read_text(encoding="utf-8"))
N = len(json.loads((FIX / "ideas_script.json").read_text(encoding="utf-8"))["lines"])


def make_runner(tmp_path, jobs):
    r = _make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan(),
                                          "captions": [{**CAP, "video_index": i} for i in (1, 2)]})
    return r


def _calls(r, task):
    return [c for c in r.director.calls if c["task"] == task]


def test_chunks_split_long_video():
    assert chunks(500, 600) == [(0.0, 500)]
    parts = chunks(3600, 600)
    assert len(parts) == 6 and parts[0][0] == 0 and parts[-1][1] == 3600
    assert all(abs((b - a) - 600) < 1 for a, b in parts)
    assert len(chunks(1250, 600)) == 2  # phần cuối 50s quá ngắn → gộp vào phần trước


def test_screen_ideas_drops_thin_and_unknown():
    cat = Catalog.model_validate_json((FIX / "ideas_catalog.json").read_text(encoding="utf-8"))
    r = IdeaList.model_validate_json((FIX / "ideas_list.json").read_text(encoding="utf-8"))
    keep, drop = screen_ideas(r, cat, {"min_footage_s": 30, "min_quality": 2})
    assert [k["title_vi"] for k in keep] == ["Một ngày ăn sập phố ẩm thực", "Bát mì bốc khói"]
    assert keep[1]["pool"] == [{"start": 20.0, "end": 60.0, "desc_vi": "phố ẩm thực, quầy mì, bát mì bốc khói"}]
    assert drop[0]["title_vi"] == "Người dẫn kể chuyện" and "20s" in drop[0]["reason_vi"]
    v = idea_videos(keep, 60.0)
    assert [x["index"] for x in v] == [1, 2] and v[1]["idea"]["hook_vi"] == "Bát mì này có gì đặc biệt?"


def test_check_shots_must_stay_in_idea_pool():
    r = SellScript.model_validate_json((FIX / "ideas_script.json").read_text(encoding="utf-8"))
    bad = r.model_copy(update={"lines": [r.lines[0].model_copy(update={"shots": [Shot(start=2, end=6)]}),
                                         *r.lines[1:]]})
    kw = dict(duration=60.0, scenes=[{"start": 20.0, "end": 60.0}], cps=10.0, target_s=65, cfg={})
    errs = check_sell_script(bad, "ko", pool_only=True, **kw)
    assert any("không nằm trong các cảnh của ý tưởng" in e for e in errs)
    assert not any("ý tưởng" in e for e in check_sell_script(r, "ko", pool_only=True, **kw))


def test_full_ideas_job(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(sell=True, ideas=True, ideas_brief="khán giả Hàn mê ăn uống",
                                             target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    assert job.status == Status.waiting and job.step == "review_segments", job.message
    assert "Chọn ý tưởng" in job.message
    plan = jobs / "j1" / "plan"
    assert (plan / "catalog.json").is_file() and (plan / "catalog_parts" / "01.json").is_file()
    data = json.loads((plan / "segments.json").read_text(encoding="utf-8"))
    assert data["ideas"] and len(data["proposal"]["ideas"]) == 2 and len(data["proposal"]["dropped"]) == 1
    assert "khán giả Hàn mê ăn uống" in _calls(r, "ideas_list")[0]["prompt"]
    assert "S2 [20.0–60.0s" in _calls(r, "ideas_list")[0]["prompt"]

    r.apply_ideas(job, [1, 2])
    job = r.resume(job)
    assert job.status == Status.waiting and job.step == "dub_voice", job.message
    calls = _calls(r, "ideas_script")
    assert len(calls) == 2 and not _calls(r, "sell")
    assert "Bát mì này có gì đặc biệt?" in calls[1]["prompt"] and "phố ẩm thực" in calls[1]["prompt"]
    assert "30.0–34.0s" in calls[1]["prompt"]  # cảnh short 1 đã dùng → short 2 được dặn tránh
    assert all(float(Path(p).stem.split("_")[1]) >= 20 for p in calls[1]["images"])  # chỉ khung trong cảnh ý tưởng
    assert json.loads((plan / "sell_video02.json").read_text(encoding="utf-8"))["video_index"] == 2

    vdir = jobs / "j1" / "voice"
    for v in (1, 2):
        for n in range(1, N + 1):
            (vdir / f"video{v:02d}_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    for v in (1, 2):
        draft = tmp_path / "drafts" / f"k_j1_video{v:02d}"
        content = json.loads((draft / "draft_content.json").read_text(encoding="utf-8"))
        vids = {m["id"]: m for m in content["materials"]["videos"]}
        segs = [s for t in content["tracks"] if t["type"] == "video" for s in t["segments"]
                if vids.get(s["material_id"], {}).get("type") == "video"]
        assert segs
        if v == 2:  # short 2: mọi cảnh (kể cả cảnh bù) nằm trong kho cảnh của ý tưởng (20–60s)
            assert all(s["source_timerange"]["start"] >= 20_000_000 - 1 for s in segs)


def test_redo_ideas_keeps_catalog(tmp_path):
    jobs, job = prepare(tmp_path, JobOptions(sell=True, ideas=True, target_language="ko", client_id="k"))
    r = make_runner(tmp_path, jobs)
    job = r.run(job)
    r.redo_ideas(job, "thêm ý tưởng về đồ ngọt")
    job = r.run(job)
    assert job.step == "review_segments" and job.status == Status.waiting
    assert len(_calls(r, "ideas_catalog")) == 1 and len(_calls(r, "ideas_list")) == 2
    p = _calls(r, "ideas_list")[1]["prompt"]
    assert "thêm ý tưởng về đồ ngọt" in p and "Một ngày ăn sập phố ẩm thực" in p
    assert "ideas_redo" not in job.data


def test_home_and_panel_ideas_mode(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    client = TestClient(app)
    home = client.get("/").text
    assert "name='mode' value='ideas'" in home and "ideas_brief" in home
    res = client.post("/jobs", data={"footage": str(f), "mode": "ideas", "target_language": "ja",
                                     "ideas_brief": "người Nhật trẻ", "sell_variants": "3", "sell_s": "70"},
                      follow_redirects=False)
    job_id = res.headers["location"].rsplit("/", 1)[1]
    o = Job.load(tmp_path / "jobs", job_id).options
    assert o.ideas and o.sell and o.ideas_brief == "người Nhật trẻ" and o.sell_variants == 1 and o.sell_s == 70
    assert "Chưa chọn ngôn ngữ" in client.post("/jobs", data={"footage": str(f), "mode": "ideas"}).text
    # bảng chọn ý tưởng trên trang job
    jobs = tmp_path / "jobs"
    job = Job.load(jobs, job_id)
    from app.director.ideas import save_proposal

    (jobs / job_id / "plan").mkdir(parents=True, exist_ok=True)
    save_proposal(jobs / job_id / "plan", [{"title_vi": "Nhật có gì đẹp", "angle_vi": "cảnh đẹp", "hook_vi": "?",
                                            "kind_vi": "top list", "shots": ["S1"], "pool": [], "footage_s": 40}],
                  [], "ghi chú")
    job.step, job.status = "review_segments", Status.waiting
    job.save(jobs)
    page = client.get(f"/jobs/{job_id}").text
    assert "💡 Ý tưởng từ video dài" in page and "name='pick_1'" in page and "Nghĩ lại ý tưởng" in page
