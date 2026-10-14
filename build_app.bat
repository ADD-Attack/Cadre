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

rem pyautogui drives the bundled hands; PyInstaller must be able to see it.
python -c "import pyautogui" 2>nul
if errorlevel 1 (
  echo Installing pyautogui...
  python -m pip install pyautogui
  if errorlevel 1 (
    echo pyautogui install failed. This window will close.
    pause
    exit /b 1
  )
)

rem The app loads the three service modules from files at runtime, so
rem bundle them inside the exe: hands, gateway, and parser. The exe then
rem runs standalone from any folder — one icon, one Start button.
python -m PyInstaller --onefile --windowed --name "Muse Relay v2" --icon muse-avatar.ico --hidden-import pyautogui --add-data "muse-avatar.ico;." --add-data "services\gateway\app.py;services\gateway" --add-data "services\parser\app.py;services\parser" --add-data "hands\muse_relay_hands.py;hands" muse_relay_v2_app.py
if errorlevel 1 (
  echo Build failed. This window will close.
  pause
  exit /b 1
)

copy /Y "dist\Muse Relay v2.exe" "Muse Relay v2.exe" >nul
echo.
echo Built: %CD%\Muse Relay v2.exe
