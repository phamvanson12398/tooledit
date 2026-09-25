import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import inspect_draft  # noqa: E402


def make_timeline() -> dict:
    return {
        "version": 360000,
        "new_version": "140.0.0",
        "platform": {"app_source": "cc", "app_version": "9.5.0", "os": "windows"},
        "canvas_config": {"width": 1080, "height": 1920, "ratio": "original"},
        "duration": 5_000_000,
        "tracks": [{"type": "video", "segments": [{}, {}]}, {"type": "audio", "segments": [{}]}],
        "materials": {
            "videos": [{"path": "C:/x.mp4"}],
            "transitions": [{"name": "Mix", "effect_id": "123", "resource_id": "456"}],
            "audios": [{"name": "Song", "music_id": "789", "path": "C:/cache/a.mp3"}],
        },
    }


def test_plain_json_draft(tmp_path: Path):
    (tmp_path / "draft_content.json").write_text(json.dumps(make_timeline()), encoding="utf-8")
    report = inspect_draft.inspect(tmp_path)
    [entry] = report["files"]
    assert entry["status"] == "json"
    tl = entry["timeline"]
    assert tl["platform"]["app_version"] == "9.5.0"
    assert tl["resources"]["transitions"][0]["resource_id"] == "456"
    assert tl["resources"]["audios"][0]["music_id"] == "789"


def test_encrypted_like_file(tmp_path: Path):
    (tmp_path / "draft_content.json").write_bytes(b"\x8a\x01binarydata")
    [entry] = inspect_draft.inspect(tmp_path)["files"]
    assert entry["status"] == "encrypted?"


def test_nested_timeline_and_string_envelope(tmp_path: Path):
    nested = tmp_path / "Timelines" / "abc"
    nested.mkdir(parents=True)
    (nested / "draft_info.json").write_text(json.dumps(make_timeline()), encoding="utf-8")
    envelope = {"content": json.dumps(make_timeline())}
    (tmp_path / "template-2.tmp").write_text(json.dumps(envelope), encoding="utf-8")
    files = {e["file"].replace("\\", "/"): e for e in inspect_draft.inspect(tmp_path)["files"]}
    assert "timeline" in files["template-2.tmp"]
    assert "timeline" in files["Timelines/abc/draft_info.json"]


def test_bom_is_accepted(tmp_path: Path):
    (tmp_path / "draft_info.json").write_bytes(b"\xef\xbb\xbf" + json.dumps(make_timeline()).encode())
    [entry] = inspect_draft.inspect(tmp_path)["files"]
    assert entry["status"] == "json"
