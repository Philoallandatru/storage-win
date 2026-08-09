[CmdletBinding()]
param(
    [string]$InstallRoot = "",
    [string]$DataDir = "C:\MLPerfData",
    [string]$ResultsDir = "C:\MLPerfResults",
    [ValidateSet("mpiexec", "mpirun")]
    [string]$MpiBin = "mpiexec",
    [string]$MilvusHost = "127.0.0.1",
    [ValidateRange(1, 65535)]
    [int]$MilvusPort = 19530,
    [switch]$SkipMilvusCheck
)

$ErrorActionPreference = "Stop"

if ($InstallRoot) {
    $resolvedInstallRoot = [IO.Path]::GetFullPath($InstallRoot)
    $appRoot = Join-Path $resolvedInstallRoot "app"
    $venvRoot = Join-Path $resolvedInstallRoot "venv"
    $layout = "installed"
} elseif (
    (Test-Path -LiteralPath (Join-Path $PSScriptRoot "app\full_test_plan_cases") -PathType Container) -and
    (Test-Path -LiteralPath (Join-Path $PSScriptRoot "venv\Scripts\python.exe") -PathType Leaf)
) {
    $resolvedInstallRoot = [IO.Path]::GetFullPath($PSScriptRoot)
    $appRoot = Join-Path $resolvedInstallRoot "app"
    $venvRoot = Join-Path $resolvedInstallRoot "venv"
    $layout = "installed"
} else {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $resolvedInstallRoot = $repoRoot
    $appRoot = $repoRoot
    $venvRoot = Join-Path $repoRoot ".venv"
    $layout = "repository"
}

$python = Join-Path $venvRoot "Scripts\python.exe"
$mlpstorage = Join-Path $venvRoot "Scripts\mlpstorage.exe"
$catalogPath = Join-Path $appRoot "full_test_plan_cases\case_catalog.json"
$casesRoot = Join-Path $appRoot "full_test_plan_cases\cases"

$requiredPaths = @(
    @{ Path = $python; Type = "Leaf" },
    @{ Path = $mlpstorage; Type = "Leaf" },
    @{ Path = $catalogPath; Type = "Leaf" },
    @{ Path = $casesRoot; Type = "Container" }
)
foreach ($required in $requiredPaths) {
    if (-not (Test-Path -LiteralPath $required.Path -PathType $required.Type)) {
        throw "Required environment path is missing: $($required.Path)"
    }
}

$venvScripts = Join-Path $venvRoot "Scripts"
$msMpiBin = "C:\Program Files\Microsoft MPI\Bin"
$pathEntries = @($venvScripts)
if (Test-Path -LiteralPath $msMpiBin -PathType Container) {
    $pathEntries += $msMpiBin
}
$env:PATH = ($pathEntries -join ";") + ";" + $env:PATH
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "Environment layout: $layout"
Write-Host "Application root: $appRoot"
Write-Host "Python: $(& $python --version 2>&1)"
if ($LASTEXITCODE -ne 0) {
    throw "Bundled Python failed with exit code $LASTEXITCODE"
}

& $python -c "import mlpstorage_py, dlio_benchmark, kv_cache, vdbbench, pymilvus; print('PYTHON_IMPORTS_OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Python workload imports failed with exit code $LASTEXITCODE"
}

$null = & $mlpstorage --help
if ($LASTEXITCODE -ne 0) {
    throw "mlpstorage CLI failed with exit code $LASTEXITCODE"
}
Write-Host "MLPSTORAGE_CLI_OK"

$dlioCommand = Get-Command dlio_benchmark -ErrorAction Stop
Write-Host "DLIO_OK $($dlioCommand.Source)"

$mpiCommand = Get-Command $MpiBin -ErrorAction Stop
$mpiOutput = & $mpiCommand.Source -n 1 hostname 2>&1
if ($LASTEXITCODE -ne 0) {
    $mpiOutput | ForEach-Object { Write-Host $_ }
    throw "MPI process launch failed with exit code $LASTEXITCODE"
}
Write-Host "MPI_OK $($mpiCommand.Source) rank_output=$($mpiOutput -join ' ')"

$resolvedDataDir = [IO.Path]::GetFullPath($DataDir)
$resolvedResultsDir = [IO.Path]::GetFullPath($ResultsDir)
foreach ($directory in @($resolvedDataDir, $resolvedResultsDir)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $probe = Join-Path $directory ".mlperf-write-check-$PID"
    try {
        [IO.File]::WriteAllText($probe, "ok")
    } finally {
        if (Test-Path -LiteralPath $probe -PathType Leaf) {
            Remove-Item -LiteralPath $probe -Force
        }
    }
    Write-Host "WRITE_OK $directory"

    $driveRoot = [IO.Path]::GetPathRoot($directory)
    if ($driveRoot -match "^([A-Za-z]):\\$") {
        $drive = Get-PSDrive -Name $Matches[1] -ErrorAction SilentlyContinue
        if ($drive) {
            Write-Host "FREE_BYTES $directory $($drive.Free)"
        }
    }
}
if ([IO.Path]::GetPathRoot($resolvedDataDir) -eq [IO.Path]::GetPathRoot($resolvedResultsDir)) {
    Write-Warning "DataDir and ResultsDir are on the same volume. Use a non-DUT volume for formal result output."
}

$catalog = Get-Content -Raw -LiteralPath $catalogPath | ConvertFrom-Json
$supportedCases = @($catalog | Where-Object { $_.native_status -eq "SUPPORTED" })
if ($supportedCases.Count -eq 0) {
    throw "The Case catalog contains no SUPPORTED native Cases: $catalogPath"
}

$passed = 0
foreach ($case in $supportedCases) {
    $caseFileName = "test_{0}.py" -f $case.case_id.ToLower().Replace("-", "_")
    $caseFile = Join-Path $casesRoot $caseFileName
    if (-not (Test-Path -LiteralPath $caseFile -PathType Leaf)) {
        throw "Case entrypoint is missing: $caseFile"
    }

    $caseArguments = @(
        $caseFile,
        "--mode", "preflight",
        "--data-dir", $resolvedDataDir,
        "--results-dir", $resolvedResultsDir,
        "--launcher", "mpi",
        "--mpi-bin", $MpiBin,
        "--mlpstorage", $mlpstorage
    )
    $caseOutput = & $python @caseArguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        $caseOutput | ForEach-Object { Write-Host $_ }
        throw "Case preflight failed: $($case.case_id), exit code $LASTEXITCODE"
    }
    $passed++
    Write-Host "CASE_OK $($case.case_id)"
}
Write-Host "SUPPORTED_PREFLIGHT_OK=$passed/$($supportedCases.Count)"

$milvusStatus = "skipped"
if (-not $SkipMilvusCheck) {
    $milvusReady = Test-NetConnection `
        -ComputerName $MilvusHost `
        -Port $MilvusPort `
        -InformationLevel Quiet `
        -WarningAction SilentlyContinue
    if (-not $milvusReady) {
        throw "Milvus is not reachable at ${MilvusHost}:$MilvusPort. VectorDB Cases are not ready."
    }
    $milvusStatus = "ready"
    Write-Host "MILVUS_READY=True host=${MilvusHost}:$MilvusPort"
} else {
    Write-Host "MILVUS_READY=SKIPPED"
}

Write-Host "ENVIRONMENT_READY supported_cases=$passed/$($supportedCases.Count) milvus=$milvusStatus"
