# AI SSD 测试用例目录

## 1. 用例分层

| 层 | 入口 | 结论范围 |
|---|---|---|
| Native | `full_test_plan_cases/cases/` | 真实 `mlpstorage open` workload |
| Trace Capture | 已验证的 `vdbbench-modular --io-trace-log` | 逻辑 I/O 来源，不是 SSD 成绩 |
| Trace Replay | `vdbbench.replay` | 固定逻辑 I/O 对目标 SSD 的条件性成绩 |
| Consumer orchestration | `tools/ai_ssd_cases/` | 仅保留已有真实 workload 的阶段化入口 |

## 2. 当前 Native 集合

当前 `full_test_plan_cases/case_catalog.json` 保留 33 个直接 Native Case：

| Family | Case | 覆盖 |
|---|---|---|
| Training | `AI-TRN-003`–`AI-TRN-005` | UNet3D/RetinaNet 的真实 datagen + run；正式规模需先过容量门禁 |
| Checkpoint | `AI-CKP-001`–`AI-CKP-007` | 8B/70B/405B/1T 配置的原生 checkpoint run；cold/间隔编排另行标注 |
| KV Cache | `AI-KV-001`–`AI-KV-008` | 原生 `mlpstorage open kvcache run` 参数可表达的 tier/users 场景 |
| VectorDB | `AI-VDB-001`–`AI-VDB-014`、`AI-VDB-016` | 原生 Milvus datagen/run；1K 链路、1M/10M 规模、索引/查询变量 |

Native 集合不包含 `whatif`、dry-run、环境 probe 或没有可表达参数的规划项。

## 3. Trace 集合

### AI-VDB-015：VectorDB logical trace replay（P0）

- Source：真实 `vdbbench-modular` Milvus run。
- Capture：记录 Insert、Flush、Load、Search；保存原始 config、source command、trace hash 和 event summary。
- Replay：`python -m vdbbench.replay <trace> --data-dir <DUT_DIR> --direct-io`。
- 主要指标：operation count、logical read/write bytes、P50/P95/P99、wall/active throughput、device bytes。
- 正确性：trace header、时间顺序、对象依赖和回放结果完整。
- 判定：`CONDITIONAL`；不能作为完整 VectorDB QPS/Recall 成绩。
- 清理：删除 replay data；保留 source trace 和 replay summary。

### KV Trace：当前仅为扩展要求，不登记为可执行 Case

KV benchmark 内部存在 tracer 实现，但当前 `mlpstorage open kvcache` CLI 未暴露
`--io-trace-log`，仓库也没有已验证的 KV replay 入口。因此不能把
`AI-KV-TRACE-001` 或独立的 Trace schema gate 写进当前可执行目录；补齐入口后再新增
真实脚本和对应测试。现有 `AI-VDB-015` 的脚本会对 source trace 做 schema/来源校验，
该校验是其执行前置条件，不单独冒充性能 Case。

## 4. Native 与 Trace 配对原则

同一业务场景必须保留配对关系：

```text
AI-VDB-001/002/003（Native）
        ↓ source workload
AI-VDB-015（Trace Capture/Replay）
```

Native 用于验证完整应用链路；Trace 用于固定存储压力、迁移到另一台机器和比较不同 SSD。两者的结果必须分栏报告。

## 5. 失败和未执行规则

- 没有对应真实命令：不生成脚本，留在规划矩阵；
- 只有 `whatif`：不生成执行 case；
- 环境命令：记录为 preflight，不记性能结果；
- 容量不足：`BLOCKED`/`NOT RUN`，不改小参数后冒充正式规模；
- Trace 只有逻辑记录：`TRACE-CAPTURE`，不记 SSD PASS；
- 真实执行但门槛失败：`FAIL`；
- 结果不完整或未命中 DUT：`INVALID`。
