# FULL_TEST_PLAN：33 个 Native Case 执行手册

当前 Case 数量、ID、命令与参数以
[`case_catalog.json`](case_catalog.json) 为唯一数据源；文档状态与旧方案迁移见
[`docs/AI_SSD_DOCUMENT_STATUS.md`](../docs/AI_SSD_DOCUMENT_STATUS.md)。

## 架构（2026-08 简化后）

```
case_catalog.json   ← 唯一数据源：33 个 case 的 native_commands（占位符命令）
run_case.py         ← 唯一执行器：占位符替换 → init → 逐阶段 mlpstorage 执行 → cleanup
run_case.cmd        ← Windows 入口：调用 run_case 模块
scripts/cases/*.cmd ← 每个 case 一个一键脚本（直接运行）
scripts/smoke_all_cases.py ← 批量缩小版验证
site_config.json    ← 站点配置（每台机器改一次）
```

## 单个 Case：一条命令运行

```powershell
.\run_case.cmd AI-KV-005
```

自动完成：按 Case ID 从 catalog 取命令 → 派生 `data/<CASE_ID>`、`results/<CASE_ID>` →
`mlpstorage init` → CAP 门禁 → prepare（datagen）→ run → 退出码原样返回 → 清理数据目录。

诊断参数：

```powershell
.\run_case.cmd AI-KV-005 --print-command     # 只打印最终 mlpstorage 命令
.\run_case.cmd AI-KV-005 --mode plan         # 打印命令不执行
.\run_case.cmd AI-KV-005 --mode preflight    # 检查环境不执行
.\run_case.cmd AI-KV-005 --keep-data         # 保留数据目录
.\run_case.cmd AI-TRN-003 --test-drive D     # 临时换盘（单盘模式）
```

### 站点配置（`site_config.json`）

每台机器只改一次。两种模式：

```jsonc
// 模式 A：单盘（默认；data 与 results 同盘，会被 CAP-03 拦截，仅适合 preflight）
{ "test_drive": "C", "test_root": "MLPerfStorageTest" }

// 模式 B：分盘（正式运行必需；data 与 results 必须不同文件系统）
{ "data_root": "G:\\MLPerfStorageTest\\data", "results_root": "D:\\MLPerfStorageTest\\results" }
```

⚠️ 分盘模式下**不要**再加 `--test-drive`（会覆盖盘符、又变同盘）。

## Dev 模式：缩小数据集 / 本机验证

正式数据集很大（unet3d 7200 文件 ≈ 983 GiB、retinanet 1,170,301 文件 ≈ 352 GiB），
受 CAP-01 容量与 CAP-03 同盘门禁约束。`run_case` 支持缩小覆盖参数：

| 参数 | 作用 |
|---|---|
| `--num-files-train N` | 覆盖 `dataset.num_files_train`（Training） |
| `--num-processes N` | 覆盖 `--num-processes`（Checkpoint ranks / datagen） |
| `--num-checkpoints-write/read N` | 覆盖 checkpoint 写/读次数（0 = 零 I/O 冒烟） |
| `--num-vectors N` | 覆盖 vectordb datagen 向量数 |
| `--trials N` / `--inter-option-delay N` | 覆盖 KV cache trials / 间隔 |
| `--duration-sec N` | 覆盖 KV/VDB 运行时长（秒） |
| `--milvus-uri <path.db>` | VDB 用本地 Milvus Lite 库替代远程 server |
| `--vdb-config <yaml>` | VDB 用缩小版 vdbbench config（如 `full_test_plan_cases/configs/vdb_smoke.yaml`） |
| `--allow-invalid-params` / `-aip` | dev：放行 MLPerf 规则校验（正式提交不可用） |
| `--skip-fs-separation-gate` | dev：绕过 CAP-03 同盘门禁 |

示例（分盘 D 数据 / E 结果，TRN-003 8 文件冒烟）：

```powershell
.\.venv\Scripts\python.exe -m full_test_plan_cases.run_case AI-TRN-003 `
  --data-dir D:\mlps_dev_data --results-dir E:\mlps_dev_res `
  --num-files-train 8 --allow-invalid-params
```

示例（VDB 用 Milvus Lite 本地库）：

