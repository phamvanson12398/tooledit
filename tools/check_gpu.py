"""Kiểm tra GPU cho nhận dạng thoại. Chạy: python tools\\check_gpu.py"""

import sys

try:
    import ctranslate2
except ImportError:
    sys.exit("Chưa cài thư viện. Chạy install.bat trước.")

n = ctranslate2.get_cuda_device_count()
print(f"Số GPU NVIDIA nhận được: {n}")
if n == 0:
    print("-> Không dùng được GPU (thiếu driver NVIDIA hoặc CUDA 12). Tool sẽ chạy bằng CPU (chậm hơn).")
    sys.exit(0)
types = sorted(ctranslate2.get_supported_compute_types("cuda"))
print(f"Kiểu tính toán GPU hỗ trợ: {', '.join(types)}")
print("-> int8_float32 có trong danh sách: " + ("CÓ (đúng cấu hình config/whisper.yaml)" if "int8_float32" in types
                                               else "KHÔNG, báo lại cho Claude"))
