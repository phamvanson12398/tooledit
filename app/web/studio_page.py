"""Tab "🎙️ Voice Studio" (chủ dự án yêu cầu 16/10): OmniVoice của tool dùng như tool TTS — giọng mẫu + chữ → file đọc,
thư viện giọng mẫu lưu lại, đủ thông số sinh. Logic ở app/tts/studio.py."""

from __future__ import annotations

import html
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from urllib.parse import quote

from app.tts import studio as st

esc = html.escape


def _param_inputs(params: dict) -> str:
    rows = []
    for k, label, kind, dflt, lo, hi, step, help_vi in st.PARAMS:
        v = params.get(k, dflt)
        if kind == "bool":
            field = f"<input type='checkbox' name='{k}' {'checked' if v else ''}>"
        else:
            field = (f"<input type='number' name='{k}' value='{v}' min='{lo}' max='{hi}' step='{step}' "
                     f"style='width:8em'>")
        rows.append(f"<tr><td><b>{esc(label)}</b><br><span class='muted'>{esc(help_vi)} "
                    f"<i>(mặc định {dflt})</i></span></td><td>{field}</td></tr>")
    return "<table class='params'>" + "".join(rows) + "</table>"


def _voice_options(voices: list[dict], selected: str = "") -> str:
    opts = ["<option value=''>— Không dùng giọng thư viện —</option>"]
    for v in voices:
        kind = "🎤 mẫu" if v.get("mode") == "clone" else "📝 mô tả"
        opts.append(f"<option value='{esc(v['slug'])}' {'selected' if v['slug'] == selected else ''}>"
                    f"{esc(v['name'])} ({kind})</option>")
    return "".join(opts)


def _lang_options(selected: str = "auto") -> str:
    return "".join(f"<option value='{k}' {'selected' if k == selected else ''}>{esc(v)}</option>"
                   for k, v in st.LANGS.items())


