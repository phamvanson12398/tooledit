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
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

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
.b-pending,.b-running{background:var(--run)}.b-waiting{background:var(--warn)}.b-error{background:var(--err)}.b-done{background:var(--ok)}.b-stopped{background:#6b7280}
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
    "plan": "AI lập kế hoạch dựng", "dub": "AI viết thuyết minh", "dub_voice": "Chờ voice thuyết minh",
    "assets": "Tìm tài nguyên", "write": "Ghi dự án CapCut",
    "captions": "AI viết caption", "done": "Xong",
}
# Tên bước riêng theo chế độ (chủ dự án 09/10: "sao các quy trình chả khác gì nhau") — job.applies đã ẩn bước không chạy
STEP_VI_MODE = {
    "review": {"segment": "AI tìm đoạn hay", "review_segments": "Chờ duyệt đoạn hay",
               "plan": "AI chọn tiêu đề · nhạc", "dub": "AI viết bài lời đọc", "dub_voice": "Chờ bạn đọc cả bài",
               "write": "Dựng cảnh theo voice → CapCut"},
    "vi_sub": {"write": "Dịch phụ đề tiếng Việt → CapCut"},
    "voice_only": {"plan": "AI lập kế hoạch (giữ nguyên hình)", "dub": "AI viết thuyết minh",
                   "dub_voice": "Chờ voice thuyết minh"},
}
MODE_VI = {"review": "🎬 Review phim / hoạt hình", "vi_sub": "🇻🇳 Chỉ phụ đề tiếng Việt",
           "voice_only": "🎙️ Chỉ thay tiếng", "dub": "🌐 Đổi ngôn ngữ", "montage": "🎞️ Ghép nhiều video",
           "normal": "✂️ Dựng thường"}


def job_mode(job) -> str:
    o = job.options
    if o.review:
        return "review"
    if o.vi_sub:
        return "vi_sub"
    if o.voice_only:
        return "voice_only"
    if len(job.footage) > 1:
        return "montage"
    return "dub" if o.target_language else "normal"


def esc_mode(job) -> str:
    """Nhãn chế độ ngắn trước tên bước trong danh sách job (trang chủ)."""
    return f"{MODE_VI[job_mode(job)].split(' ')[0]} " if job_mode(job) != "normal" else ""


def step_label(job, st: str) -> str:
    return STEP_VI_MODE.get(job_mode(job), {}).get(st) or STEP_VI.get(st, st)


STATUS_VI = {"pending": "chờ chạy", "running": "đang chạy", "waiting": "chờ bạn", "error": "lỗi", "done": "xong",
             "stopped": "đã dừng"}


