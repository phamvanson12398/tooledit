import json
from pathlib import Path

import pytest

from app.capcut_writer import SEC, DraftTemplate
from app.director.fake import FakeDirector
from app.director.schemas import EditPlan, HookSet, PlanClip, Understanding, check_plan
from app.director.tasks import make_hooks, make_plan, understand
from app.planner import hook_io
from app.planner.builder import build, duck_keyframes, text_positions, zoom_keyframes
from app.planner.subtitles import build_cues, speech_intervals
from app.planner.timeline import TimeMap
from tests.test_director import make_analysis

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "director"
SAMPLE = ROOT / "samples" / "capcut_template"


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_timemap_with_hook_and_speed():
    clips = [PlanClip(source_start=10, source_end=12), PlanClip(source_start=20, source_end=26, speed=2.0)]
    tm = TimeMap(clips, offset_us=4 * SEC)
    assert tm.to_out(10) == 4 * SEC and tm.to_out(12) == 6 * SEC
    assert tm.to_out(23) == 6 * SEC + round(1.5 * SEC)
    assert tm.to_out(15) is None and tm.end == 9 * SEC


def test_cues_japanese_chunking_and_corrections():
    words = [{"start": 1.0 + i * 0.2, "end": 1.2 + i * 0.2, "word": ch} for i, ch in enumerate("高藤力なんか優勝は絶対させないと。")]
    segs = [{"start": 1.0, "end": 5.0, "text": "", "words": words}]
    tm = TimeMap([PlanClip(source_start=0, source_end=10)])
    u = Understanding.model_validate(load("understand.json"))
    cues = build_cues(segs, tm, "ja", 8, corrections=u.name_corrections)
    assert cues[0].text.startswith("貴闘力")
    assert all(len(c.text) <= 8 for c in cues)
    assert "".join(c.text for c in cues) == "貴闘力なんか優勝は絶対させないと。"
    assert all(a.end <= b.start for a, b in zip(cues, cues[1:]))


def test_cues_drop_cut_words_and_keep_spaces():
    words = [{"start": 0.0, "end": 0.4, "word": " Hello"}, {"start": 0.5, "end": 0.9, "word": " world"},
             {"start": 5.0, "end": 5.4, "word": " cut"}]
    tm = TimeMap([PlanClip(source_start=0, source_end=2)])
    cues = build_cues([{"start": 0, "end": 6, "text": "", "words": words}], tm, "en", 20)
    assert [c.text for c in cues] == ["Hello world"]
    assert speech_intervals(cues, pad_us=0) == [(cues[0].start, cues[0].end)]


def test_duck_keyframes():
    kfs = duck_keyframes(0, 10 * SEC, [(2 * SEC, 4 * SEC)], 0.1, 0.4, 250_000)
    vals = [(k.time, k.value) for k in kfs]
    assert vals[0] == (0, 0.4) and (2 * SEC, 0.1) in vals and (4 * SEC, 0.4) in vals and vals[-1][1] == 0.4
    assert all(a[0] < b[0] for a, b in zip(vals, vals[1:]))


def test_zoom_keyframes_inside_clip():
    plan = EditPlan.model_validate(load("plan.json"))
    tm = TimeMap(plan.clips)
    kfs = zoom_keyframes(plan.zooms, tm.placed[1], {"punch_scale": 1.15, "punch_in_s": 0.15})
    assert kfs[0].value == 1.0 and max(k.value for k in kfs) == 1.15
    assert all(0 <= k.time <= tm.placed[1].out_duration for k in kfs)
    assert zoom_keyframes(plan.zooms, tm.placed[0], {}) == []


def test_text_positions_respect_safe_area():
    pos = text_positions("4:3", {"top": 0.08, "bottom": 0.18, "right": 0.12, "left": 0.04})
    assert pos["bottom"] >= -1 + 2 * 0.18 and pos["top"] <= 1 - 2 * 0.08 and pos["x"] < 0
    assert pos["bottom"] < -810 / 1920  # vẫn nằm dưới khối 4:3


def test_check_plan_rules():
    plan = EditPlan.model_validate(load("plan.json"))
    assert check_plan(plan, duration=173.8, hook_s=4, min_s=30) == []
    errs = check_plan(plan, duration=173.8, hook_s=4)  # tổng ~41s < 60s trong khi footage đủ dài
    assert any("ngắn hơn" in e for e in errs)
    bad = plan.model_copy(update={"clips": [PlanClip(source_start=0, source_end=160)]})
    assert any("vượt" in e for e in check_plan(bad, 173.8, hook_s=5))


