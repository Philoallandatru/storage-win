@echo off
REM =============================================================================
REM  AI-TRN-001 :: UNet3D A100 多文件训练（native_special）
REM  model = unet3d  |  accelerator = A100  |  data_format = npz  |  容量 ~ 983 GiB
REM  执行方式 = native_special（特殊路径原生命令）  |  破坏性 = 否  |  家族 = training（训练）
REM  预期阻塞：需要 DUT 上有 983 GiB 空间；需先 mlpstorage init + native datagen
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

"%PY%" -m ai_ssd_test_cases.test_ai_trn_001_unet3d_a100 ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

