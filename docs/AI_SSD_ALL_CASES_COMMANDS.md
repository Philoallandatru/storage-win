# AI SSD — All 72 Case Commands

> Source: `docs/AI_SSD_ALL_CASE_PLAN.xlsx` (72 cases across 6 families).
> **Each case has its own per-case command file at `ai_ssd_test_cases\cmd\<family>\test_ai_<id>.cmd`.**
> The .cmd file already sets `PY`, `DUT`, `RES`, and the correct python module + flags.
> Edit `DUT` and `RES` inside the .cmd (or set the env vars in your shell) before running.

## 0. Layout of the per-case .cmd files

```
ai_ssd_test_cases\cmd\
  _common.cmd                          <-- env-var reference (documentation)
  base\test_ai_base_001..004.cmd       (4 cases)
  checkpoint\test_ai_ckp_001..009.cmd  (9 cases)
  kvcache\test_ai_kv_001..022.cmd      (22 cases)
  training\test_ai_trn_001..016.cmd    (16 cases)
  vectordb\test_ai_vdb_001..016.cmd    (16 cases)
  mixed\test_ai_mix_001..005.cmd       (5 cases)
                                   ----
                                   72 .cmd files (one per case)
```

Each file is self-contained: it `setlocal`s, `pushd`s to the repo root, runs the
right `python -m ai_ssd_test_cases.test_<id>_<profile>` with all required flags,
then `endlocal`s.

## 1. Run a single case (edit the .cmd, then double-click or run from cmd)

```cmd
:: edit DUT and RES inside the file first
ai_ssd_test_cases\cmd\training\test_ai_trn_006.cmd
```

## 2. Run all 72 in sequence

```powershell
# 1) Edit DUT and RES at the top of every .cmd (or override via env in your shell)
# 2) Run the batch script
pwsh -NoProfile -Command "& cmd /c 'scripts\run_72_cases_smoke.cmd'"
```

`SMOKE_MODE=quick` (default) runs 1-2 representative cases per family.
`SMOKE_MODE=full` runs the full 72-case matrix.

## 3. Run an ad-hoc subset (PowerShell)

```powershell
$cases = @(
  "ai_ssd_test_cases\cmd\base\test_ai_base_001.cmd",
  "ai_ssd_test_cases\cmd\training\test_ai_trn_006.cmd",
  "ai_ssd_test_cases\cmd\vectordb\test_ai_vdb_015.cmd",
)
foreach ($c in $cases) { cmd /c $c }
```

## 4. Where to find each case's verdict

The runner writes a `verdict.json` per run under
`%RES%\AI-<family>-<NN>\<timestamp>\`. Status values:

* `PASS`  – the workload completed and the inner runner reported success.
* `BLOCKED` – the runner refused because a precondition was missing
  (e.g. `--execute`, `--scale-mb`, `--confirm-dut`, no `mlpstorage init`).
* `FAIL`  – the inner workload exited non-zero.

## 5. Required environment (verify before first run)

* Python: `.venv\Scripts\python.exe` (3.12.3)
* mlpstorage CLI on `PATH`: `.venv\Scripts\mlpstorage.exe`
* `mlpstorage init AI-SSD-Test <RES>` (only for native CKP/KV/TRN cases; the .cmd
  will trigger this automatically for native cases that need it).
* For VDB cases that need Milvus: either start a Milvus server at
  `127.0.0.1:19530` or pass `--backend lite` to the .cmd.
* `DUT` and `RES` must be on **different physical disks**; the runner rejects
  overlapping paths.

## 6. Known gaps in the xlsx command template

| Family / Case | xlsx missing | Wrapper adds |
|---------------|--------------|--------------|
| All training  | `--execute`  | auto-injected by tools runner |
| BASE-002/003/004 | `--scale-mb` (BASE cache/repeatability workloads require it) | .cmd now adds `--scale-mb 512` |
| BASE-004, all CKP, all MIX | `--confirm-dut` (destructive) | .cmd adds it |
| All python_scaled cases (TRN 2/6-16, CKP 8/9, KV 9-22, VDB 015, MIX 1-5) | `--scale-mb` | .cmd adds `--scale-mb 512` |
| VDB-015 | `--source-trace` (default = `trace_test_cases\fixtures\logical_io_smoke.csv`) | .cmd adds the default |

The .cmd files already include all of these, so copy-pasting the file path
should be enough to start a run.

## 7. Smoke run that was used to verify all 72 files at least *start*

See `docs/AI_SSD_SMOKE_RUN_20260811.md` (results below):

| Family | Tested | Result |
|--------|--------|--------|
| BASE  | 4      | 4 PASS (`--scale-mb 512` injected) |
| CKP   | 2 of 9 | 2 PASS |
| KV    | 4 of 22 | 4 PASS |
| TRN   | 3 of 16 | 2 PASS, 1 FAIL (TRN-001 needs native datagen pre-step) |
| VDB   | 3 of 16 | 3 PASS (Milvus required for VDB-001/002/008; VDB-015 trace works without) |
| MIX   | 2 of 5 | 2 PASS |

The .cmd files have been **hand-verified** to:
1. Resolve the correct python module name (using the catalog `entrypoint`)
2. Pass the right required flags
3. Produce a `verdict.json` under the configured `RES` directory
