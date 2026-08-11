# 消费级 AI PC AI SSD 多阶段系统级测试方案

**适用范围**：Windows 11、消费级 NVMe SSD、1 TB / 2 TB / 4 TB、显存与系统内存合计 32–128 GB 的 AI PC。
**依据**：本仓库 MLPerf Storage 3.x、DLIO Training/Checkpointing、KV Cache、Milvus VectorDB、Windows 适配代码及 trace/replay 工具。
**定位**：验证一块消费级 SSD 在本地训练、Checkpoint、KV Cache Offload、本地 RAG/VectorDB 以及业务共存条件下的系统级表现；不作为 NVMe 协议符合性或企业级多节点存储提交方案。

## 1. 设计原则

1. **先验证数据路径，再评价性能**：任何 workload 必须证明实际访问了被测 SSD，不能仅依据逻辑吞吐或缓存命中结果下结论。
2. **实跑与模拟分层**：业务正确性和应用级指标使用真实 workload；无法在消费级 AI PC 上承载的模型、并发或容量，使用同源 trace 录制后回放，并单独标记为 replay 结果。
3. **以系统瓶颈为结论**：同时记录 SSD、CPU、内存、GPU、Docker/Milvus 和进程级指标，区分 SSD-limited、host-limited、cache-hit、thermal-throttling 和 workload-limited。
4. **按容量和内存收敛**：不在 1 TB 消费级盘上强行复现 TB 级数据中心矩阵；每一个 case 都必须通过容量预算和保留空间门禁。
5. **固定基线、逐步加压**：每个场景按照 Smoke → Baseline → Scale → Mixed → Soak/Recovery 推进，失败时停在当前阶段，不继续消耗 SSD 写入寿命。
6. **结果可复现**：固定 seed、软件版本、配置、数据目录、结果目录、Windows 电源策略、SSD 温度起始状态和监控采样周期。

## 2. 本仓库提供的测试方案全量盘点

### 2.1 通用工作流和结果治理

这些命令本身不是 SSD 性能 case，但它们决定结果是否有效、是否可复跑：

| 能力 | 仓库入口 | 作用 | 是否属于性能结果 |
|---|---|---|---|
| 结果初始化 | `mlpstorage init` | 建立 `results-dir`、组织名和系统名哨兵 | 否，前置门禁 |
| 配置计算 | `datasize` | 计算数据集、checkpoint、KV 或 VectorDB 所需空间 | 否，容量门禁 |
| 配置查看 | `configview` | 输出最终 YAML + CLI 合并后的有效配置 | 否，复现证据 |
| 数据生成 | `datagen` | 将训练数据或向量数据写入目标存储 | 可作为写入阶段结果 |
| 正式执行 | `run` | 执行 workload 并采集结果、主机 timeseries 和日志 | 是 |
| 结果验证 | `mlpstorage validate` | 检查目录、必需文件、规则和提交结构 | 否，质量门禁 |
| 报告生成 | `reports reportgen` | 汇总多次运行并生成报告 | 否，统计输出 |
| 历史重跑 | `history show/rerun` | 重放已记录命令 | 否，复现工具 |
| 锁文件/规则覆盖率 | `lockfile`、`rules-coverage` | 固定软件依赖，检查规则实现覆盖 | 否，工程治理 |
| 容量门禁 | CAP-01 | 检查目标卷可用空间 | 否，必须通过 |
| 共享文件系统门禁 | CAP-02 | 多主机时验证路径可见性 | 消费级单机不适用 |
| 文件系统分离门禁 | CAP-03 | 检查数据/Checkpoint 与结果目录是否分离 | 单盘时需显式记录例外 |
| 主机监控 | timeseries、`disk_stats.py`、PowerShell `Get-Counter` | 采集磁盘、CPU、内存、温度、队列等 | 是，归因证据 |

### 2.2 Training I/O

#### 模型和数据形态

`mlpstorage_py/config.py` 将 Training 模型分为：

