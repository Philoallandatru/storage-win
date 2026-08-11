# AI SSD Training Case Plan — Review and Corrections

> Source: `docs/AI_SSD_ALL_CASE_PLAN.xlsx`, sheet `Training Case表` (16 cases).
> Implementation: `ai_ssd_test_cases/training/test_training_ai_trn_*.py`
>                (one wrapper per case, sharing `ai_ssd_test_cases/training/_common.py`).
> Tests: `tests/unit/test_training_wrappers.py` (10 unit tests).
> Smoke: `scripts/run_16_training_smoke.py` (inline runner; 8 s end-to-end on this host).

This document explains where the spreadsheet diverges from the runnable
code path, why, and how the 16 new wrappers compensate.  The
corrections are **recorded inside each wrapper's docstring** so a
reader who only opens the wrapper file still sees them; the doc
collects the rationale in one place.

---

## 1. Where the spreadsheet got it right

* The 16 Case IDs (`AI-TRN-001` … `AI-TRN-016`) and the case ordering
  match the catalog (`ai_ssd_test_cases/catalog.py`).
* The model families (UNet3D, RetinaNet, CosmoFlow, ResNet50, DLRM,
  Flux) and data formats (npz / jpeg / tfrecord / parquet) are correct.
* Four cases are flagged as real native MLPerf entries
  (`AI-TRN-001/003/004/005`); the other twelve are correctly marked
  `python_scaled` (no current native implementation).
* Capacity hints in the `Capacity` column (1 TB / 2 TB / 4 TB) describe
  the *target SSD* for the storage device being measured, not the
  dataset size.  The wrappers respect this by recording the dataset
  size separately in `CaseInfo.capacity_gib`.

## 2. Where the spreadsheet is wrong or misleading

The list below is ordered by impact; each item references the
xlsx row, the wrapper that addresses it, and the corresponding
`CaseInfo` in `ai_ssd_test_cases/training/_common.py`.

### 2.1 The "测试命令" column is non-executable

The xlsx row template is

```
python tools/ai_ssd_training_case_runner.py --case <ID> --data-dir <DUT_DATA> --result-dir <RESULTS> --duration-sec 300 --repeat 3
```

Three flags are missing in **every** row, and the runner rejects the
call without them:

| Missing flag | Required for | Effect of omission |
|---|---|---|
| `--execute` | every call | inner runner refuses with `--execute is required` |
| `--prepare` | native cases (TRN-001/003/004/005) | datagen never runs; the call still appears to start |
| `--confirm-dut` | destructive cases (BASE-004, CKP, MIX) | not relevant for Training (catalog marks the family non-destructive) |

The wrapper injects `--execute` and `--prepare` automatically.  The
operator still controls `--prepare` via the flag.

### 2.2 The xlsx "测试命令" mixes native and python_scaled flows

`ai_ssd_test_cases/catalog.py` lists twelve Training cases as
`python_scaled`, but the xlsx "测试命令" column sends them through the
native training wrapper, which then BLOCKS on
`this case has no formal native entry; pass --scale-mb explicitly`.

**Wrapper fix**: the wrapper defaults `--scale-mb 1024` (or 4096 for
parquet-heavy cases) and emits a clear
`WARNING: ... is python_scaled and will be rejected by the inner
runner without --scale-mb` when the caller omits the flag.  The
inner runner's own error message is preserved in `verdict.json` so
the failure mode is auditable.

### 2.3 Capacity column is the target SSD, not the dataset size

The xlsx `Capacity` column reads `1TB / 2TB / 4TB` for every case.  This
is misleading for cases whose dataset is much smaller than the SSD
(`AI-TRN-002` is a 168-file, ~22.9 GiB scaled workload) or much larger
than the SSD (`AI-TRN-003` is 983 GiB and will not fit on a 1 TB
consumer NVMe).

