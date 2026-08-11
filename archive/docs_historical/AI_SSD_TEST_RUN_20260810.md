# AI SSD 实际执行记录：2026-08-10

本记录只把原生 workload 的真实执行结果作为证据。`datasize`、`plan`、`preflight`、`dry-run`、单元测试和命令生成均不算性能 case 完成。

## 1. 测试环境和数据边界

| 项目 | 值 |
|---|---|
| 平台 | Windows；PowerShell；MS-MPI `mpiexec` |
| 原生入口 | `.\.venv\Scripts\mlpstorage.exe` |
| 被测数据根目录 | `G:\MLPerfTestData` |
| 结果根目录 | `C:\MLPerfTestRuns\results-20260810` |
| Organization | `AI-SSD-Test` |
| 测试方式 | 直接运行原生 `mlpstorage` 或项目原生 trace replay；没有 Docker，没有 smoke，没有额外 case wrapper |

结果目录位于 C 盘，workload 数据位于 G 盘。每个可运行 case 完成并提取结果后，只删除该 case 的 G 盘数据目录，保留 C 盘 metadata、summary、rank/trial 结果和日志。

## 2. 34 个 case 的总体状态

| 类别 | Case | 实际状态 |
|---|---|---|
| Training | `AI-TRN-003`–`005` | 3/3 均实际进入原生命令；`003` 被容量门禁阻断，`004` 完成全量 datagen 后在 Windows `fork` 启动点失败，`005` 复现同一平台问题 |
| Checkpointing | `AI-CKP-001`–`007` | 7/7 原生命令均执行到 CAP-01；全部因正式 10 份 checkpoint 容量不足而在写盘前阻断 |
| KV Cache | `AI-KV-001`–`008` | 8/8 均完整执行 3 options × 3 trials；72/72 trial 结果存在，均 `partial_failure=false` |
| VectorDB | `AI-VDB-001`–`014`、`016` | 15/15 原生 case 均完成环境、规则、容量和 vdbbench 初始化，随后因 `127.0.0.1:19530` 无 Milvus 服务而阻断 |
| VectorDB trace | `AI-VDB-015` | 完整 replay 211 个事件，退出码 0；判定为 `CONDITIONAL`，不能冒充 Milvus 端到端成绩 |

这里的“实际执行”不等于“性能通过”。本机得到的可落盘 workload 中，没有一个有效 SSD case 达到全部性能/health 条件；具体原因见后文。

## 3. Training

### AI-TRN-003：UNet3D / B200

原生 `open training unet3d datagen file` 在真正写数据前执行 CAP-01：

| 字段 | 值 |
|---|---:|
| Required | 1,055,524,521,600 bytes，约 983.03 GiB |
| Available | 419,319,951,360 bytes |
| Deficit | 636,204,570,240 bytes |
| 状态 | `BLOCKED/CAPACITY`；没有生成数据文件 |

这不是 GPU 缺失。Training 用 DLIO 模拟 accelerator 的计算间隔，本身不要求安装 B200。首次执行曾因 DLIO 不在当前 `PATH` 报 `E204`；激活 venv 的 Scripts 路径后可进入正式容量检查。当前 Windows 上 `--dlio-bin-path` 会拼接没有 `.exe` 的 `dlio_benchmark`，不能代替 PATH 激活。

### AI-TRN-004：RetinaNet / B200

- 全量原生 datagen 成功：1,170,301 个文件、377,567,189,824 bytes（351.64 GiB）。
- datagen 时间：03:00:57–03:07:47。
- 正式原生 run 成功进入 DLIO，并抽样验证 1,172 个文件全部有效。
- 在启动数据加载进程时失败：配置使用 `multiprocessing_context='fork'`，Windows 只支持 `spawn`。
- 尝试通过原生 `--params reader.multiprocessing_context=spawn` 覆盖时，规则引擎将该覆盖判为 `INVALID`，因此当前代码没有合规的 Windows run 路径。
- 351.64 GiB datagen 数据随后已删除；结果和错误证据保留。

### AI-TRN-005：RetinaNet / MI355

原生 run 同样进入 DLIO 后在 `multiprocessing_context='fork'` 失败。`--accelerator-type mi355` 是模拟 I/O 节奏，不表示本机必须存在 MI355；实际阻断原因仍是 Windows 多进程上下文。

## 4. Checkpointing

7 个 case 均使用原生 `open checkpointing run file`，并在写任何 checkpoint 前由 CAP-01 正确 fast-fail。本轮可用空间为 418,121,809,920 bytes。

