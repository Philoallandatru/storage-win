<#
.SYNOPSIS
    Run any MLPerf Storage native case via mlpstorage CLI.

.DESCRIPTION
    Reads the case's COMMANDS list from `full_test_plan_cases/cases/test_<id>.py`
    and invokes mlpstorage with placeholder substitution. Wraps each call
    in `setup_env.cmd` so MSVC's link.exe is on PATH for sdist builds.

    Supports all four families:
      Training    — AI-TRN-001..005 → mlpstorage open training <model> datagen/run file
      Checkpoint  — AI-CKP-001..007 → mlpstorage open checkpointing <model> datagen/run
      KV Cache    — AI-KV-001..008  → mlpstorage open kvcache run --model ...
      VectorDB    — AI-VDB-001..016 → mlpstorage vectordb run

    Placeholders in COMMANDS (e.g. <DATA_DIR>, <RESULTS_DIR>, <LOOPS>, <MPI_BIN>,
    <SYSTEMNAME>, <CACHE_DIR>, <DURATION_SEC>, <CLIENT_MEMORY_GB>,
    <ACCELERATORS>, <QUERY_PROCESSES>) are substituted from -DataDir /
    -ResultsDir / -Loops / etc. — so the user only provides the per-run
    values, not the whole command line.

.PARAMETER CaseId
    Native case id, e.g. AI-TRN-005, AI-CKP-001, AI-VDB-014, AI-KV-001.
    Case-insensitive. Hyphen count and casing don't matter — the script
    normalizes to the canonical form.

.PARAMETER DataDir
    Dataset directory (also used as cache-dir for KV-cache cases). Must
    be on a different drive than ResultsDir or -SkipFsSeparationGate set.

.PARAMETER ResultsDir
    Results directory. Must be on a different drive than DataDir or
    -SkipFsSeparationGate set.

.PARAMETER NumAccelerators
    Simulated accelerator count for training/checkpointing. Default 1.

.PARAMETER NumProcesses
    Parallel processes for the datagen phase. Default 1.

.PARAMETER NumUsers
    KV cache concurrent users. Default 200.

.PARAMETER DurationSec
    KV cache / training run duration. Default 60.

.PARAMETER ClientMemoryGb
    Client host memory in GB. Default 64.

.PARAMETER GpuMemGb
    KV cache GPU tier memory. Default 0.

.PARAMETER CpuMemGb
    KV cache CPU tier memory. Default 0.

.PARAMETER Loops
    Number of benchmark loops. MLPerf submission standard is 5; dev runs
    use 1. Default 1.

.PARAMETER QueryProcesses
    VectorDB query processes. Default 1.

.PARAMETER AcceleratorType
    One of: h100, a100, b200, mi355. Default h100.

.PARAMETER ExecType
    Executor: mpi or docker. Default mpi.

.PARAMETER MpiBin
    MPI launcher: mpiexec (Windows) or mpirun (Linux). Default mpiexec.

.PARAMETER ExtraParams
    Extra DLIO `KEY=VALUE` params to inject into the run argv via --params.

.PARAMETER SkipPrepare
    Skip the prepare/datagen phase (use existing data on disk).

.PARAMETER SkipRun
    Skip the run phase (prepare only).

.PARAMETER SkipFsSeparationGate
    Pass --skip-fs-separation-gate to mlpstorage. CAP-03 warns but does
    not raise. Dev only.

.PARAMETER DryRun
    Pass --dry-run to mlpstorage. Verify paths / capacity without
    starting the workload.

.PARAMETER List
    Print the resolved mlpstorage command(s) for the case without
    actually running them, then exit. Useful for confirming the
    command shape before committing to a long run.

.EXAMPLE
    # See what AI-TRN-005 would do without running
    .\scripts\run_mlpstorage_case.ps1 -CaseId AI-TRN-005 `
        -DataDir C:\MLPerfStorageTest\data\ai-trn-005 `
        -ResultsDir D:\MLPerfStorageTest\results\ai-trn-005 `
        -List

.EXAMPLE
    # Dry-run
    .\scripts\run_mlpstorage_case.ps1 -CaseId AI-TRN-005 `
        -DataDir C:\MLPerfStorageTest\data\ai-trn-005 `
        -ResultsDir D:\MLPerfStorageTest\results\ai-trn-005 `
        -DryRun

