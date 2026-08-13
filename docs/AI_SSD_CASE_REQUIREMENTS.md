# AI SSD Case 需求文档

> 生成：由 `tools/gen_case_requirements_doc.py` 从 `case_catalog.json` / `capacity_catalog.json` 生成，实测结果回填自 `run_ai_ssd_suite.py` 的 summary。
> 数据源唯一入口：`full_test_plan_cases/case_catalog.json`（34 基础 case）+ `capacity_catalog.json`（1TB/2TB/4TB 容量档）。

## 一、测试体系概述

- 执行引擎：`mlpstorage`（MLPerf Storage Benchmark Suite v3.0）
- 统一执行器：`full_test_plan_cases/run_case.py`（`run_case.cmd <CASE_ID>`）
- 批量套件：`scripts/run_ai_ssd_suite.py --capacity <档位> --data-drive X: --results-drive Y:`
- 四类 workload：Training / Checkpoint / KV Cache / VectorDB
- **512 GB 磁盘约束**：所有 case 以缩小参数运行（见各家族表），验证执行链路、门禁与指标产出，不生成真实容量数据；容量档（1TB/2TB/4TB）的完整数据量需对应容量的磁盘。

## 二、Case 需求总表（34 基础 case）

| Case | 家族 | 优先级 | 需求 ID | 测试目的 | 主要变量 | 主要指标 | 实测 |
|---|---|---|---|---|---|---|---|
| AI-TRN-003 | Training | P0 | TR-AI-TRAIN-001、TR-AI-TRAIN-003 | V3.0 sustained large-file reads | datasize;accelerators 1/2/4/8 | AU;samples/s;GiB/s | 待跑 |
| AI-TRN-004 | Training | P0 | TR-AI-TRAIN-001、TR-AI-TRAIN-003 | Million-JPEG small-file pressure | accelerators 1/4/8/16 | AU;files/s;P99;CPU | 待跑 |
| AI-TRN-005 | Training | P0 | TR-AI-TRAIN-001、TR-AI-TRAIN-003 | Different batch/compute small-file pressure | accelerators 1/4/8/16 | AU;files/s;P99 | 待跑 |
| AI-TRN-DLRM | Training | P0 | TR-AI-TRAIN-001、TR-AI-TRAIN-003 | DLRM Parquet embedding random-read IOPS stress (open) | num_files_train;accelerators;read_threads | AU;samples/s;IOPS | 待跑 |
| AI-CKP-001 | Checkpoint | P0 | TR-AI-CKPT-001、TR-AI-CKPT-002 | Single-node save/restore baseline | 105 GB;10 save;10 load | slowest duration;min throughput;hash | PASS |
| AI-CKP-002 | Checkpoint | P0 | TR-AI-CKPT-001、TR-AI-CKPT-002 | Simulate node-local 70B shard | 114 GB;8 ranks | slowest rank;min throughput;skew | 待跑 |
| AI-CKP-003 | Checkpoint | P0 | TR-AI-CKPT-001、TR-AI-CKPT-002、TR-AI-CKPT-003 | Multi-node concurrent save/restore | 912 GB;64 ranks | global duration;skew;bandwidth | 待跑 |
| AI-CKP-004 | Checkpoint | P1 | TR-AI-CKPT-001、TR-AI-CKPT-002 | 405B node-local SSD load | 94 GB;8 ranks | save/load GiB/s;cold bytes | 待跑 |
| AI-CKP-005 | Checkpoint | P0 | TR-AI-CKPT-001、TR-AI-CKPT-002、TR-AI-CKPT-003 | TB-scale shared checkpointing | 5.29 TB;512 ranks | global duration;skew;bandwidth | 待跑 |
| AI-CKP-006 | Checkpoint | P1 | TR-AI-CKPT-001、TR-AI-CKPT-002 | Maximum node-local shard/GC pressure | 161 GB;8 ranks | burst BW;recovery;restore time | 待跑 |
| AI-CKP-007 | Checkpoint | P0 | TR-AI-CKPT-001、TR-AI-CKPT-002、TR-AI-CKPT-003 | Extreme-model global recovery | 18 TB;1024 ranks | global duration;min throughput | 待跑 |
| AI-KV-001 | KV Cache | P0 | TR-AI-KV-001、TR-AI-KV-004 | NVMe-only high concurrency | 200 users;GPU/CPU 0;alloc 16 | worst P95;tokens/s;Tier-2 bytes | 待跑 |
| AI-KV-002 | KV Cache | P0 | TR-AI-KV-001、TR-AI-KV-004 | 4 GiB CPU spill boundary | 100 users;CPU 4 GiB;alloc 16 | spill time;P95;evictions | 待跑 |
| AI-KV-003 | KV Cache | P0 | TR-AI-KV-001、TR-AI-KV-004 | Large KV objects | 70 users;GPU/CPU 0;alloc 4 | P95;BW;RAM peak | 待跑 |
| AI-KV-004 | KV Cache | P1 | TR-AI-KV-001、TR-AI-KV-002 | Small-object IOPS ceiling | users 10 to 500 | IOPS;P99;tokens/s | 待跑 |
| AI-KV-005 | KV Cache | P1 | TR-AI-KV-001、TR-AI-KV-002 | 128 KiB/token GQA baseline | context/user sweep | P99;BW;tokens/s | 待跑 |
| AI-KV-006 | KV Cache | P1 | TR-AI-KV-001、TR-AI-KV-002 | 512 KiB/token upper bound | alloc 1/2/4/8 | P99.9;BW;OOM guard | 待跑 |
| AI-KV-007 | KV Cache | P0 | TR-AI-KV-001、TR-AI-KV-004 | Find max compliant users | users 25/50/100/200 | P95;tokens/s;queue | 待跑 |
| AI-KV-008 | KV Cache | P0 | TR-AI-KV-001、TR-AI-KV-004 | Large-model saturation | users 10/35/70/140 | P95;tokens/s;Tier-2 BW | 待跑 |
| AI-VDB-001 | VectorDB | P0 | TR-AI-VDB-001、TR-AI-VDB-003 | Windows Milvus/trace smoke | planted query;L2 | Recall;QPS;trace completeness | 待跑 |
| AI-VDB-002 | VectorDB | P0 | TR-AI-VDB-001、TR-AI-VDB-002 | Graph-index baseline | M64;ef 32/128/256 | Recall;QPS;P99 | 待跑 |
| AI-VDB-003 | VectorDB | P0 | TR-AI-VDB-001、TR-AI-VDB-002 | Disk-resident ANN baseline | degree 64;search-list | Recall;QPS;P99;physical reads | 待跑 |
| AI-VDB-004 | VectorDB | P1 | TR-AI-VDB-001、TR-AI-VDB-002 | Vector-dimension effect | 512 vs 1536 | bytes/query;QPS;P99;Recall | 待跑 |
| AI-VDB-005 | VectorDB | P1 | TR-AI-VDB-001、TR-AI-VDB-002 | Compressed-index efficiency | inline PQ 16/32 | index bytes;Recall;QPS;P99 | 待跑 |
| AI-VDB-006 | VectorDB | P1 | TR-AI-VDB-001、TR-AI-VDB-002 | Large-dataset scaling | query processes 1/4/8 | load;QPS;P99;Recall | 待跑 |
| AI-VDB-007 | VectorDB | P0 | TR-AI-VDB-001、TR-AI-VDB-002 | Large disk index | 10 shards;effort sweep | QPS;P99;Recall;physical I/O;temp | 待跑 |
| AI-VDB-008 | VectorDB | P1 | TR-AI-VDB-001、TR-AI-VDB-002 | Compare six index families | DISKANN;HNSW;AISAQ;IVF;FLAT | Recall;QPS;P99;capacity | 待跑 |
| AI-VDB-009 | VectorDB | P0 | TR-AI-VDB-002 | Accuracy-performance curve | ef/search list 32 to 512 | Recall;QPS;P99 | 待跑 |
| AI-VDB-010 | VectorDB | P1 | TR-AI-VDB-002 | Concurrency saturation | processes 1/2/4/8/16 | QPS;P99;queue;CPU | 待跑 |
| AI-VDB-011 | VectorDB | P1 | TR-AI-VDB-002 | Batch efficiency/tail cost | batch 1/8/32/64 | QPS;per-query P99;CPU | 待跑 |
| AI-VDB-012 | VectorDB | P1 | TR-AI-VDB-001 | Write/flush/compact/index efficiency | batch 1K/10K;compact on/off | vectors/s;phase times | 待跑 |
| AI-VDB-013 | VectorDB | P1 | TR-AI-VDB-002 | Query-shape effects | K10/100;COSINE/L2/IP | Recall;result bytes;P99;QPS | 待跑 |
| AI-VDB-014 | VectorDB | P0 | TR-AI-VDB-002、TR-AI-OBS-001 | Separate load/cache/search | restart/load;repeat rounds | load;first/steady P99;physical bytes | 待跑 |
| AI-VDB-016 | VectorDB | P1 | TR-AI-VDB-001、TR-AI-VDB-002 | Foreground ANN under writes | independent clients | Recall;foreground P99;ingest rate | 待跑 |

