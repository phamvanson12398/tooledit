"""Tải âm thanh giấy phép mở từ Openverse (openverse.org, dự án của WordPress) — KHÔNG cần API key.

Đã đối chiếu mã nguồn thật (github.com/WordPress/openverse, api/api/serializers/*, api/api/constants/licenses.py):
- GET https://api.openverse.org/v1/audio/?q=...&license=cc0,pdm&page_size=20 (khách không đăng nhập: tối đa 20/trang).
- Mỗi kết quả có: id, title, url (file âm thanh), foreign_landing_url (trang gốc), creator, license
  ("cc0" | "pdm" | "by" ...), license_version, license_url, provider, duration (mili giây), filetype.
Openverse gom nhiều kho (Freesound, Jamendo, Wikimedia, ccMixter...). Tool chỉ lấy CC0 và Public Domain Mark:
dùng thương mại, chỉnh sửa thoải mái, không bắt buộc ghi nguồn (vẫn ghi vào sổ nguồn).
"""

from __future__ import annotations

from pathlib import Path

import httpx

from .freesound import slug

API = "https://api.openverse.org/v1/audio/"
FREE_LICENSES = ("cc0", "pdm")


class OpenverseError(RuntimeError):
    pass


def search(query: str, *, min_s: float, max_s: float, count: int = 3, licenses: tuple[str, ...] = FREE_LICENSES,
           client: httpx.Client | None = None) -> list[dict]:
    params = {"q": query, "license": ",".join(licenses), "page_size": 20, "mature": "false"}
    c = client or httpx.Client(timeout=20, follow_redirects=True)
    try:
        r = c.get(API, params=params)
    except httpx.HTTPError as exc:
        raise OpenverseError(f"Không kết nối được Openverse: {exc}") from exc
    if r.status_code == 429:
        raise OpenverseError("Openverse báo gọi quá nhiều (429) — đợi vài phút rồi quét lại.")
    if r.status_code != 200:
        raise OpenverseError(f"Openverse trả lỗi {r.status_code}: {r.text[:200]}")
    try:
        results = r.json().get("results", [])
    except ValueError as exc:
        raise OpenverseError(f"Openverse trả dữ liệu không đọc được: {exc}") from exc
    out = []
    for s in results:
        dur = (s.get("duration") or 0) / 1000.0  # mili giây → giây
        if s.get("license") not in licenses or not s.get("url"):
            continue  # kiểm tra lại giấy phép dù đã lọc trên máy chủ
        if dur and not (min_s <= dur <= max_s):
            continue
        out.append(s)
        if len(out) >= count:
            break
    return out


def download(sound: dict, folder: Path, client: httpx.Client | None = None) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    ext = "." + (sound.get("filetype") or "mp3").lower().lstrip(".")
    if ext not in (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"):
        ext = ".mp3"
    out = folder / f"{slug(sound.get('title', ''))}_ov{str(sound['id'])[:8]}{ext}"
    if out.is_file():
        return out
    c = client or httpx.Client(timeout=60, follow_redirects=True)
    try:
        r = c.get(sound["url"])
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise OpenverseError(f"Tải {sound.get('title')} thất bại: {exc}") from exc
    tmp = out.with_suffix(".part")
    tmp.write_bytes(r.content)
    tmp.replace(out)
    return out


def license_text(sound: dict) -> str:
    lic = sound.get("license", "")
    return {"cc0": "CC0 1.0 (public domain)", "pdm": "Public Domain Mark"}.get(lic, lic) + \
        (f" — {sound['license_url']}" if sound.get("license_url") else "")
