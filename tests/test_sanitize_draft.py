import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import sanitize_draft  # noqa: E402


def test_sanitize_text_paths_and_ids():
    data = {
        "path": "C:/Users/alice/Downloads/a.mp4",
        "root": "C:\\Users\\alice\\AppData",
        "platform": {"device_id": "abc123", "mac_address": "ff", "app_version": "9.5.0"},
    }
    out = json.loads(sanitize_draft.sanitize_text(json.dumps(data)))
    assert out["path"] == "C:/Users/<USER>/Downloads/a.mp4"
    assert out["root"] == "C:\\Users\\<USER>\\AppData"
    assert out["platform"] == {"device_id": "", "mac_address": "", "app_version": "9.5.0"}


def test_sanitize_draft_skips_media_and_bak(tmp_path: Path):
    src = tmp_path / "src"
    (src / "Timelines" / "x").mkdir(parents=True)
    (src / "draft_content.json").write_text('{"path":"C:/Users/bob/v.mp4"}', encoding="utf-8")
    (src / "draft_content.json.bak").write_text("{}", encoding="utf-8")
    (src / "draft_cover.jpg").write_bytes(b"\xff\xd8")
    (src / "Timelines" / "x" / "template-2.tmp").write_text('{"device_id":"d"}', encoding="utf-8")
    dst = tmp_path / "dst"
    written = {p.relative_to(dst).as_posix() for p in sanitize_draft.sanitize_draft(src, dst)}
    assert written == {"draft_content.json", "Timelines/x/template-2.tmp"}
    assert "<USER>" in (dst / "draft_content.json").read_text(encoding="utf-8")
    assert (dst / "Timelines" / "x" / "template-2.tmp").read_text(encoding="utf-8") == '{"device_id":""}'
