@echo off
REM =============================================================================
REM  AI-BASE-003 :: 重复性 vs 监控开销（python_base）
REM  model = repeatability-monitor  |  容量 ~ 1 GiB
REM  执行方式 = python_base（Python 基础 workload）  |  破坏性 = 否  |  家族 = BASE（基础环境）
REM  预期阻塞：3 次重复 + 监控开关；repeatability profile；必须带 --scale-mb
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

"%PY%" -m ai_ssd_test_cases.test_base_repeatability_monitor_overhead ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --scale-mb ^
    512
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%
