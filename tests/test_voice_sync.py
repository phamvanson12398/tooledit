"""Voice thuyết minh khớp hình cho video nói liên tục (chủ dự án yêu cầu 03/10)."""

import json
from pathlib import Path

import numpy as np
import pytest

from app.director.schemas import DubScript, EditPlan, PlanClip, Understanding
from app.planner import dub_io
from app.planner.timeline import TimeMap
from app.planner.voice_split import RATE, choose_cuts, split_voice, write_wav

FIX = Path(__file__).resolve().parent / "fixtures" / "director"


def _tone(seconds: float, freq: float = 220.0) -> np.ndarray:
    t = np.arange(int(seconds * RATE)) / RATE
    return (np.sin(2 * np.pi * freq * t) * 12000).astype(np.int16)


def _silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * RATE), dtype=np.int16)


def test_choose_cuts_prefers_durations_over_comma_pauses():
    # 3 câu dự kiến 2s / 4s / 2s; có một chỗ ngắt hơi giữa câu 2 (giây 4.3) — không được chọn làm điểm cắt
    pauses = [(2.0, 2.8), (4.2, 4.5), (6.9, 7.7)]
    assert choose_cuts(pauses, 9.7, [2.0, 4.0, 2.0]) == pytest.approx([2.4, 7.3])
    assert choose_cuts(pauses[:1], 9.7, [2.0, 4.0, 2.0]) is None  # thiếu chỗ nghỉ


def test_split_one_file_into_lines(tmp_path):
    ff = pytest.importorskip("imageio_ffmpeg").get_ffmpeg_exe()
    lens = [2.0, 3.2, 1.6, 2.6]
    parts = [_silence(0.4)]
    for i, n in enumerate(lens):
        if i == 1:  # câu 2 có chỗ ngắt hơi ngắn ở giữa (dấu phẩy)
            parts += [_tone(1.4), _silence(0.35), _tone(n - 1.75)]
        else:
            parts.append(_tone(n, 220 + 40 * i))
        parts.append(_silence(1.0))
    src = tmp_path / "all.wav"
    write_wav(src, np.concatenate(parts))
    outs = [tmp_path / f"l{i}.wav" for i in range(4)]
    got = split_voice(src, [2.2, 3.5, 1.8, 2.8], outs, exe=ff)
    assert all(p.is_file() for p in outs)
    for g, want in zip(got, lens):
        assert abs(g - want) < 0.25, (got, lens)
    with pytest.raises(ValueError, match="nghỉ"):
        split_voice(src, [1.0] * 9, [tmp_path / f"x{i}.wav" for i in range(9)], exe=ff)


def test_line_windows_and_fit_status():
    script = DubScript(video_index=1, editor_notes="", lines=[
        {"source_start": 1.0, "source_end": 4.0, "text": "a", "text_vi": "a"},
        {"source_start": 4.1, "source_end": 7.0, "text": "b", "text_vi": "b"},   # nói liền: không có chỗ dư
        {"source_start": 9.0, "source_end": 11.0, "text": "c", "text_vi": "c"},  # sau câu này còn lặng tới hết clip
    ])
    win = dub_io.line_windows(script, TimeMap([PlanClip(source_start=0, source_end=14)]))
    assert win[0][1] == pytest.approx(3.0) and win[0][2] == pytest.approx(3.0)  # nói liền: tối đa = chỗ trống
    assert win[2][2] == pytest.approx(14 - 9 - 0.12)
    assert dub_io.fit_status(2.9, 3.0, 3.0, 1.25)[0] == "ok"
    assert dub_io.fit_status(3.5, 3.0, 3.0, 1.25)[0] == "fast"
    assert dub_io.fit_status(4.2, 3.0, 3.0, 1.25)[0] == "long"
    assert dub_io.fit_status(1.0, 3.0, 3.0, 1.25)[0] == "short"


def test_builder_uses_room_before_next_line(tmp_path):
    from app.capcut_writer import SEC, DraftTemplate
    from app.planner.builder import build
    from app.styles import load_style
    from tests.test_planner import SAMPLE, _analysis, _short_plan, load

    plan = EditPlan.model_validate(_short_plan())  # 1 clip 1–45s
    dub = DubScript.model_validate(json.loads((FIX / "dub.json").read_text(encoding="utf-8")))
    u = Understanding.model_validate(load("understand.json"))
    voice = tmp_path / "v.wav"
    voice.write_bytes(b"RIFF")
    # câu 1: chỗ 3s (2–5s), câu sau bắt đầu 10s → voice 4.5s vẫn vừa, không tăng tốc
    # câu 2: chỗ 6s (10–16s), câu sau 20s (+0.8s cho phép trễ) → voice 16s quá dài kể cả tăng tốc 1.4x → cảnh báo
    res = build(plan, u, _analysis(), DraftTemplate(SAMPLE), tmp_path, "dubfit", load_style("jp_telop"), dub=dub,
                dub_voices={1: (voice, round(4.5 * SEC)), 2: (voice, round(16 * SEC))})
    tl = res.writer.build_timeline()
    segs = [s for t in tl["tracks"] if t["type"] == "audio" for s in t["segments"]
            if s["source_timerange"] and abs(s["source_timerange"]["duration"] - 4.5 * SEC) < 0.05 * SEC
            or s["source_timerange"] and abs(s["source_timerange"]["duration"] - 16 * SEC) < 0.05 * SEC]
    speeds = sorted(s["speed"] for s in segs)
    assert speeds[0] == 1.0 and speeds[-1] == pytest.approx(1.4)
    assert any("câu 2 (tràn" in n and "Viết gọn" in n for n in res.notes)


