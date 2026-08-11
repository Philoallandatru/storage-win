@echo off
REM =============================================================================
REM  AI-TRN-015 :: 读线程饱和度（python_scaled）
REM  model = read-threads-saturation  |  data_format = mixed  |  容量 ~ 1 GiB
REM  执行方式 = python_scaled（Python 缩放兜底）  |  破坏性 = 否  |  家族 = training（训练）
REM  预期阻塞：python_scaled 兜底；必须带 --scale-mb
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

"%PY%" -m ai_ssd_test_cases.test_ai_trn_015_read_threads_saturation ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --scale-mb ^
    1024
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

