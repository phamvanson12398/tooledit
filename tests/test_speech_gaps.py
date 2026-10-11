"""Chủ dự án 11/10 (lồng tiếng nhân vật): "cứ bắt sót câu, sót ý; giọng của nhân vật nào thì phải chuẩn"."""

from __future__ import annotations

import numpy as np

from app.analysis import speech_gaps as sg


def voice(f0: float, secs: float, bright: float, seed: int = 0) -> np.ndarray:
    """Giọng giả: chuỗi hài âm f0 có rung nhẹ, độ 'sáng' (âm sắc) khác nhau."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(sg.SR * secs)) / sg.SR
    f = f0 * (1 + 0.02 * np.sin(2 * np.pi * 5 * t))
    phase = 2 * np.pi * np.cumsum(f) / sg.SR
    x = sum((bright ** k) * np.sin(k * phase) for k in range(1, 12))
    return (0.3 * x / np.max(np.abs(x)) + 0.003 * rng.standard_normal(len(t))).astype(np.float32)


def test_voiced_regions_and_uncovered():
    sil = np.zeros(sg.SR, dtype=np.float32)
    x = np.concatenate([sil, voice(200, 1.0, 0.6), sil, voice(200, 0.8, 0.6), sil])
    regs = sg.voiced_regions(x)
    assert len(regs) == 2 and abs(regs[0][0] - 1.0) < 0.1 and abs(regs[1][0] - 3.0) < 0.1
    # Whisper đã có câu ở đoạn 1 → chỉ đoạn 2 là chỗ sót
    gaps = sg.uncovered_speech(regs, [(0.95, 2.05)])
    assert len(gaps) == 1 and abs(gaps[0][0] - 3.0) < 0.1
    assert sg.uncovered_speech(regs, [(0.9, 4.0)]) == []
    assert sg.is_hallucination("ご視聴ありがとうございました") and not sg.is_hallucination("え？")


def test_voice_groups_separate_two_characters():
    parts, spans, pos = [], [], 0.0
    plan = [(120, 0.45), (280, 0.75), (125, 0.45), (270, 0.75), (118, 0.45), (290, 0.75)]  # nam trầm / nữ cao, xen kẽ
    for k, (f0, br) in enumerate(plan):
        v = voice(f0, 1.5, br, seed=k)
        spans.append((pos, pos + 1.5))
        parts += [v, np.zeros(int(0.5 * sg.SR), dtype=np.float32)]
        pos += 2.0
    spans.append(None)
    info = sg.voice_groups(np.concatenate(parts), spans)
    groups = [i["group"] for i in info[:6]]
    assert groups[0] == groups[2] == groups[4] and groups[1] == groups[3] == groups[5] and groups[0] != groups[1]
    assert info[0]["pitch"] == "trầm" and info[1]["pitch"] == "cao" and info[6] is None
    assert sg.to_concat_time(12.5, [{"start": 10.0, "end": 20.0, "offset": 1.0}]) == 3.5


def test_char_dub_checks_missing_meaning_and_voice_groups():
    from app.director.schemas import DubScript
    from app.director.tasks import check_char_dub, voice_tag

    src = [{"start": 0.0, "end": 4.0, "text": "今日は本当に楽しかったね、また来ようよ"}, {"start": 5.0, "end": 6.0, "text": "うん"}]
    lines = [{"source_start": 0.0, "source_end": 4.0, "text": "응", "text_vi": "ừ", "speaker": "A", "kind": "dub"},
             {"source_start": 5.0, "source_end": 6.0, "text": "응", "text_vi": "ừ", "speaker": "B", "kind": "dub"}]
    errs = check_char_dub(DubScript.model_validate({"video_index": 1, "lines": lines, "editor_notes": ""}), src, 6.0)
    assert any("dịch quá ngắn" in e and "câu 1" in e for e in errs) and not any("câu 2" in e for e in errs if "ngắn" in e)
    many = [dict(lines[1], source_start=float(k), source_end=k + 0.8, speaker="A" if k % 2 else "B") for k in range(6)]
    src6 = [{"start": float(k), "end": k + 0.8, "text": "うん"} for k in range(6)]
    info = [{"group": "G1", "pitch": "cao", "f0": 260}] * 6
    errs = check_char_dub(DubScript.model_validate({"video_index": 1, "lines": many, "editor_notes": ""}), src6, 6.0, info)
    assert any("nhóm giọng G1" in e for e in errs)
    assert voice_tag(info[0]) == "giọng G1 · cao ~260Hz" and voice_tag(None) == "giọng ?"
