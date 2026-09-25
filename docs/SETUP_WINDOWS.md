# Cài đặt trên Windows

Làm một lần. Mỗi lệnh gõ trong **PowerShell** (bấm Start, gõ "PowerShell").

## 1. Cài Python 3.11, Git và FFmpeg

```powershell
winget install --id Python.Python.3.11 -e
winget install --id Git.Git -e
winget install --id Gyan.FFmpeg -e
```

Cài xong **đóng PowerShell rồi mở lại**, kiểm tra:

```powershell
python --version     # phải ra 3.11.x
ffmpeg -version      # ra dòng "ffmpeg version ..."
ffprobe -version
```

## 2. Tải repo

```powershell
cd $HOME\Documents
git clone https://github.com/phamvanson12398/tooledit.git
cd tooledit
git checkout claude/new-session-lqnr47
```

(Đã clone rồi thì chỉ cần `cd $HOME\Documents\tooledit` rồi `git pull`.)

## 3. Cài thư viện

Nhấp đúp `install.bat` trong thư mục repo (hoặc chạy `.\install.bat`). Script tạo môi trường `.venv`,
cài thư viện, rồi chạy `tools\check_gpu.py`. Mất khoảng 5–15 phút.

> **Lưu ý:** trong lúc cài, **đừng bấm chuột vào cửa sổ đen**. Nếu tiêu đề cửa sổ hiện chữ
> **"Select"** thì chương trình đang bị Windows tạm dừng; bấm **Esc** để chạy tiếp.

## 4. GPU cho nhận dạng thoại (GTX 1080 Ti) `[CẦN KIỂM TRA TRÊN MÁY]`

faster-whisper cần **cuBLAS cho CUDA 12** và **cuDNN 9 cho CUDA 12** (theo README của faster-whisper).
GTX 1080 Ti (Compute Capability 6.1) chạy được kiểu `int8_float32` (đã đặt trong `config/whisper.yaml`).

1. Cập nhật driver NVIDIA mới nhất (GeForce Experience hoặc nvidia.com). Kiểm tra: `nvidia-smi`
   → dòng "CUDA Version" phải từ 12.x trở lên.
2. Cài thư viện CUDA, chọn MỘT cách:
   - Cách chính thức: cài CUDA Toolkit 12.x và cuDNN 9 (bản CUDA 12) từ trang NVIDIA.
   - Cách gọn (README faster-whisper gợi ý): tải gói thư viện ở
     https://github.com/Purfview/whisper-standalone-win/releases/tag/libs, giải nén, rồi thêm thư mục
     đó vào biến môi trường PATH.
3. Chạy lại: `.venv\Scripts\python tools\check_gpu.py` → phải thấy "Số GPU NVIDIA nhận được: 1"
   và `int8_float32` có trong danh sách.

Nếu không làm được bước 4, tool vẫn chạy bằng CPU (chậm hơn nhiều với model large-v3).
Lần chạy đầu tiên, faster-whisper tự tải model large-v3 (~3 GB) về máy.