def test_hooks_and_plan_tasks_with_fake(tmp_path):
    a = make_analysis(tmp_path, duration=60.0)
    d = FakeDirector()
    u = understand(d, a)
    hs = make_hooks(d, a, u)
    assert isinstance(hs, HookSet) and len(hs.options) == 3
    assert "Điều cấm" in d.calls[-1]["prompt"] and "貴闘力" in d.calls[-1]["prompt"]
    tpl = DraftTemplate(SAMPLE)
    music = [m for m in tpl.library if m.kind == "music"]
    plan = make_plan(FakeDirector(responses={"plan": _short_plan()}), a, u, {"name": "tiktok_retention"},
                     hook=hs.options[0], hook_s=4.0, music_items=music, business=True)
    assert plan.music.name == "Keep It High"


def _short_plan():
    p = load("plan.json")
    p["clips"] = [{"source_start": 1.0, "source_end": 45.0, "speed": 1.0, "ratio": None, "purpose_vi": ""}]
    return p


def test_business_client_rejects_non_commercial_music(tmp_path):
    a = make_analysis(tmp_path, duration=60.0)
    u = understand(FakeDirector(), a)
    tpl = DraftTemplate(SAMPLE)
    music = [m for m in tpl.library if m.kind == "music"]
    bad, good = _short_plan(), _short_plan()
    bad["music"]["name"] = "Abstraction"
    d = FakeDirector(responses={"plan": [bad, good]})
    make_plan(d, a, u, {}, music_items=music, business=True)
    assert len(d.calls) == 2 and "Commercial" in d.calls[1]["prompt"]


def test_hook_io(tmp_path):
    hs = HookSet.model_validate(load("hooks.json"))
    hook_io.save_hooks(tmp_path, [hs], {1: 2})
    sets, choices = hook_io.load_hooks(tmp_path)
    assert choices == {1: 2} and sets[0].options[1].hook_type == "contrast"
    txt = hook_io.write_hook_scripts(tmp_path, sets, choices).read_text(encoding="utf-8")
    assert "video01_hook.wav" in txt and "今も嫌われてる" in txt
    assert hook_io.missing_voices(tmp_path, choices) == ["video01_hook.wav"]
    (tmp_path / "voice" / "video01_hook.m4a").write_bytes(b"x")
    assert hook_io.find_voice(tmp_path, 1).suffix == ".m4a" and hook_io.missing_voices(tmp_path, choices) == []
    assert "=== VIDEO 01 ===" in hook_io.hook_table(sets)


def test_build_draft_end_to_end(tmp_path):
    tpl = DraftTemplate(SAMPLE)
    plan = EditPlan.model_validate(load("plan.json"))
    u = Understanding.model_validate(load("understand.json"))
    hs = HookSet.model_validate(load("hooks.json"))
    words = [{"start": 7.3 + i * 0.3, "end": 7.5 + i * 0.3, "word": ch} for i, ch in enumerate("高藤力なんか優勝は絶対させないと。")]
    analysis = {
        "scenes": {"path": "C:/f/test.mp4", "duration": 173.8, "width": 1920, "height": 1080, "scenes": []},
        "transcript": {"language": "ja", "segments": [{"start": 7.3, "end": 13.6, "text": "", "words": words}]},
        "subjects": {"points": [[t, 0.7, 0.5] for t in range(0, 170)]},
    }
    res = build(plan, u, analysis, tpl, tmp_path, "khach_job_video01", {
        "subtitle": {"max_chars": {"ja": 10}}, "hook": {"min_s": 3, "max_s": 5}, "zoom": {}, "music": {}},
        hook=hs.options[0], voice=(Path("C:/job/voice/video01_hook.wav"), 3_500_000),
        clean_audio=Path("C:/job/analysis/audio/clean_00.wav"))
    tl = res.writer.build_timeline()
    kinds = [t["type"] for t in tl["tracks"]]
    assert kinds.count("video") >= 1 and "text" in kinds and kinds.count("audio") >= 2
    video_segs = [s for t in tl["tracks"] if t["type"] == "video" for s in t["segments"]]
    assert len(video_segs) == 4 and video_segs[0]["target_timerange"]["start"] == 0  # hook + 3 clip
    assert video_segs[1]["target_timerange"]["start"] == 3_700_000  # hook = voice + 0.2s
    assert res.duration_us == tl["duration"]
    texts = [json.loads(m["content"])["text"] for m in tl["materials"]["texts"]]
    assert "なぜ病院に？" in texts and "嫌われた" in texts and any(t.startswith("貴闘力") for t in texts)
    assert {m["kind"] for m in res.missing_assets} == {"sfx"}
    crop = next(m for m in tl["materials"]["videos"])["crop"]
    assert crop["upper_left_x"] > 0.2  # bám chủ thể lệch phải (cx=0.7)
    res.writer.save()
