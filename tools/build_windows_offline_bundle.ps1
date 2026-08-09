[CmdletBinding()]
param(
    [string]$Output = (Join-Path (Get-Location) "MLPerfStorage-Windows-Offline.zip"),
    [string]$MpiInstaller = "C:\Program Files\Microsoft MPI\Redist\MSMpiSetup.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$outputPath = [IO.Path]::GetFullPath($Output)
$mpiInstallerPath = [IO.Path]::GetFullPath($MpiInstaller)
$outputParent = [IO.Path]::GetDirectoryName($outputPath)
if (-not (Test-Path -LiteralPath $outputParent -PathType Container)) {
    New-Item -ItemType Directory -Path $outputParent -Force | Out-Null
}
$staging = Join-Path $outputParent ("mlpstorage-offline-staging-" + [guid]::NewGuid().ToString("N"))
$payload = Join-Path $staging "payload"
$app = Join-Path $payload "app"
$venv = Join-Path $payload "venv"
$runtimeRoot = Join-Path $payload "runtime"
$runtime = Join-Path $runtimeRoot "python"

function Copy-BundlePath([string]$RelativePath) {
    $source = Join-Path $repoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Required bundle path is missing: $source"
    }
    $destination = Join-Path $app $RelativePath
    if ((Get-Item -LiteralPath $source).PSIsContainer) {
        Copy-BundleDirectory $source $destination
    } else {
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}

function Copy-BundleDirectory([string]$Source, [string]$Destination) {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    $excludedDirectories = @(".git", ".pytest_cache", "__pycache__", "results", "data", "checkpoints", "tests", "fixtures")
    foreach ($item in Get-ChildItem -LiteralPath $Source -Force) {
        if ($item.PSIsContainer -and $excludedDirectories -contains $item.Name) {
            continue
        }
        if (-not $item.PSIsContainer -and $item.Extension -in @(".pyc", ".pyo")) {
            continue
        }
        $itemDestination = Join-Path $Destination $item.Name
        if ($item.PSIsContainer) {
            Copy-BundleDirectory $item.FullName $itemDestination
        } else {
            Copy-Item -LiteralPath $item.FullName -Destination $itemDestination -Force
        }
    }
}

try {
    New-Item -ItemType Directory -Path $app,$venv,$runtimeRoot -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repoRoot "windows_offline_bundle\install.ps1") -Destination $staging -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot "windows_offline_bundle\run.ps1") -Destination $staging -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot "windows_offline_bundle\install.cmd") -Destination $staging -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot "windows_offline_bundle\run.cmd") -Destination $staging -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot "windows_offline_bundle\README.md") -Destination $staging -Force

    foreach ($relative in @(
        "mlpstorage_py", "configs", "full_test_plan_cases", "ai_ssd_test_cases",
        "kv_cache_benchmark", "vdb_benchmark", "pyproject.toml", "uv.lock",
        ".python-version", "mlpstorage.yaml", ".env.example"
    )) {
        Copy-BundlePath $relative
    }

    $venvSource = Join-Path $repoRoot ".venv"
    if (-not (Test-Path -LiteralPath (Join-Path $venvSource "Scripts\python.exe"))) {
        throw "A prepared Windows .venv is required: $venvSource"
    }
    Copy-Item -Path (Join-Path $venvSource "*") -Destination $venv -Recurse -Force
    $venvCacheDirectories = Get-ChildItem -LiteralPath $venv -Directory -Recurse -Force |
        Where-Object { $_.Name -in @("__pycache__", ".pytest_cache") } |
        Sort-Object FullName -Descending
    foreach ($cacheDirectory in $venvCacheDirectories) {
        Remove-Item -LiteralPath $cacheDirectory.FullName -Recurse -Force
    }
    Get-ChildItem -LiteralPath $venv -File -Recurse -Force |
        Where-Object { $_.Extension -in @(".pyc", ".pyo") } |
        Remove-Item -Force

    $pyvenvConfig = Get-Content -LiteralPath (Join-Path $venvSource "pyvenv.cfg")
    $pythonHomeLine = $pyvenvConfig | Where-Object { $_ -match '^home\s*=' } | Select-Object -First 1
    if (-not $pythonHomeLine) { throw "Cannot find Python home in .venv\pyvenv.cfg" }
    $pythonHome = ($pythonHomeLine -replace '^home\s*=\s*', '').Trim()
    if (-not (Test-Path -LiteralPath $pythonHome)) { throw "Bundled Python home is missing: $pythonHome" }
    New-Item -ItemType Directory -Path $runtime -Force | Out-Null
    Copy-Item -Path (Join-Path $pythonHome "*") -Destination $runtime -Recurse -Force

    $venvPayload = Join-Path $payload "venv"
    $finders = Get-ChildItem -LiteralPath (Join-Path $venvPayload "Lib\site-packages") -Filter "__editable___*_finder.py" -File -ErrorAction SilentlyContinue
    $sourceMappings = @{
        ($repoRoot.Replace("\", "\\")) = "__MLPERF_APP_ROOT__"
    }
    foreach ($finder in $finders) {
        $content = Get-Content -LiteralPath $finder.FullName -Raw
        foreach ($mapping in $sourceMappings.GetEnumerator()) {
            $content = $content.Replace($mapping.Key, $mapping.Value)
        }
        Set-Content -LiteralPath $finder.FullName -Value $content -Encoding utf8 -NoNewline
    }

    if (Test-Path -LiteralPath $mpiInstallerPath) {
        $mpiDestination = Join-Path $payload "mpi"
        New-Item -ItemType Directory -Path $mpiDestination -Force | Out-Null
        Copy-Item -LiteralPath $mpiInstallerPath -Destination $mpiDestination -Force
    }

    $manifest = [ordered]@{
        bundle = "MLPerf Storage Windows Offline"
        mlpstorage_version = "3.0.46"
        python = "3.12.3"
        platform = "Windows x64"
        source_commit = (& git -C $repoRoot rev-parse HEAD).Trim()
        created_at = (Get-Date).ToString("o")
        includes_python_runtime = $true
        includes_prepared_venv = $true
        includes_microsoft_mpi_installer = (Test-Path -LiteralPath (Join-Path $payload "mpi\MSMpiSetup.exe"))
        network_required_at_install = $false
        data_included = $false
        milvus_included = $false
    }
    $manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $staging "manifest.json") -Encoding utf8

    if (Test-Path -LiteralPath $outputPath) {
        Remove-Item -LiteralPath $outputPath -Force
    }
    $zipPython = Join-Path $venvSource "Scripts\python.exe"
    & $zipPython (Join-Path $repoRoot "tools\create_zip_archive.py") -Source $staging -Output $outputPath
    if ($LASTEXITCODE -ne 0) { throw "Zip creation failed with exit code $LASTEXITCODE" }
    Write-Host "Created offline bundle: $outputPath"
} finally {
    if (Test-Path -LiteralPath $staging) {
        Remove-Item -LiteralPath $staging -Recurse -Force
    }
}