class Worker:
    """Chạy nhiều job song song (mỗi job một luồng), tối đa `max_jobs()` cùng lúc; job thêm sau xếp hàng.
    Bước nặng (phân tích GPU, hỏi AI, ghi draft) còn được giới hạn riêng trong app/jobs/limits.py."""

    def __init__(self, jobs_root: Path, runner_factory, max_jobs=None):
        self.jobs_root = jobs_root
        self.runner_factory = runner_factory
        self.max_jobs = max_jobs or (lambda: 1)
        self.lock = threading.Lock()
        self.active: set[str] = set()
        self.queue: list[tuple[str, object]] = []

    def queued_ids(self) -> list[str]:
        with self.lock:
            return [j for j, _ in self.queue]

    def remove_queued(self, job_id: str) -> bool:
        with self.lock:
            n = len(self.queue)
            self.queue = [q for q in self.queue if q[0] != job_id]
            return len(self.queue) < n

    def stop(self, job_id: str) -> str:
        """Nút Dừng: job đang xếp hàng → bỏ khỏi hàng; đang chạy → đánh dấu để luồng tự dừng ở điểm an toàn gần nhất.
        Trả 'queued' / 'running' / 'idle'."""
        from app.jobs import stop as stop_mod

        if self.remove_queued(job_id):
            job = Job.load(self.jobs_root, job_id)
            job.stop("Đã bỏ khỏi hàng đợi theo yêu cầu. Bấm Chạy tiếp để chạy.")
            job.save(self.jobs_root)
            return "queued"
        with self.lock:
            running = job_id in self.active
        if running:
            stop_mod.request(job_id)
            return "running"
        return "idle"

    def start(self, job_id: str, action=None) -> bool:
        """Chạy job (hoặc xếp hàng nếu đủ luồng). False nếu job đang chạy / đã trong hàng đợi."""
        with self.lock:
            if job_id in self.active or any(j == job_id for j, _ in self.queue):
                return False
            if len(self.active) >= max(1, int(self.max_jobs())):
                self.queue.append((job_id, action))
                return True
            self.active.add(job_id)
        threading.Thread(target=self._work, args=(job_id, action), daemon=True).start()
        return True

    def _work(self, job_id: str, action) -> None:
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
            nxt = None
            with self.lock:
                self.active.discard(job_id)
                if self.queue and len(self.active) < max(1, int(self.max_jobs())):
                    nxt = self.queue.pop(0)
                    self.active.add(nxt[0])
            if nxt:
                threading.Thread(target=self._work, args=nxt, daemon=True).start()


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
               settings_path: Path | None = None, scan_fn=None, compare_fn=None) -> FastAPI:
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
    def max_jobs() -> int:  # đổi được trên giao diện (config/local.yaml), mặc định theo config/app.yaml
        local = app_settings.load(settings_path).get("parallel_jobs")
        return int(local or (app_config.load("app").get("parallel") or {}).get("jobs", 3))

    worker = Worker(Path(jobs_root), runner_factory, max_jobs)
    app.state.worker = worker

    def keep_days() -> float:
        local = app_settings.load(settings_path).get("cleanup_days")
        return float(app_config.load("app").get("cleanup_days", 2) if local is None else local)

    def cleanup_now() -> list[str]:
        from app.jobs.cleanup import cleanup_jobs

        return cleanup_jobs(Path(jobs_root), keep_days(), skip=set(worker.active) | set(worker.queued_ids()))

    app.state.cleanup_now = cleanup_now

    def cleanup_loop() -> None:  # dọn lúc mở tool, rồi mỗi giờ một lần
        while True:
            try:
                cleanup_now()
            except Exception:
                pass
            time.sleep(3600)

    threading.Thread(target=cleanup_loop, daemon=True).start()

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

    def jobs_panel() -> str:
        """Danh sách video + số luồng đang chạy — phần DUY NHẤT của trang chủ tự cập nhật (qua /api/jobs-panel),
        để không làm mất file / lựa chọn người dùng đang nhập ở form tạo video."""
        queued_ids = worker.queued_ids()

        def badge(j: Job) -> str:
            if j.job_id in worker.active:
                return "<span class='badge b-running'><span class='spinner'></span> đang chạy</span>"
            if j.job_id in queued_ids:
                return f"<span class='badge b-waiting'>xếp hàng #{queued_ids.index(j.job_id) + 1}</span>"
            return f"<span class='badge b-{j.status.value}'>{STATUS_VI[j.status.value]}</span>"

        jobs_html = "".join(
            f"<a class='job' href='/jobs/{j.job_id}'><div><div class='name'>{html.escape(Path(j.footage[0]).name)}</div>"
            f"<div class='sub'>{j.job_id} · {html.escape(j.data.get('style_used') or j.data.get('style') or '')} · "
            f"{esc_mode(j)}{step_label(j, j.step)}</div></div>{badge(j)}</a>" for j in list_jobs())
        status = (f"<p class='muted'>Đang chạy <b>{len(worker.active)}/{max_jobs()}</b> luồng"
                  f"{f', {len(queued_ids)} xếp hàng' if queued_ids else ''}</p>")
        return status + (jobs_html or "<p class='muted'>Chưa có video nào.</p>")

    @app.get("/api/jobs-panel", response_class=HTMLResponse)
    def jobs_panel_api():
        return HTMLResponse(jobs_panel())

    @app.get("/", response_class=HTMLResponse)
    def index():
        from app.styles import available_styles

        has_key = bool(app_settings.load(settings_path).get("freesound_api_key"))
        n_max = max_jobs()
        opts = "".join(f"<option value='{n}' {'selected' if n == n_max else ''}>{n}</option>" for n in range(1, 7))
        kd = keep_days()
        day_opts = "".join(f"<option value='{v}' {'selected' if float(v) == kd else ''}>{label}</option>"
                           for v, label in (("0", "không tự xóa"), ("1", "1 ngày"), ("2", "2 ngày"), ("3", "3 ngày"),
                                            ("7", "7 ngày")))
        threads = (f"<form method='post' action='/settings/parallel' class='row' style='align-items:center;gap:8px'>"
                   f"<span class='muted'>Số video chạy cùng lúc:</span>"
                   f"<select name='n' onchange='this.form.submit()' style='width:auto'>{opts}</select></form>"
                   f"<form method='post' action='/settings/cleanup' class='row' style='align-items:center;gap:8px;margin-top:6px'>"
                   f"<span class='muted'>Tự xóa job không hoạt động quá:</span>"
                   f"<select name='days' onchange='this.form.submit()' style='width:auto'>{day_opts}</select></form>")
        rcfg = app_config.load("review")  # độ dài video review lấy từ config/review.yaml (đổi config là trang tự đổi)

        def mmss(sec) -> str:
            return f"{int(sec) // 60}:{int(sec) % 60:02d}"
        review_len = f"{mmss(rcfg.get('min_video_s', 130))}–{mmss(rcfg.get('max_video_s', 150))}"
        style_cards = ["<label class='style'><input type='radio' name='style' value='auto' checked>"
                       "<b>✨ AI tự chọn</b><span>Đạo diễn xem nội dung rồi chọn kiểu phù hợp</span></label>"]
        for key, st in available_styles().items():
            style_cards.append(f"<label class='style'><input type='radio' name='style' value='{key}'>"
                               f"<b>{html.escape(st['name_vi'] or key)}</b><span>{html.escape(st['fits_vi'])}</span></label>")
        lib, lib_err = _load_library()
        body = f"""
        <div class="grid"><div>
        <div class="card"><h2>🎞️ Tạo video mới</h2>
        <form method="post" action="/jobs" enctype="multipart/form-data">
          <div class="field"><label>File footage</label>
            <div class="row"><textarea id="footage" name="footage" rows="2" style="flex:1" placeholder="Bấm Chọn file… hoặc dán đường dẫn (nhiều video: mỗi dòng một file)" required></textarea>
            <button type="button" class="btn light" onclick="pick()">📂 Chọn file…</button></div>
            <div class="muted">🎞️ <b>Ghép nhiều video:</b> trong hộp thoại Chọn file giữ <b>Ctrl</b> (hoặc <b>Shift</b>) để chọn
            nhiều file một lúc, hoặc bấm Chọn file nhiều lần (mỗi file một dòng) — tool chọn cảnh hay
            từ TẤT CẢ video (mỗi video một chút), ghép thành MỘT câu chuyện ý nghĩa dài khoảng 2 phút (chặng đường, quá trình,
            tình bạn…), giữ tiếng gốc + thêm nhạc nền, hiệu ứng.</div>
            <div class="muted" id="pickmsg"></div></div>
          <div class="field"><label>Kiểu dựng</label><div class="styles">{''.join(style_cards)}</div></div>
          <div class="field"><label>Tùy chọn</label><div class="toggles">
            <label class="tg"><input type="checkbox" name="hook" checked> Có hook voice</label>
            <label class="tg"><input type="checkbox" name="reframe"> Đổi khung theo cảnh</label>
            <label class="tg"><input type="checkbox" name="business"> Khách doanh nghiệp (nhạc Commercial)</label>
            <label class="tg"><input type="checkbox" name="confirm"> Xác nhận trước khi dựng</label>
            <label class="tg"><input type="checkbox" name="split"> Chia video dài thành nhiều video</label>
            <label class="tg"><input type="checkbox" name="hype"> ⚡ Chuyển cảnh liên tục — cảnh gay cấn lên đầu (3–5s/cảnh)</label>
            <label class="tg"><input type="checkbox" name="review"> 🎬 Review phim / hoạt hình — tìm đoạn hay, mỗi đoạn
            một video {review_len} có lời review (bạn thu voice)</label>
            <label class="tg"><input type="checkbox" name="vi_sub"> 🇻🇳 Chỉ phụ đề tiếng Việt — xem hiểu video nước ngoài
            (không dựng lại; ra file .srt + draft giữ nguyên video)</label></div></div>
          {_music_select(lib)}
          <div class="field"><label>🌐 Đổi ngôn ngữ video (thuyết minh + phụ đề, dựng lại khác bản gốc)</label>
            <select name="target_language"><option value="">Giữ nguyên ngôn ngữ gốc</option>
              <option value="ko">Đổi sang tiếng Hàn (한국어)</option><option value="ja">Đổi sang tiếng Nhật (日本語)</option>
              <option value="en">Đổi sang tiếng Anh (English)</option></select>
            <div class="muted">Video gốc tiếng Hàn / Nhật / Anh / Trung. AI dịch và viết câu thuyết minh, bạn thu voice từng câu
            bằng Voice Studio rồi tải lên; mọi cảnh được đổi khung, zoom, chuyển động, nhạc + tiêu đề mới (giữ thứ tự cảnh).</div>
            <label style="margin-top:8px">✍️ Cách viết lời thuyết minh</label><select name="script_mode">
              <option value="rewrite">AI xem video rồi VIẾT MỚI nội dung hợp nước đó (không dịch)</option>
              <option value="translate">Dịch sát lời gốc (bản địa hóa nhẹ)</option></select>
            <label class="tg"><input type="checkbox" name="voice_only"> 🎙️ Chỉ thay tiếng — giữ NGUYÊN hình</label>
            <div class="muted">Không cắt, không đổi khung / zoom / lật: video giữ đúng như gốc từ đầu đến cuối. Chỉ tắt tiếng gốc,
            thêm voice thuyết minh + phụ đề + tiêu đề (ngôn ngữ đã chọn ở trên), nhạc nền nhẹ và hiệu ứng. Không có hook,
            không chia video. Đoạn vi phạm chính sách TikTok vẫn bị cắt.</div>
            <label class="tg"><input type="checkbox" name="keep_bgm"> 🎵 Giữ nhạc nền gốc (chỉ tách bỏ giọng nói)</label>
            <div class="muted">Dùng cùng "Chỉ thay tiếng": tool tách giọng nói khỏi âm thanh gốc, giữ nguyên nhạc nền + tiếng
            hiện trường, chỉ thay lời bằng voice thuyết minh (không thêm nhạc khác). Cần cài Demucs một lần
            (docs/SETUP_WINDOWS.md); chưa cài thì tool dùng nhạc AI chọn như thường.</div></div>
          <div class="field" style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div><label>Mã khách</label><input type="text" name="client" value="khach"></div>
            <div><label>Khung video</label><select name="ratio">
              <option value="4:3">4:3</option><option value="1:1">1:1 (vuông)</option>
              <option value="16:9">16:9</option><option value="auto">Tự động</option></select></div></div>
          <p><button type="submit" class="btn big">🚀 Bắt đầu dựng</button></p>
        </form></div>{_compare_card()}</div>
        <div><div class="card"><h2>📚 Kho tài nguyên</h2>{_library_summary(lib, lib_err)}{_resource_tools(has_key)}{_template_setting()}</div>
        <div class="card jobs"><h2>🗂️ Các video</h2>{threads}<div id="jobs-panel">{jobs_panel()}</div>
        <p class='muted'>Mỗi video chạy trên một luồng riêng (ví dụ luồng 1 podcast, luồng 2 video hài). Bước phân tích
        dùng GPU nên lần lượt từng video; hỏi đạo diễn AI tối đa 2 video cùng lúc (chung hạn mức Claude Pro).</p></div></div></div>
        <script>
        async function pick(){{
          const m=document.getElementById('pickmsg'); m.textContent='Đang mở hộp thoại chọn file…';
          try{{const r=await fetch('/api/pick-file?multiple=1');const d=await r.json();
            const ps=d.paths||(d.path?[d.path]:[]);
            if(ps.length){{const f=document.getElementById('footage');const nl=String.fromCharCode(10);
              f.value=(f.value.trim()?f.value.trim()+nl:'')+ps.join(nl);
              m.textContent=ps.length>1?('Đã thêm '+ps.length+' video — tool sẽ ghép thành một video.'):'';}}
            else m.textContent=d.error||'Chưa chọn file.';}}catch(e){{m.textContent='Không mở được hộp thoại: '+e;}}
        }}
        </script>"""
        body += """<script>
        // Chỉ cập nhật danh sách video mỗi 3 giây (KHÔNG tải lại cả trang → không mất file / lựa chọn đang nhập)
        setInterval(async () => {
          if (document.hidden) return;
          try { const r = await fetch('/api/jobs-panel'); if (r.ok) document.getElementById('jobs-panel').innerHTML = await r.text(); }
          catch (e) {}
        }, 3000);
        </script>"""
        return _page("Tool dựng video", body)

    @app.post("/compare", response_class=HTMLResponse)
    def compare(original: str = Form(...), edited: str = Form(...), back: str = Form("/")):
        esc = html.escape
        o, e = Path(original.strip().strip('"')), Path(edited.strip().strip('"'))
        missing = [str(x) for x in (o, e) if not x.is_file()]
        back = back if back.startswith("/") else "/"
        if missing:
            return _page("So sánh", f"<div class='card'><h2>Không thấy file</h2><p>{esc(', '.join(missing))}</p>"
                         f"<p><a class='btn light' href='{esc(back)}'>Quay lại</a></p></div>")
        if compare_fn is None:
            from app.analysis.compare import compare_videos as fn
        else:
            fn = compare_fn
        try:
            r = fn(o, e)
        except Exception as exc:
            return _page("So sánh", f"<div class='card'><h2>⚠️ Không so sánh được</h2><pre>{esc(str(exc))}</pre>"
                         f"<p><a class='btn light' href='{esc(back)}'>Quay lại</a></p></div>")
        return _page("So sánh", _compare_result_html(r, o, e, back))

    @app.get("/api/pick-file")
    def pick_file(multiple: int = 0):
        return pick_file_dialog(multiple=bool(multiple))

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
                split: str | None = Form(None), target_language: str = Form(""), music: str = Form(""),
                music_file: UploadFile | None = File(None), voice_only: str | None = Form(None),
                keep_bgm: str | None = Form(None), script_mode: str = Form(""), hype: str | None = Form(None),
                vi_sub: str | None = Form(None), review: str | None = Form(None)):
        paths = [Path(x.strip().strip('"')) for x in footage.splitlines() if x.strip().strip('"')]
        missing_files = [p for p in paths if not p.is_file()]
        if not paths or missing_files:
            return _page("Lỗi", "<div class='card'><h2>Không thấy file</h2><p>"
                         + html.escape(", ".join(str(p) for p in missing_files) or "(chưa chọn file)")
                         + "</p><p><a class='btn light' href='/'>Quay lại</a></p></div>")
        path = paths[0]
        lang = target_language if target_language in ("ko", "ja", "en") else ""
        if voice_only and len(paths) > 1:
            return _page("Lỗi", "<div class='card'><h2>Chỉ thay tiếng dùng cho MỘT video</h2><p>Bỏ tick "
                         "<b>Chỉ thay tiếng</b> để ghép nhiều video, hoặc chỉ chọn một file.</p>"
                         "<p><a class='btn light' href='/'>Quay lại</a></p></div>")
        if voice_only and not lang:
            return _page("Lỗi", "<div class='card'><h2>Chưa chọn ngôn ngữ</h2><p>Chế độ <b>Chỉ thay tiếng</b> cần chọn "
                         "ngôn ngữ mới ở ô <b>🌐 Đổi ngôn ngữ video</b> (Hàn / Nhật / Anh).</p>"
                         "<p><a class='btn light' href='/'>Quay lại</a></p></div>")
        if review and (voice_only or vi_sub):
            return _page("Lỗi", "<div class='card'><h2>Chọn một chế độ thôi</h2><p><b>Review phim</b> không dùng cùng "
                         "<b>Chỉ thay tiếng</b> hay <b>Chỉ phụ đề tiếng Việt</b>. Bỏ bớt một ô tick.</p>"
                         "<p><a class='btn light' href='/'>Quay lại</a></p></div>")
        job = Job.create(Path(jobs_root), [p.resolve() for p in paths], JobOptions(
            client_id=client.strip() or "khach", hook=bool(hook) and not voice_only and not review,
            reframe_per_scene=bool(reframe) and not voice_only,
            confirm_before_build=bool(confirm), split=bool(split) and not voice_only and len(paths) == 1,
            hype=bool(hype) and not voice_only and not review, review=bool(review),
            target_language=lang, voice_only=bool(voice_only), keep_bgm=bool(keep_bgm) and bool(voice_only),
            script_mode=script_mode if script_mode in ("rewrite", "translate") else "",
            vi_sub=bool(vi_sub) and len(paths) == 1))
        job.data.update({"business": bool(business), "default_ratio": ratio, "style": style})
        if music_file is not None and music_file.filename:
            chosen = _save_user_music(music_file, Path(assets_root))
            if chosen:
                job.data["music_choice"] = chosen
        elif music.strip():
            job.data["music_choice"] = music.strip()
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
        running = job_id in worker.active
        queued = job_id in worker.queued_ids()
        status = "running" if running else job.status.value
        cur = STEPS.index(job.step)
        chips = []
        for i, st in enumerate(STEPS):
            if not job.applies(st) or st == "assets" or (st == "segment" and not (job.options.split or job.options.review)):
                continue
            cls = "done" if i < cur or job.status == Status.done else ("cur " + status if i == cur else "")
            chips.append(f"<span class='step {cls}'>{step_label(job, st)}</span>")
        style = job.data.get("style_used") or job.data.get("style") or "auto"
        head = (f"<div class='card'><div style='display:flex;justify-content:space-between;align-items:center'>"
                f"<div><h2 style='margin:0'>{html.escape(Path(job.footage[0]).name)}</h2>"
                f"<div class='muted'><b>{MODE_VI[job_mode(job)]}</b> · {job.job_id} · kiểu dựng: {html.escape(style)} · "
                f"{html.escape(job.footage[0])}</div></div>"
                f"<span class='badge b-{status}'>{'<span class=spinner></span> ' if running else ''}{STATUS_VI[status]}</span>"
                f"</div><div class='stepper' style='margin-top:14px'>{''.join(chips)}</div>")
        if job.data.get("summary_vi"):
            head += f"<p><b>Nội dung:</b> {html.escape(job.data['summary_vi'])}</p>"
        parts = ["<div class='topnav'><a class='btn light small' href='/'>🏠 Về trang chủ</a>"
                 f"<span class='muted'>{'Đang chạy — có thể về trang chủ, job vẫn chạy tiếp' if running else ''}</span></div>",
                 head + "</div>"]
        stop_btn = (f"<form method='post' action='/jobs/{job_id}/stop' style='display:inline;margin-left:10px' "
                    "onsubmit=\"return confirm('Dừng job này? Bước đang chạy sẽ dừng ở điểm an toàn gần nhất; bấm Chạy tiếp "
                    "để chạy lại từ bước đó.')\"><button type='submit' class='btn danger small'>⏹️ Dừng</button></form>")
        if running:
            from app.jobs import stop as stop_mod

            waiting_turn = job.message.startswith("Đang đợi lượt")
            if stop_mod.requested(job_id):
                parts.append("<div class='card'><span class='spinner'></span> <b>Đang dừng…</b> (đợi bước hiện tại tới "
                             "điểm an toàn — phân tích video có thể mất thêm một lúc). Trang tự làm mới.</div>")
            else:
                parts.append(f"<div class='card'><span class='spinner'></span> "
                             + (f"{html.escape(job.message)}" if waiting_turn else
                                f"Đang <b>{step_label(job, job.step)}</b>…")
                             + f" Trang tự làm mới.{stop_btn}</div>")
        elif queued:
            parts.append(f"<div class='card'>⏳ <b>Đang xếp hàng</b> — đợi một luồng trống (đang chạy {len(worker.active)}/"
                         f"{max_jobs()} video). Có thể tăng số video chạy cùng lúc ở trang chủ.{stop_btn}</div>")
        else:
            parts.append(_step_panel(job, d))
        log = _read(d / "log.txt")
        if log:
            parts.append(f"<div class='card'><h2>📝 Nhật ký</h2><pre>{html.escape(log[-4000:])}</pre></div>")
        if not running and not queued:
            parts.append(_manage_panel(job))
        return _page(f"Job {job_id}", "".join(parts), refresh=running or queued)

    @app.post("/jobs/{job_id}/music")
    async def change_music(job_id: str, music: str = Form(""), music_file: UploadFile | None = File(None)):
        name = music.strip()
        if music_file is not None and music_file.filename:
            name = _save_user_music(music_file, Path(assets_root)) or name
        d = Job.dir_for(Path(jobs_root), job_id)
        if not list((d / "plan").glob("edit_plan_video*.json")):  # chưa lập kế hoạch: chỉ ghi lựa chọn, dùng ở bước sau
            job = Job.load(Path(jobs_root), job_id)
            job.data["music_choice"] = name or None
            job.save(Path(jobs_root))
        else:
            worker.start(job_id, action=lambda runner, job: runner.set_music(job, name))
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/shorten-dub")
    def shorten_dub(job_id: str):
        worker.start(job_id, action=lambda runner, job: runner.shorten_dub(job))
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/accept-dub")
    def accept_dub(job_id: str):
        worker.start(job_id, action=lambda runner, job: runner.accept_pending_dub(job))  # rồi worker tự chạy tiếp
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.get("/jobs/{job_id}/srt")
    def download_srt(job_id: str):
        job = Job.load(Path(jobs_root), job_id)
        p = Path(job.data.get("srt") or "")
        if not p.is_file():
            return RedirectResponse(f"/jobs/{job_id}", status_code=303)
        return FileResponse(p, filename=p.name, media_type="application/x-subrip")

    @app.post("/jobs/{job_id}/policy-keep")
    def policy_keep(job_id: str, keep: list[str] = Form([])):
        job = Job.load(Path(jobs_root), job_id)
        if job.status == Status.waiting:  # đang chờ duyệt (chưa lập kế hoạch): chỉ ghi lựa chọn, vẫn chờ như cũ
            job.data["policy_keep"] = sorted(set(keep))
            job.save(Path(jobs_root))
        else:
            worker.start(job_id, action=lambda runner, job: runner.set_policy_keep(job, keep))
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/vi-subs")
    def toggle_vi_subs(job_id: str, on: str = Form("1")):
        worker.start(job_id, action=lambda runner, job: runner.set_vi_subtitles(job, on == "1"))
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/stop")
    def stop_job(job_id: str):
        worker.stop(job_id)
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

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

    @app.post("/settings/parallel")
    def save_parallel(n: int = Form(3)):
        app_settings.save({"parallel_jobs": max(1, min(6, n))}, settings_path)
        with worker.lock:  # tăng số luồng: cho job đang xếp hàng chạy luôn
            starts = []
            while worker.queue and len(worker.active) < max_jobs():
                nxt = worker.queue.pop(0)
                worker.active.add(nxt[0])
                starts.append(nxt)
        for nxt in starts:
            threading.Thread(target=worker._work, args=nxt, daemon=True).start()
        return RedirectResponse("/", status_code=303)

    @app.post("/settings/cleanup")
    def save_cleanup(days: float = Form(2)):
        app_settings.save({"cleanup_days": max(0.0, min(30.0, days))}, settings_path)
        cleanup_now()
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

    @app.post("/jobs/{job_id}/dub-voice")
    async def upload_dub_voice(job_id: str, files: list[UploadFile] = File(...), video: int = Form(1)):
        """Voice thuyết minh: chọn nhiều file một lượt. Tên đúng videoNN_dubMM thì theo tên, còn lại theo thứ tự."""
        from app.planner import dub_io, hook_io

        d = Job.dir_for(Path(jobs_root), job_id)
        script = dub_io.load_dub(d, video)
        if script is None:
            return RedirectResponse(f"/jobs/{job_id}", status_code=303)
        good = [f for f in files if Path(f.filename or "").suffix.lower() in hook_io.VOICE_EXTS]
        bad = [f.filename for f in files if f not in good and f.filename]
        by_name = {f.filename: f for f in good}
        vdir = d / "voice"
        vdir.mkdir(parents=True, exist_ok=True)
        for name, n in dub_io.match_uploads([f.filename for f in good], video, len(script.lines)):
            base = dub_io.line_name(video, n)
            for old in vdir.glob(f"{base}.*"):
                old.unlink()
            with open(vdir / f"{base}{Path(name).suffix.lower()}", "wb") as out:
                shutil.copyfileobj(by_name[name].file, out)
        if bad:
            return _page("Lỗi", f"<div class='card'><h2>Có file không hợp lệ</h2><p>Chỉ nhận "
                         f"{', '.join(hook_io.VOICE_EXTS)}; đã bỏ qua: {html.escape(', '.join(bad))}</p>"
                         f"<p><a class='btn light' href='/jobs/{job_id}'>Quay lại</a></p></div>")
        worker.start(job_id)
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/dub-voice-all")
    async def upload_dub_voice_all(job_id: str, file: UploadFile = File(...), video: int = Form(1)):
        """Một file voice CẢ BÀI (nghỉ ~1 giây giữa các câu) → tool tự cắt ra từng câu."""
        from app.planner import dub_io, hook_io

        d = Job.dir_for(Path(jobs_root), job_id)
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in hook_io.VOICE_EXTS:
            return _page("Lỗi", f"<div class='card'><h2>File không hợp lệ</h2><p>Chỉ nhận {', '.join(hook_io.VOICE_EXTS)}.</p>"
                         f"<p><a class='btn light' href='/jobs/{job_id}'>Quay lại</a></p></div>")
        vdir = d / "voice"
        vdir.mkdir(parents=True, exist_ok=True)
        src = vdir / f"video{video:02d}_dub_all{suffix}"
        with open(src, "wb") as out:
            shutil.copyfileobj(file.file, out)
        try:
            dub_io.split_upload(d, video, src)
        except (ValueError, RuntimeError) as exc:
            return _page("Lỗi", f"<div class='card'><h2>Chưa cắt được file voice</h2><p>{html.escape(str(exc))}</p>"
                         f"<p><a class='btn light' href='/jobs/{job_id}'>Quay lại</a></p></div>")
        worker.start(job_id)
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/dub-skip")
    def dub_skip(job_id: str):
        job = Job.load(Path(jobs_root), job_id)
        job.data["dub_skip"] = True
        job.save(Path(jobs_root))
        worker.start(job_id)
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/redo")
    def redo(job_id: str, step: str = Form(...)):
        worker.start(job_id, action=lambda runner, job: runner.redo(job, step))
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    @app.post("/jobs/{job_id}/delete")
    def delete(job_id: str):
        d = Job.dir_for(Path(jobs_root), job_id)
        worker.remove_queued(job_id)
        if job_id not in worker.active and (d / "job.json").is_file():
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
    if (job.options.split or job.options.review) and STEPS.index(job.step) > STEPS.index("review_segments"):
        buttons.append(redo("segment", "✂️ Chia lại video",
                            "AI sẽ chia lại video; hook, kế hoạch và voice cũ sẽ phải làm lại. Tiếp tục?"))
    have_plan = STEPS.index(job.step) > STEPS.index("plan") or job.status == Status.done
    if have_plan:
        buttons.append(redo("write", "🔁 Dựng lại draft", "Ghi đè draft CapCut hiện tại? Đóng CapCut trước khi bấm."))
        buttons.append(redo("plan", "🎬 Lập lại kế hoạch dựng", "AI sẽ lập kế hoạch mới và dựng lại draft. Tiếp tục?"))
    if (job.options.target_language or job.options.review) and STEPS.index(job.step) > STEPS.index("dub"):
        buttons.append(redo("dub", "🌐 Viết lại thuyết minh", "AI viết lại câu thuyết minh; voice thuyết minh cũ phải thu "
                            "lại. Tiếp tục?"))
    if job.use_hook and STEPS.index(job.step) > STEPS.index("choose_hook"):
        buttons.append(redo("choose_hook", "🎣 Chọn hook khác"))
    if job.use_hook and STEPS.index(job.step) > STEPS.index("hooks"):
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


