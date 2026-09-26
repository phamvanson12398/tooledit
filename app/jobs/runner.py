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


BUILTIN_TEMPLATE = config.ROOT / "samples" / "capcut_template"
BUILTIN = "__builtin__"  # giá trị cài đặt: dùng dự án mẫu có sẵn trong tool


def list_drafts(root: Path) -> list[tuple[Path, str]]:
    """Các dự án CapCut trên máy: (thư mục, tên hiển thị)."""
    if not Path(root).is_dir():
        return []
    out = []
    for d in sorted(Path(root).iterdir()):
        meta = d / "draft_meta_info.json"
        if not meta.is_file():
            continue
        try:
            name = json.loads(meta.read_text(encoding="utf-8-sig")).get("draft_name") or d.name
        except (OSError, ValueError):
            name = d.name
        out.append((d, name))
    return out


def template_name() -> str:
    """Tên dự án mẫu: chọn trên giao diện (config/local.yaml) trước, rồi tới config/capcut.yaml."""
    from app import settings

    return settings.load().get("template_name") or config.load("capcut").get("template_name", "capcut_template")


def resolve_template(log=lambda m: None) -> Path:
    """Tìm dự án mẫu CapCut; không thấy thì dùng mẫu có sẵn trong tool (samples/capcut_template) thay vì dừng job."""
    name = template_name()
    if name != BUILTIN:
        try:
            found = find_template(drafts_root(), name)
        except RuntimeError:
            found = None
        if found is not None:
            return found
    if (BUILTIN_TEMPLATE / "draft_meta_info.json").is_file():
        if name != BUILTIN:
            log(f"Không thấy dự án mẫu '{name}' trong CapCut → dùng dự án mẫu có sẵn trong tool. "
                "Có thể chọn dự án mẫu khác ở trang chủ (⚙️ Dự án mẫu CapCut).")
        return BUILTIN_TEMPLATE
    try:
        names = ", ".join(n for _, n in list_drafts(drafts_root())) or "(không có dự án nào)"
    except RuntimeError as exc:
        names = str(exc)
    raise RuntimeError(f"Không thấy dự án mẫu CapCut '{name}'. Các dự án đang có: {names}. "
                       "Chọn lại ở trang chủ (⚙️ Dự án mẫu CapCut).")


