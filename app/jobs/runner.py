"""Chạy job theo từng bước, dừng ở các điểm chờ người dùng (mục 3). Dùng chung cho dòng lệnh và giao diện web.

Giai đoạn 1: một video, phong cách tiktok_retention.
"""

from __future__ import annotations

import json
import time
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


LANG_VI = {"zh": "Trung", "vi": "Việt", "th": "Thái", "es": "Tây Ban Nha", "fr": "Pháp", "de": "Đức", "ru": "Nga",
           "id": "Indonesia", "pt": "Bồ Đào Nha", "ko": "Hàn", "ja": "Nhật", "en": "Anh"}


class Runner:
    def __init__(self, jobs_root: Path, *, director=None, analyze_fn=None, probe_duration_fn=None,
                 drafts_dir: Path | None = None, template_dir: Path | None = None,
                 log: Callable[[str], None] = print):
        self.jobs_root = Path(jobs_root)
        self.log = log
        self._director = director
        self._fixed_director = director is not None  # test truyền sẵn đạo diễn → luôn dùng cái đó
        self._ai: str | None = None
        self._analyze_fn = analyze_fn
        self._probe = probe_duration_fn
        self._drafts_dir = drafts_dir
        self._template_dir = template_dir

    # ---------- phụ trợ ----------

    @property
    def director(self):
        if self._director is None:
            from app.director import get_director

            self._director = get_director(ai=self._ai, log=self.log)
        return self._director

    def use_ai(self, job: Job) -> None:
        """Dùng AI đạo diễn đã chọn cho job này (Claude / Gemini — chủ dự án 11/10)."""
        ai = job.options.ai or None
        if ai != self._ai and not self._fixed_director:
            self._director = None
        self._ai = ai

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
        return (bool(job.options.target_language) and not job.data.get("dub_same")) or job.options.review or \
            job.options.films or job.options.sell

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
        from app.capcut_writer.layout import RATIOS

        if ratio in RATIOS:  # khung người dùng chọn khi tạo job (16:9 / 4:3 / 1:1 / 4:5 / 3:4 / 9:10 / 9:16)
            style = {**style, "block_ratio": ratio, "crop_ratio": ratio}
        if job.options.char_dub:  # lồng tiếng nhân vật: hình giữ tự nhiên (không "khác bản gốc"), chỉ cắt rề rà
            style = {**style, "char_dub": config.load("char_dub"), "reorder": False, "cold_open": False, "remix": False,
                     "motion": {}}  # không tự thêm chuyển động hình (chủ dự án 11/10: chỉ chọn đoạn hay, không edit)
        elif job.options.target_language and not job.options.voice_only:
            dcfg = config.load("dub")
            style = {**style, **(dcfg.get("style_override") or {})}
            if not style.get("camera") and dcfg.get("camera_default"):
                style["camera"] = dcfg["camera_default"]
        parts = job.data.get("montage_parts")
        if job.options.review:  # review phim: đoạn hay theo đúng thứ tự truyện, lời review phủ gần kín, tiếng phim hạ nhỏ
            from app.director.tasks import review_target

            rcfg = review_target(config.load("review"), job.options.review_s)  # thời lượng chủ dự án chọn (11/10)
            if job.options.cliff:  # review bỏ lửng (14/10): mỗi phần một video 1:30–2:00 (tính cả short mở đầu)
                from app.director.cliff import cliff_target

                rcfg = cliff_target(config.load("review"))
            style = {**style, "review": rcfg, "reorder": False, "cold_open": False,
                     "original_audio": rcfg.get("original_audio") or {}}
            if rcfg.get("layout"):  # bố cục như video mẫu: khối phim 9:10 cắt thẳng từ footage, bám nhân vật
                style.update({"layout": rcfg["layout"], "block_ratio": "9:10", "crop_ratio": None})
        elif (job.options.hype or parts) and not job.options.voice_only and not job.options.char_dub:  # chuyển cảnh liên tục, cảnh gay cấn lên đầu
            hcfg = config.load("hype")
            style = {**style, "hype": {"min_clip_s": hcfg.get("min_clip_s", 3.0), "max_clip_s": hcfg.get("max_clip_s", 5.0)},
                     "reorder": False, "cold_open": bool(hcfg.get("cold_open", False))}
            if hcfg.get("motion"):
                style["motion"] = hcfg["motion"]
            if parts:
                style["montage_parts"] = parts
        if job.options.sell:  # bán content: cảnh do tool cắt theo voice (đảo thứ tự / dùng lại), âm thanh gốc tắt hẳn
            from app.director.sell import sell_cfg

            scfg = sell_cfg()
            dcfg = (config.load("dub").get("style_override") or {})
            style = {**style, "sell": scfg, "reorder": False, "cold_open": False, "remix": False, "hype": None,
                     "original_audio": {"mute": True}, "mirror": None, "camera": None, "arrows": False,
                     "beat_sync": {"enabled": False},  # điểm cắt theo voice, không dời theo nhịp nhạc
                     "motion": dcfg.get("motion") or {"every_clip": True, "max_scale": 1.2},
                     "music": {**(style.get("music") or {}), "base_db": scfg.get("music_base_db", -14)}}
            style.update(self._burned_in_skip(job, scfg))
        if job.options.voice_only:  # chỉ thay tiếng: giữ nguyên hình, khung = đúng tỉ lệ video gốc
            vcfg = config.load("dub").get("voice_only") or {}
            style = {**style, **(vcfg.get("style_override") or {})}
            style["music"] = {**(style.get("music") or {}), "base_db": vcfg.get("music_base_db", -12)}
            w, h, _ = self._footage_size(job)
            if w and h:
                from app.capcut_writer.layout import nearest_ratio

                r = nearest_ratio(w, h)
                style = {**style, "block_ratio": r, "crop_ratio": r}
        if job.data.get("default_ratio") == "source":  # chủ dự án 15/10: khung video GỐC, không cắt, không thu phóng
            style = self._keep_frame(job, style)
        return style

    def _keep_frame(self, job: Job, style: dict) -> dict:
        """Khối hình = đúng tỉ lệ video gốc (gần nhất trong RATIOS, bố cục chữ tự dời theo khối), không crop, không zoom /
        chuyển động / góc máy theo người nói (builder đọc `keep_frame`)."""
        from app.capcut_writer.layout import nearest_ratio

        w, h, _ = self._footage_size(job)
        r = nearest_ratio(w, h) if w and h else style.get("block_ratio") or "16:9"
        return {**style, "keep_frame": True, "block_ratio": r, "crop_ratio": None, "motion": {}, "camera": {}}

    def _burned_in_skip(self, job: Job, scfg: dict) -> dict:
        """Bán content (chủ dự án 17/10): video gốc đã có chữ / phụ đề in sẵn → không đè chữ của tool lên: dải chữ trên →
        bỏ tiêu đề, ở giữa → bỏ chữ nhấn; chữ ở góc (logo) không tính. Chủ dự án 18/10 ("bán content không có sub ngôn ngữ
        muốn chuyển sang nữa"): phụ đề ngôn ngữ đích LUÔN có — dải chữ dưới / không rõ vùng thì phụ đề có NỀN TỐI che phụ
        đề cũ (`sub_cover`), không bỏ phụ đề nữa."""
        if not scfg.get("burned_in_skip", True):
            return {}
        try:
            b = self._understanding(job).burned_in_text
        except (OSError, ValueError):
            return {}
        if not b.present:
            return {}
        regions = set(b.regions or [])
        if not regions:
            return {"no_titles": True, "sub_cover": True}
        # chỉ dải chữ chạy ngang cả khung (top / bottom) mới đè tiêu đề / phụ đề; chữ ở góc (logo, tên kênh) thì không
        return {"no_titles": "top" in regions, "sub_cover": "bottom" in regions, "no_emphasis": "center" in regions}

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

    RECHECK_STEPS = {"post", "films_wait", "review_segments", "choose_hook", "voice", "dub_voice"}  # chạy lại bước để kiểm tra điều kiện

    def resume(self, job: Job) -> Job:
        """Người dùng bấm Tiếp tục (đã chọn hook / đã thả voice / đã duyệt) → chạy tiếp."""
        if job.status == Status.done:  # job xong rồi mới thu lại / thêm voice → cập nhật draft của video đó
            from app.jobs import stop

            stop.set_current(job.job_id)
            try:
                self.refresh_voice_drafts(job)
            finally:
                stop.set_current(None)
            return job
        if job.status in (Status.waiting, Status.error, Status.stopped) and job.step in self.RECHECK_STEPS:
            job.status = Status.pending
        else:
            job.resume()
        job.save(self.jobs_root)
        return self.run(job)

    REDO_STEPS = ("segment", "hooks", "choose_hook", "plan", "dub", "write", "match")

    def redo(self, job: Job, step: str) -> None:
        """Làm lại từ một bước (nút trên giao diện): chia lại video, viết hook mới, chọn hook khác,
        lập lại kế hoạch, dựng lại draft. Xóa kết quả cũ của các bước phụ thuộc."""
        from app.planner import hook_io

        if job.options.films and step in ("match", "write"):  # content nhiều phim: tìm lại cảnh (giữ voice) / dựng lại
            if step == "match":
                from app.planner import dub_io

                d, _, plan_dir = self._paths(job)
                (plan_dir / "films_match.json").unlink(missing_ok=True)
                dub_io.dub_path(d, 1).unlink(missing_ok=True)  # lời không đổi → voice đã thu vẫn dùng được
                job.data.pop("ready_drafts", None)
            job.step, job.status = step, Status.pending
            job._log(f"người dùng yêu cầu làm lại từ bước {step}")
            job.save(self.jobs_root)
            return
        if step not in self.REDO_STEPS or step == "match" or (step != "segment" and not job.applies(step)) or \
                (step == "segment" and not job.picks_segments):
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
        n = max(1, min(int(job.options.sell_variants or 1), int(config.load("sell").get("max_variants", 3)))) \
            if job.options.sell else 1
        if n > 1:  # bán content: nhiều bản khác nhau từ CÙNG video (chủ dự án 17/10)
            return [{"index": i, "start": u.usable_range.start, "end": u.usable_range.end, "title_vi": f"Bản {i}",
                     "summary_vi": u.summary_vi} for i in range(1, n + 1)]
        return [{"index": 1, "start": u.usable_range.start, "end": u.usable_range.end, "title_vi": "",
                 "summary_vi": u.summary_vi}]

    def _u_for(self, job: Job, video: dict):
        from app.director.tasks import for_video

        u = self._understanding(job)
        if job.options.split or job.options.review or job.options.char_dub or job.options.ideas:
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
        self.use_ai(job)
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
                t0 = time.monotonic()
                try:
                    getattr(self, f"step_{step}")(job)
                    took = time.monotonic() - t0
                    if took >= 5:  # ghi thời gian từng bước (chủ dự án 11/10 "chậm quá" — biết bước nào lâu)
                        job.data.setdefault("step_times", {})[step] = round(took, 1)
                        self.log(f"⏱️ Bước {step} mất {int(took) // 60}:{int(took) % 60:02d}")
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
        if len(job.footage) > 1 and not job.data.get("montage_parts") and not job.options.films:
            self._build_montage(job, d)  # content nhiều phim: mỗi phim phân tích riêng (footage 0, 1, 2…), không nối
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
        from app.director.tasks import TARGET_LANGS, understand

        _, analysis, plan_dir = self._paths(job)
        saved = plan_dir / "understanding.json"
        if job.data.pop("reuse_understanding", False) and saved.is_file():  # vừa chọn ngôn ngữ sau lỗi → khỏi hỏi lại AI
            from app.director.schemas import Understanding

            u = Understanding.model_validate_json(saved.read_text(encoding="utf-8"))
        else:
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
        elif u.language not in TARGET_LANGS:
            job.data["need_language"] = u.language
            raise ValueError(f"Video gốc nói tiếng '{LANG_VI.get(u.language, u.language)}' — bản TikTok phải là tiếng "
                             "Hàn / Nhật / Anh / Đức. Chọn ngôn ngữ ở ô bên dưới rồi bấm Chạy tiếp.")
        job.data.pop("need_language", None)
        if u.policy_issues:
            total = sum(x.end - x.start for x in u.policy_issues)
            self.log(f"Phát hiện {len(u.policy_issues)} đoạn vi phạm chính sách TikTok (~{total:.0f}s) — sẽ cắt bỏ.")

    def step_confirm_genre(self, job: Job) -> None:
        u = self._understanding(job)
        job.wait(f"Xác nhận nội dung: {u.summary_vi} | Phong cách sẽ dùng: {self._style_name(job)}. "
                 "Sửa plan/understanding.json nếu cần rồi bấm Tiếp tục.")

    def step_segment(self, job: Job) -> None:
        from app.director.tasks import make_segments_long

        _, analysis, plan_dir = self._paths(job)
        u = self._understanding(job)
        path = plan_dir / "segments.json"
        if not job.picks_segments:  # review phim (11/10): MỘT video tóm gọn cả phim
            start, end = u.usable_range.start, u.usable_range.end
            if job.options.voice_only or job.data.get("montage_parts"):  # giữ trọn footage từ giây 0 tới hết
                start, end = 0.0, self._footage_size(job)[2] or end
            videos = [{"index": 1, "start": start, "end": end, "title_vi": "", "summary_vi": u.summary_vi}]
            if job.options.sell:  # bán content: 1–3 bản khác nhau từ CÙNG video (chủ dự án 17/10)
                n = max(1, min(int(job.options.sell_variants or 1), int(config.load("sell").get("max_variants", 3))))
                videos = [{**videos[0], "index": i, "title_vi": f"Bản {i}" if n > 1 else ""} for i in range(1, n + 1)]
            path.write_text(json.dumps({"videos": videos, "confirmed": True}, ensure_ascii=False, indent=2),
                            encoding="utf-8")
            job.data["videos"] = videos
            return
        if path.is_file() and json.loads(path.read_text(encoding="utf-8")).get("proposal"):
            self.log("Đã có kết quả chia video, dùng lại.")
            return
        if job.options.ideas:  # ý tưởng từ video dài: danh mục cảnh (một lần) → AI nghĩ ý tưởng → chủ dự án tick
            redo = job.data.get("ideas_redo") or {}
            return self._make_ideas(job, redo.get("feedback", ""), redo.get("previous"))
        if job.options.cliff:  # review bỏ lửng: chia CẢ phim thành các phần liền nhau (không bỏ cảnh)
            from app.director.cliff import make_parts_long

            res = make_parts_long(self.director, analysis, u, log=self.log)
            videos = res["videos"]
            data = {"proposal": {"videos": videos, "dropped": [], "editor_notes": res["editor_notes"],
                                 "narrator_vi": res["narrator_vi"]}, "videos": videos, "confirmed": False}
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            job.data["videos"] = videos
            job.data["cliff_narrator"] = res["narrator_vi"]
            self.log(f"Đạo diễn chia phim thành {len(videos)} phần liền nhau (kể hết, không bỏ cảnh)"
                     + (f", nhân vật chính: {res['narrator_vi']}" if res["narrator_vi"] else "") + ".")
            return
        sp = make_segments_long(self.director, analysis, u, review=job.options.review,
                                highlight=job.options.char_dub, log=self.log)
        videos = [{"index": i, "start": v.start, "end": v.end, "title_vi": v.title_vi, "summary_vi": v.summary_vi,
                   "why_vi": v.why_vi, **({"moments": [m.model_dump() for m in v.moments]} if v.moments else {})}
                  for i, v in enumerate(sorted(sp.videos, key=lambda v: v.start), 1)]
        data = {"proposal": sp.model_dump(), "videos": videos, "confirmed": False}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        job.data["videos"] = videos
        self.log(f"Đạo diễn chia thành {len(videos)} video, bỏ {len(sp.dropped)} đoạn.")

    def step_review_segments(self, job: Job) -> None:
        _, _, plan_dir = self._paths(job)
        data = json.loads((plan_dir / "segments.json").read_text(encoding="utf-8"))
        if not data.get("confirmed") and data.get("ideas"):
            n = len((data.get("proposal") or {}).get("ideas", []))
            job.wait(f"Chọn ý tưởng muốn làm: AI đề xuất {n} ý tưởng. Tick các ý tưởng muốn dựng (mỗi ý tưởng một short) "
                     "rồi bấm Xác nhận — hoặc góp ý để AI nghĩ lại.")
            return
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
        path = plan_dir / "segments.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        # tình huống ngắn (lồng tiếng nhân vật): giữ các tình huống AI chọn nằm trong điểm cắt mới
        pool = {(m["start"], m["end"]): m for v in (data.get("proposal") or {}).get("videos", []) + data.get("videos", [])
                for m in v.get("moments") or []}

        def moments_in(r: dict) -> list[dict]:
            a, b = float(r["start"]), float(r["end"])
            src = r["moments"] if r.get("moments") is not None else sorted(pool.values(), key=lambda m: m["start"])
            return [m for m in src if m["start"] >= a - 0.5 and m["end"] <= b + 0.5]

        videos = [{"index": i, "start": float(r["start"]), "end": float(r["end"]), "title_vi": r.get("title_vi", ""),
                   "summary_vi": r.get("summary_vi", ""), **({"moments": ms} if (ms := moments_in(r)) else {})}
                  for i, r in enumerate(rows, 1)]
        if job.options.cliff:  # review bỏ lửng: giữ short mở đầu + chỗ bỏ lửng của từng phần
            videos = self._cliff_rows(rows, videos, data)
        changed = data.get("videos") != videos or not data.get("confirmed")
        data.update({"videos": videos, "confirmed": True})
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        job.data["videos"] = videos
        if changed:  # chia khác đi → hook / kế hoạch cũ không còn đúng
            hook_io.hooks_path(d).unlink(missing_ok=True)
            self._clear_plans(d, plan_dir)
        job.save(self.jobs_root)

    # ---------- Ý tưởng từ video dài (chủ dự án yêu cầu 17/10) ----------

    def _make_ideas(self, job: Job, feedback: str = "", previous: list[dict] | None = None) -> None:
        from app.director.ideas import make_catalog, make_ideas, save_proposal

        _, analysis, plan_dir = self._paths(job)
        plan_dir.mkdir(parents=True, exist_ok=True)
        u = self._understanding(job)
        cat = make_catalog(self.director, analysis, plan_dir, u, log=self.log)
        self.log(f"Danh mục cảnh: {len(cat.shots)} cảnh. AI nghĩ ý tưởng short…")
        lang = job.options.target_language or u.language
        keep, drop, notes = make_ideas(self.director, analysis, cat, u, brief=job.options.ideas_brief, language=lang,
                                       feedback=feedback, previous=previous)
        save_proposal(plan_dir, keep, drop, notes)
        job.data["videos"] = []
        job.data.pop("ideas_redo", None)
        self.log(f"AI đề xuất {len(keep)} ý tưởng" + (f", bỏ {len(drop)} ý tưởng thiếu cảnh" if drop else "") + ".")

    def apply_ideas(self, job: Job, picks: list[int]) -> None:
        """Chủ dự án tick ý tưởng (số thứ tự trong đề xuất, từ 1) → mỗi ý tưởng một video. Đổi lựa chọn → kịch bản / voice
        cũ không còn đúng (voice cất thành *_cu)."""
        from app.director.ideas import idea_videos
        from app.director.tasks import load_analysis

        d, analysis, plan_dir = self._paths(job)
        path = plan_dir / "segments.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        ideas = (data.get("proposal") or {}).get("ideas", [])
        chosen = [ideas[k - 1] for k in sorted(set(picks)) if 1 <= k <= len(ideas)]
        if not chosen:
            raise ValueError("Cần tick ít nhất một ý tưởng.")
        videos = idea_videos(chosen, float(load_analysis(analysis)["scenes"]["duration"]))
        changed = data.get("videos") != videos or not data.get("confirmed")
        data.update({"videos": videos, "confirmed": True, "picked": sorted(set(picks))})
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        job.data["videos"] = videos
        if changed:
            self._clear_plans(d, plan_dir)
            for f in [*plan_dir.glob("sell_video*.json"), *plan_dir.glob("dub_video*.json")]:
                f.unlink()
            for old in (d / "voice").glob("video*_dub*.*"):
                if "_cu" not in old.stem:
                    old.replace(old.with_name(f"{old.stem}_cu{old.suffix}"))
            job.data.pop("ready_drafts", None)
        job.save(self.jobs_root)

    def redo_ideas(self, job: Job, feedback: str) -> None:
        """Nút "💡 Nghĩ lại ý tưởng": AI nghĩ ý tưởng mới theo góp ý (danh mục cảnh giữ nguyên, không xem lại video)."""
        _, _, plan_dir = self._paths(job)
        path = plan_dir / "segments.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        job.data["ideas_redo"] = {"feedback": feedback.strip(),
                                  "previous": (data.get("proposal") or {}).get("ideas", [])}
        job.data.setdefault("ideas_feedback", []).append(feedback.strip())
        path.unlink(missing_ok=True)
        job.data.pop("videos", None)
        job.step, job.status = "segment", Status.pending
        job._log("người dùng góp ý — AI nghĩ lại ý tưởng")
        job.save(self.jobs_root)

    # ---------- Content nhiều phim từ bài TikTok ảnh (chủ dự án yêu cầu 14/10) ----------

    POST_EXT = (".jpg", ".jpeg", ".png", ".webp")

    def post_images(self, job: Job) -> list[Path]:
        d, _, _ = self._paths(job)
        return sorted(p for p in (d / "post").glob("*") if p.suffix.lower() in self.POST_EXT)

    def _post_info(self, job: Job) -> dict:
        d, _, _ = self._paths(job)
        try:
            return json.loads((d / "post" / "post.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def save_post(self, job: Job, title: str | None = None, no_images: bool | None = None) -> None:
        d, _, _ = self._paths(job)
        info = self._post_info(job)
        if title is not None and title.strip():
            info["title"] = title.strip()
        if no_images is not None:
            info["no_images"] = bool(no_images)
        (d / "post").mkdir(parents=True, exist_ok=True)
        (d / "post" / "post.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    def _films_idea(self, job: Job):
        from app.director.schemas import FilmsIdea

        _, _, plan_dir = self._paths(job)
        return FilmsIdea.model_validate_json((plan_dir / "films_idea.json").read_text(encoding="utf-8"))

    def _films_picks(self, job: Job) -> dict[int, dict]:
        _, _, plan_dir = self._paths(job)
        try:
            raw = json.loads((plan_dir / "films_match.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {int(k): v for k, v in raw.items()}

    def step_post(self, job: Job) -> None:
        """Bài gốc: tiêu đề chủ dự án tự gõ (14/10: bỏ ô dán link) + ảnh chủ dự án tải lên."""
        info = self._post_info(job)
        images = self.post_images(job)
        if not images and not info.get("no_images"):
            job.wait("Tải lên các ẢNH của bài TikTok (lưu từng ảnh từ app / chụp màn hình). Không có ảnh thì tick "
                     "'Chỉ dùng tiêu đề' rồi bấm Chạy tiếp.")
        elif not images and not info.get("title"):
            job.wait("Chưa có ảnh lẫn tiêu đề — gõ tiêu đề / mô tả bài vào ô bên dưới.")
        else:
            self.log(f"Bài gốc: {len(images)} ảnh, tiêu đề: {(info.get('title') or '(không có)')[:80]}")

    def step_idea(self, job: Job) -> None:
        from app.director.films import load_cfg, make_idea

        _, _, plan_dir = self._paths(job)
        path = plan_dir / "films_idea.json"
        if not path.is_file():
            info = self._post_info(job)
            lang = job.options.target_language or "ko"
            tpl = self._template()
            self.log("AI xem bài gốc, nhận ra các phim và viết content mới…")
            idea = make_idea(self.director, self.post_images(job)[:int(load_cfg().get("max_post_images", 20))],
                             info.get("title", ""), lang, music_items=[m for m in tpl.library if m.kind == "music"],
                             uploader=info.get("uploader", ""))
            plan_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(idea.model_dump_json(indent=2), encoding="utf-8")
        idea = self._films_idea(job)
        job.data["videos"] = [{"index": 1, "start": 0.0, "end": 0.0, "title_vi": idea.topic_vi[:80],
                               "summary_vi": idea.story_vi}]
        self.log(f"Content mới: {len(idea.lines)} câu về {len(idea.films)} phim — "
                 + ", ".join(f"{f.key}: {f.title_vi}" for f in idea.films))

    def rewrite_films_idea(self, job: Job, feedback: str) -> None:
        """Nút "✍️ Viết lại theo góp ý" (vd "bỏ phim 3, thay bằng phim X"): AI viết lại content, các bước sau làm lại."""
        from app.director.films import make_idea

        if not feedback.strip():
            raise ValueError("Hãy gõ góp ý (vd: bỏ phim 3, giọng vui hơn, thêm dừng hình…).")
        d, _, plan_dir = self._paths(job)
        prev = self._films_idea(job)
        info = self._post_info(job)
        tpl = self._template()
        self.log("AI viết lại content theo góp ý của bạn…")
        idea = make_idea(self.director, self.post_images(job), info.get("title", ""),
                         job.options.target_language or "ko", music_items=[m for m in tpl.library if m.kind == "music"],
                         feedback=feedback, previous=prev, uploader=info.get("uploader", ""))
        (plan_dir / "films_idea.json").write_text(idea.model_dump_json(indent=2), encoding="utf-8")
        self._reset_films_after_idea(job)
        job.data.setdefault("films_feedback", []).append(feedback.strip())
        job.step, job.status = "idea", Status.pending
        job._log("người dùng góp ý — đã viết lại content")
        job.save(self.jobs_root)

    def _reset_films_after_idea(self, job: Job) -> None:
        """Content đổi → cảnh đã tìm + kịch bản voice cũ không còn đúng (voice cũ cất thành *_cu)."""
        from app.planner import dub_io

        d, _, plan_dir = self._paths(job)
        (plan_dir / "films_match.json").unlink(missing_ok=True)
        dub_io.dub_path(d, 1).unlink(missing_ok=True)
        for old in (d / "voice").glob("video01_dub*.*"):
            if "_cu" not in old.stem:
                old.replace(old.with_name(f"{old.stem}_cu{old.suffix}"))
        job.data.pop("ready_drafts", None)

    def set_films(self, job: Job, paths: dict[str, str]) -> list[str]:
        """Chủ dự án chọn file cho từng phim (mã phim → đường dẫn). Trả các mã có file sai."""
        films = dict(job.data.get("films") or {})
        bad = []
        for key, p in paths.items():
            p = str(p).strip().strip('"')
            if not p:
                continue
            if Path(p).is_file():
                films[key] = str(Path(p).resolve())
            else:
                bad.append(key)
        job.data["films"] = films
        job.save(self.jobs_root)
        return bad

    def step_films_wait(self, job: Job) -> None:
        import shutil

        idea = self._films_idea(job)
        have = job.data.get("films") or {}
        missing = [f for f in idea.films if not (have.get(f.key) and Path(have[f.key]).is_file())]
        if missing:
            job.wait("Chọn file cho từng phim (bảng bên dưới). Còn thiếu: "
                     + ", ".join(f"{f.key} = {f.title_vi}" for f in missing))
            return
        paths = [Path(have[f.key]).as_posix() for f in idea.films]
        if job.footage != paths:  # đổi / thêm phim → phân tích + tìm cảnh lại
            d, analysis, plan_dir = self._paths(job)
            if job.footage:
                shutil.rmtree(analysis, ignore_errors=True)
                (plan_dir / "films_match.json").unlink(missing_ok=True)
            job.footage = paths
        job.data["film_index"] = {f.key: k for k, f in enumerate(idea.films)}

    def step_match(self, job: Job) -> None:
        from app.director.films import make_match
        from app.jobs.parallel import run_parallel

        _, analysis, plan_dir = self._paths(job)
        path = plan_dir / "films_match.json"
        if path.is_file():
            return
        idea = self._films_idea(job)
        index = job.data.get("film_index") or {f.key: k for k, f in enumerate(idea.films)}
        lang = job.options.target_language or "ko"

        def one(film):
            lines = {n: ln for n, ln in enumerate(idea.lines, 1) if ln.film == film.key}
            self.log(f"AI tìm cảnh trong {film.title_vi} cho {len(lines)} câu…")
            r = make_match(self.director, analysis, index[film.key], film, lines, lang)
            return {p.line: {"film": film.key, "start": p.start, "end": p.end, "freeze_t": p.freeze_t, "why_vi": p.why_vi}
                    for p in r.picks}

        picks = {}
        for part in run_parallel(one, idea.films):
            picks.update(part)
        path.write_text(json.dumps({str(k): v for k, v in sorted(picks.items())}, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        self.log(f"Đã tìm cảnh cho {len(picks)}/{len(idea.lines)} câu.")

    def _films_dub(self, job: Job) -> None:
        from app.director.films import to_script
        from app.planner import dub_io

        d, _, _ = self._paths(job)
        if dub_io.load_dub(d, 1) is None:
            dub_io.dub_path(d, 1).write_text(to_script(self._films_idea(job), self._films_picks(job))
                                             .model_dump_json(indent=2), encoding="utf-8")
        s = dub_io.load_dub(d, 1)
        path = dub_io.write_dub_scripts(d, {1: s}, {1: []})
        self.log(f"Đã xuất {path} ({len(s.lines)} câu — đọc liền một mạch vào một file)")

    def _write_films(self, job: Job, v: dict, ctx: dict) -> tuple[dict, list]:
        from app.director.tasks import load_analysis
        from app.planner import dub_io
        from app.planner.films_build import build_films

        d, analysis = ctx["d"], ctx["analysis"]
        idea, picks = self._films_idea(job), self._films_picks(job)
        index = job.data.get("film_index") or {f.key: k for k, f in enumerate(idea.films)}
        films = {}
        for f in idea.films:
            a = load_analysis(analysis, index[f.key])
            sc = a["scenes"]
            films[f.key] = {"path": sc["path"], "width": sc["width"], "height": sc["height"],
                            "duration": sc["duration"], "scene_starts": [x["start"] for x in sc.get("scenes", [])]}
        voices = {}
        for n in range(1, len(idea.lines) + 1):
            fv = dub_io.find_line_voice(d, 1, n)
            if fv is not None:
                voices[n] = self._review_trimmed(d, fv)  # cắt sạch lặng đầu / cuối → nói liền mạch như review
        name = f"{job.options.client_id or 'khach'}_{job.job_id}_video01"
        res = build_films(idea, picks, films, ctx["tpl"], self._drafts_dir or drafts_root(), name,
                          language=job.options.target_language or "ko", voices=voices, stills_dir=d / "stills",
                          vi_subtitles=self.vi_subtitles(job), still_fn=getattr(self, "_still_fn", None),
                          keep_frame=job.data.get("default_ratio") == "source")
        out = res.writer.save(overwrite=True)
        dur = round(res.duration_us / 1_000_000, 1)
        for n in res.notes:
            self.log(f"[video 01] {n}")
        self.log(f"Đã ghi draft CapCut: {out} ({dur}s)")
        return ({"index": 1, "draft": str(out), "duration_s": dur, "missing_assets": len(res.missing_assets),
                 "start": 0.0, "end": 0.0, "short": False, "credits": self._credits(res.used_local)},
                res.missing_assets)

    # ---------- Review bỏ lửng (chủ dự án yêu cầu 14/10) ----------

    @staticmethod
    def _cliff_hook(v: dict) -> tuple[float, float] | None:
        """Short mở đầu (giây gốc) của một phần — chỉ nhận khi nằm trong phần."""
        h = v.get("hook") or {}
        try:
            a, b = float(h["start"]), float(h["end"])
        except (KeyError, TypeError, ValueError):
            return None
        return (a, b) if b > a and a >= float(v["start"]) - 0.5 and b <= float(v["end"]) + 0.5 else None

    def _cliff_hook_s(self, v: dict) -> float:
        h = self._cliff_hook(v)
        return round(h[1] - h[0], 2) if h else 0.0

    def _cliff_hook_subs(self, job: Job, v: dict) -> list[dict]:
        """Phụ đề cho short mở đầu (chủ dự án 14/10): lời thoại gốc trong short dịch sang ngôn ngữ đích. Lưu
        plan/hook_subs_videoNN.json; sửa giây của short / đổi ngôn ngữ thì dịch lại."""
        from app.director.cliff import make_hook_subs

        hook = self._cliff_hook(v)
        if hook is None:
            return []
        d, analysis, plan_dir = self._paths(job)
        u = self._u_for(job, v)
        path = plan_dir / f"hook_subs_video{v['index']:02d}.json"
        key = {"hook": [round(hook[0], 2), round(hook[1], 2)], "language": u.language}
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if {k: saved.get(k) for k in key} == key:
                return saved.get("lines") or []
        except (OSError, ValueError):
            pass
        lines = make_hook_subs(self.director, analysis, u, hook, video_index=v["index"])
        plan_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**key, "lines": lines}, ensure_ascii=False, indent=2), encoding="utf-8")
        if lines:
            self.log(f"Video {v['index']:02d}: phụ đề cho short mở đầu — {len(lines)} câu.")
        return lines

    def _cliff_info(self, job: Job, v: dict) -> dict:
        """Thông tin phần gửi AI viết lời: thứ tự phần, ngôi kể, người kể, phần cuối?, chỗ bỏ lửng, short, phần trước."""
        from app.director.cliff import load_cfg

        vids = self.videos(job)
        i = v["index"]
        pov = job.options.cliff_pov or str(load_cfg().get("default_pov", "3"))
        return {"index": i, "total": len(vids), "pov": "1" if pov == "1" else "3",
                "narrator": job.data.get("cliff_narrator", ""), "last": i == len(vids) or bool(v.get("last")),
                "cliff_vi": v.get("cliff_vi", ""), "hook": self._cliff_hook(v),
                "prev": [x.get("summary_vi", "") for x in vids if x["index"] < i]}

    def _cliff_rows(self, rows: list[dict], videos: list[dict], data: dict) -> list[dict]:
        """Bảng duyệt review bỏ lửng: giữ short mở đầu (sửa được giây trên bảng) + chỗ bỏ lửng của từng phần. Phần mới
        (người dùng thêm / dời điểm cắt) lấy theo phần đề xuất cũ chứa nó; short không còn nằm trong phần thì bỏ short."""
        pool = (data.get("proposal") or {}).get("videos") or data.get("videos") or []
        out = []
        for r, v in zip(rows, videos):
            a, b = v["start"], v["end"]
            mid = (a + b) / 2
            old = min(pool, key=lambda p: 0 if p["start"] <= mid <= p["end"] else
                      min(abs(p["start"] - mid), abs(p["end"] - mid)), default={})
            hook = old.get("hook")
            if r.get("hook_start") not in (None, "") and r.get("hook_end") not in (None, ""):
                hook = {**(hook or {}), "start": float(r["hook_start"]), "end": float(r["hook_end"])}
            nv = {**v, "cliff_vi": old.get("cliff_vi", ""), "last": False}
            if hook:
                nv["hook"] = hook
            if self._cliff_hook(nv) is None:
                nv.pop("hook", None)
                self.log(f"Phần {v['index']:02d}: short mở đầu không nằm trong {a:.1f}–{b:.1f}s — dựng không có short.")
            out.append(nv)
        if out:
            out[-1]["last"] = True
        for x, y in zip(out, out[1:]):
            if y["start"] - x["end"] > 1.0:
                self.log(f"⚠️ Bỏ trống {x['end']:.1f}–{y['start']:.1f}s phim giữa phần {x['index']} và {y['index']} "
                         "(bạn đã sửa) — đoạn đó sẽ không được kể.")
        return out

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
        from app.jobs.parallel import run_parallel
        from app.planner import hook_io

        d, analysis, plan_dir = self._paths(job)
        tpl = self._template()
        style_name = self._style_name(job)
        job.data["style_used"] = style_name
        self.log(f"Phong cách dựng: {style_name}")
        if job.options.sell:  # bán content: MỘT lượt hỏi AI ra cả kịch bản + cảnh + tiêu đề + nhạc
            for v in self.videos(job):
                if not (plan_dir / f"edit_plan_video{v['index']:02d}.json").is_file():
                    self._sell_script(job, v, tpl)
            return

        def one(v):  # mỗi video một lượt hỏi AI — nhiều video thì hỏi song song (app/jobs/parallel.py)
            i = v["index"]
            out = plan_dir / f"edit_plan_video{i:02d}.json"
            hook, hook_s = None, 0.0
            if job.use_hook:
                hook = self._hook_for(d, i)
                voice = hook_io.find_voice(d, i)
                hook_s = max(3.0, self._voice_duration(voice) / 1_000_000 + 0.2) if voice else \
                    (8.0 if hook and hook.intro.strip() else 4.0)
            elif job.options.cliff:  # review bỏ lửng: short mở đầu tính vào 1:30–2:00
                hook_s = self._cliff_hook_s(v)
            self.log(f"Lập kế hoạch dựng video {i:02d}…")
            music = [m for m in tpl.library if m.kind == "music"]
            choice = job.data.get("music_choice")
            chosen = [m for m in music if m.name == choice] if choice else []
            if choice and not chosen:
                self.log(f"Không thấy bài nhạc đã chọn '{choice}' trong kho — để AI tự chọn.")
            plan = self._make_plan_or_pending(
                plan_dir, i, make_plan, self.director, analysis, self._u_for(job, v), self._style(job, style_name),
                             hook=hook, hook_s=hook_s, video_index=i, moments=v.get("moments"),
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
            (plan_dir / f"pending_plan_video{i:02d}.json").unlink(missing_ok=True)

        run_parallel(one, [v for v in self.videos(job)
                           if not (plan_dir / f"edit_plan_video{v['index']:02d}.json").is_file()])

    @staticmethod
    def _make_plan_or_pending(plan_dir: Path, index: int, fn, *args, **kwargs):
        """Hỏi AI lập kế hoạch; AI sai 3 lần thì LƯU bản gần nhất (plan/pending_plan_videoNN.json) để chủ dự án chọn
        "Dùng bản này" trên trang lỗi (chủ dự án 14/10: "sai thì hỏi tôi có lấy không, lấy thì làm tiếp")."""
        from app.director.base import DirectorError

        try:
            return fn(*args, **kwargs)
        except DirectorError as exc:
            if exc.last is not None:
                (plan_dir / f"pending_plan_video{index:02d}.json").write_text(json.dumps(
                    {"plan": exc.last.model_dump(), "problems": exc.problems}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
            raise

    def accept_pending_plan(self, job: Job) -> int:
        """Chủ dự án bấm "Dùng bản này": lấy kế hoạch dựng gần nhất AI đã trả (còn lỗi), chạy tiếp, không hỏi lại AI."""
        from app.director.schemas import EditPlan

        _, _, plan_dir = self._paths(job)
        n = 0
        for p in sorted(plan_dir.glob("pending_plan_video*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            plan = EditPlan.model_validate(data["plan"])
            out = plan_dir / p.name.replace("pending_plan_", "edit_plan_")
            out.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
            p.unlink()
            self.log(f"{out.stem.replace('edit_plan_', '').replace('video', 'Video ')}: dùng kế hoạch dựng gần nhất, "
                     f"bỏ qua {len(data.get('problems', []))} lỗi.")
            n += 1
        if n and job.status in (Status.error, Status.stopped):
            job.status = Status.pending
            job._log("người dùng chọn dùng kế hoạch dựng gần nhất")
            job.save(self.jobs_root)
        return n

    def step_dub(self, job: Job) -> None:
        """Chế độ Đổi ngôn ngữ: viết câu thuyết minh (ngôn ngữ đích) theo các clip của kế hoạch dựng."""
        from app.director.base import DirectorError
        from app.director.schemas import EditPlan
        from app.director.tasks import make_dub
        from app.jobs.parallel import run_parallel
        from app.planner import dub_io

        if not self._dubbing(job):
            return
        if job.options.films:  # content nhiều phim: bài đọc AI đã viết + cảnh đã tìm → kịch bản voice
            return self._films_dub(job)
        d, analysis, plan_dir = self._paths(job)

        if job.options.char_dub and any(dub_io.load_dub(d, v["index"]) is None for v in self.videos(job)):
            # bắt lời thoại gốc đầy đủ hơn trước khi dịch — chỉ trên các tình huống đã duyệt (nhanh)
            self._vocals_transcript(job, analysis, self._understanding(job).source_language)

        def one(v):  # mỗi video một lượt hỏi AI — nhiều video thì hỏi song song (app/jobs/parallel.py)
            i = v["index"]
            s = dub_io.load_dub(d, i)
            if s is None and job.options.sell:  # bán content: kịch bản viết cùng lượt với cảnh (bước plan)
                return self._sell_script(job, v)
            if s is None:
                self.log(f"Viết lời thuyết minh video {i:02d}…")
                plan = EditPlan.model_validate_json((plan_dir / f"edit_plan_video{i:02d}.json").read_text(encoding="utf-8"))
                hook = self._hook_for(d, i) if job.use_hook else None
                try:
                    s = make_dub(self.director, analysis, self._u_for(job, v), plan, hook=hook, video_index=i,
                                 mode="review" if job.options.review else "char" if job.options.char_dub
                                 else self.script_mode(job), review_s=job.options.review_s,
                                 voice_info=self._voice_info(job, analysis, plan, i) if job.options.char_dub else None,
                                 **({"cliff": self._cliff_info(job, v), "hook_s": self._cliff_hook_s(v)}
                                    if job.options.cliff else {}))
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
            if job.options.cliff:  # phụ đề cho short mở đầu — dịch sẵn cùng lúc viết lời
                self._cliff_hook_subs(job, v)
            return s

        vids = self.videos(job)
        scripts = dict(zip((v["index"] for v in vids), run_parallel(one, vids)))
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
        if job.options.review or job.options.films or job.options.sell:  # hình chạy theo giọng → không có câu "tràn"
            return {}
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

    # ---------- giọng AI bằng OmniVoice (tùy chọn, chủ dự án yêu cầu 11/10) ----------

    def tts_voices(self, job: Job) -> dict[str, dict]:
        """Giọng từng nhân vật: đã lưu trong job.data.tts.voices, chưa có thì theo đề xuất `cast` của AI."""
        from app.tts.voices import default_voices

        return default_voices(self._dub_scripts(job), (job.data.get("tts") or {}).get("voices"))

    def save_tts_voices(self, job: Job, voices: dict[str, dict], clone_ok: bool) -> None:
        tts = job.data.setdefault("tts", {})
        old = tts.get("voices") or {}
        out = {}
        for k, v in voices.items():
            mode = v.get("mode") if v.get("mode") in ("auto", "design", "clone", "upload") else "auto"
            item = {"mode": mode, "instruct": (v.get("instruct") or "").strip(), "note_vi": v.get("note_vi", "")}
            # giọng mẫu tải lên: file mới (nếu có) hoặc giữ file đã tải lần trước — khỏi phải tải lại
            sample = v.get("sample") or (old.get(k) or {}).get("sample")
            if sample:
                item["sample"] = sample
                item["ref_text"] = (v.get("ref_text") if v.get("sample") else
                                    v.get("ref_text") or (old.get(k) or {}).get("ref_text") or "").strip()
            out[k] = item
        tts["voices"] = out
        tts["clone_ok"] = bool(clone_ok)
        job.save(self.jobs_root)

    @staticmethod
    def _tts_fit(job: Job, cfg: dict) -> bool:
        """Đọc vừa khít thời lượng câu gốc? Review phim: KHÔNG — hình được dựng theo giọng đọc (build_from_voice), giọng
        phải nói tốc độ tự nhiên (chủ dự án 09/10: "đọc 2 giây mà ghi 4 giây")."""
        return (bool(cfg.get("fit_duration", True)) and not job.options.review and not job.options.films
                and not job.options.sell)

    def tts_generate(self, job: Job, video_index: int | None = None, only_missing: bool = True) -> int:
        """🤖 Cho OmniVoice đọc thoại: tạo voice/videoNN_dubMM.wav cho các câu (mặc định câu còn thiếu voice), mỗi nhân
        vật một giọng, đọc vừa thời lượng câu gốc. Trả số câu đã tạo; xong thì job chạy tiếp như khi tự thu đủ voice."""
        from app.planner import dub_io
        from app.tts import voices as ov

        cfg = ov.load_cfg()  # config/tts.yaml + python / model chọn trên giao diện
        d, analysis, _ = self._paths(job)
        scripts = self._dub_scripts(job)
        vids = [v for v in self.videos(job) if v["index"] in scripts and (video_index is None or v["index"] == video_index)]
        voices = self.tts_voices(job)
        clone_ok = bool((job.data.get("tts") or {}).get("clone_ok"))
        items, used = [], set()
        for v in vids:
            i, script = v["index"], scripts[v["index"]]
            only = ({n for n in range(1, len(script.lines) + 1) if not dub_io.find_line_voice(d, i, n)}
                    if only_missing else None)
            lang = (job.options.target_language or "ko") if job.options.films else self._u_for(job, v).language
            got = ov.build_items(script, i, d / "voice", lang, dub_io.windows_for(d, i, script),
                                 self._tts_fit(job, cfg), only)
            from app.director.tasks import wrong_language

            skipped = [it for it in got if wrong_language(it["text"], lang)]  # câu còn tiếng gốc → không đọc nhầm ngôn ngữ
            if skipped:
                self.log(f"⚠️ Video {i:02d}: {len(skipped)} câu chưa được dịch sang ngôn ngữ đích ({lang}) — OmniVoice KHÔNG "
                         "đọc các câu này; bấm 'AI viết lại thuyết minh' hoặc sửa câu rồi đọc lại: "
                         + ", ".join(Path(it["out"]).stem.split("_dub")[-1] for it in skipped[:10]))
                got = [it for it in got if it not in skipped]
            items += got
            used |= {it["voice"] for it in got}
        if not items:
            self.log("OmniVoice: không còn câu nào thiếu voice.")
            return 0
        req_voices = {}
        audio_src = None
        for name in sorted(used):
            v = dict(voices.get(name) or {"mode": "auto"})
            if v.get("mode") == "upload":  # giọng mẫu chủ dự án tải lên (11/10)
                sample = Path(v.get("sample") or "")
                if not clone_ok:
                    self.log(f"🎤 {name}: chưa tick xác nhận quyền dùng giọng — không dùng giọng mẫu, dùng giọng mô tả / tự chọn.")
                    v["mode"] = "design" if v.get("instruct") else "auto"
                elif not sample.is_file():
                    self.log(f"🎤 {name}: chưa có file giọng mẫu — dùng giọng mô tả / tự chọn.")
                    v["mode"] = "design" if v.get("instruct") else "auto"
                else:
                    ref, cut = ov.prepare_sample(sample, d / "voice" / "refs" / f"mau_{ov.safe_name(name)}.wav",
                                                 float(cfg.get("max_ref_s", 10.0)))
                    v.update({"mode": "clone", "ref_audio": str(ref),
                              "ref_text": "" if cut else (v.get("ref_text") or "")})
                    self.log(f"🎤 {name}: clone từ giọng mẫu bạn tải lên ({sample.name})"
                             + (f" — file dài, lấy {float(cfg.get('max_ref_s', 10.0)):.0f} giây đầu." if cut else "."))
            if v.get("mode") == "clone" and not v.get("ref_audio"):
                if not clone_ok:
                    self.log(f"🎭 {name}: chưa tick xác nhận quyền dùng giọng — không clone, dùng giọng mô tả / tự chọn.")
                    v["mode"] = "design" if v.get("instruct") else "auto"
                else:
                    if audio_src is None:  # giọng nói sạch (Demucs) làm mẫu; chưa tách được thì dùng âm thanh đã lọc ồn
                        self._bgm(job, analysis)
                        voc = analysis / "audio" / "vocals_00.wav"
                        audio_src = voc if voc.is_file() else analysis / "audio" / "clean_00.wav"
                    lines = [ln for s in scripts.values() for ln in s.lines]
                    tagged = [(ln, g) for vi, s in scripts.items()  # chỉ lấy mẫu từ nhóm giọng chính của nhân vật
                              for ln, g in zip(s.lines, dub_io.voice_groups(d, vi, len(s.lines)) or [None] * len(s.lines))
                              if ov.voice_key(ln) == name]
                    gs = [g["group"] for _, g in tagged if g]
                    if gs:
                        main = max(set(gs), key=gs.count)
                        lines = [ln for ln, g in tagged if g and g["group"] == main] or lines
                    span = ov.pick_reference(lines, name, float(cfg.get("min_ref_s", 3.0)), float(cfg.get("max_ref_s", 10.0)))
                    if span is None or not audio_src.is_file():
                        self.log(f"🎭 {name}: không tìm được đoạn giọng gốc để clone — dùng giọng mô tả / tự chọn.")
                        v["mode"] = "design" if v.get("instruct") else "auto"
                    else:
                        ref = ov.cut_reference(audio_src, span[0], span[1], d / "voice" / "refs" / f"{ov.safe_name(name)}.wav")
                        from app.director.tasks import load_analysis

                        segs = load_analysis(analysis)["transcript"].get("segments", [])
                        v.update({"ref_audio": str(ref), "ref_text": ov.ref_text(segs, *span)})
                        self.log(f"🎭 {name}: clone từ giọng gốc {span[0]:.1f}–{span[1]:.1f}s.")
            req_voices[name] = v
        request = {"model": cfg.get("model", "k2-fsa/OmniVoice"), "device": str(cfg.get("device", "auto")),
                   "num_step": int(cfg.get("num_step", 32)), "voices": req_voices, "items": items}
        gen = (job.data.get("tts") or {}).get("gen")
        if gen:  # thông số Voice Studio (tốc độ, seed…) — bán content dùng giọng thư viện
            request["gen"] = dict(gen)
        self.log(f"🤖 OmniVoice đọc {len(items)} câu ({len(used)} giọng)… lần đầu tải model có thể lâu.")
        run = getattr(self, "_tts_run", None) or ov.run_worker
        from app.jobs.limits import group_slot

        def on_line(line: str) -> None:
            if line.startswith(("PROGRESS", "INFO", "ERROR")):
                self.log(f"OmniVoice: {line.split(' ', 1)[-1]}")

        with group_slot("gpu", on_wait=lambda what: self.log(f"Đang đợi lượt {what} để chạy OmniVoice…")):
            run(request, d / "voice" / "tts_request.json", cfg, on_line)
        job.data.setdefault("tts", {})["last"] = {"items": len(items), "video": video_index}
        job.data.pop("dub_skip", None)
        if job.step == "dub_voice":
            job.status = Status.pending
        job.save(self.jobs_root)
        self.log(f"✅ OmniVoice đã đọc xong {len(items)} câu — tool dựng tiếp.")
        return len(items)

    def _sell_script(self, job: Job, v: dict, tpl=None, *, feedback: str = "", previous=None):
        """Bán content: AI viết kịch bản + chọn cảnh + tiêu đề + nhạc (một lượt) → lưu kế hoạch dựng + kịch bản voice."""
        from app.director.sell import make_sell_script, sell_plan, sell_to_dub
        from app.planner import dub_io

        d, analysis, plan_dir = self._paths(job)
        tpl = tpl or self._template()
        music = [m for m in tpl.library if m.kind == "music"]
        local = [m for m in music if m.material.get("local")]
        if local:  # nhạc file trên máy → chép được vào dự án CapCut (nhạc thư viện CapCut chỉ tham chiếu)
            music = local
        else:
            self.log("Kho assets/ chưa có nhạc file — dùng nhạc thư viện CapCut (không chép vào dự án được; CapCut tự "
                     "tải khi mở). Muốn đóng gói đủ nhạc: thả file nhạc vào assets\\music.")
        choice = job.data.get("music_choice")
        chosen = [m for m in tpl.library if m.kind == "music" and m.name == choice] if choice else []
        i = v["index"]
        self.log(f"AI viết kịch bản bán content + chọn cảnh video {i:02d}…")
        from app.director.schemas import SellScript

        n_var = len(self.videos(job))
        others = []
        for k in range(1, n_var + 1):  # các bản khác đã viết → bản này phải khác hẳn
            f = plan_dir / f"sell_video{k:02d}.json"
            if k != i and f.is_file():
                try:
                    others.append(SellScript.model_validate_json(f.read_text(encoding="utf-8")))
                except ValueError:
                    pass
        ideas = job.options.ideas
        library = self._library_for(job, v, analysis)
        if library:
            self.log(f"Kho cảnh chung: {len(library)} cảnh cùng khung AI được bù khi video gốc thiếu cảnh khớp lời.")
        r = make_sell_script(self.director, analysis, self._u_for(job, v),
                             brief=job.options.ideas_brief if ideas else job.options.sell_brief,
                             sell_s=job.options.sell_s, music_items=chosen or music, video_index=i,
                             feedback=feedback, previous=previous, variant=(1, 1) if ideas else (i, n_var),
                             others=others, idea=v if ideas else None, library=library)
        ratio = job.data.get("default_ratio")
        plan = sell_plan(r, ratio if ratio in ("16:9", "4:3", "1:1") else "16:9")
        if chosen:
            plan = plan.model_copy(update={"music": plan.music.model_copy(update={"name": chosen[0].name})})
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / f"edit_plan_video{i:02d}.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        (plan_dir / f"sell_video{i:02d}.json").write_text(r.model_dump_json(indent=2), encoding="utf-8")
        script = sell_to_dub(r)
        dub_io.dub_path(d, i).write_text(script.model_dump_json(indent=2), encoding="utf-8")
        dub_io.pending_path(d, i).unlink(missing_ok=True)
        return script

    def _sell_auto_voice(self, job: Job) -> bool:
        """Bán content (chủ dự án 17/10): giọng chọn sẵn trong thư viện Voice Studio → OmniVoice tự đọc các câu còn thiếu
        (giọng mẫu thì clone — chỉ khi giọng đó đã được xác nhận quyền; giọng mô tả thì đọc theo mô tả), dùng thông số
        mặc định của Voice Studio. Trả True nếu đã đọc được câu nào. Lỗi → ghi nhật ký, chuyển sang chờ bạn thu tay."""
        from app.tts import studio
        from app.tts.voices import NARRATOR

        v = studio.get_voice(job.options.sell_voice)
        if v is None:
            job.data["auto_tts_error"] = "không thấy giọng"
            self.log(f"⚠️ Không thấy giọng '{job.options.sell_voice}' trong thư viện Voice Studio — chờ bạn thu voice.")
            return False
        if v.get("mode") == "clone" and v.get("sample_path"):
            if not v.get("consent"):
                job.data["auto_tts_error"] = "chưa xác nhận quyền"
                self.log(f"⚠️ Giọng '{v['name']}' chưa được xác nhận quyền dùng — không clone, chờ bạn thu voice.")
                return False
            params = studio.load_params()
            spec = {"mode": "clone", "ref_audio": v["sample_path"], "ref_text": v.get("ref_text") or "",
                    "preprocess_prompt": bool(params.get("preprocess_prompt", True)),
                    "prompt_cache": str(Path(v["sample_path"]).parent / (
                        "prompt.pt" if params.get("preprocess_prompt", True) else "prompt_raw.pt"))}
        else:
            spec = {"mode": "design", "instruct": v.get("instruct", "")}
        tts = job.data.setdefault("tts", {})
        tts["voices"] = {NARRATOR: spec}
        tts["gen"] = {k: val for k, val in studio.load_params().items() if k in studio.WORKER_KEYS}
        self.log(f"🎙️ Giọng Voice Studio '{v['name']}' — OmniVoice tự đọc cả bài…")
        try:
            return self.tts_generate(job) > 0
        except Exception as exc:
            job.data["auto_tts_error"] = str(exc)
            job.save(self.jobs_root)
            self.log(f"⚠️ OmniVoice không đọc được ({exc}) — chờ bạn thu voice hoặc bấm 🤖 Cho OmniVoice đọc.")
            return False

    def sell_short_voice(self, job: Job) -> dict[int, dict]:
        from app.director.sell import short_voice

        d, _, _ = self._paths(job)
        return short_voice(d, self._dub_scripts(job), job.options.sell_s)

    def sell_lengthen(self, job: Job, video_index: int) -> None:
        """Nút "📏 Viết dài thêm cho đủ thời lượng": lưu tốc độ đọc THẬT của giọng vừa thu (để AI tính đúng số chữ), rồi
        AI viết lại cả bài dài hơn (giữ ý cũ, thêm chi tiết thật) — voice cũ cất *_cu, chờ đọc lại."""
        from app.planner import dub_io

        info = self.sell_short_voice(job).get(video_index)
        d, _, _ = self._paths(job)
        script = self._dub_scripts(job).get(video_index)
        rate = (info or {}).get("rate") or (dub_io.voice_rate(d, video_index, script, min_lines=1) if script else None)
        if rate:
            u = self._u_for(job, next(x for x in self.videos(job) if x["index"] == video_index))
            saved = dub_io.remember_voice_rate(u.language, rate, "sell_voice_cps")
            self.log(f"Giọng bạn đọc ~{rate:.1f} chữ/giây — đã lưu {saved:.1f} để AI viết đủ chữ cho video.")
        fb = ("Bài đọc thật " + (f"chỉ dài {info['voice_s']:.0f} giây, video cần ~{info['target_s']:.0f} giây" if info
                                  else "còn ngắn so với video")
              + (f" (giọng đọc ~{rate:.1f} chữ/giây → cần viết THÊM khoảng {info['extra_chars']} chữ)" if info and rate
                 else "")
              + ". Viết DÀI HƠN cho voice phủ kín video: giữ các ý hay của bản trước, thêm ý / chi tiết THẬT có trong "
                "video (phụ đề trên hình, điều thấy trong cảnh), không lặp ý, không bịa.")
        job.data.pop("sell_accept_short", None)
        self.rewrite_review(job, video_index, fb)

    def rewrite_review(self, job: Job, video_index: int, feedback: str) -> None:
        """Review phim — nút "✍️ Viết lại theo góp ý": AI viết lại bài lời đọc của một video theo đúng góp ý của chủ dự
        án (kèm bản trước), voice cũ của video đó cất thành *_cu, job quay về chờ đọc lại cả bài."""
        from app.director.tasks import make_review_script
        from app.planner import dub_io

        if not feedback.strip():
            raise ValueError("Hãy gõ góp ý (vd: câu cứng quá, nói tự nhiên như kể với bạn bè, thêm chỗ hài…).")
        d, analysis, _ = self._paths(job)
        scripts = self._dub_scripts(job)
        v = next(x for x in self.videos(job) if x["index"] == video_index)
        u = self._u_for(job, v)
        self.log(f"Video {video_index:02d}: AI viết lại bài lời đọc theo góp ý của bạn…")
        if job.options.sell:
            script = self._sell_script(job, v, feedback=feedback, previous=scripts.get(video_index))
        else:
            script = make_review_script(self.director, analysis, u, video_index=video_index, feedback=feedback,
                                        previous=scripts.get(video_index), review_s=job.options.review_s,
                                        **({"cliff": self._cliff_info(job, v), "hook_s": self._cliff_hook_s(v)}
                                           if job.options.cliff else {}))
            dub_io.dub_path(d, video_index).write_text(script.model_dump_json(indent=2), encoding="utf-8")
        scripts[video_index] = script
        for old in (d / "voice").glob(f"video{video_index:02d}_dub*.*"):
            if "_cu" not in old.stem:
                old.replace(old.with_name(f"{old.stem}_cu{old.suffix}"))
        dub_io.write_dub_scripts(d, scripts, {i: dub_io.windows_for(d, i, s) for i, s in scripts.items()})
        job.data.setdefault("review_feedback", []).append({"video": video_index, "feedback": feedback.strip()})
        job.data.pop("dub_skip", None)
        job.step = "dub_voice"
        job.status = Status.pending
        job.save(self.jobs_root)
        self.log(f"Video {video_index:02d}: đã có bài lời đọc mới ({len(script.lines)} câu) — đọc lại cả bài rồi tải lên.")

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
        if missing and job.options.sell and job.options.sell_voice and not job.data.get("auto_tts_error"):
            if self._sell_auto_voice(job):  # OmniVoice đã đọc → bước này chạy lại để kiểm tra
                return
            missing = dub_io.missing_lines(d, self._dub_scripts(job))
        if missing:
            try:
                self.write_ready_videos(job)  # voice đến đâu ghi CapCut đến đấy
            except RuntimeError as exc:  # CapCut đang mở → vẫn chờ voice, báo rõ thay vì làm job lỗi
                self.log(f"⚠️ Chưa ghi được video đủ voice vào CapCut: {exc}")
            job.wait(f"Thu voice thuyết minh theo kịch bản bên dưới rồi tải lên. Còn thiếu {len(missing)} file: "
                     + ", ".join(missing[:8]) + (" …" if len(missing) > 8 else ""))
            return
        if job.options.sell and not job.data.get("sell_accept_short"):  # chủ dự án 15/10: voice phải phủ kín video
            short = self.sell_short_voice(job)
            if short and job.options.sell_voice and not job.data.get("auto_lengthened"):
                # giọng AI tự đọc → tự viết dài thêm MỘT lần (lưu tốc độ thật), đọc lại; vẫn ngắn thì mới hỏi bạn
                job.data["auto_lengthened"] = True
                self.log("Voice AI đọc ngắn hơn video — tự viết dài thêm theo đúng tốc độ giọng rồi đọc lại (một lần).")
                for i in short:
                    self.sell_lengthen(job, i)
                return
            if short:
                job.wait("⚠️ Voice chưa đủ dài: " + "; ".join(
                    f"video {i:02d} đọc {x['voice_s']:.0f}s, cần ≥ {x['need_s']:.0f}s" for i, x in short.items())
                    + " — bấm '📏 Viết dài thêm cho đủ thời lượng' (AI viết lại theo đúng tốc độ giọng bạn) rồi đọc lại, "
                    "hoặc 'Vẫn dựng với voice này' (phần thiếu chỉ có hình + nhạc).")

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

    def _vocals_transcript(self, job: Job, analysis: Path, language: str | None) -> None:
        """Lồng tiếng nhân vật (chủ dự án 11/10: "nhiều khi không bắt được tiếng gốc"): nhận dạng LẠI lời thoại trên phần
        giọng nói Demucs đã tách khỏi nhạc, bộ lọc giọng nói nhạy hơn (config/char_dub.yaml → whisper_options) — CHỈ trên
        các tình huống đã duyệt (file giọng nói nối liền, ngắn → nhanh). Câu mới thay câu cũ trong các đoạn đó; lời thoại
        cũ cất ở analysis/transcript_mix.json. Không tách được giọng / lỗi → giữ lời thoại cũ, ghi lý do."""
        from app.analysis.separate import to_source_time

        ccfg = config.load("char_dub")
        sig = json.dumps(self._bgm_ranges(job))
        if job.data.get("vocals_transcript") == sig or not ccfg.get("vocals_transcribe", True):
            return
        if self._bgm(job, analysis) is None:
            return
        concat = analysis / "audio" / "vocals_concat.wav"
        layout = job.data.get("bgm_layout") or []
        if not concat.is_file() or not layout:
            self.log("Chưa có phần giọng nói tách riêng — giữ lời thoại đã nhận dạng.")
            return
        from app.jobs.limits import group_slot

        try:
            with group_slot("gpu", on_wait=lambda what: self.log(f"Đang đợi lượt {what} để nhận dạng lại thoại…")):
                self.log("Nhận dạng lại lời thoại trên giọng nói đã tách nhạc (bắt câu ngắn / câu nói chen nhạc)…")
                tr = self._transcribe(concat, ccfg.get("whisper_options") or {}, language)
        except Exception as exc:
            self.log(f"Không nhận dạng lại được lời thoại — giữ bản cũ. Lý do: {exc}")
            return
        new_segs = []
        for sg in tr.segments:  # giây trong file nối → giây gốc của video
            a, b = to_source_time(sg.start, layout), to_source_time(sg.end, layout)
            if a is None and b is None:
                continue
            a = b - (sg.end - sg.start) if a is None else a
            b = a + (sg.end - sg.start) if b is None else b
            words = [w.model_copy(update={"start": ws, "end": we}) for w in sg.words
                     if (ws := to_source_time(w.start, layout)) is not None and (we := to_source_time(w.end, layout))
                     is not None]
            new_segs.append({**sg.model_dump(), "start": a, "end": b, "words": [w.model_dump() for w in words]})
        if ccfg.get("rescue_gaps", True):  # chủ dự án 11/10 "cứ bắt sót câu": nghe lại chỗ có tiếng người mà chưa có câu
            try:
                extra = self._rescue_gaps(concat, [(sg.start, sg.end) for sg in tr.segments], layout, language, ccfg)
            except Exception as exc:
                self.log(f"Bỏ qua bước nghe lại chỗ sót câu: {exc}")
                extra = []
            if extra:
                self.log(f"Nghe lại chỗ sót: thêm {len(extra)} câu Whisper bỏ lỡ ("
                         + ", ".join(f"{x['start']:.1f}s" for x in extra[:6]) + ("…" if len(extra) > 6 else "") + ").")
                new_segs = sorted(new_segs + extra, key=lambda x: x["start"])
        path = analysis / "transcript.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        backup = analysis / "transcript_mix.json"
        if not backup.is_file():
            backup.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        entry = next((t for t in data if t.get("footage", 0) == 0), None)
        if entry is None:
            entry = {"footage": 0, "language": tr.language, "segments": []}
            data.insert(0, entry)
        inside = lambda sg: any(x["start"] <= (sg["start"] + sg["end"]) / 2 <= x["end"] for x in layout)  # noqa: E731
        old = [sg for sg in entry.get("segments") or [] if inside(sg)]
        entry["segments"] = sorted([sg for sg in entry.get("segments") or [] if not inside(sg)] + new_segs,
                                   key=lambda sg: sg["start"])
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        job.data["vocals_transcript"] = sig
        self.log(f"Lời thoại gốc trong các tình huống: {len(old)} → {len(new_segs)} câu sau khi nhận dạng lại trên giọng "
                 "đã tách nhạc.")

    def _voice_info(self, job: Job, analysis: Path, plan, video_index: int) -> list | None:
        """Lồng tiếng nhân vật (chủ dự án 11/10: "giọng nhân vật nào phải chuẩn"): đo nhóm giọng từng câu thoại gốc trên
        giọng nói đã tách nhạc (app/analysis/speech_gaps.voice_groups) → gợi ý cho AI ghi tên nhân vật đúng, lưu
        plan/voice_groups_videoNN.json để trang voice hiện. Không có giọng tách riêng / lỗi → None (AI đoán như cũ)."""
        from app.analysis import speech_gaps as sg
        from app.director.tasks import load_analysis
        from app.planner.char_lines import source_lines

        ccfg = config.load("char_dub")
        concat = analysis / "audio" / "vocals_concat.wav"
        layout = job.data.get("bgm_layout") or []
        if not ccfg.get("voice_groups", True) or not concat.is_file() or not layout:
            return None
        try:
            src = source_lines(load_analysis(analysis)["transcript"].get("segments", []), plan.clips,
                               max_s=float(ccfg.get("max_line_s", 7.0)))
            spans = []
            for x in src:
                a, b = sg.to_concat_time(x["start"], layout), sg.to_concat_time(x["end"], layout)
                spans.append((a, b) if a is not None and b is not None and b > a else None)
            info = sg.voice_groups(sg.decode16k(concat), spans, threshold=float(ccfg.get("voice_group_threshold", 0.35)))
        except Exception as exc:
            self.log(f"Không đo được nhóm giọng — AI đoán nhân vật theo lời thoại + hình như cũ. Lý do: {exc}")
            return None
        _, _, plan_dir = self._paths(job)
        (plan_dir / f"voice_groups_video{video_index:02d}.json").write_text(json.dumps(
            [{"start": x["start"], "end": x["end"], **(v or {})} for x, v in zip(src, info)], ensure_ascii=False),
            encoding="utf-8")
        groups = sorted({v["group"] for v in info if v}, key=lambda g: int(g[1:]))
        self.log(f"Video {video_index:02d}: máy đo được {len(groups)} nhóm giọng trên {len(src)} câu thoại "
                 f"({', '.join(groups[:8])}) — gửi AI để ghi đúng nhân vật.")
        return info

    def _rescue_gaps(self, concat: Path, covered: list[tuple[float, float]], layout: list[dict], language: str | None,
                     ccfg: dict) -> list[dict]:
        """Chỗ trên giọng nói đã tách nhạc CÓ tiếng người mà chưa câu nào phủ tới → ghép các chỗ đó (cách nhau 0.8 giây
        lặng) thành một file, nhận dạng KHÔNG qua bộ lọc giọng nói (VAD hay bỏ câu ngắn / nói nhỏ / nói chen) rồi đặt lại
        đúng giây gốc. Bỏ câu "bịa" quen thuộc của Whisper. Trả câu mới (giây gốc)."""
        import wave

        import numpy as np

        from app.analysis import speech_gaps as sg
        from app.analysis.separate import to_source_time

        x = sg.decode16k(concat)
        gaps = sg.uncovered_speech(sg.voiced_regions(x, rel_db=float(ccfg.get("rescue_rel_db", 28))), covered,
                                   min_s=float(ccfg.get("rescue_min_s", 0.45)))[: int(ccfg.get("rescue_max", 60))]
        if not gaps:
            return []
        gap_pad, sil = 0.15, np.zeros(int(0.8 * sg.SR), dtype=np.float32)
        parts, table, pos = [], [], 0.0
        for a, b in gaps:
            a2, b2 = max(0.0, a - gap_pad), min(len(x) / sg.SR, b + gap_pad)
            piece = x[int(a2 * sg.SR):int(b2 * sg.SR)]
            table.append((pos, pos + len(piece) / sg.SR, a2))
            parts += [piece, sil]
            pos += (len(piece) + len(sil)) / sg.SR
        out = concat.with_name("vocals_gaps.wav")
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sg.SR)
            w.writeframes((np.clip(np.concatenate(parts), -1, 1) * 32767).astype(np.int16).tobytes())
        tr = self._transcribe(out, {"vad_filter": False, "condition_on_previous_text": False, "batched": False}, language)

        def to_src(t: float) -> float | None:
            for r0, r1, c0 in table:
                if r0 - 0.05 <= t <= r1 + 0.05:
                    return to_source_time(c0 + min(max(t, r0), r1) - r0, layout)
            return None

        found = []
        for seg in tr.segments:
            if sg.is_hallucination(seg.text):
                continue
            a, b = to_src(seg.start), to_src(seg.end)
            if a is None or b is None or b - a < 0.2:
                continue
            words = [w.model_copy(update={"start": ws, "end": we}) for w in seg.words
                     if (ws := to_src(w.start)) is not None and (we := to_src(w.end)) is not None]
            found.append({**seg.model_dump(), "start": a, "end": b, "words": [w.model_dump() for w in words],
                          "rescued": True})
        return found

    def _transcribe(self, audio: Path, options: dict, language: str | None):
        from app.analysis.transcribe import transcribe

        return transcribe(audio, options=options, language=language, log=self.log)

    def _unvoiced_vocals(self, job: Job, analysis: Path, bgm: Path | None) -> Path | None:
        """Lồng tiếng nhân vật: giọng gốc Demucs tách ra, phát ở chỗ không có câu lồng tiếng (tiếng cười, hét…)."""
        if not (job.options.char_dub and bgm and config.load("char_dub").get("keep_unvoiced", True)):
            return None
        voc = analysis / "audio" / "vocals_00.wav"
        return voc.resolve() if voc.is_file() else None

    def _bgm_ranges(self, job: Job) -> list[list[float]]:
        """Lồng tiếng nhân vật: các đoạn cần tách nhạc = các tình huống đã duyệt (hoặc cả đoạn của video). Rỗng = cả video."""
        if not job.options.char_dub:
            return []
        out = []
        for v in job.data.get("videos") or []:
            ms = v.get("moments") or [{"start": v["start"], "end": v["end"]}]
            out += [[round(float(m["start"]), 2), round(float(m["end"]), 2)] for m in ms]
        return sorted(out)

    def _bgm(self, job: Job, analysis: Path) -> Path | None:
        """Nhạc nền gốc đã tách giọng nói (analysis/audio/bgm_00.wav, tách một lần; giọng nói ở vocals_00.wav).
        Lồng tiếng nhân vật: CHỈ tách ở các tình huống đã duyệt (chủ dự án 11/10: tách cả phim "lâu cực") — đổi tình
        huống thì tách lại. Không tách được → None (dùng nhạc AI chọn như thường) và ghi lý do vào nhật ký."""
        out = analysis / "audio" / "bgm_00.wav"
        ranges = self._bgm_ranges(job)
        sep_sig = f"{config.load('char_dub').get('demucs_model', '')}/{config.load('char_dub').get('demucs_shifts', '')}" \
            if job.options.char_dub else ""
        if out.is_file() and job.data.get("bgm_ranges", []) == ranges and job.data.get("bgm_model", "") == sep_sig:
            return out.resolve()
        from app.analysis.separate import separate_bgm, separate_ranges, torch_device
        from app.jobs.limits import group_slot

        bcfg = dict((config.load("dub").get("voice_only") or {}).get("keep_bgm") or {})
        if job.options.char_dub:  # lồng tiếng nhân vật: model tách kỹ hơn (chủ dự án 11/10 "bị lẫn giọng cũ")
            ccfg = config.load("char_dub")
            bcfg.update({k: v for k, v in (("model", ccfg.get("demucs_model")), ("shifts", ccfg.get("demucs_shifts")))
                         if v})
        dev = torch_device()
        where = ("GPU" if dev == "cuda" else
                 "CPU — CHẬM: nhấp đúp install_gpu_torch.bat để dùng GPU" if dev == "cpu" else "?")
        try:
            with group_slot("gpu", on_wait=lambda what: self.log(f"Đang đợi lượt {what} để tách nhạc nền…")):
                if ranges:
                    secs = sum(b - a for a, b in ranges)
                    self.log(f"Tách nhạc nền khỏi giọng nói — chỉ {len(ranges)} tình huống đã duyệt (~{secs / 60:.1f} "
                             f"phút), Demucs chạy bằng {where}…")
                    layout = separate_ranges(Path(job.footage[0]), [tuple(r) for r in ranges], out,
                                             analysis / "audio" / "vocals_00.wav",
                                             concat_vocals_dst=analysis / "audio" / "vocals_concat.wav",
                                             total_s=self._footage_size(job)[2] or max(b for _, b in ranges) + 1,
                                             model=bcfg.get("model", "htdemucs"), device=str(bcfg.get("device", "auto")),
                                             shifts=int(bcfg.get("shifts") or 0))
                    job.data["bgm_layout"] = layout
                else:
                    self.log(f"Tách nhạc nền khỏi giọng nói của video gốc (Demucs chạy bằng {where}, có thể mất vài "
                             "phút)…")
                    separate_bgm(Path(job.footage[0]), out, model=bcfg.get("model", "htdemucs"),
                                 device=str(bcfg.get("device", "auto")), vocals_dst=analysis / "audio" / "vocals_00.wav")
        except Exception as exc:
            self.log(f"Không giữ được nhạc nền gốc — dùng nhạc AI chọn thay thế. Lý do: {exc}")
            return None
        job.data["bgm_ranges"] = ranges
        job.data["bgm_model"] = sep_sig
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

    def _write_ctx(self, job: Job) -> dict:
        """Dữ liệu dùng chung khi ghi draft CapCut cho các video của job."""
        from app.director.tasks import load_analysis

        d, analysis, plan_dir = self._paths(job)
        if job.options.films:  # content nhiều phim: dựng riêng (app/planner/films_build.py)
            return {"d": d, "analysis": analysis, "plan_dir": plan_dir, "tpl": self._template()}
        style = self._style(job)
        a = load_analysis(analysis)
        a["text_boxes"] = self._text_boxes(job, analysis, a)
        src = self._capcut_source(analysis, Path(a["scenes"].get("path") or ""))
        if src is not None:
            a["scenes"] = {**a["scenes"], "path": src.as_posix()}
        clean = analysis / "audio" / "clean_00.wav"
        if (style.get("audio") or {}).get("clean") == "light":  # vlog: lọc ồn nhẹ, giữ âm thanh hiện trường
            light = analysis / "audio" / "light_00.wav"
            if light.is_file():
                clean = light
            else:
                self.log("Job phân tích trước khi có bản lọc ồn nhẹ — dùng bản lọc ồn thường (tạo job mới để có).")
        return {"d": d, "analysis": analysis, "plan_dir": plan_dir, "tpl": self._template(), "style": style, "a": a,
                "clean": clean}

    def _capcut_source(self, analysis: Path, src: Path) -> Path | None:
        """Video gốc nén bằng codec CapCut có thể không mở được (AV1 — hay gặp ở video tải từ YouTube; chủ dự án 17/10) →
        đổi một lần sang H.264 (analysis/capcut_src_00.mp4), draft trỏ vào bản này. Codec khác / lỗi → None (dùng file gốc)."""
        from app.analysis import ffmpeg

        codecs = [c.lower() for c in (config.load("capcut").get("transcode_codecs") or ["av1"])]
        if not codecs or not src.is_file():
            return None
        out = analysis / "capcut_src_00.mp4"
        if out.is_file() and out.stat().st_mtime >= src.stat().st_mtime:
            return out.resolve()
        codec = ffmpeg.video_codec(src)
        if codec not in codecs:
            return None
        self.log(f"Video gốc nén bằng {codec.upper()} — CapCut có thể không mở được, đổi sang H.264 (làm một lần)…")
        tmp = out.with_name("capcut_src_00.part.mp4")
        try:
            ffmpeg.run(ffmpeg.h264_args(src, tmp))
            tmp.replace(out)
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            self.log(f"⚠️ Không đổi được sang H.264 ({exc}) — dùng file gốc.")
            return None
        return out.resolve()

    def _write_video(self, job: Job, v: dict, ctx: dict) -> tuple[dict, list]:
        """Ghi draft CapCut cho MỘT video; trả (thông tin draft, tài nguyên còn thiếu)."""
        if job.options.films:
            return self._write_films(job, v, ctx)
        from app.director.schemas import EditPlan
        from app.director.policy import cut_ranges, repair_policy
        from app.director.policy import load_cfg as policy_cfg
        from app.planner import hook_io
        from app.planner.builder import build

        d, analysis, plan_dir = ctx["d"], ctx["analysis"], ctx["plan_dir"]
        tpl, style, a, clean = ctx["tpl"], ctx["style"], ctx["a"], ctx["clean"]
        i = v["index"]
        plan = EditPlan.model_validate_json((plan_dir / f"edit_plan_video{i:02d}.json").read_text(encoding="utf-8"))
        u_v = self._u_for(job, v)
        plan, cut = repair_policy(plan, cut_ranges(u_v), policy_cfg().get("min_piece_s", 0.5))
        for c in cut:  # lưới an toàn: đoạn vi phạm được đánh dấu sau khi đã có kế hoạch dựng
            self.log(f"[video {i:02d}] {c}")
        hook, voice = None, None
        if job.use_hook:
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
                        dub_voices[n] = self._review_trimmed(d, f) if (job.options.review or job.options.sell) else \
                            (f.resolve(), self._voice_duration(f))
                rate = dub_io.voice_rate(d, i, dub)
                if rate:  # nhớ tốc độ đọc thật của giọng bạn → lần sau AI viết câu vừa giọng, khỏi đè tiếng
                    key = "review_voice_cps" if job.options.review else "sell_voice_cps" if job.options.sell \
                        else "voice_cps"
                    saved = dub_io.remember_voice_rate(u_v.language, rate, key)
                    self.log(f"Giọng thu của bạn đọc ~{rate:.1f} ký tự/giây ({u_v.language}); đã lưu {saved:.1f} "
                             + ("(giọng review) " if job.options.review else "")
                             + "để lần sau viết câu vừa giọng.")
        if job.options.review and dub is not None:  # review: DỰNG TỪ VOICE — cảnh cắt theo bài đọc + voice đã thu
            from app.director.tasks import effective_cps, review_dub_cfg
            from app.planner.review_sync import build_from_voice

            rcfg = config.load("review")
            plan, dub, sync_notes = build_from_voice(
                plan, dub, {n: us / 1_000_000 for n, (_, us) in (dub_voices or {}).items()},
                [x["start"] for x in a["scenes"].get("scenes", [])],
                cps=effective_cps(review_dub_cfg(config.load("dub")), u_v.language),
                gap_s=float(rcfg.get("voice_gap_s", 0.12)), cut_s=float(rcfg.get("cut_s", 2.0)),
                min_cut_s=float(rcfg.get("min_cut_s", 1.0)))
            for n in sync_notes:
                self.log(f"[video {i:02d}] {n}")
        dub_windows, timed_fx, extra_sources = None, None, None
        if job.options.sell and dub is not None:  # bán content: cảnh cắt / đảo / dùng lại theo voice thật
            from app.director.sell import sell_cfg, sell_cps
            from app.planner.sell_sync import build_sell

            from app import scene_library

            scfg = sell_cfg()
            sc = a["scenes"]
            b = u_v.burned_in_text
            want = {s.lib for ln in dub.lines for s in (ln.shots or []) if s.lib}
            extra_sources = scene_library.sources(want) if want else {}
            if want - set(extra_sources):  # cảnh kho đã bị xóa → bỏ, tool bù bằng cảnh video gốc như cũ
                self.log(f"[video {i:02d}] ⚠️ Không thấy cảnh kho {', '.join(sorted(want - set(extra_sources)))} — dùng "
                         "cảnh video gốc thay.")
                dub = dub.model_copy(update={"lines": [ln.model_copy(update={"shots": [
                    s for s in ln.shots if not s.lib or s.lib in extra_sources]}) for ln in dub.lines]})
            # ý tưởng từ video dài: cảnh bù (khi thiếu) chỉ lấy trong các cảnh của ý tưởng, không lấy bừa cả video dài
            pool = (v.get("pool") or None) if job.options.ideas else None
            clips, dub_windows, sync_notes = build_sell(
                dub, {n: us / 1_000_000 for n, (_, us) in (dub_voices or {}).items()}, pool or sc.get("scenes") or [],
                float(sc["duration"]), cps=sell_cps(scfg, u_v.language), cfg=scfg,
                allow_mirror=getattr(u_v, "mirror_ok", True) and not b.present)
            plan = plan.model_copy(update={"clips": clips, "transitions": [], "zooms": [], "emphasis": [], "sfx": [],
                                           "effects": [], "stickers": [], "arrows": []})
            from app.planner.sell_sync import sell_fx

            fcfg = scfg.get("fx") or {}
            timed_fx = sell_fx(dub, dub_windows, scfg,
                               emphasis=bool(fcfg.get("emphasis", True)) and not style.get("no_emphasis"))
            for n in sync_notes:
                self.log(f"[video {i:02d}] {n}")
        bgm = self._bgm(job, analysis) if (job.options.voice_only and job.options.keep_bgm) or job.options.char_dub \
            else None
        res = build(plan, u_v, a, tpl, self._drafts_dir or drafts_root(), name, style,
                    hook=hook, voice=voice,
                    clean_audio=clean.resolve() if clean.is_file() and not job.options.sell else None,
                    video_index=i, dub=dub, dub_voices=dub_voices, vi_subtitles=self.vi_subtitles(job),
                    bgm_audio=bgm, vocals_audio=self._unvoiced_vocals(job, analysis, bgm),
                    cold_clip=self._cliff_hook(v) if job.options.cliff else None,
                    cold_subs=self._cliff_hook_subs(job, v) if job.options.cliff else None, dub_windows=dub_windows,
                    timed_fx=timed_fx, extra_sources=extra_sources)
        if job.options.sell:
            from app.director.sell import sell_cfg

            res.writer.pack_media = bool(sell_cfg().get("pack_media", True))
            used_lib = sorted({c.lib for c in plan.clips if c.lib and c.lib in (extra_sources or {})})
            if used_lib:
                from app import scene_library

                scene_library.mark_used(used_lib, job.job_id)
                self.log(f"[video {i:02d}] Dùng {len(used_lib)} cảnh từ kho cảnh chung: {', '.join(used_lib)}.")
        out = res.writer.save(overwrite=True)
        if res.writer.packed_files():
            self.log(f"[video {i:02d}] Đã đóng gói {len(res.writer.packed_files())} file (video nguồn, voice, nhạc) vào "
                     f"{Path(out) / 'media'} — mở CapCut không thiếu file.")
        dur = round(res.duration_us / 1_000_000, 1)
        info = {"index": i, "draft": str(out), "duration_s": dur, "missing_assets": len(res.missing_assets),
                       "start": v["start"], "end": v["end"],
                       "short": dur < config.load("split").get("min_video_s", 60),
                       "credits": self._credits(res.used_local)}
        for n in res.notes:
            self.log(f"[video {i:02d}] {n}")
        self.log(f"Đã ghi draft CapCut: {out} ({dur}s)")
        return info, res.missing_assets

    def step_write(self, job: Job) -> None:
        if job.options.vi_sub:
            return self._write_vi_sub(job)
        ctx = self._write_ctx(job)
        drafts, missing = [], []
        for v in self.videos(job):
            info, miss = self._write_video(job, v, ctx)
            drafts.append(info)
            missing += miss
        (ctx["d"] / "missing_assets.json").write_text(json.dumps(missing, ensure_ascii=False, indent=2), encoding="utf-8")
        job.data["drafts"] = drafts
        job.data["draft"] = drafts[0]["draft"]
        job.data["duration_s"] = drafts[0]["duration_s"]
        job.data["missing_assets"] = len(missing)
        job.data.pop("ready_drafts", None)

    def _review_trimmed(self, d: Path, f: Path) -> tuple[Path, int]:
        """Review nói liền mạch (chủ dự án 11/10): bản voice đã cắt sạch lặng đầu / cuối (voice/_lien_mach/, làm lại khi
        file gốc đổi) — độ dài câu đo trên bản này nên cảnh và giọng nối sát nhau. Không đọc được file → dùng file gốc."""
        from app.planner.voice_split import trim_file

        out = d / "voice" / "_lien_mach" / f"{f.stem}.wav"
        try:
            if not out.is_file() or out.stat().st_mtime < f.stat().st_mtime:
                trim_file(f, out, float(config.load("review").get("voice_trim_keep_s", 0.03)))
            return out.resolve(), self._voice_duration(out)
        except Exception:
            return f.resolve(), self._voice_duration(f)

    def _voice_sig(self, d: Path, index: int) -> str:
        """Dấu vân tay voice của một video (tên + cỡ + giờ sửa) — đổi voice thì ghi lại draft."""
        files = sorted((d / "voice").glob(f"video{index:02d}_dub*.*")) if (d / "voice").is_dir() else []
        return "|".join(f"{f.name}:{f.stat().st_size}:{int(f.stat().st_mtime)}" for f in files if "_cu" not in f.stem)

    def _voices_newer(self, job: Job, index: int, draft: Path) -> bool:
        """Có file voice của video này mới hơn lần ghi draft cuối (tải lên / OmniVoice SAU khi dựng xong)?"""
        from app.capcut_writer.template import timeline_copies

        d, _, _ = self._paths(job)
        names = [f"video{index:02d}_dub*.*", f"video{index:02d}_hook.*"]
        files = [f for n in names for f in (d / "voice").glob(n)
                 if "_cu" not in f.stem and f.is_file()] if (d / "voice").is_dir() else []
        if not files:
            return False
        written = [p.stat().st_mtime for p in timeline_copies(draft) if p.is_file()]
        return not written or max(f.stat().st_mtime for f in files) > max(written) + 1

    def refresh_voice_drafts(self, job: Job) -> list[int]:
        """Chủ dự án 14/10 "có voice rồi mà không thêm vào dự án CapCut": job đã XONG, sau đó bạn tải voice / thu lại /
        cho OmniVoice đọc → trước đây tool không dựng lại. Giờ video nào có voice mới hơn draft thì ghi lại draft đó
        (chỉnh tay trong CapCut của video đó sẽ mất — giống bấm 🔁 Dựng lại draft). Trả các video đã ghi lại."""
        if not (self._dubbing(job) or job.use_hook) or job.options.vi_sub:
            return []
        drafts = list(job.data.get("drafts") or [])
        todo = [dr for dr in drafts if self._voices_newer(job, int(dr["index"]), Path(dr["draft"]))]
        if not todo:
            return []
        vids = {v["index"]: v for v in self.videos(job)}
        done = []
        try:
            ctx = self._write_ctx(job)
            for dr in todo:
                i = int(dr["index"])
                info, _ = self._write_video(job, vids[i], ctx)
                drafts[drafts.index(dr)] = {**dr, **info}
                done.append(i)
        except RuntimeError as exc:  # thường là CapCut đang mở
            job._log(f"⚠️ Có voice mới nhưng chưa ghi được vào dự án CapCut: {exc} Đóng CapCut rồi bấm 🔁 Dựng lại draft.")
            job.save(self.jobs_root)
            self.log(job.message)
            return done
        job.data["drafts"] = drafts
        job.data["draft"] = drafts[0]["draft"]
        job._log(f"✅ Đã cập nhật voice mới vào dự án CapCut: video {', '.join(f'{i:02d}' for i in done)}.")
        job.save(self.jobs_root)
        self.log(job.message)
        return done

    def write_ready_videos(self, job: Job) -> list[int]:
        """Voice đến đâu ghi CapCut đến đấy (chủ dự án yêu cầu 09/10): video nào ĐỦ voice thì ghi draft ngay, không
        chờ các video khác. Voice đổi thì ghi lại. Trả các video vừa ghi."""
        from app.planner import dub_io

        if not self._dubbing(job) or job.options.vi_sub:
            return []
        d, _, _ = self._paths(job)
        scripts = self._dub_scripts(job)
        ready = job.data.setdefault("ready_drafts", {})
        todo = []
        for v in self.videos(job):
            i, s = v["index"], scripts.get(v["index"])
            if s is None or dub_io.missing_lines(d, {i: s}):
                continue
            sig = self._voice_sig(d, i)
            if ready.get(str(i), {}).get("sig") != sig:
                todo.append((v, sig))
        if not todo:
            return []
        ctx = self._write_ctx(job)
        done = []
        for v, sig in todo:
            info, _ = self._write_video(job, v, ctx)
            ready[str(v["index"])] = {**info, "sig": sig}
            done.append(v["index"])
            self.log(f"✅ Video {v['index']:02d} đủ voice — đã ghi dự án CapCut (mở CapCut xem được ngay, các video "
                     "khác vẫn chờ voice).")
        job.save(self.jobs_root)
        return done

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
        if job.options.films:  # caption đã viết cùng content (không hỏi AI thêm)
            from app.director.films import to_captions

            out = d / "deliver" / "video01_captions.txt"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(captions_text(to_captions(self._films_idea(job))), encoding="utf-8")
            job.data["captions"] = str(d / "deliver")
            self.log(f"Đã xuất caption: {out}")
            return
        credits = {dr["index"]: dr.get("credits") or [] for dr in job.data.get("drafts", [])}
        for v in self.videos(job):
            i = v["index"]
            out = d / "deliver" / f"video{i:02d}_captions.txt"
            cap_json = plan_dir / f"captions_video{i:02d}.json"
            if cap_json.is_file() and out.is_file():  # đã viết rồi: không gọi lại AI, chỉ cập nhật phần ghi nguồn
                c = Captions.model_validate_json(cap_json.read_text(encoding="utf-8"))
            else:
                plan = EditPlan.model_validate_json((plan_dir / f"edit_plan_video{i:02d}.json").read_text(encoding="utf-8"))
                hook = self._hook_for(d, i) if job.use_hook else None
                c = make_captions(self.director, analysis, self._u_for(job, v), plan, hook=hook, video_index=i)
                cap_json.write_text(c.model_dump_json(indent=2), encoding="utf-8")
            text = captions_text(c)
            if credits.get(i):
                text += "\n\n=== GHI NGUỒN (bắt buộc theo giấy phép, dán vào caption) ===\n" + "\n".join(credits[i])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            self.log(f"Đã xuất caption: {out}")
        job.data["captions"] = str(d / "deliver")
        if job.options.ideas:  # chủ dự án 17/10: job xong → cảnh đẹp của video dài vào kho cảnh chung
            self._harvest_library(job)

    def _harvest_library(self, job: Job) -> int:
        """Cắt cảnh đẹp (danh mục cảnh của job Ý tưởng) vào kho cảnh chung. Lỗi chỉ ghi nhật ký, không làm hỏng job."""
        from app import scene_library
        from app.director.policy import cut_ranges
        from app.director.schemas import Catalog
        from app.director.tasks import load_analysis

        _, analysis, plan_dir = self._paths(job)
        try:
            cat = Catalog.model_validate_json((plan_dir / "catalog.json").read_text(encoding="utf-8"))
            sc = load_analysis(analysis)["scenes"]
            n = scene_library.harvest(job.job_id, Path(sc["path"]), (int(sc["width"]), int(sc["height"])), cat,
                                      banned=cut_ranges(self._understanding(job)), log=self.log)
        except Exception as exc:
            self.log(f"⚠️ Chưa lưu được cảnh vào kho cảnh chung: {exc}")
            return 0
        job.data["library_added"] = job.data.get("library_added", 0) + n
        self.log(f"📦 Đã lưu {n} cảnh đẹp vào kho cảnh chung (thư mục library) — job Bán content / Ý tưởng sau thiếu "
                 "cảnh sẽ lấy từ kho." if n else "📦 Kho cảnh chung: không có cảnh mới để lưu.")
        return n

    def _library_for(self, job: Job, v: dict, analysis: Path) -> list[dict]:
        """Cảnh kho chung AI được bù cho video này (cùng tỉ lệ khung, hợp chủ đề)."""
        from app import scene_library
        from app.capcut_writer.layout import nearest_ratio
        from app.director.tasks import load_analysis

        try:
            sc = load_analysis(analysis)["scenes"]
            it = v.get("idea") or {}
            query = " ".join([self._understanding(job).summary_vi, v.get("title_vi", ""), v.get("summary_vi", ""),
                              it.get("angle_vi", "")])
            return scene_library.candidates(nearest_ratio(int(sc["width"]), int(sc["height"])), query,
                                            exclude_job=job.job_id)
        except Exception as exc:
            self.log(f"⚠️ Không đọc được kho cảnh chung: {exc}")
            return []
