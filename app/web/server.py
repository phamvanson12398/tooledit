"""Giao diện web chạy trên máy (FastAPI + HTML đơn giản, không cần build frontend). Mục 9 CLAUDE.md.

Mở: start.bat → trình duyệt http://127.0.0.1:8765
Job chạy trong một luồng nền (mỗi lúc một job, vì GPU và hạn mức Claude Pro có hạn); trang tự làm mới.
"""

from __future__ import annotations

import html
import json
import shutil
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app import config as app_config
from app.config import ROOT
from app.jobs.job import STEPS, Job, JobOptions, Status

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
input[type=number]{padding:7px 8px;border:1px solid var(--line);border-radius:8px;font-size:14px}
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
.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.actions form{margin:0}
.btn.danger{background:#fee2e2;color:var(--err)}.btn.small{padding:7px 14px;font-size:13px}
.topnav{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
.upload{border:2px dashed #c7c9ff;border-radius:12px;padding:16px;background:#f7f7ff;margin-top:12px}
.upload input[type=file]{font-size:14px;margin:6px 0 10px}
.note{background:#fff7e6;border:1px solid #fde3a7;border-radius:10px;padding:10px 12px;font-size:13px;margin-top:10px}
"""

STEP_VI = {
    "analyze": "Phân tích footage", "understand": "AI hiểu nội dung", "confirm_genre": "Chờ xác nhận nội dung",
    "segment": "AI chia video", "review_segments": "Chờ duyệt chia video",
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


def create_app(jobs_root: Path = JOBS_ROOT, runner_factory=None, *, assets_root: Path | None = None,
               settings_path: Path | None = None, scan_fn=None) -> FastAPI:
    from app import settings as app_settings
    from app.assets import ledger

    assets_root = Path(assets_root or ledger.ASSETS_ROOT)
    settings_path = Path(settings_path or app_settings.LOCAL)
    if scan_fn is None:
        def scan_fn(download: bool, api_key: str):
            from app.assets.scan import scan_resources
            from app.jobs.runner import drafts_root

            return scan_resources(drafts_root(), Path(jobs_root), assets_root, download=download, api_key=api_key)
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

        has_key = bool(app_settings.load(settings_path).get("freesound_api_key"))
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
            <label class="tg"><input type="checkbox" name="confirm"> Xác nhận trước khi dựng</label>
            <label class="tg"><input type="checkbox" name="split"> Chia video dài thành nhiều video</label></div></div>
          <div class="field" style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div><label>Mã khách</label><input type="text" name="client" value="khach"></div>
            <div><label>Khung cho footage ngang</label><select name="ratio"><option value="4:3">4:3</option>
              <option value="1:1">1:1 (vuông)</option></select></div></div>
          <p><button type="submit" class="btn big">🚀 Bắt đầu dựng</button></p>
        </form></div></div>
        <div><div class="card"><h2>📚 Kho tài nguyên</h2>{_library_summary()}{_resource_tools(has_key)}{_template_setting()}</div>
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

    @app.get("/api/pick-folder")
    def pick_folder():
        return pick_folder_dialog()

    @app.post("/assets/import-capcut", response_class=HTMLResponse)
    async def import_capcut(draft: str = Form(""), folder: str = Form(""), mood: str = Form(""),
                            copy_to_capcut: str | None = Form(None), zipfile: UploadFile | None = File(None)):
        from app.assets.capcut_import import find_draft_dir, import_project, safe_extract

        esc = html.escape
        try:
            from_capcut = False
            if zipfile is not None and zipfile.filename:
                work = assets_root / ".imports" / time.strftime("%Y%m%d_%H%M%S")
                work.mkdir(parents=True, exist_ok=True)
                zpath = work / "project.zip"
                with open(zpath, "wb") as f:
                    shutil.copyfileobj(zipfile.file, f)
                src = find_draft_dir(safe_extract(zpath, work / "x"))
            elif folder.strip():
                src = find_draft_dir(Path(folder.strip().strip('"')))
            elif draft.strip():
                src, from_capcut = Path(draft), True
            else:
                raise ValueError("Chưa chọn dự án: chọn trong danh sách, tải lên .zip hoặc chọn thư mục.")
            if src is None:
                raise ValueError("Không tìm thấy dự án CapCut (thiếu draft_content.json) trong file / thư mục đã chọn.")
            copy_to = None
            if copy_to_capcut and not from_capcut:
                from app.jobs.runner import drafts_root

                try:
                    copy_to = drafts_root()
                except Exception:
                    copy_to = None
            res = import_project(src, assets_root, mood=mood.strip(), copy_to=copy_to)
        except Exception as exc:
            return _page("Lỗi", f"<div class='card'><h2>Không lấy được tài nguyên</h2><pre>{esc(str(exc))}</pre>"
                         "<p><a class='btn light' href='/'>🏠 Về trang chủ</a></p></div>")
        rows = "".join(f"<tr><td>{esc(r['kind_vi'])}</td><td>{esc(r['name'])}</td>"
                       f"<td>{'✅ dùng được ngay' if r['cached'] else '⏳ cần CapCut tải'}</td>"
                       f"<td>{'mới' if r['new'] else 'đã có'}</td></tr>" for r in res["items"])
        tip = ""
        if res["need_download"]:
            where = (f"Dự án đã được chép vào CapCut ({esc(res['copied_to'])}). " if res["copied_to"] else "")
            tip = (f"<div class='note'>{where}{res['need_download']} tài nguyên CapCut chưa tải về máy này: mở dự án "
                   f"<b>{esc(res['project'])}</b> trong CapCut 1 lần (chờ tải xong), đóng lại — lần dựng sau tool tự dùng được.</div>")
        audio = (f"<p>Đã chép {len(res['local_audio'])} file âm thanh riêng của bạn trong dự án vào kho: "
                 f"{esc(', '.join(res['local_audio']))}</p>" if res["local_audio"] else "")
        body = (f"<div class='topnav'><a class='btn light small' href='/'>🏠 Về trang chủ</a></div>"
                f"<div class='card'><h2>📦 Dự án “{esc(res['project'])}”: {len(res['items'])} tài nguyên "
                f"({res['added']} mới, {res['ready']} dùng được ngay)</h2>{tip}{audio}"
                f"<table><tr><th>Loại</th><th>Tên</th><th>Trạng thái</th><th></th></tr>{rows}</table></div>")
        return _page("Lấy tài nguyên từ dự án", body)

    @app.post("/assets/import-folder", response_class=HTMLResponse)
    def import_folder_page(folder: str = Form(...), kind: str = Form("auto"), source: str = Form("other"),
                           license: str = Form(""), author: str = Form("")):
        from app.assets.importer import import_folder

        try:
            res = import_folder(Path(folder.strip().strip('"')), assets_root, kind=kind, source=source,
                                license=license, author=author)
        except Exception as exc:
            return _page("Lỗi", f"<div class='card'><h2>Không nhập được</h2><pre>{html.escape(str(exc))}</pre>"
                         "<p><a class='btn light' href='/'>🏠 Về trang chủ</a></p></div>")
        esc = html.escape
        rows = "".join(f"<tr><td>{esc(e.get('original_name', ''))}</td><td>{esc(e.get('kind', ''))}</td>"
                       f"<td>{esc(e.get('tag', ''))}</td></tr>" for e in res["imported"])
        note = ("<div class='note'>Nguồn này <b>bắt buộc ghi tác giả</b>: video nào dùng các file này, tool tự thêm dòng "
                "ghi nguồn vào cuối caption.</div>" if res["credit_required"] else "")
        body = (f"<div class='topnav'><a class='btn light small' href='/'>🏠 Về trang chủ</a></div>"
                f"<div class='card'><h2>📁 Đã nhập {len(res['imported'])} file</h2>{note}"
                f"<table><tr><th>File</th><th>Loại</th><th>Nhóm</th></tr>{rows}</table>"
                f"<p class='muted'>Bỏ qua {len(res['skipped'])} file (đã có trong kho). Nhóm 'khac' = không đoán được từ "
                "tên thư mục; đạo diễn vẫn dùng được theo tên file.</p></div>")
        return _page("Nhập thư mục", body)

    @app.post("/jobs")
    def new_job(footage: str = Form(...), client: str = Form("khach"), hook: str | None = Form(None),
                reframe: str | None = Form(None), business: str | None = Form(None),
                confirm: str | None = Form(None), ratio: str = Form("4:3"), style: str = Form("auto"),
                split: str | None = Form(None)):
        path = Path(footage.strip().strip('"'))
        if not path.is_file():
            return _page("Lỗi", f"<div class='card'><h2>Không thấy file</h2><p>{html.escape(str(path))}</p>"
                         "<p><a class='btn light' href='/'>Quay lại</a></p></div>")
        job = Job.create(Path(jobs_root), [path.resolve()], JobOptions(
            client_id=client.strip() or "khach", hook=bool(hook), reframe_per_scene=bool(reframe),
            confirm_before_build=bool(confirm), split=bool(split)))
        job.data.update({"business": bool(business), "default_ratio": ratio, "style": style})
        job.save(Path(jobs_root))
        worker.start(job.job_id)
        return RedirectResponse(f"/jobs/{job.job_id}", status_code=303)

    @app.get("/jobs/{job_id}", response_class=HTMLResponse)
    def job_page(job_id: str):
        try:
            job = Job.load(Path(jobs_root), job_id)
        except (OSError, ValueError):  # file đang được ghi dở → tải lại sau giây lát
            return _page(f"Job {job_id}", "<div class='card'><span class='spinner'></span> Đang cập nhật trạng thái…"
                         "</div>", refresh=True)
        d = job.dir(Path(jobs_root))
        running = worker.active == job_id
        status = "running" if running else job.status.value
        cur = STEPS.index(job.step)
        chips = []
        for i, st in enumerate(STEPS):
            if not job.applies(st) or st == "assets" or (st == "segment" and not job.options.split):
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
        parts = ["<div class='topnav'><a class='btn light small' href='/'>🏠 Về trang chủ</a>"
                 f"<span class='muted'>{'Đang chạy — có thể về trang chủ, job vẫn chạy tiếp' if running else ''}</span></div>",
                 head + "</div>"]
        if running:
            parts.append(f"<div class='card'><span class='spinner'></span> Đang <b>{STEP_VI.get(job.step, job.step)}</b>… "
                         "trang tự làm mới.</div>")
        else:
            parts.append(_step_panel(job, d))
        log = _read(d / "log.txt")
        if log:
            parts.append(f"<div class='card'><h2>📝 Nhật ký</h2><pre>{html.escape(log[-4000:])}</pre></div>")
        if not running:
            parts.append(_manage_panel(job))
        return _page(f"Job {job_id}", "".join(parts), refresh=running)

    @app.post("/jobs/{job_id}/continue")
    def cont(job_id: str):
        worker.start(job_id)
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/choose")
    async def choose(job_id: str, request: Request):
        form = await request.form()
        choices = {int(k.split("_", 1)[1]): int(v) for k, v in form.items()
                   if k.startswith("choice_") and k.split("_", 1)[1].isdigit()}
        worker.start(job_id, action=lambda runner, job: runner.choose_hooks(job, choices))
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/segments")
    async def segments(job_id: str, request: Request):
        form = await request.form()
        rows = []
        for key in form:
            if key.startswith("keep_"):
                k = key[5:]
                rows.append({"start": float(form.get(f"start_{k}") or 0), "end": float(form.get(f"end_{k}") or 0),
                             "title_vi": str(form.get(f"title_{k}") or ""),
                             "summary_vi": str(form.get(f"summary_{k}") or "")})
        worker.start(job_id, action=lambda runner, job: runner.apply_segments(job, rows))
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/resources/scan", response_class=HTMLResponse)
    def resources_scan(download: str | None = Form(None)):
        key = app_settings.load(settings_path).get("freesound_api_key", "")
        try:
            report = scan_fn(bool(download), key)
        except Exception as exc:
            return _page("Quét tài nguyên", f"<div class='card'><h2>⚠️ Quét lỗi</h2><pre>{html.escape(str(exc))}</pre>"
                         "<p><a class='btn light' href='/'>🏠 Về trang chủ</a></p></div>")
        return _page("Quét tài nguyên", _scan_report_html(report, bool(download), bool(key)))

    @app.post("/settings/freesound")
    def save_freesound(key: str = Form("")):
        app_settings.save({"freesound_api_key": key.strip()}, settings_path)
        return RedirectResponse("/", status_code=303)

    @app.post("/settings/template")
    def save_template(name: str = Form(...)):
        app_settings.save({"template_name": name}, settings_path)
        return RedirectResponse("/", status_code=303)

    @app.post("/assets/upload", response_class=HTMLResponse)
    async def upload_asset(kind: str = Form(...), tag: str = Form(""), file: UploadFile = File(...)):
        from app.assets.local import AUDIO_EXTS
        from app.assets.freesound import slug

        name = Path(file.filename or "").name
        ext = Path(name).suffix.lower()
        if kind not in ("sfx", "music") or ext not in AUDIO_EXTS:
            return _page("Lỗi", f"<div class='card'><h2>File không hợp lệ</h2><p>Chỉ nhận âm thanh "
                         f"{', '.join(AUDIO_EXTS)}.</p><p><a class='btn light' href='/'>Quay lại</a></p></div>")
        folder = assets_root / kind / (slug(tag) if tag.strip() else "khac")
        folder.mkdir(parents=True, exist_ok=True)
        out = folder / f"{slug(Path(name).stem)}{ext}"
        with open(out, "wb") as f:
            shutil.copyfileobj(file.file, f)
        ledger.add(assets_root, out, source="user", license="người dùng tự thêm (tự xác nhận quyền dùng)",
                   extra={"original_name": name, "kind": kind, "tag": tag})
        return _page("Đã thêm", f"<div class='card'><h2>✅ Đã thêm vào kho</h2><p>{html.escape(out.name)} → "
                     f"{html.escape(kind)} / {html.escape(folder.name)}</p><p><a class='btn' href='/'>🏠 Về trang chủ</a>"
                     "</p></div>")

    @app.post("/jobs/{job_id}/voice")
    async def upload_voice(job_id: str, voice: UploadFile = File(...), video: int = Form(1)):
        from app.planner import hook_io

        d = Job.dir_for(Path(jobs_root), job_id)
        ext = Path(voice.filename or "").suffix.lower()
        if ext not in hook_io.VOICE_EXTS:
            return _page("Lỗi", f"<div class='card'><h2>File voice không hợp lệ</h2><p>Chỉ nhận "
                         f"{', '.join(hook_io.VOICE_EXTS)} (bạn chọn: {html.escape(voice.filename or '')}).</p>"
                         f"<p><a class='btn light' href='/jobs/{job_id}'>Quay lại</a></p></div>")
        vdir = d / "voice"
        vdir.mkdir(parents=True, exist_ok=True)
        for old in vdir.glob(f"{hook_io.voice_name(video)}.*"):  # thay file cũ (có thể khác đuôi)
            old.unlink()
        with open(vdir / f"{hook_io.voice_name(video)}{ext}", "wb") as f:
            shutil.copyfileobj(voice.file, f)
        worker.start(job_id)
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/redo")
    def redo(job_id: str, step: str = Form(...)):
        worker.start(job_id, action=lambda runner, job: runner.redo(job, step))
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/delete")
    def delete(job_id: str):
        d = Job.dir_for(Path(jobs_root), job_id)
        if worker.active != job_id and (d / "job.json").is_file():
            shutil.rmtree(d, ignore_errors=True)
        return RedirectResponse("/", status_code=303)

    return app


def _manage_panel(job: Job) -> str:
    """Các nút làm lại / xóa: mọi thao tác đều bấm trên giao diện."""
    jid = job.job_id

    def redo(step: str, label: str, confirm: str = "") -> str:
        onsubmit = f" onsubmit=\"return confirm('{confirm}')\"" if confirm else ""
        return (f"<form method='post' action='/jobs/{jid}/redo'{onsubmit}><input type='hidden' name='step' value='{step}'>"
                f"<button type='submit' class='btn light small'>{label}</button></form>")

    buttons = []
    if job.options.split and STEPS.index(job.step) > STEPS.index("review_segments"):
        buttons.append(redo("segment", "✂️ Chia lại video",
                            "AI sẽ chia lại video; hook, kế hoạch và voice cũ sẽ phải làm lại. Tiếp tục?"))
    have_plan = STEPS.index(job.step) > STEPS.index("plan") or job.status == Status.done
    if have_plan:
        buttons.append(redo("write", "🔁 Dựng lại draft", "Ghi đè draft CapCut hiện tại? Đóng CapCut trước khi bấm."))
        buttons.append(redo("plan", "🎬 Lập lại kế hoạch dựng", "AI sẽ lập kế hoạch mới và dựng lại draft. Tiếp tục?"))
    if job.options.hook and STEPS.index(job.step) > STEPS.index("choose_hook"):
        buttons.append(redo("choose_hook", "🎣 Chọn hook khác"))
    if job.options.hook and STEPS.index(job.step) > STEPS.index("hooks"):
        buttons.append(redo("hooks", "✍️ Viết hook mới", "AI sẽ viết 3 phương án hook mới. Tiếp tục?"))
    buttons.append(f"<form method='post' action='/jobs/{jid}/delete' onsubmit=\"return confirm('Xóa job này? "
                   "(draft đã ghi trong CapCut vẫn giữ nguyên)')\"><button type='submit' class='btn danger small'>"
                   "🗑️ Xóa job</button></form>")
    return (f"<div class='card'><h2>🛠️ Thao tác</h2><div class='actions'>"
            f"<a class='btn small' href='/'>🏠 Về trang chủ</a>{''.join(buttons)}</div></div>")


def _continue_button(job: Job, label: str = "Tiếp tục") -> str:
    return (f"<form method='post' action='/jobs/{job.job_id}/continue' style='margin-top:12px'>"
            f"<button type='submit' class='btn'>{label}</button></form>")


def _resource_tools(has_key: bool) -> str:
    """Nút quét / làm giàu kho + cài đặt Freesound + thêm file / cả thư mục âm thanh của mình vào kho."""
    from app.assets.scan import ENERGY_VI

    esc = html.escape
    cfg = app_config.load("assets")
    tags = "".join(f"<option value='{k}'>SFX · {k}</option>" for k in (cfg.get("sfx_queries") or {}))
    tags += "".join(f"<option value='{k}'>SFX · {esc(g.get('vi', k))}</option>" for k, g in (cfg.get("sfx_groups") or {}).items())
    tags += "".join(f"<option value='{k}'>Nhạc · {ENERGY_VI.get(k, k)} ({k})</option>"
                    for k in (cfg.get("music_queries") or {}))
    tags += "".join(f"<option value='{k}'>Nhạc · {esc(g.get('vi', k))}</option>"
                    for k, g in (cfg.get("music_groups") or {}).items())
    sources = "".join(f"<option value='{k}'>{esc(v.get('vi', k))}{' — phải ghi nguồn' if v.get('credit') else ''}</option>"
                      for k, v in (cfg.get("manual_sources") or {}).items())
    key_state = "✅ đã lưu key" if has_key else "chưa có key — vẫn tải được từ Openverse"
    try:
        from app.jobs.runner import drafts_root, list_drafts

        drafts = "".join(f"<option value='{esc(str(d))}'>{esc(n)}</option>" for d, n in list_drafts(drafts_root()))
    except Exception:
        drafts = ""
    return f"""
    <form method="post" action="/resources/scan" onsubmit="this.querySelector('button').innerHTML='<span class=spinner></span> Đang quét / tải… (có thể vài phút)'">
      <label class="tg" style="margin-top:12px"><input type="checkbox" name="download" checked>
        Tự tải thêm cái còn thiếu (Freesound + Openverse, chỉ CC0 / Public Domain)</label>
      <p><button type="submit" class="btn">🔍 Quét &amp; làm giàu kho</button></p>
      <p class="muted">Kho gồm {len(cfg.get('sfx_groups') or {})} nhóm SFX và {len(cfg.get('music_groups') or {})} nhóm nhạc
      (chuyển cảnh, va chạm, căng thẳng, đám đông, thiên nhiên… / hành động, tài liệu, cảm động, Nhật, Hàn, trap…).
      Nhóm nào chưa đủ file thì tool tự tìm và tải.</p></form>
    <details><summary class="muted">⚙️ Cài đặt Freesound ({key_state})</summary>
      <form method="post" action="/settings/freesound" style="margin-top:8px">
        <p class="muted">Lấy key miễn phí: đăng ký tài khoản ở freesound.org rồi vào
        <a href="https://freesound.org/apiv2/apply" target="_blank">freesound.org/apiv2/apply</a>, copy "Client secret/Api key".</p>
        <div class="row"><input type="text" name="key" placeholder="{'Đã lưu — dán key mới để thay' if has_key else 'Dán API key'}">
        <button class="btn small" type="submit">Lưu</button></div></form></details>
    <details><summary class="muted">📁 Nhập cả thư mục (Pixabay, Mixkit, YouTube Audio Library, Incompetech…)</summary>
      <form class="upload" method="post" action="/assets/import-folder"
            onsubmit="this.querySelector('button[type=submit]').innerHTML='<span class=spinner></span> Đang nhập…'">
        <p class="muted">Các trang này không có API nên tải tay về máy (có thể chia thư mục như SFX/ChuyenCanh,
        Nhac/CamDong…), rồi chọn thư mục ở đây. Tool tự xếp nhóm theo tên thư mục, ghi sổ nguồn và CREDITS.csv.</p>
        <div class="row"><input type="text" id="folder" name="folder" placeholder="Bấm Chọn thư mục… hoặc dán đường dẫn" required>
        <button type="button" class="btn light small" onclick="pickFolder()">📂 Chọn thư mục…</button></div>
        <div class="row" style="margin-top:8px"><select name="kind"><option value="auto">Tự nhận SFX / nhạc</option>
          <option value="sfx">Tất cả là SFX</option><option value="music">Tất cả là nhạc nền</option></select>
          <select name="source">{sources}</select></div>
        <div class="row" style="margin-top:8px"><input type="text" name="license" placeholder="Giấy phép (để trống = theo nguồn)">
          <input type="text" name="author" placeholder="Tác giả (nếu có)"></div>
        <p><button type="submit" class="btn small">Nhập vào kho</button></p>
        <p class="muted">Không nhập file giấy phép NonCommercial (NC) hoặc NoDerivatives (ND). Không lấy file từ CapCut/TikTok ra.</p>
      </form></details>
    <details><summary class="muted">📦 Lấy hiệu ứng / nhạc từ một dự án CapCut</summary>
      <form class="upload" method="post" action="/assets/import-capcut" enctype="multipart/form-data"
            onsubmit="this.querySelector('button[type=submit]').innerHTML='<span class=spinner></span> Đang đọc dự án…'">
        <p class="muted">Dự án đang có trong CapCut trên máy đã được tự quét. Dùng ô này để <b>giữ lại</b> tài nguyên của một
        dự án (kể cả khi sau này xóa nó), gắn nhãn tâm trạng cho nhạc, hoặc lấy từ <b>dự án ở máy khác</b> (nén .zip gửi sang).
        Chọn MỘT trong ba cách:</p>
        <label>1) Dự án trong CapCut trên máy này</label><select name="draft"><option value="">— không chọn —</option>{drafts}</select>
        <label style="margin-top:8px;display:block">2) Hoặc tải lên file .zip của thư mục dự án</label>
        <input type="file" name="zipfile" accept=".zip">
        <label style="margin-top:8px;display:block">3) Hoặc chọn thư mục dự án</label>
        <div class="row"><input type="text" id="cc_folder" name="folder" placeholder="Thư mục dự án CapCut">
        <button type="button" class="btn light small" onclick="pickFolder('cc_folder')">📂 Chọn…</button></div>
        <div class="row" style="margin-top:8px"><input type="text" name="mood" placeholder="Nhãn tâm trạng cho nhạc (vd: vui, căng, buồn) — không bắt buộc"></div>
        <label class="tg" style="margin-top:8px"><input type="checkbox" name="copy_to_capcut" checked>
          Chép dự án (zip / thư mục ngoài) vào CapCut để mở 1 lần cho CapCut tải tài nguyên</label>
        <p><button type="submit" class="btn small">Lấy tài nguyên</button></p></form></details>
    <details><summary class="muted">➕ Thêm một file âm thanh</summary>
      <form class="upload" method="post" action="/assets/upload" enctype="multipart/form-data">
        <div class="row"><select name="kind"><option value="sfx">SFX</option><option value="music">Nhạc nền</option></select>
        <select name="tag">{tags}</select></div>
        <input type="file" name="file" accept="audio/*" required><br>
        <button class="btn small" type="submit">Thêm vào kho</button>
        <p class="muted">Chỉ thêm file bạn có quyền dùng. Nguồn được ghi vào sổ assets/ledger.json.</p></form></details>
    <script>
    async function pickFolder(id){{
      try{{const r=await fetch('/api/pick-folder');const d=await r.json();
        if(d.path) document.getElementById(id||'folder').value=d.path; else if(d.error) alert(d.error);}}
      catch(e){{alert('Không mở được hộp thoại: '+e);}}
    }}
    </script>"""


def _template_setting() -> str:
    """Chọn dự án CapCut làm khuôn (dự án mẫu) ngay trên giao diện."""
    from app.jobs.runner import BUILTIN, drafts_root, list_drafts, resolve_template, template_name

    esc = html.escape
    current = template_name()
    try:
        drafts = list_drafts(drafts_root())
    except Exception:
        drafts = []
    try:
        used = resolve_template()
        from app.jobs.runner import BUILTIN_TEMPLATE

        state = "mẫu có sẵn trong tool" if used == BUILTIN_TEMPLATE else f"dự án CapCut '{esc(current)}'"
    except Exception as exc:
        state = f"⚠️ {esc(str(exc))}"
    names = sorted({n for _, n in drafts})
    opts = [f"<option value='{BUILTIN}' {'selected' if current == BUILTIN else ''}>Mẫu có sẵn trong tool</option>"]
    opts += [f"<option value='{esc(n)}' {'selected' if n == current else ''}>{esc(n)}</option>" for n in names]
    return (f"<details><summary class='muted'>🧩 Dự án mẫu CapCut (đang dùng: {state})</summary>"
            "<form method='post' action='/settings/template' style='margin-top:8px'>"
            "<p class='muted'>Dự án mẫu là khuôn để tool nhân bản chữ, clip, âm thanh. Nên chọn dự án bạn tạo riêng "
            "làm mẫu và đừng xóa nó trong CapCut; không có thì dùng mẫu có sẵn trong tool.</p>"
            f"<div class='row'><select name='name'>{''.join(opts)}</select>"
            "<button class='btn small' type='submit'>Lưu</button></div></form></details>")


def _scan_report_html(rep, download: bool, has_key: bool) -> str:
    esc = html.escape
    names = {"music": "nhạc", "sfx": "SFX", "video_effect": "hiệu ứng", "transition": "chuyển cảnh",
             "sticker": "sticker", "filter": "filter", "text_animation": "animation chữ"}
    box = lambda d: "".join(f"<div><b>{n}</b>{names.get(k, k)}</div>" for k, n in d.items()) or "<div>trống</div>"  # noqa: E731
    color = {"có sẵn": "done", "đã tải": "running", "còn thiếu": "error"}
    rows = "".join(
        f"<tr><td>{esc(n['label'])}</td><td>{n['have']}</td><td class='muted'>{esc(n['why'])}</td>"
        f"<td><span class='badge b-{color.get(n['status'], 'pending')}'>{esc(n['status'])}</span></td></tr>"
        for n in rep.needs)
    parts = ["<div class='topnav'><a class='btn light small' href='/'>🏠 Về trang chủ</a></div>",
             "<div class='card'><h2>🔍 Kết quả quét tài nguyên</h2>",
             f"<p><b>Từ CapCut</b> (mọi dự án trên máy):</p><div class='lib'>{box(rep.capcut)}</div>",
             f"<p><b>Kho trên máy</b> (thư mục assets/):</p><div class='lib'>{box(rep.local)}</div>",
             f"<h2 style='margin-top:18px'>Tài nguyên cần thiết</h2><table><tr><th>Cần</th><th>Đang có</th><th>Vì sao</th>"
             f"<th>Trạng thái</th></tr>{rows}</table>"]
    if rep.downloaded:
        dl = "".join(f"<tr><td>{esc(d.get('name') or d['file'])}</td><td>{esc(d.get('tag', ''))}</td>"
                     f"<td>{esc(d.get('author', ''))}</td><td><a href='{esc(d.get('url', ''))}' target='_blank'>nguồn</a></td>"
                     "<td>CC0</td></tr>" for d in rep.downloaded)
        parts.append(f"<h2 style='margin-top:18px'>⬇️ Vừa tải về ({len(rep.downloaded)})</h2><table><tr><th>Tên</th>"
                     f"<th>Loại</th><th>Tác giả</th><th>Link</th><th>Giấy phép</th></tr>{dl}</table>")
    if rep.errors:
        parts.append(f"<div class='note'>{'<br>'.join(esc(e) for e in rep.errors)}</div>")
    still = [n for n in rep.needs if n["status"] == "còn thiếu"]
    if still:
        if not download:
            hint = "Tick <b>Tải thêm từ internet</b> rồi quét lại để tool tự tải bản CC0 từ Freesound."
        elif not has_key:
            hint = "Chưa có Freesound API key: mở <b>⚙️ Cài đặt Freesound</b> ở trang chủ để nhập."
        else:
            hint = "Freesound chưa có bản phù hợp cho các mục này."
        parts.append(f"<div class='note'>Còn thiếu {len(still)} mục. {hint} Hoặc: mở CapCut, dùng thử âm thanh loại đó "
                     "trong một dự án bất kỳ rồi lưu; hoặc thêm file của bạn ở mục <b>➕ Thêm file âm thanh</b>.</div>")
    for jid in rep.jobs_to_redo:
        parts.append(f"<form method='post' action='/jobs/{esc(jid)}/redo' style='margin-top:10px'>"
                     f"<input type='hidden' name='step' value='write'><button class='btn small' type='submit'>"
                     f"🔁 Dựng lại draft job {esc(jid)} với tài nguyên mới</button></form>")
    parts.append("</div>")
    return "".join(parts)


def _library_summary() -> str:
    """Số nhạc / SFX / hiệu ứng đạo diễn có thể dùng (tự quét mọi dự án CapCut trên máy)."""
    try:
        from app.jobs.runner import Runner

        tpl = Runner(JOBS_ROOT, log=lambda m: None)._template()
    except Exception as exc:
        return f"<p class='muted'>Chưa đọc được dự án mẫu CapCut: {html.escape(str(exc))}</p>"
    count = lambda k: sum(1 for i in tpl.library if i.kind == k)  # noqa: E731
    boxes = "".join(f"<div><b>{count(k)}</b>{label}</div>" for k, label in
                    (("music", "nhạc nền"), ("sfx", "SFX"), ("video_effect", "hiệu ứng"), ("transition", "chuyển cảnh"),
                     ("sticker", "sticker")))
    return (f"<div class='lib'>{boxes}</div><p class='muted'>Tool tự quét <b>mọi dự án CapCut</b> trên máy: nhạc, SFX, "
            "hiệu ứng, sticker, chuyển cảnh bạn từng dùng (và CapCut đã tải về) đều vào kho. Muốn kho nhiều hơn: mở CapCut, "
            "thêm vài bài nhạc / hiệu ứng vào một dự án bất kỳ rồi lưu — lần dựng sau tool tự thấy.</p>")


def pick_folder_dialog() -> dict:
    """Hộp thoại chọn thư mục của Windows (server và trình duyệt cùng một máy)."""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return {"error": "Máy không có tkinter, hãy dán đường dẫn thư mục."}
    try:
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="Chọn thư mục âm thanh đã tải về")
        root.destroy()
    except Exception as exc:
        return {"error": f"Không mở được hộp thoại chọn thư mục: {exc}"}
    return {"path": str(Path(path)) if path else ""}


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


def _segments_panel(job: Job, d: Path) -> str:
    """Bảng duyệt chia video: các video (sửa được điểm cắt, bỏ tick để bỏ) + các đoạn bị bỏ (tick để dựng thêm)."""
    esc = html.escape
    data = json.loads(_read(d / "plan" / "segments.json") or "{}")
    prop = data.get("proposal") or {}
    min_s = app_config.load("split").get("min_video_s", 60)

    def row(key: str, v: dict, keep: bool, note: str) -> str:
        span = float(v["end"]) - float(v["start"])
        short = f" <span class='badge b-waiting'>ngắn hơn {min_s}s</span>" if span < min_s else ""
        return (f"<tr><td><input type='checkbox' name='keep_{key}' {'checked' if keep else ''}></td>"
                f"<td><input type='number' step='0.1' name='start_{key}' value='{float(v['start']):.1f}' style='width:90px'>"
                f" – <input type='number' step='0.1' name='end_{key}' value='{float(v['end']):.1f}' style='width:90px'></td>"
                f"<td>{span:.0f}s{short}</td><td><b>{esc(v.get('title_vi', ''))}</b><br>"
                f"<span class='muted'>{esc(v.get('summary_vi', '') or note)}</span>"
                f"<input type='hidden' name='title_{key}' value='{esc(v.get('title_vi', ''))}'>"
                f"<input type='hidden' name='summary_{key}' value='{esc(v.get('summary_vi', '') or note)}'></td></tr>")

    vids = "".join(row(f"v{i}", v, True, v.get("why_vi", "")) for i, v in enumerate(data.get("videos", []), 1))
    dropped = "".join(row(f"d{i}", {**x, "title_vi": "Đoạn bị bỏ"}, False, "Lý do bỏ: " + x.get("reason_vi", ""))
                      for i, x in enumerate(prop.get("dropped", []), 1))
    head = "<tr><th>Dựng</th><th>Giây (bắt đầu – kết thúc)</th><th>Độ dài</th><th>Nội dung</th></tr>"
    return (f"<div class='card'><h2>✂️ Duyệt chia video</h2>"
            f"<p>AI đề xuất {len(data.get('videos', []))} video độc lập. Sửa giây bắt đầu/kết thúc nếu muốn, bỏ tick để "
            f"không dựng, hoặc tick đoạn bị bỏ để dựng thêm. Mỗi video sau khi dựng sẽ được cắt gọn còn 60–150 giây.</p>"
            f"<p class='muted'>Ghi chú editor: {esc(prop.get('editor_notes', ''))}</p>"
            f"<form method='post' action='/jobs/{job.job_id}/segments'>"
            f"<h2 style='margin-top:14px'>Video sẽ dựng</h2><table>{head}{vids}</table>"
            + (f"<h2 style='margin-top:18px'>Đoạn bị bỏ</h2><table>{head}{dropped}</table>" if dropped else "")
            + "<p><button type='submit' class='btn'>✅ Xác nhận và dựng tiếp</button></p></form></div>")


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
        from app.planner import hook_io

        _, choices = hook_io.load_hooks(d)
        forms = []
        for v in sorted(choices):
            have = hook_io.find_voice(d, v)
            state = f"✅ đã có ({esc(have.name)}) — tải lại để thay" if have else "❌ còn thiếu"
            forms.append(
                f"<form class='upload' method='post' action='/jobs/{job.job_id}/voice' enctype='multipart/form-data'>"
                f"<b>📤 Voice cho video{v:02d}</b> <span class='muted'>{state}</span><br>"
                f"<input type='hidden' name='video' value='{v}'>"
                f"<input type='file' name='voice' accept='.wav,.mp3,.m4a,audio/*' required>"
                f"<br><button type='submit' class='btn small'>Tải lên</button></form>")
        return (f"<div class='card'><h2>🎙️ Thu voice hook</h2><p>Thu các câu dưới đây bằng Voice Studio, rồi tải lên "
                f"từng file (wav / mp3 / m4a). Đủ file là tool tự dựng tiếp.</p>"
                f"<pre>{esc(_read(d / 'hook_scripts.txt'))}</pre>{''.join(forms)}"
                f"<p class='muted'>{esc(job.message)}</p></div>")
    if job.status == Status.waiting and job.step == "review_segments":
        return _segments_panel(job, d)
    if job.status == Status.waiting:
        extra = ""
        u = d / "plan" / "understanding.json"
        if job.step == "confirm_genre" and u.is_file():
            data = json.loads(_read(u))
            extra = (f"<p>Phong cách đề xuất: {esc(data.get('suggested_style', ''))}</p>"
                     f"<p>Ghi chú editor: {esc(data.get('editor_notes', ''))}</p>")
        return f"<div class='card'><pre>{esc(job.message)}</pre>{extra}{_continue_button(job)}</div>"
    if job.status == Status.done:
        drafts = job.data.get("drafts") or [{"index": 1, "draft": job.data.get("draft", ""),
                                             "duration_s": job.data.get("duration_s", "?")}]
        parts = [f"<div class='card'><h2>✅ Xong — {len(drafts)} video</h2><p>Mở CapCut để xem, chỉnh và xuất từng draft.</p>"]
        for dr in drafts:
            i = dr["index"]
            short = " <span class='badge b-waiting'>ngắn hơn 1 phút</span>" if dr.get("short") else ""
            parts.append(f"<h2 style='margin-top:18px'>🎬 Video {i:02d}{short}</h2><p>Draft: <b>{esc(dr['draft'])}</b> "
                         f"({dr.get('duration_s', '?')} giây)</p>")
            plan = d / "plan" / f"edit_plan_video{i:02d}.json"
            if plan.is_file():
                pdata = json.loads(_read(plan))
                titles = [t for t in pdata.get("titles_top", []) + pdata.get("titles_bottom", []) if t]
                if titles:
                    parts.append("<p><b>Dòng tiêu đề:</b></p><pre>" + esc("\n".join(titles)) + "</pre>")
                parts.append(f"<p><b>Ghi chú editor:</b> {esc(pdata.get('editor_notes', ''))}</p>")
            cap = _read(d / "deliver" / f"video{i:02d}_captions.txt")
            if cap:
                parts.append(f"<details><summary><b>📣 Caption + hashtag</b></summary><pre>{esc(cap)}</pre></details>")
        missing = json.loads(_read(d / "missing_assets.json") or "[]")
        if missing:
            rows = "".join(f"<tr><td>{m.get('video', 1):02d}</td><td>{esc(m['kind'])}</td><td>{esc(str(m['what']))}</td><td>{m['at_s']}s</td>"
                           f"<td>{esc(m.get('purpose_vi', ''))}</td></tr>" for m in missing)
            parts.append("<h2 style='margin-top:18px'>🧩 Tài nguyên cần bổ sung</h2><table><tr><th>Video</th><th>Loại</th><th>Cần gì</th><th>Giây</th>"
                         f"<th>Để làm gì</th></tr>{rows}</table><div class='note'>Mở CapCut, thêm các âm thanh/hiệu ứng "
                         "này vào một dự án bất kỳ (để CapCut tải về), lưu lại, rồi bấm <b>🔁 Dựng lại draft</b> bên dưới."
                         "</div>")
        parts.append("</div>")
        return "".join(parts)
    return f"<div class='card'>{_continue_button(job, 'Chạy')}</div>"


app = create_app()
