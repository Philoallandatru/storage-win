@echo off
REM ==============================================================================
REM  AI-KV-005 :: Mistral 7B GQA (native)
REM  model = mistral7b-gqa  |  accelerator = A100  |  data_format = kv  |  capacity ~ 1 GiB
REM  execution = native  |  destructive = False  |  family = kvcache
REM  expected blocker: native: mlpstorage open kvcache mistral-7b run
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

"%PY%" -m ai_ssd_test_cases.test_kv_mistral7b_gqa ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

