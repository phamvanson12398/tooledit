@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Cai Antigravity CLI - AI dao dien Gemini Pro - TUY CHON ===
echo.
echo Dung goi Google AI Pro cua tai khoan Google, KHONG can API key.
echo.
set AGY=%LOCALAPPDATA%\agy\bin\agy.exe

if exist "%AGY%" (
  echo [1/2] Da co Antigravity CLI, bo qua buoc cai. Ban nay tu cap nhat ngam.
) else (
  echo [1/2] Cai Antigravity CLI bang trinh cai chinh thuc cua Google ...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://antigravity.google/cli/install.ps1 | iex"
)
if not exist "%AGY%" (
  echo LOI: chua thay agy.exe sau khi cai. Chup man hinh gui lai cho Claude.
  pause
  exit /b 1
)
"%AGY%" --version

echo.
echo [2/2] DANG NHAP LAN DAU: cua so Antigravity se mo ngay sau day.
echo   - Dang nhap tai khoan Google co goi AI Pro theo huong dan tren trinh duyet.
echo   - Thay giao dien chat la xong: go /quit roi Enter, hoac bam Ctrl+C hai lan.
echo   - Da dang nhap tu truoc thi thoat luon.
echo.
pause
"%AGY%"
echo.
echo XONG. Mo start.bat, o "AI dao dien" chon Gemini Pro khi tao job.
pause
