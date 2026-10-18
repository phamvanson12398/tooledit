"""Tiếng Đức (chủ dự án yêu cầu 18/10): thêm vào danh sách ngôn ngữ bản TikTok."""

from app import config
from app.director.policy import find_bad_words
from app.director.tasks import (LANGUAGE_NAMES, MARKETS, TARGET_LANGS, latin_language, script_language,
                                wrong_language)


def test_german_is_a_target_language():
    assert "de" in TARGET_LANGS and LANGUAGE_NAMES["de"] == "tiếng Đức" and "Đức" in MARKETS["de"]
    assert "de" in config.load("whisper")["languages"]
    assert config.load("localize")["markets"]["de"]["audience"]
    assert config.load("subtitles")["limits"]["de"]["max_chars_per_line"] > 20
    assert config.load("sell")["voice_cps"]["de"] > 0


def test_tell_english_from_german():
    assert latin_language("Das ist wirklich nicht so einfach, aber wir schaffen das schon.") == "de"
    assert latin_language("This is the best ramen I have ever had, and it was so cheap.") == "en"
    assert latin_language("Okay") is None
    assert script_language("Heute zeige ich dir, wie man die beste Suppe der Welt kocht, und es ist einfach.") == "de"


def test_german_target_rejects_english_or_asian_lines():
    assert not wrong_language("Schau mal, wie lecker das aussieht!", "de")
    assert wrong_language("Look at this, it is the best thing ever and you have to try it", "de")
    assert wrong_language("これは本当に美味しいです", "de")
    assert not wrong_language("Tokyo Tower bei Nacht", "de")  # tên riêng / câu ngắn không rõ → không chặn
    assert wrong_language("Das ist wirklich nicht so einfach, aber wir schaffen das", "en")


def test_german_bad_words_match_word_start():
    assert find_bad_words("Was für eine Scheiße!", "de") == ["scheiße"]
    assert find_bad_words("Wir abonnieren nichts", "de") == []


def test_home_has_german_option(tmp_path):
    from fastapi.testclient import TestClient

    from app.jobs.job import Job
    from app.web.server import create_app

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    app = create_app(tmp_path / "jobs", lambda root, log: None)
    app.state.worker.start = lambda job_id, action=None: True
    c = TestClient(app)
    assert "<option value=\"de\">Đổi sang tiếng Đức (Deutsch)</option>" in c.get("/").text
    for mode in ("dub", "sell", "ideas"):
        r = c.post("/jobs", data={"footage": str(f), "mode": mode, "target_language": "de"}, follow_redirects=False)
        assert r.status_code == 303, (mode, r.text[:300])
        assert Job.load(tmp_path / "jobs", r.headers["location"].rsplit("/", 1)[1]).options.target_language == "de"
