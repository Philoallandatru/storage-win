[CmdletBinding()]
param(
    [string]$RunRoot = "",
    [string]$Collection = "offline_windows_milvus_hnsw_10k",
    [string]$SystemName = "offline-windows-lite",
    [string]$PythonPath = "",
    [int]$NumVectors = 10000,
    [int]$Dimension = 1536,
    [int]$Queries = 200
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# In an installed bundle this launcher lives under <InstallRoot>\app and the
# bundled venv is its sibling. PythonPath is only useful when validating the
# source launcher against a prepared external venv.
if (-not [string]::IsNullOrWhiteSpace($PythonPath)) {
    $appRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $python = [System.IO.Path]::GetFullPath($PythonPath)
} else {
    $installedPython = Join-Path $PSScriptRoot "..\venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $installedPython -PathType Leaf) {
        $appRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
        $python = (Resolve-Path -LiteralPath $installedPython).Path
    } else {
        $appRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
        $python = Join-Path $appRoot ".venv\Scripts\python.exe"
    }
}

$config = Join-Path $appRoot "configs\vectordbbench\default.yaml"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python environment not found: $python"
}
if (-not (Test-Path -LiteralPath $config -PathType Leaf)) {
    throw "Bundled VectorDB configuration not found: $config"
}

$pythonPathEntries = @($appRoot, (Join-Path $appRoot "vdb_benchmark"))
if ($env:PYTHONPATH) {
    $pythonPathEntries += $env:PYTHONPATH
}
$env:PYTHONPATH = $pythonPathEntries -join ";"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if ([string]::IsNullOrWhiteSpace($RunRoot)) {
    $RunRoot = Join-Path $env:TEMP ("mlpstorage-vdb-bundle-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
}
if (-not [System.IO.Path]::IsPathRooted($RunRoot)) {
    $RunRoot = Join-Path $appRoot $RunRoot
}
$RunRoot = [System.IO.Path]::GetFullPath($RunRoot)
$resultsDir = Join-Path $RunRoot "results"
$milvusDb = Join-Path $RunRoot "milvus_lite.db"

if (Test-Path -LiteralPath $RunRoot) {
    throw "Run directory already exists: $RunRoot. Pass a new -RunRoot to avoid reusing a previous local database."
}
New-Item -ItemType Directory -Path $RunRoot -Force | Out-Null

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host ""
    Write-Host "==> $Label"
    & $python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

Invoke-Checked -Label "Verify bundled Milvus Lite" -Arguments @(
    "-c",
    "import pymilvus, milvus_lite; print('pymilvus', pymilvus.__version__); print('milvus_lite', milvus_lite.__file__)"
)

Invoke-Checked -Label "Initialize MLPerf Storage results" -Arguments @(
    "-m", "mlpstorage_py.main", "init", "MLCommons", $resultsDir
)

Invoke-Checked -Label "Generate vectors in bundled Milvus Lite" -Arguments @(
    "-m", "mlpstorage_py.main", "open", "vectordb", "datagen", "file",
    "--vdb-engine", "milvus",
    "--vdb-index", "HNSW",
    "--config", $config,
    "--milvus-uri", $milvusDb,
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
    "--storage-root", $RunRoot,
    "--storage-type", "local_fs",
    "--systemname", $SystemName,
    "--results-dir", $resultsDir,
    "--skip-validation"
)

Invoke-Checked -Label "Run MLPerf Storage VectorDB queries" -Arguments @(
    "-m", "mlpstorage_py.main", "open", "vectordb", "run", "file",
    "--vdb-engine", "milvus",
    "--vdb-index", "HNSW",
    "--config", $config,
    "--milvus-uri", $milvusDb,
    "--collection", $Collection,
    "--num-query-processes", "1",
    "--batch-size", "10",
    "--queries", $Queries,
    "--report-count", "100",
    "--vector-dim", $Dimension,
    "--search-limit", "10",
    "--search-ef", "64",
    "--num-query-vectors", "1000",
    "--storage-root", $RunRoot,
    "--storage-type", "local_fs",
    "--systemname", $SystemName,
    "--results-dir", $resultsDir,
    "--skip-validation"
)

$runMetadata = Get-ChildItem -LiteralPath $resultsDir -Recurse -File -Filter "*_metadata.json" |
    Where-Object { $_.FullName -match "\\run\\" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $runMetadata) {
    throw "VectorDB completed but no run metadata was found under $resultsDir"
}

Write-Host ""
Write-Host "Native Windows bundled VectorDB test passed."
Write-Host "Results: $($runMetadata.DirectoryName)"
Write-Host "Database: $milvusDb"