def _compare_card(original: str = "", back: str = "/") -> str:
    """Ô so sánh video gốc với video đã edit (đã xuất từ CapCut)."""
    esc = html.escape
    return f"""<div class="card"><h2>🔍 So sánh video gốc và video đã edit</h2>
    <p class="muted">Xuất video từ CapCut xong, chọn file gốc và file đã edit — tool ước lượng khác nhau bao nhiêu % về
    hình, tiếng và thời lượng (chạy trên máy, có thể mất 1–2 phút với video dài).</p>
    <form method="post" action="/compare">
      <input type="hidden" name="back" value="{esc(back)}">
      <div class="field"><label>Video gốc</label><div class="row">
        <input type="text" id="cmp_original" name="original" value="{esc(original)}" placeholder="Bấm Chọn file…" required>
        <button type="button" class="btn light" onclick="pickTo('cmp_original')">📂 Chọn file…</button></div></div>
      <div class="field"><label>Video đã edit (file xuất từ CapCut)</label><div class="row">
        <input type="text" id="cmp_edited" name="edited" placeholder="Bấm Chọn file…" required>
        <button type="button" class="btn light" onclick="pickTo('cmp_edited')">📂 Chọn file…</button></div></div>
      <button type="submit" class="btn">🔍 So sánh</button>
    </form>
    <script>
    async function pickTo(id){{
      try{{const r=await fetch('/api/pick-file');const d=await r.json();
        if(d.path) document.getElementById(id).value=d.path; else if(d.error) alert(d.error);}}
      catch(e){{alert('Không mở được hộp thoại: '+e);}}
    }}
    </script></div>"""


