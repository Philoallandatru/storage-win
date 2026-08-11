@echo off
REM ==============================================================================
REM  Common environment template for AI SSD case .cmd files.
REM  Each generated .cmd is self-contained; this file is documentation only.
REM ==============================================================================
REM  Required:
REM    PY   -> C:\Users\Administrator\Documents\Code\repos\storage\.venv\Scripts\python.exe
REM    DUT  -> root of the data directory on the SSD under test (e.g. G:\ai-ssd\data)
REM    RES  -> root of the result directory (must NOT be inside DUT) (e.g. D:\ai-ssd\results)
REM
REM  Flags the runner injects based on catalog:
REM    --execute          always required (planning-only without it)
REM    --confirm-dut      required for destructive cases (CKP 1-9)
REM    --scale-mb N       required for python_scaled cases (TRN-002/006-016, CKP-008/009, KV-009-022)
REM    --source-trace F   required for trace cases (VDB-015); default is logical_io_smoke.csv
REM
REM  Optional but recommended:
REM    --keep-data        skip auto-clean of python_scaled/ subtree (default = clean on exit)
REM    --prepare          run native datagen before the workload (native cases only)
REM    --duration-sec N   per-run wall clock (default 60s, used by inner runner)
REM    --repeat N         number of repetitions (default 3)