| 模式 | 可用模型 | 主要数据形态 | 适合评价的 SSD 特性 |
|---|---|---|---|
| CLOSED / OPEN | `unet3d`、`retinanet` | NPZ 大文件、JPEG 大量小文件 | 持续读取带宽、metadata/IOPS、并发扩展 |
| WHATIF | `cosmoflow`、`resnet50` | TFRecord 中小对象、shuffle | 随机/混合读取、批内访问 |
| WHATIF | `dlrm`、`flux` | Parquet row-group、列式数据 | metadata、预取、列裁剪和大对象读取 |

#### 命令和变量

- `datasize → datagen file/object → run file/object → configview`。
- 加速器配置：`a100`、`h100`、`b200`、`mi355`；CLOSED 主要限制为 `b200`/`mi355`，AI PC 采用模拟加速器和单机模式。
- 关键变量：加速器数、reader threads、batch size、compute time、文件数、文件大小、shuffle、buffered/direct I/O、cold/warm cache。
- Training 数据集容量规则通常要求至少覆盖 `500 steps` 和 `5 × client host memory`，是防止页缓存吞吐虚高的核心条件。

#### 可形成的 Training 测试方案

1. 大文件连续供给：UNet3D。
2. 大量小文件：RetinaNet。
3. TFRecord 中小对象：ResNet50/CosmoFlow。
4. Parquet 列式读取：DLRM/Flux。
5. 加速器数量扩展：1 → 2 → 4 → 饱和点。
6. reader thread 扩展：1/2/4/8/16/32，寻找 SSD 与 CPU 的拐点。
7. cold/warm/direct 路径对照。
8. 多 workload 并发读写干扰。

### 2.3 Checkpointing

#### 模型、规模和模式

| 模型 | 8-rank subset | full 进程数 | 估算完整 checkpoint | 消费级 AI PC 建议 |
|---|---:|---:|---:|---|
| `llama3-8b` | 8 | 8 | 约 105 GB | 首选真实写入/恢复基线 |
| `llama3-70b` | 8 | 64 | 约 912 GB | 8-rank subset 可实跑，full 仅扩展环境 |
| `llama3-405b` | 8 | 512 | 约 5.29 TB | 仅 trace 或容量充足时做 subset |
| `llama3-1t` | 8 | 1024 | 约 18 TB | 仅 trace/replay，不作为本机实跑要求 |

#### 可形成的 Checkpoint 测试方案

1. write-only、read-only、write+read。
2. `fsync` 持久化写入。
3. warm restore 与 cold restore 分离。
4. 10 次写入 + 10 次读取的正式规则流程。
5. 连续 checkpoint 间隔和后台 GC 影响。
6. model shard 与 optimizer shard 的不同访问比例。
7. 中断写入、重启恢复、hash/文件大小一致性验证。
8. file、object、streaming backend 对比；Windows 消费级盘以 local file backend 为主。

### 2.4 KV Cache Offloading

#### MLPerf Storage CLI 的固定方案

`mlpstorage closed/open/whatif kvcache` 当前 CLI 支持 `tiny-1b`、`mistral-7b`、`llama2-7b`、`llama3.1-8b`、`llama3.1-70b-instruct`。CLOSED 方案固定为：

| Option | 模型 | 用户数 | GPU tier | CPU tier | 并发 allocation | 主要压力 |
|---|---|---:|---:|---:|---:|---|
| 1 | Llama 3.1 8B | 200 | 0 GB | 0 GB | 16 | 最大 NVMe 压力、读写混合 |
| 2 | Llama 3.1 8B | 100 | 0 GB | 4 GB | 16 | CPU spill 后进入 NVMe |
| 3 | Llama 3.1 70B Instruct | 70 | 0 GB | 0 GB | 4 | 大对象、较低并发 |

#### Standalone KV 工具提供的扩展方案

独立 `kv_cache_benchmark` 还支持 `deepseek-v3`、`qwen3-32b`、`gpt-oss-20b`、`gpt-oss-120b` 等模型，以及：

- GPU/CPU/NVMe 三层容量矩阵。
- `prefill-only` 写密集、`decode-only` 读密集、mixed 多轮。
- `generation-mode`：`none`、`fast`、`realistic`。
- chatbot/coding/document persona、RAG、prefix cache、多轮对话。
- request rate、最大用户数、autoscaler、capacity/QoS 模式。
- `num-gpus`、tensor parallel、最大并发 allocation。
- `precondition`、BurstGPT/ShareGPT、block-layer latency tracing。
- 独立 KV trace：`Timestamp, Operation, Object_Size_Bytes, Tier, Key, Phase`。

