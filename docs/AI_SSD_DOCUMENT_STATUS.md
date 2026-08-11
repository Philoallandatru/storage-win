# AI SSD 文档状态与唯一入口

> 最后核对：2026-08-10

本页解决“应该看哪份文档、哪个目录才是当前实现”的问题。旧方案和历史执行记录仍保留用于审计，但不再作为当前 Case 数量、命令或执行状态的依据。

## 当前有效基线

| 用途 | 唯一入口 | 说明 |
|---|---|---|
| Native Case 目录 | [`full_test_plan_cases/case_catalog.json`](../full_test_plan_cases/case_catalog.json) | 当前 33 个直接调用 `mlpstorage open ...` 的 Case；Case ID、参数和状态以此为准 |
| Native Case 脚本 | [`full_test_plan_cases/cases/`](../full_test_plan_cases/cases/) | 每个 Case 一个独立入口，不使用旧的通用 workload 模拟器 |
| 日常 Windows 单 Case | [`full_test_plan_cases/README.md`](../full_test_plan_cases/README.md) / [`run_case.cmd`](../run_case.cmd) | 测试人员只输入 Case ID；路径、MPI、结果初始化和清理由 [`site_config.json`](../full_test_plan_cases/site_config.json) 提供 |
| Native 执行规则 | [`AI_SSD_TEST_EXECUTION.md`](AI_SSD_TEST_EXECUTION.md) | 门禁、四类 workload、证据和清理要求 |
| Native/Trace 分层 | [`AI_SSD_TEST_CASE_CATALOG.md`](AI_SSD_TEST_CASE_CATALOG.md) | 33 Native 与 1 个 Trace 的边界 |
| Trace Case | [`trace_test_cases/README.md`](../trace_test_cases/README.md) | 当前只有 `AI-VDB-015`；Trace Capture/Replay 不能冒充 Native 成绩 |
| 需求与判定 | [`AI_SSD_TEST_REQUIREMENTS.md`](AI_SSD_TEST_REQUIREMENTS.md) / [`AI_SSD_TEST_CASES_SUPPLEMENT.md`](AI_SSD_TEST_CASES_SUPPLEMENT.md) | 当前需求 ID、状态、证据和无效条件 |
| 最近实测快照 | [`AI_SSD_TEST_RUN_20260810.md`](AI_SSD_TEST_RUN_20260810.md) | 2026-08-10 的历史结果快照，不等同于当前机器配置或未来运行结果 |

## 当前 Case 数量

### MLPerf Native：33 个

| 家族 | 数量 | Case |
|---|---:|---|
| Training | 3 | `AI-TRN-003`–`AI-TRN-005` |
| Checkpoint | 7 | `AI-CKP-001`–`AI-CKP-007` |
| KV Cache | 8 | `AI-KV-001`–`AI-KV-008` |
| VectorDB | 15 | `AI-VDB-001`–`AI-VDB-014`、`AI-VDB-016` |

### Trace：1 个

`AI-VDB-015` 独立位于 `trace_test_cases/`，用于正式 VectorDB source trace 的 capture/replay。它的结论范围是条件性 SSD I/O 结果，不包含 Milvus 端到端 Recall/QPS 成绩。

## 历史资料：不再作为执行依据

以下文件描述的是早期 72 Case/18 项需求或旧 runner 方案。它们保留为设计演进和审计材料；其中的 Case ID、脚本名、命令、数量和“已通过”结论都不能直接用于当前执行。

| 历史文件 | 当前处理 |
|---|---|
| [`../archive/docs_historical/AI_SSD_TEST_PLAN.md`](../archive/docs_historical/AI_SSD_TEST_PLAN.md) | 72 Case 上位方案，历史参考 |
| [`../archive/docs_historical/AI_SSD_TEST_PLAN_SIMPLIFIED.md`](../archive/docs_historical/AI_SSD_TEST_PLAN_SIMPLIFIED.md) | 旧的“9 个实际 + 6 个模拟 Trace”子集，历史参考 |
| [`../archive/docs_historical/AI_SSD_TEST_PLAN_CASE_DESIGN.md`](../archive/docs_historical/AI_SSD_TEST_PLAN_CASE_DESIGN.md) | 旧 72 Case 设计附录，历史参考 |
| [`../archive/docs_historical/AI_SSD_REMAINING_CASE_SELECTION.md`](../archive/docs_historical/AI_SSD_REMAINING_CASE_SELECTION.md) | 旧的 BASE/CKP/KV/MIX 首轮选择，历史参考 |
| [`../archive/docs_historical/AI_SSD_TRAINING_CASE_SELECTION.md`](../archive/docs_historical/AI_SSD_TRAINING_CASE_SELECTION.md) | 旧 Training 首轮选择，历史参考 |
| [`../archive/docs_historical/AI_SSD_IO_PATTERN_ANALYSIS.md`](../archive/docs_historical/AI_SSD_IO_PATTERN_ANALYSIS.md) | 基于旧 72 Case 矩阵的 Pattern 分析，历史参考 |
| [`../archive/docs_historical/AI_SSD_WINDOWS_CASE_VALIDATION_20260807.md`](../archive/docs_historical/AI_SSD_WINDOWS_CASE_VALIDATION_20260807.md) | 旧 runner 的 Windows 验证记录；其中明确的 `SMOKE_PASS`/`whatif` 不属于正式 Native PASS |
| [`../archive/docs_historical/WINDOWS_TRAINING_PORT_20260802.md`](../archive/docs_historical/WINDOWS_TRAINING_PORT_20260802.md) | 旧 Windows Training 移植手册；原路径现在只保留当前入口说明 |
| `../archive/docs_historical/AI_SSD_TEST_PLAN*.xlsx/.pdf`、旧对外归纳表和旧矩阵 CSV | 早期导出/工作文件，不能覆盖 JSON Case catalog |
| [`../archive/docs_historical/AI_PC_CONSUMER_SSD_MULTI_STAGE_TEST_PLAN.md`](../archive/docs_historical/AI_PC_CONSUMER_SSD_MULTI_STAGE_TEST_PLAN.md) 及同组设计文档 | 消费级 AI PC 的独立设计资料；不作为当前 MLPerf Native Case 目录 |

## 执行前的最小检查

1. 先从 `full_test_plan_cases/case_catalog.json` 确认 Case ID 是否存在。
2. Windows 日常执行只使用 `.\run_case.cmd <CASE_ID>`；入口直接执行真实 workload。
3. `whatif` 和单元测试都不是性能 PASS。
4. 容量、MPI、Milvus 或 Windows 兼容性不满足时直接返回错误，不要改小正式参数后沿用原 Case ID。
5. Trace Capture、Trace Replay、Consumer orchestration 和 Native 结果必须分栏归档。

## 文档更新规则

- Case 数量、Case ID 和命令：先改 JSON/脚本，再同步 Markdown。
- 机器路径、MPI、时长、初始化和清理：只改 `site_config.json` 和执行说明，不把站点路径写死到案例说明中。
- 新增或删除 Case 后，必须同步更新本页、Case catalog、执行手册和测试记录索引。
- 新的实测结果应新建带日期的快照，不覆盖历史结果；历史快照不能反向修改当前基线。
