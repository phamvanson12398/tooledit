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


def load_model(attempt: dict, factory: Callable | None = None):
    if factory is None:
        from app.gpu_libs import register_cuda_dlls

        register_cuda_dlls()  # Windows: chỉ đường tới cublas/cudnn cài bằng pip
        from faster_whisper import WhisperModel as factory  # noqa: N813
    return factory(attempt.get("model", "large-v3"), device=attempt.get("device", "auto"),
                   compute_type=attempt.get("compute_type", "default"))


def pick_language(detected: str, probs: list[tuple[str, float]] | None, allowed: list[str]) -> str | None:
    """Nếu ngôn ngữ nhận được không thuộc ko/ja/en, chọn ngôn ngữ cho phép có xác suất cao nhất."""
    if not allowed or detected in allowed:
        return None
    ranked = [(lang, p) for lang, p in (probs or []) if lang in allowed]
    return max(ranked, key=lambda x: x[1])[0] if ranked else allowed[0]


def transcribe(audio: Path, cfg: dict | None = None, factory: Callable | None = None,
               log: Callable[[str], None] = lambda msg: None, options: dict | None = None,
               language: str | None = None) -> Transcript:
    """Thử lần lượt từng cấu hình (GPU rồi CPU...). Lỗi GPU có thể chỉ lộ ra lúc bắt đầu tính
    (ví dụ thiếu cublas64_12.dll), nên mỗi lần thử phải chạy trọn cả nhận dạng.
    options: tham số thêm cho model.transcribe (vd vad_parameters nhạy hơn — đối chiếu faster-whisper 1.2.1);
    language: biết trước tiếng gốc thì khỏi tự nhận."""
    cfg = cfg or config.load("whisper")
    errors = []
    for attempt in attempts(cfg):
        try:
            model = load_model(attempt, factory)
            return _run(model, attempt, audio, cfg, options, language, log)
        except Exception as exc:  # thiếu CUDA/cuDNN, GPU không hỗ trợ, hết VRAM, chưa tải được model...
            errors.append(f"{attempt}: {exc}")
            log(f"Không chạy được với {attempt.get('device')}/{attempt.get('model')}: {exc}. Thử cách khác...")
    raise RuntimeError("Không chạy được nhận dạng thoại:\n" + "\n".join(errors))


def _run(model, used: dict, audio: Path, cfg: dict, options: dict | None = None,
         language: str | None = None, log: Callable[[str], None] = lambda msg: None) -> Transcript:
    allowed = cfg.get("languages", ["ko", "ja", "en"])
    kwargs = dict(beam_size=cfg.get("beam_size", 5), word_timestamps=cfg.get("word_timestamps", True),
                  vad_filter=True, **(options or {}))
    if language:
        kwargs["language"] = language
    runner = model
    if use_batched(cfg, used) and hasattr(model, "feature_extractor"):  # chỉ WhisperModel thật (không phải model giả khi test)  # chủ dự án 11/10 "phân tích lâu": chạy theo lô trên GPU, nhanh hơn nhiều lần
        try:
            from faster_whisper import BatchedInferencePipeline

            runner = BatchedInferencePipeline(model)
            # without_timestamps=False: vẫn chia câu theo mốc thời gian (mặc định của chế độ lô gộp cả đoạn ~30s)
            kwargs.update(batch_size=int(cfg.get("batch_size", 8)), without_timestamps=False)
        except ImportError:
            runner = model
    try:
        return _decode(runner, used, audio, kwargs, allowed, language)
    except Exception as exc:
        if runner is model:
            raise
        log(f"Nhận dạng theo lô lỗi ({exc}) — chạy lại cách thường (chậm hơn).")
        for k in ("batch_size", "without_timestamps"):
            kwargs.pop(k, None)
        return _decode(model, used, audio, kwargs, allowed, language)


def use_batched(cfg: dict, used: dict) -> bool:
    """Chế độ lô (BatchedInferencePipeline, faster-whisper ≥ 1.1) chỉ đáng dùng trên GPU."""
    return bool(cfg.get("batched", True)) and used.get("device", "auto") in ("cuda", "auto")


def _decode(runner, used: dict, audio: Path, kwargs: dict, allowed: list, language: str | None) -> Transcript:
    segments, info = runner.transcribe(str(audio), **kwargs)
    forced = None if language else pick_language(info.language, getattr(info, "all_language_probs", None), allowed)
    if forced:
        segments, info = runner.transcribe(str(audio), **{**kwargs, "language": forced})
    out = [
        Segment(
            start=s.start, end=s.end, text=s.text.strip(),
            words=[Word(start=w.start, end=w.end, word=w.word, probability=w.probability) for w in (s.words or [])],
        )
        for s in segments  # generator: nhận dạng chạy thật ở đây
    ]
    return Transcript(language=forced or language or info.language, language_probability=info.language_probability,
                      duration=info.duration, model=used.get("model", ""), device=used.get("device", ""),
                      segments=out)
