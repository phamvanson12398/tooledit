"""Giao diện web chạy trên máy (FastAPI + HTML đơn giản, không cần build frontend). Mục 9 CLAUDE.md.

Mở: start.bat → trình duyệt http://127.0.0.1:8765
Job chạy trong một luồng nền (mỗi lúc một job, vì GPU và hạn mức Claude Pro có hạn); trang tự làm mới.
"""

from __future__ import annotations

import html
import json
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import ROOT
from app.jobs.job import Job, JobOptions, Status

JOBS_ROOT = ROOT / "jobs"

CSS = """
body{font-family:system-ui,Segoe UI,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;color:#222}
h1{font-size:22px} h2{font-size:18px;margin-top:28px} a{color:#1565c0}
.card{border:1px solid #ddd;border-radius:10px;padding:16px;margin:12px 0;background:#fafafa}
.st{display:inline-block;padding:2px 10px;border-radius:12px;color:#fff;font-size:13px}
.pending,.running{background:#1976d2}.waiting{background:#f57c00}.error{background:#c62828}.done{background:#2e7d32}
pre{white-space:pre-wrap;background:#fff;border:1px solid #eee;padding:10px;border-radius:6px;font-size:13px}
button{background:#1565c0;color:#fff;border:0;border-radius:6px;padding:8px 16px;font-size:15px;cursor:pointer}
input[type=text]{width:100%;padding:8px;font-size:15px;box-sizing:border-box}
label{display:block;margin:6px 0} table{border-collapse:collapse;width:100%} td,th{border:1px solid #ddd;padding:6px}
.hook{border:1px solid #ccc;border-radius:8px;padding:10px;margin:8px 0;background:#fff}
"""

STEP_VI = {
    "analyze": "Phân tích footage", "understand": "AI hiểu nội dung", "confirm_genre": "Chờ xác nhận nội dung",
    "hooks": "AI viết hook", "choose_hook": "Chờ chọn hook", "voice": "Chờ file voice",
    "plan": "AI lập kế hoạch dựng", "assets": "Tìm tài nguyên", "write": "Ghi dự án CapCut",
    "captions": "AI viết caption", "done": "Xong",
}
STATUS_VI = {"pending": "chờ chạy", "running": "đang chạy", "waiting": "chờ bạn", "error": "lỗi", "done": "xong"}


class Worker:
    """Chạy job trong luồng nền, lần lượt từng job."""

    def __init__(self, jobs_root: Path, runner_factory):
        self.jobs_root = jobs_root
        self.runner_factory = runner_factory
        self.lock = threading.Lock()
        self.active: str | None = None

    def start(self, job_id: str, action=None) -> bool:
        if not self.lock.acquire(blocking=False):
            return False
        self.active = job_id

        def work():
            try:
                log_path = Job.dir_for(self.jobs_root, job_id) / "log.txt"

                def log(msg: str) -> None:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

                runner = self.runner_factory(self.jobs_root, log)
                job = Job.load(self.jobs_root, job_id)
                if action:
                    action(runner, job)
                if job.status == Status.pending:
                    runner.run(job)
                else:
                    runner.resume(job)
            except Exception as exc:  # lỗi ngoài dự kiến: ghi vào job để hiện trên giao diện
                try:
                    job = Job.load(self.jobs_root, job_id)
                    job.fail(f"Lỗi: {exc}")
                    job.save(self.jobs_root)
                except Exception:
                    pass
            finally:
                self.active = None
                self.lock.release()

        threading.Thread(target=work, daemon=True).start()
        return True