def _compare_result_html(r, original: Path, edited: Path, back: str) -> str:
    esc = html.escape

    def bar(pct: float) -> str:
        color = "#16a34a" if pct >= 60 else ("#d97706" if pct >= 35 else "#dc2626")
        return (f"<div style='background:#e5e7eb;border-radius:6px;height:12px;width:100%'><div style='width:{pct:.0f}%;"
                f"height:12px;border-radius:6px;background:{color}'></div></div>")

    rows = [("🖼️ Hình ảnh", r.visual_diff, f"{r.visual_matched:.0f}% khung hình của bản edit gần như trùng một khung gốc"
             + (f" (trong đó {r.mirrored_share:.0f}% là cảnh lật ngang)" if r.mirrored_share else "")),
            ("🔊 Âm thanh", r.audio_diff, "đường âm lượng so theo từng đoạn 3 giây" if r.audio_diff is not None
             else "không đo được"),
            ("⏱️ Thời lượng", r.duration_diff, f"gốc {r.original_s:.0f}s → edit {r.edited_s:.0f}s")]
    body = "".join(f"<tr><td><b>{name}</b></td><td style='width:45%'>{bar(v) if v is not None else '—'}</td>"
                   f"<td><b>{'' if v is None else f'{v:.0f}%'}</b></td><td class='muted'>{esc(note)}</td></tr>"
                   for name, v, note in rows)
    verdict = ("Khác rất nhiều so với bản gốc." if r.overall >= 70 else "Khác khá nhiều so với bản gốc." if r.overall >= 50
               else "Còn khá giống bản gốc — có thể dựng lại mạnh tay hơn (đổi khung, zoom, nhạc, thứ tự lời dẫn…).")
    notes = "".join(f"<p class='muted'>{esc(n)}</p>" for n in r.notes)
    return (f"<div class='topnav'><a class='btn light small' href='{esc(back)}'>← Quay lại</a></div>"
            f"<div class='card'><h2>🔍 Kết quả so sánh</h2>"
            f"<p class='muted'>Gốc: {esc(str(original))}<br>Edit: {esc(str(edited))}</p>"
            f"<div style='font-size:42px;font-weight:800'>{r.overall:.0f}% <span style='font-size:18px;font-weight:600'>"
            f"khác bản gốc</span></div><p>{verdict}</p>{bar(r.overall)}"
            f"<table style='margin-top:14px'><tr><th>Phần</th><th></th><th>Khác</th><th>Chi tiết</th></tr>{body}</table>"
            f"{notes}<div class='note'>Đây là ước lượng mức khác biệt về hình và tiếng để bạn tự đánh giá bản edit (tổng = 60% "
            "hình + 30% tiếng + 10% thời lượng). Đây KHÔNG phải cách TikTok chấm điểm và không bảo đảm gì về phân phối "
            "video.</div></div>")


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


