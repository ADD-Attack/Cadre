@echo off
REM ============================================================
REM  Builds "Muse Relay.exe" and puts it on your Desktop.
REM
REM  Before running: put this file, muse_relay_app.py, and
REM  muse.ico in the SAME folder (your Downloads folder works).
REM  Then double-click this file. It takes a few minutes.
REM ============================================================

cd /d %~dp0

echo Installing build tools and app dependencies...
python -m pip install --upgrade pyinstaller flask pyautogui pillow waitress
if errorlevel 1 goto :fail

echo Building Muse Relay.exe ...
if exist muse.ico (
    python -m PyInstaller --onefile --noconsole --name "Muse Relay" --icon muse.ico --add-data "muse.ico;." muse_relay_app.py
) else (
    echo (muse.ico not found next to this file - building without a custom icon)
    python -m PyInstaller --onefile --noconsole --name "Muse Relay" muse_relay_app.py
)
if errorlevel 1 goto :fail

copy /Y "dist\Muse Relay.exe" "%USERPROFILE%\Desktop\Muse Relay.exe" >nul

echo.
echo Done. "Muse Relay.exe" is on your Desktop.
echo Double-click it to start a session - no more terminals.
echo You can delete the old "Muse Relay" shortcut and the .bat files.
pause
exit /b 0

:fail
echo.
echo Something failed - take a screenshot of this window and send it to Muse.
pause
exit /b 1
