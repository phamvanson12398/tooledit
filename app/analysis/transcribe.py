"""Nhận dạng thoại bằng faster-whisper, có timestamp theo từ và dự phòng CPU/model nhỏ."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from app import config


class Word(BaseModel):
    start: float
    end: float
    word: str
    probability: float = 1.0


class Segment(BaseModel):
    start: float
    end: float
    text: str
    words: list[Word] = []


class Transcript(BaseModel):
    language: str
    language_probability: float
    duration: float
    model: str
    device: str
    segments: list[Segment]


def attempts(cfg: dict) -> list[dict]:
    """Danh sách cấu hình thử lần lượt: cấu hình chính rồi tới các phương án dự phòng."""
    main = {k: cfg[k] for k in ("model", "device", "compute_type") if k in cfg}
    return [main, *cfg.get("fallback", [])]


def load_model(cfg: dict, factory: Callable | None = None):
    """Thử từng cấu hình; trả về (model, cấu hình đã dùng). Lỗi hết thì báo lỗi tiếng Việt."""
    if factory is None:
        from faster_whisper import WhisperModel as factory  # noqa: N813
    errors = []
    for a in attempts(cfg):
        try:
            model = factory(a.get("model", "large-v3"), device=a.get("device", "auto"),
                            compute_type=a.get("compute_type", "default"))
            return model, a
        except Exception as exc:  # thiếu CUDA/cuDNN, hết VRAM, chưa tải được model...
            errors.append(f"{a}: {exc}")
    raise RuntimeError("Không nạp được model nhận dạng thoại:\n" + "\n".join(errors))


def pick_language(detected: str, probs: list[tuple[str, float]] | None, allowed: list[str]) -> str | None:
    """Nếu ngôn ngữ nhận được không thuộc ko/ja/en, chọn ngôn ngữ cho phép có xác suất cao nhất."""
    if not allowed or detected in allowed:
        return None
    ranked = [(lang, p) for lang, p in (probs or []) if lang in allowed]
    return max(ranked, key=lambda x: x[1])[0] if ranked else allowed[0]


def transcribe(audio: Path, cfg: dict | None = None, factory: Callable | None = None) -> Transcript:
    cfg = cfg or config.load("whisper")
    model, used = load_model(cfg, factory)
    allowed = cfg.get("languages", ["ko", "ja", "en"])
    kwargs = dict(beam_size=cfg.get("beam_size", 5), word_timestamps=cfg.get("word_timestamps", True),
                  vad_filter=True)
    segments, info = model.transcribe(str(audio), **kwargs)
    forced = pick_language(info.language, getattr(info, "all_language_probs", None), allowed)
    if forced:
        segments, info = model.transcribe(str(audio), language=forced, **kwargs)
    out = [
        Segment(
            start=s.start, end=s.end, text=s.text.strip(),
            words=[Word(start=w.start, end=w.end, word=w.word, probability=w.probability) for w in (s.words or [])],
        )
        for s in segments  # generator: nhận dạng chạy thật ở đây
    ]
    return Transcript(language=forced or info.language, language_probability=info.language_probability,
                      duration=info.duration, model=used.get("model", ""), device=used.get("device", ""),
                      segments=out)