#### KV 的三类执行方式

1. **真实运行**：KV benchmark 将 Tier-2 cache directory 放到被测 SSD，测 tokens/s、读写带宽和 P95/P99/P99.9/P99.99。
2. **逻辑录制**：使用 standalone KV `--io-trace-log` 记录操作，不进行真实 NVMe I/O。
3. **过滤回放**：只保留 `Tier-2` 事件，用 replay 工具按原始时间间隔、对象大小和读写顺序压测 SSD。

### 2.5 VectorDB / Milvus

#### 引擎、索引和数据集

| 配置 | 规模 | 维度 | 索引 | 用途 |
|---|---:|---:|---|---|
| Windows smoke | 1K | 128 | HNSW/FLAT | 连接、写入、查询、trace 链路 |
| 1M baseline | 1M | 1536 | HNSW | 内存/图索引基线 |
| 1M disk | 1M | 1536 | DISKANN | 磁盘型 ANN 基线 |
| 1M dimension | 1M | 512 | DISKANN/AISAQ | 维度、压缩和容量影响 |
| 10M scale | 10M | 1536 | HNSW/DISKANN | 大数据集、分片和后台 I/O |

#### VectorDB 测试方案

1. ingest、flush、compact、index build。
2. timed、query-count、sweep 三种查询模式。
3. top-k、batch、query processes、search effort 扫描。
4. HNSW、DISKANN、AISAQ 之间的固定 Recall 对比。
5. FLAT ground truth、Recall@K、QPS、P50/P95/P99。
6. cold load、warm search、search-only。
7. ingest+search、index build+search 的前后台干扰。
8. Milvus 逻辑 trace 录制和本地 SSD replay。

#### Trace 的边界

VDB trace 记录的是客户端逻辑操作及估算字节量，不包含 Milvus WAL、protobuf、对象存储、索引放大和 compaction 物理 I/O。因此必须同时报告：

- 逻辑 trace bytes；
- Windows `PhysicalDisk` 实际 bytes；
- 逻辑/物理放大倍数；
- 真实 Milvus 结果与 replay 结果。

### 2.6 仓库附属工具

| 工具 | 作用 | 在本方案中的定位 |
|---|---|---|
| `vdbbench.trace_runner` | 对真实 Milvus 记录 insert/flush/load/search trace | VDB 录制 |
| `vdbbench.replay` | 按时间节奏、对象大小回放到 Windows 文件系统 | SSD 确定性压测 |
| `vdbbench.windows_direct_io` | Windows 对齐的 unbuffered read/write | 绕过页缓存验证 |
| `vdbbench.simple_bench` | 简化 Milvus 查询基线 | 快速 smoke |
| `vdbbench.enhanced_bench` | ground truth、Recall 统计、搜索参数 sweep | VDB characterization |
| `vdbbench.compact_and_watch` | 监控索引构建和 compaction | 后台 I/O 观测 |
| KV `--io-trace-log` | 记录 Tier-0/1/2 逻辑事件 | KV 录制 |
| PowerShell `Get-Counter` / `typeperf` | 采集 PhysicalDisk、CPU、内存、GPU 和进程指标 | 系统级归因 |

## 3. 消费级 AI PC 的收敛范围

### 3.1 设备档位

| 档位 | SSD | 显存+系统内存 | 主要用途 |
|---|---|---|---|
| S32 | 1 TB / 2 TB | 32 GB | 轻量本地推理、RAG、7B/8B KV |
| S64 | 1 TB / 2 TB / 4 TB | 64 GB | 本地微调、8B checkpoint、RAG 主力 |
| S128 | 2 TB / 4 TB | 128 GB | 大数据集、70B subset、长时间混合负载 |

每台 DUT 必须记录实际 host RAM、VRAM、SSD 型号/固件、PCIe link、文件系统、剩余容量、Windows 电源策略和驱动版本；“32/64/128 GB”只作为系统分档，不能替代真实参数。

### 3.2 保留范围和容量预算

