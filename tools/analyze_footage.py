"""Chạy thử bước Phân tích trên một video thật và in tóm tắt.

Chạy:  python tools\\analyze_footage.py "D:\\footage\\video.mp4"
Kết quả nằm trong jobs\\<job_id>\\analysis\\ (không commit lên git).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analysis.pipeline import run_analysis  # noqa: E402
from app.jobs.job import Job  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", type=Path)
    parser.add_argument("--jobs-root", type=Path, default=ROOT / "jobs")
    args = parser.parse_args(argv)
    if not args.video.is_file():
        print(f"Không thấy file: {args.video}", file=sys.stderr)
        return 2
    job = Job.create(args.jobs_root, [args.video.resolve()])
    print(f"Job: {job.job_id}")
    t0 = time.time()
    result = run_analysis(job, args.jobs_root, progress=lambda m: print(f"[{time.time() - t0:6.1f}s] {m}"))
    tr, sc, sj = result["transcripts"][0], result["scenes"][0], result["subjects"][0]
    print("\n===== TÓM TẮT =====")
    print(f"Thời gian chạy: {time.time() - t0:.0f} giây")
    print(f"Video: {sc['width']}x{sc['height']}, {sc['duration']:.1f} giây, {len(sc['scenes'])} cảnh")
    print(f"Ngôn ngữ: {tr.get('language')}  | model: {tr.get('model')} trên {tr.get('device')}")
    print(f"Số câu thoại: {len(tr['segments'])}")
    for s in tr["segments"][:8]:
        print(f"  {s['start']:6.1f}-{s['end']:6.1f}  {s['text']}")
    print(f"Khung hình đã trích: {len(result['frames'])}")
    print(f"Số mặt nhiều nhất trong một khung: {sj['face_count_max']}")
    print(f"\nChi tiết: {job.dir(args.jobs_root) / 'analysis'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
