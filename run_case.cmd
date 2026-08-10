@echo off
setlocal
set "REPO_ROOT=%~dp0"
set "PYTHON=%REPO_ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo ERROR: Python environment not found: "%PYTHON%" 1>&2
  echo Run the Windows environment installation first. 1>&2
  exit /b 2
)

set "PATH=%REPO_ROOT%.venv\Scripts;%PATH%"
"%PYTHON%" -m full_test_plan_cases.run_case %*
exit /b %ERRORLEVEL%