def _page(title: str, body: str, refresh: bool = False) -> HTMLResponse:
    meta = '<meta http-equiv="refresh" content="3">' if refresh else ""
    return HTMLResponse(f"<!doctype html><html lang='vi'><head><meta charset='utf-8'>{meta}<title>{html.escape(title)}"
                        f"</title><style>{CSS}</style></head><body>{body}</body></html>")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def create_app(jobs_root: Path = JOBS_ROOT, runner_factory=None) -> FastAPI:
    if runner_factory is None:
        from app.jobs.runner import Runner

        runner_factory = lambda root, log: Runner(root, log=log)  # noqa: E731
    app = FastAPI(title="Tool dựng video TikTok")
    worker = Worker(Path(jobs_root), runner_factory)
    app.state.worker = worker

    def list_jobs() -> list[Job]:
        root = Path(jobs_root)
        if not root.is_dir():
            return []
        jobs = []
        for d in sorted(root.iterdir(), reverse=True):
            if (d / "job.json").is_file():
                try:
                    jobs.append(Job.load(root, d.name))
                except Exception:
                    continue
        return jobs

    @app.get("/", response_class=HTMLResponse)
    def index():
        rows = "".join(
            f"<tr><td><a href='/jobs/{j.job_id}'>{j.job_id}</a></td><td>{html.escape(Path(j.footage[0]).name)}</td>"
            f"<td>{STEP_VI.get(j.step, j.step)}</td><td><span class='st {j.status.value}'>"
            f"{STATUS_VI[j.status.value]}</span></td></tr>" for j in list_jobs())
        body = f"""
        <h1>Tool dựng video TikTok (CapCut 9.5.0)</h1>
        <div class="card"><h2>Job mới</h2>
        <form method="post" action="/jobs">
          <label>Đường dẫn file footage trên máy (ví dụ C:\\Users\\...\\video.mp4)
            <input type="text" name="footage" required></label>
          <label>Mã khách (dùng trong tên draft) <input type="text" name="client" value="khach"></label>
          <label><input type="checkbox" name="hook" checked> Có hook</label>
          <label><input type="checkbox" name="reframe"> Đổi khung theo cảnh</label>
          <label><input type="checkbox" name="business"> Khách doanh nghiệp (chỉ nhạc Commercial)</label>
          <label><input type="checkbox" name="confirm"> Xác nhận trước khi dựng</label>
          <label>Khung mặc định cho footage ngang
            <select name="ratio"><option>4:3</option><option>1:1</option></select></label>
          <p><button type="submit">Bắt đầu</button></p>
        </form>
        <p style="color:#666;font-size:13px">Chia video dài, tự tải tài nguyên, đủ 6 phong cách: Giai đoạn 2.
        Giai đoạn 1 dựng một video, phong cách tiktok_retention.</p></div>
        <h2>Các job</h2>
        <table><tr><th>Job</th><th>Footage</th><th>Bước</th><th>Trạng thái</th></tr>{rows or
        "<tr><td colspan=4>Chưa có job</td></tr>"}</table>"""
        return _page("Tool dựng video", body, refresh=worker.active is not None)

    @app.post("/jobs")
    def new_job(footage: str = Form(...), client: str = Form("khach"), hook: str | None = Form(None),
                reframe: str | None = Form(None), business: str | None = Form(None),
                confirm: str | None = Form(None), ratio: str = Form("4:3")):
        path = Path(footage.strip().strip('"'))
        if not path.is_file():
            return _page("Lỗi", f"<h1>Không thấy file</h1><p>{html.escape(str(path))}</p><p><a href='/'>Quay lại</a></p>")
        job = Job.create(Path(jobs_root), [path.resolve()], JobOptions(
            client_id=client.strip() or "khach", hook=bool(hook), reframe_per_scene=bool(reframe),
            confirm_before_build=bool(confirm)))
        job.data.update({"business": bool(business), "default_ratio": ratio})
        job.save(Path(jobs_root))
        worker.start(job.job_id)
        return RedirectResponse(f"/jobs/{job.job_id}", status_code=303)

    @app.get("/jobs/{job_id}", response_class=HTMLResponse)
    def job_page(job_id: str):
        job = Job.load(Path(jobs_root), job_id)
        d = job.dir(Path(jobs_root))
        running = worker.active == job_id
        status = "running" if running else job.status.value
        parts = [f"<p><a href='/'>← Danh sách job</a></p><h1>Job {job.job_id}</h1>",
                 f"<p>Footage: {html.escape(job.footage[0])}</p>",
                 f"<p>Bước: <b>{STEP_VI.get(job.step, job.step)}</b> <span class='st {status}'>"
                 f"{STATUS_VI[status]}</span></p>"]
        if job.data.get("summary_vi"):
            parts.append(f"<div class='card'><b>Nội dung:</b> {html.escape(job.data['summary_vi'])}</div>")
        if not running:
            parts.append(_step_panel(job, d))
        log = _read(d / "log.txt")
        if log:
            parts.append(f"<h2>Nhật ký</h2><pre>{html.escape(log[-4000:])}</pre>")
        return _page(f"Job {job_id}", "".join(parts), refresh=running)

    @app.post("/jobs/{job_id}/continue")
    def cont(job_id: str):
        worker.start(job_id)
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/choose")
    async def choose(job_id: str, request_form: str = Form(..., alias="choice_1")):
        choice = int(request_form)
        worker.start(job_id, action=lambda runner, job: runner.choose_hooks(job, {1: choice}))
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    return app