| Case | 模型/进程 | Required bytes | Deficit bytes | 状态 |
|---|---|---:|---:|---|
| `AI-CKP-001` | 8B / 8 | 1,127,428,915,200 | 709,307,105,280 | `BLOCKED/CAPACITY` |
| `AI-CKP-002` | 70B / 8 subset | 1,222,723,502,080 | 804,601,692,160 | `BLOCKED/CAPACITY` |
| `AI-CKP-003` | 70B / 64 | 9,781,788,016,640 | 9,363,666,206,720 | `BLOCKED/CAPACITY` |
| `AI-CKP-004` | 405B / 8 subset | 1,013,847,162,880 | 595,725,352,960 | `BLOCKED/CAPACITY` |
| `AI-CKP-005` | 405B / 512 | 56,779,467,653,120 | 56,361,345,843,200 | `BLOCKED/CAPACITY` |
| `AI-CKP-006` | 1T / 8 subset | 1,725,368,893,440 | 1,307,247,083,520 | `BLOCKED/CAPACITY` |
| `AI-CKP-007` | 1T / 1024 | 193,241,316,065,280 | 192,823,194,255,360 | `BLOCKED/CAPACITY` |

容量要求包含正式 case 规定的多份 checkpoint，不应通过缩小 checkpoint 数或改成 smoke 来假装完成。7 个 case 都没有留下 checkpoint 文件。

## 5. KV Cache

### 5.1 执行完整性

8 个 case 均直接运行：

```powershell
.\.venv\Scripts\mlpstorage.exe open kvcache run <case 参数> `
  --trials 3 --loops 1 `
  --cache-dir G:\MLPerfTestData\<CASE> `
  --results-dir C:\MLPerfTestRuns\results-20260810 `
  --exec-type mpi --num-processes 1 --hosts localhost --mpi-bin mpiexec
```

每个 case 都跑满 3 个 option、每个 option 3 个 trial，共 9 个 trial。下表中每个 Option 的字段依次为：`聚合 tokens/s / Storage read GiB/s / Storage write GiB/s / worst P95 ms`。

| Case | 模型/用户 | Option 1 | Option 2 | Option 3 | Trial health | SSD 证据与结论 |
|---|---|---|---|---|---|---|
| `AI-KV-001` | Llama3.1-8B / 200 | 760.00 / 12.837 / 2.979 / 96099.23 | 758.08 / 12.282 / 2.841 / 97109.85 | 795.72 / 13.008 / 2.985 / 27994.84 | FAIL 9/9 | SSD 读写；单 trial 最大写 183.90 GiB、读 803.26 GiB；性能失败 |
| `AI-KV-002` | Llama3.1-8B / 100；CPU 4 GiB | 556.35 / 1.492 / 1.719 / 9097.24 | 564.04 / 1.710 / 1.711 / 8674.44 | 509.09 / 0.976 / 1.632 / 3390.02 | FAIL 9/9 | SSD 读写；最大写 112.88 GiB、读 126.48 GiB；性能失败 |
| `AI-KV-003` | Llama3.1-70B / 70 | 167.11 / 6.810 / 1.935 / 79487.39 | 170.87 / 6.674 / 1.869 / 91719.43 | 227.28 / 9.742 / 2.231 / 47723.55 | FAIL 9/9 | SSD 读写；最大写 141.19 GiB、读 601.29 GiB；性能失败 |
| `AI-KV-004` | tiny-1b / 10 | 317.84 / 0 / 0 / 708.72 | 319.04 / 0 / 0 / 574.48 | 316.97 / 0 / 0 / 536.51 | PASS 9/9 | `storage_entries=0`、Storage bytes=0；工作集全在 CPU tier，`NOT-SSD` |
| `AI-KV-005` | Mistral-7B / 10 | 201.70 / 0.058 / 0.560 / 6058.06 | 200.86 / 0.083 / 0.504 / 4595.76 | 211.12 / 0.013 / 0.495 / 3316.19 | FAIL 9/9 | SSD 读写；最大写 34.63 GiB、读 14.91 GiB；性能失败 |
| `AI-KV-006` | Llama2-7B / 10 | 58.66 / 0.134 / 0.686 / 17777.45 | 60.91 / 0.064 / 0.660 / 26097.04 | 62.64 / 0.127 / 0.726 / 10947.15 | FAIL 9/9 | SSD 读写；最大写 51.24 GiB、读 19.89 GiB；性能失败 |
| `AI-KV-007` | Llama3.1-8B / 10 | 214.50 / 0 / 0.544 / 3192.88 | 208.22 / 0 / 0.481 / 3442.48 | 195.40 / 0 / 0.468 / 3832.97 | FAIL 9/9 | 有 Storage entries 和写入，最大写 34.99 GiB，但 Storage 读为 0；只覆盖 SSD offload 写 |
| `AI-KV-008` | Llama3.1-70B / 10 | 96.42 / 0.116 / 0.778 / 10428.93 | 96.32 / 0.201 / 0.705 / 15369.95 | 101.17 / 0.025 / 0.749 / 8576.63 | FAIL 9/9 | SSD 读写；最大写 48.66 GiB、读 28.78 GiB；性能失败 |