## 三、各家族测试内容与缩小验证参数

### Training

**缩小验证参数**：8 files + `--allow-invalid-params`（真实 datagen + 训练）

| Case | 测试内容（test_purpose） | 主要指标 |
|---|---|---|
| AI-TRN-003 | V3.0 sustained large-file reads | AU;samples/s;GiB/s |
| AI-TRN-004 | Million-JPEG small-file pressure | AU;files/s;P99;CPU |
| AI-TRN-005 | Different batch/compute small-file pressure | AU;files/s;P99 |
| AI-TRN-DLRM | DLRM Parquet embedding random-read IOPS stress (open) | AU;samples/s;IOPS |

### Checkpoint

**缩小验证参数**：8 ranks + 1 写 / 1 读 + `--allow-invalid-params`（真实 I/O 冒烟；容量档保留 capacity_catalog 的 I/O 量）

| Case | 测试内容（test_purpose） | 主要指标 |
|---|---|---|
| AI-CKP-001 | Single-node save/restore baseline | slowest duration;min throughput;hash |
| AI-CKP-002 | Simulate node-local 70B shard | slowest rank;min throughput;skew |
| AI-CKP-003 | Multi-node concurrent save/restore | global duration;skew;bandwidth |
| AI-CKP-004 | 405B node-local SSD load | save/load GiB/s;cold bytes |
| AI-CKP-005 | TB-scale shared checkpointing | global duration;skew;bandwidth |
| AI-CKP-006 | Maximum node-local shard/GC pressure | burst BW;recovery;restore time |
| AI-CKP-007 | Extreme-model global recovery | global duration;min throughput |

