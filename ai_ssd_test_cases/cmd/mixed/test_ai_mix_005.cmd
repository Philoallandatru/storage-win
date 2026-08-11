@echo off
REM =============================================================================
REM  AI-MIX-005 :: 4 类 fill/GC 8 小时 soak（python_scaled，破坏性）
REM  model = four-class-soak  |  容量 ~ 50 GiB
REM  执行方式 = python_scaled（Python 缩放兜底）  |  破坏性 = 是（破坏性，必须 --confirm-dut）  |  家族 = mixed（混合负载）
REM  预期阻塞：破坏性；长跑约 8 小时；必须 --confirm-dut + --scale-mb
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

"%PY%" -m ai_ssd_test_cases.test_mixed_four_class_soak ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --scale-mb ^
    512 ^
    --confirm-dut
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%
