@echo off
REM ============================================================
REM  AI-VDB-016  HNSW  - run this script directly
REM  DATA_DIR and RESULT_DIR must be on different filesystems (CAP-03)
REM ============================================================
setlocal

cd /d "%~dp0..\.."
set "REPO_ROOT=%CD%"
set "PY=%REPO_ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
set "PATH=%REPO_ROOT%\.venv\Scripts;%PATH%"

REM ---------- edit these two per machine (must be different drives) ----------
set "DATA_DIR=G:\MLPerfStorageTest\data\AI-VDB-016"
set "RESULT_DIR=D:\MLPerfStorageTest\results\AI-VDB-016"

REM ---------- dev: uncomment the two lines below to shrink the dataset ----------
REM set "NUM_FILES_TRAIN=8"
REM set "ALLOW_INVALID=1"

set "EXTRA="
if defined NUM_FILES_TRAIN set "EXTRA=%EXTRA% --num-files-train %NUM_FILES_TRAIN%"
if "%ALLOW_INVALID%"=="1" set "EXTRA=%EXTRA% --allow-invalid-params"

echo [%~n0] data-dir=%DATA_DIR%  results-dir=%RESULT_DIR%
"%PY%" -m full_test_plan_cases.run_case AI-VDB-016 --mode execute --data-dir "%DATA_DIR%" --results-dir "%RESULT_DIR%" --systemname ai-vdb-016 %EXTRA%
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
