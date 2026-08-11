@echo off
REM ==============================================================================
REM  AI-TRN-005 :: RetinaNet MI355 JPEG 训练 (native)
REM  model = retinanet  |  accelerator = MI355  |  data_format = jpeg  |  capacity ~ 351.6 GiB
REM  execution = native  |  destructive = False  |  family = training
REM  expected blocker: needs ~352 GiB on DUT; MI355 driver not on host
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

"%PY%" -m ai_ssd_test_cases.test_ai_trn_005_retinanet_mi355_jpeg ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

