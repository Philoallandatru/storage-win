@echo off
REM ==============================================================================
REM  AI-TRN-006 :: CosmoFlow A100 TFRecord (python_scaled)
REM  model = cosmoflow  |  accelerator = A100  |  data_format = tfrecord  |  capacity ~ 1 GiB
REM  execution = python_scaled  |  destructive = False  |  family = training
REM  expected blocker: python_scaled fallback; --scale-mb required
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

"%PY%" -m ai_ssd_test_cases.test_ai_trn_006_cosmoflow_a100_tfrecord ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --scale-mb ^
    1024
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

