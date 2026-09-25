"""Giúp faster-whisper (CTranslate2) tìm thấy thư viện CUDA cài bằng pip trên Windows.

Gói pip nvidia-cublas-cu12 / nvidia-cudnn-cu12 đặt DLL ở site-packages/nvidia/<tên>/bin
(cublas64_12.dll, cudnn64_9.dll...). Windows không tự tìm ở đó, nên phải thêm các thư mục
này vào PATH trước khi CTranslate2 nạp chúng.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_DONE = False


def nvidia_bin_dirs(search_paths: list[str] | None = None) -> list[Path]:
    dirs: list[Path] = []
    for base in search_paths if search_paths is not None else sys.path:
        root = Path(base) / "nvidia"
        if not root.is_dir():
            continue
        for sub in sorted(root.iterdir()):
            for name in ("bin", "lib"):
                d = sub / name
                if d.is_dir() and any(d.glob("*.dll")) and d not in dirs:
                    dirs.append(d)
    return dirs


def register_cuda_dlls() -> list[Path]:
    """Chỉ có tác dụng trên Windows; gọi nhiều lần cũng không sao."""
    global _DONE
    if _DONE or sys.platform != "win32":
        return []
    dirs = nvidia_bin_dirs()
    if dirs:
        os.environ["PATH"] = os.pathsep.join([*map(str, dirs), os.environ.get("PATH", "")])
        for d in dirs:
            try:
                os.add_dll_directory(str(d))
            except (OSError, AttributeError):
                pass
    _DONE = True
    return dirs
