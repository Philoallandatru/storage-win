@echo off
REM =============================================================================
REM  AI-TRN-005 :: RetinaNet MI355 JPEG 训练（native）
REM  model = retinanet  |  accelerator = MI355  |  data_format = jpeg  |  容量 ~ 351.6
REM  执行方式 = native（原生 mlpstorage 命令）  |  破坏性 = 否  |  家族 = training（训练）
REM  预期阻塞：需要 DUT 上有 352 GiB 空间（与 004 同数据集，MI355 节奏）
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

REM --- ensure the result dir has mlpstorage init metadata (idempotent) ---
    mlpstorage init "AI-SSD-Test" "%RES%" 1>nul 2>&1

"%PY%" -m ai_ssd_test_cases.test_ai_trn_005_retinanet_mi355_jpeg ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

