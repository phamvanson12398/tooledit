@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Cai Gemini CLI - AI dao dien Gemini Pro - TUY CHON ===
echo.
echo Dung goi Google AI Pro cua tai khoan Google, KHONG can API key.
echo LUU Y: KHONG bam chuot vao cua so nay trong luc cai.
echo.

where node >nul 2>nul
if errorlevel 1 (
  echo [1/3] Chua co Node.js - cai Node.js LTS bang winget ...
  winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
  echo.
  echo Cai Node.js xong: DONG cua so nay roi NHAP DUP LAI install_gemini.bat de cai tiep.
  echo Neu winget bao loi: tai Node.js LTS o https://nodejs.org roi chay lai file nay.
  pause
  exit /b 0
)
echo [1/3] Da co Node.js:
node --version

echo [2/3] Cai Gemini CLI ban 0.63.0 - ban da doi chieu voi tool ...
call npm install -g @google/gemini-cli@0.63.0
if errorlevel 1 (
  echo LOI khi cai Gemini CLI. Chup man hinh gui lai cho Claude.
  pause
  exit /b 1
)
call gemini --version
if errorlevel 1 (
  echo LOI: chua chay duoc lenh gemini. Dong cua so, mo lai roi chay lai file nay.
  pause
  exit /b 1
)

echo.
echo [3/3] DANG NHAP LAN DAU: cua so Gemini se mo ngay sau day.
echo   - Chon "Sign in with Google", dang nhap tai khoan Google co goi AI Pro tren trinh duyet.
echo   - Thay giao dien chat cua Gemini la xong: go /quit roi Enter de thoat.
echo.
pause
call gemini
echo.
echo XONG. Mo start.bat, o "AI dao dien" chon Gemini Pro khi tao job.
pause
