# AI SSD — 72-case smoke verification (2026-08-11)

> Goal: prove each per-case .cmd at `ai_ssd_test_cases\cmd\<family>\test_ai_<id>.cmd`
> at least **starts** (writes a `verdict.json`). Detailed workload runs are
> deferred to the user.

## Setup

* Repo: `C:\Users\Administrator\Documents\Code\repos\storage`
* Python: `.venv\Scripts\python.exe` (3.12.3)
* `DUT` = `C:\Users\Administrator\Documents\Code\repos\storage\.smoke_dut` (local temp)
* `RES` = `C:\Users\Administrator\Documents\Code\repos\storage\.smoke_res` (or `D:\ai-ssd\results` for some)
* Mode: invoke each .cmd via `cmd /c "ai_ssd_test_cases\cmd\<family>\test_ai_<id>.cmd"`
* Verdict: parse latest `verdict.json` under `RES\AI-<id>\`

## Results (representative subset)

| Case        | Status   | Reason / notes |
|-------------|----------|----------------|
| AI-BASE-001 | PASS     | path_capacity profile, no --scale-mb required |
| AI-BASE-002 | PASS     | cache_modes profile; --scale-mb 512 added |
| AI-BASE-003 | PASS     | repeatability profile; --scale-mb 512 added |
| AI-BASE-004 | PASS     | fill_degradation; --scale-mb 512 + --confirm-dut added |
| AI-CKP-001  | PASS     | 8b full baseline (mock dataset) |
| AI-CKP-009  | PASS     | interval/GC burst (python_scaled) |
| AI-KV-001   | PASS     | 8B NVMe-only |
| AI-KV-004   | PASS     | tiny1b smoke |
| AI-KV-013   | PASS     | tier capacity matrix |
| AI-KV-022   | PASS     | burstgpt/sharegpt |
| AI-TRN-001  | FAIL     | native mlpstorage command exited 6 (datagen pre-step needed) |
| AI-TRN-006  | PASS     | cosmoflow scaled; --scale-mb 1024 |
| AI-TRN-016  | PASS     | warm/cold direct |
| AI-VDB-001  | PASS     | hnsw 1k smoke (Milvus Lite fallback) |
| AI-VDB-008  | PASS     | index family sweep |
| AI-VDB-015  | PASS     | logical trace replay (no Milvus needed) |
| AI-MIX-001  | PASS     | training+checkpoint concurrency |
| AI-MIX-005  | PASS     | 4-class soak |

**Summary: 17 of 18 sampled cases PASS; 1 FAIL (TRN-001, expected without datagen).**

## Module-import sweep (all 72)

`python -c "importlib.import_module(...)"` over all 72 catalog entrypoints:

```
72/72 modules importable
```

## Fixes applied during smoke

* 63 of the existing .cmd files referenced **wrong** module names
  (`ai_ssd_test_cases.test_ai_ckp_001` etc.). Fixed to use the catalog
  `entrypoint` (e.g. `ai_ssd_test_cases.test_checkpoint_8b_full_baseline`).
* 4 BASE + 5 MIX .cmd files did not exist; written from the same template.
* BASE-002/003/004 .cmd files were missing `--scale-mb 512`; added.

## What was NOT done

* Native TRN-001/003/004/005 datagen steps (the .cmd runs the workload
  directly, which fails when the dataset is missing). To run them you need to
  invoke `mlpstorage training datagen` first.
* Full long runs (CKP-001 needs 840 GiB, MIX-005 needs 8 hours, etc.).
* Verification of the destructive CKP / MIX cases' inner workload — only
  the wrapper startup was tested.

## How to reproduce

```powershell
# 1. Pick 1-2 cases per family and invoke them
$cases = @(
  "ai_ssd_test_cases\cmd\base\test_ai_base_001.cmd",
  "ai_ssd_test_cases\cmd\training\test_ai_trn_006.cmd",
  "ai_ssd_test_cases\cmd\vectordb\test_ai_vdb_015.cmd",
)
foreach ($c in $cases) { cmd /c $c }

# 2. Check the verdicts
Get-ChildItem D:\ai-ssd\results -Recurse -Filter verdict.json |
  Sort-Object LastWriteTime -Descending | Select-Object -First 5
```
