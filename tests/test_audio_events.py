import wave

import numpy as np

from app.analysis.audio_events import (
    analyze_audio_events, detect_beats, detect_events, events_for_prompt, transcript_markers,
)

SR = 16000
rng = np.random.default_rng(0)


def tone(sec, amp, mod_hz=None):
    t = np.arange(int(sec * SR)) / SR
    x = amp * rng.standard_normal(len(t)).astype(np.float32)
    if mod_hz:
        x *= (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * mod_hz * t))).astype(np.float32)
    return x


def make_signal():
    # 0–4s nói chuyện vừa, 4–6s im, 6–8s tiếng cười ha-ha (to, dao động 5 Hz), 8–10s im,
    # 10–11.5s hò reo to đều (không dao động), 11.5–13s im, 13–14.5s hét to khi đang nói
    return np.concatenate([tone(4, 0.03), tone(2, 0.002), tone(2, 0.4, mod_hz=5), tone(2, 0.002),
                           tone(1.5, 0.4), tone(1.5, 0.002), tone(1.5, 0.4)])


def test_detect_laugh_cheer_shout():
    sig = make_signal()
    speech = [(0.0, 4.0), (13.0, 14.5)]
    ev = detect_events(sig, SR, speech)
    kinds = {e["kind"]: e for e in ev}
    assert set(kinds) == {"laugh", "cheer", "shout"}, ev
    assert 5.8 <= kinds["laugh"]["start"] <= 6.2 and 7.8 <= kinds["laugh"]["end"] <= 8.2
    assert 9.8 <= kinds["cheer"]["start"] <= 10.2
    assert 12.8 <= kinds["shout"]["start"] <= 13.2
    assert all(e["strength"] > 10 for e in ev)
    assert "tiếng cười" in events_for_prompt(ev) and "6.0" in events_for_prompt(ev)


def test_transcript_markers_and_wav_roundtrip(tmp_path):
    segs = [{"start": 1.0, "end": 2.0, "text": "そうなん(笑)", "words": []},
            {"start": 3.0, "end": 4.0, "text": "진짜 ㅋㅋㅋ", "words": []},
            {"start": 5.0, "end": 6.0, "text": "normal words", "words": []}]
    assert [m["start"] for m in transcript_markers(segs)] == [1.0, 3.0]
    wav = tmp_path / "a.wav"
    sig = make_signal()
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(sig, -1, 1) * 32767).astype(np.int16).tobytes())
    ev = analyze_audio_events(wav, [{"start": 0.0, "end": 4.0, "text": "", "words": []},
                                    {"start": 13.0, "end": 14.5, "text": "", "words": []}])
    assert {e["kind"] for e in ev} == {"laugh", "cheer", "shout"}


def test_detect_beats_120bpm():
    sr = 11025
    x = np.zeros(sr * 8, np.float32)
    for k in range(16):  # nhịp mỗi 0.5 giây, bắt đầu 0.25s
        i = int((0.25 + 0.5 * k) * sr)
        x[i:i + 300] = rng.standard_normal(300).astype(np.float32) * 0.8
    beats = detect_beats(x, sr)
    gaps = np.diff(beats)
    assert abs(float(np.median(gaps)) - 0.5) < 0.02
    assert min(abs(b - 0.25) for b in beats) < 0.03


def test_quiet_laugh_between_words():
    # nói 0–3s, cười ha-ha to ngang giọng nói 3.5–5s (không có chữ), nói tiếp 5.5–8s
    sig = np.concatenate([tone(3, 0.1), tone(0.5, 0.002), tone(1.5, 0.12, mod_hz=5), tone(0.5, 0.002),
                          tone(2.5, 0.1)])
    speech = [(0.0, 3.0), (5.5, 8.0)]
    ev = detect_events(sig, SR, speech)
    laughs = [e for e in ev if e["kind"] == "laugh"]
    assert len(laughs) == 1 and 3.3 <= laughs[0]["start"] <= 3.7 and 4.8 <= laughs[0]["end"] <= 5.2, ev
    # tiếng động đều (không nhịp nhàng) trong khoảng trống → không phải tiếng cười
    flat = np.concatenate([tone(3, 0.1), tone(0.5, 0.002), tone(1.5, 0.12), tone(0.5, 0.002), tone(2.5, 0.1)])
    assert not [e for e in detect_events(flat, SR, speech) if e["kind"] == "laugh"]
