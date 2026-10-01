"""So sánh video gốc với video đã edit (ước lượng % khác biệt)."""

from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.analysis.compare import (
    audio_similarity, center_crop, combine, compare_videos, dhash, hamming, visual_similarity,
)


def _frames(seed: int, n: int = 12, h: int = 108, w: int = 192):
    rng = np.random.default_rng(seed)
    return [cv2.GaussianBlur((rng.random((h, w)) * 255).astype(np.uint8), (15, 15), 0) for _ in range(n)]


def _in_9_16(g: np.ndarray, flip: bool = False) -> np.ndarray:
    """Khung 16:9 đặt giữa nền đen 9:16 (như bố cục bản edit)."""
    canvas = np.zeros((341, 192), np.uint8)
    y = (341 - g.shape[0]) // 2
    canvas[y:y + g.shape[0]] = g[:, ::-1] if flip else g
    return canvas


def test_dhash_and_crop():
    g = _frames(1, 1)[0]
    assert hamming(dhash(g), dhash(g)) == 0
    assert hamming(dhash(g), dhash(cv2.GaussianBlur(g, (3, 3), 0))) <= 6  # đổi nhẹ → vẫn giống
    assert center_crop(np.zeros((341, 192)), 16 / 9).shape == (108, 192)
    assert center_crop(np.zeros((341, 192)), 1.0).shape == (192, 192)


def test_visual_similarity_finds_block_and_mirror():
    orig = _frames(2)
    same, sm, mir = visual_similarity(orig, [_in_9_16(g) for g in orig])
    assert sm == 1.0 and mir == 0.0
    _, fm, fmir = visual_similarity(orig, [_in_9_16(g, flip=True) for g in orig])
    assert fm == 1.0 and fmir == 1.0  # cảnh lật ngang vẫn nhận ra là cùng nội dung
    _, om, _ = visual_similarity(orig, [_in_9_16(g) for g in _frames(3)])
    assert om == 0.0


def test_audio_similarity():
    rng = np.random.default_rng(4)
    env = rng.normal(-30, 6, 900)
    assert audio_similarity(env, env[200:500]) == 1.0
    assert audio_similarity(env, rng.normal(-30, 6, 300)) == 0.0
    assert audio_similarity(env, env[:10]) is None


def test_combine_weights():
    r = combine(1.0, 1.0, 1.0, 60, 60)
    assert r.overall == 0.0
    r = combine(0.5, 0.0, 0.0, 120, 60)
    assert r.visual_diff == 75.0 and r.audio_diff == 100.0 and r.duration_diff == 50.0
    assert r.overall == round(0.6 * 75 + 0.3 * 100 + 0.1 * 50, 1)
    r = combine(0.5, 0.0, None, 60, 60)
    assert r.audio_diff is None and r.overall == round(0.85 * 75, 1) and r.notes


def _write(path: Path, frames, fps=10):
    h, w = frames[0].shape
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for g in frames:
        for _ in range(5):  # mỗi ảnh giữ 0.5 giây
            vw.write(cv2.cvtColor(g, cv2.COLOR_GRAY2BGR))
    vw.release()


def test_compare_real_files_and_web(tmp_path):
    orig = _frames(5, 16)
    _write(tmp_path / "goc.mp4", orig)
    # bản edit: nửa đầu giữ nguyên cảnh gốc (đặt trong khung 9:16), nửa sau là cảnh khác
    _write(tmp_path / "edit.mp4", [_in_9_16(g) for g in orig[:8]] + [_in_9_16(g) for g in _frames(6, 8)])
    r = compare_videos(tmp_path / "goc.mp4", tmp_path / "edit.mp4", audio=False)
    assert 35 <= r.visual_matched <= 65 and 20 <= r.overall <= 70 and r.audio_diff is None

    from app.web.server import create_app

    client = TestClient(create_app(tmp_path / "jobs", lambda root, log: None))
    assert "So sánh video gốc và video đã edit" in client.get("/").text
    page = client.post("/compare", data={"original": str(tmp_path / "goc.mp4"),
                                         "edited": str(tmp_path / "edit.mp4")}).text
    assert "khác bản gốc" in page and "Hình ảnh" in page
    assert "Không thấy file" in client.post("/compare", data={"original": "x.mp4", "edited": "y.mp4"}).text
