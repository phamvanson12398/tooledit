"""Kiểm tra GPU cho nhận dạng thoại. Chạy: .venv\\Scripts\\python tools\\check_gpu.py"""

import ctypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import ctranslate2
except ImportError:
    sys.exit("Chưa cài thư viện. Chạy install.bat trước.")

from app.gpu_libs import register_cuda_dlls  # noqa: E402

n = ctranslate2.get_cuda_device_count()
print(f"Số GPU NVIDIA nhận được: {n}")
if n == 0:
    print("-> Không dùng được GPU (thiếu driver NVIDIA hoặc CUDA 12). Tool sẽ chạy bằng CPU (chậm hơn).")
    sys.exit(0)
types = sorted(ctranslate2.get_supported_compute_types("cuda"))
print(f"Kiểu tính toán GPU hỗ trợ: {', '.join(types)}")
print("-> int8_float32: " + ("CÓ" if "int8_float32" in types else "KHÔNG, báo lại cho Claude"))

if sys.platform == "win32":
    dirs = register_cuda_dlls()
    print(f"Thư mục thư viện NVIDIA tìm thấy: {len(dirs)}")
    ok = True
    for dll in ("cublas64_12.dll", "cublasLt64_12.dll", "cudnn64_9.dll"):
        try:
            ctypes.WinDLL(dll)
            print(f"  {dll}: nạp được")
        except OSError as exc:
            ok = False
            print(f"  {dll}: KHÔNG nạp được ({exc})")
    if not ok:
        print("-> Chạy: .venv\\Scripts\\pip install -r requirements-gpu.txt")
