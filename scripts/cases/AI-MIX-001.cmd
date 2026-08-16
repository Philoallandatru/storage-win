@echo off
REM ============================================================
REM  AI-MIX-001  KV Cache (C:) + VectorDB (E:) concurrent  - run this script directly
REM  DATA_DIR and RESULT_DIR must be on different filesystems (CAP-03)
REM  (capacity variants default both to G: - run_case bypasses CAP-03)
REM ============================================================
setlocal

cd /d "%~dp0..\.."
set "REPO_ROOT=%CD%"
set "PY=%REPO_ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
set "PATH=%REPO_ROOT%\.venv\Scripts;%PATH%"

REM ---------- data/results location (default: C: drive; edit for other drives) ----------
REM   Data and results are on the SAME drive by default (SINGLE_DRIVE=1 below).
REM   To use two drives, edit both paths AND set SINGLE_DRIVE=0.
set "DATA_DIR=C:\MLPerfStorageTest\data\AI-MIX-001"
set "RESULT_DIR=C:\MLPerfStorageTest\results\AI-MIX-001"

set "VDB_DATA_DIR=E:\MLPerfStorageTest\data\AI-MIX-001"

REM ---------- 1 = data and results share one drive (C:-only machine) ----------
set "SINGLE_DRIVE=1"
set "GATE="
if "%SINGLE_DRIVE%"=="1" set "GATE=--skip-fs-separation-gate"

echo [%~n0] data-dir=%DATA_DIR%  results-dir=%RESULT_DIR%
"%PY%" -m full_test_plan_cases.run_case AI-MIX-001 --mode execute --data-dir "%DATA_DIR%" --results-dir "%RESULT_DIR%" --systemname ai-mix-001 --num-users 10 --num-vectors 1000 --duration-sec 10 --generation-mode fast --vdb-config %REPO_ROOT%\full_test_plan_cases\configs\vdb_smoke.yaml --milvus-uri %VDB_DATA_DIR%\milvus_lite.db --mix-vdb-data-dir %VDB_DATA_DIR% %GATE%
set "RC=%ERRORLEVEL%"

REM ---------- generic data cleanup (set CLEANUP=0 to keep data) ----------
if "%CLEANUP%"=="0" goto :skip_cleanup
echo "%DATA_DIR%" | findstr /i /c:"%~n0" >nul
if errorlevel 1 (
  echo [%~n0] CLEANUP_SKIPPED: DATA_DIR does not contain case id, refusing to delete: "%DATA_DIR%"
  goto :skip_cleanup
)
if exist "%DATA_DIR%" (
  echo [%~n0] cleaning data: %DATA_DIR%
  rmdir /s /q "%DATA_DIR%" 2>nul
  echo [%~n0] DATA_CLEANED
)
:skip_cleanup
endlocal & exit /b %RC%
