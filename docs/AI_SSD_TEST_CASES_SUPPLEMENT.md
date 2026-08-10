# AI SSD 测试用例补充说明（技术与判定版）

**版本**：1.0

**用途**：解释管理层版文档中出现的指标、执行方式、证据要求和常见判定边界

**适用范围**：Training、Checkpointing、KV Cache、VectorDB、Mixed、Soak、Recovery
**上位文档**：[AI SSD 测试用例说明（管理层版）](AI_SSD_TEST_CASES_EXECUTIVE_GUIDE.md)

## 1. 文档层级和 Case 对应关系

本仓库现在区分规划材料和可执行 workload 入口：

| 层级 | 数量/内容 | 使用方式 |
|---|---|---|
| 完整场景矩阵 | 72 个规划项 | 只用于覆盖分析；其中 BLOCKED/whatif 项不生成执行入口 |
| 直接 native 套件 | 33 个 Case | `full_test_plan_cases/cases/`，直接调用 `mlpstorage open ...` |
| Trace 套件 | 1 个可执行 Case | `trace_test_cases/AI-VDB-015`，已验证 VectorDB capture/replay；KV trace 仍是扩展要求，不登记为假 Case |
| 消费级 native 套件 | 17 个核心 + 3 个可选 Case | `tools/ai_ssd_cases/cases/`，只保留真实 native workload |

管理报告应优先引用可执行 native 套件；Trace 套件必须以 `TRACE-CAPTURE`/`TRACE-REPLAY` 单独引用；完整矩阵只用于解释覆盖范围。环境探测、填盘、Docker restart、空 integrity 和 whatif 项不作为测试结果引用。

## 2. 术语解释

| 术语 | 含义 | 为什么重要 |
|---|---|---|
| AU（Accelerator Utilization） | 模拟加速器被数据供给的有效利用程度 | 训练吞吐高但 AU 低，可能是计算/数据节奏不匹配 |
| P95/P99/P99.9/P99.99 | 不是平均值，而是最慢请求分位数 | 低延迟业务通常由尾部请求决定体验 |
| QoS/SLA | 延迟或吞吐目标 | 用于判断最大合格用户数，而非只追求峰值 |
| Cold | 数据不应主要来自页缓存 | 用于证明恢复读或首次访问真正触及 SSD |
| Warm | 数据可能已在内存/页缓存 | 适合表示重复访问体验，不能替代 cold 结果 |
| Direct I/O | 尝试绕过操作系统页缓存的访问路径 | 用于校准 SSD 物理能力；必须用监控证明确实生效 |
| Tier-2 | KV Cache 的 NVMe/SSD 层 | `storage_entries=0` 或 Tier-2 bytes=0 时不是有效 SSD offload 测试 |
| Recall@K | 前 K 个搜索结果与真实答案的重合质量 | VectorDB 必须先固定质量，再比较速度 |
| QPS | 每秒查询数 | 需要和 Recall、并发、P99 一起解释 |
| Trace/Replay | 记录并回放逻辑 I/O 的方向、大小、节奏 | 可以隔离 SSD，但不保留完整应用和文件系统行为 |
| WAF | 设备实际写入量与主机写入量的比例 | 反映 GC、SLC 转换和内部放大；没有设备计数器时只能报告逻辑/物理近似 |
| pSLC | TLC SSD 中用于短时高性能写入的缓存区域 | 容量、填充率、回收和温度会显著影响后半程性能 |

## 3. 每个 Case 的统一执行状态机

### 3.1 准备阶段

记录 SSD 型号、序列号、固件、容量、PCIe link、文件系统、卷 GUID、剩余空间、温度、电源模式、BitLocker、TRIM、主机内存/显存和结果目录。

必须确认 data、cache、checkpoint、VectorDB volume 均落在目标 DUT；结果和原始日志尽量放在非 DUT。

### 3.2 设备状态阶段

每个性能 Case 必须明确以下一种状态：

| 状态 | 说明 |
|---|---|
| Fresh/FOB | 清理或新盘状态，只用于初始基线 |
| Preconditioned | 已按指定数据模式和写入量预处理 |
| Filled | 达到指定占用率，例如 50%/80%/90% |
| Steady-state | 经过足够运行窗口，性能和温度进入稳定区 |
| Warm/Cold | 明确页缓存和应用缓存状态 |

