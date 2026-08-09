# AI SSD Test Cases

本目录按 `docs/AI_SSD_TEST_PLAN.xlsx` 拆分为 72 个独立用例。

## 命名规则

每个脚本均为 `test_<类别>_<case_name>.py`：

每个脚本都带有稳定的 `case_no`（001–072），与 Excel 汇总表保持一致。

- `test_base_*.py`：基础路径、缓存和填充率
- `test_training_*.py`：训练供数
- `test_checkpoint_*.py`：Checkpoint 持久化与恢复
- `test_kv_*.py`：KV Cache tier 与尾延迟
- `test_vdb_*.py`：VectorDB 建库与查询
- `test_mixed_*.py`：前台/后台混合干扰

## 运行方式

默认只打印 native 执行计划，不会启动 workload：

```powershell
python ai_ssd_test_cases/test_training_unet3d_a100_baseline.py --mode plan
```

直接执行 native mlpstorage Case：

```powershell
mlpstorage init ai-trn-001 D:\ai_ssd\results
python ai_ssd_test_cases/test_training_unet3d_a100_baseline.py --mode execute --prepare --confirm-dut --data-dir <DUT_DATA> --results-dir <RESULTS>
```

脚本不会替用户初始化、清理或改写结果目录。

在 Windows DUT 上执行时，可显式选择结果目录和 MPI：

```powershell
python ai_ssd_test_cases/test_training_unet3d_a100_baseline.py --mode execute --prepare --confirm-dut --launcher single --data-dir D:\ai_ssd\data --results-dir D:\ai_ssd\results
```

脚本直接调用仓库的 `mlpstorage` 命令；没有对应 native 命令的 Case 会返回 `BLOCKED`，不会降级为标准库 probe 或 `whatif --dry-run`。

测试目的、编号步骤、测试时长、命令和通过标准保存在 `case_catalog.json`；脚本本身只负责直接调用对应的 native `mlpstorage` 命令。
