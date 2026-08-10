# Bundled native Windows VectorDB smoke test

The offline bundle contains pymilvus and milvus-lite. It can therefore run a
single-node MLPerf Storage VectorDB smoke test without WSL, Docker, or a
separate Milvus server.

After extracting and installing the bundle:

    powershell -ExecutionPolicy Bypass -File .\install.ps1 -InstallRoot C:\MLPerfStorage

Run the bundled test:

    & C:\MLPerfStorage\app\run-vdb.ps1

Or use the CMD wrapper:

    C:\MLPerfStorage\app\run-vdb.cmd

The runner creates a fresh local milvus_lite.db and executes:

1. mlpstorage init;
2. mlpstorage open vectordb datagen;
3. mlpstorage open vectordb run.

The default smoke workload is 10,000 1,536-dimensional vectors with HNSW and
200 queries. Results are written below a timestamped directory under %TEMP%.
Override the size for a smaller check, for example:

    & C:\MLPerfStorage\app\run-vdb.ps1 -NumVectors 1000 -Queries 20

This local URI path is single-node only. Remote or multi-node VectorDB runs
still use --host and --port with a separately managed Milvus service.
