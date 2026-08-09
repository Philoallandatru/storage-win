[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$PythonIndexUrl = "https://pypi.tuna.tsinghua.edu.cn/simple",
    [switch]$RecreateVenv,
    [switch]$UpdateLock
)

$ErrorActionPreference = "Stop"
$repoPath = [IO.Path]::GetFullPath($RepoRoot)
$venvPath = Join-Path $repoPath ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$kvCacheProject = Join-Path $repoPath "kv_cache_benchmark"
$vdbProject = Join-Path $repoPath "vdb_benchmark"

if ($PythonIndexUrl) {
    $env:UV_INDEX_URL = $PythonIndexUrl
    Write-Host "Python package index: $PythonIndexUrl"
}

$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCommand) {
    throw "uv was not found. Install it on the online build machine, then rerun this script."
}
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $systemPythonVersion = (& $pythonCommand.Source --version 2>&1 | Out-String).Trim()
    Write-Host "System Python: $systemPythonVersion (uv will select the repository venv interpreter)"
}

if ($RecreateVenv -and (Test-Path -LiteralPath $venvPath)) {
    $resolvedVenv = (Resolve-Path -LiteralPath $venvPath).Path
    if ($resolvedVenv -ne [IO.Path]::GetFullPath($venvPath)) {
        throw "Refusing to remove an unexpected venv path: $resolvedVenv"
    }
    Remove-Item -LiteralPath $venvPath -Recurse -Force
}

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    Write-Host "Creating .venv with Python 3.12.3"
    & $uvCommand.Source venv --python 3.12.3 $venvPath
    if ($LASTEXITCODE -ne 0) { throw "uv venv failed with exit code $LASTEXITCODE" }
}

$venvVersion = (& $venvPython --version 2>&1 | Out-String).Trim()
if ($venvVersion -notmatch "Python 3\.12\.") {
    throw "The existing .venv is not Python 3.12.x: $venvVersion. Use -RecreateVenv."
}

Push-Location $repoPath
try {
    if ($UpdateLock) {
        Write-Host "Updating uv.lock"
        & $uvCommand.Source lock
        if ($LASTEXITCODE -ne 0) { throw "uv lock failed with exit code $LASTEXITCODE" }
    }
    Write-Host "Syncing the root project from uv.lock"
    & $uvCommand.Source sync --frozen --all-groups --extra test --extra vectordb
    if ($LASTEXITCODE -ne 0) { throw "uv sync failed with exit code $LASTEXITCODE" }

    foreach ($project in @($kvCacheProject, $vdbProject)) {
        if (Test-Path -LiteralPath (Join-Path $project "pyproject.toml")) {
            Write-Host "Installing editable local project: $project"
            $pipArgs = @("pip", "install", "--python", $venvPython)
            if ($PythonIndexUrl) { $pipArgs += @("--index-url", $PythonIndexUrl) }
            $pipArgs += @("--editable", $project)
            & $uvCommand.Source @pipArgs
            if ($LASTEXITCODE -ne 0) { throw "Editable install failed for $project" }
        }
    }
} finally {
    Pop-Location
}

& $venvPython -c "import mlpstorage_py; print('mlpstorage_py=' + mlpstorage_py.__file__)"
if ($LASTEXITCODE -ne 0) { throw "mlpstorage_py import failed" }
& $venvPython -c "import dlio_benchmark; print('dlio_benchmark=' + dlio_benchmark.__file__)"
if ($LASTEXITCODE -ne 0) { throw "dlio_benchmark import failed" }
Write-Host "Build environment is ready. Dot-source tools\activate_windows_venv.ps1 before running commands."
