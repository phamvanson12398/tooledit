import json
from pathlib import Path

import pytest

from app.capcut_writer import (
    SEC, DraftTemplate, DraftWriter, Keyframe, TextStyle, VideoSource, block_crop, block_size,
)
from app.capcut_writer.layout import band_centers
from app.capcut_writer.media import video_source_from_probe
from app.capcut_writer.template import main_timeline_path, read_json, timeline_copies
from app.capcut_writer.writer import utf16_len

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "capcut_template"
VERT = VideoSource(Path("C:/footage/a.mp4"), 1080, 1920, 60 * SEC)
WIDE = VideoSource(Path("C:/footage/b.mp4"), 3840, 2160, 20 * SEC)


@pytest.fixture(scope="module")
def tpl():
    return DraftTemplate(SAMPLE)


def build(tpl, tmp_path):
    w = DraftWriter(tpl, tmp_path, "khach_job01_video01")
    trans = tpl.find("transition")
    w.add_video(VERT, target_start=0, duration=3 * SEC, source_start=5 * SEC,
                keyframes=[Keyframe("scale", 0, 1.0), Keyframe("scale", 3 * SEC, 1.2)],
                transition=trans)
    w.add_video(WIDE, target_start=3 * SEC, duration=2 * SEC, crop=block_crop(3840, 2160, "4:3"), speed=1.5)
    w.add_text("이게 1조짜리입니다", start=0, duration=2 * SEC, y=-0.6,
               style=TextStyle(size=12, color=(1, 1, 0), stroke_color=(0, 0, 0)),
               animations=[a for a in tpl.library if a.kind == "text_animation"])
    w.add_text("地獄の合図", start=SEC, duration=2 * SEC, y=0.7)  # chồng thời gian → làn chữ thứ 2
    w.add_sticker(tpl.find("sticker"), start=SEC, duration=SEC, x=0.5, y=0.5, scale=0.6)
    w.add_effect(tpl.find("video_effect"), start=0, duration=SEC)
    w.add_filter(tpl.find("filter"), start=0, duration=5 * SEC)
    w.add_music(tpl.find("music", "Keep It High"), target_start=0, duration=5 * SEC, volume=0.3)
    w.add_local_audio(Path("C:/job/voice/video01_hook.wav"), 4 * SEC, target_start=0, duration=3 * SEC)
    return w


def test_template_prototypes_and_library(tpl):
    assert main_timeline_path(SAMPLE).parent.parent.name == "Timelines"
    assert set(tpl.prototypes) == {"video", "audio", "text", "sticker", "effect", "filter"}
    kinds = {i.kind for i in tpl.library}
    assert kinds == {"video_effect", "filter", "transition", "sticker", "music", "text_animation"}
    music = {i.name: i.is_vip for i in tpl.library if i.kind == "music"}
    assert music == {"Abstraction": True, "Keep It High": False}
    assert {a.category for a in tpl.library if a.kind == "text_animation"} == {"in", "loop", "out"}


def test_build_timeline_structure(tpl, tmp_path):
    tl = build(tpl, tmp_path).build_timeline()
    assert tl["duration"] == 5 * SEC
    types = [t["type"] for t in tl["tracks"]]
    assert types == ["video", "effect", "filter", "text", "text", "sticker", "audio", "audio"]
    ids = {}
    for items in tl["materials"].values():
        if isinstance(items, list):
            for m in items:
                if isinstance(m, dict) and "id" in m:
                    assert m["id"] not in ids, "id bị trùng"
                    ids[m["id"]] = m
    for t in tl["tracks"]:
        for s in t["segments"]:
            assert s["material_id"] in ids
            for ref in s["extra_material_refs"]:
                assert ref in ids
    v1, v2 = tl["tracks"][0]["segments"]
    assert v1["source_timerange"] == {"start": 5 * SEC, "duration": 3 * SEC}
    assert v2["source_timerange"]["duration"] == 3 * SEC  # 2s * speed 1.5
    assert v1["common_keyframes"][0]["property_type"] == "KFTypeScaleX"
    assert any(ids[r].get("type") == "transition" for r in v1["extra_material_refs"])
    assert ids[v2["material_id"]]["crop"]["upper_left_x"] == pytest.approx(0.125)
    text = json.loads(ids[tl["tracks"][3]["segments"][0]["material_id"]]["content"])
    assert text["text"] == "이게 1조짜리입니다"
    assert text["styles"][0]["range"] == [0, utf16_len("이게 1조짜리입니다")]
    assert text["styles"][0]["strokes"]
    local = [m for m in tl["materials"]["audios"] if m["type"] == "extract_music"]
    assert local and local[0]["path"] == "C:/job/voice/video01_hook.wav"