```powershell
.\.venv\Scripts\python.exe -m full_test_plan_cases.run_case AI-VDB-001 `
  --data-dir D:\mlps_dev_data --results-dir E:\mlps_dev_res `
  --vdb-config full_test_plan_cases\configs\vdb_smoke.yaml `
  --milvus-uri D:\mlps_dev_data\lite.db --duration-sec 10
```

注意：dev 缩小跑带 `-aip`，**不算正式 MLPerf PASS**；正式提交必须完整数据集。

## 一键脚本（每 case 一个）

`scripts/cases/AI-TRN-003.cmd` 等 33 个脚本：编辑头部 `DATA_DIR`/`RESULT_DIR`
盘符后直接运行。dev 缩小：取消注释 `NUM_FILES_TRAIN=8` / `ALLOW_INVALID=1` 两行。
重新生成：`python tools/gen_case_scripts.py`。

## 批量缩小版验证

```powershell
.\.venv\Scripts\python.exe scripts\smoke_all_cases.py            # 全部 33 个
.\.venv\Scripts\python.exe scripts\smoke_all_cases.py --only AI-TRN-003,AI-KV-001
```

按家族自动套缩小参数：Training 8 文件 + `-aip`；Checkpoint 8 ranks + 零 I/O；
KV 10s × 1 trial；VDB 需 Milvus server（标注 BLOCKED）。

## 全量入口（`run_all`）

```powershell
.\.venv\Scripts\python.exe -m full_test_plan_cases.run_all `
  --mode plan --data-dir C:\MLPerfStorageTest\data --results-dir C:\MLPerfStorageTest\results

# 正式执行（需分盘配置）
.\.venv\Scripts\python.exe -m full_test_plan_cases.run_all `
  --mode execute --confirm-dut --init-results --cleanup-data --prepare
```

`run_all` 逐个调用 `run_case`；execute/dry-run/preflight 模式下第一个非零退出码触发
套件级 fast-fail。

## 1TB / 2TB 容量适配压力 case

针对单块 1TB / 2TB SSD 设计，case_id 带 `-1TB` / `-2TB` 后缀（定义见
[`capacity_catalog.json`](capacity_catalog.json)），**默认单盘运行**（run_case
自动加 `--skip-fs-separation-gate`），Training 按盘容量调整数据集：

| Case | 盘 | 数据量 | 填盘 |
|---|---|---|---|
| `AI-TRN-003-1TB`（unet3d 3500 文件） | 1TB | 478 GiB | 51% |
| `AI-TRN-004-1TB`（retinanet） | 1TB | 352 GiB | 38% |
| `AI-CKP-001-1TB`（8B 10 写 10 读） | 1TB | 120 GB×2 流量 | 13% |
| `AI-VDB-002-1TB`（1M 全量 + 查询） | 1TB | ~15 GiB | — |
| `AI-TRN-003-2TB`（unet3d 正式 7200） | 2TB | 983 GiB | 53% |
| `AI-CKP-002-2TB`（70B 8 ranks 10 写） | 2TB | 1.04 TB | 56% |
| `AI-VDB-006-2TB`（10M 向量） | 2TB | ~150 GiB | 8% |

运行方式与普通 case 相同（`run_case.cmd AI-TRN-003-1TB` 或
`scripts\cases\AI-TRN-003-1TB.cmd`）；一键脚本默认 data/results 都在 `G:`。

## 环境前提

| 依赖 | 说明 |
|---|---|
| Python venv | `uv sync`（或 `setup_env.cmd`）；缺 `kv_cache`/`vdbbench` 时：`uv pip install -e kv_cache_benchmark -e vdb_benchmark` |
| MPI | `mpiexec`（MS-MPI）；checkpointing 需 8 的倍数 ranks |
| 分盘 | data 与 results 必须不同文件系统（CAP-03），否则 `-aip` 也不放行，需 `--skip-fs-separation-gate` |
| 容量 | TRN-003 983 GiB / TRN-004/005 352 GiB；CKP 大模型 checkpoint ≥1 TB |
| Milvus | VDB 需 `127.0.0.1:19530` server（docker），或用 `--milvus-uri` 本地 Milvus Lite |

`AI-VDB-015` 是独立的 trace case（`trace_test_cases/`），不在 33 Native 内。

正式 `PASS` 只能来自真实 native workload 的输出与退出码；`DRY_RUN` 不算通过。
