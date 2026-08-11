@echo off
REM =============================================================================
REM  AI-CKP-008 :: 冷热恢复 save/load（native，破坏性）
REM  model = ckp-cold-warm  |  data_format = ckpt  |  容量 ~ 1 GiB
REM  执行方式 = python_scaled（Python 缩放兜底）  |  破坏性 = 是（破坏性，必须 --confirm-dut）  |  家族 = checkpoint（检查点）
REM  预期阻塞：破坏性；冷热恢复路径；必须 --confirm-dut
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

"%PY%" -m ai_ssd_test_cases.test_checkpoint_cold_warm_recovery ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --confirm-dut ^
    --scale-mb ^
    1024
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

