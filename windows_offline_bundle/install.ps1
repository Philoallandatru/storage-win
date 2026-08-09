[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "MLPerfStorage")
)

$ErrorActionPreference = "Stop"
$bundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$payloadRoot = Join-Path $bundleRoot "payload"
$appRoot = Join-Path $InstallRoot "app"
$venvRoot = Join-Path $InstallRoot "venv"
$pythonRoot = Join-Path $InstallRoot "runtime\python"

if (-not (Test-Path -LiteralPath $payloadRoot -PathType Container)) {
    throw "Bundle payload not found: $payloadRoot"
}

New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $payloadRoot "app") -Destination $InstallRoot -Recurse -Force
Copy-Item -LiteralPath (Join-Path $payloadRoot "venv") -Destination $InstallRoot -Recurse -Force
Copy-Item -LiteralPath (Join-Path $payloadRoot "runtime") -Destination $InstallRoot -Recurse -Force
if (Test-Path -LiteralPath (Join-Path $payloadRoot "mpi")) {
    Copy-Item -LiteralPath (Join-Path $payloadRoot "mpi") -Destination $InstallRoot -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $bundleRoot "run.ps1") -Destination $InstallRoot -Force
Copy-Item -LiteralPath (Join-Path $bundleRoot "run.cmd") -Destination $InstallRoot -Force
if (Test-Path -LiteralPath (Join-Path $bundleRoot "verify_windows_benchmark_environment.ps1") -PathType Leaf) {
    Copy-Item -LiteralPath (Join-Path $bundleRoot "verify_windows_benchmark_environment.ps1") -Destination $InstallRoot -Force
}

$pyvenv = Join-Path $venvRoot "pyvenv.cfg"
@"
home = $pythonRoot
implementation = CPython
uv = bundled
version_info = 3.12.3
include-system-site-packages = false
"@ | Set-Content -LiteralPath $pyvenv -Encoding ascii

$placeholder = "__MLPERF_APP_ROOT__"
$finderFiles = Get-ChildItem -LiteralPath (Join-Path $venvRoot "Lib\site-packages") -Filter "__editable___*_finder.py" -File -ErrorAction SilentlyContinue
foreach ($finder in $finderFiles) {
    $content = Get-Content -LiteralPath $finder.FullName -Raw
    $escapedAppRoot = $appRoot.Replace("\", "\\")
    $content = $content.Replace($placeholder, $escapedAppRoot)
    Set-Content -LiteralPath $finder.FullName -Value $content -Encoding utf8 -NoNewline
}

$mpiCommand = Get-Command mpiexec -ErrorAction SilentlyContinue
if (-not $mpiCommand) {
    $mpiInstaller = Join-Path $InstallRoot "mpi\MSMpiSetup.exe"
    if (Test-Path -LiteralPath $mpiInstaller -PathType Leaf) {
        Write-Host "Microsoft MPI is not installed. Starting the bundled installer..."
        Start-Process -FilePath $mpiInstaller -Wait -Verb RunAs
        $mpiCommand = Get-Command mpiexec -ErrorAction SilentlyContinue
    }
}
if (-not $mpiCommand) {
    Write-Warning "mpiexec was not found. Training/checkpointing/KV execution will require Microsoft MPI."
}

$python = Join-Path $venvRoot "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Bundled Python was not installed correctly: $python"
}

$state = [ordered]@{
    install_root = $InstallRoot
    app_root = $appRoot
    python = $python
    python_version = (& $python --version 2>&1 | Out-String).Trim()
    installed_at = (Get-Date).ToString("o")
}
$state | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $InstallRoot "install-state.json") -Encoding utf8

Write-Host "MLPerf Storage installed at $InstallRoot"
Write-Host "Run preflight with: $InstallRoot\run.ps1 -Case AI-TRN-003 -Mode preflight"
