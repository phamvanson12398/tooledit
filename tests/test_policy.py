"""Tuân thủ chính sách TikTok: đoạn vi phạm bị cắt khỏi video, hook, chữ trên màn hình, caption."""

import json

from app.capcut_writer import DraftTemplate
from app.director.base import render_prompt
from app.director.fake import FakeDirector
from app.director.policy import (
    add_auto_issues, check_policy, cut_ranges, find_bad_words, merge_ranges, repair_policy, transcript_hits,
)
from app.director.schemas import EditPlan, PolicyIssue, Understanding
from app.director.tasks import make_hooks, make_plan, understand
from tests.test_director import GOOD, make_analysis
from tests.test_planner import SAMPLE, _short_plan, load

CFG = {"enabled": True, "pad_s": 0.1, "min_piece_s": 0.5, "merge_gap_s": 0.5,
       "bad_words": {"en": ["fuck", "shit"], "ko": ["씨발"], "ja": ["死ね"]}}


def test_find_bad_words():
    assert find_bad_words("What the FUCKING hell", "en", CFG) == ["fuck"]
    assert find_bad_words("Scunthorpe shitake", "en", CFG) == ["shit"]  # đầu từ
    assert find_bad_words("pushit", "en", CFG) == []  # giữa từ thì không
    assert find_bad_words("아 씨발 진짜", "ko", CFG) == ["씨발"]
    assert find_bad_words("お前なんか死ねよ", None, CFG) == ["死ね"]
    assert find_bad_words("fuck", "en", {**CFG, "enabled": False}) == []


def test_transcript_hits_use_word_times():
    segs = [{"start": 0, "end": 4, "text": " oh shit that hurt", "words": [
        {"start": 0.0, "end": 0.3, "word": " oh"}, {"start": 0.4, "end": 0.8, "word": " shit"},
        {"start": 0.9, "end": 1.2, "word": " that"}]},
            {"start": 5, "end": 7, "text": " 아 씨발", "words": [
                {"start": 5.0, "end": 5.2, "word": " 아"}, {"start": 5.3, "end": 5.5, "word": " 씨"},
                {"start": 5.5, "end": 5.8, "word": "발"}]},
            {"start": 8, "end": 9, "text": "fine", "words": []}]
    hits = transcript_hits(segs, None, CFG)
    assert [(h.start, h.end) for h in hits] == [(0.4, 0.8), (5.3, 5.8)]
    assert all(h.auto and h.category == "profanity" for h in hits)


def test_add_auto_issues_skips_already_flagged():
    u = Understanding.model_validate({**GOOD, "language": "en", "policy_issues": [
        {"start": 0.0, "end": 2.0, "category": "harassment", "reason_vi": "lăng mạ"}]})
    segs = [{"start": 0, "end": 1, "text": "shit", "words": [{"start": 0.2, "end": 0.5, "word": "shit"}]},
            {"start": 3, "end": 4, "text": "fuck", "words": [{"start": 3.1, "end": 3.4, "word": "fuck"}]}]
    u2 = add_auto_issues(u, segs, CFG)
    assert [(p.start, p.category) for p in u2.policy_issues] == [(0.0, "harassment"), (3.1, "profanity")]


def test_merge_and_cut_ranges():
    assert merge_ranges([(5, 6), (1, 2), (2.3, 3)], gap=0.5) == [(1, 3), (5, 6)]
    u = Understanding.model_validate({**GOOD, "policy_issues": [
        {"start": 10, "end": 12, "category": "violence", "reason_vi": "x"}]})
    assert cut_ranges(u, CFG) == [(9.9, 12.1)]
    assert cut_ranges(u, {**CFG, "enabled": False}) == []


def test_repair_policy_splits_clips_and_remaps_transitions():
    p = load("plan.json")
    p["transitions"] = [{"after_clip": 0, "name": "a"}, {"after_clip": 1, "name": "b"}]
    plan = EditPlan.model_validate(p)  # clips 1–6.1, 7.3–22, 23.1–45
    new, fixes = repair_policy(plan, [(10.0, 12.0), (2.0, 6.5)])
    assert [(c.source_start, c.source_end) for c in new.clips] == [(1.0, 2.0), (7.3, 10.0), (12.0, 22.0), (23.1, 45.0)]
    assert new.clips[3].speed == 1.2 and len(fixes) == 2
    assert [(t.after_clip, t.name) for t in new.transitions] == [(0, "a"), (2, "b")]
    assert check_policy(new, [(10.0, 12.0), (2.0, 6.5)], "ja") == []
    gone, _ = repair_policy(plan, [(0, 50)])
    assert gone.clips == [] and any("không còn clip" in e for e in check_policy(gone, [(0, 50)], "ja"))


def test_check_policy_onscreen_text():
    p = load("plan.json")
    p["titles_top"] = ["死ねと言われた", "x"]
    errs = check_policy(EditPlan.model_validate(p), [], "ja", CFG)
    assert any("chữ trên màn hình" in e for e in errs)


def _u_with_issue(a, start=30.0, end=35.0):
    u = understand(FakeDirector(), a)
    return u.model_copy(update={"policy_issues": [PolicyIssue(start=start, end=end, category="violence",
                                                              reason_vi="đánh nhau thật")]})


