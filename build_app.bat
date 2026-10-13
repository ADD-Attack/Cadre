@echo off
title Build Muse Relay v2 App
cd /d %~dp0

rem Install PyInstaller if it is not there yet.
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
  echo Installing PyInstaller...
  python -m pip install pyinstaller
  if errorlevel 1 (
    echo PyInstaller install failed. This window will close.
    pause
    exit /b 1
  )
)

python -m PyInstaller --onefile --windowed --name "Muse Relay v2" --icon muse-avatar.ico --add-data "muse-avatar.ico;." muse_relay_v2_app.py
if errorlevel 1 (
  echo Build failed. This window will close.
  pause
  exit /b 1
)

copy /Y "dist\Muse Relay v2.exe" "Muse Relay v2.exe" >nul
echo.
echo Built: %CD%\Muse Relay v2.exe
