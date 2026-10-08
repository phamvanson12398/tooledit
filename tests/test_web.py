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
    assert "🔍 Quét &amp; làm giàu kho" in home and "chưa có key" in home

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


def test_web_split_flow(tmp_path):
    from tests.test_runner import _split_director

    jobs = tmp_path / "jobs"
    footage = tmp_path / "long.mp4"
    footage.write_bytes(b"x")
    director = _split_director()

    def factory(root, log):
        r = make_runner(tmp_path, root)
        r._director = director
        r.log = log
        return r

    app = create_app(jobs, factory)
    orig = app.state.worker.start
    holder = {}

    def start(job_id, action=None):
        if not (jobs / job_id / "analysis").exists():
            make_analysis(jobs / job_id, duration=200.0)
        holder["id"] = job_id
        return orig(job_id, action)

    app.state.worker.start = start
    client = TestClient(app)
    assert "name=\"split\"" in client.get("/").text
    client.post("/jobs", data={"footage": str(footage), "hook": "on", "split": "on"})
    wait_idle(app)
    jid = holder["id"]
    page = client.get(f"/jobs/{jid}").text
    assert "Duyệt chia video" in page and "name='keep_v2'" in page and "name='keep_d1'" in page
    # giữ 2 video, sửa điểm cắt video 2; không tick đoạn bị bỏ
    client.post(f"/jobs/{jid}/segments", data={
        "keep_v1": "on", "start_v1": "1.0", "end_v1": "70.0", "title_v1": "A", "summary_v1": "a",
        "keep_v2": "on", "start_v2": "75.0", "end_v2": "148.0", "title_v2": "B", "summary_v2": "b",
        "start_d1": "150", "end_d1": "173"})
    wait_idle(app)
    page = client.get(f"/jobs/{jid}").text
    assert "name='choice_1'" in page and "name='choice_2'" in page
    client.post(f"/jobs/{jid}/choose", data={"choice_1": "1", "choice_2": "2"})
    wait_idle(app)
    page = client.get(f"/jobs/{jid}").text
    assert "Voice cho video01" in page and "Voice cho video02" in page
    client.post(f"/jobs/{jid}/voice", data={"video": "1"}, files={"voice": ("a.wav", b"RIFF")})
    wait_idle(app)
    assert Job.load(jobs, jid).step == "voice"  # còn thiếu video 2
    client.post(f"/jobs/{jid}/voice", data={"video": "2"}, files={"voice": ("b.m4a", b"x")})
    wait_idle(app)
    job = Job.load(jobs, jid)
    assert job.status == Status.done, job.message
    page = client.get(f"/jobs/{jid}").text
    assert "2 video" in page and "Video 02" in page and "✂️ Chia lại video" in page
    assert (jobs / jid / "voice" / "video02_hook.m4a").is_file()


def test_web_import_folder(tmp_path):
    src = tmp_path / "tai_ve" / "SFX" / "DamDong"
    src.mkdir(parents=True)
    (src / "crowd cheer.mp3").write_bytes(b"x")
    app = create_app(tmp_path / "jobs", assets_root=tmp_path / "assets", settings_path=tmp_path / "l.yaml",
                     scan_fn=lambda d, k: None)
    client = TestClient(app)
    home = client.get("/").text
    assert "Nhập cả thư mục" in home and "Incompetech" in home and "làm giàu kho" in home
    page = client.post("/assets/import-folder", data={"folder": str(tmp_path / "tai_ve"), "kind": "auto",
                                                       "source": "pixabay"}).text
    assert "Đã nhập 1 file" in page and "dam_dong" in page
    assert (tmp_path / "assets" / "sfx" / "dam_dong" / "crowd_cheer_pb.mp3").is_file()
    assert "Không nhập được" in client.post("/assets/import-folder", data={"folder": str(tmp_path / "khong_co")}).text


def test_web_import_capcut_zip(tmp_path):
    import io
    import zipfile

    from tests.test_planner import SAMPLE

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for f in SAMPLE.rglob("*"):
            if f.is_file():
                zf.write(f, Path("DuAnMau") / f.relative_to(SAMPLE))
    app = create_app(tmp_path / "jobs", assets_root=tmp_path / "assets", settings_path=tmp_path / "l.yaml",
                     scan_fn=lambda d, k: None)
    client = TestClient(app)
    assert "Lấy hiệu ứng / nhạc từ một dự án CapCut" in client.get("/").text
    page = client.post("/assets/import-capcut", data={"mood": "vui"},
                       files={"zipfile": ("duan.zip", buf.getvalue(), "application/zip")}).text
    assert "capcut_template" in page and "cần CapCut tải" in page and "chuyển cảnh" in page
    assert (tmp_path / "assets" / "capcut_library.json").is_file()
    assert "Chưa chọn dự án" in client.post("/assets/import-capcut", data={}).text


