[CmdletBinding()]
param(
    [string]$Version = "v10.1.1",
    [string]$Destination = (Join-Path (Get-Location) ".artifacts\msmpi"),
    [switch]$Force,
    [switch]$InstallRuntime,
    [switch]$InstallSdk
)

$ErrorActionPreference = "Stop"
$apiUri = "https://api.github.com/repos/microsoft/Microsoft-MPI/releases/tags/$Version"
$destinationPath = [IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Path $destinationPath -Force | Out-Null

$headers = @{
    Accept = "application/vnd.github+json"
    "User-Agent" = "MLPerf-Storage-Windows-Bundle"
}
Write-Host "Reading Microsoft-MPI release metadata: $Version"
$release = Invoke-RestMethod -Uri $apiUri -Headers $headers

$assetPaths = [ordered]@{}
foreach ($assetName in @("msmpisetup.exe", "msmpisdk.msi")) {
    $asset = @($release.assets) | Where-Object { $_.name -ieq $assetName } | Select-Object -First 1
    if (-not $asset) {
        throw "Release $Version does not contain the expected asset: $assetName"
    }
    $target = Join-Path $destinationPath $asset.name
    if ($Force -or -not (Test-Path -LiteralPath $target -PathType Leaf)) {
        Write-Host "Downloading $($asset.name)"
        Invoke-WebRequest -Uri $asset.browser_download_url -Headers @{ "User-Agent" = $headers["User-Agent"] } -OutFile $target
    } else {
        Write-Host "Keeping existing file: $target"
    }
    if ((Get-Item -LiteralPath $target).Length -le 0) {
        throw "Downloaded file is empty: $target"
    }
    $assetPaths[$asset.name] = $target
    Write-Host "SHA256 $($asset.name): $((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash)"
}

$metadata = [ordered]@{
    product = "Microsoft MPI"
    version = $Version
    release_url = "https://github.com/microsoft/Microsoft-MPI/releases/tag/$Version"
    downloaded_at = (Get-Date).ToString("o")
    assets = $assetPaths
}
$metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $destinationPath "download-metadata.json") -Encoding utf8

if ($InstallRuntime) {
    Write-Host "Starting Microsoft MPI runtime installer (administrator privileges may be required)."
    $process = Start-Process -FilePath $assetPaths["msmpisetup.exe"] -Wait -PassThru -Verb RunAs
    if ($process.ExitCode -ne 0) {
        throw "Microsoft MPI runtime installer failed with exit code $($process.ExitCode)"
    }
}
if ($InstallSdk) {
    Write-Host "Starting Microsoft MPI SDK installer (administrator privileges may be required)."
    $process = Start-Process -FilePath "msiexec.exe" -ArgumentList @("/i", $assetPaths["msmpisdk.msi"]) -Wait -PassThru -Verb RunAs
    if ($process.ExitCode -ne 0) {
        throw "Microsoft MPI SDK installer failed with exit code $($process.ExitCode)"
    }
}

Write-Host "Microsoft MPI files are ready in $destinationPath"
Write-Output $assetPaths["msmpisetup.exe"]
