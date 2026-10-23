"""VOICE STUDIO (chủ dự án yêu cầu 16/10): tab riêng dùng OmniVoice của tool như một tool TTS.

- Đưa giọng mẫu (file âm thanh) + chữ cần đọc → OmniVoice đọc ra file WAV.
- Giọng mẫu LƯU vào thư viện (`studio/voices/<tên>/`: sample.wav + meta.json + prompt.pt cache) để lần sau chọn lại; cũng
  lưu được giọng "mô tả" (instruct) không cần file mẫu.
- Đủ các thông số sinh của OmniVoice 0.2.1 (đối chiếu `OmniVoiceGenerationConfig` + chữ ký `generate()`), lưu làm mặc
  định (`config/local.yaml → studio_params`).
- Clone giọng CHỈ khi tick xác nhận có quyền dùng giọng đó (như `clone_ok` ở trang voice).
Thư mục `studio/` bị .gitignore (giọng / âm thanh không bao giờ commit).
"""

from __future__ import annotations

import json
import re
import threading
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from app.config import ROOT

STUDIO = ROOT / "studio"
LANGS = {"auto": "Tự nhận (không chỉ định)", "ko": "Tiếng Hàn", "ja": "Tiếng Nhật", "en": "Tiếng Anh", "de": "Tiếng Đức", "vi": "Tiếng Việt",
         "zh": "Tiếng Trung"}

# (khóa, nhãn, kiểu, mặc định, min, max, bước, giải thích) — mặc định = OmniVoiceGenerationConfig bản 0.2.1
PARAMS: list[tuple] = [
    ("speed", "Tốc độ đọc", "float", 1.0, 0.5, 2.0, 0.05, ">1 nhanh hơn, <1 chậm hơn. Bị bỏ qua nếu đặt Thời lượng."),
    ("duration", "Thời lượng cố định (giây)", "float", 0.0, 0.0, 600.0, 0.1,
     "0 = để model tự ước lượng theo chữ. Đặt số thì file ra dài đúng chừng đó (ghi đè Tốc độ)."),
    ("num_step", "Số bước sinh", "int", 32, 4, 64, 1, "Nhiều bước = mượt / chuẩn hơn nhưng chậm hơn (16 nhanh, 32 chuẩn)."),
    ("guidance_scale", "Độ bám điều kiện (guidance)", "float", 2.0, 0.0, 10.0, 0.1,
     "Cao = bám giọng mẫu / mô tả chặt hơn; quá cao dễ gắt, méo."),
    ("t_shift", "Dịch bước thời gian (t_shift)", "float", 0.1, 0.0, 1.0, 0.01,
     "Nhỏ = chú ý vùng nhiễu nhiều (ảnh hưởng độ tự nhiên). Giữ 0.1 nếu không chắc."),
    ("layer_penalty_factor", "Phạt lớp mã (layer penalty)", "float", 5.0, 0.0, 20.0, 0.5,
     "Khuyến khích mở các lớp mã đầu trước. Giữ mặc định nếu không thử nghiệm."),
    ("position_temperature", "Nhiệt độ chọn vị trí", "float", 5.0, 0.0, 20.0, 0.5,
     "Cao = đa dạng hơn khi chọn chỗ sinh tiếp."),
    ("class_temperature", "Nhiệt độ lấy mẫu", "float", 0.0, 0.0, 2.0, 0.05,
     "0 = luôn chọn khả năng cao nhất (ổn định); tăng lên = ngữ điệu biến hóa hơn, mỗi lần một khác."),
    ("denoise", "Khử nhiễu (denoise)", "bool", True, None, None, None, "Thêm token khử nhiễu — giọng sạch hơn."),
    ("preprocess_prompt", "Xử lý giọng mẫu", "bool", True, None, None, None,
     "Cắt khoảng lặng, cắt bớt mẫu quá dài, thêm dấu câu cho lời đọc mẫu."),
    ("postprocess_output", "Hậu xử lý file ra", "bool", True, None, None, None,
     "Bỏ lặng thừa, fade vào / ra, đệm hai đầu."),
    ("normalize_text", "Chuẩn hóa chữ", "bool", False, None, None, None,
     "Đổi số / ngày / tiền thành chữ đọc được (vd 2345 → đọc thành chữ)."),
    ("audio_chunk_duration", "Độ dài mỗi khúc (giây)", "float", 15.0, 0.0, 60.0, 0.5,
     "Văn bản dài được chia khúc chừng này giây để đọc dần (0 = không chia)."),
    ("audio_chunk_threshold", "Ngưỡng bắt đầu chia khúc (giây)", "float", 30.0, 0.0, 600.0, 1.0,
     "Chỉ chia khúc khi bài ước lượng dài hơn chừng này giây."),
    ("pad_duration", "Đệm lặng mỗi đầu (giây)", "float", 0.1, 0.0, 2.0, 0.05, "0 = không đệm."),
    ("fade_duration", "Fade vào / ra (giây)", "float", 0.1, 0.0, 2.0, 0.05, "0 = không fade."),
    ("seed", "Seed (hạt ngẫu nhiên)", "int", -1, -1, 2_147_483_647, 1,
     "-1 = ngẫu nhiên mỗi lần. Đặt số cố định → cùng chữ + cùng tham số ra lại đúng giọng đọc đó."),
]
WORKER_KEYS = {k for k, *_ in PARAMS} - {"duration", "preprocess_prompt"}


