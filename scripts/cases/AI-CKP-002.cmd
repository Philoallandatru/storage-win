@echo off
REM ============================================================
REM  AI-CKP-002  Llama3-70B 8-rank subset  - run this script directly
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
set "DATA_DIR=C:\MLPerfStorageTest\data\AI-CKP-002"
set "RESULT_DIR=C:\MLPerfStorageTest\results\AI-CKP-002"

REM ---------- 1 = data and results share one drive (C:-only machine) ----------
set "SINGLE_DRIVE=1"
set "GATE="
if "%SINGLE_DRIVE%"=="1" set "GATE=--skip-fs-separation-gate"

echo [%~n0] data-dir=%DATA_DIR%  results-dir=%RESULT_DIR%
"%PY%" -m full_test_plan_cases.run_case AI-CKP-002 --mode execute --data-dir "%DATA_DIR%" --results-dir "%RESULT_DIR%" --systemname ai-ckp-002 --num-processes 8 --allow-invalid-params --num-checkpoints-write 1 --num-checkpoints-read 1 --client-memory-gb 64 %GATE%
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
