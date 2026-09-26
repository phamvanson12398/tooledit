"""Tải âm thanh CC0 từ Freesound API v2 (key miễn phí, người dùng tự nhập trong giao diện).

Đã đối chiếu mã nguồn thật của Freesound (github.com/MTG/freesound, apiv2/urls.py + serializers.py) và thư viện
chính thức freesound-python:
- Tìm kiếm: GET https://freesound.org/apiv2/search/ (bí danh cũ /search/text/), tham số query, filter, fields,
  page_size, sort; xác thực bằng header "Authorization: Token <key>".
- Giá trị lọc giấy phép: license:"Creative Commons 0"; trường `license` trả về là deed URL
  (CC0 = .../publicdomain/zero/1.0/) → kiểm tra lại lần nữa trước khi tải.
- `previews` có khóa "preview-hq-mp3" (file nghe thử MP3 chất lượng cao, tải không cần OAuth).
Chỉ lấy CC0 (mục 7): không ghi công bắt buộc, dùng thương mại được.
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx

API = "https://freesound.org/apiv2/search/"
CC0_FILTER = 'license:"Creative Commons 0"'


class FreesoundError(RuntimeError):
    pass


def is_cc0(license_url: str) -> bool:
    return "publicdomain/zero" in (license_url or "")


def search(key: str, query: str, *, min_s: float, max_s: float, count: int = 3, client: httpx.Client | None = None
           ) -> list[dict]:
    params = {
        "query": query,
        "filter": f"{CC0_FILTER} duration:[{min_s} TO {max_s}]",
        "fields": "id,name,license,username,duration,previews,url",
        "sort": "rating_desc",
        "page_size": max(count * 3, 5),
    }
    c = client or httpx.Client(timeout=20)
    try:
        r = c.get(API, params=params, headers={"Authorization": f"Token {key}"})
    except httpx.HTTPError as exc:
        raise FreesoundError(f"Không kết nối được Freesound: {exc}") from exc
    if r.status_code == 401:
        raise FreesoundError("Freesound từ chối key (401). Kiểm tra lại API key trong phần cài đặt.")
    if r.status_code != 200:
        raise FreesoundError(f"Freesound trả lỗi {r.status_code}: {r.text[:200]}")
    try:
        data = r.json()
    except ValueError as exc:
        raise FreesoundError(f"Freesound trả dữ liệu không đọc được: {exc}") from exc
    results = [s for s in data.get("results", []) if is_cc0(s.get("license", ""))
               and (s.get("previews") or {}).get("preview-hq-mp3")]
    return results[:count]


def slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return s[:40] or "sound"


def download(sound: dict, folder: Path, client: httpx.Client | None = None) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"fs{sound['id']}_{slug(sound.get('name', ''))}.mp3"
    if out.is_file():
        return out
    c = client or httpx.Client(timeout=30, follow_redirects=True)
    try:
        r = c.get(sound["previews"]["preview-hq-mp3"])
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise FreesoundError(f"Tải {sound.get('name')} thất bại: {exc}") from exc
    tmp = out.with_suffix(".part")
    tmp.write_bytes(r.content)
    tmp.replace(out)
    return out
