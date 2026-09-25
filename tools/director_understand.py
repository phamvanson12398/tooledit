"""Chạy thử đạo diễn AI (Claude Code) bước "hiểu nội dung" trên một job đã phân tích.

Chạy:  .venv\\Scripts\\python tools\\director_understand.py 20260925_02
Kết quả lưu ở jobs\\<job_id>\\plan\\understanding.json
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.director import get_director  # noqa: E402
from app.director.tasks import understand  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("job_id")
    parser.add_argument("--jobs-root", type=Path, default=ROOT / "jobs")
    args = parser.parse_args(argv)
    job_dir = args.jobs_root / args.job_id
    analysis = job_dir / "analysis"
    if not (analysis / "transcript.json").is_file():
        print(f"Job {args.job_id} chưa được phân tích (thiếu {analysis / 'transcript.json'}).", file=sys.stderr)
        return 2
    t0 = time.time()
    director = get_director(log=lambda m: print(f"[{time.time() - t0:6.1f}s] {m}"))
    result = understand(director, analysis)
    out = job_dir / "plan" / "understanding.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print("\n===== ĐẠO DIỄN NHẬN XÉT =====")
    print(f"Thời gian: {time.time() - t0:.0f} giây")
    print(f"Tóm tắt: {result.summary_vi}")
    print(f"Thể loại: {result.genre} | Không khí: {result.mood} | Số người: {result.people_count}")
    print(f"Chủ thể chính: {result.main_subject} | Ngôn ngữ: {result.language}")
    print(f"Phong cách đề xuất: {result.suggested_style} — {result.style_reason_vi}")
    print("Khoảnh khắc đáng chú ý:")
    for m in result.key_moments:
        print(f"  {m.start:6.1f}-{m.end:6.1f}s  {m.why_vi}")
    print(f"Đoạn nên dùng: {result.usable_range.start:.1f}-{result.usable_range.end:.1f}s")
    for c in result.name_corrections:
        print(f"Sửa tên: {c.wrong} → {c.right} ({c.evidence_vi})")
    b = result.burned_in_text
    print(f"Chữ có sẵn trên hình: {'có' if b.present else 'không'} {', '.join(b.regions)} {b.note_vi}")
    for n in result.sensitive_notes_vi:
        print(f"Lưu ý nhạy cảm: {n}")
    print(f"Ghi chú editor: {result.editor_notes}")
    print(f"\nĐã lưu: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
