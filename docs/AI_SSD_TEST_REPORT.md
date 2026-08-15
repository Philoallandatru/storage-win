# AI SSD 测试报告（数据驱动）

> 生成：2026-08-15 16:34:01 · 由 `tools/gen_test_report.py` 从 `suite_summary_*.json` 与 results 目录自动生成
> 场景数：1 · case 运行数：4 · **PASS 4 / FAIL 0 / SKIP 0**

## 一、环境与场景

| 场景文件 | 容量档 | 内存档 | case 数 | PASS | FAIL | SKIP |
|---|---|---|---|---|---|---|
| suite_summary_512GB_32GB.json | 512GB | 32GB | 4 | 4 | 0 | 0 |

## 二、逐 case 结果与指标

| Case | 容量 | 内存 | 家族 | 结果 | rc | 耗时 | 关键指标 |
|---|---|---|---|---|---|---|---|
| AI-CKP-001 | 512GB | 32GB | Checkpoint | PASS | 0 | 100s | save_GBps=1.894, load_GBps=3.706, save_s=55.29 |
| AI-TRN-003 | 512GB | 32GB | Training | PASS | 0 | 103s | AU=0.9 |
| AI-VDB-001 | 512GB | 32GB | VectorDB | PASS | 0 | 31s | recall@k=1, total_queries=100, QPS=976 |
| AI-VDB-004 | 512GB | 32GB | VectorDB | PASS | 0 | 30s | recall@k=1, total_queries=100, QPS=761 |

## 三、汇总统计

- 总运行：**4**（PASS 4 / FAIL 0 / SKIP 0，通过率 **100.0%**）

### 3.1 按家族

| 家族 | 运行 | PASS | FAIL | SKIP | 平均耗时 |
|---|---|---|---|---|---|
| Training | 1 | 1 | 0 | 0 | 1.7 min |
| Checkpoint | 1 | 1 | 0 | 0 | 1.7 min |
| VectorDB | 2 | 2 | 0 | 0 | 0.5 min |

### 3.2 时长分布（PASS 的 case）

- 最短 30s · 中位 100s · 最长 103s · 总和 4min
- 所有 PASS case 均 ≤ 1.5h 预算