def defaults() -> dict:
    from app.tts.voices import load_cfg

    d = {k: dflt for k, _, _, dflt, *_ in PARAMS}
    d["num_step"] = int(load_cfg().get("num_step", d["num_step"]))
    return d


def clean_params(raw: dict, base: dict | None = None) -> dict:
    """Giá trị từ form (chuỗi) → đúng kiểu, kẹp trong khoảng cho phép. Ô bool không gửi = False."""
    base = base or defaults()
    out = {}
    for k, _, kind, dflt, lo, hi, *_ in PARAMS:
        v = raw.get(k)
        if kind == "bool":
            out[k] = str(v).lower() in ("1", "true", "on", "yes") if v is not None else False
            continue
        try:
            val = (int(float(v)) if kind == "int" else float(v)) if v not in (None, "") else base.get(k, dflt)
        except (TypeError, ValueError):
            val = base.get(k, dflt)
        out[k] = min(max(val, lo), hi)
    return out


def load_params(settings_path: Path | None = None) -> dict:
    from app import settings

    saved = (settings.load(settings_path) if settings_path else settings.load()).get("studio_params") or {}
    d = defaults()
    d.update({k: v for k, v in saved.items() if k in d})
    return d


def save_params(params: dict, settings_path: Path | None = None) -> None:
    from app import settings

    if settings_path:
        settings.save({"studio_params": params}, settings_path)
    else:
        settings.save({"studio_params": params})


# ---------- thư viện giọng ----------

def slug(name: str) -> str:
    s = unicodedata.normalize("NFKC", name).strip()
    s = re.sub(r"[\\/:*?\"<>|\s]+", "_", s)[:60].strip("._")
    return s or "giong"


def voices_dir(root: Path | None = None) -> Path:
    return (root or STUDIO) / "voices"


def list_voices(root: Path | None = None) -> list[dict]:
    out = []
    d = voices_dir(root)
    for meta in sorted(d.glob("*/meta.json")) if d.is_dir() else []:
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
        except ValueError:
            continue
        m["slug"] = meta.parent.name
        m["sample_path"] = str(meta.parent / "sample.wav") if (meta.parent / "sample.wav").is_file() else ""
        out.append(m)
    return sorted(out, key=lambda m: m.get("created", ""), reverse=True)


def get_voice(slug_name: str, root: Path | None = None) -> dict | None:
    return next((v for v in list_voices(root) if v["slug"] == slug_name), None)


def save_voice(name: str, *, sample: Path | None = None, ref_text: str = "", language: str = "auto",
               instruct: str = "", note: str = "", consent: bool = False, max_ref_s: float = 15.0,
               root: Path | None = None, prepare=None) -> dict:
    """Lưu giọng vào thư viện. Có file mẫu → giọng clone (bắt buộc consent), đổi sang WAV mono 24 kHz ≤ max_ref_s;
    không có file mà có instruct → giọng mô tả. Trùng tên thì ghi đè (cache prompt cũ bị xóa)."""
    name = name.strip()
    if not name:
        raise ValueError("Đặt tên cho giọng mẫu (vd: Giọng nam trầm kênh A).")
    if sample is None and not instruct.strip():
        raise ValueError("Chọn file giọng mẫu, hoặc gõ mô tả giọng (instruct).")
    if sample is not None and not consent:
        raise ValueError("Tick xác nhận bạn có quyền dùng giọng này thì mới lưu / clone được giọng mẫu.")
    d = voices_dir(root) / slug(name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.pt").unlink(missing_ok=True)
    trimmed = False
    if sample is not None:
        if prepare is None:
            from app.tts.voices import prepare_sample as prepare
        _, trimmed = prepare(Path(sample), d / "sample.wav", max_ref_s)
        if trimmed:
            ref_text = ""  # mẫu bị cắt bớt → lời đọc gõ cho cả file không còn khớp, để OmniVoice tự nhận dạng
    else:
        (d / "sample.wav").unlink(missing_ok=True)
    meta = {"name": name, "mode": "clone" if sample is not None else "design", "ref_text": ref_text.strip(),
            "instruct": instruct.strip(), "language": language if language in LANGS else "auto", "note": note.strip(),
            "consent": bool(consent) if sample is not None else False, "trimmed": trimmed,
            "created": datetime.now().isoformat(timespec="seconds")}
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**meta, "slug": d.name}


