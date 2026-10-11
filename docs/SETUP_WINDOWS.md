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

**Đăng nhập lại / đổi tài khoản Claude** (vd hết hạn đăng nhập, tool báo lỗi xác thực, hoặc muốn dùng tài khoản khác).
Đóng `start.bat` trước, rồi trong PowerShell:

```powershell
claude auth status    # xem đang đăng nhập tài khoản nào
claude auth logout    # đăng xuất tài khoản hiện tại
claude auth login     # mở trình duyệt → đăng nhập tài khoản Claude Pro → quay lại PowerShell thấy báo thành công
```

Cách khác: gõ `claude` để mở cửa sổ chat, gõ `/logout` (hoặc `/login` để đổi tài khoản), làm theo hướng dẫn trên trình
duyệt, rồi gõ `/exit`. Xong mở lại `start.bat`.

Nếu `claude` vẫn "not recognized" sau khi mở lại PowerShell: file cài nằm ở
`%USERPROFILE%\.local\bin\claude.exe`; xem https://code.claude.com/docs/en/troubleshoot-install.

## Gemini Pro — AI đạo diễn thứ hai (TÙY CHỌN)

Khi tạo job có ô **🤖 AI đạo diễn**: Claude (mặc định) hoặc **Gemini Pro**. Gemini chạy qua Gemini CLI chính thức của
Google, đăng nhập bằng tài khoản Google có **gói Google AI Pro** — không cần API key.

**Cách dễ nhất:** nhấp đúp **`install_gemini.bat`** trong thư mục tool. File này:
1. kiểm tra Node.js (Gemini CLI cần Node.js 20+); chưa có thì cài bằng `winget` — cài xong **đóng cửa sổ, nhấp đúp lại**;
2. cài Gemini CLI bản 0.63.0 (bản tool đã đối chiếu cờ lệnh): `npm install -g @google/gemini-cli@0.63.0`;
3. mở Gemini lần đầu: chọn **Sign in with Google**, đăng nhập trên trình duyệt, thấy giao diện chat thì gõ `/quit`.

Kiểm tra bằng PowerShell:

```powershell
gemini --version      # in ra 0.63.0
```

**Đăng nhập lại / đổi tài khoản Google:** gõ `gemini`, gõ `/auth`, chọn lại **Sign in with Google**, rồi `/quit`.
Model mặc định `gemini-2.5-pro` (sửa `gemini_model` trong `config\director.yaml`; để `null` = Gemini CLI tự chọn).

## OmniVoice — giọng AI đọc thoại (TÙY CHỌN)

Dùng khi muốn tool tự đọc thoại thay vì tự thu (nút **🤖 Cho OmniVoice đọc** trên trang voice). OmniVoice
(https://github.com/k2-fsa/OmniVoice, Apache-2.0) chạy trên máy bạn; có GPU NVIDIA thì nhanh, không có vẫn chạy bằng CPU
nhưng rất chậm.

**Cách dễ nhất:** tắt tool (đóng cửa sổ `start.bat`), nhấp đúp **`install_omnivoice.bat`** trong thư mục tool. File này
tự tạo môi trường riêng `omnivoice-env` trong thư mục tool, tự nhận GPU NVIDIA (có thì cài PyTorch bản GPU, không thì bản
CPU), cài OmniVoice rồi kiểm tra — cuối cùng hiện `OmniVoice OK - dung GPU: True/False`. Mất 10–30 phút, tải 3–5 GB.
Tool TỰ TÌM môi trường này, không cần sửa `config\tts.yaml` (để `python: ""`).

Cách tự cài bằng tay (khi muốn dùng môi trường OmniVoice có sẵn, vd của Voice Studio):

```powershell
cd C:\
py -3.11 -m venv omnivoice-env
C:\omnivoice-env\Scripts\python -m pip install --upgrade pip
# Có GPU NVIDIA (kiểm tra CUDA bằng lệnh nvidia-smi); không có GPU thì bỏ phần +cu128 và --extra-index-url:
C:\omnivoice-env\Scripts\python -m pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 --extra-index-url https://download.pytorch.org/whl/cu128
C:\omnivoice-env\Scripts\python -m pip install -r <thư mục tool>\requirements-tts.txt
```

Rồi mở `config\tts.yaml` sửa dòng `python:` thành `C:\omnivoice-env\Scripts\python.exe` (hoặc python của môi trường
Voice Studio). Lần đầu chạy, OmniVoice tự tải model
(vài GB) từ HuggingFace — mạng chậm thì đặt biến `HF_ENDPOINT=https://hf-mirror.com` trước khi mở `start.bat`.

## 6. Dùng hằng ngày

Nhấp đúp **`start.bat`** trong thư mục repo → trình duyệt mở giao diện http://127.0.0.1:8765.
Cập nhật tool: `git pull` rồi chạy lại `install.bat` (hoặc `.venv\Scripts\pip install -r requirements.txt`).

## Tùy chọn: key Freesound để tự tải âm thanh CC0

Không bắt buộc. Có key thì nút **🔍 Quét tài nguyên** tự tải SFX / nhạc nền còn thiếu (chỉ giấy phép CC0).
Đăng ký ở https://freesound.org → mở https://freesound.org/apiv2/apply → tạo key → dán vào
**⚙️ Cài đặt Freesound** trên trang chủ tool. Key lưu ở `config/local.yaml` (không commit).

## Tùy chọn: Demucs để "Giữ nhạc nền gốc" (chế độ Chỉ thay tiếng)

Không bắt buộc. Cần khi muốn giữ nhạc nền của video gốc và chỉ thay lời thuyết minh. Demucs (giấy phép MIT) tách giọng
nói khỏi nhạc ngay trên máy, kéo theo PyTorch (~1–2 GB). Mở PowerShell trong thư mục tool:

```powershell
.\.venv\Scripts\python -m pip install -r requirements-bgm.txt
.\.venv\Scripts\python -c "import demucs; print('Demucs OK')"
```

Lần tách đầu tiên Demucs tự tải model (~80 MB, cần internet). Máy có GPU NVIDIA thì nhanh; không có GPU vẫn chạy bằng
CPU (video 1–2 phút mất vài phút). Đổi `device: cpu` trong `config\dub.yaml → voice_only → keep_bgm` nếu GPU báo hết bộ nhớ.
