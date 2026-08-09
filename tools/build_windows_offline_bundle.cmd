@echo off
setlocal

echo Building the MLPerf Storage Windows offline ZIP...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0prepare_windows_offline_bundle.ps1" %*
set "exit_code=%ERRORLEVEL%"

if not "%exit_code%"=="0" (
    echo.
    echo Build failed with exit code %exit_code%.
) else (
    echo.
    echo Build completed.
)
pause
exit /b %exit_code%
