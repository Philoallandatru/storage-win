@echo off
REM ==============================================================================
REM  AI-CKP-008 :: 冷/热恢复 (python_scaled)
REM  model = ckp-cold-warm  |  accelerator = *  |  data_format = ckpt  |  capacity ~ 1 GiB
REM  execution = python_scaled  |  destructive = True  |  family = checkpoint
REM  expected blocker: destructive + python_scaled; --confirm-dut + --scale-mb required
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

"%PY%" -m ai_ssd_test_cases.test_checkpoint_cold_warm_recovery ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --confirm-dut ^
    --scale-mb ^
    1024
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

