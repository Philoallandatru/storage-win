@echo off
REM ==============================================================================
REM  AI-VDB-015 :: 逻辑 trace 回放 (trace)
REM  model = logical-trace-replay  |  accelerator = *  |  data_format = vdb  |  capacity ~ 1 GiB
REM  execution = trace  |  destructive = False  |  family = vectordb
REM  expected blocker: trace: replay logical_io_smoke.csv (default source)
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

"%PY%" -m ai_ssd_test_cases.test_vdb_logical_trace_replay ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --source-trace ^
    "C:\Users\Administrator\Documents\Code\repos\storage\full_test_plan_cases\fixtures\logical_io_smoke.csv"
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

