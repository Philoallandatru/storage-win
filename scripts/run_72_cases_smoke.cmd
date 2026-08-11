@echo off
REM ============================================================
REM  AI SSD 72-case batch runner (Windows / PowerShell-friendly)
REM
REM  Calls each per-case .cmd file in ai_ssd_test_cases\cmd\<family>\.
REM  Each per-case .cmd already sets PY, DUT, RES, and the right
REM  python module + flags.  Edit DUT and RES at the top of each
REM  per-case .cmd before running, or override them in this script.
REM
REM  Default mode: SMOKE_MODE=quick -> 1-2 representative cases per family
REM  Full mode:    SMOKE_MODE=full  -> all 72 cases
REM ============================================================

if "%SMOKE_MODE%"=="" set SMOKE_MODE=quick

set EXIT_ALL=0
set CMDROOT=ai_ssd_test_cases\cmd

call :run "%CMDROOT%\base\test_ai_base_001.cmd"
call :run "%CMDROOT%\base\test_ai_base_002.cmd"
if /I not "%SMOKE_MODE%"=="quick" (
    call :run "%CMDROOT%\base\test_ai_base_003.cmd"
    call :run "%CMDROOT%\base\test_ai_base_004.cmd"
)

call :run "%CMDROOT%\checkpoint\test_ai_ckp_001.cmd"
if /I not "%SMOKE_MODE%"=="quick" (
    call :run "%CMDROOT%\checkpoint\test_ai_ckp_008.cmd"
    call :run "%CMDROOT%\checkpoint\test_ai_ckp_009.cmd"
)

call :run "%CMDROOT%\kvcache\test_ai_kv_001.cmd"
call :run "%CMDROOT%\kvcache\test_ai_kv_004.cmd"
if /I not "%SMOKE_MODE%"=="quick" (
    call :run "%CMDROOT%\kvcache\test_ai_kv_013.cmd"
    call :run "%CMDROOT%\kvcache\test_ai_kv_022.cmd"
)

call :run "%CMDROOT%\training\test_ai_trn_006.cmd"
call :run "%CMDROOT%\training\test_ai_trn_016.cmd"
if /I not "%SMOKE_MODE%"=="quick" (
    call :run "%CMDROOT%\training\test_ai_trn_002.cmd"
    call :run "%CMDROOT%\training\test_ai_trn_008.cmd"
    call :run "%CMDROOT%\training\test_ai_trn_010.cmd"
    call :run "%CMDROOT%\training\test_ai_trn_012.cmd"
    call :run "%CMDROOT%\training\test_ai_trn_014.cmd"
)

call :run "%CMDROOT%\vectordb\test_ai_vdb_001.cmd"
call :run "%CMDROOT%\vectordb\test_ai_vdb_015.cmd"
if /I not "%SMOKE_MODE%"=="quick" (
    call :run "%CMDROOT%\vectordb\test_ai_vdb_002.cmd"
    call :run "%CMDROOT%\vectordb\test_ai_vdb_008.cmd"
    call :run "%CMDROOT%\vectordb\test_ai_vdb_012.cmd"
)

call :run "%CMDROOT%\mixed\test_ai_mix_001.cmd"
if /I not "%SMOKE_MODE%"=="quick" (
    call :run "%CMDROOT%\mixed\test_ai_mix_002.cmd"
    call :run "%CMDROOT%\mixed\test_ai_mix_005.cmd"
)

echo.
echo == summary: SMOKE_MODE=%SMOKE_MODE%  EXIT_ALL=%EXIT_ALL%
exit /b %EXIT_ALL%

:run
echo.
echo === %~1 ===
call %~1
if errorlevel 1 set EXIT_ALL=1
goto :eof
