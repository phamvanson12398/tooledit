"""Test trên dự án mẫu thật do CapCut 9.5.0 tạo (samples/capcut_template, đã xóa định danh)."""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples" / "capcut_template"
sys.path.insert(0, str(ROOT / "tools"))

import inspect_draft  # noqa: E402
import make_probe_draft  # noqa: E402


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sample_is_plain_json_capcut_950():
    report = inspect_draft.inspect(SAMPLE)
    assert all(f["status"] == "json" for f in report["files"])
    timelines = [
        f["timeline"]
        for f in report["files"]
        if "timeline" in f and Path(f["file"]).name in ("draft_content.json", "template-2.tmp")
    ]
    assert len(timelines) == 4
    for tl in timelines:
        assert tl["platform"]["app_source"] == "cc"
        assert tl["platform"]["app_version"] == "9.5.0"
        assert tl["version"] == 360000


def test_four_timeline_copies_identical():
    files = make_probe_draft.timeline_files(SAMPLE)
    assert set(files) == {"GOC_CONTENT", "GOC_TEMPLATE2", "TRONG_CONTENT", "TRONG_TEMPLATE2"}
    contents = {p.read_bytes() for p in files.values()}
    assert len(contents) == 1


def test_library_resources_referenced_by_id():
    tl = load(SAMPLE / "draft_content.json")
    m = tl["materials"]
    assert m["transitions"][0]["effect_id"] == m["transitions"][0]["resource_id"]
    assert m["video_effects"][0]["resource_id"]
    assert m["effects"][0]["type"] == "filter"
    music = m["audios"][0]
    assert music["type"] == "music" and music["music_id"]
    assert "Cache/music" in music["path"]


def test_make_probe_labels_each_file(tmp_path: Path):
    src = tmp_path / "capcut_template"
    shutil.copytree(SAMPLE, src)
    dst = make_probe_draft.make_probe(src)
    for label, path in make_probe_draft.timeline_files(dst).items():
        text = json.loads(load(path)["materials"]["texts"][0]["content"])
        assert text["text"] == label
        assert text["styles"][0]["range"] == [0, len(label)]
    meta = load(dst / "draft_meta_info.json")
    assert meta["draft_name"] == "capcut_template_probe"
    # bản gốc không bị đụng tới
    original = json.loads(load(src / "draft_content.json")["materials"]["texts"][0]["content"])
    assert original["text"] != "GOC_CONTENT"
