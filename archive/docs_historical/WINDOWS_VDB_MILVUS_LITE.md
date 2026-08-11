# Native Windows VectorDB Test with Milvus Lite

This guide runs an MLPerf Storage VectorDB workload on native Windows with
Python and Milvus Lite. It uses a local `.db` file and starts Milvus Lite
inside the Python process.

This single-node workflow does not require WSL, Docker, or MPI. It is a
functional smoke test, not a substitute for a remote Milvus deployment used
for multi-node or DISKANN submission runs.

## 1. Prerequisites

Use a native Windows x64 PowerShell session with:

- Python 3.12 x64, or the Python runtime managed by `uv`;
- `uv`;
- Git;
- a clone of this repository.

Check the tools from the repository root:

```powershell
python --version
uv --version
git status --short
```

If Python 3.12 is not installed, `uv` can provision it:

```powershell
uv python install 3.12
```

## 2. Create the native Windows environment

Run this once from the repository root. The execution-policy change only
applies to the current PowerShell process.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

uv venv --python 3.12 .venv
$Python = (Resolve-Path .\.venv\Scripts\python.exe).Path

uv pip install --python $Python -e ".[vectordb-milvus]"
uv pip install --python $Python -e ".\vdb_benchmark"

# Install this explicitly on Windows. In the tested environment,
# pymilvus[milvus-lite] alone did not install the milvus-lite package.
uv pip install --python $Python milvus-lite

& $Python -c "import pymilvus, milvus_lite; print('pymilvus', pymilvus.__version__); print('milvus_lite', milvus_lite.__file__)"
```

The last command must import both `pymilvus` and `milvus_lite` successfully.

## 3. Define a fresh test run

Use a new run directory so an old local database or result tree cannot be
mistaken for the current run:

```powershell
$RunRoot = Join-Path $env:TEMP ("mlpstorage-vdb-native-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
$ResultsDir = Join-Path $RunRoot "results"
$MilvusDb = Join-Path $RunRoot "milvus_lite.db"
$Collection = "native_windows_milvus_hnsw_10k"

New-Item -ItemType Directory -Path $RunRoot -Force | Out-Null
```

`$MilvusDb` is the local Milvus Lite URI. Do not pass it as a remote host or
start a separate Milvus container.

## 4. Initialize the MLPerf Storage result directory

```powershell
& $Python -m mlpstorage_py.main init MLCommons $ResultsDir
if ($LASTEXITCODE -ne 0) { throw "mlpstorage init failed" }
```

## 5. Generate the vector data

The test below uses 10,000 vectors with 1,536 dimensions. The run command
must use the same dimension.

```powershell
& $Python -m mlpstorage_py.main open vectordb datagen file `
    --vdb-engine milvus `
    --vdb-index HNSW `
    --config tests/configs/milvus_10k_hnsw.yaml `
    --milvus-uri $MilvusDb `
    --collection $Collection `
    --num-vectors 10000 `
    --dimension 1536 `
    --num-shards 1 `
    --vector-dtype FLOAT_VECTOR `
    --distribution uniform `
    --batch-size 500 `
    --chunk-size 2000 `
    --index-type HNSW `
    --force `
    --systemname native-windows-lite `
    --results-dir $ResultsDir
if ($LASTEXITCODE -ne 0) { throw "VectorDB datagen failed" }
```

## 6. Run the MLPerf Storage VectorDB query test

`--index-type` belongs to data generation. The run command identifies the
loaded index with `--vdb-index` and uses the existing local collection.

```powershell
& $Python -m mlpstorage_py.main open vectordb run file `
    --vdb-engine milvus `
    --vdb-index HNSW `
    --milvus-uri $MilvusDb `
    --collection $Collection `
    --num-query-processes 1 `
    --batch-size 10 `
    --queries 200 `
    --report-count 100 `
    --search-limit 10 `
    --search-ef 64 `
    --systemname native-windows-lite `
    --results-dir $ResultsDir
if ($LASTEXITCODE -ne 0) { throw "VectorDB run failed" }
```

The successful run prints `RESULT: valid`, with `failed_batches: 0` in the
benchmark statistics. A result tree is created below:

```text
<RunRoot>\results\open\MLCommons\results\native-windows-lite\vector_database\milvus\HNSW\
    datagen\<timestamp>\
    run\<timestamp>\
```

To locate the run metadata:

```powershell
Get-ChildItem -LiteralPath $ResultsDir -Recurse -Filter '*_metadata.json' |
    Where-Object FullName -Match '\\run\\' |
    Select-Object -ExpandProperty FullName
```

## 7. One-command PowerShell runner

After cloning the repository, the same workflow can be executed with:

```powershell
.\tests\run_milvus_10k_hnsw.ps1
```

The script creates a timestamped directory under `$env:TEMP`, installs the
native dependencies into `.venv` if needed, runs `init`, `datagen`, and
`run`, and prints the result directory. Use `-SkipInstall` when the
environment is already prepared:

```powershell
.\tests\run_milvus_10k_hnsw.ps1 -SkipInstall
```

## 8. Troubleshooting

### `milvus-lite is required`

Install the package explicitly into the same environment used to run the
benchmark:

```powershell
uv pip install --python $Python milvus-lite
```

### Vector dimension mismatch

Keep `--dimension` in `datagen` equal to `--vector-dim` in the modular runner
or the query dimension used by the MLPerf Storage run. The example uses
1,536 for both phases.

### Need a remote Milvus server

Omit `--milvus-uri` and use the remote endpoint instead:

```powershell
--host 127.0.0.1 --port 19530
```

Local `.db` URIs are single-node only.

### Disk I/O metrics are unavailable

Native Windows does not provide Linux `/proc/diskstats`, so the benchmark can
complete successfully while reporting disk I/O metrics as unavailable. This
does not invalidate the vector query result; it only limits host disk metric
collection for this local smoke test.
