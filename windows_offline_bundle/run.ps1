[CmdletBinding()]
param(
    [ValidateSet("plan", "preflight", "dry-run", "execute")]
    [string]$Mode = "preflight",
    [string]$Case = "AI-TRN-003",
    [string]$DataDir = "D:\ai_ssd\data",
    [string]$ResultsDir = "E:\ai_ssd\results",
    [ValidateSet("single", "mpi")]
    [string]$Launcher = "single",
    [ValidateSet("mpiexec", "mpirun")]
    [string]$MpiBin = "mpiexec",
    [switch]$Prepare,
    [switch]$ConfirmDut,
    [switch]$InitResults,
    [string]$OrgName,
    [int]$Accelerators,
    [int]$ClientMemoryGb,
    [int]$DurationSec,
    [int]$Loops,
    [int]$QueryProcesses
)

$ErrorActionPreference = "Stop"
$installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = Join-Path $installRoot "app"
$python = Join-Path $installRoot "venv\Scripts\python.exe"
$mlpstorage = Join-Path $installRoot "venv\Scripts\mlpstorage.exe"
$caseFile = Join-Path $appRoot ("full_test_plan_cases\cases\test_{0}.py" -f $Case.ToLower().Replace("-", "_"))

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Installation not found. Run install.ps1 first: $installRoot"
}
if (-not (Test-Path -LiteralPath $caseFile -PathType Leaf)) {
    throw "Unknown Case: $Case"
}

$env:PATH = (Join-Path $installRoot "venv\Scripts") + ";" + $env:PATH

if ($InitResults) {
    $initOrg = if ($OrgName) { $OrgName } else { $Case.ToLower() }
    Write-Host "Initializing results directory with native mlpstorage: $ResultsDir"
    & $mlpstorage init $initOrg $ResultsDir
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$arguments = @(
    $caseFile,
    "--mode", $Mode,
    "--data-dir", $DataDir,
    "--results-dir", $ResultsDir,
    "--launcher", $Launcher,
    "--mpi-bin", $MpiBin
)
if ($Prepare) { $arguments += "--prepare" }
if ($ConfirmDut) { $arguments += "--confirm-dut" }
if ($PSBoundParameters.ContainsKey("Accelerators")) { $arguments += @("--accelerators", $Accelerators) }
if ($PSBoundParameters.ContainsKey("ClientMemoryGb")) { $arguments += @("--client-memory-gb", $ClientMemoryGb) }
if ($PSBoundParameters.ContainsKey("DurationSec")) { $arguments += @("--duration-sec", $DurationSec) }
if ($PSBoundParameters.ContainsKey("Loops")) { $arguments += @("--loops", $Loops) }
if ($PSBoundParameters.ContainsKey("QueryProcesses")) { $arguments += @("--query-processes", $QueryProcesses) }

Write-Host "Running $Case in $Mode mode"
& $python @arguments
exit $LASTEXITCODE