.EXAMPLE
    # Full run
    .\scripts\run_mlpstorage_case.ps1 -CaseId AI-TRN-005 `
        -DataDir C:\MLPerfStorageTest\data\ai-trn-005 `
        -ResultsDir D:\MLPerfStorageTest\results\ai-trn-005 `
        -AcceleratorType h100 -Loops 1

.EXAMPLE
    # Different families — same script
    .\scripts\run_mlpstorage_case.ps1 -CaseId AI-CKP-001 `
        -DataDir C:\MLPerfStorageTest\data\ai-ckp-001 `
        -ResultsDir D:\MLPerfStorageTest\results\ai-ckp-001 `
        -Loops 1

    .\scripts\run_mlpstorage_case.ps1 -CaseId AI-KV-001 `
        -DataDir C:\MLPerfStorageTest\data\ai-kv-001 `
        -ResultsDir D:\MLPerfStorageTest\results\ai-kv-001 `
        -NumUsers 200 -DurationSec 60

    .\scripts\run_mlpstorage_case.ps1 -CaseId AI-VDB-001 `
        -DataDir C:\MLPerfStorageTest\data\ai-vdb-001 `
        -ResultsDir D:\MLPerfStorageTest\results\ai-vdb-001
#>

[CmdletBinding(DefaultParameterSetName = 'Run')]
param(
    [Parameter(Mandatory = $true)] [string] $CaseId,

    [Parameter(Mandatory = $true)] [string] $DataDir,
    [Parameter(Mandatory = $true)] [string] $ResultsDir,

    [int] $NumAccelerators = 1,
    [int] $NumProcesses = 1,
    [int] $NumUsers = 200,
    [int] $DurationSec = 60,
    [int] $ClientMemoryGb = 64,
    [int] $GpuMemGb = 0,
    [int] $CpuMemGb = 0,
    [int] $Loops = 1,
    [int] $QueryProcesses = 1,
    [ValidateSet('h100','a100','b200','mi355')] [string] $AcceleratorType = 'h100',
    [ValidateSet('mpi','docker')] [string] $ExecType = 'mpi',
    [ValidateSet('mpirun','mpiexec')] [string] $MpiBin = 'mpiexec',
    [string[]] $ExtraParams,
    [switch] $SkipPrepare,
    [switch] $SkipRun,
    [switch] $SkipFsSeparationGate,
    [switch] $DryRun,
    [switch] $List
)

$ErrorActionPreference = 'Stop'
$REPO_ROOT = (Resolve-Path "$PSScriptRoot\..").Path
$MLPSTORAGE = Join-Path $REPO_ROOT '.venv\Scripts\mlpstorage.exe'
$SETUP_ENV = Join-Path $REPO_ROOT 'setup_env.cmd'

# --- case-id normalization --------------------------------------------------
# Accept AI-TRN--005 (typo), ai-trn-005, AI TRN 005, ai.trn.005, etc.
# Normalize to canonical form: AI-TRN-005. File path uses underscore form:
# full_test_plan_cases/cases/test_ai_trn_005.py
$normalized = $CaseId.ToUpper() -replace '[^A-Z0-9]+', '-'
$normalized = $normalized.Trim('-')
$caseFile = Join-Path $REPO_ROOT 'full_test_plan_cases\cases' "test_$($normalized.ToLower() -replace '-','_').py"
$systemName = "$($normalized.ToLower())-native"
if (-not (Test-Path $caseFile)) {
    $available = (Get-ChildItem (Join-Path $REPO_ROOT 'full_test_plan_cases\cases') -Filter 'test_*.py' |
        ForEach-Object { "  " + ($_.BaseName -replace '^test_', '' -replace '_','-') })
    $msg = "Case entrypoint not found: $caseFile`nAvailable cases:`n" + ($available -join "`n")
    throw $msg
}

# --- load COMMANDS list from the case file ----------------------------------
# Delegate placeholder substitution to a Python helper that mirrors the
# case file's own values table. Keeps the case files as the single
# source of truth — adding a new case (or a new placeholder) just works
# without editing this runner.
$venvPy = Join-Path $REPO_ROOT '.venv\Scripts\python.exe'
$resolveScript = Join-Path $REPO_ROOT 'scripts\_resolve_case_args.py'
if (-not (Test-Path $venvPy)) { throw "python.exe not found at $venvPy" }
if (-not (Test-Path $resolveScript)) { throw "resolver script not found at $resolveScript" }

