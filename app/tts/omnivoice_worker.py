"""Chạy OmniVoice đọc thoại (tách riêng khỏi tool — chạy bằng python của môi trường đã cài omnivoice + torch).

Cách gọi:  <python có omnivoice> omnivoice_worker.py request.json
request.json:
  {"model": "k2-fsa/OmniVoice", "device": "auto", "num_step": 32,
   "voices": {"<tên giọng>": {"mode": "clone", "ref_audio": "ref.wav", "ref_text": "..."}
                             | {"mode": "design", "instruct": "male, child, high pitch"} | {"mode": "auto"}},
   "items":  [{"text": "...", "language": "ko", "voice": "<tên giọng>", "duration": 2.4 | null, "out": "x.wav"}]}
  Tùy chọn (Voice Studio 16/10): "gen": {num_step, guidance_scale, t_shift, layer_penalty_factor, position_temperature,
  class_temperature, denoise, postprocess_output, audio_chunk_duration, audio_chunk_threshold, pad_duration,
  fade_duration, speed, normalize_text, seed}; giọng clone thêm "preprocess_prompt" và "prompt_cache" (file .pt —
  có thì nạp lại, chưa có thì tạo rồi lưu: VoiceClonePrompt.save / .load), item thêm "speed".
In ra từng dòng "PROGRESS i/n <file>" để tool hiện tiến độ; lỗi → in "ERROR ..." và thoát mã 1.

API đối chiếu mã nguồn OmniVoice 0.2.1 (omnivoice/models/omnivoice.py): OmniVoice.from_pretrained(name, device_map,
dtype); model.create_voice_clone_prompt(ref_audio, ref_text); model.generate(text, language, voice_clone_prompt |
instruct, duration, num_step=...) → list[np.ndarray] ở model.sampling_rate (24 kHz).
Tham số sinh (OmniVoiceGenerationConfig) + speed + normalize_text đối chiếu chữ ký generate() bản 0.2.1.
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


GEN_KEYS = ("num_step", "guidance_scale", "t_shift", "layer_penalty_factor", "position_temperature", "class_temperature",
            "denoise", "postprocess_output", "audio_chunk_duration", "audio_chunk_threshold", "pad_duration",
            "fade_duration", "preprocess_prompt")


def _clone_prompt(model, v: dict):
    """Giọng mẫu → VoiceClonePrompt; có file cache (.pt) thì nạp lại cho nhanh, chưa có thì tạo rồi lưu."""
    from omnivoice import VoiceClonePrompt

    cache = v.get("prompt_cache")
    if cache and Path(cache).is_file():
        try:
            return VoiceClonePrompt.load(cache)
        except Exception as exc:  # bản cache cũ / hỏng → tạo lại
            print(f"INFO tạo lại giọng mẫu ({type(exc).__name__})", flush=True)
    prompt = model.create_voice_clone_prompt(ref_audio=v["ref_audio"], ref_text=v.get("ref_text") or None,
                                             preprocess_prompt=bool(v.get("preprocess_prompt", True)))
    if cache:
        try:
            Path(cache).parent.mkdir(parents=True, exist_ok=True)
            prompt.save(cache)
        except Exception:
            pass
    if not (v.get("ref_text") or "").strip():
        print(f"INFO lời đọc của giọng mẫu (tự nhận dạng): {getattr(prompt, 'ref_text', '')}", flush=True)
    return prompt


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
    gen = dict(req.get("gen") or {})
    seed = gen.pop("seed", None)
    speed = gen.pop("speed", None)
    normalize = bool(gen.pop("normalize_text", False))
    gen_kw = {k: v for k, v in gen.items() if k in GEN_KEYS}
    gen_kw.setdefault("num_step", int(req.get("num_step", 32)))
    prompts: dict[str, dict] = {}
    for name, v in (req.get("voices") or {}).items():
        if v.get("mode") == "clone" and v.get("ref_audio"):
            prompts[name] = {"voice_clone_prompt": _clone_prompt(model, v)}
        elif v.get("mode") == "design" and (v.get("instruct") or "").strip():
            prompts[name] = {"instruct": v["instruct"].strip()}
        else:
            prompts[name] = {}
    items = req.get("items") or []
    for i, it in enumerate(items, 1):
        kw = dict(prompts.get(it.get("voice", ""), {}))
        if it.get("duration"):
            kw["duration"] = float(it["duration"])
        elif it.get("speed") or speed:  # duration thắng speed (như tài liệu generate)
            kw["speed"] = float(it.get("speed") or speed)
        if normalize:
            kw["normalize_text"] = True
        if seed is not None and int(seed) >= 0:  # cùng seed + cùng tham số → ra lại đúng giọng đọc đó
            import torch

            torch.manual_seed(int(seed) + i - 1)
        audio = model.generate(text=it["text"], language=it.get("language") or None, **gen_kw, **kw)
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
