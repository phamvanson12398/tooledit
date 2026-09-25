@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Cai dat thu vien cho tool dung video ===
if not exist .venv (
  py -3.11 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo === Kiem tra GPU ===
python tools\check_gpu.py
echo.
echo Xong. Nhan phim bat ky de dong.
pause >nul
