[CmdletBinding()]
param(
    [Alias("Destination")]
    [string]$Output = "E:\MLPerfStorage-Windows-Offline.zip",
    [string]$MpiVersion = "v10.1.1",
    [string]$MpiDirectory = "",
    [string]$PythonIndexUrl = "https://pypi.tuna.tsinghua.edu.cn/simple",
    [switch]$SkipMpiDownload,
    [switch]$InstallMpiRuntime,
    [switch]$InstallMpiSdk,
    [switch]$RecreateVenv,
    [switch]$UpdateLock
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $MpiDirectory) {
    $MpiDirectory = Join-Path $repoRoot ".artifacts\msmpi"
}
$mpiDirectoryPath = [IO.Path]::GetFullPath($MpiDirectory)
$mpiInstaller = Join-Path $mpiDirectoryPath "msmpisetup.exe"

if (-not $SkipMpiDownload) {
    $downloadArgs = @(
        "-Version", $MpiVersion,
        "-Destination", $mpiDirectoryPath
    )
    if ($InstallMpiRuntime) { $downloadArgs += "-InstallRuntime" }
    if ($InstallMpiSdk) { $downloadArgs += "-InstallSdk" }
    & (Join-Path $PSScriptRoot "download_msmpi.ps1") @downloadArgs
    if ($LASTEXITCODE -ne 0) { throw "MPI download failed with exit code $LASTEXITCODE" }
}
if (-not (Test-Path -LiteralPath $mpiInstaller -PathType Leaf)) {
    throw "MS-MPI runtime installer was not found: $mpiInstaller"
}

& (Join-Path $PSScriptRoot "setup_windows_build_env.ps1") -RepoRoot $repoRoot -PythonIndexUrl $PythonIndexUrl -RecreateVenv:$RecreateVenv -UpdateLock:$UpdateLock
if ($LASTEXITCODE -ne 0) { throw "Windows environment setup failed with exit code $LASTEXITCODE" }

& (Join-Path $PSScriptRoot "build_windows_offline_bundle.ps1") -Output $Output -MpiInstaller $mpiInstaller
if ($LASTEXITCODE -ne 0) { throw "Offline bundle build failed with exit code $LASTEXITCODE" }

Write-Host "Windows offline bundle is ready: $([IO.Path]::GetFullPath($Output))"
