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
    plan = EditPlan.model_validate({**load("plan.json"), "default_ratio": "4:3"})  # bố cục cũ (classic)
    u = Understanding.model_validate(load("understand.json"))
    hs = HookSet.model_validate(load("hooks.json"))
    words = [{"start": 7.3 + i * 0.3, "end": 7.5 + i * 0.3, "word": ch} for i, ch in enumerate("高藤力なんか優勝は絶対させないと。")]
    analysis = {
        "scenes": {"path": "C:/f/test.mp4", "duration": 173.8, "width": 1920, "height": 1080, "scenes": []},
        "transcript": {"language": "ja", "segments": [{"start": 7.3, "end": 13.6, "text": "", "words": words}]},
        "subjects": {"points": [[t, 0.7, 0.5] for t in range(0, 170)]},
    }
    res = build(plan, u, analysis, tpl, tmp_path, "khach_job_video01", {
        "subtitle": {"max_chars": {"ja": 10}}, "hook": {"min_s": 3, "max_s": 5}, "zoom": {}, "music": {},
        "layout": "classic"},
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
    canvases = tl["materials"]["canvases"]
    assert canvases and all(c["type"] == "canvas_blur" and c["blur"] == 0.375 for c in canvases)
    res.writer.save()


def test_four_titles_layout_like_reference(tmp_path):
    """Bố cục mặc định theo video mẫu: nền đen, khối 16:9 giữa, 2 tiêu đề trên + 2 dưới suốt video."""
    from app.capcut_writer.layout import row_to_y
    from app.planner.builder import layout_for
    from app.styles import load_style

    style = load_style("jp_telop")
    four = layout_for(style)
    assert four and four["block_ratio"] == "16:9"
    tpl = DraftTemplate(SAMPLE)
    plan = EditPlan.model_validate(load("plan.json"))
    u = Understanding.model_validate(load("understand.json"))
    res = build(plan, u, _analysis(), tpl, tmp_path, "four", style)
    tl = res.writer.build_timeline()
    mats = {m["id"]: json.loads(m["content"])["text"] for m in tl["materials"]["texts"]}
    segs = {mats[s["material_id"]]: s for t in tl["tracks"] if t["type"] == "text" for s in t["segments"]}
    rows = four["title_rows"]
    for text, row in zip(plan.titles_top + plan.titles_bottom, rows):
        seg = segs[text]
        assert abs(seg["clip"]["transform"]["y"] - row_to_y(row)) < 1e-6
        assert seg["target_timerange"]["start"] == 0 and seg["target_timerange"]["duration"] == res.duration_us
        assert seg["clip"]["scale"]["x"] > 1.0  # phóng to cho dòng tràn gần hết chiều ngang
    assert segs["曙との関係について"]["clip"]["transform"]["x"] > 0  # nhãn chủ đề góc phải
    sub = segs[next(t for t in segs if t.startswith("優勝"))]
    assert -0.4 < sub["clip"]["transform"]["y"] < 0  # phụ đề trong khối video
    crop = tl["materials"]["videos"][0]["crop"]
    assert crop["upper_left_x"] == 0 and crop["lower_right_x"] == 1  # 16:9 giữ nguyên khung
    assert all(c["type"] == "canvas_color" for c in tl["materials"]["canvases"])
    assert not [n for n in res.notes if "thiếu dòng tiêu đề" in n]


def test_plan_requires_four_titles(tmp_path):
    from app.director.schemas import check_titles

    p = load("plan.json")
    assert check_titles(EditPlan.model_validate(p), 12) == []
    p["titles_bottom"] = ["一行だけ"]
    assert check_titles(EditPlan.model_validate(p), 12)
    p["titles_bottom"] = ["とても長すぎるタイトル行ですよね", "x"]
    assert any("tối đa" in e for e in check_titles(EditPlan.model_validate(p), 12))


def _analysis():
    words = [{"start": 7.3 + i * 0.3, "end": 7.5 + i * 0.3, "word": ch} for i, ch in enumerate("優勝は絶対させないと。")]
    return {"scenes": {"path": "C:/f/box.mp4", "duration": 173.8, "width": 1920, "height": 1080, "scenes": []},
            "transcript": {"language": "ja", "segments": [{"start": 7.3, "end": 11.0, "text": "", "words": words}]},
            "subjects": {"points": []}}


def test_replay_clip_and_sfx_from_library(tmp_path):
    from app.capcut_writer.template import LibraryItem
    from app.styles import load_style

    tpl = DraftTemplate(SAMPLE)
    tpl.library.append(LibraryItem(kind="sfx", name="Punch Hit", resource_id="999",
                                   material={**next(m for m in tpl.library if m.kind == "music").material,
                                             "music_id": "999", "name": "Punch Hit", "duration": 1_200_000}))
    p = load("plan.json")
    p["clips"].append({"source_start": 19.2, "source_end": 21.0, "speed": 0.4, "replay": True, "purpose_vi": "replay"})
    p["sfx"] = [{"source_time": 19.3, "kind": "boom", "name": "Punch Hit", "reason_vi": "cú đấm"},
                {"source_time": 20.0, "kind": "whoosh", "name": None, "reason_vi": "chuyển"}]
    plan = EditPlan.model_validate(p)
    assert check_plan(plan, 173.8, min_s=10) == []  # replay được phép lặp footage
    u = Understanding.model_validate(load("understand.json"))
    res = build(plan, u, _analysis(), tpl, tmp_path, "sport", load_style("sports_analysis"))
    tl = res.writer.build_timeline()
    texts = [json.loads(m["content"])["text"] for m in tl["materials"]["texts"]]
    assert "リプレイ" in texts
    videos = [s for t in tl["tracks"] if t["type"] == "video" for s in t["segments"]]
    replay = videos[-1]
    assert replay["speed"] == 0.4 and replay["volume"] == 0.0
    assert replay["target_timerange"]["duration"] == round(1.8 / 0.4 * SEC)
    audio_names = [m["name"] for m in tl["materials"]["audios"]]
    assert "Punch Hit" in audio_names
    assert [m["what"] for m in res.missing_assets] == ["whoosh"]


def test_replay_rules():
    p = load("plan.json")
    p["clips"].append({"source_start": 19.2, "source_end": 21.0, "speed": 1.0, "replay": True})
    p["clips"].append({"source_start": 50.0, "source_end": 52.0, "speed": 0.5})
    errs = check_plan(EditPlan.model_validate(p), 173.8, min_s=10)
    assert any("phải quay chậm" in e for e in errs) and any("chỉ clip replay" in e for e in errs)


def test_styles_available_and_loadable():
    from app.styles import available_styles, load_style, styles_for_prompt

    styles = available_styles()
    for name in ("tiktok_retention", "podcast", "sports_analysis", "vlog", "entertainment", "jp_telop"):
        assert name in styles and styles[name]["name_vi"]
        st = load_style(name)
        assert st["director_brief"] and st["subtitle"]["size"] and st["hook_text"]["size"] >= 30
    assert "sports_analysis:" in styles_for_prompt()


def test_understand_rejects_unknown_style(tmp_path):
    bad = load("understand.json")
    bad["suggested_style"] = "khong_co"
    d = FakeDirector({"understand": [bad, load("understand.json")]})
    understand(d, make_analysis(tmp_path))
    assert len(d.calls) == 2 and "sports_analysis" in d.calls[1]["prompt"]


def test_audio_kind_and_merge_library(tmp_path):
    import shutil

    from app.capcut_writer.template import audio_kind

    assert audio_kind({"type": "music", "duration": 2_000_000}) == "sfx"
    assert audio_kind({"type": "music", "duration": 60_000_000}) == "music"
    assert audio_kind({"type": "sound", "duration": 60_000_000}) == "sfx"
    a = DraftTemplate(SAMPLE)
    shutil.copytree(SAMPLE, tmp_path / "coll")
    assert a.merge_library(DraftTemplate(tmp_path / "coll")) == 0  # trùng hết
    moods = {i.name: i.mood for i in a.library if i.kind == "music"}
    assert "vui" in moods["Keep It High"]


def test_decor_effects_stickers_transitions_filter(tmp_path):
    from app.styles import load_style

    tpl = DraftTemplate(SAMPLE)
    names = {k: next(i.name for i in tpl.library if i.kind == k) for k in ("video_effect", "sticker", "transition", "filter")}
    p = load("plan.json")
    p.update({"effects": [{"source_time": 19.3, "duration": 0.8, "name": names["video_effect"]}],
              "stickers": [{"source_time": 20.0, "duration": 1.5, "name": names["sticker"], "position": "top_left"}],
              "transitions": [{"after_clip": 0, "name": names["transition"]}],
              "filter": names["filter"],
              "emphasis": [{"source_time": 8.0, "text": "A"}, {"source_time": 12.0, "text": "B"}]})
    plan = EditPlan.model_validate(p)
    assert check_plan(plan, 173.8, min_s=10) == []
    u = Understanding.model_validate(load("understand.json"))
    res = build(plan, u, _analysis(), tpl, tmp_path, "deco", load_style("entertainment"))
    tl = res.writer.build_timeline()
    kinds = [t["type"] for t in tl["tracks"]]
    assert "effect" in kinds and "sticker" in kinds and "filter" in kinds
    first_clip = next(t for t in tl["tracks"] if t["type"] == "video")["segments"][0]
    trans_ids = {m["id"] for m in tl["materials"]["transitions"]}
    assert trans_ids & set(first_clip["extra_material_refs"])
    colors = [json.loads(m["content"])["styles"][0]["fill"]["content"]["solid"]["color"]
              for m in tl["materials"]["texts"] if json.loads(m["content"])["text"] in ("A", "B")]
    assert len(colors) == 2 and colors[0] != colors[1]  # chữ nhấn đổi màu luân phiên
    bad = EditPlan.model_validate({**p, "transitions": [{"after_clip": 5, "name": "x"}]})
    assert any("after_clip" in e for e in check_plan(bad, 173.8, min_s=10))


def test_sports_layout_like_reference(tmp_path):
    """Kiểu thể thao theo video mẫu boxing: nền đen, khối 9:10 phóng vào pha đấu, không tiêu đề,
    phụ đề vàng cụm ngắn trong khối, mũi tên xanh chỉ chi tiết."""
    from app.planner.builder import ARROW_ROTATION, arrow_placement, block_point
    from app.styles import layout_for, load_style

    style = load_style("sports_analysis")
    lay = layout_for(style)
    assert lay["name"] == "sports_focus" and not lay["titles"] and lay["block_ratio"] == "9:10"
    p = load("plan.json")
    p["arrows"] = [{"source_time": 8.0, "x": 0.5, "y": 0.5, "points": "down_right", "duration": 1.0},
                   {"source_time": 9.0, "x": 0.01, "y": 0.5, "points": "left"}]  # điểm thứ 2 bị cắt mất
    plan = EditPlan.model_validate(p)
    assert check_plan(plan, 173.8, min_s=10) == []
    tpl = DraftTemplate(SAMPLE)
    u = Understanding.model_validate(load("understand.json"))
    a = _analysis()
    a["subjects"] = {"points": [[t, 0.5, 0.5] for t in range(0, 170)]}
    res = build(plan, u, a, tpl, tmp_path, "sport", style)
    tl = res.writer.build_timeline()
    mats = {m["id"]: m for m in tl["materials"]["texts"]}
    segs = [(json.loads(mats[s["material_id"]]["content"])["text"], s)
            for t in tl["tracks"] if t["type"] == "text" for s in t["segments"]]
    texts = [t for t, _ in segs]
    assert not set(plan.titles_top + plan.titles_bottom) & set(texts)  # không có dòng tiêu đề
    arrows = [s for t, s in segs if t == "→"]
    assert len(arrows) == 1 and arrows[0]["clip"]["rotation"] == ARROW_ROTATION["down_right"]
    ax, ay = arrows[0]["clip"]["transform"]["x"], arrows[0]["clip"]["transform"]["y"]
    assert ax < 0 and ay > 0  # nằm phía trên-trái điểm cần chỉ (giữa khung)
    assert any("ngoài khung" in n for n in res.notes)
    subs = [t for t in texts if t != "→" and t not in (e.text for e in plan.emphasis)]
    assert subs and all(len(t) <= 7 for t in subs)  # cụm ngắn kiểu video mẫu
    crop = tl["materials"]["videos"][0]["crop"]
    assert 0.2 < crop["upper_left_x"] < 0.3  # 16:9 → 9:10: lấy ~51% chiều ngang quanh chủ thể
    assert all(c["type"] == "canvas_color" for c in tl["materials"]["canvases"])
    # hình học
    assert block_point(0.5, 0.5, None, "9:10") == (0.0, 0.0)
    x, y, rot = arrow_placement((0.0, 0.0), "down", 96)
    assert x == 0 and y == 0.1 and rot == 90  # mũi tên chỉ xuống nằm phía trên điểm


def test_plan_sends_frames_only_for_arrow_styles(tmp_path):
    from app.styles import load_style

    a = make_analysis(tmp_path, duration=60.0)
    u = understand(FakeDirector(), a)
    music = [m for m in DraftTemplate(SAMPLE).library if m.kind == "music"]
    d = FakeDirector(responses={"plan": _short_plan()})
    make_plan(d, a, u, load_style("sports_analysis"), music_items=music)
    assert d.calls[-1]["images"] and "Mũi tên chỉ chi tiết" in d.calls[-1]["prompt"]
    assert "(bố cục cố định)" in d.calls[-1]["prompt"]
    d2 = FakeDirector(responses={"plan": {**_short_plan(), "arrows": [
        {"source_time": 5.0, "x": 0.5, "y": 0.5, "points": "down"}]}})
    with pytest.raises(Exception):
        make_plan(d2, a, u, load_style("jp_telop"), music_items=music)  # kiểu không dùng mũi tên → sai khuôn
    assert any("không dùng mũi tên" in c["prompt"] for c in d2.calls[1:])
