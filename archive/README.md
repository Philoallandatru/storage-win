# Archive — 历史数据归档

> 归档时间：2026-08-11
> 归档依据：`docs/AI_SSD_DOCUMENT_STATUS.md`（当前有效基线 = `full_test_plan_cases/`，33 Native + 1 Trace）

本目录集中存放已被判定为"历史参考 / 不再作为执行依据"的文件，避免仓库根目录与 `docs/` 混杂。归档内容只作设计演进和审计材料，**其中的 Case ID、命令、数量和"已通过"结论均不能用于当前执行**。

## 目录结构

| 子目录 | 内容 |
|---|---|
| `root_artifacts/` | 根目录历史运行产物：`.smoke_*` 冒烟目录、`_*.log` / `_*.cmd` 调试文件、`output/` `outputs/` `mlps_test_results/` `hydra_log/` `tmp/` `checkpoints/` `data/` 等（均为 untracked/ignored 本地产物） |
| `docs_historical/` | `docs/` 下旧 AI SSD 计划/选择/归纳/运行记录：旧 72 Case 计划（`AI_SSD_ALL_CASE_PLAN.xlsx`、`AI_SSD_TEST_PLAN*.xlsx/md/pdf`）、`AI_SSD_REMAINING_*`、`AI_SSD_TRAINING_*`、`AI_SSD_CASE_对外归纳表*.xlsx`、`AI_SSD_IO_PATTERN_ANALYSIS.md`、运行记录（`SMOKE_RUN_20260811`、`TEST_RUN_20260810`、`WINDOWS_CASE_VALIDATION_20260807`）、消费级 AI PC 设计资料（`AI_PC_CONSUMER_SSD_*`）、旧矩阵 CSV、`WINDOWS_TRAINING_PORT_20260802.md` |
| `tools_historical/` | 依赖上述旧 xlsx 的旧构建脚本：`build_ai_ssd_all_case_plan.mjs`、`build_ai_ssd_training_case_table.mjs`、`build_ai_pc_consumer_ssd_matrix.mjs`、`build_standards_based_ai_pc_ssd_matrix.mjs`、`inspect_ai_pc_consumer_ssd_matrix.mjs`、`reword_ai_pc_consumer_ssd_matrix.mjs` |

## 当前有效入口（未归档）

- 33 Native Case 总表：`full_test_plan_cases/case_catalog.json`
- 33 Native 命令表：`docs/AI_SSD_NATIVE_CASES_MLPSTORAGE_COMMANDS.xlsx`
- 日常执行：`run_case.cmd <CASE_ID>`（配置见 `full_test_plan_cases/site_config.json`）
- Trace Case：`trace_test_cases/`（AI-VDB-015）
- 72 legacy .cmd 索引：`docs/AI_SSD_ALL_CASES_COMMANDS.md`（入口在 `ai_ssd_test_cases/cmd/`）

## 恢复方法

归档文件通过 `git mv` 移动，git 历史完整保留。需要找回时：

```bash
git mv archive/docs_historical/<file> docs/            # tracked 文件
mv archive/root_artifacts/<file> .                      # 本地产物
```
