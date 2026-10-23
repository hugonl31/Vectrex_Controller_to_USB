@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Adapter.ps1" -Action Flash %*
set "adapterResult=%errorlevel%"
pause
exit /b %adapterResult%
