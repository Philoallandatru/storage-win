@echo off
REM ==============================================================================
REM  AI-MIX-005 :: 4-class fill/GC 8h soak (python_scaled, DESTRUCTIVE)
REM  model = four-class-soak  |  capacity ~ 50 GiB (8h loop)
REM  execution = python_scaled  |  destructive = True   |  family = Mixed
REM  expected blocker: --scale-mb + --confirm-dut required; long-running (~8h)
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

"%PY%" -m ai_ssd_test_cases.test_mixed_four_class_soak ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --scale-mb ^
    512 ^
    --confirm-dut
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%
