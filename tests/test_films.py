"""Chế độ "Content nhiều phim từ bài TikTok ảnh" (chủ dự án yêu cầu 14/10): AI xem ảnh + tiêu đề bài gốc → content mới
nhiều phim → chủ dự án chọn file từng phim → AI tìm cảnh trong đúng phim → voice → dựng, xen dừng hình."""

import json
from pathlib import Path

from app.director.fake import FakeDirector
from app.director.films import check_idea, load_cfg, to_script
from app.director.schemas import FilmsIdea
from app.jobs.job import Job, JobOptions, Status
from tests.test_review import SENT
from tests.test_runner import make_runner

CFG = load_cfg()
TEXT = SENT.strip()  # 93 chữ ≈ 9.3 giây ở 10 chữ/giây


def _idea(n_freeze: int = 2, text: str = TEXT) -> dict:
    lines = []
    for k in range(8):
        film = "phim1" if k < 4 else "phim2"
        freeze = k in (1, 5)[:n_freeze]
        lines.append({"film": film, "shot": "freeze" if freeze else "video", "text": text, "text_vi": "câu kể",
                      "want_vi": f"cảnh {k + 1}", "label": ("타키" if film == "phim1" else "미츠하") if freeze else ""})
    return {"topic_vi": "Top nhân vật hay trong phim hoạt hình", "story_vi": "Mở: ai cũng nhớ… rồi từng nhân vật… kết.",
            "films": [{"key": "phim1", "title": "너의 이름은", "title_vi": "Your Name", "characters": ["Taki"]},
                      {"key": "phim2", "title": "날씨의 아이", "title_vi": "Đứa con của thời tiết",
                       "characters": ["Hina"]}],
            "lines": lines, "titles_top": ["잊을 수 없는", "애니 주인공들"],
            "music": {"name": None, "mood_vi": "cảm động", "energy": "mid"},
            "caption": "다시 보고 싶은 애니 주인공들", "caption_vi": "Những nhân vật muốn xem lại",
            "hashtags": ["#애니", "#추천", "#명장면"], "hashtags_vi": ["anime", "gợi ý", "cảnh hay"],
            "editor_notes": "2 phim, mỗi phim 1 lần dừng hình"}


def _picks() -> dict:
    picks = []
    for n in range(1, 9):
        base = 20.0 + ((n - 1) % 4) * 60.0
        p = {"line": n, "start": base, "end": base + 15.0, "why_vi": "khung 00_x.jpg"}
        if n in (2, 6):
            p["freeze_t"] = base + 5.0
        picks.append(p)
    return {"picks": picks, "editor_notes": "tìm bằng khung hình"}


def test_idea_checks():
    ok = FilmsIdea.model_validate(_idea())
    assert check_idea(ok, "ko", CFG, set()) == []
    no_freeze = FilmsIdea.model_validate(_idea(n_freeze=0))
    assert any("DỪNG HÌNH" in e for e in check_idea(no_freeze, "ko", CFG, set()))
    bad = _idea()
    bad["lines"][0]["film"] = "phim9"
    bad["lines"][1]["label"] = ""
    bad["lines"][2]["text"] = "This is English text " * 4
    errs = check_idea(FilmsIdea.model_validate(bad), "ko", CFG, set())
    assert any("phim9" in e for e in errs) and any("label" in e for e in errs) and any("tiếng Hàn" in e for e in errs)
    short = FilmsIdea.model_validate({**_idea(), "lines": _idea()["lines"][:4]})  # ~37 giây < 60
    assert any("viết THÊM" in e for e in check_idea(short, "ko", CFG, set()))


def _analysis_for(job_dir: Path, films: list[Path]) -> None:
    a = job_dir / "analysis"
    (a / "frames").mkdir(parents=True, exist_ok=True)
    frames, scenes, tr, subj = [], [], [], []
    for i, f in enumerate(films):
        for k in range(10):
            fr = a / "frames" / f"{i:02d}_{k * 30:08.2f}.jpg"
            fr.write_bytes(b"\xff\xd8")
            frames.append({"footage": i, "t": k * 30.0, "file": fr.relative_to(a).as_posix()})
        scenes.append({"footage": i, "path": f.as_posix(), "duration": 300.0, "width": 1920, "height": 1080,
                       "scenes": [{"index": j, "start": j * 10.0, "end": j * 10.0 + 10} for j in range(30)]})
        tr.append({"footage": i, "language": None, "segments": []})
        subj.append({"footage": i, "points": [], "face_count_max": 0, "faces": []})
    for name, data in (("frames.json", frames), ("scenes.json", scenes), ("transcript.json", tr),
                       ("subjects.json", subj)):
        (a / name).write_text(json.dumps(data), encoding="utf-8")


