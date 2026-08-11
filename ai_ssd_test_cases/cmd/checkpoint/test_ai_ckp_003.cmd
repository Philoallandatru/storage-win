@echo off
REM =============================================================================
REM  AI-CKP-003 :: 70B 全量分布式 save/load（native，破坏性）
REM  model = llama3-70b  |  accelerator = A100  |  data_format = ckpt  |  容量 ~ 58368 GiB
REM  执行方式 = native（原生 mlpstorage 命令）  |  破坏性 = 是（破坏性，必须 --confirm-dut）  |  家族 = checkpoint（检查点）
REM  预期阻塞：破坏性；分布式；需要 1.2 TiB；必须 --confirm-dut
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

"%PY%" -m ai_ssd_test_cases.test_checkpoint_70b_full_distributed ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --confirm-dut
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

