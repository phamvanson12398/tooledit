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


def test_openverse_only_free_licenses(tmp_path):
    from app.assets import openverse

    def handler(request: httpx.Request):
        if request.url.path == "/v1/audio/":
            assert request.url.params["license"] == "cc0,pdm"
            return httpx.Response(200, json={"results": [
                {"id": "a1", "title": "Epic Rise", "url": "https://x/a.mp3", "license": "by", "duration": 40000},
                {"id": "b2c3d4e5f6", "title": "Whoosh Fast", "url": "https://x/b.mp3", "license": "cc0",
                 "duration": 1200, "filetype": "mp3", "creator": "c", "provider": "freesound",
                 "foreign_landing_url": "https://freesound.org/s/1/", "license_url": "https://cc/zero"},
                {"id": "c3", "title": "Long", "url": "https://x/c.mp3", "license": "pdm", "duration": 400000}]})
        return httpx.Response(200, content=b"ID3")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    got = openverse.search("whoosh", min_s=0.1, max_s=3.0, count=5, client=client)
    assert [g["id"] for g in got] == ["b2c3d4e5f6"]  # bỏ CC BY (dù API trả về) và bài quá dài
    out = openverse.download(got[0], tmp_path, client=client)
    assert out.name == "whoosh_fast_ovb2c3d4e5.mp3" and out.read_bytes() == b"ID3"


def test_scan_enrich_groups_without_freesound_key(tmp_path):
    """Không có key Freesound vẫn làm giàu kho được qua Openverse; mỗi nhóm tải tới đủ số cần."""
    from app import config

    def handler(request: httpx.Request):
        if request.url.path == "/v1/audio/":
            q = request.url.params["q"]
            return httpx.Response(200, json={"results": [
                {"id": f"{q}{i}xxxxxxxx", "title": f"{q} {i}", "url": f"https://x/{q}{i}.mp3", "license": "cc0",
                 "duration": 1500, "creator": "u", "provider": "freesound", "foreign_landing_url": "https://f/1"}
                for i in range(2)]})
        return httpx.Response(200, content=b"ID3")

    ov = httpx.Client(transport=httpx.MockTransport(handler))
    rep = scan_resources(tmp_path, tmp_path / "jobs", tmp_path / "assets", download=True, api_key="",
                         capcut_items=[], probe=lambda p: 1, openverse_client=ov)
    assert rep.download_enabled
    cc = next(n for n in rep.needs if n["tag"] == "chuyen_canh" and n["kind"] == "sfx")
    target = config.load("assets")["group_targets"]["sfx"]
    assert cc["status"] == "đã tải" and cc["have"] >= target
    assert len(list((tmp_path / "assets" / "sfx" / "chuyen_canh").glob("*.mp3"))) >= target
    led = ledger.load(tmp_path / "assets")
    assert all(e["source"].startswith("openverse") and "CC0" in e["license"] for e in led)
    csv_text = (tmp_path / "assets" / "CREDITS.csv").read_text(encoding="utf-8-sig")
    assert csv_text.splitlines()[0].startswith("ten_file,thu_muc,nguon") and "chuyen_canh" in csv_text


def test_import_folder_sorts_by_readme_folder_names(tmp_path):
    from app.assets.importer import import_folder, infer_tag

    assert infer_tag(["SFX", "ChuyenCanh"], "sfx") == "chuyen_canh"
    assert infer_tag(["Nhac", "TaiLieu_BiAn"], "music") == "tai_lieu"
    assert infer_tag(["Nhac", "TruyenCamHung"], "music") == "cam_hung"
    assert infer_tag(["tải về", "Thời gian - Tua"], "sfx") == "thoi_gian"
    assert infer_tag(["downloads", "whoosh pack"], "sfx") == "chuyen_canh"
    assert infer_tag(["random"], "sfx") == "khac"
    src = tmp_path / "KhoTaiNguyen"
    for rel in ("SFX/VaCham/big hit.mp3", "Nhac/CamDong/sad piano.mp3", "SFX/VaCham/readme.txt"):
        f = src / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")
    res = import_folder(src, tmp_path / "assets", kind="auto", source="incompetech", author="Kevin MacLeod")
    files = sorted(e["file"] for e in res["imported"])
    assert files == ["music/cam_dong/sad_piano_ic.mp3", "sfx/va_cham/big_hit_ic.mp3"]
    assert res["credit_required"] and all(e["credit_required"] for e in res["imported"])
    assert all(e["license"] == "CC BY 4.0" for e in res["imported"])
    again = import_folder(src, tmp_path / "assets", kind="auto", source="incompetech")
    assert not again["imported"] and len(again["skipped"]) == 2  # không nhập trùng


def test_credit_lines_for_cc_by_files(tmp_path, monkeypatch):
    from app.jobs.runner import Runner

    assets = tmp_path / "assets"
    f = assets / "music" / "cam_dong" / "sad_ic.mp3"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"x")
    ledger.add(assets, f, source="Incompetech (Kevin MacLeod)", license="CC BY 4.0", author="Kevin MacLeod",
               url="https://incompetech.com/x", credit_required=True, extra={"name": "Sad Song"})
    g = assets / "sfx" / "hai" / "boing_pb.mp3"
    g.parent.mkdir(parents=True)
    g.write_bytes(b"x")
    ledger.add(assets, g, source="Pixabay", license="Pixabay Content License")
    monkeypatch.setattr(ledger, "ASSETS_ROOT", assets)
    lines = Runner._credits([str(f), str(g), "C:/khac/file.mp3"])
    assert lines == ['"Sad Song" by Kevin MacLeod — CC BY 4.0 (https://incompetech.com/x)']