def _load_labels_safe() -> dict:
    from app.capcut_writer.template import _load_labels

    return _load_labels()


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

        tdir = self._template_dir if self._template_dir is not None else resolve_template(self.log)
        tpl = DraftTemplate(Path(tdir))
        if self._template_dir is None and config.load("capcut").get("library_scan", True):
            from app.capcut_writer.library import scan_drafts
            from app.capcut_writer.template import _load_labels

            added = tpl.merge_items(scan_drafts(drafts_root()))
            tpl._apply_labels(_load_labels())
            self.log(f"Kho tài nguyên tự quét từ CapCut: thêm {added} mục")
        if self._template_dir is None:  # tài nguyên đã nhập từ dự án CapCut (kể cả dự án đã xóa / từ máy khác)
            from app.assets.capcut_import import load_imported

            added = tpl.merge_items(load_imported())
            tpl._apply_labels(_load_labels_safe())
            if added:
                self.log(f"Kho nhập từ dự án CapCut: thêm {added} mục")
        if self._template_dir is None:
            from app.assets.local import scan_local

            added = tpl.merge_items(scan_local())
            if added:
                self.log(f"Kho local assets/: thêm {added} file âm thanh")
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

    RECHECK_STEPS = {"review_segments", "choose_hook", "voice"}  # chạy lại bước để kiểm tra điều kiện

    def resume(self, job: Job) -> Job:
        """Người dùng bấm Tiếp tục (đã chọn hook / đã thả voice / đã duyệt) → chạy tiếp."""
        if job.status in (Status.waiting, Status.error) and job.step in self.RECHECK_STEPS:
            job.status = Status.pending
        else:
            job.resume()
        job.save(self.jobs_root)
        return self.run(job)

    REDO_STEPS = ("segment", "hooks", "choose_hook", "plan", "write")

    def redo(self, job: Job, step: str) -> None:
        """Làm lại từ một bước (nút trên giao diện): chia lại video, viết hook mới, chọn hook khác,
        lập lại kế hoạch, dựng lại draft. Xóa kết quả cũ của các bước phụ thuộc."""
        from app.planner import hook_io

        if step not in self.REDO_STEPS or (step != "segment" and not job.applies(step)) or \
                (step == "segment" and not job.options.split):
            raise ValueError(f"Không làm lại được bước {step!r}")
        d, _, plan_dir = self._paths(job)
        if step == "segment":
            for f in (plan_dir / "segments.json", hook_io.hooks_path(d)):
                f.unlink(missing_ok=True)
            job.data.pop("videos", None)
        if step == "hooks":
            hook_io.hooks_path(d).unlink(missing_ok=True)
        if step == "choose_hook":
            sets, _ = hook_io.load_hooks(d)
            hook_io.save_hooks(d, sets, {})
        if step in ("segment", "hooks", "choose_hook"):
            # câu hook đổi → voice cũ không còn khớp; giữ bản sao để không mất file
            for old in (d / "voice").glob("video*_hook.*"):
                old.replace(old.with_name(f"{old.stem}_cu{old.suffix}"))
        if step in ("segment", "hooks", "choose_hook", "plan"):
            self._clear_plans(d, plan_dir)
        job.step = step
        job.status = Status.pending
        job._log(f"người dùng yêu cầu làm lại từ bước {step}")
        job.save(self.jobs_root)

    @staticmethod
    def _clear_plans(d: Path, plan_dir: Path) -> None:
        for pattern in ("edit_plan_video*.json", "captions_video*.json"):
            for f in plan_dir.glob(pattern):
                f.unlink()
        for f in (d / "deliver").glob("video*_captions.txt"):
            f.unlink()

    # ---------- danh sách video của job ----------

    def videos(self, job: Job) -> list[dict]:
        """Các video sẽ dựng: [{index, start, end, title_vi, summary_vi}]. Job cũ / không chia → 1 video."""
        if job.data.get("videos"):
            return job.data["videos"]
        u = self._understanding(job)
        return [{"index": 1, "start": u.usable_range.start, "end": u.usable_range.end, "title_vi": "",
                 "summary_vi": u.summary_vi}]

    def _u_for(self, job: Job, video: dict):
        from app.director.tasks import for_video

        u = self._understanding(job)
        return for_video(u, video) if job.options.split else u

    def _hook_for(self, d: Path, index: int):
        from app.planner import hook_io

        sets, choices = hook_io.load_hooks(d)
        s = next((x for x in sets if x.video_index == index), None)
        return s.options[choices[index] - 1] if s and index in choices else None

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

    def step_segment(self, job: Job) -> None:
        from app.director.tasks import make_segments

        _, analysis, plan_dir = self._paths(job)
        u = self._understanding(job)
        path = plan_dir / "segments.json"
        if not job.options.split:
            videos = [{"index": 1, "start": u.usable_range.start, "end": u.usable_range.end, "title_vi": "",
                       "summary_vi": u.summary_vi}]
            path.write_text(json.dumps({"videos": videos, "confirmed": True}, ensure_ascii=False, indent=2),
                            encoding="utf-8")
            job.data["videos"] = videos
            return
        if path.is_file() and json.loads(path.read_text(encoding="utf-8")).get("proposal"):
            self.log("Đã có kết quả chia video, dùng lại.")
            return
        sp = make_segments(self.director, analysis, u)
        videos = [{"index": i, "start": v.start, "end": v.end, "title_vi": v.title_vi, "summary_vi": v.summary_vi,
                   "why_vi": v.why_vi} for i, v in enumerate(sorted(sp.videos, key=lambda v: v.start), 1)]
        data = {"proposal": sp.model_dump(), "videos": videos, "confirmed": False}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        job.data["videos"] = videos
        self.log(f"Đạo diễn chia thành {len(videos)} video, bỏ {len(sp.dropped)} đoạn.")

    def step_review_segments(self, job: Job) -> None:
        _, _, plan_dir = self._paths(job)
        data = json.loads((plan_dir / "segments.json").read_text(encoding="utf-8"))
        if not data.get("confirmed"):
            job.wait(f"Duyệt cách chia video: {len(data.get('videos', []))} video. Chỉnh điểm cắt, bỏ bớt hoặc "
                     "thêm đoạn bị bỏ rồi bấm Xác nhận.")

    def apply_segments(self, job: Job, rows: list[dict]) -> None:
        """Người dùng duyệt bảng chia video: rows = [{start, end, title_vi, summary_vi}] các video giữ lại."""
        from app.director.tasks import load_analysis
        from app.planner import hook_io

        d, analysis, plan_dir = self._paths(job)
        duration = load_analysis(analysis)["scenes"]["duration"]
        rows = sorted(rows, key=lambda r: float(r["start"]))
        if not rows:
            raise ValueError("Cần giữ ít nhất một video.")
        for r in rows:
            a, b = float(r["start"]), float(r["end"])
            if not (0 <= a < b <= duration + 0.5):
                raise ValueError(f"Điểm cắt {a:.1f}–{b:.1f}s không hợp lệ (footage dài {duration:.1f}s).")
        for x, y in zip(rows, rows[1:]):
            if float(y["start"]) < float(x["end"]) - 0.5:
                raise ValueError(f"Video {float(x['start']):.1f}–{float(x['end']):.1f}s và "
                                 f"{float(y['start']):.1f}–{float(y['end']):.1f}s chồng nhau.")
        videos = [{"index": i, "start": float(r["start"]), "end": float(r["end"]), "title_vi": r.get("title_vi", ""),
                   "summary_vi": r.get("summary_vi", "")} for i, r in enumerate(rows, 1)]
        path = plan_dir / "segments.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        changed = data.get("videos") != videos or not data.get("confirmed")
        data.update({"videos": videos, "confirmed": True})
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        job.data["videos"] = videos
        if changed:  # chia khác đi → hook / kế hoạch cũ không còn đúng
            hook_io.hooks_path(d).unlink(missing_ok=True)
            self._clear_plans(d, plan_dir)
        job.save(self.jobs_root)

    def step_hooks(self, job: Job) -> None:
        from app.director.tasks import make_hooks
        from app.planner import hook_io

        d, analysis, _ = self._paths(job)
        sets, choices = hook_io.load_hooks(d) if hook_io.hooks_path(d).is_file() else ([], {})
        done = {s.video_index for s in sets}
        for v in self.videos(job):
            if v["index"] in done:
                continue
            self.log(f"Viết hook cho video {v['index']:02d}…")
            sets.append(make_hooks(self.director, analysis, self._u_for(job, v), video_index=v["index"],
                                   restrict=job.options.split))
            hook_io.save_hooks(d, sorted(sets, key=lambda s: s.video_index), choices)

    def step_choose_hook(self, job: Job) -> None:
        from app.planner import hook_io

        d, _, _ = self._paths(job)
        sets, choices = hook_io.load_hooks(d)
        if not choices or any(v["index"] not in choices for v in self.videos(job)):
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
        tpl = self._template()
        style_name = self._style_name(job)
        job.data["style_used"] = style_name
        self.log(f"Phong cách dựng: {style_name}")
        for v in self.videos(job):
            i = v["index"]
            out = plan_dir / f"edit_plan_video{i:02d}.json"
            if out.is_file():
                continue
            hook, hook_s = None, 0.0
            if job.options.hook:
                hook = self._hook_for(d, i)
                voice = hook_io.find_voice(d, i)
                hook_s = max(3.0, self._voice_duration(voice) / 1_000_000 + 0.2) if voice else 4.0
            self.log(f"Lập kế hoạch dựng video {i:02d}…")
            plan = make_plan(self.director, analysis, self._u_for(job, v), load_style(style_name), hook=hook,
                             hook_s=hook_s, video_index=i,
                             music_items=[m for m in tpl.library if m.kind == "music"],
                             sfx_items=[m for m in tpl.library if m.kind == "sfx"],
                             decor_items=[m for m in tpl.library if m.kind in ("video_effect", "sticker",
                                                                                "transition", "filter")],
                             business=job.data.get("business", False), reframe=job.options.reframe_per_scene,
                             default_ratio=job.data.get("default_ratio")
                             or config.load("capcut").get("default_block", "4:3"))
            out.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

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
        tpl = self._template()
        style = load_style(job.data.get("style_used") or self._style_name(job))
        a = load_analysis(analysis)
        clean = analysis / "audio" / "clean_00.wav"
        if (style.get("audio") or {}).get("clean") == "light":  # vlog: lọc ồn nhẹ, giữ âm thanh hiện trường
            light = analysis / "audio" / "light_00.wav"
            if light.is_file():
                clean = light
            else:
                self.log("Job phân tích trước khi có bản lọc ồn nhẹ — dùng bản lọc ồn thường (tạo job mới để có).")
        drafts, missing = [], []
        for v in self.videos(job):
            i = v["index"]
            plan = EditPlan.model_validate_json((plan_dir / f"edit_plan_video{i:02d}.json").read_text(encoding="utf-8"))
            hook, voice = None, None
            if job.options.hook:
                hook = self._hook_for(d, i)
                vpath = hook_io.find_voice(d, i)
                voice = (vpath, self._voice_duration(vpath)) if vpath else None
            name = f"{job.options.client_id or 'khach'}_{job.job_id}_video{i:02d}"
            res = build(plan, self._u_for(job, v), a, tpl, self._drafts_dir or drafts_root(), name, style,
                        hook=hook, voice=voice, clean_audio=clean.resolve() if clean.is_file() else None,
                        video_index=i)
            out = res.writer.save(overwrite=True)
            dur = round(res.duration_us / 1_000_000, 1)
            drafts.append({"index": i, "draft": str(out), "duration_s": dur, "missing_assets": len(res.missing_assets),
                           "short": dur < config.load("split").get("min_video_s", 60),
                           "credits": self._credits(res.used_local)})
            missing += res.missing_assets
            for n in res.notes:
                self.log(f"[video {i:02d}] {n}")
            self.log(f"Đã ghi draft CapCut: {out} ({dur}s)")
        (d / "missing_assets.json").write_text(json.dumps(missing, ensure_ascii=False, indent=2), encoding="utf-8")
        job.data["drafts"] = drafts
        job.data["draft"] = drafts[0]["draft"]
        job.data["duration_s"] = drafts[0]["duration_s"]
        job.data["missing_assets"] = len(missing)

    @staticmethod
    def _credits(used_paths: list[str]) -> list[str]:
        """Dòng ghi nguồn cho các file trong kho có giấy phép yêu cầu ghi tác giả (ví dụ Incompetech CC BY)."""
        from app.assets import ledger

        root = ledger.ASSETS_ROOT.resolve()
        by_file = ledger.by_file(ledger.ASSETS_ROOT)
        lines = []
        for p in used_paths:
            try:
                rel = Path(p).resolve().relative_to(root).as_posix()
            except ValueError:
                continue
            e = by_file.get(rel)
            if e and e.get("credit_required"):
                lines.append(ledger.credit_line(e))
        return lines

    def step_captions(self, job: Job) -> None:
        from app.director.schemas import Captions, EditPlan
        from app.director.tasks import captions_text, make_captions

        d, analysis, plan_dir = self._paths(job)
        credits = {dr["index"]: dr.get("credits") or [] for dr in job.data.get("drafts", [])}
        for v in self.videos(job):
            i = v["index"]
            out = d / "deliver" / f"video{i:02d}_captions.txt"
            cap_json = plan_dir / f"captions_video{i:02d}.json"
            if cap_json.is_file() and out.is_file():  # đã viết rồi: không gọi lại AI, chỉ cập nhật phần ghi nguồn
                c = Captions.model_validate_json(cap_json.read_text(encoding="utf-8"))
            else:
                plan = EditPlan.model_validate_json((plan_dir / f"edit_plan_video{i:02d}.json").read_text(encoding="utf-8"))
                hook = self._hook_for(d, i) if job.options.hook else None
                c = make_captions(self.director, analysis, self._u_for(job, v), plan, hook=hook, video_index=i)
                cap_json.write_text(c.model_dump_json(indent=2), encoding="utf-8")
            text = captions_text(c)
            if credits.get(i):
                text += "\n\n=== GHI NGUỒN (bắt buộc theo giấy phép, dán vào caption) ===\n" + "\n".join(credits[i])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            self.log(f"Đã xuất caption: {out}")
        job.data["captions"] = str(d / "deliver")
