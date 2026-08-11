@echo off
REM ==============================================================================
REM  AI-BASE-001 :: DUT path & capacity traceability (python_base, non-destructive)
REM  model = dut-path-capacity  |  capacity ~ 1 GiB
REM  execution = python_base  |  destructive = False  |  family = BASE
REM  expected blocker: needs `mlpstorage init` to exist under RES for some
REM                    metadata writes; python_base fallback otherwise
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

"%PY%" -m ai_ssd_test_cases.test_base_dut_path_capacity ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%