所有 KV summary 位于：

```text
C:\MLPerfTestRuns\results-20260810\open\AI-SSD-Test\results\ai-kv-<NNN>-open-g\kv_cache\<model>\run\<timestamp>\summary.json
```

每个 summary 的 `trial_count=3`、`partial_failure=false`，每个 run 下均有 9 个 `kvcache_results_*.json`。因此这些是完整运行结果；但只有命中 Storage tier 才能评价 SSD，health FAIL 也不能被退出码 0 覆盖。

### 5.2 额外发现

- Windows 上 MS-MPI 集群 collector 每次都返回“未生成 output file”，框架随后回退到 local-only collection；这不影响 workload 的 9 个 trial，但正式提交前必须修复采集证据。
- 当前 CLOSED KV CLI 存在代码缺陷：fail-fast 校验要求 `model`，但 CLOSED CLI 又不提供 `--model`，导致 `closed kvcache datasize/run` 在默认模型注入前报 `E101 Missing model`。本轮使用各 case 明确可表达的 OPEN 原生命令完成实际 I/O。
- `AI-KV-004` 的 health 显示 PASS 但 SSD 字节为 0，说明 case 设计必须把 `storage_entries > 0` 和 Storage tier bytes > 0 设为前置有效性条件。

## 6. VectorDB Native

`AI-VDB-001`–`014` 和 `AI-VDB-016` 的原生 `mlpstorage open vectordb ... file` 命令逐个独立执行。每个 case 都完成：

1. CLI 和 OPEN 参数规则校验；
2. 环境校验和结果目录创建；
3. vdbbench 初始化；
4. 远端 backend 场景下跳过本地 CAP；
5. PyMilvus 连接 `127.0.0.1:19530`。

所有 case 随后在约 10 秒内因本机没有 Milvus 服务而失败，状态统一为 `BLOCKED/EXTERNAL_SERVICE`。没有生成向量数据库数据，也没有 QPS、Recall 或查询延迟成绩。结果 metadata 位于对应 `ai-vdb-<NNN>-open-g` 目录。

这证明命令和参数可以走到真实数据库连接点，但不能记成 VectorDB case 完成。要完成这些 case，必须先部署可用 Milvus，并确认 Milvus 的实际数据卷映射到 DUT；`mlpstorage` 本身不会启动 Milvus。

## 7. AI-VDB-015：Logical Trace Replay

使用仓库已有正式 `vdbbench` source trace，直接执行项目原生 replay：

| 字段 | 值 |
|---|---:|
| Events | 211 |
| Reads / Writes | 200 / 11 |
| Logical bytes | 53,099,200 bytes |
| P50 / P95 / P99 | 0.2085 / 0.38225 / 0.58355 ms |
| Wall throughput | 768.772 MiB/s |
| Active-I/O throughput | 1,388.425 MiB/s |
| Exit code | 0 |
| 判定 | `CONDITIONAL` |

Replay 完成后目标数据目录已删除。该结果只表示固定逻辑 trace 在目标盘上的 replay 性能，不包含 Milvus 网络、WAL、索引构建、compaction、ANN 计算或 Recall，不能替代端到端 VectorDB 结果。

## 8. 最终清理与审计

| 检查项 | 最终状态 |
|---|---|
| `mlpstorage` / DLIO / MPI workload 进程 | 0 |
| `G:\MLPerfTestData` | 0 文件，0 GiB |
| `D:\MLPerfData`、`D:\MLPerfKVCache`、`D:\MLPerfCheckpoint` | 0 文件 |
| `D:\AI-SSD-TestData`、`E:\AI-SSD-TestData` | 0 文件 |
| G 盘最终空闲 | 389.41 GiB |
| C 盘 results | 保留完整证据 |

本轮曾生成并随后删除的主要数据包括：RetinaNet 351.64 GiB、KV-001 181.68 GiB、KV-002 100.07 GiB、KV-003 141.19 GiB、KV-005 29.13 GiB、KV-006 51.24 GiB、KV-007 27.77 GiB、KV-008 49.98 GiB，以及各 trace replay 临时数据。删除均以单个 case 的已核对绝对路径为边界，没有删除结果目录。

## 9. 结论

- KV Cache 是本机唯一完成了全部规定 trial 的原生 workload 类别；7 个 case 命中 SSD，但均未通过 health，另 1 个 case 只命中 CPU tier。
- Training 和 Checkpointing 不需要真实 GPU；当前阻断分别是 Windows `fork` 实现和正式规模容量，不是显卡缺失。
- VectorDB Native 必须有外部 Milvus 服务及正确的 DUT volume 映射；本机没有该服务，所以没有端到端成绩。
- Trace replay 已完整通过，但只能作为条件性 SSD I/O 结果。
- 所有临时 workload 数据已清理，结果证据已保留。
