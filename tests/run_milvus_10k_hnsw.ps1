[CmdletBinding()]
param(
    [string]$VenvPath = ".venv",
    [string]$RunRoot = "",
    [int]$NumVectors = 10000,
    [int]$Dimension = 1536,
    [int]$Queries = 200,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$UvPath = (Get-Command uv -ErrorAction Stop).Source

if ([string]::IsNullOrWhiteSpace($RunRoot)) {
    $RunRoot = Join-Path $env:TEMP ("mlpstorage-vdb-native-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
}
if (-not [System.IO.Path]::IsPathRooted($VenvPath)) {
    $VenvPath = Join-Path $RepoRoot $VenvPath
}
if (-not [System.IO.Path]::IsPathRooted($RunRoot)) {
    $RunRoot = Join-Path $RepoRoot $RunRoot
}

$VenvPath = [System.IO.Path]::GetFullPath($VenvPath)
$RunRoot = [System.IO.Path]::GetFullPath($RunRoot)
$Python = Join-Path $VenvPath "Scripts\python.exe"
$ResultsDir = Join-Path $RunRoot "results"
$MilvusDb = Join-Path $RunRoot "milvus_lite.db"
$Collection = "native_windows_milvus_hnsw_10k"

if (Test-Path -LiteralPath $RunRoot) {
    throw "Run directory already exists: $RunRoot`nPass a new -RunRoot so this run cannot reuse old results."
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host "`n==> $Label"
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path -LiteralPath $Python)) {
    Invoke-Checked -Label "Create Python 3.12 virtual environment" -Executable $UvPath -Arguments @(
        "venv", "--python", "3.12", $VenvPath
    )
}

if (-not $SkipInstall) {
    Invoke-Checked -Label "Install MLPerf Storage VectorDB dependencies" -Executable $UvPath -Arguments @(
        "pip", "install", "--python", $Python, "-e", ".[vectordb-milvus]"
    )
    Invoke-Checked -Label "Install modular VectorDB package" -Executable $UvPath -Arguments @(
        "pip", "install", "--python", $Python, "-e", ".\vdb_benchmark"
    )
    Invoke-Checked -Label "Install Milvus Lite for native Windows" -Executable $UvPath -Arguments @(
        "pip", "install", "--python", $Python, "milvus-lite"
    )
}

Invoke-Checked -Label "Verify Python dependencies" -Executable $Python -Arguments @(
    "-c", "import pymilvus, milvus_lite; print('pymilvus', pymilvus.__version__); print('milvus_lite', milvus_lite.__file__)"
)

New-Item -ItemType Directory -Path $RunRoot -Force | Out-Null

Invoke-Checked -Label "Initialize MLPerf Storage results" -Executable $Python -Arguments @(
    "-m", "mlpstorage_py.main", "init", "MLCommons", $ResultsDir
)

Invoke-Checked -Label "Generate Milvus Lite vectors" -Executable $Python -Arguments @(
    "-m", "mlpstorage_py.main", "open", "vectordb", "datagen", "file",
    "--vdb-engine", "milvus",
    "--vdb-index", "HNSW",
    "--config", "tests/configs/milvus_10k_hnsw.yaml",
    "--milvus-uri", $MilvusDb,
    "--collection", $Collection,
    "--num-vectors", $NumVectors,
    "--dimension", $Dimension,
    "--num-shards", "1",
    "--vector-dtype", "FLOAT_VECTOR",
    "--distribution", "uniform",
    "--batch-size", "500",
    "--chunk-size", "2000",
    "--index-type", "HNSW",
    "--force",
    "--systemname", "native-windows-lite",
    "--results-dir", $ResultsDir
)

Invoke-Checked -Label "Run MLPerf Storage VectorDB queries" -Executable $Python -Arguments @(
    "-m", "mlpstorage_py.main", "open", "vectordb", "run", "file",
    "--vdb-engine", "milvus",
    "--vdb-index", "HNSW",
    "--milvus-uri", $MilvusDb,
    "--collection", $Collection,
    "--num-query-processes", "1",
    "--batch-size", "10",
    "--queries", $Queries,
    "--report-count", "100",
    "--search-limit", "10",
    "--search-ef", "64",
    "--systemname", "native-windows-lite",
    "--results-dir", $ResultsDir
)

$RunMetadata = Get-ChildItem -LiteralPath $ResultsDir -Recurse -File -Filter "*_metadata.json" |
    Where-Object { $_.FullName -match "\\run\\" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($null -eq $RunMetadata) {
    throw "The command exited successfully, but no VectorDB run metadata was found under $ResultsDir"
}

Write-Host "`nNative Windows MLPerf Storage VectorDB test passed."
Write-Host "Results: $($RunMetadata.DirectoryName)"
Write-Host "Database: $MilvusDb"
