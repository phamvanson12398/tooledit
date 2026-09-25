"""Ánh xạ giây trong footage gốc → micro giây trên timeline của video (sau hook, sau khi cắt, có tốc độ)."""

from __future__ import annotations

from dataclasses import dataclass

SEC = 1_000_000


@dataclass
class Placed:
    source_start: float
    source_end: float
    speed: float
    out_start: int  # µs trên timeline

    @property
    def out_duration(self) -> int:
        return round((self.source_end - self.source_start) / self.speed * SEC)

    @property
    def out_end(self) -> int:
        return self.out_start + self.out_duration


class TimeMap:
    def __init__(self, clips, offset_us: int = 0):
        """clips: danh sách có source_start, source_end, speed (theo thứ tự dựng)."""
        self.placed: list[Placed] = []
        t = int(offset_us)
        for c in clips:
            p = Placed(c.source_start, c.source_end, c.speed, t)
            self.placed.append(p)
            t = p.out_end
        self.end = t

    def to_out(self, source_t: float) -> int | None:
        """Giây gốc → µs trên timeline; None nếu thời điểm đó bị cắt bỏ."""
        for p in self.placed:
            if p.source_start - 1e-6 <= source_t <= p.source_end + 1e-6:
                return p.out_start + round((source_t - p.source_start) / p.speed * SEC)
        return None

    def clip_at(self, source_t: float) -> Placed | None:
        for p in self.placed:
            if p.source_start - 0.05 <= source_t <= p.source_end + 0.05:
                return p
        return None

    def clip_containing(self, source_t: float) -> Placed | None:
        """Clip chứa đúng thời điểm (không nới biên)."""
        for p in self.placed:
            if p.source_start <= source_t <= p.source_end:
                return p
        return None