不得把整块消费级盘填满。建议默认保留 **15–20%** 未使用空间，并为 Windows、Docker、Milvus、结果文件和临时文件预留独立预算。

| SSD | 建议单次测试最大工作区 | 适合真实 workload |
|---|---:|---|
| 1 TB | 550–650 GiB | UNet/Retina 缩小数据集、8B checkpoint、1M VectorDB、8B KV |
| 2 TB | 1.1–1.35 TiB | 5×RAM training、8B/70B subset、1M–5M VectorDB |
| 4 TB | 2.2–2.8 TiB | 大型 training、70B subset 多轮、10M VectorDB、长时间 mixed |

容量计算应满足：

```text
active_workset + temporary_space + result_space + reserved_free_space
    <= filesystem_usable_space
```

Training 的 `5 × host memory` 是上限约束，不是强制一次性生成全部模型矩阵；在 1 TB/128 GB 组合上，应拆分数据形态逐项测试，不能同时保留多个训练集、checkpoint 和 VectorDB。

### 3.3 不纳入本轮主结论的内容

- NVMe 协议、固件合规、PLP、Sanitize、企业级耐久度认证。
- MPI 多节点、64/512/1024 rank full checkpoint。
- S3/object-storage 作为本地消费级 SSD 的主路径。
- 需要 Linux `drop_caches`、bpftrace 或独占块设备的强制条件；Windows 用 reboot、文件集驱逐和 Direct I/O 形成替代证据，并明确标注方法。
- 以峰值顺序带宽替代 AI workload 结论。

## 4. 多阶段测试流程

### Stage 0 — DUT 资格和可观测性门禁

**目标**：确认测试环境能够产生可信数据，不消耗大量 SSD 写入寿命。

**内容**：

1. 记录 SSD 身份、固件、容量、SMART/NVMe health、PCIe link、温度起点和剩余寿命。
2. 固定 Windows 电源模式、GPU 驱动、后台更新状态、Defender 扫描策略和 Docker Desktop 资源限制。
3. 建立三个路径：`DUT_DATA`、`DUT_CACHE`、`RESULTS`；尽量让 `RESULTS` 位于另一块盘。
4. 执行 `mlpstorage init`、`configview` 和各 workload 的 `datasize`。
5. 启动 1 秒采样：PhysicalDisk read/write bytes、IOPS、平均读写延迟、queue length、busy、温度、CPU、RAM、paging、GPU utilization/VRAM。

**通过条件**：身份和路径映射完整；容量预算通过；监控无明显缺口；结果目录不污染 DUT 统计。失败则停止后续阶段。

### Stage 1 — 路径、缓存和微型 I/O 校准

**目标**：先证明 Windows 上看到的是 SSD 真实能力，而不是页缓存、Docker VHDX 或结果写入。

| Case | 操作 | 重点指标 |
|---|---|---|
| S1-IO-01 | VDB 1K/128 trace replay，buffered | P50/P95/P99、逻辑/物理 bytes |
| S1-IO-02 | 同一 trace 使用 `--direct-io` | unbuffered bytes、对齐放大、延迟 |
| S1-IO-03 | cold → warm → reboot-cold 对照 | 物理读量、首轮/稳态延迟 |
| S1-IO-04 | 50/80/90% 盘占用短跑 | 温度、queue、GC 退化 |

每个 case 至少 3 次。输出“buffered、direct、cold、warm”四条独立曲线，不允许合并成单一平均值。

### Stage 2 — Native smoke bring-up

**目标**：验证四类业务在目标 AI PC 上能够端到端启动、访问 DUT、写出完整结果。

| 家族 | 建议 smoke | 实跑方式 |
|---|---|---|
| Training | UNet3D：2–8 个小文件；RetinaNet：1K–10K 小文件 | `mlpstorage open training ... run file`，单机非 MPI |
| Checkpoint | Llama3-8B，1 次 write + 1 次 read | local file backend；容量不足时使用已有 checkpoint 只做 read |
| KV | Llama3.1-8B，30–60 s，CPU tier 0/4 GB | `cache-dir` 指向 DUT；确认 Tier-2 bytes > 0 |
| VectorDB | Milvus 1K/50K vectors，HNSW/DISKANN，30 s query | Windows Docker Compose + `mlpstorage` CLI |