def delete_voice(slug_name: str, root: Path | None = None) -> bool:
    import shutil

    d = voices_dir(root) / slug(slug_name)
    if not (d / "meta.json").is_file():
        return False
    shutil.rmtree(d)
    return True


# ---------- đọc ----------

def outputs_dir(root: Path | None = None) -> Path:
    return (root or STUDIO) / "outputs"


def split_texts(text: str, per_line: bool) -> list[str]:
    if per_line:
        return [t.strip() for t in text.splitlines() if t.strip()]
    t = text.strip()
    return [t] if t else []


def build_request(cfg: dict, *, voice: dict | None, texts: list[str], language: str, params: dict, out_dir: Path,
                  stamp: str, instruct: str = "") -> dict:
    """Yêu cầu cho omnivoice_worker.py. voice = giọng trong thư viện (clone / design) hoặc None (instruct gõ tay / tự
    chọn). File ra: <out_dir>/<stamp>_<giọng>_NN.wav."""
    gen = {k: v for k, v in params.items() if k in WORKER_KEYS}
    if voice and voice.get("mode") == "clone" and voice.get("sample_path"):
        vdir = Path(voice["sample_path"]).parent
        spec = {"mode": "clone", "ref_audio": voice["sample_path"], "ref_text": voice.get("ref_text") or "",
                "preprocess_prompt": bool(params.get("preprocess_prompt", True)),
                # cache theo cách xử lý mẫu (đổi ô "Xử lý giọng mẫu" thì tạo lại)
                "prompt_cache": str(vdir / ("prompt.pt" if params.get("preprocess_prompt", True) else "prompt_raw.pt"))}
        vname = voice.get("slug") or "mau"
    elif (voice and voice.get("instruct")) or instruct.strip():
        spec = {"mode": "design", "instruct": (instruct.strip() or voice.get("instruct", ""))}
        vname = (voice or {}).get("slug") or "mota"
    else:
        spec, vname = {"mode": "auto"}, "tu_chon"
    lang = None if language in ("", "auto") else language
    dur = float(params.get("duration") or 0)
    items = [{"text": t, "language": lang, "voice": "v", "duration": dur if dur > 0 else None,
              "out": str(out_dir / f"{stamp}_{slug(vname)}_{i:02d}.wav")} for i, t in enumerate(texts, 1)]
    return {"model": cfg.get("model", "k2-fsa/OmniVoice"), "device": cfg.get("device", "auto"),
            "num_step": int(params.get("num_step", 32)), "voices": {"v": spec}, "items": items, "gen": gen}


