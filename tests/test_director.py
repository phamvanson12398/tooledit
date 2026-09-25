import json
from pathlib import Path

import pytest

from app.director.base import DirectorError, render_prompt
from app.director.claude_cli import build_command, parse_output
from app.director.fake import FakeDirector
from app.director.schemas import TimeRange, Understanding, check_ranges
from app.director.tasks import format_transcript, pick_evenly, understand

ROOT = Path(__file__).resolve().parents[1]
GOOD = json.loads((ROOT / "tests/fixtures/director/understand.json").read_text(encoding="utf-8"))


def make_analysis(tmp_path: Path, duration=60.0) -> Path:
    a = tmp_path / "analysis"
    (a / "frames").mkdir(parents=True)
    frames = []
    for i in range(20):
        f = a / "frames" / f"00_{i * 3:08.2f}.jpg"
        f.write_bytes(b"\xff\xd8")
        frames.append({"footage": 0, "t": i * 3.0, "file": f.relative_to(a).as_posix()})
    (a / "frames.json").write_text(json.dumps(frames), encoding="utf-8")
    (a / "transcript.json").write_text(json.dumps([{"footage": 0, "language": "ja", "segments": [
        {"start": 1.0, "end": 3.0, "text": "こんにちは", "words": []}]}]), encoding="utf-8")
    (a / "scenes.json").write_text(json.dumps([{"footage": 0, "duration": duration, "width": 1920, "height": 1080,
                                                "scenes": [{"index": 0, "start": 0, "end": duration}]}]),
                                   encoding="utf-8")
    (a / "subjects.json").write_text(json.dumps([{"footage": 0, "points": [], "face_count_max": 2}]),
                                     encoding="utf-8")
    return a


def test_persona_is_prepended_to_every_prompt():
    p = render_prompt("understand", {k: "x" for k in (
        "styles", "client_style", "duration", "width", "height", "scene_count", "language", "scenes",
        "transcript", "frames")})
    assert p.startswith("# Vai trò") and "editor_notes" in p and "# Nhiệm vụ: hiểu nội dung" in p
    assert "{{" not in p
    with pytest.raises(KeyError):
        render_prompt("understand", {})


def test_understand_with_fake_director(tmp_path):
    a = make_analysis(tmp_path)
    d = FakeDirector()
    r = understand(d, a)
    assert isinstance(r, Understanding) and r.suggested_style == "jp_telop"
    call = d.calls[0]
    assert len(call["images"]) == 12  # chỉ gửi 12/20 khung hình
    assert "[1.0-3.0] こんにちは" in call["prompt"]


def test_retry_when_moment_outside_footage(tmp_path):
    a = make_analysis(tmp_path, duration=30.0)  # key moment 35.3-42.5 vượt quá 30s
    fixed = json.loads(json.dumps(GOOD))
    fixed["key_moments"] = [{"start": 5, "end": 8, "why_vi": "ok"}]
    d = FakeDirector({"understand": [GOOD, fixed]})
    r = understand(d, a)
    assert len(d.calls) == 2 and "vượt quá độ dài footage" in d.calls[1]["prompt"]
    assert r.key_moments[0].start == 5


def test_gives_up_after_max_attempts(tmp_path):
    a = make_analysis(tmp_path)
    bad = {"summary_vi": "thiếu trường"}
    d = FakeDirector({"understand": [bad]}, max_attempts=2)
    with pytest.raises(DirectorError):
        understand(d, a)
    assert len(d.calls) == 2


def test_check_ranges():
    errs = check_ranges([TimeRange(start=5, end=3), TimeRange(start=1, end=100)], duration=50)
    assert len(errs) == 2


def test_build_command_never_uses_bare():
    cmd = build_command("claude", {"type": "object"}, model="sonnet", with_images=True)
    assert "--bare" not in cmd and cmd[:2] == ["claude", "-p"]
    assert cmd[cmd.index("--tools") + 1] == "Read"
    assert cmd[cmd.index("--output-format") + 1] == "json"
    assert "--json-schema" in cmd and cmd[cmd.index("--model") + 1] == "sonnet"
    assert build_command("claude", {})[build_command("claude", {}).index("--tools") + 1] == ""


def test_parse_output_variants():
    assert parse_output(json.dumps({"type": "result", "subtype": "success", "structured_output": {"a": 1}})) == {"a": 1}
    assert parse_output(json.dumps({"subtype": "success", "result": "Đây: {\"a\": 2}"})) == {"a": 2}
    with pytest.raises(DirectorError, match="chưa đăng nhập"):
        parse_output(json.dumps({"type": "result", "is_error": True, "result": "Not logged in · Please run /login"}))
    with pytest.raises(DirectorError):
        parse_output("không phải json")


def test_helpers():
    assert pick_evenly(list(range(10)), 3) == [0, 3, 6]
    assert format_transcript([{"start": 0, "end": 1, "text": "a" * 50}], max_chars=20).endswith("(cắt bớt)")
