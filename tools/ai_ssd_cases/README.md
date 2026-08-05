# Consumer AI-PC SSD executable cases

This directory contains one launchable Python file for every case in the
consumer AI-PC matrix (29 core cases plus 8 optional cases). The files under
`cases/` are intentionally small entry points; `runner.py` provides the common
implementation so that preflight, command construction, monitoring and result
format stay consistent.

## Quick start

Run a safe preflight or command preview first:

```powershell
python tools/ai_ssd_cases/cases/s0_env_01.py `
  --dut-root C:\ai_ssd_dut `
  --results-root C:\ai_ssd_results `
  --mode preflight

python tools/ai_ssd_cases/cases/s2_trn_01.py `
  --dut-root C:\ai_ssd_dut `
  --results-root D:\ai_ssd_results `
  --mode dry-run
```

Execute a native smoke with Windows ETW/PhysicalDisk capture:

```powershell
python tools/ai_ssd_cases/cases/s2_ckpt_01.py `
  --dut-root C:\ai_ssd_dut `
  --checkpoint-dir C:\ai_ssd_checkpoint `
  --results-root D:\ai_ssd_results `
  --monitor
```

Cases that write/overwrite a test directory, fill the device, reboot the host
or run a long soak require an explicit `--confirm-destructive`. This prevents
an accidental case launch from consuming TBW or destroying unrelated data.

## Common options

| Option | Meaning |
|---|---|
| `--dut-root` | Root on the target SSD; data/cache/checkpoint subdirectories default below it |
| `--results-root` | Evidence directory; keep it off the DUT whenever possible |
| `--mode execute` | Run the underlying workload (default) |
| `--mode dry-run` | Print and record commands without running them |
| `--mode preflight` | Only validate paths, tools and safety gates |
| `--monitor` | Wrap the command with `tools/record_windows_io.ps1` |
| `--trace` | Logical CSV for VDB/KV/checkpoint replay cases |
| `--direct` | Request direct/unbuffered behavior where the backend supports it |
| `--extra-arg ARG` | Append a backend-specific argument without editing the case file |

Each invocation creates:

```text
<results-root>/<case-id>/<run-id>/
├── manifest.json
├── verdict.json
├── command_*.stdout.log
├── command_*.stderr.log
└── windows_io/                 # when --monitor is used
    ├── *.etl
    ├── *.physicaldisk.csv
    └── *.manifest.json
```

`PASS` means the underlying command returned zero. Business thresholds such as
AU, Recall, KV P99, checkpoint hash and physical-DUT attribution remain in the
case verdict review; a zero exit code alone is not a product PASS.

## Case index

The entry-point filename follows the case ID in lowercase with separators
changed to underscores. The complete machine-readable catalog is in
`catalog.py`.

| Stage | Case files |
|---|---|
| Stage 0 | `s0_env_01.py`, `s0_cap_02.py`, `s0_config_03.py` |
| Stage 1 | `s1_io_01.py`–`s1_io_04.py` |
| Stage 2 | `s2_trn_01.py`, `s2_ckpt_01.py`, `s2_kv_01.py`, `s2_vdb_01.py` |
| Stage 3 | `s3_trn_01.py`–`s3_trn_03.py`, `s3_ckpt_01.py`–`s3_ckpt_03.py`, `s3_kv_01.py`–`s3_kv_03.py`, `s3_vdb_01.py`–`s3_vdb_02.py` |
| Stage 4 | `s4_mix_01.py`–`s4_mix_03.py` |
| Stage 5 | `s5_soak_01.py`, `s5_soak_02.py` |
| Stage 6 | `s6_rec_01.py`, `s6_rec_02.py` |
| Optional | `o_trn_04.py`, `o_trn_05.py`, `o_ckpt_04.py`, `o_ckpt_05.py`, `o_kv_04.py`, `o_kv_05.py`, `o_vdb_03.py`, `o_soak_03.py` |

## Scope boundary

The scripts invoke the repository's real `mlpstorage`, `vdbbench` and Docker
commands where the current Windows implementation supports them. A large
model “subset” is not silently emulated as a full model: if no subset fixture
or trace is supplied, the case returns `NOT_RUN` and explains how to provide
one. Similarly, replay results are labeled as logical SSD replay and are never
reported as native model performance.
