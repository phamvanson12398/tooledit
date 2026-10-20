"""Chủ dự án 20/10: "các chế độ khi cấu hình đều cho chọn voice" — giọng Voice Studio chọn khi tạo job → OmniVoice tự đọc
ở MỌI chế độ có voice (không chỉ Bán content); nhiều nhân vật thì mọi nhân vật dùng giọng đó."""

from pathlib import Path

from app.director.fake import FakeDirector
from app.jobs.job import JobOptions, Status
from tests.test_planner import _short_plan
from tests.test_runner import make_runner, prepare
from tests.test_sell_more import _studio_voice, _wav, settings_mem  # noqa: F401  (fixture)
from tests.test_wild import PARTS


def _run(tmp_path, monkeypatch, opts, data=None):
    v = _studio_voice(tmp_path, monkeypatch)
    jobs, job = prepare(tmp_path, JobOptions(**opts, sell_voice=v["slug"]))
    job.data.update(data or {})
    job.save(jobs)
    r = make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan()})
    reqs = []

    def fake_tts(request, request_path, cfg, on_line):
        reqs.append(request)
        for it in request["items"]:
            _wav(Path(it["out"]), 2.0)

    r._tts_run = fake_tts
    return r.run(job), reqs


def test_anim_all_characters_use_chosen_voice(tmp_path, monkeypatch, settings_mem):
    job, reqs = _run(tmp_path, monkeypatch, {"anim": True, "target_language": "ko", "client_id": "k"})
    assert job.status == Status.done, job.message  # không dừng chờ thu voice
    voices = reqs[0]["voices"]
    assert {"냥이", "멍이"} <= set(voices) and all(x["mode"] == "clone" for x in voices.values())


def test_wild_reads_with_chosen_voice(tmp_path, monkeypatch, settings_mem):
    job, reqs = _run(tmp_path, monkeypatch, {"wild": True, "target_language": "ko", "client_id": "k"},
                     {"montage_parts": PARTS})
    assert job.status == Status.done, job.message
    assert len(reqs[0]["items"]) == 4 and reqs[0]["voices"]["Người dẫn"]["mode"] == "clone"


def test_home_voice_picker_for_every_voice_mode(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    v = _studio_voice(tmp_path, monkeypatch)
    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    c = TestClient(app)
    page = c.get("/").text
    assert 'data-modes="normal dub voice_only review cliff films char_dub anim wild sell ideas yt">\n' \
           '                <label style="margin-top:10px">🎙️ Giọng đọc</label>' in page
    for mode in ("review", "char_dub", "dub", "vi_sub"):
        res = c.post("/jobs", data={"footage": str(f), "mode": mode, "target_language": "ja", "sell_voice": v["slug"]},
                     follow_redirects=False)
        o = Job.load(tmp_path / "jobs", res.headers["location"].rsplit("/", 1)[1]).options
        assert o.sell_voice == ("" if mode == "vi_sub" else v["slug"]), mode
