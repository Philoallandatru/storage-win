@echo off
REM =============================================================================
REM  AI-CKP-004 :: 405B 子集 save/load（native，破坏性）
REM  model = llama3-405b  |  accelerator = A100  |  data_format = ckpt  |  容量 ~ 4224 GiB
REM  执行方式 = native（原生 mlpstorage 命令）  |  破坏性 = 是（破坏性，必须 --confirm-dut）  |  家族 = checkpoint（检查点）
REM  预期阻塞：破坏性；需要 5.4 TiB；必须 --confirm-dut
REM
REM  跑之前编辑下面的 PY / DUT / RES。DUT 和 RES 必须在不同物理盘上，
REM  runner 会直接拒掉路径嵌套的情况。
REM =============================================================================
setlocal

REM ============================================================================
REM  环境变量（用环境变量覆盖，不要改这里）
REM
REM    PY  - python 可执行文件路径；不设则自动探测 .venv\Scripts\python.exe，
REM          找不到回退到 PATH 上的 python
REM    DUT - 数据盘根目录（必须存在且可写）
REM    RES - 结果目录（必须与 DUT 在不同物理盘；runner 会自动校验）
REM
REM  跑之前：
REM    set PY=C:\path\to\python.exe         :: 可选
REM    set DUT=E:\big-ssd\data               :: 必填
REM    set RES=D:\results                      :: 必填
REM    ai_ssd_test_cases\cmd\checkpoint\test_ai_ckp_004.cmd
REM ============================================================================

REM --- 切到仓库根，借 pushd 解析 .. 路径 ---
pushd "%~dp0..\..\.." >nul
set "REPO_ROOT=%CD%"
if not defined PY  set "PY=%REPO_ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
if not defined DUT (
    echo [错误] 环境变量 DUT 未设置。请先 set DUT=E:\path\to\data
    popd >nul
    exit /b 2
)
if not defined RES (
    echo [错误] 环境变量 RES 未设置。请先 set RES=D:\path\to\results
    popd >nul
    exit /b 2
)
if not exist "%DUT%" (
    echo [错误] DUT 目录不存在：%DUT%
    popd >nul
    exit /b 2
)
if not exist "%RES%" (
    echo [信息] RES 目录不存在，自动创建：%RES%
    mkdir "%RES%" 2>nul
)

set "PATH=%REPO_ROOT%\.venv\Scripts;%PATH%"


REM --- ensure the result dir has mlpstorage init metadata (idempotent) ---
    mlpstorage init "AI-SSD-Test" "%RES%" 1>nul 2>&1

"%PY%" -m ai_ssd_test_cases.test_checkpoint_405b_subset ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --confirm-dut
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