### KV Cache

**缩小验证参数**：10 users + 10 s + 1 trial + `--generation-mode fast`

| Case | 测试内容（test_purpose） | 主要指标 |
|---|---|---|
| AI-KV-001 | NVMe-only high concurrency | worst P95;tokens/s;Tier-2 bytes |
| AI-KV-002 | 4 GiB CPU spill boundary | spill time;P95;evictions |
| AI-KV-003 | Large KV objects | P95;BW;RAM peak |
| AI-KV-004 | Small-object IOPS ceiling | IOPS;P99;tokens/s |
| AI-KV-005 | 128 KiB/token GQA baseline | P99;BW;tokens/s |
| AI-KV-006 | 512 KiB/token upper bound | P99.9;BW;OOM guard |
| AI-KV-007 | Find max compliant users | P95;tokens/s;queue |
| AI-KV-008 | Large-model saturation | P95;tokens/s;Tier-2 BW |

### VectorDB

**缩小验证参数**：100 vectors + 10 s + `vdb_smoke.yaml` + Milvus Lite

| Case | 测试内容（test_purpose） | 主要指标 |
|---|---|---|
| AI-VDB-001 | Windows Milvus/trace smoke | Recall;QPS;trace completeness |
| AI-VDB-002 | Graph-index baseline | Recall;QPS;P99 |
| AI-VDB-003 | Disk-resident ANN baseline | Recall;QPS;P99;physical reads |
| AI-VDB-004 | Vector-dimension effect | bytes/query;QPS;P99;Recall |
| AI-VDB-005 | Compressed-index efficiency | index bytes;Recall;QPS;P99 |
| AI-VDB-006 | Large-dataset scaling | load;QPS;P99;Recall |
| AI-VDB-007 | Large disk index | QPS;P99;Recall;physical I/O;temp |
| AI-VDB-008 | Compare six index families | Recall;QPS;P99;capacity |
| AI-VDB-009 | Accuracy-performance curve | Recall;QPS;P99 |
| AI-VDB-010 | Concurrency saturation | QPS;P99;queue;CPU |
| AI-VDB-011 | Batch efficiency/tail cost | QPS;per-query P99;CPU |
| AI-VDB-012 | Write/flush/compact/index efficiency | vectors/s;phase times |
| AI-VDB-013 | Query-shape effects | Recall;result bytes;P99;QPS |
| AI-VDB-014 | Separate load/cache/search | load;first/steady P99;physical bytes |
| AI-VDB-016 | Foreground ANN under writes | Recall;foreground P99;ingest rate |

