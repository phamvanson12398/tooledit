"""Chạy job theo từng bước, dừng ở các điểm chờ người dùng (mục 3). Dùng chung cho dòng lệnh và giao diện web.

Giai đoạn 1: một video, phong cách tiktok_retention.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable

from app import config
from app.jobs.job import Job, Status

DEFAULT_STYLE = "tiktok_retention"


def drafts_root() -> Path:
    cfg = config.load("capcut")
    if cfg.get("drafts_root"):
        return Path(cfg["drafts_root"])
    base = os.environ.get("LOCALAPPDATA") if sys.platform == "win32" else None
    if not base:
        raise RuntimeError("Chưa cấu hình drafts_root trong config/capcut.yaml")
    return Path(base) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"


def find_template(root: Path, name: str) -> Path | None:
    """Thư mục dự án mẫu: trùng tên thư mục, hoặc có draft_name (tên hiển thị trong CapCut) trùng tên.
    Tên thư mục và tên hiển thị có thể khác nhau (máy chủ dự án: thư mục '0925', tên 'capcut_template')."""
    direct = Path(root) / name
    if direct.is_dir():
        return direct
    if not Path(root).is_dir():
        return None
    for d in Path(root).iterdir():
        meta = d / "draft_meta_info.json"
        if meta.is_file():
            try:
                if json.loads(meta.read_text(encoding="utf-8-sig")).get("draft_name") == name:
                    return d
            except (OSError, ValueError):
                continue
    return None


class Runner:
    def __init__(self, jobs_root: Path, *, director=None, analyze_fn=None, probe_duration_fn=None,
                 drafts_dir: Path | None = None, template_dir: Path | None = None,
                 log: Callable[[str], None] = print):
        self.jobs_root = Path(jobs_root)
        self.log = log
        self._director = director
        self._analyze_fn = analyze_fn
        self._probe = probe_duration_fn
        self._drafts_dir = drafts_dir
        self._template_dir = template_dir

    # ---------- phụ trợ ----------

    @property
    def director(self):
        if self._director is None:
            from app.director import get_director

            self._director = get_director(log=self.log)
        return self._director

    def _paths(self, job: Job) -> tuple[Path, Path, Path]:
        d = job.dir(self.jobs_root)
        return d, d / "analysis", d / "plan"

    def _understanding(self, job: Job):
        from app.director.schemas import Understanding

        _, _, plan_dir = self._paths(job)
        return Understanding.model_validate_json((plan_dir / "understanding.json").read_text(encoding="utf-8"))

    def _template(self):
        from app.capcut_writer import DraftTemplate

        if self._template_dir is not None:
            tdir = self._template_dir
        else:
            tdir = find_template(drafts_root(), config.load("capcut").get("template_name", "capcut_template"))
        if tdir is None or not Path(tdir).is_dir():
            raise RuntimeError(f"Không thấy dự án mẫu CapCut ({tdir or 'theo config/capcut.yaml'}). "
                               "Kiểm tra template_name trong config/capcut.yaml.")
        tpl = DraftTemplate(Path(tdir))
        if self._template_dir is None and config.load("capcut").get("library_scan", True):
            from app.capcut_writer.library import scan_drafts
            from app.capcut_writer.template import _load_labels

            added = tpl.merge_items(scan_drafts(drafts_root()))
            tpl._apply_labels(_load_labels())
            self.log(f"Kho tài nguyên tự quét từ CapCut: thêm {added} mục")
        return tpl

    def _style_name(self, job: Job) -> str:
        """Phong cách người dùng chọn; 'auto' = theo đề xuất của đạo diễn (nếu preset tồn tại)."""
        from app.styles import available_styles

        chosen = job.data.get("style") or "auto"
        styles = available_styles()
        if chosen != "auto" and chosen in styles:
            return chosen
        try:
            suggested = self._understanding(job).suggested_style
        except FileNotFoundError:
            suggested = None
        return suggested if suggested in styles else DEFAULT_STYLE

    # ---------- chạy ----------

    RECHECK_STEPS = {"choose_hook", "voice"}  # chạy lại bước để kiểm tra điều kiện, không nhảy qua

    def resume(self, job: Job) -> Job:
        """Người dùng bấm Tiếp tục (đã chọn hook / đã thả voice / đã duyệt) → chạy tiếp."""
        if job.status in (Status.waiting, Status.error) and job.step in self.RECHECK_STEPS:
            job.status = Status.pending
        else:
            job.resume()
        job.save(self.jobs_root)
        return self.run(job)

    REDO_STEPS = ("hooks", "choose_hook", "plan", "write")

    def redo(self, job: Job, step: str) -> None:
        """Làm lại từ một bước (nút trên giao diện): viết hook mới, chọn hook khác, lập lại kế hoạch, dựng lại draft."""
        from app.planner import hook_io

        if step not in self.REDO_STEPS or not job.applies(step):
            raise ValueError(f"Không làm lại được bước {step!r}")
        if step in ("hooks", "choose_hook"):
            d, _, _ = self._paths(job)
            if step == "choose_hook":
                sets, _ = hook_io.load_hooks(d)
                hook_io.save_hooks(d, sets, {})
            # câu hook đổi → voice cũ không còn khớp; giữ bản sao để không mất file
            for old in (d / "voice").glob(f"{hook_io.voice_name(1)}.*"):
                old.replace(old.with_name(f"{old.stem}_cu{old.suffix}"))
        job.step = step
        job.status = Status.pending
        job._log(f"người dùng yêu cầu làm lại từ bước {step}")
        job.save(self.jobs_root)

    def run(self, job: Job) -> Job:
        """Chạy các bước cho tới khi xong hoặc gặp điểm dừng / lỗi. Lưu job.json sau mỗi bước."""
        while job.status == Status.pending:
            step = job.step
            job.start()
            job.save(self.jobs_root)
            try:
                getattr(self, f"step_{step}")(job)
            except Exception as exc:  # báo lỗi tiếng Việt, giữ nguyên bước để chạy lại
                job.fail(f"Lỗi ở bước {step}: {exc}")
            job.save(self.jobs_root)
            if job.status == Status.running:  # bước không tự đổi trạng thái → xong, sang bước sau
                job.advance()
                job.save(self.jobs_root)
        return job

    def step_analyze(self, job: Job) -> None:
        _, analysis, _ = self._paths(job)
        if (analysis / "frames.json").is_file():
            self.log("Đã phân tích trước đó, dùng lại kết quả.")
            return
        if self._analyze_fn is None:
            from app.analysis.pipeline import run_analysis as fn
        else:
            fn = self._analyze_fn
        fn(job, self.jobs_root, progress=self.log)

    def step_understand(self, job: Job) -> None:
        from app.director.tasks import understand

        _, analysis, plan_dir = self._paths(job)
        u = understand(self.director, analysis)
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / "understanding.json").write_text(u.model_dump_json(indent=2), encoding="utf-8")
        job.data["summary_vi"] = u.summary_vi
        job.data["suggested_style"] = u.suggested_style

    def step_confirm_genre(self, job: Job) -> None:
        u = self._understanding(job)
        job.wait(f"Xác nhận nội dung: {u.summary_vi} | Phong cách sẽ dùng: {self._style_name(job)}. "
                 "Sửa plan/understanding.json nếu cần rồi bấm Tiếp tục.")

    def step_hooks(self, job: Job) -> None:
        from app.director.tasks import make_hooks
        from app.planner import hook_io

        d, analysis, _ = self._paths(job)
        hs = make_hooks(self.director, analysis, self._understanding(job), video_index=1)
        hook_io.save_hooks(d, [hs])

    def step_choose_hook(self, job: Job) -> None:
        from app.planner import hook_io

        d, _, _ = self._paths(job)
        sets, choices = hook_io.load_hooks(d)
        if not choices:
            job.wait("Chọn hook cho từng video (bảng bên dưới), rồi chạy tiếp với lựa chọn.\n" + hook_io.hook_table(sets))
            return
        path = hook_io.write_hook_scripts(d, sets, choices)
        self.log(f"Đã xuất {path}")

    def choose_hooks(self, job: Job, choices: dict[int, int]) -> None:
        from app.planner import hook_io

        d, _, _ = self._paths(job)
        sets, _ = hook_io.load_hooks(d)
        for v, c in choices.items():
            if not any(s.video_index == v for s in sets) or not 1 <= c <= 3:
                raise ValueError(f"Lựa chọn không hợp lệ: video {v} → phương án {c}")
        hook_io.save_hooks(d, sets, choices)

    def step_voice(self, job: Job) -> None:
        from app.planner import hook_io

        d, _, _ = self._paths(job)
        _, choices = hook_io.load_hooks(d)
        missing = hook_io.missing_voices(d, choices)
        if missing:
            job.wait(f"Thu voice theo câu hook bên dưới rồi tải file lên. Còn thiếu: {', '.join(missing)}")

    def step_plan(self, job: Job) -> None:
        from app.director.tasks import make_plan
        from app.planner import hook_io
        from app.styles import load_style

        d, analysis, plan_dir = self._paths(job)
        u = self._understanding(job)
        hook, hook_s = None, 0.0
        if job.options.hook:
            sets, choices = hook_io.load_hooks(d)
            hook = sets[0].options[choices[1] - 1]
            voice = hook_io.find_voice(d, 1)
            hook_s = max(3.0, self._voice_duration(voice) / 1_000_000 + 0.2) if voice else 4.0
        tpl = self._template()
        style_name = self._style_name(job)
        job.data["style_used"] = style_name
        self.log(f"Phong cách dựng: {style_name}")
        plan = make_plan(self.director, analysis, u, load_style(style_name), hook=hook, hook_s=hook_s,
                         music_items=[m for m in tpl.library if m.kind == "music"],
                         sfx_items=[m for m in tpl.library if m.kind == "sfx"],
                         decor_items=[m for m in tpl.library if m.kind in ("video_effect", "sticker", "transition",
                                                                            "filter")],
                         business=job.data.get("business", False), reframe=job.options.reframe_per_scene,
                         default_ratio=job.data.get("default_ratio") or config.load("capcut").get("default_block", "4:3"))
        (plan_dir / "edit_plan_video01.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    def _voice_duration(self, voice: Path) -> int:
        if self._probe is None:
            from app.capcut_writer.media import probe_duration as fn
        else:
            fn = self._probe
        return fn(voice)

    def step_assets(self, job: Job) -> None:
        """Giai đoạn 1: tài nguyên lấy từ dự án mẫu; thiếu gì ghi vào missing_assets.json ở bước write."""

    def step_write(self, job: Job) -> None:
        from app.director.schemas import EditPlan
        from app.director.tasks import load_analysis
        from app.planner import hook_io
        from app.planner.builder import build
        from app.styles import load_style

        d, analysis, plan_dir = self._paths(job)
        u = self._understanding(job)
        plan = EditPlan.model_validate_json((plan_dir / "edit_plan_video01.json").read_text(encoding="utf-8"))
        hook, voice = None, None
        if job.options.hook:
            sets, choices = hook_io.load_hooks(d)
            hook = sets[0].options[choices[1] - 1]
            vpath = hook_io.find_voice(d, 1)
            voice = (vpath, self._voice_duration(vpath)) if vpath else None
        clean = analysis / "audio" / "clean_00.wav"
        name = f"{job.options.client_id or 'khach'}_{job.job_id}_video01"
        res = build(plan, u, load_analysis(analysis), self._template(), self._drafts_dir or drafts_root(), name,
                    load_style(job.data.get("style_used") or self._style_name(job)), hook=hook, voice=voice,
                    clean_audio=clean.resolve() if clean.is_file() else None)
        out = res.writer.save(overwrite=True)
        (d / "missing_assets.json").write_text(json.dumps(res.missing_assets, ensure_ascii=False, indent=2),
                                               encoding="utf-8")
        job.data["draft"] = str(out)
        job.data["duration_s"] = round(res.duration_us / 1_000_000, 1)
        job.data["missing_assets"] = len(res.missing_assets)
        for n in res.notes:
            self.log(n)
        self.log(f"Đã ghi draft CapCut: {out} ({job.data['duration_s']}s)")

    def step_captions(self, job: Job) -> None:
        from app.director.schemas import EditPlan
        from app.director.tasks import captions_text, make_captions
        from app.planner import hook_io

        d, analysis, plan_dir = self._paths(job)
        plan = EditPlan.model_validate_json((plan_dir / "edit_plan_video01.json").read_text(encoding="utf-8"))
        hook = None
        if job.options.hook:
            sets, choices = hook_io.load_hooks(d)
            hook = sets[0].options[choices[1] - 1]
        c = make_captions(self.director, analysis, self._understanding(job), plan, hook=hook)
        out = d / "deliver" / "video01_captions.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(captions_text(c), encoding="utf-8")
        (plan_dir / "captions_video01.json").write_text(c.model_dump_json(indent=2), encoding="utf-8")
        job.data["captions"] = str(out)
        self.log(f"Đã xuất caption: {out}")
