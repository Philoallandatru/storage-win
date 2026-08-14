# AI SSD Case 变种矩阵（容量 × 内存）

> 生成：2026-08-13 · 配套 `full_test_plan_cases/matrix_catalog.json` 与 `scripts/run_ai_ssd_suite.py`
> 矩阵定义：每个 case 按 **容量档（512GB / 1TB / 2TB / 4TB）× 内存档（32GB / 64GB / 128GB）** 组合成变种，共 **4 × 3 = 12 个场景**。

## 一、矩阵总览

| 场景 | 容量档 | 内存档 | case 集 | 内存覆盖参数 |
|---|---|---|---|---|
| S01 | 512GB | 32GB | 34 基础 case | `--client-memory-gb 32` / `--cpu-mem-gb 32` |
| S02 | 512GB | 64GB | 34 基础 case | `--client-memory-gb 64` / `--cpu-mem-gb 64` |
| S03 | 512GB | 128GB | 34 基础 case | `--client-memory-gb 128` / `--cpu-mem-gb 128` |
| S04 | 1TB | 32GB | 12 case（每家族 3：Training unet3d/retinanet/DLRM、Checkpoint 8b/70b/405b、KV ×3、VDB ×3） | 同上（按家族） |
| S05 | 1TB | 64GB | 同上 | 同上 |
| S06 | 1TB | 128GB | 同上 | 同上 |
| S07 | 2TB | 32GB | 12 case（每家族 3） | 同上（按家族） |
| S08 | 2TB | 64GB | 同上 | 同上 |
| S09 | 2TB | 128GB | 同上 | 同上 |
| S10 | 4TB | 32GB | 12 case（每家族 3） | 同上（按家族） |
| S11 | 4TB | 64GB | 同上 | 同上 |
| S12 | 4TB | 128GB | 同上 | 同上 |

> **覆盖保证**：每个容量档 × 每个测试类型（Training/Checkpoint/KV Cache/VectorDB）**至少 3 个 case**（见 `capacity_catalog.json`）。

## 二、各家族的内存参数映射

| 家族 | 内存参数 | 32GB / 64GB / 128GB 的语义 |
|---|---|---|
| Training（run 阶段） | `--client-host-memory-in-gb <N>` | 客户端主机内存（数据加载缓冲），通过 `run_case --client-memory-gb` 注入 |
| Checkpoint | `--client-host-memory-in-gb <N>` | 客户端主机内存（checkpoint 写入缓冲），通过 `run_case --client-memory-gb` 注入 |
| KV Cache | `--cpu-mem-gb <N>` | KV cache 的 CPU 内存分层大小（GPU=0 时全部经 CPU 层溢出到 NVMe），通过 `run_case --cpu-mem-gb` 注入 |
| VectorDB | 无（数据在 Milvus 引擎） | 内存档仅记录配置，不产生参数差异 |

## 三、单 case 时长预算（≤ 1.5h 硬约束）

所有变种以**缩小参数**运行（数据量最小化），实测单 case 时长：

| 家族 | 实测时长 | 1.5h 预算余量 |
|---|---|---|
| Training（8 文件） | 1m44s ~ 4m46s | 充足（~19-52 倍余量） |
| Checkpoint（1 写 1 读真实 I/O） | 实测 1m45s（8b ~21GB）；70b/405b/1t 约 2-5 分钟 | 充足（>18 倍余量） |
| KV Cache（10 users × 10s × fast） | 9m44s ~ 10m29s | 充足（~9 倍余量） |
| VectorDB（100 向量 + Milvus Lite） | ~32s | 充足 |

> 结论：**全部 12 场景的每个 case 均满足"运行时间不长于 1.5h"**；KV 家族是耗时上限（MLPerf v3.0 固定 3 个 option），其余家族都在 5 分钟内。

## 四、运行方式

```bash
# 单个场景（如 1TB 容量 × 128GB 内存）
python scripts/run_ai_ssd_suite.py --capacity 1TB --memory 128GB \
    --data-drive D: --results-drive E:

# 单盘机器（只有 C:）—— 自动加 --skip-fs-separation-gate
python scripts/run_ai_ssd_suite.py --capacity 512GB --memory 64GB \
    --data-drive C: --results-drive C:

# 512GB 档 × 三种内存
python scripts/run_ai_ssd_suite.py --capacity 512GB --memory 32GB --data-drive D: --results-drive E:
python scripts/run_ai_ssd_suite.py --capacity 512GB --memory 64GB --data-drive D: --results-drive E:
python scripts/run_ai_ssd_suite.py --capacity 512GB --memory 128GB --data-drive D: --results-drive E:

# 单个 case 变种（手动指定内存）
python -m full_test_plan_cases.run_case AI-KV-001-1TB --mode execute \
    --cpu-mem-gb 128 --data-dir D:\MLPerfStorageTest\data --results-dir E:\MLPerfStorageTest\results
```

- **盘符不写死**：`--data-drive` / `--results-drive` 支持任意盘符（含同盘/单盘）；`scripts/cases/*.cmd` 顶部 `DATA_DIR`/`RESULT_DIR` 可改任意盘符，单盘时设 `SINGLE_DRIVE=1`（自动加 `--skip-fs-separation-gate`）。
- **磁盘空间是硬约束（CAP-01）**：Checkpoint 真实 I/O 的所需空间 = 模型 checkpoint 全量 × 写次数（llama3-8b 1 写 ≈ 113 GB，更大模型更多）；KV 按 users 计（10 users ≈ 10-25 GB）。空间不足时 case 会被门禁正确拦截。
- 汇总输出：`suite_summary_<容量>_<内存>.json`（如 `suite_summary_1TB_128GB.json`）
- 环境检查、跑后清理、SKIP 机制与基础档一致

## 五、完整矩阵预计总时长

| 容量档 | case 数/场景 | 场景数 | 预计耗时/场景 | 小计 |
|---|---|---|---|---|
| 512GB | 34 | 3（内存） | ~1h42m | ~5h06m |
| 1TB | 12 | 3 | ~45m | ~2h15m |
| 2TB | 12 | 3 | ~46m | ~2h18m |
| 4TB | 12 | 3 | ~45m | ~2h15m |
| **合计** | 70 × 3 | 12 | — | **~11h54m** |

> 全矩阵 12 场景共 **70 case × 3 内存档 = 210 次运行**，可在 ~12 小时内分批跑完（套件支持 `--only` 按家族/单 case 筛选）。KV 家族占绝大部分时长。

## 六、配置来源

- case 集定义：`full_test_plan_cases/case_catalog.json`（512GB 档 34 case）+ `capacity_catalog.json`（1TB/2TB/4TB 档）
- 矩阵定义：`full_test_plan_cases/matrix_catalog.json`（12 场景 + 内存参数映射）
- 执行器：`full_test_plan_cases/run_case.py`（`--client-memory-gb` / `--cpu-mem-gb` 覆盖）