def test_save_writes_all_copies_and_meta(tpl, tmp_path):
    w = build(tpl, tmp_path)
    dst = w.save()
    contents = {p.read_text(encoding="utf-8") for p in timeline_copies(dst)}
    assert len(contents) == 1
    assert not list((dst / "Timelines").glob("*/attachment/patch"))
    meta = read_json(dst / "draft_meta_info.json")
    assert meta["draft_name"] == "khach_job01_video01"
    assert meta["draft_fold_path"] == dst.as_posix()
    assert meta["tm_duration"] == 5 * SEC
    videos = [v for g in meta["draft_materials"] if g["type"] == 0 for v in g["value"]]
    assert {v["file_Path"] for v in videos} == {"C:/footage/a.mp4", "C:/footage/b.mp4"}
    with pytest.raises(FileExistsError):
        w.save()


def test_source_range_checked(tpl, tmp_path):
    w = DraftWriter(tpl, tmp_path, "x")
    with pytest.raises(ValueError):
        w.add_video(VERT, target_start=0, duration=10 * SEC, source_start=55 * SEC)


def test_layout_math():
    assert block_size("4:3") == (1080, 810)
    assert block_size("1:1") == (1080, 1080)
    c = block_crop(1920, 1080, "1:1", center_x=0.9)
    assert c.right == pytest.approx(1.0) and c.right - c.left == pytest.approx(1080 / 1920)
    c = block_crop(1080, 1920, "4:3")
    assert c.left == 0 and c.bottom - c.top == pytest.approx((1080 / 1920) / (4 / 3))
    top, bottom = band_centers("4:3")
    assert top == pytest.approx((810 / 1920 + 1) / 2) and bottom == -top


def test_probe_parsing_rotation():
    info = {"streams": [{"codec_type": "video", "width": 1920, "height": 1080,
                         "side_data_list": [{"rotation": -90}]}, {"codec_type": "audio"}],
            "format": {"duration": "12.5"}}
    src = video_source_from_probe(Path("x.mp4"), info)
    assert (src.width, src.height, src.duration, src.has_audio) == (1080, 1920, 12_500_000, True)


def test_local_audio_matches_capcut_written_material(tpl, tmp_path):
    """Mẫu lần 3 có file kkk2.wav do CapCut 9.5.0 tự thêm: vật liệu tool ghi phải khớp các trường chính."""
    real = next(a for a in tpl.timeline["materials"]["audios"] if a["type"] == "extract_music")
    w = DraftWriter(tpl, tmp_path, "x")
    w.add_local_audio(Path("C:/job/voice/video01_hook.wav"), 4 * SEC, target_start=0, duration=3 * SEC)
    mine = next(a for a in w.build_timeline()["materials"]["audios"] if a["type"] == "extract_music")
    for key in ("type", "category_name", "app_id", "check_flag", "music_id", "local_material_id", "category_id"):
        assert mine[key] == real[key], key
    assert set(real) <= set(mine)  # không thiếu trường nào CapCut ghi
    seg = next(s for t in w.build_timeline()["tracks"] if t["type"] == "audio" for s in t["segments"])
    kinds = sorted(k for k, items in w._materials.items() for m in items if m["id"] in seg["extra_material_refs"])
    assert kinds == ["beats", "placeholder_infos", "sound_channel_mappings", "speeds", "vocal_separations"]


def test_commercial_label_from_config(tpl):
    music = {i.name: i for i in tpl.library if i.kind == "music"}
    assert music["Keep It High"].commercial and not music["Abstraction"].commercial
    assert all(i.name != "kkk2.wav" for i in tpl.library)  # âm thanh local không phải tài nguyên thư viện
    plain = DraftTemplate(SAMPLE, labels={})
    assert not any(i.commercial for i in plain.library)
