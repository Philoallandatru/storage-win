@echo off
REM =============================================================================
REM  AI-BASE-001 :: DUT 路径与容量可追溯（python_base）
REM  model = dut-path-capacity  |  容量 ~ 1 GiB
REM  执行方式 = python_base（Python 基础 workload）  |  破坏性 = 否  |  家族 = BASE（基础环境）
REM  预期阻塞：需要真实 SSD；python_base 走本地缓存目录
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

"%PY%" -m ai_ssd_test_cases.test_base_dut_path_capacity ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%