## 四、容量档（1TB / 2TB / 4TB）

容量档 case 以 `case_id` 后缀 `-1TB/-2TB/-4TB` 表示，基于基础 case 叠加容量参数（见 `capacity_catalog.json`）。512 GB 盘上以缩小参数验证配置解析与执行链路。

### 1TB

| Case | 基础 case | 容量覆盖参数 | 实测 |
|---|---|---|---|
| AI-TRN-003-1TB | AI-TRN-003 | `--num-files-train 3500` | 待跑 |
| AI-TRN-004-1TB | AI-TRN-004 | `` | 待跑 |
| AI-TRN-DLRM-1TB | AI-TRN-DLRM | `--num-files-train 400 --num-accelerators 4` | 待跑 |
| AI-CKP-001-1TB | AI-CKP-001 | `--num-checkpoints-write 1 --num-checkpoints-read 1` | 待跑 |
| AI-KV-007-1TB | AI-KV-007 | `--duration-sec 300 --trials 3` | 待跑 |
| AI-VDB-002-1TB | AI-VDB-002 | `--duration-sec 120` | 待跑 |

### 2TB

| Case | 基础 case | 容量覆盖参数 | 实测 |
|---|---|---|---|
| AI-TRN-003-2TB | AI-TRN-003 | `--num-files-train 7200` | 待跑 |
| AI-TRN-004-2TB | AI-TRN-004 | `` | 待跑 |
| AI-TRN-DLRM-2TB | AI-TRN-DLRM | `--num-accelerators 8` | 待跑 |
| AI-CKP-002-2TB | AI-CKP-002 | `--num-processes 8 --num-checkpoints-write 1 --num-checkpoints-read 1` | 待跑 |
| AI-KV-008-2TB | AI-KV-008 | `--duration-sec 300 --trials 3` | 待跑 |
| AI-VDB-006-2TB | AI-VDB-006 | `--duration-sec 120` | 待跑 |

### 4TB

| Case | 基础 case | 容量覆盖参数 | 实测 |
|---|---|---|---|
| AI-TRN-003-4TB | AI-TRN-003 | `--num-files-train 7200` | 待跑 |
| AI-TRN-004-4TB | AI-TRN-004 | `` | 待跑 |
| AI-TRN-DLRM-4TB | AI-TRN-DLRM | `--num-accelerators 16` | 待跑 |
| AI-CKP-002-4TB | AI-CKP-002 | `--num-processes 8 --num-checkpoints-write 3 --num-checkpoints-read 3` | 待跑 |
| AI-CKP-001-4TB | AI-CKP-001 | `--num-checkpoints-write 10 --num-checkpoints-read 10` | 待跑 |
| AI-VDB-006-4TB | AI-VDB-006 | `--duration-sec 120` | 待跑 |

## 五、判定标准（Pass / Fail / Invalid）

- **Pass**：达到门禁（如 Training AU ≥ 90% @ declared load）且结果、代码版本 manifest 完整。
- **Fail**：未达门禁、运行中断或指标回归。
- **Invalid**：路径/盘符错误、数据缺失、结果目录不在 DUT 上等无法验证 DUT 的情况。
- 缩小版（dev smoke）**Pass** 仅代表执行链路、门禁与指标产出正常，不代表真实容量下的性能结论。

## 六、运行与清理

- 单 case：`run_case.cmd <CASE_ID> --data-dir X:\... --results-dir Y:\...`（可加缩小参数）
- 批量：`python scripts/run_ai_ssd_suite.py --capacity 512GB --data-drive D: --results-drive E:`
- 套件每次运行前后自动检查环境（python/mlpstorage/vdbbench/milvus-lite/磁盘空间），
  每个 case 结束后自动删除数据目录，汇总写入 `suite_summary_<档位>.json`。
