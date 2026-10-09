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
        u = Understanding.model_validate_json((plan_dir / "understanding.json").read_text(encoding="utf-8"))
        keep = set(job.data.get("policy_keep") or [])
        if keep:  # người dùng chọn GIỮ LẠI một số đoạn AI cho là vi phạm chính sách → không cắt các đoạn đó
            from app.director.policy import policy_key

            u = u.model_copy(update={"policy_issues": [p for p in u.policy_issues if policy_key(p) not in keep]})
        target = job.options.target_language
        return u.dubbed_to(target) if target and target != u.language else u

    def _dubbing(self, job: Job) -> bool:
        """Có lời thuyết minh: chế độ Đổi ngôn ngữ (tiếng gốc khác tiếng đích) hoặc Review phim (luôn có lời review)."""
        return (bool(job.options.target_language) and not job.data.get("dub_same")) or job.options.review

    def _footage_size(self, job: Job) -> tuple[int, int, float]:
        """(rộng, cao, thời lượng giây) của footage, từ kết quả phân tích; chưa phân tích → (0, 0, 0)."""
        _, analysis, _ = self._paths(job)
        p = analysis / "scenes.json"
        try:
            sc = json.loads(p.read_text(encoding="utf-8"))
            sc = sc[0] if isinstance(sc, list) else sc
            return int(sc.get("width", 0)), int(sc.get("height", 0)), float(sc.get("duration", 0))
        except (OSError, ValueError, IndexError, AttributeError):
            return 0, 0, 0.0

    def _style(self, job: Job, name: str | None = None) -> dict:
        """Phong cách dựng; chế độ Đổi ngôn ngữ thì ghi đè để bản dựng khác hẳn bản gốc (không đảo cảnh)."""
        from app.styles import load_style

        style = load_style(name or job.data.get("style_used") or self._style_name(job))
        ratio = job.data.get("default_ratio")
        if ratio in ("16:9", "4:3", "1:1"):  # khung người dùng chọn khi tạo job
            style = {**style, "block_ratio": ratio, "crop_ratio": ratio}
        if job.options.target_language and not job.options.voice_only:
            dcfg = config.load("dub")
            style = {**style, **(dcfg.get("style_override") or {})}
            if not style.get("camera") and dcfg.get("camera_default"):
                style["camera"] = dcfg["camera_default"]
        parts = job.data.get("montage_parts")
        if job.options.review:  # review phim: đoạn hay theo đúng thứ tự truyện, lời review phủ gần kín, tiếng phim hạ nhỏ
            rcfg = config.load("review")
            style = {**style, "review": rcfg, "reorder": False, "cold_open": False,
                     "original_audio": rcfg.get("original_audio") or {}}
        elif (job.options.hype or parts) and not job.options.voice_only:  # chuyển cảnh liên tục, cảnh gay cấn lên đầu
            hcfg = config.load("hype")
            style = {**style, "hype": {"min_clip_s": hcfg.get("min_clip_s", 3.0), "max_clip_s": hcfg.get("max_clip_s", 5.0)},
                     "reorder": False, "cold_open": bool(hcfg.get("cold_open", False))}
            if hcfg.get("motion"):
                style["motion"] = hcfg["motion"]
            if parts:
                style["montage_parts"] = parts
        if job.options.voice_only:  # chỉ thay tiếng: giữ nguyên hình, khung = đúng tỉ lệ video gốc
            vcfg = config.load("dub").get("voice_only") or {}
            style = {**style, **(vcfg.get("style_override") or {})}
            style["music"] = {**(style.get("music") or {}), "base_db": vcfg.get("music_base_db", -12)}
            w, h, _ = self._footage_size(job)
            if w and h:
                from app.capcut_writer.layout import nearest_ratio

                r = nearest_ratio(w, h)
                style = {**style, "block_ratio": r, "crop_ratio": r}
        return style

    def _template(self):
        from app.capcut_writer import DraftTemplate

        tdir = self._template_dir if self._template_dir is not None else resolve_template(self.log)
        tpl = DraftTemplate(Path(tdir))
        if Path(tdir).resolve() != BUILTIN_TEMPLATE.resolve() and (BUILTIN_TEMPLATE / "draft_meta_info.json").is_file():
            borrowed = tpl.borrow_missing(DraftTemplate(BUILTIN_TEMPLATE))
            if borrowed:
                self.log(f"Dự án mẫu '{Path(tdir).name}' thiếu lớp {', '.join(borrowed)} → mượn khuôn từ dự án mẫu "
                         "có sẵn trong tool. Nên chọn dự án mẫu có đủ clip video, chữ, âm thanh.")
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

    RECHECK_STEPS = {"review_segments", "choose_hook", "voice", "dub_voice"}  # chạy lại bước để kiểm tra điều kiện

    def resume(self, job: Job) -> Job:
        """Người dùng bấm Tiếp tục (đã chọn hook / đã thả voice / đã duyệt) → chạy tiếp."""
        if job.status in (Status.waiting, Status.error, Status.stopped) and job.step in self.RECHECK_STEPS:
            job.status = Status.pending
        else:
            job.resume()
        job.save(self.jobs_root)
        return self.run(job)

    REDO_STEPS = ("segment", "hooks", "choose_hook", "plan", "dub", "write")

    def redo(self, job: Job, step: str) -> None:
        """Làm lại từ một bước (nút trên giao diện): chia lại video, viết hook mới, chọn hook khác,
        lập lại kế hoạch, dựng lại draft. Xóa kết quả cũ của các bước phụ thuộc."""
        from app.planner import hook_io

        if step not in self.REDO_STEPS or (step != "segment" and not job.applies(step)) or \
                (step == "segment" and not (job.options.split or job.options.review)):
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
        if step in ("segment", "hooks", "choose_hook", "plan", "dub"):
            # kế hoạch / câu thuyết minh đổi → voice thuyết minh cũ không còn khớp; giữ bản sao
            for old in (d / "voice").glob("video*_dub*.*"):
                if not old.stem.endswith("_cu"):
                    old.replace(old.with_name(f"{old.stem}_cu{old.suffix}"))
            for f in plan_dir.glob("dub_video*.json"):
                f.unlink()
            job.data.pop("dub_skip", None)
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
        if job.options.split or job.options.review:
            return for_video(u, video)
        if job.options.voice_only or job.data.get("montage_parts"):  # chỉ thay tiếng / ghép nhiều video: toàn bộ footage
            return for_video(u, {**video, "summary_vi": video.get("summary_vi") or u.summary_vi})
        return u

    def _hook_for(self, d: Path, index: int):
        from app.planner import hook_io

        sets, choices = hook_io.load_hooks(d)
        s = next((x for x in sets if x.video_index == index), None)
        return s.options[choices[index] - 1] if s and index in choices else None

    def run(self, job: Job) -> Job:
        """Chạy các bước cho tới khi xong hoặc gặp điểm dừng / lỗi / người dùng bấm Dừng. Lưu job.json sau mỗi bước."""
        from app.jobs import stop

        stop.set_current(job.job_id)
        log = self.log

        def checked_log(msg: str) -> None:  # mỗi lần báo tiến trình là một điểm kiểm tra Dừng
            log(msg)
            stop.check()

        self.log = checked_log
        try:
            return self._run(job)
        except stop.JobStopped:
            job.stop()
            job.save(self.jobs_root)
            log("⏹️ Đã dừng theo yêu cầu.")
            return job
        finally:
            self.log = log
            stop.clear(job.job_id)
            stop.set_current(None)

    def _run(self, job: Job) -> Job:
        from app.jobs import stop
        from app.jobs.limits import slot

        def waiting(what: str) -> None:  # video khác đang dùng tài nguyên này → đợi lượt
            job._log(f"Đang đợi lượt {what} (video khác đang dùng)…")
            job.save(self.jobs_root)
            self.log(f"Đợi lượt {what}…")

        while job.status == Status.pending:
            stop.check()
            step = job.step
            with slot(step, on_wait=waiting):
                job.start()
                job.save(self.jobs_root)
                try:
                    getattr(self, f"step_{step}")(job)
                except stop.JobStopped:
                    raise
                except Exception as exc:  # báo lỗi tiếng Việt, giữ nguyên bước để chạy lại
                    if stop.requested(job.job_id):  # lỗi do bị tắt giữa chừng (vd tiến trình AI bị dừng)
                        raise stop.JobStopped() from exc
                    job.fail(f"Lỗi ở bước {step}: {exc}")
            job.save(self.jobs_root)
            if job.status == Status.running:  # bước không tự đổi trạng thái → xong, sang bước sau
                job.advance()
                job.save(self.jobs_root)
        return job

    def step_analyze(self, job: Job) -> None:
        d, analysis, _ = self._paths(job)
        if (analysis / "frames.json").is_file():
            self.log("Đã phân tích trước đó, dùng lại kết quả.")
            return
        if len(job.footage) > 1 and not job.data.get("montage_parts"):
            self._build_montage(job, d)
        if self._analyze_fn is None:
            from app.analysis.pipeline import run_analysis as fn
        else:
            fn = self._analyze_fn
        fn(job, self.jobs_root, progress=self.log)

    def _build_montage(self, job: Job, d: Path) -> None:
        """Nhiều video → nối thành source/montage.mp4 (giữ danh sách gốc ở job.data.sources) để chọn cảnh từ tất cả."""
        from app.analysis.montage import build_montage

        self.log(f"Ghép {len(job.footage)} video thành một nguồn chung để chọn cảnh (có thể mất vài phút)…")
        out = d / "source" / "montage.mp4"
        fn = getattr(self, "_montage_fn", None) or build_montage
        parts = fn([Path(p) for p in job.footage], out)
        job.data["sources"] = list(job.footage)
        job.data["montage_parts"] = parts
        job.footage = [str(out.resolve())]
        job.save(self.jobs_root)
        self.log("Đã ghép xong: " + ", ".join(f"video {p['index']} ({p['end'] - p['start']:.0f}s)" for p in parts))

    def step_understand(self, job: Job) -> None:
        from app.director.tasks import understand

        _, analysis, plan_dir = self._paths(job)
        u = understand(self.director, analysis)
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / "understanding.json").write_text(u.model_dump_json(indent=2), encoding="utf-8")
        job.data["summary_vi"] = u.summary_vi
        job.data["suggested_style"] = u.suggested_style
        target = job.options.target_language
        job.data["source_language"] = u.language
        if target and target == u.language:
            job.data["dub_same"] = True
            self.log(f"Video gốc đã là {target} — "
                     + ("lời review viết luôn bằng tiếng này." if job.options.review else
                        "không cần thuyết minh, chỉ dựng lại khác bản gốc."))
        elif target:
            job.data.pop("dub_same", None)
            self.log(f"Đổi ngôn ngữ: {u.language} → {target} (thuyết minh + phụ đề {target}).")
        elif u.language not in ("ko", "ja", "en"):
            raise ValueError(f"Video gốc nói tiếng '{u.language}': hãy tạo job mới và chọn 'Đổi ngôn ngữ sang' "
                             "tiếng Hàn / Nhật / Anh.")
        if u.policy_issues:
            total = sum(x.end - x.start for x in u.policy_issues)
            self.log(f"Phát hiện {len(u.policy_issues)} đoạn vi phạm chính sách TikTok (~{total:.0f}s) — sẽ cắt bỏ.")

    def step_confirm_genre(self, job: Job) -> None:
        u = self._understanding(job)
        job.wait(f"Xác nhận nội dung: {u.summary_vi} | Phong cách sẽ dùng: {self._style_name(job)}. "
                 "Sửa plan/understanding.json nếu cần rồi bấm Tiếp tục.")

    def step_segment(self, job: Job) -> None:
        from app.director.tasks import make_segments

        _, analysis, plan_dir = self._paths(job)
        u = self._understanding(job)
        path = plan_dir / "segments.json"
        if not job.options.split and not job.options.review:
            start, end = u.usable_range.start, u.usable_range.end
            if job.options.voice_only or job.data.get("montage_parts"):  # giữ trọn footage từ giây 0 tới hết
                start, end = 0.0, self._footage_size(job)[2] or end
            videos = [{"index": 1, "start": start, "end": end, "title_vi": "", "summary_vi": u.summary_vi}]
            path.write_text(json.dumps({"videos": videos, "confirmed": True}, ensure_ascii=False, indent=2),
                            encoding="utf-8")
            job.data["videos"] = videos
            return
        if path.is_file() and json.loads(path.read_text(encoding="utf-8")).get("proposal"):
            self.log("Đã có kết quả chia video, dùng lại.")
            return
        sp = make_segments(self.director, analysis, u, review=job.options.review)
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
                                   restrict=job.options.split or job.options.review))
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
                hook_s = max(3.0, self._voice_duration(voice) / 1_000_000 + 0.2) if voice else \
                    (8.0 if hook and hook.intro.strip() else 4.0)
            self.log(f"Lập kế hoạch dựng video {i:02d}…")
            music = [m for m in tpl.library if m.kind == "music"]
            choice = job.data.get("music_choice")
            chosen = [m for m in music if m.name == choice] if choice else []
            if choice and not chosen:
                self.log(f"Không thấy bài nhạc đã chọn '{choice}' trong kho — để AI tự chọn.")
            plan = make_plan(self.director, analysis, self._u_for(job, v), self._style(job, style_name), hook=hook,
                             hook_s=hook_s, video_index=i,
                             music_items=chosen or music,
                             sfx_items=[m for m in tpl.library if m.kind == "sfx"],
                             decor_items=[m for m in tpl.library if m.kind in ("video_effect", "sticker",
                                                                                "transition", "filter")],
                             business=job.data.get("business", False) and not chosen,
                             reframe=job.options.reframe_per_scene,
                             default_ratio=job.data.get("default_ratio") if job.data.get("default_ratio") in
                             ("4:3", "1:1") else config.load("capcut").get("default_block", "4:3"))
            if chosen and plan.music.name != chosen[0].name:  # nhạc người dùng chọn luôn được dùng
                plan = plan.model_copy(update={"music": plan.music.model_copy(update={"name": chosen[0].name})})
            if chosen:
                self.log(f"Nhạc nền theo lựa chọn của bạn: {chosen[0].name}")
            out.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    def step_dub(self, job: Job) -> None:
        """Chế độ Đổi ngôn ngữ: viết câu thuyết minh (ngôn ngữ đích) theo các clip của kế hoạch dựng."""
        from app.director.base import DirectorError
        from app.director.schemas import EditPlan
        from app.director.tasks import make_dub
        from app.planner import dub_io

        if not self._dubbing(job):
            return
        d, analysis, plan_dir = self._paths(job)
        scripts = {}
        for v in self.videos(job):
            i = v["index"]
            s = dub_io.load_dub(d, i)
            if s is None:
                self.log(f"Viết lời thuyết minh video {i:02d}…")
                plan = EditPlan.model_validate_json((plan_dir / f"edit_plan_video{i:02d}.json").read_text(encoding="utf-8"))
                hook = self._hook_for(d, i) if job.options.hook else None
                try:
                    s = make_dub(self.director, analysis, self._u_for(job, v), plan, hook=hook, video_index=i,
                                 mode="review" if job.options.review else self.script_mode(job))
                except DirectorError as exc:
                    if exc.last is None:
                        raise
                    if not config.load("dub").get("accept_imperfect", False):
                        # giữ bản gần nhất để người dùng chọn "Dùng bản này" trên trang lỗi (không phải hỏi lại AI)
                        dub_io.pending_path(d, i).write_text(json.dumps(
                            {"script": exc.last.model_dump(), "problems": exc.problems}, ensure_ascii=False, indent=2),
                            encoding="utf-8")
                        raise
                    s = exc.last
                    self.log(f"Video {i:02d}: dùng bản thuyết minh gần nhất dù còn {len(exc.problems)} lỗi nhỏ "
                             "(accept_imperfect trong config/dub.yaml).")
                dub_io.dub_path(d, i).write_text(s.model_dump_json(indent=2), encoding="utf-8")
                dub_io.pending_path(d, i).unlink(missing_ok=True)
            scripts[i] = s
        path = dub_io.write_dub_scripts(d, scripts, {i: dub_io.windows_for(d, i, s) for i, s in scripts.items()})
        self.log(f"Đã xuất {path} ({sum(len(s.lines) for s in scripts.values())} câu cần thu)")

    def accept_pending_dub(self, job: Job) -> int:
        """Người dùng chọn "Dùng bản thuyết minh gần nhất" sau khi AI sửa 3 lần vẫn còn lỗi nhỏ: lấy bản đã lưu, chạy tiếp
        (không hỏi lại AI). Trả số video đã nhận."""
        from app.director.schemas import DubScript
        from app.planner import dub_io

        d, _, _ = self._paths(job)
        n = 0
        for v in self.videos(job):
            p = dub_io.pending_path(d, v["index"])
            if p.is_file():
                data = json.loads(p.read_text(encoding="utf-8"))
                s = DubScript.model_validate(data["script"])
                dub_io.dub_path(d, v["index"]).write_text(s.model_dump_json(indent=2), encoding="utf-8")
                p.unlink()
                self.log(f"Video {v['index']:02d}: dùng bản thuyết minh gần nhất, bỏ qua {len(data.get('problems', []))} lỗi.")
                n += 1
        return n

    def long_dub_lines(self, job: Job) -> dict[int, list[tuple[int, int]]]:
        """Các câu đã thu voice nhưng quá dài so với chỗ trống (đèn 🔴): {video: [(số câu, số ký tự tối đa nên viết)]}."""
        from app.director.tasks import effective_cps
        from app.planner import dub_io

        d, _, _ = self._paths(job)
        cfg = config.load("dub")
        max_speed, delay = float(cfg.get("max_speed", 1.25)), float(cfg.get("max_delay_s", 0.8))
        out: dict[int, list[tuple[int, int]]] = {}
        for v, script in self._dub_scripts(job).items():
            windows = dub_io.windows_for(d, v, script)
            u = self._u_for(job, next(x for x in self.videos(job) if x["index"] == v))
            rate = dub_io.voice_rate(d, v, script) or effective_cps(cfg, u.language)
            for i, win in enumerate(windows, 1):
                f = dub_io.find_line_voice(d, v, i)
                secs = dub_io.voice_seconds(f) if f and win else None
                if secs and dub_io.fit_status(secs, win[1], win[2] + delay, max_speed)[0] == "long":
                    out.setdefault(v, []).append((i, max(3, int(rate * (win[2] + delay) * max_speed * 0.95))))
        return out

    def shorten_dub(self, job: Job) -> int:
        """Nút "✂️ Viết gọn các câu 🔴": AI viết lại NGẮN HƠN đúng những câu voice bị tràn (giữ thời điểm, giữ các câu
        khác), voice cũ của các câu đó cất thành *_cu, job quay về chờ thu lại đúng các câu này. Trả số câu đã viết lại."""
        from app.director.tasks import shorten_dub_lines
        from app.planner import dub_io

        d, analysis, _ = self._paths(job)
        n = 0
        scripts = self._dub_scripts(job)
        for v, items in self.long_dub_lines(job).items():
            u = self._u_for(job, next(x for x in self.videos(job) if x["index"] == v))
            script = shorten_dub_lines(self.director, scripts[v], items, u)
            dub_io.dub_path(d, v).write_text(script.model_dump_json(indent=2), encoding="utf-8")
            scripts[v] = script
            for i, _ in items:
                for old in (d / "voice").glob(f"{dub_io.line_name(v, i)}.*"):
                    old.replace(old.with_name(f"{old.stem}_cu{old.suffix}"))
            n += len(items)
            self.log(f"Video {v:02d}: AI đã viết gọn {len(items)} câu thuyết minh bị tràn — thu lại đúng các câu này.")
        if n:
            dub_io.write_dub_scripts(d, scripts, {i: dub_io.windows_for(d, i, s) for i, s in scripts.items()})
            job.data.pop("dub_skip", None)
            job.step = "dub_voice"
            job.status = Status.pending
        job.save(self.jobs_root)
        return n

    def _dub_scripts(self, job: Job) -> dict:
        from app.planner import dub_io

        d, _, _ = self._paths(job)
        return {v["index"]: s for v in self.videos(job) if (s := dub_io.load_dub(d, v["index"])) is not None}

    def step_dub_voice(self, job: Job) -> None:
        from app.planner import dub_io

        if not self._dubbing(job) or job.data.get("dub_skip"):
            return
        d, _, _ = self._paths(job)
        missing = dub_io.missing_lines(d, self._dub_scripts(job))
        if missing:
            job.wait(f"Thu voice thuyết minh theo kịch bản bên dưới rồi tải lên. Còn thiếu {len(missing)} file: "
                     + ", ".join(missing[:8]) + (" …" if len(missing) > 8 else ""))

    def _text_boxes(self, job: Job, analysis: Path, a: dict) -> list:
        """Vùng chữ in sẵn trên footage (để cắt tránh / che). Chỉ dò khi AI báo footage có chữ; lưu text_boxes.json."""
        cache = analysis / "text_boxes.json"
        b = self._understanding(job).burned_in_text
        if not b.present or not (config.load("text_cover") or {}).get("enabled", True):
            return []
        if cache.is_file():
            try:
                cached = json.loads(cache.read_text(encoding="utf-8"))
                if all(isinstance(x, dict) for x in cached):  # bản cũ chưa có thời gian chữ hiện → dò lại
                    return cached
            except ValueError:
                pass
        from app.analysis.textdetect import REGION_ZONES, boxes_from_files
        from app.director.tasks import pick_evenly

        frames = pick_evenly(sorted(a["frames"], key=lambda f: f["t"]), 600)  # mọi khung (tối đa 600) để biết lúc nào có chữ
        try:
            boxes = boxes_from_files([analysis / f["file"] for f in frames], b.regions or list(REGION_ZONES),
                                     times=[f["t"] for f in frames],
                                     sample=int((config.load("text_cover") or {}).get("frames", 40)))
        except Exception as exc:  # thiếu OpenCV / khung hình hỏng: dựng bình thường, không che
            self.log(f"Không dò được vùng chữ in sẵn: {exc}")
            return []
        cache.write_text(json.dumps(boxes), encoding="utf-8")
        self.log(f"Dò được {len(boxes)} vùng chữ in sẵn trên footage.")
        return boxes

    def _bgm(self, job: Job, analysis: Path) -> Path | None:
        """Nhạc nền gốc đã tách giọng nói (lưu analysis/audio/bgm_00.wav, tách một lần). Không tách được → None
        (dùng nhạc AI chọn như thường) và ghi lý do vào nhật ký."""
        out = analysis / "audio" / "bgm_00.wav"
        if out.is_file():
            return out.resolve()
        from app.analysis.separate import separate_bgm
        from app.jobs.limits import group_slot

        bcfg = (config.load("dub").get("voice_only") or {}).get("keep_bgm") or {}
        try:
            with group_slot("gpu", on_wait=lambda what: self.log(f"Đang đợi lượt {what} để tách nhạc nền…")):
                self.log("Tách nhạc nền khỏi giọng nói của video gốc (Demucs, có thể mất vài phút)…")
                separate_bgm(Path(job.footage[0]), out, model=bcfg.get("model", "htdemucs"),
                             device=str(bcfg.get("device", "auto")))
        except Exception as exc:
            self.log(f"Không giữ được nhạc nền gốc — dùng nhạc AI chọn thay thế. Lý do: {exc}")
            return None
        self.log("Đã tách xong nhạc nền gốc.")
        return out.resolve()

    def set_policy_keep(self, job: Job, keys: list[str]) -> bool:
        """Người dùng chọn giữ lại các đoạn AI đánh dấu vi phạm chính sách. Đã có kế hoạch dựng thì lập lại kế hoạch
        (các clip phải tính lại). Trả True nếu phải lập lại."""
        old = sorted(job.data.get("policy_keep") or [])
        job.data["policy_keep"] = sorted(set(keys))
        self.log(f"Giữ lại {len(job.data['policy_keep'])} đoạn bị AI đánh dấu vi phạm chính sách TikTok (theo lựa chọn "
                 "của bạn).")
        _, _, plan_dir = self._paths(job)
        if job.data["policy_keep"] != old and list(plan_dir.glob("edit_plan_video*.json")):
            self.redo(job, "plan")
            return True
        job.save(self.jobs_root)
        return False

    def script_mode(self, job: Job) -> str:
        """Cách viết thuyết minh: rewrite (AI xem video, viết mới theo nước đích) hoặc translate (dịch sát)."""
        mode = job.options.script_mode or config.load("dub").get("default_script_mode", "rewrite")
        return mode if mode in ("rewrite", "translate") else "rewrite"

    def vi_subtitles(self, job: Job) -> bool:
        """Phụ đề tiếng Việt để kiểm tra (chế độ Đổi ngôn ngữ): theo nút bật/tắt của job, mặc định theo config/dub.yaml."""
        if "vi_subs" in job.data:
            return bool(job.data["vi_subs"])
        return bool((config.load("dub").get("vi_subtitles") or {}).get("enabled", True))

    def set_vi_subtitles(self, job: Job, on: bool) -> None:
        """Bật / tắt phụ đề tiếng Việt rồi dựng lại draft (không hỏi lại AI)."""
        job.data["vi_subs"] = bool(on)
        if job.data.get("drafts"):
            self.redo(job, "write")
        else:
            job.save(self.jobs_root)

    def set_music(self, job: Job, name: str | None) -> int:
        """Đổi nhạc nền sau khi đã có kế hoạch dựng (không hỏi lại AI): ghi vào mọi edit_plan rồi dựng lại draft.
        name rỗng = để AI chọn lại (lập lại kế hoạch). Trả số kế hoạch đã sửa."""
        from app.director.schemas import EditPlan

        d, _, plan_dir = self._paths(job)
        if not name:
            job.data.pop("music_choice", None)
            self.redo(job, "plan")
            return 0
        job.data["music_choice"] = name
        n = 0
        for f in sorted(plan_dir.glob("edit_plan_video*.json")):
            plan = EditPlan.model_validate_json(f.read_text(encoding="utf-8"))
            plan = plan.model_copy(update={"music": plan.music.model_copy(update={"name": name})})
            f.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
            n += 1
        if n:
            self.redo(job, "write")
        else:
            job.save(self.jobs_root)
        return n

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
        from app.director.policy import cut_ranges, repair_policy
        from app.director.policy import load_cfg as policy_cfg
        from app.director.tasks import load_analysis
        from app.planner import hook_io
        from app.planner.builder import build

        if job.options.vi_sub:
            return self._write_vi_sub(job)
        d, analysis, plan_dir = self._paths(job)
        tpl = self._template()
        style = self._style(job)
        a = load_analysis(analysis)
        a["text_boxes"] = self._text_boxes(job, analysis, a)
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
            u_v = self._u_for(job, v)
            plan, cut = repair_policy(plan, cut_ranges(u_v), policy_cfg().get("min_piece_s", 0.5))
            for c in cut:  # lưới an toàn: đoạn vi phạm được đánh dấu sau khi đã có kế hoạch dựng
                self.log(f"[video {i:02d}] {c}")
            hook, voice = None, None
            if job.options.hook:
                hook = self._hook_for(d, i)
                vpath = hook_io.find_voice(d, i)
                voice = (vpath, self._voice_duration(vpath)) if vpath else None
            name = f"{job.options.client_id or 'khach'}_{job.job_id}_video{i:02d}"
            dub, dub_voices = None, None
            if self._dubbing(job):
                from app.planner import dub_io

                dub = dub_io.load_dub(d, i)
                if dub is not None:
                    dub_voices = {}
                    for n in range(1, len(dub.lines) + 1):
                        f = dub_io.find_line_voice(d, i, n)
                        if f is not None:
                            dub_voices[n] = (f.resolve(), self._voice_duration(f))
                    rate = dub_io.voice_rate(d, i, dub)
                    if rate:  # nhớ tốc độ đọc thật của giọng bạn → lần sau AI viết câu vừa giọng, khỏi đè tiếng
                        saved = dub_io.remember_voice_rate(u_v.language, rate)
                        self.log(f"Giọng thu của bạn đọc ~{rate:.1f} ký tự/giây ({u_v.language}); đã lưu {saved:.1f} "
                                 "để lần sau viết câu thuyết minh vừa giọng.")
            bgm = self._bgm(job, analysis) if job.options.voice_only and job.options.keep_bgm else None
            res = build(plan, u_v, a, tpl, self._drafts_dir or drafts_root(), name, style,
                        hook=hook, voice=voice, clean_audio=clean.resolve() if clean.is_file() else None,
                        video_index=i, dub=dub, dub_voices=dub_voices, vi_subtitles=self.vi_subtitles(job),
                        bgm_audio=bgm)
            out = res.writer.save(overwrite=True)
            dur = round(res.duration_us / 1_000_000, 1)
            drafts.append({"index": i, "draft": str(out), "duration_s": dur, "missing_assets": len(res.missing_assets),
                           "start": v["start"], "end": v["end"],
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

    def _write_vi_sub(self, job: Job) -> None:
        """Phụ đề tiếng Việt: dịch lời (lưu plan/subtitle_vi.json, dịch một lần) → .srt + draft CapCut giữ nguyên video."""
        from app.capcut_writer import VideoSource
        from app.director.tasks import load_analysis
        from app.planner import visub

        d, analysis, plan_dir = self._paths(job)
        a = load_analysis(analysis)
        segs = [s for s in a["transcript"].get("segments", []) if s.get("text", "").strip()]
        if not segs:
            raise ValueError("Không nhận dạng được lời thoại nào trong video — không có gì để dịch.")
        lang = a["transcript"].get("language") or ""
        cache = plan_dir / "subtitle_vi.json"
        plan_dir.mkdir(parents=True, exist_ok=True)
        vi = json.loads(cache.read_text(encoding="utf-8")) if cache.is_file() else None
        if not vi or len(vi) != len(segs):
            self.log(f"Dịch {len(segs)} câu thoại ({lang or 'không rõ tiếng'}) sang tiếng Việt…")
            vi = visub.translate(self.director, segs, lang, int(config.load("dub").get("vi_sub_batch", 60)))
            cache.write_text(json.dumps(vi, ensure_ascii=False, indent=2), encoding="utf-8")
        cue_list = visub.cues(segs, vi)
        name = f"{job.options.client_id or 'khach'}_{job.job_id}_vietsub"
        deliver = d / "deliver"
        deliver.mkdir(exist_ok=True)
        srt_path = deliver / f"{Path(job.footage[0]).stem}_vi.srt"
        srt_path.write_text(visub.srt(cue_list), encoding="utf-8-sig")  # BOM: trình phát Windows đọc đúng dấu tiếng Việt
        sc = a["scenes"]
        src = VideoSource(Path(sc["path"]), sc["width"], sc["height"], round(sc["duration"] * 1_000_000))
        w = visub.build_draft(self._template(), self._drafts_dir or drafts_root(), name, src, cue_list)
        out = w.save(overwrite=True)
        dur = round(sc["duration"], 1)
        job.data.update({"drafts": [{"index": 1, "draft": str(out), "duration_s": dur, "missing_assets": 0,
                                     "start": 0.0, "end": dur, "short": False, "credits": []}],
                         "draft": str(out), "duration_s": dur, "missing_assets": 0, "srt": str(srt_path)})
        self.log(f"Đã dịch xong {len(cue_list)} dòng phụ đề tiếng Việt → {srt_path}")
        self.log(f"Đã ghi draft CapCut: {out}")

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