def _save_user_music(upload, assets_root: Path) -> str | None:
    """File nhạc người dùng tải lên khi tạo job → assets/music/tu_chon/ + sổ nguồn. Trả tên bài trong kho."""
    from app.assets import ledger
    from app.assets.freesound import slug
    from app.assets.local import AUDIO_EXTS

    ext = Path(upload.filename or "").suffix.lower()
    if ext not in AUDIO_EXTS:
        return None
    folder = Path(assets_root) / "music" / "tu_chon"
    folder.mkdir(parents=True, exist_ok=True)
    stem = slug(Path(upload.filename).stem) or "nhac"
    out = folder / f"{stem}{ext}"
    with open(out, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    ledger.add(assets_root, out, source="user", license="người dùng tự thêm (tự xác nhận quyền dùng)",
               extra={"original_name": upload.filename, "kind": "music", "tag": "tu_chon"})
    return f"tu_chon_{out.stem}"  # cùng cách đặt tên của scan_local: <nhóm>_<tên file>


def _load_library():
    """Kho tài nguyên (dự án mẫu + mọi dự án CapCut + kho local). Trả (template, lỗi)."""
    try:
        from app.jobs.runner import Runner

        return Runner(JOBS_ROOT, log=lambda m: None)._template(), None
    except Exception as exc:
        return None, str(exc)


def _music_select(tpl) -> str:
    """Ô chọn nhạc nền khi tạo job: mặc định AI tự chọn; hoặc chọn một bài trong kho; hoặc tải file nhạc của bạn."""
    esc = html.escape
    items = [m for m in (tpl.library if tpl else []) if m.kind == "music"]
    groups: dict[str, list] = {}
    for m in sorted(items, key=lambda m: m.name.lower()):
        groups.setdefault("Kho của bạn (assets)" if m.material.get("local") else "Nhạc CapCut", []).append(m)
    opts = "".join(
        f"<optgroup label='{esc(g)}'>" + "".join(
            f"<option value='{esc(m.name)}'>{esc(m.name)} · {m.material.get('duration', 0) / 1e6:.0f}s"
            f"{' · ' + esc(m.mood) if m.mood else ''}{' · Commercial' if m.commercial else ''}</option>" for m in ms)
        + "</optgroup>" for g, ms in groups.items())
    return (f"<div class='field'><label>🎵 Nhạc nền</label><select name='music'>"
            f"<option value=''>✨ AI tự chọn theo nội dung</option>{opts}</select>"
            "<div class='row' style='margin-top:6px'><input type='file' name='music_file' accept='.mp3,.wav,.m4a,audio/*'>"
            "</div><div class='muted'>Hoặc tải lên file nhạc của bạn (tự thêm vào kho, dùng cho video này). "
            "Để trống cả hai = AI tự chọn.</div></div>")


def _library_summary(tpl=None, err: str | None = None) -> str:
    """Số nhạc / SFX / hiệu ứng đạo diễn có thể dùng (tự quét mọi dự án CapCut trên máy)."""
    if tpl is None and err is None:
        tpl, err = _load_library()
    if tpl is None:
        return f"<p class='muted'>Chưa đọc được dự án mẫu CapCut: {html.escape(str(err))}</p>"
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


def pick_file_dialog(multiple: bool = False, dialog=None) -> dict:
    """Mở hộp thoại chọn file của Windows ngay trên máy chạy tool (server và trình duyệt cùng một máy).
    multiple=True: chọn NHIỀU file một lúc (giữ Ctrl / Shift trong hộp thoại) — tkinter askopenfilenames."""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return {"error": "Máy không có tkinter, hãy dán đường dẫn file."}
    try:
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        types = [("Video", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v"), ("Tất cả", "*.*")]
        fd = dialog or filedialog
        if multiple:
            raw = fd.askopenfilenames(title="Chọn file footage (giữ Ctrl hoặc Shift để chọn nhiều file)", filetypes=types)
            paths = list(root.tk.splitlist(raw)) if raw else []  # Tk cũ có thể trả chuỗi thay vì tuple
        else:
            one = fd.askopenfilename(title="Chọn file footage", filetypes=types)
            paths = [one] if one else []
        root.destroy()
    except Exception as exc:
        return {"error": f"Không mở được hộp thoại chọn file: {exc}"}
    paths = [str(Path(p)) for p in paths if p]
    return {"path": paths[0] if paths else "", "paths": paths}


def _policy_html(d: Path, start: float = 0.0, end: float = 1e9, job: Job | None = None, form: bool = True) -> str:
    """Bảng các đoạn AI cho là vi phạm chính sách TikTok (trong khoảng start–end của footage). Có job + form: tick để
    GIỮ LẠI đoạn đó (người dùng tự chịu trách nhiệm), mặc định là cắt bỏ."""
    from app.director.policy import policy_key
    from app.director.schemas import POLICY_VI

    data = json.loads(_read(d / "plan" / "understanding.json") or "{}")
    rows = [p for p in data.get("policy_issues") or [] if p["end"] > start and p["start"] < end]
    if not rows:
        return ""
    esc = html.escape
    keep = set((job.data.get("policy_keep") if job else None) or [])
    n_keep = sum(policy_key(p) in keep for p in rows)
    editable = job is not None and form

    def row(p) -> str:
        k = policy_key(p)
        tick = (f"<td><input type='checkbox' name='keep' value='{esc(k)}' {'checked' if k in keep else ''}></td>"
                if editable else f"<td>{'✅ giữ' if k in keep else '✂️ cắt'}</td>")
        return (f"<tr>{tick}<td>{p['start']:.1f}–{p['end']:.1f}s</td>"
                f"<td>{esc(POLICY_VI.get(p['category'], p['category']))}</td>"
                f"<td>{esc(p.get('reason_vi', ''))}{' <span class=muted>(máy tự dò)</span>' if p.get('auto') else ''}</td></tr>")

    head = f"<tr><th>{'Giữ lại' if editable else ''}</th><th>Giây</th><th>Loại</th><th>Lý do</th></tr>"
    table = f"<table>{head}{''.join(row(p) for p in rows)}</table>"
    summary = (f"🚫 Đoạn AI cho là vi phạm chính sách TikTok — cắt {len(rows) - n_keep}"
               + (f", giữ lại {n_keep}" if n_keep else ""))
    if not editable:
        return (f"<details><summary><b>{summary}</b></summary>{table}"
                "<p class='muted'>Muốn giữ lại đoạn nào: chọn ở khung này trên trang job sau bước duyệt.</p></details>")
    return (f"<details {'open' if n_keep else ''}><summary><b>{summary}</b></summary>"
            f"<form method='post' action='/jobs/{job.job_id}/policy-keep' onsubmit=\"return confirm('Giữ lại các đoạn đã "
            "tick? Video có thể bị TikTok hạn chế / gỡ — bạn tự chịu trách nhiệm. Nếu đã có kế hoạch dựng, tool sẽ lập lại "
            "kế hoạch (voice thuyết minh cũ được cất thành *_cu).')\">"
            f"{table}<p class='muted'>Mặc định các đoạn này bị CẮT. Tick ô <b>Giữ lại</b> nếu AI đánh dấu nhầm hoặc bạn "
            "vẫn muốn giữ (bạn tự chịu trách nhiệm với TikTok).</p>"
            "<button type='submit' class='btn small light'>💾 Lưu: giữ lại các đoạn đã tick</button></form></details>")


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
            + _policy_html(d, job=job, form=False)
            + "<p><button type='submit' class='btn'>✅ Xác nhận và dựng tiếp</button></p></form></div>")


def _dub_panel(job: Job, d: Path, skip: bool = True) -> str:
    """Chờ voice thuyết minh: kịch bản từng câu + ô tải nhiều file cho từng video + nút bỏ qua."""
    from app.planner import dub_io

    esc = html.escape
    forms = []
    for p in sorted((d / "plan").glob("dub_video*.json")):
        v = int(p.stem.replace("dub_video", ""))
        script = dub_io.load_dub(d, v)
        rows = []
        windows = dub_io.windows_for(d, v, script)
        dcfg = app_config.load("dub")
        max_speed = float(dcfg.get("max_speed", 1.25))
        delay = float(dcfg.get("max_delay_s", 0.8))  # câu được trễ tối đa chừng này (chống đè tiếng)
        icons = {"ok": "🟢", "fast": "🟡", "short": "⚪", "long": "🔴"}
        n_long = 0
        for i, ln in enumerate(script.lines, 1):
            have = dub_io.find_line_voice(d, v, i)
            win = windows[i - 1] if i - 1 < len(windows) else None
            slot = (f"chỗ {win[1]:.1f}s · tối đa {win[2]:.1f}s" if win else f"~{ln.source_end - ln.source_start:.1f}s")
            fit = ""
            if script.story_vi:  # review: hình tự co / giãn theo giọng — đọc theo nhịp tự nhiên của bạn
                slot = "đọc theo nhịp của bạn · hình tự co / giãn khớp giọng"
                secs = dub_io.voice_seconds(have) if have else None
                if secs is not None:
                    fit = f"<br><span class='muted'>🟢 voice {secs:.1f}s — cảnh của câu này sẽ dài đúng {secs:.1f}s</span>"
            elif have and win:
                secs = dub_io.voice_seconds(have)
                if secs is not None:
                    level, msg = dub_io.fit_status(secs, win[1], win[2] + delay, max_speed)
                    n_long += level == "long"
                    fit = f"<br><span class='muted'>{icons[level]} {esc(msg)}</span>"
            rows.append(f"<tr><td>{'✅' if have else '❌'}</td><td><b>{esc(dub_io.line_name(v, i))}</b><br>"
                        f"<span class='muted'>{slot}</span></td>"
                        f"<td>{('<span class=tag>🗣️ lời dẫn: ' + esc(ln.action_vi) + '</span> ') if ln.kind == 'narration' else ''}"
                        f"{esc(ln.text)}"
                        f"<br><span class='muted'>🇻🇳 {esc(ln.text_vi)}</span>"
                        + (f"<br><span class='muted'>🌏 Bản địa hóa: {esc(ln.adapt_vi)}</span>" if ln.adapt_vi else "")
                        + fit + "</td></tr>")
        rate = dub_io.voice_rate(d, v, script)
        tools = ""
        if rate:
            tools += (f"<p class='muted'>🎚️ Giọng bạn đọc ~{rate:.1f} ký tự/giây — tool nhớ tốc độ này để lần sau AI viết câu "
                      "vừa giọng.</p>")
        if n_long:
            tools += (f"<form method='post' action='/jobs/{job.job_id}/shorten-dub' onsubmit=\"return confirm('AI sẽ viết lại "
                      f"ngắn hơn {n_long} câu 🔴 (các câu khác giữ nguyên). Voice cũ của các câu đó được cất thành *_cu, "
                      "bạn thu lại đúng các câu này. Tiếp tục?')\"><button type='submit' class='btn small'>"
                      f"✂️ Viết gọn {n_long} câu 🔴 (AI viết lại ngắn hơn)</button></form>")
        done = sum(1 for i in range(1, len(script.lines) + 1) if dub_io.find_line_voice(d, v, i))
        whole = ""
        if script.story_vi:  # review: bài lời đọc viết trước — đọc liền một mạch, tool dựng cảnh theo voice
            sep = "" if job.options.target_language == "ja" else " "
            whole = (f"<div class='card' style='background:#f7f7ff'><b>📜 Bài lời đọc — đọc LIỀN MỘT MẠCH, nghỉ ~1 giây "
                     f"giữa các câu, rồi tải lên ô <u>Một file cả bài</u></b>"
                     f"<p style='font-size:1.15em;line-height:1.7'>{esc(sep.join(ln.text.strip() for ln in script.lines))}</p>"
                     f"<p class='muted'>🇻🇳 {esc(' '.join(ln.text_vi.strip() for ln in script.lines))}</p>"
                     f"<p class='muted'>📖 {esc(script.story_vi)}</p>"
                     "<p class='muted'>Tool đo từng câu bạn đọc rồi tự cắt cảnh của đúng đoạn phim câu đó kể, dài đúng bằng câu "
                     "— đọc nhanh hay chậm đều khớp.</p></div>")
        forms.append(
            f"<h2 style='margin-top:14px'>🎬 Video {v:02d} — đã có {done}/{len(script.lines)} câu</h2>{whole}"
            f"<details {'open' if done < len(script.lines) else ''}><summary>Kịch bản thuyết minh</summary>"
            f"<table><tr><th></th><th>File</th><th>Câu cần thu</th></tr>{''.join(rows)}</table></details>{tools}"
            f"<form class='upload' method='post' action='/jobs/{job.job_id}/dub-voice' enctype='multipart/form-data'>"
            f"<input type='hidden' name='video' value='{v}'>"
            f"<input type='file' name='files' accept='.wav,.mp3,.m4a,audio/*' multiple required>"
            f"<br><button type='submit' class='btn small'>📤 Tải lên (chọn nhiều file một lượt)</button></form>"
            f"<form class='upload' method='post' action='/jobs/{job.job_id}/dub-voice-all' enctype='multipart/form-data'>"
            f"<input type='hidden' name='video' value='{v}'>"
            f"<b>Hoặc một file cả bài</b> <span class='muted'>(đọc hết các câu theo thứ tự, nghỉ ~1 giây giữa các câu — "
            f"tool tự cắt ra {len(script.lines)} câu)</span><br>"
            f"<input type='file' name='file' accept='.wav,.mp3,.m4a,audio/*' required>"
            f"<br><button type='submit' class='btn small'>✂️ Tải lên và tự cắt</button></form>")
    return (f"<div class='card'><h2>🎙️ Thu voice thuyết minh</h2><p>Thu từng câu bằng Voice Studio, đặt tên file đúng như "
            "cột File (vd <b>video01_dub01.wav</b>) rồi chọn tất cả tải lên một lượt. Nếu file đặt tên kiểu 1.wav, 2.wav… "
            "tool tự xếp theo thứ tự vào các câu còn thiếu. Đủ file là tool tự dựng tiếp.</p>"
            "<p class='muted'>Video nói liên tục (hướng dẫn trang điểm…): đọc cả kịch bản một lượt vào MỘT file, nghỉ ~1 giây "
            "giữa các câu, tải ở ô <b>Một file cả bài</b>. Sau khi tải, mỗi câu có đèn: 🟢 khớp · 🟡 hơi dài, tool tự tăng tốc "
            "nhẹ · ⚪ ngắn (có khoảng im) · 🔴 quá dài — thu lại riêng câu đó (tải file tên đúng videoNN_dubMM ở ô trên).</p>"
            f"{''.join(forms)}<p class='muted'>"
            f"{esc(job.message) if skip else 'Tải thêm voice xong, bấm 🔁 Dựng lại draft ở khung Thao tác.'}</p>"
            + (f"<form method='post' action='/jobs/{job.job_id}/dub-skip' onsubmit=\"return confirm('Dựng luôn khi chưa đủ "
               "voice? Câu thiếu voice vẫn có phụ đề, giữ tiếng gốc. Tải voice sau rồi bấm Dựng lại draft.')\">"
               "<button type='submit' class='btn light small'>⏭️ Dựng luôn (câu thiếu voice chỉ có phụ đề)</button></form>"
               if skip else "") + "</div>")


def _pending_dub_html(job: Job, d: Path) -> str:
    """AI viết thuyết minh 3 lần vẫn còn lỗi nhỏ: cho chọn dùng luôn bản gần nhất (không hỏi lại AI)."""
    pend = sorted((d / "plan").glob("pending_dub_video*.json"))
    if not pend:
        return ""
    esc = html.escape
    items = []
    for p in pend:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        v = p.stem.replace("pending_dub_video", "")
        probs = data.get("problems", [])
        items.append(f"<p><b>Video {esc(v)}</b> — {len(data.get('script', {}).get('lines', []))} câu, còn "
                     f"{len(probs)} lỗi:</p><ul>" + "".join(f"<li>{esc(x)}</li>" for x in probs[:8])
                     + ("<li>…</li>" if len(probs) > 8 else "") + "</ul>")
    return ("<div class='card' style='margin:10px 0'><b>🛟 Tùy chọn: dùng bản thuyết minh gần nhất</b>"
            "<p class='muted'>AI đã sửa 3 lần nhưng vẫn còn vài lỗi nhỏ (thường là vài câu hơi nhiều chữ so với chỗ trống). "
            "Bạn có thể dùng luôn bản này: câu dài sẽ được tăng tốc nhẹ khi dựng, câu nào vẫn tràn sẽ có đèn 🔴 để bạn "
            "thu gọn lại. Hoặc bấm <b>Chạy lại bước này</b> để AI viết lại (mất thêm vài phút và hạn mức Claude).</p>"
            + "".join(items)
            + f"<form method='post' action='/jobs/{job.job_id}/accept-dub'><button type='submit' class='btn'>"
            "✅ Dùng bản này, bỏ qua lỗi còn lại</button></form></div>")


def _step_panel(job: Job, d: Path) -> str:
    esc = html.escape
    if job.status == Status.error:
        return (f"<div class='card'><h2>⚠️ Có lỗi</h2><pre>{esc(job.message)}</pre>"
                f"{_pending_dub_html(job, d)}{_continue_button(job, 'Chạy lại bước này')}</div>")
    if job.status == Status.stopped:
        return (f"<div class='card'><h2>⏹️ Đã dừng</h2><p>Dừng ở bước <b>{esc(step_label(job, job.step))}</b>. "
                "Kết quả các bước trước vẫn giữ nguyên.</p>"
                f"{_continue_button(job, '▶️ Chạy tiếp từ bước này')}</div>")
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
                    f"</span>"
                    + (f"<div class='muted'>💬 Câu dẫn: {esc(o.intro)}<br>🇻🇳 {esc(o.intro_vi)}</div>" if o.intro else "")
                    + f"<div class='line'>{esc(o.line)}</div><div>🇻🇳 {esc(o.line_vi)}</div>"
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
    if job.status == Status.waiting and job.step == "dub_voice":
        return _dub_panel(job, d)
    if job.status == Status.waiting:
        extra = ""
        u = d / "plan" / "understanding.json"
        if job.step == "confirm_genre" and u.is_file():
            data = json.loads(_read(u))
            extra = (f"<p>Phong cách đề xuất: {esc(data.get('suggested_style', ''))}</p>"
                     f"<p>Ghi chú editor: {esc(data.get('editor_notes', ''))}</p>{_policy_html(d, job=job)}")
        return f"<div class='card'><pre>{esc(job.message)}</pre>{extra}{_continue_button(job)}</div>"
    if job.status == Status.done:
        drafts = job.data.get("drafts") or [{"index": 1, "draft": job.data.get("draft", ""),
                                             "duration_s": job.data.get("duration_s", "?")}]
        parts = [f"<div class='card'><h2>✅ Xong — {len(drafts)} video</h2><p>Mở CapCut để xem, chỉnh và xuất từng draft.</p>"]
        if job.data.get("srt"):
            parts.append(f"<p>🇻🇳 <b>Phụ đề tiếng Việt:</b> <a class='btn small' href='/jobs/{job.job_id}/srt'>⬇️ Tải file .srt</a> "
                         f"<span class='muted'>({esc(job.data['srt'])}) — để cùng thư mục, cùng tên với video gốc rồi mở "
                         "bằng VLC / PotPlayer / Phim & TV là xem được ngay; hoặc mở draft CapCut (phụ đề đã gắn sẵn).</span></p>")
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
            if dr.get("start") is not None:
                parts.append(_policy_html(d, float(dr["start"]), float(dr["end"]), job=job))
            cap = _read(d / "deliver" / f"video{i:02d}_captions.txt")
            if cap:
                parts.append(f"<details><summary><b>📣 Caption + hashtag</b></summary><pre>{esc(cap)}</pre></details>")
        cur = job.data.get("music_choice") or "AI tự chọn"
        lib, _ = _load_library()
        parts.append(f"<details><summary><b>🎵 Đổi nhạc nền</b> <span class='muted'>(đang: {esc(cur)})</span></summary>"
                     f"<form method='post' action='/jobs/{job.job_id}/music' enctype='multipart/form-data'>"
                     f"{_music_select(lib)}<p class='muted'>Chọn bài khác → tool chỉ dựng lại draft (không hỏi lại AI). "
                     "Chọn 'AI tự chọn' → AI lập lại kế hoạch dựng.</p>"
                     "<button type='submit' class='btn small'>🎵 Đổi nhạc và dựng lại</button></form></details>")
        parts.append("<details><summary><b>🔍 So sánh với video gốc (sau khi xuất từ CapCut)</b></summary>"
                     + _compare_card(job.footage[0], f"/jobs/{job.job_id}") + "</details>")
        if list((d / "plan").glob("dub_video*.json")):
            vi_on = bool(job.data.get("vi_subs", (app_config.load("dub").get("vi_subtitles") or {}).get("enabled", True)))
            parts.append(
                f"<div class='card' style='margin:10px 0'><b>🇻🇳 Phụ đề tiếng Việt để kiểm tra:</b> "
                f"{'<span class=tag>đang BẬT</span>' if vi_on else '<span class=tag>đang TẮT</span>'}"
                "<p class='muted'>Chữ vàng nhỏ ngay dưới phụ đề chính = nghĩa tiếng Việt của câu thuyết minh đang nói, "
                "để bạn xem voice và phụ đề đã khớp hình chưa. <b>Tắt rồi mới xuất video đăng TikTok.</b></p>"
                f"<form method='post' action='/jobs/{job.job_id}/vi-subs'><input type='hidden' name='on' "
                f"value='{'0' if vi_on else '1'}'><button type='submit' class='btn small light'>"
                f"{'🚫 Tắt phụ đề tiếng Việt và dựng lại' if vi_on else '🇻🇳 Bật phụ đề tiếng Việt và dựng lại'}"
                "</button></form></div>")
            parts.append("<details><summary><b>🎙️ Voice thuyết minh (xem kịch bản / tải thêm)</b></summary>"
                         + _dub_panel(job, d, skip=False) + "</details>")
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