仅用 `fsutil file createnew` 增加逻辑文件长度，不能自动证明 NAND 已被真实写入。填充/预处理应尽量使用不可压缩数据、实际覆盖写、TRIM 和空闲回收，并保存执行量、耗时、空间和健康计数器。

### 3.3 Workload 阶段

执行顺序建议为：

1. 配置冻结：模型、数据集、seed、并发度、线程、TP、duration、top-k、读写比例。
2. Precondition：生成数据、加载 VectorDB、预置 KV Cache 或准备 Checkpoint。
3. Warm-up：确认命令、路径和监控正常，不计入正式成绩。
4. Measurement：至少三次独立运行；长稳 Case 使用连续时间窗口。
5. Post-check：检查退出码、文件数、字节数、hash、Recall、KV 命中和错误日志。

### 3.4 结果阶段

每次运行必须能回答：

- 逻辑 I/O 发生了多少；
- 物理 DUT 实际读写了多少；
- 应用指标和设备指标是否在同一时间窗口；
- CPU、内存、Docker 或温度是否先成为瓶颈；
- 数据是否完整；
- 结果是否达到 Case 的门槛。

## 4. 各类 Case 的技术判定

### 4.1 Training

主要指标：AU、samples/s、epoch time、逻辑读取量、PhysicalDisk 读取量、队列、CPU、page faults。

默认门槛沿用 workload 配置：UNet3D/ResNet50 通常为 AU≥90%，RetinaNet 为 AU≥85%，CosmoFlow/DLRM 等为 AU≥70%。数据集必须满足仓库规定的有效规模，至少覆盖 500 steps 和 `5 × host memory` 中的较大者，除非明确标记为 scaled 或 smoke。

判定重点：

- AU 达标后比较吞吐，而不是只比较吞吐；
- 至少三次运行并报告中位数、最小值和 CV；
- cold/direct 结果必须有物理读证据；
- CPU 持续饱和而 SSD 未饱和时，应标记 host-limited，不应把结果归因于 SSD。

### 4.2 Checkpoint

正式恢复流程建议为 `10 Save → 经过验证的 cache clear/reboot → 10 cold Load`。每个 rank 记录文件大小、完成时间、吞吐、hash 和错误。

主指标：

- 最慢 rank 完成时间；
- 最小 rank 吞吐；
- 全局 save/load 窗口；
- cold load 的物理读量；
- 连续 Checkpoint 的后半程退化。

如果 1 TB 设备无法保留规定数量的 Checkpoint，应执行单轮或少轮 smoke，并标记 `CONDITIONAL`/`NOT RUN`，不能把容量不足的结果当作完整 10/10 成绩。

### 4.3 KV Cache

至少验证以下硬条件：

1. `storage_entries > 0`；
2. Tier-2 实际读写字节大于 0；
3. 所有 rank/trial 都有结果；
4. OOM、并发上限或 CPU tier 吸收全部流量没有改变原定 workload 形状。

Interactive profile 的默认参考门槛为 P95/P99/P99.9/P99.99 不超过 50/100/150/200 ms；Responsive 和 Batch 使用仓库 `config.yaml` 中对应的门槛。

应分别报告：

- prefill 写密集；
- decode 读密集；
- mixed 读写；
- warm/cold；
- 不同 users、context、TP 和 tier 容量。

不能用 mixed 的平均吞吐掩盖 decode 的尾延迟。

### 4.4 VectorDB

执行顺序通常是 ingest → flush → compact/index build → load/restart → search。

主指标：row count、Recall@K、QPS、P50/P90/P99、first-query latency、索引构建时间、容量和物理 I/O。

比较索引或 SSD 时必须固定：数据集、seed、query set、top-k、距离度量和 Recall 门槛。推荐先要求 Recall@10≥0.95，再比较 QPS/P99。HNSW smoke 只能验证链路，不能替代 1M/10M DISKANN。

### 4.5 Mixed / Soak / Recovery

Mixed 需要先有各 workload 的 solo baseline，然后在相同 DUT 状态下并发运行。默认起始判定为：前台 P99 不超过 solo 的 1.5 倍，后台吞吐不低于 solo 的 80%；实际产品可按业务 SLA 收紧。

