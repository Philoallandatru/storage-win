@echo off
REM ==============================================================================
REM  AI-BASE-003 :: Repeatability vs monitoring overhead (python_base)
REM  model = repeatability-monitor  |  capacity ~ 1 GiB
REM  execution = python_base  |  destructive = False  |  family = BASE
REM  expected blocker: 3 runs + monitor on/off; python_base uses synthetic I/O
REM                    --scale-mb required for repeatability profile
REM
REM  Edit PY / DUT / RES below before running.  DUT and RES must live on
REM  different physical disks so the runner can reject overlapping paths.
REM ==============================================================================

setlocal
set "PY=C:\Users\Administrator\Documents\Code\repos\storage\.venv\Scripts\python.exe"
set "DUT=G:\ai-ssd\data"
set "RES=D:\ai-ssd\results"
set "PATH=C:\Users\Administrator\Documents\Code\repos\storage\.venv\Scripts;%PATH%"

REM --- move to repo root so `python -m ...` resolves ---
pushd "%~dp0..\..\..\.." >nul

"%PY%" -m ai_ssd_test_cases.test_base_repeatability_monitor_overhead ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --scale-mb ^
    512
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%