**通过条件**：进程退出码为 0；结果目录必需文件齐全；Training 有 AU/吞吐；Checkpoint 有读写字节和完整性；KV 有 storage entries；VDB 有 row count、QPS 和延迟；PhysicalDisk 在 workload 窗口有对应读写。

### Stage 3 — Representative workload characterization

这是消费级 AI PC 的主成绩阶段，控制在每台设备 4–8 小时。

#### 3.1 Training 三个代表性 profile

| Profile | 配置 | 变量 | 结论 |
|---|---|---|---|
| T-Large | UNet3D / 大文件 | 1/2/4 simulated accelerator；reader 1/4/8/16 | 持续供给能力和 AU |
| T-Small | RetinaNet / 小文件 | 并发 1/4/8；batch 和 threads | IOPS、metadata、尾延迟 |
| T-Medium | ResNet50 或 CosmoFlow / TFRecord | shuffle、batch、reader threads | 中小对象混合读取 |

每个 profile：1 次 warm-up + 3 次 measured；当 host RAM 为 32/64/128 GB 时，数据集分别优先覆盖至少 160/320/640 GB，若容量预算不允许则使用缩小版本并标记 `scaled`，不与 full 结果混报。

#### 3.2 Checkpoint 三个代表性 profile

| Profile | 适用盘 | 操作 |
|---|---|---|
| C-8B | 1/2/4 TB | 105 GB checkpoint；1、3、10 次 write/read；`fsync`；warm/cold restore |
| C-70B-subset | 2/4 TB | 约 114 GB、8-rank subset；至少 1 次完整 save/load，4 TB 可做 3–10 次 |
| C-Burst | 2/4 TB | 连续 checkpoint 间隔 5/30/300 s，观察 GC 和后续恢复退化 |

1 TB 盘不要求一次保留 10 个 8B checkpoint；可采用 `1 write → cold read → 删除 → 下一轮`，并报告“单轮恢复”而非正式 10/10 结果。

#### 3.3 KV Cache 三个代表性 profile

| Profile | 配置 | 变量 |
|---|---|---|
| K-NVMe | 8B，GPU/CPU tier=0 | users 25/50/100；none/realistic |
| K-CPU-spill | 8B，CPU tier=4 GB | spill threshold、eviction、P95/P99 |
| K-Trace-large | 70B/32B/120B 逻辑对象 | 录制 Tier-2 后 1×/2×/4× replay |

附加两轮 prefill-only/decode-only，分别得到写密集和读密集曲线；RAG、prefix cache、多轮和 autoscaling 作为扩展变量，而不是第一轮全部组合。

#### 3.4 VectorDB 两个代表性 profile

| Profile | 配置 | 变量 |
|---|---|---|
| V-1M | 1M × 1536，HNSW + DISKANN | top-k 10/100、query processes 1/2/4、search effort |
| V-10M | 10M × 1536，DISKANN，建议 4 TB | 仅在容量和 Docker 内存足够时执行；否则 5M scaled |

所有 ANN 比较必须先满足相同 Recall@K（建议目标 0.95 或项目指定门槛），再比较 QPS 和 P99；索引建立、flush、compact、load、search 分阶段计时。

### Stage 4 — Mixed workload and QoS

**目标**：验证 AI PC 日常同时训练、推理和本地 RAG 时，SSD 是否出现不可接受的尾延迟或吞吐塌陷。

优先执行两个组合：

1. `KV decode + Checkpoint write`：前台推理尾延迟对大块后台写入的敏感度。
2. `VDB search + ingest/compact`：RAG 查询在数据库后台维护时的 Recall/QPS/P99。

可选执行 `Training read + Checkpoint write`。每个组合先跑 solo，再以后台 50%/75%/100% 负载阶梯并发。

**建议门槛**：

- 前台 P99 ≤ solo 的 1.5 倍；
- 前台 Recall 不下降超过 1 个百分点；
- 后台吞吐 ≥ solo 的 80%；
- 无 I/O error、文件损坏、Docker/Milvus 重启或 KV eviction 异常；
- 温度、queue、CPU 和 paging 能解释所有性能下降。

