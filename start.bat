@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Chua cai dat. Hay chay install.bat truoc.
  pause
  exit /b 1
)
echo === Tool dung video TikTok ===
echo Dang mo giao dien tai http://127.0.0.1:8765  (dong cua so nay de tat tool)
start "" http://127.0.0.1:8765
.venv\Scripts\python -m uvicorn app.web.server:app --host 127.0.0.1 --port 8765
pause
