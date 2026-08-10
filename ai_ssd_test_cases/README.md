# Legacy AI SSD Case Entrypoints

This directory restores the Python entrypoints referenced by
`docs/AI_SSD_ALL_CASE_PLAN.xlsx`. Every file name contains both the workload
name and the model/profile, for example:

```text
test_ai_trn_004_retinanet_b200_jpeg.py
test_kv_option1_8b_nvme_only.py
test_vdb_diskann_1m_1536.py
test_mixed_training_checkpoint.py
```

## Native Case

Cases with a current MLPerf-native implementation delegate to the independent
entrypoint in `full_test_plan_cases/cases/`. The command still runs the real
workload and preserves stdout, stderr, manifest, and verdict files:

```powershell
python ai_ssd_test_cases\test_ai_trn_004_retinanet_b200_jpeg.py `
  --execute `
  --data-dir G:\MLPerfStorageTest\data\AI-TRN-004 `
  --result-dir E:\MLPerfStorageTest\results\AI-TRN-004 `
  --prepare
```

Native VectorDB cases use the remote Milvus endpoint configured by the
underlying MLPerf command. Start Milvus and map its data volume to the DUT
before running them.

## Python scaled Case

Cases without a current native MLPerf command require an explicit scale. The
runner never silently shrinks a formal workload:

```powershell
python ai_ssd_test_cases\test_ai_trn_006_cosmoflow_a100_tfrecord.py `
  --execute --scale-mb 256 `
  --data-dir G:\MLPerfStorageTest\data\AI-TRN-006 `
  --result-dir E:\MLPerfStorageTest\results\AI-TRN-006
```

The run is a real Python storage-pattern workload, but its manifest contains
`formal_status=NOT_FORMAL`. It must not be reported as a formal MLPerf PASS.

For a Python-started VectorDB fallback, use Milvus Lite explicitly:

```powershell
uv sync --extra vectordb-milvus
```

```powershell
python ai_ssd_test_cases\test_vdb_index_family_sweep.py `
  --execute --backend lite --scale-mb 32 `
  --data-dir G:\MLPerfStorageTest\data\AI-VDB-008 `
  --result-dir E:\MLPerfStorageTest\results\AI-VDB-008
```

## Evidence and safety

Each invocation writes a timestamped directory under
`<result-dir>/<case-id>/` containing `manifest.json` and `verdict.json`.
Destructive cases require `--confirm-dut`; data cleanup additionally requires
an explicit `--cleanup-root`.