**Wrapper fix**: `CaseInfo.capacity_gib` records the *dataset* size in
GiB separately from the SSD column in the xlsx.  The wrapper docstring
calls out the contradiction where it exists (`AI-TRN-003`,
`AI-TRN-004`, `AI-TRN-005`).  A unit test
(`test_dataset_size_does_not_equal_target_ssd`) guards against the two
ever being conflated again — the dataset size must always be
< 1000 GiB.

### 2.4 The "测试标准" column is not enforced anywhere

Rows claim pass thresholds such as `AU≥90%`, `AU≥85%`, `AU≥70%`.
These are not encoded in the codebase.  A wrapper that calls
`run_case(case_id, argv)` will return `BLOCKED` on the inner runner
*before* any of these thresholds are evaluated.

**Wrapper fix**: the wrappers do not invent new thresholds.  They emit
`verdict.json` with the inner runner's status, and the docstring
states that the thresholds are aspirational until the real DLIO path
is wired in.  The `formal_status` field is set to `FORMAL` for native
runs that pass and `NOT_FORMAL` for `python_scaled` runs that pass,
so the boundary is explicit at the verdict level.

### 2.5 "测试步骤" with multi-stage sweeps is not expressible in the Python-scaled harness

`AI-TRN-014` (concurrency 1..16), `AI-TRN-015` (read_threads 1..32), and
`AI-TRN-016` (warm / cold / direct) all describe multi-stage sweeps.  The
current Python-scaled harness (`_file_profile` in
`ai_ssd_test_cases/runner.py`) produces a single point per `--scale-mb`
call.  The wrappers cannot honestly reproduce the sweep, so they
document the limitation in the docstring and labels the run
`formal_status: NOT_FORMAL`.

### 2.6 The "测试工具" column says `mlperform`; the real tool is `mlpstorage`

`AGENTS.md` documents `mlpstorage` as the entry point.  The xlsx uses
the historical name `mlperform`.  This is a documentation drift, not a
behavioural one.  The wrappers use the real runner
(`tools/ai_ssd_training_case_runner.py`) and call out the drift in the
module docstring of `__init__.py`.

### 2.7 Windows `multiprocessing_context: fork` is undocumented in the xlsx

`configs/dlio/workload/{unet3d_a100,unet3d_b200,retinanet_b200,retinanet_mi355}.yaml`
all hard-code `multiprocessing_context: fork`.  The xlsx plan does not
mention this; on Windows it manifests as a process-spawn failure after
datagen completes (see `docs/AI_SSD_TEST_RUN_20260810.md`).

**Wrapper fix**: each native wrapper's docstring names the fork file
and predicts the failure mode.  The wrapper itself cannot fix the
fork issue; the YAML or DLIO promotion logic must.

### 2.8 Destructive flag is mis-assigned in the original xlsx

The xlsx does not flag any Training case as destructive.  The catalog
(`ai_ssd_test_cases/catalog.py`) marks the whole Training family as
`destructive=False`; only `AI-BASE-004`, all Checkpoint cases, and
all Mixed cases are destructive.  The wrappers were corrected to
match the catalog; this is locked by
`test_training_cases_are_not_destructive`.

## 3. The fix the xlsx itself needs

The xlsx is a static artifact; we cannot auto-regenerate it.  The
following edits would bring the spreadsheet in line with the codebase:

| Sheet | Row(s) | Change |
|---|---|---|
| Training Case表 | every row | Append `--execute --prepare --confirm-dut` to the "测试命令" cell, where appropriate. |
| Training Case表 | rows 2, 6-16 | Add `--scale-mb <MiB>` to the "测试命令" cell. |
| Training Case表 | every row | Rename "测试工具" from `mlperform` to `mlpstorage` (or `tools/ai_ssd_training_case_runner.py`). |
| Training Case表 | every row | Add a "Blocker" column: `fork / capacity / scale` so reviewers can predict the failure mode. |
| Training Case表 | rows 1, 3, 4, 5 | Note that the dataset is 983 GiB / 352 GiB and the SSD must be at least 1.2x that. |
| Training Case表 | every row | Replace the absolute AU thresholds with `<<see catalog AU threshold>>` or remove them. |
| Training Case表 | rows 14, 15, 16 | Mark "partial coverage" — the Python-scaled harness does not implement a sweep. |

