"""Bán content "nửa thuyết minh, nửa tiếng gốc" (chủ dự án 20/10): AI tự quyết xen vài đoạn giữ nguyên hình + tiếng gốc."""

import json
from pathlib import Path

from app.director.fake import FakeDirector
from app.director.schemas import OrigInsert, SellScript
from app.director.sell import check_inserts, sell_to_dub
from app.jobs.job import JobOptions, Status
from app.planner.sell_sync import build_sell
from tests.test_planner import _short_plan
from tests.test_runner import make_runner as _make_runner, prepare

SELL = json.loads((Path(__file__).parent / "fixtures" / "director" / "sell.json").read_text(encoding="utf-8"))
N = len(SELL["lines"])
CFG = {"orig_audio": {"min_s": 1.5, "max_s": 10, "max_share": 0.4}}


def _with(inserts):
    return SellScript.model_validate({**SELL, "inserts": inserts})


def test_check_inserts():
    ok = _with([{"after_line": 2, "start": 40, "end": 45, "text": "정말 맛있어요!", "text_vi": "Ngon thật!"}])
    assert check_inserts(ok, "ko", duration=60, target_s=65, cfg=CFG) == []
    errs = check_inserts(_with([{"after_line": 2, "start": 10, "end": 25, "text": "本当においしい"},
                                {"after_line": 30, "start": 70, "end": 72}]), "ko", duration=60, target_s=65, cfg=CFG)
    text = " | ".join(errs)
    assert "dài 15.0s" in text and "phải DỊCH" in text and "after_line 30" in text and "ngoài video" in text
    many = _with([{"after_line": k, "start": 10 * k, "end": 10 * k + 9} for k in range(4)])
    assert any("tối đa 40%" in e for e in check_inserts(many, "ko", duration=60, target_s=65, cfg=CFG))


def test_build_sell_places_insert_after_line_and_shifts():
    s = sell_to_dub(_with([]))
    ins = [OrigInsert(after_line=2, start=40, end=45, text="정말 맛있어요!", text_vi="Ngon thật!")]
    voice = {n: 3.0 for n in range(1, N + 1)}
    base_clips, base_win, _ = build_sell(s, voice, [{"start": 0, "end": 60}], 60.0, cps=10.0)
    out = []
    clips, win, notes = build_sell(s, voice, [{"start": 0, "end": 60}], 60.0, cps=10.0, inserts=ins, insert_out=out)
    keep = [c for c in clips if c.keep_audio]
    assert len(keep) == 1 and (keep[0].source_start, keep[0].source_end, keep[0].speed) == (40.0, 45.0, 1.0)
    assert win[1][0] == base_win[1][0] and win[2][0] - base_win[2][0] == 5_000_000  # câu 3 lùi đúng 5 giây
    assert out == [{"start": win[1][0] + round((3.0 + 0.08) * 1_000_000), "end": win[2][0], "text": "정말 맛있어요!",
                    "text_vi": "Ngon thật!"}]
    assert "1 đoạn giữ tiếng gốc" in notes[0]


def test_sell_job_keeps_original_audio_in_inserts(tmp_path):
    script = {**SELL, "inserts": [{"after_line": 2, "start": 40, "end": 45, "text": "정말 맛있어요!", "text_vi": "Ngon thật!",
                                   "why_vi": "khách khen thật"}]}
    jobs, job = prepare(tmp_path, JobOptions(sell=True, sell_s=70, target_language="ko", client_id="k"))
    r = _make_runner(tmp_path, jobs)
    r._director = FakeDirector(responses={"plan": _short_plan(), "sell": script})
    job = r.run(job)
    assert job.step == "dub_voice", job.message
    assert "GIỮ NGUYÊN TIẾNG GỐC" in next(c["prompt"] for c in r.director.calls if c["task"] == "sell")
    assert "Giữ tiếng gốc (không cần đọc)" in (jobs / "j1" / "dub_scripts.txt").read_text(encoding="utf-8")
    for n in range(1, N + 1):
        (jobs / "j1" / "voice" / f"video01_dub{n:02d}.wav").write_bytes(b"RIFF")
    job = r.resume(job)
    assert job.status == Status.done, job.message
    content = json.loads((Path(job.data["draft"]) / "draft_content.json").read_text(encoding="utf-8"))
    vids = {m["id"]: m for m in content["materials"]["videos"]}
    segs = [s for t in content["tracks"] if t["type"] == "video" for s in t["segments"]
            if vids.get(s["material_id"], {}).get("type") == "video"]
    loud = [s for s in segs if s["volume"] > 0]
    assert len(loud) == 1 and loud[0]["source_timerange"]["start"] == 40_000_000  # chỉ đoạn giữ tiếng gốc có tiếng
    assert any("정말 맛있어요" in m.get("content", "") for m in content["materials"]["texts"])  # phụ đề dịch lời gốc


def test_ideas_and_youtube_drop_inserts(tmp_path):
    from app.jobs.runner import Runner

    r = Runner(tmp_path, log=lambda m: None)
    job = type("J", (), {})()
    job.options = JobOptions(sell=True, ideas=True)
    assert r._sell_inserts(job, 1) == []
