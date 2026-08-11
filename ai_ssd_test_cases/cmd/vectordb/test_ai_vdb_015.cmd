@echo off
REM =============================================================================
REM  AI-VDB-015 :: 逻辑 trace 回放（trace）
REM  model = logical-trace-replay  |  data_format = vdb  |  容量 ~ 1 GiB
REM  执行方式 = trace（逻辑 trace 回放）  |  破坏性 = 否  |  家族 = vectordb（向量数据库）
REM  预期阻塞：回放 logical_io_smoke.csv；不需要 Milvus；带 --source-trace
REM
REM  跑之前编辑下面的 PY / DUT / RES。DUT 和 RES 必须在不同物理盘上，
REM  runner 会直接拒掉路径嵌套的情况。
REM =============================================================================
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