def test_web_parallel_setting(tmp_path):
    app = create_app(tmp_path / "jobs", settings_path=tmp_path / "l.yaml", scan_fn=lambda d, k: None)
    client = TestClient(app)
    assert "Đang chạy <b>0/3</b> luồng" in client.get("/").text
    client.post("/settings/parallel", data={"n": "5"})
    assert "Đang chạy <b>0/5</b> luồng" in client.get("/").text


def test_home_never_full_reloads_while_jobs_run(tmp_path):
    """Lỗi thật: trang chủ tải lại mỗi 3 giây khi có video chạy → mất file/lựa chọn đang nhập."""
    from pathlib import Path as P

    jobs = tmp_path / "jobs"
    Job.create(jobs, [P("C:/f/a.mp4")], job_id="r1")
    app = create_app(jobs, settings_path=tmp_path / "l.yaml", scan_fn=lambda d, k: None)
    app.state.worker.active.add("r1")  # giả như đang chạy
    client = TestClient(app)
    home = client.get("/").text
    assert 'http-equiv="refresh"' not in home and "/api/jobs-panel" in home
    panel = client.get("/api/jobs-panel").text
    assert "đang chạy" in panel and "r1" in panel and "1/3" in panel


def test_inline_scripts_have_no_syntax_errors(tmp_path):
    """Mọi đoạn <script> trên trang chủ phải chạy được (lỗi cú pháp làm nút 'Chọn file…' không bấm được)."""
    import re
    import shutil
    import subprocess

    import pytest
    from fastapi.testclient import TestClient

    from app.web.server import create_app

    node = shutil.which("node")
    if not node:
        pytest.skip("không có Node.js để kiểm tra cú pháp JavaScript")
    html_page = TestClient(create_app(tmp_path / "jobs", lambda root, log: None)).get("/").text
    scripts = re.findall(r"<script>(.*?)</script>", html_page, flags=re.S)
    assert scripts and any("function pick" in s for s in scripts)
    for i, js in enumerate(scripts):
        f = tmp_path / f"s{i}.js"
        f.write_text(js, encoding="utf-8")
        r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, f"script {i} lỗi cú pháp: {r.stderr[:300]}"


def test_pick_file_dialog_multiple(monkeypatch):
    """Nút Chọn file: chọn NHIỀU file một lúc (askopenfilenames); Tk cũ trả chuỗi cũng tách đúng."""
    import sys
    import types

    from app.web.server import pick_file_dialog

    class FakeTk:
        def __init__(self):
            self.tk = types.SimpleNamespace(splitlist=lambda raw: tuple(raw.split("|")) if isinstance(raw, str) else raw)

        def withdraw(self): pass

        def attributes(self, *a): pass

        def destroy(self): pass

    fd = types.SimpleNamespace(askopenfilenames=lambda **kw: ("C:/v/a.mp4", "C:/v/b.mp4"),
                               askopenfilename=lambda **kw: "C:/v/a.mp4")
    tk_mod = types.ModuleType("tkinter")
    tk_mod.Tk = FakeTk
    tk_mod.filedialog = fd
    monkeypatch.setitem(sys.modules, "tkinter", tk_mod)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", fd)
    r = pick_file_dialog(multiple=True)
    assert len(r["paths"]) == 2 and r["path"].endswith("a.mp4")
    fd.askopenfilenames = lambda **kw: "C:/v/a.mp4|C:/v/c.mp4"  # Tk cũ: chuỗi
    assert [p[-5:] for p in pick_file_dialog(multiple=True)["paths"]] == ["a.mp4", "c.mp4"]
    fd.askopenfilenames = lambda **kw: ""  # bấm Hủy
    assert pick_file_dialog(multiple=True) == {"path": "", "paths": []}
    assert pick_file_dialog()["paths"] == [pick_file_dialog()["path"]]  # nút chọn 1 file (so sánh video) vẫn như cũ
