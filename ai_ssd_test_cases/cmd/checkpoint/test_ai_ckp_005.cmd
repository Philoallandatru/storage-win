@echo off
REM ==============================================================================
REM  AI-CKP-005 :: 405B full shared (native)
REM  model = llama3-405b  |  accelerator = A100  |  data_format = ckpt  |  capacity ~ 57344 GiB
REM  execution = native  |  destructive = True  |  family = checkpoint
REM  expected blocker: destructive: needs 56 TiB on DUT; --confirm-dut required
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

REM --- ensure the result dir has mlpstorage init metadata (idempotent) ---
    mlpstorage init "AI-SSD-Test" "%RES%" 1>nul 2>&1

"%PY%" -m ai_ssd_test_cases.test_checkpoint_405b_full_shared ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --confirm-dut
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