def register(app: FastAPI, page, *, root: Path | None = None, settings_path: Path | None = None, run_worker=None,
             tts_cfg=None) -> None:
    root = Path(root or st.STUDIO)
    run = st.StudioRun()
    app.state.studio = run

    def cfg() -> dict:
        if tts_cfg is not None:
            return tts_cfg()
        from app.tts.voices import load_cfg

        return load_cfg()

    def save_upload(up: UploadFile) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="studio_"))
        dst = tmp / Path(up.filename or "mau.wav").name
        with open(dst, "wb") as f:
            shutil.copyfileobj(up.file, f)
        return dst

    @app.get("/studio", response_class=HTMLResponse)
    def studio_page(voice: str = "", msg: str = ""):
        voices = st.list_voices(root)
        params = st.load_params(settings_path)
        c = cfg()
        lib_rows = []
        for v in voices:
            sample = (f"<audio controls preload='none' src='/studio/file/voices/{esc(v['slug'])}/sample.wav'></audio>"
                      if v.get("sample_path") else f"<span class='muted'>📝 {esc(v.get('instruct', ''))}</span>")
            lib_rows.append(
                f"<tr><td><b>{esc(v['name'])}</b><br><span class='muted'>{esc(st.LANGS.get(v.get('language'), ''))}"
                f"{' · ' + esc(v['note']) if v.get('note') else ''}"
                f"{' · lời mẫu: ' + esc(v['ref_text'][:60]) if v.get('ref_text') else ''}</span><br>{sample}</td>"
                f"<td><a class='btn small light' href='/studio?voice={esc(v['slug'])}'>Dùng</a>"
                f"<form method='post' action='/studio/voices/{esc(v['slug'])}/delete' "
                f"onsubmit=\"return confirm('Xóa giọng mẫu {esc(v['name'])}?')\" style='margin-top:4px'>"
                "<button class='btn small light' type='submit'>🗑️</button></form></td></tr>")
        hist = []
        for h in st.history(root):
            hist.append(f"<tr><td><audio controls preload='none' src='/studio/file/outputs/{esc(h['file'])}'></audio>"
                        f"<br><a href='/studio/file/outputs/{esc(h['file'])}' download>⬇️ {esc(h['file'])}</a></td>"
                        f"<td>{esc((h.get('text') or '')[:140])}<br><span class='muted'>{esc(h.get('voice_name', ''))}"
                        f" · {esc(h.get('created', ''))}</span></td></tr>")
        body = f"""
        <div class='topnav'><a class='btn light small' href='/'>🏠 Về trang chủ</a>
        <span class='muted'>OmniVoice: {esc(str(c.get('model', '')))} · python: {esc(str(c.get('python') or 'của tool'))}
        (đổi ở trang chủ → ⚙️ Cài đặt → 🤖 OmniVoice)</span></div>
        {f"<div class='note'>{esc(msg)}</div>" if msg else ""}
        <div class='grid'><div>
        <style>.studio label{{display:block;margin-top:6px}}.studio details{{margin-top:8px}}</style>
        <form class='card studio' method='post' action='/studio/generate' enctype='multipart/form-data'>
          <h2>🎙️ Voice Studio — đọc chữ bằng giọng mẫu</h2>
          <label>1️⃣ Giọng đọc</label>
          <select name='voice'>{_voice_options(voices, voice)}</select>
          <details {'open' if not voices else ''} style='margin-top:8px'><summary>➕ Giọng mẫu mới (tải file, tự lưu vào
          thư viện)</summary>
            <input type='file' name='sample' accept='audio/*,.wav,.mp3,.m4a'>
            <input type='text' name='new_name' placeholder='Tên giọng (vd: Nam trầm kênh A)' style='width:100%;margin-top:6px'>
            <input type='text' name='ref_text' placeholder='Lời đọc trong file mẫu (không bắt buộc — để trống thì OmniVoice tự nhận dạng)' style='width:100%;margin-top:6px'>
            <div class='muted'>Mẫu tốt nhất 3–10 giây, một người nói, không nhạc nền. Dài hơn
            {float(c.get('studio_max_ref_s', 15)):.0f} giây thì lấy đoạn đầu.</div>
          </details>
          <label style='margin-top:8px'>hoặc 📝 Mô tả giọng (không cần file mẫu)</label>
          <input type='text' name='instruct' style='width:100%' placeholder='vd: female, young adult, high pitch  (tiếng Anh, cách nhau dấu phẩy)'>
          <label style='margin-top:6px'><input type='checkbox' name='save_design'> Lưu mô tả này vào thư viện với tên ở ô
          "Tên giọng"</label>
          <label style='margin-top:6px'><input type='checkbox' name='consent'> Tôi xác nhận <b>có quyền dùng giọng mẫu
          này</b> (giọng của tôi / đã được người đó cho phép)</label>
          <label style='margin-top:12px'>2️⃣ Chữ cần đọc</label>
          <textarea name='text' rows='6' style='width:100%' required placeholder='Gõ hoặc dán chữ cần đọc…'></textarea>
          <label><input type='checkbox' name='per_line'> Mỗi dòng một file riêng</label>
          <label style='margin-top:8px'>🌐 Ngôn ngữ</label><select name='language'>{_lang_options()}</select>
          <details style='margin-top:10px'><summary>⚙️ 3️⃣ Thông số OmniVoice (đủ mọi tham số)</summary>
            {_param_inputs(params)}
            <label><input type='checkbox' name='remember'> Lưu các thông số này làm mặc định</label>
          </details>
          <div class='go'><button type='submit' class='btn big'>🔊 Đọc</button></div>
        </form>
        <div class='card'><h2>⏳ Tiến độ</h2><div id='status' class='muted'>Chưa chạy.</div>
          <form method='post' action='/studio/stop'><button class='btn small light' type='submit'>⏹️ Dừng</button></form>
        </div>
        <div class='card'><h2>🎧 File đã đọc</h2><table>{''.join(hist) or "<tr><td class='muted'>Chưa có.</td></tr>"}</table></div>
        </div>
        <div class='side'><div class='card'><h2>📚 Thư viện giọng mẫu</h2>
          <table>{''.join(lib_rows) or "<tr><td class='muted'>Chưa có giọng nào — tải file mẫu ở ô bên trái.</td></tr>"}</table>
          <p class='muted'>Lưu ở thư mục <b>studio\\voices</b> trong tool. Giọng mẫu được xử lý một lần rồi giữ lại
          (prompt.pt) nên lần đọc sau nhanh hơn.</p></div></div></div>
        <script>
        async function poll(){{try{{const r=await fetch('/studio/status');const s=await r.json();
          const el=document.getElementById('status');
          el.innerHTML=(s.running?'<span class="spinner"></span> Đang đọc… ':'')+
            (s.log||[]).slice(-8).map(x=>x.replace(/&/g,'&amp;').replace(/</g,'&lt;')).join('<br>');
          if(window._wasRunning&&!s.running) location.reload(); window._wasRunning=s.running;}}catch(e){{}}}}
        poll(); setInterval(poll,2000);
        </script>"""
        return page("Voice Studio", body)

    @app.get("/studio/status")
    def studio_status():
        return JSONResponse(run.snapshot())

    @app.post("/studio/stop")
    def studio_stop():
        run.stop()
        return RedirectResponse("/studio", status_code=303)

    @app.post("/studio/generate")
    async def studio_generate(request: Request, text: str = Form(...), voice: str = Form(""),
                              language: str = Form("auto"), instruct: str = Form(""), new_name: str = Form(""),
                              ref_text: str = Form(""), sample: UploadFile | None = File(None)):
        form = await request.form()
        params = st.clean_params(dict(form), st.load_params(settings_path))
        if form.get("remember"):
            st.save_params(params, settings_path)
        consent = bool(form.get("consent"))
        try:
            v = st.get_voice(voice, root) if voice else None
            if sample is not None and sample.filename:  # giọng mẫu mới → lưu thư viện rồi dùng luôn
                v = st.save_voice(new_name.strip() or Path(sample.filename).stem, sample=save_upload(sample),
                                  ref_text=ref_text, language=language, consent=consent, root=root,
                                  max_ref_s=float(cfg().get("studio_max_ref_s", 15)))
                v = st.get_voice(v["slug"], root)
            elif instruct.strip() and form.get("save_design"):
                v = st.save_voice(new_name.strip() or instruct.strip()[:30], instruct=instruct, language=language,
                                  root=root)
                v = st.get_voice(v["slug"], root)
            if v and v.get("mode") == "clone" and not (v.get("consent") or consent):
                raise ValueError("Giọng mẫu này chưa được xác nhận quyền dùng — tick ô xác nhận rồi đọc lại.")
            texts = st.split_texts(text, bool(form.get("per_line")))
            if not texts:
                raise ValueError("Chưa có chữ cần đọc.")
        except ValueError as exc:
            return RedirectResponse(f"/studio?msg={quote(str(exc))}", status_code=303)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        req = st.build_request(cfg(), voice=v, texts=texts, language=language, params=params,
                               out_dir=st.outputs_dir(root), stamp=stamp, instruct="" if v else instruct)
        meta = {"voice_name": (v or {}).get("name") or (f"mô tả: {instruct}" if instruct.strip() else "OmniVoice tự chọn"),
                "language": language, "params": params}
        if not run.start(req, meta, root, run_worker, cfg()):
            return RedirectResponse("/studio?msg=" + quote("Đang đọc lượt trước — đợi xong hoặc bấm Dừng."),
                                    status_code=303)
        return RedirectResponse(f"/studio?voice={quote((v or {}).get('slug', ''))}", status_code=303)

    @app.post("/studio/voices/{slug_name}/delete")
    def studio_delete(slug_name: str):
        st.delete_voice(slug_name, root)
        return RedirectResponse("/studio", status_code=303)

    @app.get("/studio/file/{kind}/{rel:path}")
    def studio_file(kind: str, rel: str):
        base = st.voices_dir(root) if kind == "voices" else st.outputs_dir(root) if kind == "outputs" else None
        p = st.safe_file(base, rel) if base is not None else None
        if p is None or p.suffix.lower() not in (".wav", ".mp3", ".m4a"):
            return HTMLResponse("Không thấy file", status_code=404)
        return FileResponse(p, filename=p.name, media_type="audio/wav")
