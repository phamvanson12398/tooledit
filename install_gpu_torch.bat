@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Doi PyTorch cua tool sang ban GPU - tach nhac nen Demucs nhanh hon nhieu ===
echo.
echo pip install demucs tren Windows mac dinh keo ve PyTorch ban CHI CHAY CPU nen tach nhac rat cham.
echo File nay cai lai PyTorch ban GPU CUDA 12.6 - ban ho tro card GTX 10xx nhu 1080 Ti,
echo giu nguyen so phien ban dang co. Tai khoang 2.5 GB.
echo LUU Y: KHONG bam chuot vao cua so nay trong luc cai.
echo.
if not exist .venv\Scripts\python.exe (
  echo LOI: chua co moi truong .venv - chay install.bat truoc.
  pause
  exit /b 1
)
set PY=.venv\Scripts\python.exe

%PY% -c "import demucs" 2>nul
if errorlevel 1 (
  echo [1/3] Chua co Demucs - cai Demucs truoc ...
  %PY% -m pip install -r requirements-bgm.txt
)
%PY% -c "import torch, torchaudio; open('torch_ver.txt', 'w').write(torch.__version__.split('+')[0] + ' ' + torchaudio.__version__.split('+')[0])"
if errorlevel 1 (
  echo LOI: chua doc duoc phien ban PyTorch. Chup man hinh gui lai cho Claude.
  pause
  exit /b 1
)
for /f "tokens=1,2" %%a in (torch_ver.txt) do (
  set TV=%%a
  set TAV=%%b
)
del torch_ver.txt
echo [2/3] Dang co torch %TV%, torchaudio %TAV% - cai lai ban GPU cu126 cung phien ban ...
%PY% -m pip install --force-reinstall --no-deps torch==%TV%+cu126 torchaudio==%TAV%+cu126 --index-url https://download.pytorch.org/whl/cu126
if errorlevel 1 (
  echo Phien ban %TV% khong co ban cu126 - thu torch 2.8.0 ban cu126 ...
  %PY% -m pip install --force-reinstall --no-deps torch==2.8.0+cu126 torchaudio==2.8.0+cu126 --index-url https://download.pytorch.org/whl/cu126
)

echo.
echo [3/3] Kiem tra GPU:
%PY% -c "import torch; ok = torch.cuda.is_available(); print('Thay GPU:', ok); ok and print('GPU chay duoc:', torch.cuda.get_device_name(0), float(torch.ones(2).cuda().sum()))"
if errorlevel 1 (
  echo LOI khi chay thu tren GPU. Chup man hinh gui lai cho Claude.
  pause
  exit /b 1
)
echo.
echo XONG. Thay "GPU chay duoc: ..." la Demucs se dung GPU. Mo lai start.bat.
pause
