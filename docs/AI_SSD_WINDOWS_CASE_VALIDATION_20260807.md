# AI SSD Windows Case 验证记录

> 历史记录（2026-08-07）。本记录中的 `SMOKE_PASS`、`REPO_TRY_PASS` 和 `whatif --dry-run` 不属于正式 MLPerf Storage 结果；当前 native Case 已改为直接调用 `mlpstorage`，本文件不能作为正式 PASS 证明。

日期：2026-08-07
平台：Windows
脚本数量：72 个

## 序号规则

序号与脚本、`case_catalog.json`、Excel 汇总表保持一致：

- 001–016：Training
- 017–020：BASE
- 021–029：Checkpoint
- 030–051：KV Cache
- 052–067：VectorDB
- 068–072：Mixed

## 验证结果

| 验证项 | 范围 | 结果 |
|---|---:|---|
| Windows 计划模式 | 72/72 | PASS |
| 脚本编译检查 | 72/72 | PASS |
| 精选 case 缩小执行 | 29/29 | PASS |
| 结果 manifest 的 `case_no` | 29/29 | PASS |
| 分类执行入口（BASE/Checkpoint/KV/VectorDB/Mixed） | 5/5 | SMOKE_PASS |
| 实际 Windows 训练供数 + PhysicalDisk 采集 | AI-TRN-001 | 历史 probe，不是 formal PASS |
| 仓库真实 CLI `whatif --dry-run` 构造 | Training/Checkpoint/KV/VectorDB | 4/4 PASS |

精选 case 的缩小执行参数：`--execute --prepare --duration-sec 5 --repeat 1 --sample-mib 1 --sample-points 100`。最终结果保存在 `outputs/ai_ssd_case_validation_20260807/selected_final/`，29 个 manifest 均为 `SMOKE_PASS`，`formal_status=NOT_EVALUATED`。

AI-TRN-001 实际运行使用 `--monitor-windows`，已生成 PhysicalDisk CSV 和 ETL；训练供数结果包含 workers=1/2/4、吞吐、IOPS、P99 和实际运行耗时。完整原始结果保存在 `outputs/ai_ssd_case_validation_20260807/actual_trn001_integrated/`。

本次 5 秒/点实测吞吐为 workers=1/2/4：`384.157 / 521.537 / 678.344 MiB/s`，对应 P99：`0.417 / 0.544 / 0.800 ms`。PhysicalDisk 汇总显示平均读约 `1.2 KiB/s`、平均写约 `1.65 MiB/s`、峰值队列 `0`；这说明该短测的部分数据由系统缓存提供，不能替代 cold/direct SSD 资格测试。

新增的仓库 CLI 试跑通过每个脚本的 `--repo-try-run` 触发，实际调用当前仓库 `.venv` 中的 `mlpstorage_py.main`：Training 使用 DLIO workload，Checkpoint 使用 checkpointing workload，KV Cache 使用三选项 wrapper，VectorDB 使用 Milvus/vdbbench 命令构造。输出写入 `outputs/ai_ssd_case_validation_20260807/repo_try_*` 和 `D:\ai_ssd_try\runner_*`。KV Cache 在 Windows what-if 模式会返回“没有生成 rank 结果文件”的内部非零码，但日志已确认三条 `Dry-run mode` 命令被构造，因此 runner 将其判定为 `REPO_TRY_PASS`；这不是正式 KV 结果。

## 结果边界

本轮验证确认了 Windows 路径、脚本入口、序号、结果 manifest、缩小版读写逻辑、基本并发逻辑，以及仓库真实 CLI 的参数映射和命令构造可执行；不等同于正式性能认证。

本记录中的旧 runner 已废弃。当前 Case 入口直接调用 `mlpstorage`；没有对应 native 命令的 Case 直接 `BLOCKED`。

旧的 `--repo-try-run` 只负责 CLI 参数校验和命令构造，不代表 workload 结果；当前正式执行请使用 `full_test_plan_cases/cases/` 中的 direct native Case。

正式测试仍需接入批准的真实 workload：

- Training：真实 MLPerf/DLIO 训练与 AU 采集；
- Checkpoint：真实模型分片、TB 级容量和 cold-cache 方法；
- KV Cache：真实 KV Cache/MLPerf workload；
- VectorDB：真实 Milvus/index workload；
- Mixed：真实前台/后台 workload 共存；
- PhysicalDisk、ETW、Direct I/O 和 pSLC 配置：Windows DUT 上的正式采集与门禁。
