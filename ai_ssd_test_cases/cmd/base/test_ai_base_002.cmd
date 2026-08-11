@echo off
REM ==============================================================================
REM  AI-BASE-002 :: Cache-path modes (cached / buffered / direct) (python_base)
REM  model = cache-path-modes  |  capacity ~ 1 GiB
REM  execution = python_base  |  destructive = False  |  family = BASE
REM  expected blocker: requires a real SSD; python_base fallback uses local cache
REM                    --scale-mb required for cache_modes profile
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

"%PY%" -m ai_ssd_test_cases.test_base_cache_path_modes ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --scale-mb ^
    512
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%
