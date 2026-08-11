@echo off
REM ==============================================================================
REM  AI-BASE-004 :: Fill-level / GC degradation (python_base, DESTRUCTIVE)
REM  model = fill-level-degradation  |  capacity ~ 200 GiB (fill to 90%)
REM  execution = python_base  |  destructive = True   |  family = BASE
REM  expected blocker: destructive; --confirm-dut required; fill DUT 20-90%
REM                    --scale-mb required for fill_degradation profile
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

"%PY%" -m ai_ssd_test_cases.test_base_fill_level_degradation ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --confirm-dut ^
    --scale-mb ^
    512
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%