Soak 应报告时间序列，而不是只给全程平均值：温度、队列、吞吐、P99、容量、健康计数器和错误事件都要能定位到时间点。

Recovery 至少包含进程重启、服务/Docker 重启、Windows reboot-cold 和数据完整性检查。没有专用断电装置时，普通 reboot 不能替代 PLP/掉电测试。

## 5. 结果状态定义

| 状态 | 判定含义 |
|---|---|
| PASS | 路径、配置、监控、正确性和性能门槛全部通过 |
| CONDITIONAL | 功能和性能通过，但使用 scaled、trace/replay 或未满足正式规模 |
| FAIL | 真实 workload 执行，但业务门槛、QoS、Recall、稳定性或错误门槛未通过 |
| INVALID | 未命中 DUT、缓存口径不成立、缺少关键证据、trace 不完整或数据损坏 |
| NOT RUN | 容量、软件、硬件或平台条件不满足，尚未形成结果 |

`INVALID` 和 `NOT RUN` 不能用性能高低抵消；否则不同设备的测试条件不再可比。

## 6. 最小证据包

每个正式 Case 至少归档：

```text
<results>/<case>/<run>/
├── manifest.json             # DUT、版本、路径、参数、seed、执行模式
├── configview.txt            # 最终配置快照
├── workload_summary.json     # 应用指标和阶段时间
├── windows_disk_1s.csv       # PhysicalDisk 1 秒采样
├── process_1s.csv            # 进程/CPU/RAM/分页（如适用）
├── temperature_health.csv    # 温度和健康计数器
├── eventlog.evtx             # WHEA/StorPort 等事件（如适用）
├── trace.csv                 # Trace/Replay/Hybrid 才需要
├── integrity_report.json     # hash、文件数、row count 或 KV 校验
├── stdout.log / stderr.log   # 原始输出
└── verdict.json              # 最终状态、门槛、无效原因和瓶颈归因
```

## 7. 常见误读与纠正

| 误读 | 正确解释 |
|---|---|
| “物理读量比逻辑量小，所以 SSD 很快” | 可能是页缓存命中；必须另标 warm，不能称 cold |
| “Replay 吞吐很高，所以应用一定很快” | Replay 只保留逻辑 I/O 节奏，不含模型计算和数据库内部放大 |
| “模拟 8 个 accelerator 等于 8 张真实 GPU” | 它只用于制造更短的 compute gap 和更高 I/O 压力 |
| “Recall 低一点但 QPS 高很多，说明 SSD 更强” | 这是准确率与性能交换，不能作为同等质量下的比较 |
| “首个写入窗口很快” | 可能仍在 pSLC burst 阶段，应查看 sustained、温度和后半程 |
| “命令返回 0 就是 PASS” | 还需要业务阈值、数据完整性和 DUT 归因证据 |

## 8. 推荐的报告字段

管理汇总页只保留结论；技术附页建议保留：

`Case ID`、`执行模式`、`DUT 型号/固件`、`容量/填充率`、`模型/数据规模`、`固定参数`、`变化参数`、`主指标`、`P95/P99`、`中位数/CV`、`物理 I/O`、`CPU/RAM/温度`、`正确性结果`、`状态`、`无效条件`、`证据路径`、`限制和备注`。

## 9. 当前执行优先级

建议按以下顺序推进：

1. Stage 0：身份、容量、路径、配置和监控门禁；
2. Stage 1：buffered/direct、cold/warm、填充率和 I/O 校准；
3. Stage 2：四类 workload smoke 与完整性；
4. Stage 3：UNet3D/RetinaNet/ResNet50、8B Checkpoint、KV Option 1/2/3、1M HNSW/DISKANN；
5. Stage 4：KV+Checkpoint、VDB search+ingest、Training+Checkpoint；
6. Stage 5/6：热稳定、长时间运行和恢复；
7. 最后再扩展 10M VectorDB、405B/1T replay、RAG/prefix/multi-turn 和完整参数 sweep。

这样可以先得到可用于产品决策的最小闭环，再把扩展 Case 用于定位瓶颈，而不是让大量表格先于有效证据产生。
