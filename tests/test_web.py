import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.jobs.job import Job, Status
from app.web.server import create_app
from tests.test_director import make_analysis
from tests.test_runner import make_runner


def wait_idle(app, timeout=20):
    t = time.time()
    while app.state.worker.active and time.time() - t < timeout:
        time.sleep(0.05)
    time.sleep(0.05)


def test_web_full_flow(tmp_path):
    jobs = tmp_path / "jobs"
    footage = tmp_path / "test.mp4"
    footage.write_bytes(b"x")

    def factory(root, log):
        r = make_runner(tmp_path, root)
        r.log = log
        return r

    app = create_app(jobs, factory)
    client = TestClient(app)
    home = client.get("/").text
    assert "Tạo video mới" in home and "Chọn file" in home and "value='sports_analysis'" in home

    # file không tồn tại → báo lỗi
    assert "Không thấy file" in client.post("/jobs", data={"footage": str(tmp_path / "khong.mp4")}).text

    # tạo job; phân tích giả: chuẩn bị sẵn thư mục analysis trước khi luồng chạy
    job_dir_holder = {}
    orig_start = app.state.worker.start

    def start(job_id, action=None):
        if not (jobs / job_id / "analysis").exists():
            make_analysis(jobs / job_id, duration=60.0)
        job_dir_holder["id"] = job_id
        return orig_start(job_id, action)

    app.state.worker.start = start
    r = client.post("/jobs", data={"footage": str(footage), "client": "khachA", "hook": "on", "style": "podcast"},
                    follow_redirects=False)
    assert r.status_code == 303
    wait_idle(app)
    job_id = job_dir_holder["id"]
    page = client.get(f"/jobs/{job_id}").text
    assert "Chọn hook" in page and "name='choice_1'" in page

    client.post(f"/jobs/{job_id}/choose", data={"choice_1": "2"})
    wait_idle(app)
    page = client.get(f"/jobs/{job_id}").text
    assert "Thu voice hook" in page and "video01_hook.wav" in page

    assert "type='file' name='voice'" in page and "Thả file vào thư mục" not in page
    assert "🏠 Về trang chủ" in page
    # sai định dạng → báo lỗi, không lưu
    assert "không hợp lệ" in client.post(f"/jobs/{job_id}/voice", files={"voice": ("a.txt", b"x")}).text
    client.post(f"/jobs/{job_id}/voice", files={"voice": ("thu_am.mp3", b"ID3")})
    wait_idle(app)
    assert (jobs / job_id / "voice" / "video01_hook.mp3").read_bytes() == b"ID3"
    job = Job.load(jobs, job_id)
    assert job.status == Status.done, job.message
    page = client.get(f"/jobs/{job_id}").text
    assert "Caption + hashtag" in page and "Tài nguyên cần bổ sung" in page and "khachA" in page
    assert job_id in client.get("/").text
    assert job.data["style_used"] == "podcast"

    assert "🔁 Dựng lại draft" in page and "🎣 Chọn hook khác" in page and "🗑️ Xóa job" in page

    # dựng lại draft ngay trên giao diện
    client.post(f"/jobs/{job_id}/redo", data={"step": "write"})
    wait_idle(app)
    assert Job.load(jobs, job_id).status == Status.done
    assert any("làm lại từ bước write" in h.message for h in Job.load(jobs, job_id).history)

    # chọn hook khác → quay lại bảng chọn, voice cũ được cất đi
    client.post(f"/jobs/{job_id}/redo", data={"step": "choose_hook"})
    wait_idle(app)
    job = Job.load(jobs, job_id)
    assert job.step == "choose_hook" and job.status == Status.waiting
    assert not (jobs / job_id / "voice" / "video01_hook.mp3").exists()
    assert (jobs / job_id / "voice" / "video01_hook_cu.mp3").exists()

    # xóa job
    client.post(f"/jobs/{job_id}/delete")
    assert not (jobs / job_id).exists()
    assert job_id not in client.get("/").text


def test_web_resource_scan_settings_upload(tmp_path):
    from app.assets.scan import ScanReport

    calls = []

    def scan_fn(download, key):
        calls.append((download, key))
        return ScanReport(capcut={"sfx": 3}, local={"sfx": 1}, download_enabled=download,
                          needs=[{"kind": "sfx", "tag": "boom", "label": "SFX boom", "why": "job j1 đang thiếu",
                                  "have": 1, "status": "đã tải", "jobs": ["j1"]},
                                 {"kind": "sfx", "tag": "laugh", "label": "SFX laugh", "why": "x", "have": 0,
                                  "status": "còn thiếu", "jobs": []}],
                          downloaded=[{"file": "sfx/boom/fs7_a.mp3", "name": "Boom", "tag": "boom", "author": "u",
                                       "url": "https://freesound.org/s/7/"}], jobs_to_redo=["j1"])

    app = create_app(tmp_path / "jobs", assets_root=tmp_path / "assets", settings_path=tmp_path / "local.yaml",
                     scan_fn=scan_fn)
    client = TestClient(app)
    home = client.get("/").text
    assert "🔍 Quét tài nguyên" in home and "chưa có key" in home

    client.post("/settings/freesound", data={"key": " ABC "})
    assert "đã lưu key" in client.get("/").text
    page = client.post("/resources/scan", data={"download": "on"}).text
    assert calls[-1] == (True, "ABC")
    assert "Kết quả quét" in page and "SFX boom" in page and "đã tải" in page and "còn thiếu" in page
    assert "Dựng lại draft job j1" in page and "freesound.org/s/7" in page

    r = client.post("/assets/upload", data={"kind": "sfx", "tag": "laugh"},
                    files={"file": ("Cười To.MP3", b"ID3")})
    assert "Đã thêm vào kho" in r.text
    saved = list((tmp_path / "assets" / "sfx" / "laugh").glob("*.mp3"))
    assert len(saved) == 1
    import json
    led = json.loads((tmp_path / "assets" / "ledger.json").read_text(encoding="utf-8"))["items"]
    assert led[0]["source"] == "user" and led[0]["file"].startswith("sfx/laugh/")
    assert "không hợp lệ" in client.post("/assets/upload", data={"kind": "sfx"}, files={"file": ("a.exe", b"x")}).text