def test_make_plan_cuts_flagged_part_without_retry(tmp_path):
    a = make_analysis(tmp_path, duration=60.0)
    u = _u_with_issue(a)
    music = [m for m in DraftTemplate(SAMPLE).library if m.kind == "music"]
    d = FakeDirector(responses={"plan": _short_plan()})  # clip 1–45 chứa đoạn 30–35
    plan = make_plan(d, a, u, {"name": "tiktok_retention"}, music_items=music)
    assert len(d.calls) == 1  # tự cắt, không phải hỏi lại đạo diễn
    assert all(c.source_end <= 29.9 or c.source_start >= 35.1 for c in plan.clips)
    assert "đánh nhau thật" in d.calls[0]["prompt"] and "BẮT BUỘC CẮT BỎ" in d.calls[0]["prompt"]


def test_hooks_must_avoid_flagged_part(tmp_path):
    a = make_analysis(tmp_path, duration=60.0)
    hooks = load("hooks.json")
    o = hooks["options"][0]
    u = _u_with_issue(a, o["footage"]["start"], o["footage"]["end"])
    good = json.loads(json.dumps(hooks))
    for opt in good["options"]:
        opt["footage"] = {"start": 50.0, "end": 54.0}
        opt["source"] = {"start": 50.0, "end": 55.0}
    d = FakeDirector(responses={"hooks": [hooks, good]})
    make_hooks(d, a, u)
    assert len(d.calls) == 2 and "chính sách TikTok" in d.calls[1]["prompt"]


def test_persona_has_tiktok_policy():
    p = render_prompt("captions", {k: "x" for k in (
        "video_index", "language_name", "market", "hook", "summary", "sensitive_notes", "policy_cuts",
        "name_corrections", "key_moments", "transcript", "range", "audio_events")})
    assert "Chính sách TikTok" in p and "{{" not in p


def test_policy_panel_html(tmp_path):
    from app.web.server import _policy_html

    (tmp_path / "plan").mkdir()
    u = {**GOOD, "policy_issues": [{"start": 10, "end": 12, "category": "violence", "reason_vi": "máu <b>", "auto": False},
                                   {"start": 80, "end": 81, "category": "profanity", "reason_vi": "tục", "auto": True}]}
    (tmp_path / "plan" / "understanding.json").write_text(json.dumps(u), encoding="utf-8")
    h = _policy_html(tmp_path)
    assert "bạo lực" in h and "máu &lt;b&gt;" in h and "máy tự dò" in h
    assert "bạo lực" not in _policy_html(tmp_path, 50, 100)
    assert _policy_html(tmp_path, 20, 30) == ""


def test_find_platforms_real_config():
    from app.director.policy import find_forbidden, find_platforms

    assert find_platforms("Check my YouTube channel!", "en") == ["youtube"]
    assert "유튜브" in find_platforms("유튜브 구독과 좋아요 부탁해요", "ko")
    assert "チャンネル登録" in find_platforms("チャンネル登録よろしく", "ja")
    assert find_platforms("youtube 見てね", "ja") == ["youtube"]  # tên Latin trong video tiếng Nhật
    assert find_platforms("インスタント麺と短いshortsの話 高評価のお店", "ja") == []  # từ dễ nhầm không bị bắt
    assert find_forbidden("#fyp #shorts #youtube", "en") == ["youtube"]
    assert find_platforms("youtube", "en", {"enabled": False}) == []


def test_transcript_platform_mentions_cut_short_sentence():
    cfg = {**CFG, "platform_sentence_s": 6.0, "other_platforms": {"en": ["youtube"], "ko": ["유튜브"]}}
    segs = [{"start": 10, "end": 13, "text": " Subscribe on YouTube!", "words": [
        {"start": 10.0, "end": 10.6, "word": " Subscribe"}, {"start": 11.0, "end": 11.5, "word": " YouTube"}]},
            {"start": 20, "end": 30, "text": " long story I saw on youtube and then we went home", "words": [
                {"start": 20.0, "end": 21.0, "word": " long"}, {"start": 24.0, "end": 24.4, "word": " youtube"}]}]
    hits = transcript_hits(segs, "en", cfg)
    assert [(h.start, h.end, h.category) for h in hits] == [(10, 13, "other_platform"), (24.0, 24.4, "other_platform")]


def test_captions_reject_other_platform(tmp_path):
    from app.director.tasks import make_captions

    a = make_analysis(tmp_path, duration=60.0)
    u = understand(FakeDirector(), a)
    plan = EditPlan.model_validate(_short_plan())
    good = load("captions.json")
    bad = {**good, "hashtags": good["hashtags"][:-1] + ["#youtube"],
           "hashtags_vi": good["hashtags_vi"]}
    d = FakeDirector(responses={"captions": [bad, good]})
    make_captions(d, a, u, plan)
    assert len(d.calls) == 2 and "youtube" in d.calls[1]["prompt"]
    assert "nền tảng nào khác ngoài TikTok" in d.calls[0]["prompt"]
