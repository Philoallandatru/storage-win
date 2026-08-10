# AI SSD 测试需求与用例设计评估

评估日期：2026-08-10  
评估对象：`AI_SSD_TEST_REQUIREMENTS.md`、`AI_SSD_TEST_EXECUTION.md`、`AI_SSD_TEST_CASE_CATALOG.md`、Native/Trace 入口和实际执行记录

## 1. 一致性检查

| 检查项 | 结果 | 证据 |
|---|---|---|
| 需求都有稳定 ID | 通过 | `TR-AI-SSD-001`–`012` |
| Native 与 Trace 分层 | 通过 | 33 个 Native + `trace_test_cases` 独立集合 |
| `whatif`/dry-run 不算测试结果 | 通过 | 需求状态和 Native README 均明确 |
| VectorDB Trace 来源可追溯 | 通过/有边界 | `vdbbench-modular --io-trace-log`、source trace、hash/manifest 要求；当前机器未监听 Milvus，因此本次复用了仓库已有正式 source trace |
| Trace Replay 指标可观测 | 通过 | operation、逻辑字节、P50/P95/P99、device bytes |
| 结果状态可区分 | 通过 | PASS/FAIL/BLOCKED/INVALID/CONDITIONAL/NOT RUN |
| 容量规则与实际配置一致 | 已修复 | 生成器接受 YAML 行尾注释，`AI-TRN-003=7200` |
| 结果初始化前置条件显式 | 已修复 | Native `--init-results` 调用原生 `mlpstorage init` |
| 测试数据有收尾 | 已修复 | Native `--cleanup-data`；Trace `--cleanup`；本次实际目录已删除 |

## 2. 可执行性检查

### 已可执行

- Native 33 个入口均包含原生 `mlpstorage open ...` 命令；结构测试通过。
- VectorDB Trace replay 已在 Windows 上实际退出码 0；当前可执行 Trace 目录只保留 `AI-VDB-015`。
- KV Native 已实际进入正式 workload，产生真实 Tier-2 entries、读写字节和设备延迟。
- 生成器会从当前 YAML 读取带行尾注释的文件规模。

### 有明确外部前置条件

- Training/Checkpointing：需要 MPI；正式规模还需要数据容量和 DLIO 配置。
- VectorDB Native/Trace capture：需要 Milvus 在目标 host/port ready；`mlpstorage` 不负责自动启动服务。
- KV Native：正式 option 序列耗时较长，需在有足够容量的机器上用交互式终端或长超时运行。

### 当前不可在本机形成完整成绩的项目

- `AI-TRN-003`：当前合法配置约 984 GiB，本机没有足够单一测试盘空间；应为 `BLOCKED/NOT RUN`。
- `AI-CKP-004`–`007`：405B/1T 的完整 10 write + 10 read 需要容量和 MPI rank 条件，本机未执行。
- VectorDB Native：Milvus 端口当前未监听，未执行新的 Native run/capture。
- KV Trace：底层 tracer 存在，但当前 mlpstorage CLI 未暴露 `--io-trace-log`，且没有已验证的 KV replay 入口，因此未生成可执行 KV Trace Case。
- KV-001：本次工具 30 分钟上限打断了完整 3 options × 3 trials；已保留部分真实证据并标为 `INCOMPLETE/TIMEOUT`。

## 3. 落地性结论

当前设计达到“可执行、可审计、可迁移”的基础要求，但不能把所有 33 个入口都宣称为本机已经完成。落地时必须按照以下顺序：

1. 先执行环境和容量门禁；
2. 选择一个能完整满足容量的 workload；
3. 先完成 Native baseline；
4. 再 capture/replay Trace；
5. 最后扩展参数扫描、混合负载和 soak。

不能把以下内容当作正式结果：

- 只有 plan/preflight/dry-run 的运行；
- 只有 `whatif` 的估算；
- 只有 source trace、没有 replay 的 Capture；
- scaled/replay 当成 Native；
- 部分 trial 或单个 option 当成完整 KV 序列；
- 容量门禁失败后手工缩小参数却继续沿用正式 Case ID。

## 4. 最终审查结论

设计文档、执行手册和用例目录之间的术语、状态和证据要求已经统一；Native 与 VectorDB Trace 也已分离。实际运行证明了两类重要事实：

- VectorDB Trace replay 路线在当前 Windows 环境可落地并可清理；
- KV Native 路线能够真实命中 Tier-2，但正式全序列需要更长执行窗口，且当前结果已显示明显 QoS/设备延迟失败趋势。

因此当前版本可以作为测试执行基线，但最终产品结论仍需在完整容量、完整 KV 序列、MPI/ Milvus 条件满足后补齐；本评估不把未完成项目包装成已完成。
