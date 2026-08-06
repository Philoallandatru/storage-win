# AI SSD Test Cases

本目录按 `docs/AI_SSD_TEST_PLAN.xlsx` 拆分为 72 个独立用例。

## 命名规则

每个脚本均为 `test_<类别>_<case_name>.py`：

- `test_base_*.py`：基础路径、缓存和填充率
- `test_training_*.py`：训练供数
- `test_checkpoint_*.py`：Checkpoint 持久化与恢复
- `test_kv_*.py`：KV Cache tier 与尾延迟
- `test_vdb_*.py`：VectorDB 建库与查询
- `test_mixed_*.py`：前台/后台混合干扰

## 运行方式

默认只生成执行计划和 manifest，不会启动重负载：

```powershell
python ai_ssd_test_cases/test_training_unet3d_a100_baseline.py
```

执行可重复的 scaled smoke probe：

```powershell
python ai_ssd_test_cases/test_training_unet3d_a100_baseline.py --execute --prepare --data-dir <DUT_DATA> --result-dir <RESULTS>
```

`--execute` 的 Checkpoint/KV/VectorDB/Mixed 脚本使用标准库实现小规模 probe，结果用于验证路径、读写、尾延迟和并发逻辑；Checkpoint 默认最多写 8 个缩放分片，只有在授权 DUT 上才使用 `--full-scale`。正式容量、模型、Milvus 索引或 MLPerf SLA 测试应替换为批准的 workload，并保留同一 Case ID。

所有脚本都包含测试目的、编号步骤、测试时长、命令和通过标准；完整字段可查 `case_catalog.json`。
