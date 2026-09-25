"""Chạy một job trọn quy trình Giai đoạn 1 từ dòng lệnh (trước khi có giao diện web).

Tạo job mới:
    .venv\\Scripts\\python tools\\run_job.py new "D:\\footage\\video.mp4" --hook --client khachA
Chạy tiếp (sau khi chọn hook / thả voice / duyệt):
    .venv\\Scripts\\python tools\\run_job.py continue 20260925_03 --choose 1=2
Dùng lại job đã phân tích bằng analyze_footage.py (không phân tích lại):
    .venv\\Scripts\\python tools\\run_job.py continue 20260925_02 --hook --client khachA
Xem trạng thái:
    .venv\\Scripts\\python tools\\run_job.py status 20260925_03
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.jobs.job import Job, JobOptions, Status  # noqa: E402
from app.jobs.runner import Runner  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def add_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--hook", action="store_true", help="có hook voice")
    p.add_argument("--confirm", action="store_true", help="dừng xác nhận nội dung trước khi dựng")
    p.add_argument("--reframe", action="store_true", help="đổi khung 4:3/1:1 theo cảnh")
    p.add_argument("--business", action="store_true", help="khách doanh nghiệp: chỉ dùng nhạc Commercial")
    p.add_argument("--client", help="mã khách (dùng trong tên draft)")
    p.add_argument("--ratio", choices=["4:3", "1:1"], help="khung mặc định cho footage ngang")


def apply_options(job: Job, args) -> None:
    if args.hook:
        job.options.hook = True
    if args.confirm:
        job.options.confirm_before_build = True
    if args.reframe:
        job.options.reframe_per_scene = True
    if args.client:
        job.options.client_id = args.client
    if args.business:
        job.data["business"] = True
    if args.ratio:
        job.data["default_ratio"] = args.ratio


def report(job: Job) -> None:
    print("\n" + "=" * 60)
    print(f"Job {job.job_id} | bước: {job.step} | trạng thái: {job.status.value}")
    print(job.message)
    if job.status == Status.done:
        print(f"\nDraft CapCut: {job.data.get('draft')} ({job.data.get('duration_s')} giây)")
        if job.data.get("missing_assets"):
            print(f"Tài nguyên cần bổ sung: {job.data['missing_assets']} mục — xem missing_assets.json trong job")
    elif job.status == Status.waiting and job.step == "choose_hook":
        print(f"\n→ Chọn xong chạy: .venv\\Scripts\\python tools\\run_job.py continue {job.job_id} --choose 1=<số>")
    elif job.status in (Status.waiting, Status.error):
        print(f"\n→ Xử lý xong chạy: .venv\\Scripts\\python tools\\run_job.py continue {job.job_id}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--jobs-root", type=Path, default=ROOT / "jobs")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_new = sub.add_parser("new")
    p_new.add_argument("video", type=Path)
    add_options(p_new)
    p_cont = sub.add_parser("continue")
    p_cont.add_argument("job_id")
    p_cont.add_argument("--choose", action="append", default=[], help="video=phương án, ví dụ 1=2")
    add_options(p_cont)
    p_stat = sub.add_parser("status")
    p_stat.add_argument("job_id")
    args = parser.parse_args(argv)

    t0 = time.time()
    runner = Runner(args.jobs_root, log=lambda m: print(f"[{time.time() - t0:6.1f}s] {m}"))
    if args.cmd == "status":
        report(Job.load(args.jobs_root, args.job_id))
        return 0
    if args.cmd == "new":
        if not args.video.is_file():
            print(f"Không thấy file: {args.video}", file=sys.stderr)
            return 2
        job = Job.create(args.jobs_root, [args.video.resolve()])
        apply_options(job, args)
        job.save(args.jobs_root)
        job = runner.run(job)
    else:
        job = Job.load(args.jobs_root, args.job_id)
        apply_options(job, args)
        if args.choose:
            runner.choose_hooks(job, {int(a): int(b) for a, b in (c.split("=") for c in args.choose)})
        job = runner.resume(job) if job.status != Status.pending else runner.run(job)
    report(job)
    return 0 if job.status != Status.error else 1


if __name__ == "__main__":
    sys.exit(main())