### Stage 5 — Fill、热稳定性和长时间运行

**目标**：暴露消费级 SSD 在高占用、SLC 缓存耗尽、GC 和温度上升后的真实退化。

1. 盘占用：50%、80%、90% 三档；90% 只做短时敏感性测试。
2. workload：KV precondition、8B checkpoint 周期写入、VDB ingest+compact、Training 持续读。
3. 时长：1 TB 2–4 h；2 TB 4–8 h；4 TB 8–24 h。
4. 监控：温度、thermal throttle、write latency P99、queue、available capacity、Windows WHEA/StorPort 事件。

**判定**：无数据损坏；无持续错误；连续 3 个窗口的吞吐下降超过 10% 时标记 thermal/GC cliff，并报告恢复时间，不能仅给出全程平均值。

### Stage 6 — Recovery and data integrity

**目标**：验证“性能测试完成”之后数据仍然可用。

1. Checkpoint：比较写入前后文件大小、hash、恢复结果和元数据。
2. Training：重启后重新读取一个固定 batch，确认数据集清单和样本数一致。
3. KV：中止 workload 后重新启动，验证 cache 目录清理、孤儿文件和重新建立速度。
4. VectorDB：停止/启动 Milvus，验证 row count、index load、Recall 和首轮查询延迟。
5. Windows：执行 warm restart、系统 reboot-cold、Docker/Milvus restart 三种恢复路径。

恢复后重复 Stage 2 的最小 smoke；关键指标相对恢复前基线偏差超过 10% 时，标记为恢复退化而不是简单 Pass。

### Stage 7 — 发布判定和结果归档

每个 case 归档以下内容：

```text
case_id/run_id/
├── manifest.json              # DUT、SSD、软件、路径、seed、参数
├── workload/summary.json      # 应用指标
├── workload/metadata.json     # 运行元数据和验证状态
├── stdout.log / stderr.log
├── windows_disk_1s.csv        # PhysicalDisk 监控
├── process_1s.csv             # 进程/CPU/RAM/GPU 监控
├── trace.csv                  # 若为录制或回放
├── integrity.json             # hash、行数、文件大小
└── verdict.json               # pass / conditional / invalid / not-run
```

统一判定：

| 状态 | 含义 |
|---|---|
| `PASS` | 路径、数据完整性、监控和性能门槛均满足 |
| `CONDITIONAL` | 功能通过，但使用 scaled 数据、trace/replay 或未达到正式 MLPerf 进程规则 |
| `INVALID` | 实际未命中 DUT、缺少关键日志/监控、trace 不完整、数据损坏或容量门禁被绕过 |
| `NOT_RUN` | 硬件容量、软件或 Windows 能力不满足，不能用 0 分替代 |

## 5. 收敛后的核心 Case 集

建议把完整仓库能力收敛为 **29 个核心 case + 8 个可选扩展 case**：

| 阶段 | 核心 Case | 数量 |
|---|---|---:|
| Stage 0 | DUT/路径/容量/监控/配置门禁 | 3 |
| Stage 1 | buffered/direct/cold/warm/fill | 4 |
| Stage 2 | Training、Checkpoint、KV、VDB smoke | 4 |
| Stage 3 | 3 Training + 3 Checkpoint + 3 KV + 2 VDB | 11 |
| Stage 4 | KV+Checkpoint、VDB+ingest、Training+Checkpoint | 3 |
| Stage 5 | fill/thermal/soak | 2 |
| Stage 6 | recovery/integrity | 2 |
| **合计** | **核心发布套件** | **29** |

其中：

- **实盘必跑**：Stage 0–3 的本地 file、KV SSD tier、Milvus 1M 以内 workload，以及 Stage 6 integrity。
- **trace/replay 优先**：70B/405B/1T 大模型 KV 对象、无法放入本机的 VDB/Checkpoint 规模、倍速和超高并发压力。
- **可选扩展**：RAG/prefix/multi-turn/autoscaler 全组合、10M VectorDB、90% fill 长时间 soak、多个 reader/TP 全 sweep。

## 6. 推荐执行顺序

