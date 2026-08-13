@echo off
REM setup_env.cmd — source MSVC env then run a command (default: uv sync).
REM
REM Use:
REM   setup_env.cmd                 :: uv sync
REM   setup_env.cmd uv lock         :: any uv subcommand
REM   setup_env.cmd pytest tests    :: any command
REM
REM Why: dgen-py (and s3dlio) ship Linux-only wheels, so on Windows uv has
REM to compile them from sdist via cargo, which needs MSVC's link.exe.
REM VS 2022 BuildTools at
REM   C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools
REM has the toolset; we source its vcvars64.bat to put link.exe / cl.exe
REM plus the Windows SDK on PATH along with all the INCLUDE / LIB dirs.
REM
REM If the path below changes, edit VCVARS.

setlocal

set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%VCVARS%" (
    echo ERROR: vcvars64.bat not found at "%VCVARS%" 1>&2
    echo Adjust the VCVARS path in setup_env.cmd to match your VS install. 1>&2
    exit /b 1
)

REM If no args were passed, default to `uv sync` for convenience.
if "%~1"=="" (
    call "%VCVARS%" >nul
    if errorlevel 1 ( echo vcvars64.bat failed & exit /b 1 )
    pushd "%~dp0"
    uv sync %UV_SYNC_EXTRA%
    set "RC=%ERRORLEVEL%"
    popd
    exit /b %RC%
)

REM Otherwise run whatever the caller passed, with MSVC env active.
call "%VCVARS%" >nul
if errorlevel 1 ( echo vcvars64.bat failed & exit /b 1 )
%*
exit /b %ERRORLEVEL%