def test_place_voices_never_overlap():
    # video nói liền: 4 câu sát nhau, voice câu 1 và 2 dài hơn chỗ → câu sau lùi lại, không đè, rồi bắt kịp ở chỗ lặng
    S = 1_000_000
    windows = [(0, 2.0, 2.0), (2 * S, 2.0, 2.0), (4 * S, 2.0, 4.0), (10 * S, 2.0, 3.0)]
    durs = {1: 3 * S, 2: 3 * S, 3: 2 * S, 4: 2 * S}
    pl = dub_io.place_voices(windows, durs, max_speed=1.25, hard_max_speed=1.4, max_delay_s=0.8)
    order = [pl[i] for i in sorted(pl)]
    for x, y in zip(order, order[1:]):
        assert y["start"] >= x["end"]  # không bao giờ đè
    assert pl[2]["delay_s"] > 0 and pl[2]["speed"] > 1.0  # câu 2 phải chờ câu 1 nói xong và nói nhanh hơn chút
    assert pl[4]["delay_s"] == 0 and pl[4]["speed"] == 1.0  # sau khoảng lặng: đúng giờ trở lại
    assert all(p["speed"] <= 1.4 for p in order)


def test_split_upload_writes_line_files(tmp_path):
    ff = pytest.importorskip("imageio_ffmpeg").get_ffmpeg_exe()
    from tests.test_planner import _short_plan

    d = tmp_path / "job"
    (d / "plan").mkdir(parents=True)
    dub = json.loads((FIX / "dub.json").read_text(encoding="utf-8"))
    dub_io.dub_path(d, 1).write_text(json.dumps(dub), encoding="utf-8")
    (d / "plan" / "edit_plan_video01.json").write_text(json.dumps(_short_plan()), encoding="utf-8")
    slots = [ln["source_end"] - ln["source_start"] for ln in dub["lines"]]
    src = tmp_path / "all.wav"
    write_wav(src, np.concatenate([x for s in slots for x in (_tone(s * 0.8), _silence(1.0))]))
    (d / "voice").mkdir()
    (d / "voice" / "video01_dub02.mp3").write_bytes(b"old")  # voice cũ của câu 2 bị thay
    got = dub_io.split_upload(d, 1, src, exe=ff)
    assert len(got) == len(slots) and dub_io.missing_lines(d, {1: DubScript.model_validate(dub)}) == []
    assert not (d / "voice" / "video01_dub02.mp3").exists()
    assert abs(dub_io.voice_seconds(d / "voice" / "video01_dub02.wav") - slots[1] * 0.8) < 0.25


def test_vietnamese_check_subtitles(tmp_path):
    from app.capcut_writer import DraftTemplate
    from app.planner.builder import build
    from app.styles import load_style
    from tests.test_planner import SAMPLE, _analysis, _short_plan, load

    plan = EditPlan.model_validate(_short_plan())
    dub = DubScript.model_validate(json.loads((FIX / "dub.json").read_text(encoding="utf-8")))
    u = Understanding.model_validate(load("understand.json"))

    def texts(on: bool):
        res = build(plan, u, _analysis(), DraftTemplate(SAMPLE), tmp_path, f"vi{on}", load_style("jp_telop"),
                    dub=dub, vi_subtitles=on)
        tl = res.writer.build_timeline()
        mats = {m["id"]: json.loads(m["content"])["text"] for m in tl["materials"]["texts"]}
        segs = [s for t in tl["tracks"] if t["type"] == "text" for s in t["segments"]]
        return res, {mats[s["material_id"]]: s for s in segs}

    res, on = texts(True)
    vi = [t for t in on if "Đô vật sumo" in t or "vốn bị ghét" in t]
    assert vi and any("TIẾNG VIỆT" in n for n in res.notes)
    ko = next(s for t, s in on.items() if "스모" in t)
    assert on[vi[0]]["clip"]["transform"]["y"] < ko["clip"]["transform"]["y"]  # nằm ngay dưới phụ đề chính
    assert on[vi[0]]["target_timerange"]["start"] == ko["target_timerange"]["start"]  # cùng lúc câu thuyết minh
    _, off = texts(False)
    assert not [t for t in off if "Đô vật sumo" in t]


def test_place_voices_rounded_speed_never_exceeds_file():
    # tốc độ lẻ (vd 1.23456…) làm tròn lên 3 chữ số → độ dài × tốc độ vẫn không được dài hơn file voice
    S = 1_000_000
    for v in (7_123_457, 9_876_543, 12_345_679, 10_000_001):
        pl = dub_io.place_voices([(0, 2.0, 5.3), (6 * S, 2.0, 3.0)], {1: v}, max_speed=1.25, hard_max_speed=1.4,
                                 max_delay_s=0.8)[1]
        assert round((pl["end"] - pl["start"]) * pl["speed"]) <= v


def test_writer_trims_tiny_overshoot(tmp_path):
    from app.capcut_writer import DraftTemplate, DraftWriter
    from tests.test_planner import SAMPLE

    w = DraftWriter(DraftTemplate(SAMPLE), tmp_path, "trim")
    seg = w.add_local_audio(tmp_path / "v.wav", 5_000_000, target_start=0, duration=4_000_100, speed=1.25)
    assert seg["source_timerange"]["duration"] <= 5_000_000  # lệch 125 µs → tự cắt đuôi, không báo lỗi
    with pytest.raises(ValueError):
        w.add_local_audio(tmp_path / "v.wav", 5_000_000, target_start=0, duration=4_500_000, speed=1.25)
