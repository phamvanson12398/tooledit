"""Nạp preset phong cách trong styles/*.yaml."""

from __future__ import annotations

import yaml

from app.config import ROOT

STYLES_DIR = ROOT / "styles"


def load_style(name: str) -> dict:
    path = STYLES_DIR / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Chưa có preset phong cách {name} (styles/{name}.yaml)")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def available_styles() -> dict[str, dict]:
    """Tên preset → {name_vi, fits_vi, description_vi}."""
    out = {}
    for path in sorted(STYLES_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        out[path.stem] = {k: data.get(k, "") for k in ("name_vi", "fits_vi", "description_vi")}
    return out


def styles_for_prompt() -> str:
    return "\n".join(f"- {k}: {v['name_vi']} — hợp với: {v['fits_vi']}" for k, v in available_styles().items())


def layout_for(style: dict) -> dict | None:
    """Bố cục của kiểu dựng: khóa `layout` trong style, không có thì theo preset của config/layout.yaml.
    Trả None cho bố cục cũ (classic), còn lại là dict cấu hình kèm "name"."""
    from app import config

    lay = config.load("layout")
    name = style.get("layout") or lay.get("preset", "four_titles")
    if name == "classic" or not isinstance(lay.get(name), dict):
        return None
    out = {**lay[name], "name": name}
    # khung hiển thị: cố định theo frame_ratio của bố cục (chủ dự án chốt 02/10: 3:4 cho mọi video);
    # không đặt frame_ratio thì theo khung người dùng chọn (style["block_ratio"])
    ratio = out.get("frame_ratio") or style.get("block_ratio")
    return adapt_layout(out, ratio) if ratio and ratio != out.get("block_ratio") else out


def block_rows(ratio: str) -> tuple[float, float]:
    """Mép trên / mép dưới của khối video (phần chiều cao khung 9:16, từ trên xuống) khi khối rộng bằng khung."""
    from app.capcut_writer.layout import RATIOS

    h = (1080 / RATIOS[ratio]) / 1920
    return 0.5 - h / 2, 0.5 + h / 2


def adapt_layout(lay: dict, ratio: str) -> dict:
    """Đổi khối video sang tỉ lệ khác (vd 16:9 → 4:3 / 1:1) và dời mọi thứ theo khối: dòng tiêu đề giữ cùng vị trí
    TƯƠNG ĐỐI trong dải trên / dải dưới, phụ đề và nhãn chủ đề giữ cùng vị trí tương đối trong khối, chữ tiêu đề nhỏ
    lại nếu dải hẹp hơn (để không đè lên video)."""
    from app.capcut_writer.layout import RATIOS

    if ratio not in RATIOS or lay.get("block_ratio") not in RATIOS:
        return lay
    t0, b0 = block_rows(lay["block_ratio"])
    t1, b1 = block_rows(ratio)
    out = {**lay, "block_ratio": ratio}
    if lay.get("title_rows"):
        rows = []
        for r in lay["title_rows"]:
            if r < 0.5:
                rows.append(r / t0 * t1)
            else:
                rows.append(b1 + (r - b0) / (1 - b0) * (1 - b1))
        out["title_rows"] = [round(r, 4) for r in rows]
        if len(rows) == 4:  # dải hẹp → chữ tiêu đề không được cao hơn khoảng cách giữa 2 dòng (không chồng nhau)
            gap = min(rows[1] - rows[0], rows[3] - rows[2]) * 1920  # px
            line_px = lay.get("title_size", 20) * lay.get("char_width_per_size", 0.0017) * 1080 * 1.25
            out["title_scale_max"] = round(min(lay.get("title_scale_max", 2.2), gap / max(line_px, 1e-6)), 3)

    def inside(row: float) -> float:  # giữ cùng vị trí tương đối TRONG khối video
        return round(t1 + (row - t0) / (b0 - t0) * (b1 - t1), 4)

    for key in ("subtitle_row", "topic_row"):
        if key in lay:
            out[key] = inside(lay[key])
    return out