class StudioRun:
    """Một lượt đọc chạy nền (một lượt mỗi lúc); trang Studio hỏi /studio/status để hiện tiến độ."""

    def __init__(self):
        self.lock = threading.Lock()
        self.state: dict = {"running": False, "log": [], "outputs": [], "error": "", "started": 0.0}
        self._stop = False

    def snapshot(self) -> dict:
        with self.lock:
            return json.loads(json.dumps(self.state))

    def stop(self) -> None:
        self._stop = True

    def start(self, request: dict, meta: dict, root: Path | None = None, run_worker=None, cfg: dict | None = None) -> bool:
        with self.lock:
            if self.state["running"]:
                return False
            self.state = {"running": True, "log": ["Bắt đầu…"], "outputs": [], "error": "", "started": time.time()}
            self._stop = False
        t = threading.Thread(target=self._run, args=(request, meta, root, run_worker, cfg), daemon=True)
        t.start()
        return True

    def _line(self, line: str) -> None:
        if self._stop:
            raise RuntimeError("Đã dừng theo yêu cầu.")
        with self.lock:
            self.state["log"] = (self.state["log"] + [line])[-60:]

    def _run(self, request: dict, meta: dict, root: Path | None, run_worker, cfg: dict | None) -> None:
        from app.tts import voices as ov

        out = outputs_dir(root)
        out.mkdir(parents=True, exist_ok=True)
        try:
            (run_worker or ov.run_worker)(request, out / "_request.json", cfg or ov.load_cfg(), self._line)
            done = [it["out"] for it in request["items"] if Path(it["out"]).is_file()]
            for f, it in zip(done, request["items"]):
                Path(f).with_suffix(".json").write_text(json.dumps(
                    {**meta, "text": it["text"], "created": datetime.now().isoformat(timespec="seconds")},
                    ensure_ascii=False, indent=2), encoding="utf-8")
            with self.lock:
                self.state["outputs"] = [Path(f).name for f in done]
                self.state["log"].append(f"✅ Xong {len(done)} file ({time.time() - self.state['started']:.0f}s).")
        except Exception as exc:
            with self.lock:
                self.state["error"] = str(exc)
                self.state["log"].append(f"❌ {exc}")
        finally:
            with self.lock:
                self.state["running"] = False


def history(root: Path | None = None, limit: int = 40) -> list[dict]:
    d = outputs_dir(root)
    out = []
    for wav in sorted(d.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit] if d.is_dir() else []:
        meta = {}
        if wav.with_suffix(".json").is_file():
            try:
                meta = json.loads(wav.with_suffix(".json").read_text(encoding="utf-8"))
            except ValueError:
                pass
        out.append({"file": wav.name, **meta})
    return out


STAMP_RE = re.compile(r"^(\d{8}_\d{6})_.*_(\d+)$")


def _order_key(p: Path) -> tuple:
    """Thứ tự file đã đọc: lượt cũ trước, trong một lượt theo đúng thứ tự dòng (…_01, _02…)."""
    m = STAMP_RE.match(p.stem)
    return (m.group(1), int(m.group(2))) if m else (datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y%m%d_%H%M%S"), 0)


def ordered_outputs(root: Path | None = None, batch: str = "") -> list[Path]:
    """Mọi file âm thanh đã đọc (hoặc chỉ một lượt — `batch` = mốc giờ YYYYMMDD_HHMMSS) theo thứ tự đọc."""
    d = outputs_dir(root)
    files = [f for f in d.glob("*.wav") if not batch or f.name.startswith(batch + "_")] if d.is_dir() else []
    return sorted(files, key=_order_key)


def batches(root: Path | None = None, limit: int = 10) -> list[dict]:
    """Các lượt đọc gần nhất: [{batch, files, label}] — để tải cả lượt một lần."""
    groups: dict[str, list[Path]] = {}
    for f in ordered_outputs(root):
        m = STAMP_RE.match(f.stem)
        if m:
            groups.setdefault(m.group(1), []).append(f)
    out = []
    for b in sorted(groups, reverse=True)[:limit]:
        t = datetime.strptime(b, "%Y%m%d_%H%M%S")
        out.append({"batch": b, "files": len(groups[b]), "label": t.strftime("%d/%m %H:%M:%S")})
    return out


def zip_outputs(files: list[Path]) -> bytes:
    """Nén các file thành MỘT file zip, đặt tên lại theo thứ tự 1.wav, 2.wav… (chủ dự án 23/10) + danh_sach.txt ghi
    số nào đọc câu gì."""
    import io
    import zipfile

    buf = io.BytesIO()
    lines = []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for i, f in enumerate(files, 1):
            name = f"{i}{f.suffix.lower()}"
            z.write(f, name)
            text = ""
            if f.with_suffix(".json").is_file():
                try:
                    text = json.loads(f.with_suffix(".json").read_text(encoding="utf-8")).get("text", "")
                except ValueError:
                    pass
            lines.append(f"{name}\t{text}\t(file gốc: {f.name})")
        z.writestr("danh_sach.txt", "\n".join(lines) + "\n")
    return buf.getvalue()


def safe_file(base: Path, rel: str) -> Path | None:
    """Đường dẫn file nằm TRONG base (chặn ../); không có thì None."""
    try:
        p = (base / rel).resolve()
        p.relative_to(base.resolve())
    except (ValueError, OSError):
        return None
    return p if p.is_file() else None
