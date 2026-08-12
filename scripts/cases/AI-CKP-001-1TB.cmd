@echo off
REM ============================================================
REM  AI-CKP-001-1TB  capacity  - run this script directly
REM  DATA_DIR and RESULT_DIR must be on different filesystems (CAP-03)
REM  (capacity variants default both to G: - run_case bypasses CAP-03)
REM ============================================================
setlocal

cd /d "%~dp0..\.."
set "REPO_ROOT=%CD%"
set "PY=%REPO_ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
set "PATH=%REPO_ROOT%\.venv\Scripts;%PATH%"

REM ---------- edit these two per machine (must be different drives) ----------
set "DATA_DIR=G:\MLPerfStorageTest\data\AI-CKP-001-1TB"
set "RESULT_DIR=G:\MLPerfStorageTest\results\AI-CKP-001-1TB"

REM ---------- dev: uncomment the two lines below to shrink the dataset ----------
REM set "NUM_FILES_TRAIN=8"
REM set "ALLOW_INVALID=1"

set "EXTRA="
if defined NUM_FILES_TRAIN set "EXTRA=%EXTRA% --num-files-train %NUM_FILES_TRAIN%"
if "%ALLOW_INVALID%"=="1" set "EXTRA=%EXTRA% --allow-invalid-params"

echo [%~n0] data-dir=%DATA_DIR%  results-dir=%RESULT_DIR%
"%PY%" -m full_test_plan_cases.run_case AI-CKP-001-1TB --mode execute --data-dir "%DATA_DIR%" --results-dir "%RESULT_DIR%" --systemname ai-ckp-001-1tb %EXTRA%
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