1. Stage 0：每换一台 SSD 或重装系统后都执行。
2. Stage 1：确认 Windows 路径和物理 I/O 口径。
3. Stage 2：确认四类业务链路可运行。
4. Stage 3：建立单 SSD 的基础画像和容量档位结果。
5. Stage 4：评价 AI PC 日常业务共存。
6. Stage 5：只在 Stage 3/4 稳定后执行，避免在错误配置上消耗 TBW。
7. Stage 6：完成恢复和数据完整性验证。
8. Stage 7：生成报告；将 native、scaled、trace/replay、not-run 分开统计。

该顺序使 1 TB 设备可以在约半天内完成资格、smoke 和代表性基线；2 TB/4 TB 设备再追加混合和长时间阶段。结果应按 **SSD 容量 × 内存档位 × workload 家族 × 执行模式** 分层比较，不能把不同容量、不同缓存状态或不同 trace 口径合并成一个总分。

## 7. 首轮执行的明确配置选择与理由

本节给出建议的“第一轮可执行配置”，用于避免把完整仓库矩阵一次性展开。

### 7.1 系统档位

| Profile | 硬件组合 | 首轮执行内容 | 选择理由 |
|---|---|---|---|
| P1 | 1 TB + 总内存/显存 32 GB | 8B KV、8B checkpoint、UNet/Retina scaled、1M VectorDB | 最小消费级配置，验证可用性和基础 I/O，不做大规模 endurance |
| P2 | 2 TB + 64 GB | 8B full、70B subset、ResNet50、1M/5M VectorDB、8B KV mixed | 代表主流 AI PC，容量和内存可以同时覆盖训练、恢复和本地 RAG |
| P3 | 4 TB + 128 GB | 大数据集 Training、8B 10/10、70B subset 多轮、10M VectorDB、KV trace stress | 评价高容量盘的持续写入、GC、热稳定性和混合业务能力 |

不建议把 `1 TB + 128 GB` 作为完整 Training 配置：Training 的 5×host-memory 约束会使数据集接近 640 GB，再叠加 checkpoint 和保留空间，必须拆成 scaled case 分开执行。

### 7.2 Training 配置

| Case | 具体配置 | 选择理由 |
|---|---|---|
| T1 大文件基线 | `unet3d_h100`；1 simulated accelerator；reader threads 4；默认 168 文件约 23.5 GiB 起步 | H100 配置体量小、容易在 1 TB 上启动，能先验证 NPZ 大文件供给和 AU |
| T1 持续压力 | `unet3d_b200`；1/2/4 simulated accelerators；数据集按 200/400/640 GiB 缩放 | B200 的 compute time 更短，能更快把压力转移到 SSD；完整约 984 GiB 只适合 4 TB 或特殊容量预算 |
| T2 小文件压力 | `retinanet_b200`；先 100K 文件，再 1.17M 文件；并发 1/2/4 | JPEG 单文件约 315 KiB，能暴露 metadata、IOPS 和小文件尾延迟；比单纯顺序带宽更贴近本地数据集读取问题 |
| T3 中等对象 | `resnet50_a100`；1024 TFRecord、batch 400、reader/computation threads 8 | 约 136.8 GiB，能在 1 TB/2 TB 上实跑，覆盖 TFRecord 内多 sample 读取 |
| 可选 T4 | CosmoFlow、DLRM、Flux | CosmoFlow 约 1.38 TiB，DLRM/Flux 更大；它们适合 4 TB scaled/full 或 trace，不作为 P1/P2 必测项 |

加速器类型在 Windows 单机测试中只是 DLIO 的计算间隔模型，不代表真实 GPU 性能。因此首轮固定一个基线，再用 1/2/4 加速器寻找 SSD 饱和点，不把 H100/B200 数值当成显卡排名。

### 7.3 Checkpoint 配置

| Case | 具体配置 | 选择理由 |
|---|---|---|
| C1 | `llama3-8b`；约 105 GB；1 write/read、3 write/read、4 TB 时 10/10 | 规模最接近消费级本地微调/恢复；模型和 optimizer shard 都能真实落盘 |
| C2 | `llama3-70b` subset；8 ranks；约 114 GB；2 TB/4 TB 执行 1 或 3 轮 | 在不需要 912 GB full checkpoint 的情况下，覆盖更大模型分片和突发写入 |
| C3 可选 | `llama3-405b` subset；约 94 GB；4 TB 单轮 | 只用于比较 shard 形态；不把它当作本机能运行 405B 模型的证明 |
| C4 trace | `llama3-1t` 或 405B full 逻辑 trace/replay | full 规模为 TB 级到十几 TB，超出消费级单盘合理范围 |

