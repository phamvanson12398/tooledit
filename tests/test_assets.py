import json
from pathlib import Path

import httpx

from app.assets import freesound, ledger
from app.assets.local import scan_local
from app.assets.scan import scan_resources
from app.capcut_writer import DraftTemplate
from app.capcut_writer.template import LibraryItem
from app.director.schemas import EditPlan, Understanding
from app.planner.builder import build
from tests.test_planner import SAMPLE, _analysis, load

CC0 = "http://creativecommons.org/publicdomain/zero/1.0/"
BY = "https://creativecommons.org/licenses/by/4.0/"


def fake_freesound(results):
    """Giả lập Freesound API: trả kết quả tìm kiếm + file preview."""
    seen = []

    def handler(request: httpx.Request):
        if request.url.path == "/apiv2/search/":
            seen.append(request)
            return httpx.Response(200, json={"results": results})
        return httpx.Response(200, content=b"ID3fake")

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def sound(i, lic=CC0, dur=1.2):
    return {"id": i, "name": f"Pop {i}!", "license": lic, "username": "u", "duration": dur,
            "url": f"https://freesound.org/s/{i}/",
            "previews": {"preview-hq-mp3": f"https://cdn.freesound.org/previews/{i}.mp3"}}


def test_freesound_only_cc0_and_token_header(tmp_path):
    client, seen = fake_freesound([sound(1, BY), sound(2), sound(3)])
    got = freesound.search("KEY", "pop", min_s=0.1, max_s=3, count=2, client=client)
    assert [s["id"] for s in got] == [2, 3]  # bỏ file không phải CC0 dù API trả về
    req = seen[0]
    assert req.headers["Authorization"] == "Token KEY"
    assert 'license:"Creative Commons 0"' in req.url.params["filter"]
    assert "duration:[0.1 TO 3]" in req.url.params["filter"]
    out = freesound.download(got[0], tmp_path, client=client)
    assert out.name == "fs2_pop_2.mp3" and out.read_bytes() == b"ID3fake"


def test_scan_downloads_missing_and_ledger(tmp_path):
    assets, jobs = tmp_path / "assets", tmp_path / "jobs"
    (jobs / "j1").mkdir(parents=True)
    (jobs / "j1" / "missing_assets.json").write_text(json.dumps(
        [{"kind": "sfx", "what": "boom", "video": 1, "at_s": 3.0}]), encoding="utf-8")
    capcut = [LibraryItem(kind="sfx", name="Whoosh Fast", resource_id="1", material={}),
              LibraryItem(kind="music", name="Song", resource_id="2", material={})]
    # không bật tải: chỉ báo thiếu
    rep = scan_resources(tmp_path, jobs, assets, capcut_items=capcut, probe=lambda p: 1)
    st = {n["tag"]: n for n in rep.needs}
    assert st["whoosh"]["status"] == "có sẵn" and st["boom"]["status"] == "còn thiếu"
    assert st["boom"]["jobs"] == ["j1"] and rep.downloaded == []

    client, _ = fake_freesound([sound(7)])
    rep = scan_resources(tmp_path, jobs, assets, download=True, api_key="K", client=client, capcut_items=capcut,
                         probe=lambda p: 1)
    st = {n["tag"]: n for n in rep.needs}
    assert st["boom"]["status"] == "đã tải" and st["whoosh"]["status"] == "có sẵn"
    assert list((assets / "sfx" / "boom").glob("fs7_*.mp3"))
    entry = next(e for e in ledger.load(assets) if e["file"].startswith("sfx/boom/"))
    assert entry["source"] == "freesound" and entry["license"] == CC0 and entry["duration_us"] == 1_200_000
    assert rep.jobs_to_redo == ["j1"] and rep.local["sfx"] >= 1
    # sổ nguồn cho biết độ dài → quét local không cần ffprobe
    items = scan_local(assets, probe=lambda p: (_ for _ in ()).throw(RuntimeError("không gọi")))
    boom = next(i for i in items if i.mood == "boom")
    assert boom.kind == "sfx" and boom.material["local"] and boom.material["duration"] == 1_200_000


def test_builder_uses_local_sfx_and_music_fallback(tmp_path):
    assets = tmp_path / "assets"
    for kind, tag, name in (("sfx", "pop", "p.mp3"), ("music", "mid", "m.mp3")):
        f = assets / kind / tag / name
        f.parent.mkdir(parents=True)
        f.write_bytes(b"x")
    tpl = DraftTemplate(SAMPLE)
    tpl.library = [i for i in tpl.library if i.kind not in ("music", "sfx")]
    tpl.merge_items(scan_local(assets, probe=lambda p: 20_000_000))
    p = load("plan.json")
    t = p["clips"][0]["source_start"] + 1
    p["sfx"] = [{"source_time": t, "kind": "pop", "name": None}]
    p["music"] = {"name": None, "mood_vi": "vui", "energy": "mid"}
    plan = EditPlan.model_validate(p)
    u = Understanding.model_validate(load("understand.json"))
    from app.styles import load_style

    res = build(plan, u, _analysis(), tpl, tmp_path / "drafts", "loc", load_style("tiktok_retention"))
    audios = res.writer.build_timeline()["materials"]["audios"]
    paths = {Path(a["path"]).name for a in audios if a.get("category_name") == "local"}
    assert {"p.mp3", "m.mp3"} <= paths
    assert not [m for m in res.missing_assets if m["kind"] in ("sfx", "music")]
