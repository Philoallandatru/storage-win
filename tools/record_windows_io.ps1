[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Name,

    [Parameter(Mandatory = $true)]
    [string]$CommandPath,

    [string[]]$CommandArgumentList = @(),

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [int]$SampleIntervalSeconds = 1
)

$ErrorActionPreference = "Stop"
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $resolvedOutput | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$prefix = Join-Path $resolvedOutput ("{0}_{1}" -f $Name, $stamp)
$etlPath = "$prefix.etl"
$counterPath = "$prefix.physicaldisk.csv"
$manifestPath = "$prefix.manifest.json"

$counterPaths = @(
    '\PhysicalDisk(*)\Disk Read Bytes/sec',
    '\PhysicalDisk(*)\Disk Write Bytes/sec',
    '\PhysicalDisk(*)\Disk Reads/sec',
    '\PhysicalDisk(*)\Disk Writes/sec',
    '\PhysicalDisk(*)\Avg. Disk sec/Read',
    '\PhysicalDisk(*)\Avg. Disk sec/Write',
    '\PhysicalDisk(*)\Current Disk Queue Length',
    '\PhysicalDisk(*)\% Disk Time'
)

$wprStarted = $false
$counterProcess = $null
$exitCode = $null
$start = Get-Date

try {
    & wpr.exe -start GeneralProfile -filemode
    if ($LASTEXITCODE -ne 0) {
        throw "wpr -start failed with exit code $LASTEXITCODE. Run PowerShell as Administrator."
    }
    $wprStarted = $true

    # Start-Process concatenates ArgumentList entries into one command line;
    # quote counter paths explicitly so the wildcard/parenthesis syntax is
    # passed to typeperf unchanged (and so output paths with spaces work).
    $counterArgs = @(
        "-si",
        [string]$SampleIntervalSeconds,
        "-o",
        ('"' + $counterPath + '"')
    ) + ($counterPaths | ForEach-Object { '"' + $_ + '"' })
    $counterProcess = Start-Process -FilePath "typeperf.exe" -ArgumentList $counterArgs -PassThru -WindowStyle Hidden
    Start-Sleep -Milliseconds 500
    if ($counterProcess.HasExited) {
        Write-Warning "typeperf exited before workload start (exit code $($counterProcess.ExitCode)); PhysicalDisk CSV may be incomplete."
    }

    $process = Start-Process -FilePath $CommandPath -ArgumentList $CommandArgumentList -Wait -PassThru -NoNewWindow
    $exitCode = $process.ExitCode
}
finally {
    if ($counterProcess -and -not $counterProcess.HasExited) {
        Start-Sleep -Milliseconds 500
        Stop-Process -Id $counterProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($wprStarted) {
        & wpr.exe -stop $etlPath "AI SSD trace: $Name" | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "wpr -stop failed with exit code $LASTEXITCODE"
        }
    }
}

$manifest = [ordered]@{
    name = $Name
    start_time = $start.ToUniversalTime().ToString("o")
    end_time = (Get-Date).ToUniversalTime().ToString("o")
    command_path = [System.IO.Path]::GetFullPath($CommandPath)
    command_arguments = $CommandArgumentList
    exit_code = $exitCode
    windows = [System.Environment]::OSVersion.VersionString
    sample_interval_seconds = $SampleIntervalSeconds
    etw_trace = $etlPath
    physicaldisk_counters = $counterPath
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Host "Command exit code: $exitCode"
Write-Host "ETW: $etlPath"
Write-Host "PhysicalDisk counters: $counterPath"
Write-Host "Manifest: $manifestPath"
exit $exitCode