1 TB 设备采用“单轮写入 → cold read → 删除 → 下一轮”，不强行生成 10 个 checkpoint；否则测试结果会被容量和保留空间约束主导，而不是 SSD 性能。

Windows 单机 `num-processes=1` 的 checkpoint 读取只能作为功能 smoke；正式 checkpoint 规则要求 8 或更高的合法进程数，因此该结果标记为 `CONDITIONAL`，不作为 MLPerf CLOSED 成绩。

### 7.4 KV Cache 配置

| Case | 具体配置 | 选择理由 |
|---|---|---|
| K1 NVMe-only | `llama3.1-8b`；GPU/CPU tier=0；users 25/50/100；duration 300 s；generation `none` | 对应仓库固定 Option 1，Tier-2 I/O 最直接，适合比较 SSD 读写带宽和尾延迟 |
| K2 CPU spill | `llama3.1-8b`；CPU tier=4 GiB；users 25/50/100；max allocations 16 | 对应固定 Option 2，能观察 CPU RAM 耗尽后 spill 到 NVMe 的拐点 |
| K3 大对象 | `llama3.1-70b-instruct`；users 10/35/70；allocations 4 | 对应固定 Option 3，单对象更大但并发可控；2 TB/4 TB 可实跑，1 TB 优先 trace |
| K4 对象大小扩展 | `llama2-7b`、`mistral-7b`、`deepseek-v3`、`qwen3-32b` | 覆盖约 24–512 KiB/token 的对象分布，适合用 trace/replay 分离对象大小因素 |

首轮固定 `seed=42`、`duration=300 s`、3–5 trials，报告 median 和最大 P95/P99；`generation=realistic`、RAG、prefix cache、multi-turn 和 autoscaler 在基线稳定后再加，避免把 SSD、请求生成器和模型行为混在一起。

### 7.5 VectorDB 配置

| Case | 具体配置 | 选择理由 |
|---|---|---|
| V1 图索引 | 1M × 1536；HNSW；top-k 10/100；query processes 1/2/4 | 代表内存型本地 RAG，数据规模适合 1 TB/2 TB，能形成 QPS/Recall 基线 |
| V2 磁盘索引 | 1M × 1536；DISKANN；同一 query set | 代表 SSD 参与 ANN 查询的核心场景，必须和 HNSW 保持相同 Recall 门槛 |
| V3 大规模 | 10M × 1536；DISKANN；10 shards；仅 4 TB | 评价索引、load、后台 compaction 和持续读；1 TB/2 TB 使用 5M scaled |
| V4 可选压缩 | 1M × 512；AISAQ | 分析降低维度和压缩索引后，SSD 容量、QPS 和 Recall 的变化 |

VectorDB 运行固定 `timed=60 s` 作为基线，稳定后再使用 query-count 和 sweep。任何 index comparison 都先锁定 Recall@K，再比较 QPS/P99，避免用较低准确率换取虚高吞吐。

### 7.6 配置选择的总理由

上述选择遵循四个约束：

1. **代表不同 I/O 形态**：UNet3D 覆盖大文件带宽，RetinaNet 覆盖小文件 IOPS，ResNet50 覆盖中等对象，Checkpoint 覆盖大块写读，KV 覆盖小对象高并发和大对象 spill，VectorDB 覆盖随机 ANN 访问。
2. **能够落在 1–4 TB 消费级容量内**：大于 1 TB 的训练和 full checkpoint 不作为低容量设备的强制项。
3. **能够在 Windows 实际运行**：优先 local file、单机、Milvus Docker 和已验证的 Windows Direct I/O；MPI 多节点和 Linux-only object path 降为扩展或 replay。
4. **结果具有可解释性**：先固定模型和 seed，再逐步改变容量、并发、缓存状态、温度和混合负载，能够区分 SSD 能力与主机/软件瓶颈。
