@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Cai OmniVoice (giong AI doc thoai) - TUY CHON ===
echo.
echo OmniVoice duoc cai vao thu muc rieng "omnivoice-env" ngay trong thu muc tool,
echo khong anh huong tool chinh. Tool se tu tim thay, KHONG can sua config\tts.yaml.
echo.
echo LUU Y: KHONG bam chuot vao cua so nay trong luc cai.
echo Neu tieu de cua so hien chu "Select", bam phim Esc de chay tiep.
echo Qua trinh mat 10-30 phut (tai khoang 3-5 GB). Lan dau doc thoai, OmniVoice tai them model vai GB.
echo.

if not exist omnivoice-env\Scripts\python.exe (
  echo [1/4] Tao moi truong Python omnivoice-env ... (khoang 30 giay)
  py -3.11 -m venv omnivoice-env || python -m venv omnivoice-env
  if not exist omnivoice-env\Scripts\python.exe (
    echo LOI: khong tao duoc moi truong Python. Kiem tra da cai Python 3.11 chua: python --version
    pause
    exit /b 1
  )
) else (
  echo [1/4] Da co moi truong omnivoice-env, cai tiep vao do.
)
set PY=omnivoice-env\Scripts\python.exe

echo [2/4] Cap nhat pip ...
%PY% -m pip install --upgrade pip

where nvidia-smi >nul 2>nul
if errorlevel 1 (
  echo [3/4] KHONG thay GPU NVIDIA - cai PyTorch ban CPU. OmniVoice van chay nhung CHAM.
  %PY% -m pip install torch==2.8.0 torchaudio==2.8.0
) else (
  echo [3/4] Thay GPU NVIDIA - cai PyTorch ban GPU CUDA 12.8 (khoang 3 GB) ...
  %PY% -m pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 --extra-index-url https://download.pytorch.org/whl/cu128
)
if errorlevel 1 (
  echo LOI khi cai PyTorch. Chup man hinh gui lai cho Claude.
  pause
  exit /b 1
)

echo [4/4] Cai OmniVoice ...
%PY% -m pip install -r requirements-tts.txt
if errorlevel 1 (
  echo LOI khi cai OmniVoice. Chup man hinh gui lai cho Claude.
  pause
  exit /b 1
)

echo.
echo Kiem tra:
%PY% -c "import omnivoice, torch; print('OmniVoice OK - dung GPU:', torch.cuda.is_available())"
if errorlevel 1 (
  echo LOI: chua import duoc omnivoice. Chup man hinh gui lai cho Claude.
  pause
  exit /b 1
)
echo.
echo XONG. Mo lai start.bat roi bam "Cho OmniVoice doc" tren trang voice.
echo Nhan phim bat ky de dong.
pause >nul
