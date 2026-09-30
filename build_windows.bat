@echo off
setlocal
cd /d %~dp0

if not exist .venv (
  py -3.12 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-build.txt
pytest
pyinstaller --noconfirm --clean sambo_photo_studio.spec

echo.
echo Build complete: dist\삼보사진관.exe
pause