$pyArgs = @(
    $resolveScript,
    (Resolve-Path $caseFile).Path,
    (Resolve-Path $DataDir).Path,
    (Resolve-Path $ResultsDir).Path,
    '--systemname', $systemName,
    '--loops', $Loops,
    '--mpi-bin', $MpiBin,
    '--num-accelerators', $NumAccelerators,
    '--client-memory-gb', $ClientMemoryGb,
    '--duration-sec', $DurationSec,
    '--query-processes', $QueryProcesses,
    '--num-users', $NumUsers,
    '--gpu-mem-gb', $GpuMemGb,
    '--cpu-mem-gb', $CpuMemGb,
    '--accelerator-type', $AcceleratorType
)
if ($SkipFsSeparationGate) { $pyArgs += '--skip-fs-separation-gate' }
if ($DryRun) { $pyArgs += '--dry-run' }
foreach ($p in $ExtraParams) { $pyArgs += @('--params', $p) }

$pyOut = & $venvPy @pyArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python resolver failed (exit=$LASTEXITCODE): $pyOut" -ForegroundColor Red
    throw "Failed to resolve case commands from $caseFile"
}
$caseInfoJson = $pyOut | ConvertFrom-Json
if ($caseInfoJson.native_status -ne 'SUPPORTED' -or -not $caseInfoJson.commands) {
    throw "Case $normalized is not natively supported via mlpstorage: status=$($caseInfoJson.native_status) reason=$($caseInfoJson.native_reason)"
}
$commands = @($caseInfoJson.commands | ForEach-Object {
    @{ phase = $_.phase; argv = @($_.argv) }
})

# --- placeholder substitution ----------------------------------------------
# All placeholder substitution is done by _resolve_case_args.py, which
# mirrors each case file's own values dict. If a new placeholder appears
# in a case file's COMMANDS, add it to the values dict in that helper.
# No PS-side substitution table needed here.

# --- CAP-03 sanity check ----------------------------------------------------
$dataDrive = (Get-Item $DataDir -ErrorAction SilentlyContinue).PSDrive.Name
$resultsDrive = (Get-Item $ResultsDir -ErrorAction SilentlyContinue).PSDrive.Name
if ($dataDrive -and $resultsDrive -and $dataDrive -eq $resultsDrive) {
    Write-Warning "DataDir and ResultsDir both on drive ${dataDrive}: — CAP-03 will hard-fail."
    if (-not $SkipFsSeparationGate) {
        throw "Refusing to run: data and results must be on different drives. Re-run with -SkipFsSeparationGate to bypass (dev only)."
    }
}

# --- dispatch ---------------------------------------------------------------
if (-not (Test-Path $MLPSTORAGE)) { throw "mlpstorage not found at $MLPSTORAGE — run setup_env.cmd uv sync first" }
if (-not (Test-Path $SETUP_ENV)) { throw "setup_env.cmd not found at $SETUP_ENV" }

$phases = @()
foreach ($cmd in $commands) {
    $phase = $cmd['phase']
    if ($phase -match 'prepare|datagen' -and $SkipPrepare) { continue }
    if ($phase -match '^run$' -and $SkipRun) { continue }
    $phases += $cmd
}

if ($phases.Count -eq 0) {
    Write-Warning "All phases skipped (-SkipPrepare + -SkipRun). Nothing to do."
    return
}

$idx = 0
foreach ($cmd in $phases) {
    $idx++
    $phase = $cmd['phase']
    $argv = $cmd['argv']
    Write-Host ""
    Write-Host "=== [$normalized] Phase $idx/$($phases.Count): $phase ===" -ForegroundColor Green
    Write-Host "==> mlpstorage $($argv -join ' ')" -ForegroundColor Cyan

    if ($List) { continue }

    & $SETUP_ENV @($MLPSTORAGE) @argv
    if ($LASTEXITCODE -ne 0) {
        throw "[$normalized] phase '$phase' failed (exit code $LASTEXITCODE)"
    }
}

if ($List) {
    Write-Host "`n(List mode — no commands executed.)" -ForegroundColor Yellow
} else {
    Write-Host "`n=== $normalized complete ===" -ForegroundColor Green
}