def _continue_button(job: Job, label: str = "Tiếp tục") -> str:
    return (f"<form method='post' action='/jobs/{job.job_id}/continue'><button type='submit'>{label}</button>"
            "</form>")


def _step_panel(job: Job, d: Path) -> str:
    esc = html.escape
    if job.status == Status.error:
        return (f"<div class='card'><b>Lỗi:</b><pre>{esc(job.message)}</pre>"
                f"{_continue_button(job, 'Chạy lại bước này')}</div>")
    if job.status == Status.waiting and job.step == "choose_hook":
        from app.director.schemas import HOOK_TYPES_VI
        from app.planner import hook_io

        sets, _ = hook_io.load_hooks(d)
        items = []
        for s in sets:
            for i, o in enumerate(s.options, 1):
                items.append(
                    f"<div class='hook'><label><input type='radio' name='choice_{s.video_index}' value='{i}' "
                    f"{'checked' if i == 1 else ''}> <b>[{i}] {esc(HOOK_TYPES_VI[o.hook_type])}</b>: "
                    f"{esc(o.line)}</label><div>Dịch: {esc(o.line_vi)}</div>"
                    f"<div>Chữ trên màn: {esc(o.onscreen_text)} · Footage {o.footage.start:.1f}–{o.footage.end:.1f}s"
                    f" · Nguồn {o.source.start:.1f}–{o.source.end:.1f}s</div>"
                    f"<div style='color:#555'>Vì sao: {esc(o.why_vi)}</div></div>")
            items.append(f"<p><i>Ghi chú editor: {esc(s.editor_notes)}</i></p>")
        return (f"<div class='card'><h2>Chọn hook</h2><form method='post' action='/jobs/{job.job_id}/choose'>"
                f"{''.join(items)}<button type='submit'>Chọn hook này</button></form></div>")
    if job.status == Status.waiting and job.step == "voice":
        return (f"<div class='card'><h2>Thu voice hook</h2><pre>{esc(_read(d / 'hook_scripts.txt'))}</pre>"
                f"<p>Thả file vào thư mục: <b>{esc(str(d / 'voice'))}</b></p>"
                f"<pre>{esc(job.message)}</pre>{_continue_button(job, 'Đã thả file, tiếp tục')}</div>")
    if job.status == Status.waiting:
        extra = ""
        u = d / "plan" / "understanding.json"
        if job.step == "confirm_genre" and u.is_file():
            data = json.loads(_read(u))
            extra = (f"<p>Phong cách đề xuất: {esc(data.get('suggested_style', ''))}</p>"
                     f"<p>Ghi chú editor: {esc(data.get('editor_notes', ''))}</p>")
        return f"<div class='card'><pre>{esc(job.message)}</pre>{extra}{_continue_button(job)}</div>"
    if job.status == Status.done:
        parts = [f"<div class='card'><h2>Xong</h2><p>Draft CapCut: <b>{esc(job.data.get('draft', ''))}</b> "
                 f"({job.data.get('duration_s', '?')} giây). Mở CapCut để xem, chỉnh và xuất.</p>"]
        plan = d / "plan" / "edit_plan_video01.json"
        if plan.is_file():
            parts.append(f"<p><b>Ghi chú editor:</b> {esc(json.loads(_read(plan)).get('editor_notes', ''))}</p>")
        cap = _read(d / "deliver" / "video01_captions.txt")
        if cap:
            parts.append(f"<h2>Caption + hashtag</h2><pre>{esc(cap)}</pre>")
        missing = json.loads(_read(d / "missing_assets.json") or "[]")
        if missing:
            rows = "".join(f"<tr><td>{esc(m['kind'])}</td><td>{esc(str(m['what']))}</td><td>{m['at_s']}s</td>"
                           f"<td>{esc(m.get('purpose_vi', ''))}</td></tr>" for m in missing)
            parts.append("<h2>Tài nguyên cần bổ sung</h2><table><tr><th>Loại</th><th>Cần gì</th><th>Giây</th>"
                         f"<th>Để làm gì</th></tr>{rows}</table>")
        parts.append("</div>")
        return "".join(parts)
    return _continue_button(job, "Chạy")


app = create_app()
