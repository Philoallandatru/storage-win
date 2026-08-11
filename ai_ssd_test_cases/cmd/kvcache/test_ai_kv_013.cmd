@echo off
REM =============================================================================
REM  AI-KV-013 :: Tier 容量矩阵（python_scaled）
REM  model = tier-capacity  |  data_format = kv  |  容量 ~ 1 GiB
REM  执行方式 = python_scaled（Python 缩放兜底）  |  破坏性 = 否  |  家族 = KV Cache
REM  预期阻塞：python_scaled；必须带 --scale-mb
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
REM    ai_ssd_test_cases\cmd\kvcache\test_ai_kv_013.cmd
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


"%PY%" -m ai_ssd_test_cases.test_kv_tier_capacity_matrix ^
    --data-dir "%DUT%" ^
    --result-dir "%RES%" ^
    --execute ^
    --scale-mb ^
    1024
set RC=%ERRORLEVEL%

popd >nul
endlocal & exit /b %RC%