def _fake_still(src, at_s, dst, crop, width):
    import cv2
    import numpy as np

    dst.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst), np.zeros((1080, 972, 3), np.uint8))
    return dst, 972, 1080


def test_films_job_end_to_end(tmp_path):
    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [], JobOptions(films=True, target_language="ko"), job_id="mf")
    job.step = "post"
    job.save(jobs)
    r = make_runner(tmp_path, jobs)
    r.save_post(job, title="5 nhân vật anime đáng nhớ")  # chủ dự án tự gõ tiêu đề
    r._still_fn = _fake_still
    r._director = FakeDirector(responses={"films_idea": _idea(), "films_match": _picks()})
    analyzed = []

    def fake_analyze(job, root, progress):
        analyzed.append(list(job.footage))
        _analysis_for(job.dir(root), [Path(p) for p in job.footage])
    r._analyze_fn = fake_analyze

    job = r.run(job)  # chưa có ảnh bài gốc → chờ
    assert job.step == "post" and job.status == Status.waiting and "ẢNH" in job.message
    post = jobs / "mf" / "post"
    for k in range(3):
        (post / f"anh_{k + 1:02d}.jpg").write_bytes(b"\xff\xd8")
    job = r.resume(job)
    assert job.step == "films_wait" and job.status == Status.waiting, job.message
    assert "phim1 = Your Name" in job.message and "phim2" in job.message
    idea_call = next(c for c in r._director.calls if c["task"] == "films_idea")
    assert "5 nhân vật anime đáng nhớ" in idea_call["prompt"] and len(idea_call["images"]) == 3
    assert "DỪNG HÌNH" in idea_call["prompt"] and "30%" in idea_call["prompt"]

    f1, f2 = tmp_path / "your_name.mkv", tmp_path / "weathering.mp4"
    f1.write_bytes(b"x")
    f2.write_bytes(b"x")
    assert r.set_films(job, {"phim1": str(f1), "phim2": str(tmp_path / "khong_co.mp4")}) == ["phim2"]
    job = r.resume(job)
    assert job.step == "films_wait" and "phim2" in job.message                         # vẫn thiếu phim 2
    r.set_films(job, {"phim2": str(f2)})
    job = r.resume(job)
    assert job.step == "dub_voice" and job.status == Status.waiting, job.message
    assert analyzed == [[f1.resolve().as_posix(), f2.resolve().as_posix()]]          # mỗi phim một footage, không nối
    match_calls = [c for c in r._director.calls if c["task"] == "films_match"]
    assert len(match_calls) == 2 and any("Your Name" in c["prompt"] for c in match_calls)
    assert all(len(c["images"]) == 10 for c in match_calls)                          # khung hình của đúng phim đó
    picks = json.loads((jobs / "mf" / "plan" / "films_match.json").read_text(encoding="utf-8"))
    assert picks["1"]["film"] == "phim1" and picks["5"]["film"] == "phim2" and picks["2"]["freeze_t"] == 85.0
    txt = (jobs / "mf" / "dub_scripts.txt").read_text(encoding="utf-8")
    assert "📜 BÀI LỜI ĐỌC" in txt and len(r._dub_scripts(job)[1].lines) == 8

    for n in range(1, 9):
        (jobs / "mf" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    d1 = job.data["drafts"][0]
    assert abs(d1["duration_s"] - 8 * 3.05) < 0.3                                    # video dài đúng bằng giọng đọc
    content = json.loads((Path(d1["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    vids = content["materials"]["videos"]
    paths = {Path(m["path"]).name for m in vids}
    assert {"your_name.mkv", "weathering.mp4"} <= paths                               # hình từ 2 phim
    photos = [m for m in vids if m.get("type") == "photo"]
    assert len(photos) == 2                                                           # 2 lần dừng hình = ảnh cắt từ phim
    texts = [json.loads(t["content"])["text"] for t in content["materials"]["texts"]]
    assert "타키" in texts and "미츠하" in texts                                        # tên nhân vật khi dừng hình
    assert "너의 이름은" in texts and "날씨의 아이" in texts                              # tên phim khi sang phim mới
    assert "잊을 수 없는" in texts
    cap = (jobs / "mf" / "deliver" / "video01_captions.txt").read_text(encoding="utf-8")
    assert "#애니" in cap and "DỊCH TIẾNG VIỆT" in cap
    # 🔎 tìm lại cảnh: giữ voice đã thu, hỏi lại AI tìm cảnh, dựng lại
    n_match = len([c for c in r._director.calls if c["task"] == "films_match"])
    r.redo(job, "match")
    job = r.run(job)
    assert job.status == Status.done, job.message
    assert len([c for c in r._director.calls if c["task"] == "films_match"]) == n_match + 2
    assert (jobs / "mf" / "voice" / "video01_dub01.wav").is_file()                     # voice không bị cất đi


def test_to_script_for_voice_page():
    idea = FilmsIdea.model_validate(_idea())
    s = to_script(idea, {1: {"start": 20.0, "end": 35.0}})
    assert s.story_vi and len(s.lines) == 8 and s.lines[0].source_start == 20.0
    assert "Your Name" in s.lines[0].action_vi and "dừng hình" in s.lines[1].action_vi


def test_web_form_films(tmp_path):
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    client = TestClient(app)
    home = client.get("/").text
    assert "Content nhiều phim" in home and 'name="post_title"' in home and 'name="post_images"' in home
    assert 'name="post_url"' not in home                                               # bỏ ô dán link (14/10)
    # ô "Chọn video" (bắt buộc) bị ẩn ở chế độ này phải bị tắt — không thì trình duyệt chặn nút Bắt đầu (lỗi 14/10)
    assert "querySelectorAll('input,select,textarea')" in home
    no_lang = client.post("/jobs", data={"mode": "films", "post_title": "Top 5"})
    assert "Chưa chọn ngôn ngữ" in no_lang.text
    no_title = client.post("/jobs", data={"mode": "films", "target_language": "ja"})
    assert "Chưa có tiêu đề" in no_title.text
    r = client.post("/jobs", data={"mode": "films", "target_language": "ja", "post_title": "Top 5"},
                    files=[("post_images", ("a.jpg", b"\xff\xd8", "image/jpeg")),
                           ("post_images", ("b.png", b"\x89PNG", "image/png"))], follow_redirects=False)
    job = Job.load(tmp_path / "jobs", r.headers["location"].rsplit("/", 1)[1])
    assert job.options.films and job.step == "post" and job.options.target_language == "ja" and job.footage == []
    d = tmp_path / "jobs" / job.job_id
    assert sorted(p.name for p in (d / "post").glob("anh_*")) == ["anh_01.jpg", "anh_02.png"]
    page = client.get(f"/jobs/{job.job_id}").text
    assert "Content nhiều phim" in page and "Top 5" in page and "Chờ ảnh bài gốc" in page
    # chờ chọn phim: bảng chọn file từng phim + content AI viết
    (d / "plan").mkdir(parents=True, exist_ok=True)
    (d / "plan" / "films_idea.json").write_text(json.dumps(_idea(), ensure_ascii=False), encoding="utf-8")
    job.step, job.status = "films_wait", Status.waiting
    job.save(tmp_path / "jobs")
    page = client.get(f"/jobs/{job.job_id}").text
    assert "Chọn file từng phim" in page and "name='film_phim1'" in page and "Đứa con của thời tiết" in page
    assert "⏸️ dừng hình · 타키" in page and "Viết lại theo góp ý" in page


def test_web_post_and_films_routes(tmp_path):
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    jobs = tmp_path / "jobs"
    job = Job.create(jobs, [], JobOptions(films=True, target_language="ko"), job_id="mw")
    job.step, job.status = "post", Status.waiting
    job.save(jobs)
    calls = []

    class R:
        def __init__(self, root, log):
            from app.jobs.runner import Runner

            self.r = Runner(root, log=log)

        def __getattr__(self, k):
            return getattr(self.r, k)

        def resume(self, job):
            calls.append(job.step)
            return job

    app = create_app(jobs, R)
    app.state.worker.start = lambda job_id, action=None: app.state.worker._work(job_id, action)
    client = TestClient(app)
    client.post("/jobs/mw/post", data={"post_title": "Top 5 phim"},
                files=[("post_images", ("x.jpg", b"\xff\xd8", "image/jpeg"))])
    assert calls == ["post"]                                                          # chạy tiếp đúng MỘT lần
    assert (jobs / "mw" / "post" / "anh_01.jpg").is_file()
    assert json.loads((jobs / "mw" / "post" / "post.json").read_text(encoding="utf-8"))["title"] == "Top 5 phim"
    assert Job.load(jobs, "mw").data["post_title"] == "Top 5 phim"
    f = tmp_path / "a.mp4"
    f.write_bytes(b"x")
    client.post("/jobs/mw/films", data={"film_phim1": str(f)})
    assert Job.load(jobs, "mw").data["films"] == {"phim1": str(f.resolve())} and len(calls) == 2
