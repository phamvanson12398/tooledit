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
:root{--bg:#f4f6fb;--card:#fff;--ink:#1d2433;--mute:#6b7385;--line:#e4e8f0;--pri:#5b5bf7;--pri2:#8b5cf6;
--ok:#16a34a;--warn:#f59e0b;--err:#dc2626;--run:#2563eb}
*{box-sizing:border-box}body{margin:0;font-family:"Segoe UI",system-ui,"Noto Sans JP",sans-serif;background:var(--bg);color:var(--ink)}
header{background:linear-gradient(120deg,var(--pri),var(--pri2));color:#fff;padding:18px 28px;display:flex;align-items:center;gap:14px}
header .logo{font-size:26px}header h1{font-size:20px;margin:0}header small{opacity:.85}
header a{color:#fff;text-decoration:none}
main{max-width:1180px;margin:24px auto;padding:0 20px}
.grid{display:grid;grid-template-columns:1.1fr .9fr;gap:22px}@media(max-width:900px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;box-shadow:0 2px 10px rgba(30,40,80,.05);margin-bottom:22px}
.card h2{margin:0 0 14px;font-size:17px}
.muted{color:var(--mute);font-size:13px}
.field{margin:12px 0}.field>label{display:block;font-weight:600;font-size:14px;margin-bottom:6px}
.row{display:flex;gap:8px}.row input{flex:1}
input[type=text],select{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:10px;font-size:14px;background:#fbfcff}
input[type=text]:focus{outline:2px solid #c7c9ff;border-color:var(--pri)}
.btn{display:inline-block;background:linear-gradient(120deg,var(--pri),var(--pri2));color:#fff;border:0;border-radius:10px;
padding:10px 20px;font-size:15px;font-weight:600;cursor:pointer;text-decoration:none}
.btn.light{background:#eef0ff;color:var(--pri)}.btn.big{padding:13px 28px;font-size:16px}
.styles{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}
.style{border:1.5px solid var(--line);border-radius:12px;padding:10px 12px;cursor:pointer;display:block;background:#fbfcff}
.style input{display:none}.style b{display:block;font-size:14px}.style span{font-size:12px;color:var(--mute)}
.style:has(input:checked){border-color:var(--pri);background:#f1f0ff;box-shadow:0 0 0 3px #e3e1ff}
.toggles{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.tg{display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--line);border-radius:10px;cursor:pointer;font-size:14px}
.tg input{appearance:none;width:38px;height:22px;background:#d6dae4;border-radius:11px;position:relative;transition:.2s;flex:none}
.tg input:before{content:"";position:absolute;width:18px;height:18px;border-radius:50%;background:#fff;top:2px;left:2px;transition:.2s}
.tg input:checked{background:var(--pri)}.tg input:checked:before{left:18px}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;color:#fff}
.b-pending,.b-running{background:var(--run)}.b-waiting{background:var(--warn)}.b-error{background:var(--err)}.b-done{background:var(--ok)}
.jobs a.job{display:flex;justify-content:space-between;align-items:center;padding:12px;border:1px solid var(--line);border-radius:12px;
margin:8px 0;text-decoration:none;color:var(--ink);background:#fbfcff}.jobs a.job:hover{border-color:var(--pri)}
.jobs .name{font-weight:600}.jobs .sub{font-size:12px;color:var(--mute)}
.stepper{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 18px}
.step{padding:6px 12px;border-radius:20px;font-size:12px;background:#eceff5;color:var(--mute)}
.step.done{background:#dcfce7;color:#166534}.step.cur{background:var(--pri);color:#fff}.step.cur.waiting{background:var(--warn)}
.step.cur.error{background:var(--err)}
pre{white-space:pre-wrap;background:#f8f9fc;border:1px solid var(--line);padding:12px;border-radius:10px;font-size:13px;margin:0}
.hook{border:1.5px solid var(--line);border-radius:12px;padding:12px 14px;margin:10px 0;cursor:pointer;display:block;background:#fbfcff}
.hook:has(input:checked){border-color:var(--pri);background:#f1f0ff}
.hook .line{font-size:17px;font-weight:600;margin:4px 0}.tag{background:#eef0ff;color:var(--pri);padding:2px 8px;border-radius:8px;font-size:12px}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid var(--line);padding:8px;text-align:left}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid #c7c9ff;border-top-color:var(--pri);border-radius:50%;animation:sp 1s linear infinite;vertical-align:-2px}
@keyframes sp{to{transform:rotate(360deg)}}
.lib{display:flex;gap:10px;flex-wrap:wrap}.lib div{background:#f1f0ff;border-radius:10px;padding:8px 12px;font-size:13px}
.lib b{font-size:18px;color:var(--pri);display:block}
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
    return HTMLResponse(
        f"<!doctype html><html lang='vi'><head><meta charset='utf-8'>{meta}"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title>"
        f"<style>{CSS}</style></head><body><header><span class='logo'>🎬</span><div><h1><a href='/'>Tool dựng video TikTok"
        f"</a></h1><small>CapCut 9.5.0 · đạo diễn AI chạy trên máy</small></div></header><main>{body}</main></body></html>")


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
        from app.styles import available_styles

        jobs_html = "".join(
            f"<a class='job' href='/jobs/{j.job_id}'><div><div class='name'>{html.escape(Path(j.footage[0]).name)}</div>"
            f"<div class='sub'>{j.job_id} · {STEP_VI.get(j.step, j.step)}</div></div>"
            f"<span class='badge b-{j.status.value}'>{STATUS_VI[j.status.value]}</span></a>" for j in list_jobs())
        style_cards = ["<label class='style'><input type='radio' name='style' value='auto' checked>"
                       "<b>✨ AI tự chọn</b><span>Đạo diễn xem nội dung rồi chọn kiểu phù hợp</span></label>"]
        for key, st in available_styles().items():
            style_cards.append(f"<label class='style'><input type='radio' name='style' value='{key}'>"
                               f"<b>{html.escape(st['name_vi'] or key)}</b><span>{html.escape(st['fits_vi'])}</span></label>")
        body = f"""
        <div class="grid"><div>
        <div class="card"><h2>🎞️ Tạo video mới</h2>
        <form method="post" action="/jobs">
          <div class="field"><label>File footage</label>
            <div class="row"><input type="text" id="footage" name="footage" placeholder="Bấm Chọn file… hoặc dán đường dẫn" required>
            <button type="button" class="btn light" onclick="pick()">📂 Chọn file…</button></div>
            <div class="muted" id="pickmsg"></div></div>
          <div class="field"><label>Kiểu dựng</label><div class="styles">{''.join(style_cards)}</div></div>
          <div class="field"><label>Tùy chọn</label><div class="toggles">
            <label class="tg"><input type="checkbox" name="hook" checked> Có hook voice</label>
            <label class="tg"><input type="checkbox" name="reframe"> Đổi khung theo cảnh</label>
            <label class="tg"><input type="checkbox" name="business"> Khách doanh nghiệp (nhạc Commercial)</label>
            <label class="tg"><input type="checkbox" name="confirm"> Xác nhận trước khi dựng</label></div></div>
          <div class="field" style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div><label>Mã khách</label><input type="text" name="client" value="khach"></div>
            <div><label>Khung cho footage ngang</label><select name="ratio"><option value="4:3">4:3</option>
              <option value="1:1">1:1 (vuông)</option></select></div></div>
          <p><button type="submit" class="btn big">🚀 Bắt đầu dựng</button></p>
        </form></div></div>
        <div><div class="card"><h2>📚 Kho tài nguyên</h2>{_library_summary()}</div>
        <div class="card jobs"><h2>🗂️ Các video</h2>{jobs_html or "<p class='muted'>Chưa có video nào.</p>"}</div></div></div>
        <script>
        async function pick(){{
          const m=document.getElementById('pickmsg'); m.textContent='Đang mở hộp thoại chọn file…';
          try{{const r=await fetch('/api/pick-file');const d=await r.json();
            if(d.path){{document.getElementById('footage').value=d.path;m.textContent='';}}
            else m.textContent=d.error||'Chưa chọn file.';}}catch(e){{m.textContent='Không mở được hộp thoại: '+e;}}
        }}
        </script>"""
        return _page("Tool dựng video", body, refresh=worker.active is not None)

    @app.get("/api/pick-file")
    def pick_file():
        return pick_file_dialog()

    @app.post("/jobs")
    def new_job(footage: str = Form(...), client: str = Form("khach"), hook: str | None = Form(None),
                reframe: str | None = Form(None), business: str | None = Form(None),
                confirm: str | None = Form(None), ratio: str = Form("4:3"), style: str = Form("auto")):
        path = Path(footage.strip().strip('"'))
        if not path.is_file():
            return _page("Lỗi", f"<div class='card'><h2>Không thấy file</h2><p>{html.escape(str(path))}</p>"
                         "<p><a class='btn light' href='/'>Quay lại</a></p></div>")
        job = Job.create(Path(jobs_root), [path.resolve()], JobOptions(
            client_id=client.strip() or "khach", hook=bool(hook), reframe_per_scene=bool(reframe),
            confirm_before_build=bool(confirm)))
        job.data.update({"business": bool(business), "default_ratio": ratio, "style": style})
        job.save(Path(jobs_root))
        worker.start(job.job_id)
        return RedirectResponse(f"/jobs/{job.job_id}", status_code=303)

    @app.get("/jobs/{job_id}", response_class=HTMLResponse)
    def job_page(job_id: str):
        from app.jobs.job import STEPS

        job = Job.load(Path(jobs_root), job_id)
        d = job.dir(Path(jobs_root))
        running = worker.active == job_id
        status = "running" if running else job.status.value
        cur = STEPS.index(job.step)
        chips = []
        for i, st in enumerate(STEPS):
            if not job.applies(st) or st == "assets":
                continue
            cls = "done" if i < cur or job.status == Status.done else ("cur " + status if i == cur else "")
            chips.append(f"<span class='step {cls}'>{STEP_VI.get(st, st)}</span>")
        style = job.data.get("style_used") or job.data.get("style") or "auto"
        head = (f"<div class='card'><div style='display:flex;justify-content:space-between;align-items:center'>"
                f"<div><h2 style='margin:0'>{html.escape(Path(job.footage[0]).name)}</h2>"
                f"<div class='muted'>{job.job_id} · kiểu dựng: {html.escape(style)} · {html.escape(job.footage[0])}</div></div>"
                f"<span class='badge b-{status}'>{'<span class=spinner></span> ' if running else ''}{STATUS_VI[status]}</span>"
                f"</div><div class='stepper' style='margin-top:14px'>{''.join(chips)}</div>")
        if job.data.get("summary_vi"):
            head += f"<p><b>Nội dung:</b> {html.escape(job.data['summary_vi'])}</p>"
        parts = [head + "</div>"]
        if running:
            parts.append(f"<div class='card'><span class='spinner'></span> Đang <b>{STEP_VI.get(job.step, job.step)}</b>… "
                         "trang tự làm mới.</div>")
        else:
            parts.append(_step_panel(job, d))
        log = _read(d / "log.txt")
        if log:
            parts.append(f"<div class='card'><h2>📝 Nhật ký</h2><pre>{html.escape(log[-4000:])}</pre></div>")
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
    return (f"<form method='post' action='/jobs/{job.job_id}/continue' style='margin-top:12px'>"
            f"<button type='submit' class='btn'>{label}</button></form>")


def _library_summary() -> str:
    """Số nhạc / SFX / hiệu ứng đạo diễn có thể dùng (dự án mẫu + bộ sưu tập)."""
    try:
        from app.jobs.runner import Runner

        tpl = Runner(JOBS_ROOT, log=lambda m: None)._template()
    except Exception as exc:
        return f"<p class='muted'>Chưa đọc được dự án mẫu CapCut: {html.escape(str(exc))}</p>"
    count = lambda k: sum(1 for i in tpl.library if i.kind == k)  # noqa: E731
    boxes = "".join(f"<div><b>{count(k)}</b>{label}</div>" for k, label in
                    (("music", "nhạc nền"), ("sfx", "SFX"), ("video_effect", "hiệu ứng"), ("transition", "chuyển cảnh"),
                     ("sticker", "sticker")))
    return (f"<div class='lib'>{boxes}</div><p class='muted'>Muốn đạo diễn có nhiều nhạc/SFX để chọn: tạo dự án CapCut "
            "tên <b>bo_suu_tap_nhac</b>, thêm các bài nhạc và hiệu ứng âm thanh hay dùng, lưu lại. Gắn tâm trạng cho "
            "từng bài trong config/capcut_labels.yaml.</p>")


def pick_file_dialog() -> dict:
    """Mở hộp thoại chọn file của Windows ngay trên máy chạy tool (server và trình duyệt cùng một máy)."""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return {"error": "Máy không có tkinter, hãy dán đường dẫn file."}
    try:
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Chọn file footage", filetypes=[("Video", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v"), ("Tất cả", "*.*")])
        root.destroy()
    except Exception as exc:
        return {"error": f"Không mở được hộp thoại chọn file: {exc}"}
    return {"path": str(Path(path)) if path else ""}


def _step_panel(job: Job, d: Path) -> str:
    esc = html.escape
    if job.status == Status.error:
        return (f"<div class='card'><h2>⚠️ Có lỗi</h2><pre>{esc(job.message)}</pre>"
                f"{_continue_button(job, 'Chạy lại bước này')}</div>")
    if job.status == Status.waiting and job.step == "choose_hook":
        from app.director.schemas import HOOK_TYPES_VI
        from app.planner import hook_io

        sets, _ = hook_io.load_hooks(d)
        items = []
        for s in sets:
            for i, o in enumerate(s.options, 1):
                items.append(
                    f"<label class='hook'><input type='radio' name='choice_{s.video_index}' value='{i}' "
                    f"{'checked' if i == 1 else ''}> <span class='tag'>Phương án {i} · {esc(HOOK_TYPES_VI[o.hook_type])}"
                    f"</span><div class='line'>{esc(o.line)}</div><div>🇻🇳 {esc(o.line_vi)}</div>"
                    f"<div class='muted'>Chữ trên màn: <b>{esc(o.onscreen_text)}</b> · Footage "
                    f"{o.footage.start:.1f}–{o.footage.end:.1f}s · Nguồn {o.source.start:.1f}–{o.source.end:.1f}s</div>"
                    f"<div class='muted'>Vì sao: {esc(o.why_vi)}</div></label>")
            items.append(f"<p><i>Ghi chú editor: {esc(s.editor_notes)}</i></p>")
        return (f"<div class='card'><h2>🎣 Chọn hook</h2><form method='post' action='/jobs/{job.job_id}/choose'>"
                f"{''.join(items)}<button type='submit' class='btn'>Chọn hook này</button></form></div>")
    if job.status == Status.waiting and job.step == "voice":
        return (f"<div class='card'><h2>🎙️ Thu voice hook</h2><pre>{esc(_read(d / 'hook_scripts.txt'))}</pre>"
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
        parts = [f"<div class='card'><h2>✅ Xong</h2><p>Draft CapCut: <b>{esc(job.data.get('draft', ''))}</b> "
                 f"({job.data.get('duration_s', '?')} giây). Mở CapCut để xem, chỉnh và xuất.</p>"]
        plan = d / "plan" / "edit_plan_video01.json"
        if plan.is_file():
            parts.append(f"<p><b>Ghi chú editor:</b> {esc(json.loads(_read(plan)).get('editor_notes', ''))}</p>")
        cap = _read(d / "deliver" / "video01_captions.txt")
        if cap:
            parts.append(f"<h2 style='margin-top:18px'>📣 Caption + hashtag</h2><pre>{esc(cap)}</pre>")
        missing = json.loads(_read(d / "missing_assets.json") or "[]")
        if missing:
            rows = "".join(f"<tr><td>{esc(m['kind'])}</td><td>{esc(str(m['what']))}</td><td>{m['at_s']}s</td>"
                           f"<td>{esc(m.get('purpose_vi', ''))}</td></tr>" for m in missing)
            parts.append("<h2 style='margin-top:18px'>🧩 Tài nguyên cần bổ sung</h2><table><tr><th>Loại</th><th>Cần gì</th><th>Giây</th>"
                         f"<th>Để làm gì</th></tr>{rows}</table>")
        parts.append("</div>")
        return "".join(parts)
    return f"<div class='card'>{_continue_button(job, 'Chạy')}</div>"


app = create_app()
