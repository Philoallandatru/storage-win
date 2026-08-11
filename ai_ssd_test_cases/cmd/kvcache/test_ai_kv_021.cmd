@echo off
REM ==============================================================================
REM  AI-KV-021 :: tier2 trace 回放 (python_scaled)
REM  model = tier2-trace-replay  |  accelerator = *  |  data_format = kv  |  capacity ~ 1 GiB
REM  execution = python_scaled  |  destructive = False  |  family = kvcache
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

"%PY%" -m ai_ssd_test_cases.test_kv_tier2_trace_replay ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --scale-mb ^
    1024
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

