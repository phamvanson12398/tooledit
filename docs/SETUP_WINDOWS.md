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

1. Driver NVIDIA: `nvidia-smi` → dòng "CUDA Version" phải từ 12.x trở lên.
2. Cài thư viện NVIDIA bằng pip (install.bat đã làm bước này):

   ```powershell
   .venv\Scripts\pip install -r requirements-gpu.txt
   ```

   Tool tự thêm thư mục DLL của các gói này vào PATH khi chạy (`app/gpu_libs.py`).
3. Kiểm tra: `.venv\Scripts\python tools\check_gpu.py` → cả 3 dòng `cublas64_12.dll`,
   `cublasLt64_12.dll`, `cudnn64_9.dll` phải "nạp được".

**Chưa chắc chắn:** các bản cuDNN 9 mới có thể đã bỏ hỗ trợ card đời Pascal (GTX 10xx). Nếu GPU
không chạy được, tool **tự chuyển sang CPU** (chậm hơn nhưng vẫn ra kết quả) và in lý do.
Lần chạy đầu, faster-whisper tự tải model large-v3 (~3 GB) về máy.

## 5. Claude Code (đạo diễn AI)

Tool gọi Claude Code chạy trên máy, đăng nhập bằng gói Claude Pro. Theo tài liệu chính thức
(https://code.claude.com/docs/en/setup), cài trên Windows bằng PowerShell, **không cần quyền Administrator**:

```powershell
irm https://claude.ai/install.ps1 | iex
```

Cài xong **đóng PowerShell rồi mở lại**, kiểm tra:

```powershell
claude --version     # in ra số phiên bản, ví dụ "2.1.x (Claude Code)"
claude doctor        # kiểm tra cài đặt
```

Đăng nhập lần đầu: gõ `claude`, làm theo hướng dẫn mở trình duyệt, đăng nhập tài khoản Claude Pro, rồi gõ
`/exit` để thoát. Gói Free không dùng được Claude Code.

Nếu `claude` vẫn "not recognized" sau khi mở lại PowerShell: file cài nằm ở
`%USERPROFILE%\.local\bin\claude.exe`; xem https://code.claude.com/docs/en/troubleshoot-install.

## 6. Dùng hằng ngày

Nhấp đúp **`start.bat`** trong thư mục repo → trình duyệt mở giao diện http://127.0.0.1:8765.
Cập nhật tool: `git pull` rồi chạy lại `install.bat` (hoặc `.venv\Scripts\pip install -r requirements.txt`).
