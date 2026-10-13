@echo off
title Muse Relay v2 Launcher
setlocal
set ROOT=%USERPROFILE%\muse-relay-v2

rem Read the hands session secret from the existing relay script, so the
rem gateway pairs with the hands that are already running. The secret
rem itself is never stored in this file.
set HANDS_SECRET=
for /f "tokens=3 delims=' " %%a in ('findstr /c:"SHARED_SECRET =" "%USERPROFILE%\Downloads\cursor_relay.py"') do set HANDS_SECRET=%%a
if "%HANDS_SECRET%"=="" (
  echo Could not read the hands secret from Downloads\cursor_relay.py.
  echo Make sure the hands are set up first. This window will close.
  pause
  exit /b 1
)

rem Fresh gateway token for this launch only. It is printed at the top
rem of the gateway window; it is not saved anywhere.
powershell -NoProfile -Command "[guid]::NewGuid().ToString('N')" > "%TEMP%\muse-v2-token.txt"
set /p GATEWAY_TOKEN=<"%TEMP%\muse-v2-token.txt"
del "%TEMP%\muse-v2-token.txt" >nul 2>&1

start "Muse Relay v2 - Parser (port 5011)" cmd /k "cd /d %ROOT%\services\parser && python app.py"
start "Muse Relay v2 - Gateway (port 5010)" cmd /k "cd /d %ROOT%\services\gateway && set RELAY_GATEWAY_TOKEN=%GATEWAY_TOKEN% && set HANDS_URL=http://127.0.0.1:5000 && set HANDS_SECRET=%HANDS_SECRET% && set PARSER_URL=http://127.0.0.1:5011 && echo Gateway token for this launch: %GATEWAY_TOKEN% && python app.py"

echo.
echo Muse Relay v2 starting: parser on port 5011, gateway on port 5010.
echo The hands must also be running (use the Muse Relay desktop icon).
echo If a service window shows "address already in use", that service was
echo already running - just close the duplicate window.
echo This launcher window will close in 8 seconds.
timeout /t 8 >nul
endlocal
