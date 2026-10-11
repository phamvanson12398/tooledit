"""Chạy OmniVoice đọc thoại (tách riêng khỏi tool — chạy bằng python của môi trường đã cài omnivoice + torch).

Cách gọi:  <python có omnivoice> omnivoice_worker.py request.json
request.json:
  {"model": "k2-fsa/OmniVoice", "device": "auto", "num_step": 32,
   "voices": {"<tên giọng>": {"mode": "clone", "ref_audio": "ref.wav", "ref_text": "..."}
                             | {"mode": "design", "instruct": "male, child, high pitch"} | {"mode": "auto"}},
   "items":  [{"text": "...", "language": "ko", "voice": "<tên giọng>", "duration": 2.4 | null, "out": "x.wav"}]}
In ra từng dòng "PROGRESS i/n <file>" để tool hiện tiến độ; lỗi → in "ERROR ..." và thoát mã 1.

API đối chiếu mã nguồn OmniVoice 0.2.1 (omnivoice/models/omnivoice.py): OmniVoice.from_pretrained(name, device_map,
dtype); model.create_voice_clone_prompt(ref_audio, ref_text); model.generate(text, language, voice_clone_prompt |
instruct, duration, num_step=...) → list[np.ndarray] ở model.sampling_rate (24 kHz).
File này KHÔNG import gì của tool để chạy được ở môi trường python khác.
"""

from __future__ import annotations

import json
import sys
import wave
from pathlib import Path


def _write_wav(path: Path, audio, rate: int) -> None:
    import numpy as np

    pcm = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(rate))
        w.writeframes((pcm * 32767).astype(np.int16).tobytes())


def _device(name: str):
    import torch

    if name and name != "auto":
        return name, (torch.float16 if name.startswith("cuda") else torch.float32)
    if torch.cuda.is_available():
        return "cuda:0", torch.float16
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps", torch.float32
    return "cpu", torch.float32


def _utf8_stdout() -> None:
    """Windows in ra ống bằng cp1252 → lỗi 'charmap' với chữ Việt / Hàn / Nhật. Ép UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str]) -> int:
    req = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    here = Path(__file__).resolve().parent  # không để thư mục của tool che mất thư viện omnivoice thật
    sys.path[:] = [p for p in sys.path if p and Path(p).resolve() != here]
    try:
        from omnivoice import OmniVoice
    except ImportError:
        print("ERROR chưa cài omnivoice ở môi trường python này (pip install omnivoice — xem docs/SETUP_WINDOWS.md)",
              flush=True)
        return 1
    device, dtype = _device(str(req.get("device", "auto")))
    print(f"INFO tải model {req.get('model', 'k2-fsa/OmniVoice')} trên {device}…", flush=True)
    model = OmniVoice.from_pretrained(req.get("model", "k2-fsa/OmniVoice"), device_map=device, dtype=dtype)
    rate = int(getattr(model, "sampling_rate", 24000))
    prompts: dict[str, dict] = {}
    for name, v in (req.get("voices") or {}).items():
        if v.get("mode") == "clone" and v.get("ref_audio"):
            prompts[name] = {"voice_clone_prompt": model.create_voice_clone_prompt(
                ref_audio=v["ref_audio"], ref_text=v.get("ref_text") or None)}
        elif v.get("mode") == "design" and (v.get("instruct") or "").strip():
            prompts[name] = {"instruct": v["instruct"].strip()}
        else:
            prompts[name] = {}
    items = req.get("items") or []
    for i, it in enumerate(items, 1):
        kw = dict(prompts.get(it.get("voice", ""), {}))
        if it.get("duration"):
            kw["duration"] = float(it["duration"])
        audio = model.generate(text=it["text"], language=it.get("language") or None,
                               num_step=int(req.get("num_step", 32)), **kw)
        _write_wav(Path(it["out"]), audio[0], rate)
        print(f"PROGRESS {i}/{len(items)} {Path(it['out']).name}", flush=True)
    return 0


if __name__ == "__main__":
    _utf8_stdout()
    try:
        sys.exit(main(sys.argv))
    except Exception as exc:  # báo lỗi gọn cho tool hiện bằng tiếng Việt
        print(f"ERROR {type(exc).__name__}: {exc}", flush=True)
        sys.exit(1)
