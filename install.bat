@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Cai dat thu vien cho tool dung video ===
echo.
echo LUU Y: KHONG bam chuot vao cua so nay trong luc cai.
echo Neu tieu de cua so hien chu "Select", bam phim Esc de chay tiep.
echo Toan bo qua trinh co the mat 5-15 phut (tai khoang 1 GB).
echo.

if not exist .venv (
  echo [1/4] Tao moi truong Python .venv ... (khoang 30 giay)
  py -3.11 -m venv .venv || python -m venv .venv
  if errorlevel 1 (
    echo LOI: khong tao duoc moi truong Python. Kiem tra da cai Python 3.11 chua: python --version
    pause
    exit /b 1
  )
) else (
  echo [1/4] Da co moi truong .venv, bo qua.
)
call .venv\Scripts\activate.bat

echo [2/4] Cap nhat pip ...
python -m pip install --upgrade pip

echo [3/4] Cai thu vien (buoc nay lau nhat, se thay nhieu dong chu chay qua) ...
pip install -r requirements.txt
if errorlevel 1 (
  echo LOI khi cai thu vien. Chup man hinh gui lai cho Claude.
  pause
  exit /b 1
)

echo.
echo [4/4] Kiem tra GPU ...
python tools\check_gpu.py
echo.
echo XONG. Nhan phim bat ky de dong.
pause >nul
