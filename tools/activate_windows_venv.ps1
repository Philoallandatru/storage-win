[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$SystemName = "windows-offline-build"
)

$ErrorActionPreference = "Stop"
$repoPath = [IO.Path]::GetFullPath($RepoRoot)
$venvPath = Join-Path $repoPath ".venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "The repository venv is missing: $venvPath. Run setup_windows_build_env.ps1 first."
}

$env:VIRTUAL_ENV = $venvPath
$env:Path = (Join-Path $venvPath "Scripts") + ";" + $env:Path
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:MLPERF_SYSTEMNAME = $SystemName

Write-Host "Activated MLPerf Storage venv: $venvPath"
Write-Host "Python: $(& $pythonPath --version 2>&1)"
Write-Host "MLPERF_SYSTEMNAME: $env:MLPERF_SYSTEMNAME"