The "BASE / Checkpoint / KV / VectorDB / Mixed" sheets have analogous
gaps; the same review pass should be applied before they get wrapper
scripts.

## 4. Smoke run, 2026-08-11

| Case | execution | wall | wrapper rc | wrapper status | verdict formal_status | notes |
|---|---|---:|---:|---|---|---|
| AI-TRN-001 | native_special | 0.54s | 1 | FAIL | EXPECTED_FAIL | mlpstorage init missing in inline smoke; E101 fail-fast |
| AI-TRN-002 | python_scaled | 0.58s | 0 | PASS | NOT_FORMAL | 256 MiB synthetic; wrapper auto-cleaned |
| AI-TRN-003 | native | 0.18s | 0 | PASS | EXPECTED_FAIL | init check tolerant; ran into DLIO skip_listing check (no data) |
| AI-TRN-004 | native | 0.18s | 0 | PASS | EXPECTED_FAIL | same as TRN-003 |
| AI-TRN-005 | native | 0.18s | 0 | PASS | EXPECTED_FAIL | same as TRN-003 |
| AI-TRN-006 | python_scaled | 0.56s | 0 | PASS | NOT_FORMAL | 256 MiB; auto-cleaned |
| AI-TRN-007 | python_scaled | 0.58s | 0 | PASS | NOT_FORMAL | same |
| AI-TRN-008 | python_scaled | 0.60s | 0 | PASS | NOT_FORMAL | same |
| AI-TRN-009 | python_scaled | 0.58s | 0 | PASS | NOT_FORMAL | same |
| AI-TRN-010 | python_scaled | 0.59s | 0 | PASS | NOT_FORMAL | 512 MiB |
| AI-TRN-011 | python_scaled | 0.60s | 0 | PASS | NOT_FORMAL | 512 MiB |
| AI-TRN-012 | python_scaled | 0.57s | 0 | PASS | NOT_FORMAL | 512 MiB |
| AI-TRN-013 | python_scaled | 0.60s | 0 | PASS | NOT_FORMAL | 512 MiB |
| AI-TRN-014 | python_scaled | 0.58s | 0 | PASS | NOT_FORMAL | 256 MiB |
| AI-TRN-015 | python_scaled | 0.61s | 0 | PASS | NOT_FORMAL | 256 MiB |
| AI-TRN-016 | python_scaled | 0.60s | 0 | PASS | NOT_FORMAL | 256 MiB |

15 of 16 wrappers exit cleanly; 1 (`TRN-001`) hits the `mlpstorage
init` check because the inline smoke driver does not run `mlpstorage
init` (the end-to-end PS1 script does).  No wrapper hung, no wrapper
crashed, every case wrote both `manifest.json` and `verdict.json`,
and the host disk was 389.41 GiB free both before and after the run.

## 5. Why the wrappers live in a sub-package

The repository already has
`ai_ssd_test_cases/test_ai_trn_001_unet3d_a100.py` … `test_ai_trn_016_warm_cold_direct.py`.
Those files are 8 lines of
`from .runner import main_from_filename; main_from_filename(__file__)`;
they exist so the project-legacy runner can dispatch by filename.

The new wrappers deliberately sit in `ai_ssd_test_cases/training/`
with a different naming convention because they:

* use `subprocess.run` to launch the workload in a separate process,
  matching the user's "Python launches a terminal command" intent;
* expose a stable public argparse surface that the unit test suite
  pins down (see `tests/unit/test_training_wrappers.py`);
* carry a per-case docstring that names the blocker (fork / capacity /
  python-scaled) without re-reading the spreadsheet.

The two sets can coexist: the legacy `test_ai_trn_*.py` files continue
to dispatch through the runner, the new `test_training_*.py` files
launch a real subprocess and own their own manifest.  Future
iterations can adopt the same convention for Checkpoint (9 cases),
KV Cache (22 cases), and VectorDB (16 cases) — three sibling
sub-packages with the same `_common.py` shape.
