@echo off
REM ==============================================================================
REM  AI-TRN-016 :: warm/cold/direct 三路对比 (python_scaled)
REM  model = warm-cold-direct  |  accelerator = *  |  data_format = mixed  |  capacity ~ 1 GiB
REM  execution = python_scaled  |  destructive = False  |  family = training
REM  expected blocker: python_scaled single-point; warm/cold/direct sweep not reproduced
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

"%PY%" -m ai_ssd_test_cases.test_ai_trn_016_warm_cold_direct ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --scale-mb ^
    1024
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

