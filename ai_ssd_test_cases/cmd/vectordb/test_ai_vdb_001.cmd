@echo off
REM ==============================================================================
REM  AI-VDB-001 :: 1K HNSW Windows smoke (native)
REM  model = hnsw-1k-smoke  |  accelerator = *  |  data_format = vdb  |  capacity ~ 1 GiB
REM  execution = native  |  destructive = False  |  family = vectordb
REM  expected blocker: native: mlpstorage open vectordb hnsw search file (1K smoke)
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

"%PY%" -m ai_ssd_test_cases.test_vdb_hnsw_1k_smoke ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

