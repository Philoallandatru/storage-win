@echo off
REM ==============================================================================
REM  AI-TRN-003 :: UNet3D B200 大规模训练 (native)
REM  model = unet3d  |  accelerator = B200  |  data_format = npz  |  capacity ~ 983 GiB
REM  execution = native  |  destructive = False  |  family = training
REM  expected blocker: needs 983 GiB on DUT (CAP-01 will fail with current G: 389 GiB free)
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

"%PY%" -m ai_ssd_test_cases.test_ai_trn_003_unet3d_b200 ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

