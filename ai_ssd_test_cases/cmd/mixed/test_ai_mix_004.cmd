@echo off
REM ==============================================================================
REM  AI-MIX-004 :: KV interactive + VectorDB search concurrency (python_scaled, DESTRUCTIVE)
REM  model = kv-interactive-vdb-search  |  capacity ~ 1 GiB
REM  execution = python_scaled  |  destructive = True   |  family = Mixed
REM  expected blocker: --scale-mb + --confirm-dut required; VDB needs Milvus or lite
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

"%PY%" -m ai_ssd_test_cases.test_mixed_kv_interactive_vdb_search ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --scale-mb ^
    512 ^
    --confirm-dut
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%
