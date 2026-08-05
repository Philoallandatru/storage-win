# AI SSD 测试计划标准化 Case 设计

**版本**：1.0

**上位计划**：[AI SSD 场景驱动测试方案](AI_SSD_TEST_PLAN.md)

**适用范围**：上位计划中的 72 个 AI SSD workload Case
**设计目的**：把“矩阵里的测试项”变成测试人员、评审人员和管理人员都能追踪的可执行 Case。

## 1. 使用方式

本文件是 `AI_SSD_TEST_PLAN.md` 的标准化 Case 设计附录。72 个 Case 保留原有 ID、模型、指标和执行状态；每个 Case 采用“家族默认模板 + Case 特有字段”的方式描述：

- 家族默认模板定义工具、步骤、证据包、无效条件和通用判定。
- Case 注册表定义该 Case 唯一的目的、配置、变化参数、通过标准、时长和状态。
- Case 如果没有覆盖某个默认字段，直接继承该家族默认值，不再重复抄写。

这样既保持 Excel 可导入字段的一致性，也避免 72 个 Case 的公共内容发生漂移。

## 2. 统一 Case 模板

### 2.1 必填的前 7 个字段

| 顺序 | 字段 | 填写要求 |
|---:|---|---|
| 1 | Case ID | 稳定、唯一；重跑不新建 ID |
| 2 | 测试工具 | CLI、配置、脚本、采集器及版本 |
| 3 | 测试目的 | 一句话说明要证明的系统行为 |
| 4 | 测试步骤 | 准备、配置、执行、采集、验证、判定；每步一个动作 |
| 5 | 测试时长 | 包含准备、预热、稳定窗口、正式运行和清理 |
| 6 | 测试脚本 | 可复制命令或脚本路径；变量使用 `<PLACEHOLDER>` |
| 7 | 测试标准 | 可计算的性能、完整性、稳态或路径门槛 |

### 2.2 工程附加字段

| 字段 | 填写要求 |
|---|---|
| 需求/来源 | 关联 `TR-AI-*` 需求或仓库配置/文档 |
| 阶段/优先级 | S0–S6；P0/P1/P2 |
| 测试家族 | Base、Training、Checkpoint、KV、VectorDB、Mixed |
| 推荐配置 | 模型、数据量、rank、用户数、索引等 |
| 容量/内存 | SSD 容量、host memory、必要时 GPU/VRAM |
| 执行模式 | Native、Scaled、Trace/Replay、Hybrid、X |
| 前置条件 | 数据生成、服务健康、容量、缓存状态等 |
| DUT 状态 | Fresh/FOB、Preconditioned、Filled、Steady、Warm、Cold |
| Active Range | 实际访问的数据或设备地址范围 |
| 块大小/RW/QD | 逻辑对象大小、读写比例、队列/线程/OIO |
| 数据模式 | 可压缩/不可压缩、随机种子、访问局部性 |
| 监控项 | 应用、PhysicalDisk、进程、温度、健康、事件日志 |
| 通过/失败/无效 | Pass、Conditional、Fail、Invalid、Not Run 的客观条件 |
| 证据包 | manifest、配置、日志、timeseries、trace、完整性和 verdict |
| 备注 | 容量限制、缩放比例、工具限制和结论边界 |

### 2.3 注册表字段的继承关系

为了让阅读版表格不变成 28 列的超宽 Excel，注册表使用以下映射：

| 模板字段 | 在本附录中的位置 |
|---|---|
| Case ID | 注册表 `Case ID` |
| 测试工具 | 注册表 `工具/模式` 的工具部分；完整版本见 Case 卡片 |
| 测试目的 | 注册表 `测试目的` |
| 测试步骤 | 所属家族默认模板的 `测试步骤`；Case 只写差异步骤 |
| 测试时长 | 注册表 `时长` |
| 测试脚本 | 注册表 `Script` |
| 测试标准 | 注册表 `通过标准` + 家族默认标准 |
| 需求/阶段/优先级 | 家族默认字段和上位计划第 4 节需求表；有特殊情况在 `状态/备注` 中覆盖 |
| 固定/变化参数 | 注册表对应两列；未列出的参数继承模型配置和家族默认值 |
| 前置条件/DUT 状态/监控/无效/证据 | 所属家族默认模板；Case 特有差异在目的、标准或备注中写明 |

这种继承关系是有意设计的：公共步骤和判定只维护一份，Case 表只保留真正影响结论的变量，避免同一个 Case 在 Excel、Markdown 和脚本中出现三套不一致描述。

## 3. 家族默认模板

Case 注册表中的“步骤、工具、证据和无效条件”默认继承下面的定义；Case 只记录自己的差异。

### BASE-DEFAULT：路径、缓存、重复性和填充率

| 字段 | 默认内容 |
|---|---|
| 测试工具 | PowerShell、`typeperf`/Windows monitor、`vdbbench.replay`（适用时） |
| 测试步骤 | 1. 识别 DUT；2. 准备缓存/填充状态；3. 运行 warm-up；4. 执行三次 measured run；5. 合并应用和设备时间戳；6. 归档 verdict |
| 默认时长 | 15–60 分钟 |
| 默认脚本 | `tools/record_windows_io.ps1`、对应 replay 命令 |
| 默认监控 | PhysicalDisk bytes、IOPS、平均延迟、queue、busy、CPU/RAM、温度、健康计数器 |
| 默认证据 | manifest、路径映射、1 秒设备监控、健康快照、原始日志、verdict |
| 默认无效 | 未命中目标盘、结果目录落入 DUT、缓存状态不明、监控缺口、盘符与序列号无法对应 |

### TRAIN-DEFAULT：训练数据供给

| 字段 | 默认内容 |
|---|---|
| 测试工具 | `mlpstorage training`、DLIO workload YAML、`datasize`/`datagen`、Windows monitor |
| 测试步骤 | 1. 执行 datasize；2. 生成数据；3. 验证文件数/字节数；4. warm-up；5. 固定 epochs 执行三次；6. 校验 AU、samples/s 和物理读；7. 归档结果 |
| 默认时长 | 45 分钟–8 小时，按数据规模和模式调整 |
| 默认脚本 | `mlpstorage ... training datasize` → `datagen` → `run`；模型配置来自 `configs/dlio/workload/` |
| 默认固定参数 | seed、数据格式、epochs、模型配置、host memory、结果目录 |
| 默认监控 | AU、samples/s、epoch time、逻辑/物理读、queue、CPU、RAM、page faults、温度 |
| 默认标准 | AU 达到 workload 门槛；无读取错误；三次吞吐 CV≤5%；数据实际命中 DUT |
| 默认无效 | 数据集不足、物理读≈0、结果盘成为瓶颈、CPU 持续饱和且 SSD 未饱和、配置与数据漂移 |
| 默认证据 | datasize、datagen manifest、summary、metadata、timeseries、stdout/stderr、1 秒监控、verdict |

### CKP-DEFAULT：Checkpoint 保存、冷恢复和一致性

| 字段 | 默认内容 |
|---|---|
| 测试工具 | `mlpstorage checkpointing`、fsync、hash/integrity 工具、Windows monitor |
| 测试步骤 | 1. 做容量 gate；2. 固定 rank/layout；3. Save-only；4. 记录 fsync/close；5. 清缓存或重启；6. Load-only；7. 校验 hash、字节数和最慢 rank；8. 归档 verdict |
| 默认时长 | 1–8 小时；完整 10 Save+10 Load 按容量增加 |
| 默认脚本 | `mlpstorage ... checkpointing run file`；写读阶段使用 `num-checkpoints-read/write` 分离 |
| 默认固定参数 | 模型、rank、checkpoint layout、fsync、结果目录、容量余量 |
| 默认监控 | 每 rank bytes/time、min throughput、max completion time、rank skew、物理读写、温度、健康 |
| 默认标准 | 所有 rank/轮次完成；逻辑字节正确；hash/restore 正确；cold load 有物理读证据 |
| 默认无效 | 缺 rank/轮次、读命中页缓存、容量不足未标记、数据损坏、冷态方法不可验证 |
| 默认证据 | rank 结果、checkpoint metadata、hash、summary、cold 方法记录、1 秒监控、verdict |

### KV-DEFAULT：KV Cache 分层、尾延迟和回放

| 字段 | 默认内容 |
|---|---|
| 测试工具 | `kv_cache_benchmark`/`kv_cache.cli`、KV trace、`vdbbench.replay`、Windows monitor |
| 测试步骤 | 1. 确认 cache-dir 在 DUT；2. 配置 tier 容量；3. precondition；4. warm-up；5. 三次 measured trial；6. 验证 `storage_entries` 和 Tier-2 bytes；7. 分析 QoS/trace；8. 归档 verdict |
| 默认时长 | 15 分钟–4 小时 |
| 默认脚本 | `python -m kv_cache.cli ...`；Trace Case 先过滤 Tier-2，再用 `vdbbench.replay --direct-io` |
| 默认固定参数 | model、context、seed、duration、generation mode、performance profile、结果目录 |
| 默认监控 | storage entries、read/write BW、tokens/s、P95/P99/P99.9/P99.99、hit/evict、queue、CPU/RAM、温度 |
| 默认标准 | Tier-2 bytes>0；所有 trial/rank 有结果；对应 QoS 达标；trace 时间和对象关系完整 |
| 默认无效 | CPU tier 吸收全部 I/O、cache-dir 落错盘、缺 rank/trial、未过滤 tier、trace 对象缺失/时间倒退 |
| 默认证据 | 配置、rank JSON、KV summary、trace、过滤 trace、replay 结果、1 秒监控、verdict |

### VDB-DEFAULT：向量库导入、索引、搜索和共存

| 字段 | 默认内容 |
|---|---|
| 测试工具 | Milvus/Docker、`vdbbench`、ground truth、Windows monitor |
| 测试步骤 | 1. 验证容器和 volume；2. ingest；3. flush/compact/index build；4. 建 ground truth；5. cold/warm load；6. search sweep；7. 校验 row count/Recall；8. 归档 verdict |
| 默认时长 | 30 分钟–8 小时 |
| 默认脚本 | `vdbbench` 配置文件、`--io-trace-log`；回放使用 `vdbbench.replay` |
| 默认固定参数 | dataset、seed、query set、top-k、metric、index config、volume、结果目录 |
| 默认监控 | vectors/s、phase time、Recall@K、QPS、P50/P90/P99、logical/device bytes、Docker CPU/RAM、温度 |
| 默认标准 | row count 正确；Recall 达到门槛后再比较 QPS/P99；阶段无错误；trace 完整 |
| 默认无效 | volume 未命中 DUT、Recall 不达标仍参与排名、容器重启、trace 不完整、逻辑/物理字节混报 |
| 默认证据 | load/index/search summary、ground truth、recall_stats、trace、Docker health、设备监控、verdict |

### MIX-DEFAULT：前后台共存和长稳

| 字段 | 默认内容 |
|---|---|
| 测试工具 | 对应前后台 workload、并发启动器、Windows monitor、健康/事件采集 |
| 测试步骤 | 1. 建立各自 solo baseline；2. 准备相同 DUT 状态；3. 同步启动前后台；4. 运行稳定窗口；5. 记录前台尾延迟和后台吞吐；6. 结束后校验数据；7. 归档 verdict |
| 默认时长 | 1–8 小时 |
| 默认固定参数 | solo 基线、seed、工作集、温度起点、前后台启动屏障、结果目录 |
| 默认监控 | foreground P95/P99、background throughput、queue、temperature、CPU/RAM、errors、health |
| 默认标准 | 前台 P99≤1.5×solo；后台吞吐≥0.8×solo；无数据错误；时间窗口无监控缺口 |
| 默认无效 | 没有真正重叠、无 solo baseline、只测总吞吐、监控未覆盖混合窗口、host-limited |
| 默认证据 | 两类 workload summary、并发时间线、solo/mixed 对比、设备/进程监控、健康和 verdict |

## 4. Case 卡片示例：AI-TRN-003

下面是完整展开后的 Case 卡片；注册表中的其他 Case 继承所属家族默认字段，并覆盖差异字段。

| 字段 | 内容 |
|---|---|
| Case ID | `AI-TRN-003` |
| 测试工具 | `mlpstorage` + DLIO；`configs/dlio/workload/unet3d_b200.yaml`；Windows 1 秒采集 |
| 测试目的 | 验证大 NPZ 文件持续读取时，单盘能够支持多少 B200 模拟加速器而不让训练等待 |
| 测试步骤 | 1. 执行 datasize；2. 生成声明规模的数据；3. 确认结果目录不在 DUT；4. 运行 1/2/4/8 accelerator warm-up；5. 每档执行 3 次；6. 校验 AU、samples/s、物理读和温度；7. 输出最大合格 accelerator 数 |
| 测试时长 | 缩小数据集 1–3 小时；完整约 983 GiB 作为 Scaled/Scaled-up 试验 |
| 测试脚本 | `mlpstorage open training run file --accelerator-type b200 --num-accelerators <N> --data-dir <DUT_DIR> --results-dir <RESULT_DIR>` |
| 测试标准 | AU≥90%；三次吞吐 CV≤5%；direct/cold 模式有物理读证据；输出可解释饱和点 |
| 需求/阶段/优先级 | `TR-AI-TRAIN-001/003`；Q1；P0 |
| 固定/变化参数 | 固定模型、seed、epochs、host memory、reader 配置；变化 accelerator 数、数据规模和路径模式 |
| DUT 状态 | Preconditioned；分别记录 warm、cold、Direct |
| 监控/证据 | AU、samples/s、epoch、PhysicalDisk、queue、CPU、RAM、temperature、summary、metadata、timeseries、verdict |
| 无效条件 | 数据不足、结果盘在 DUT、物理读≈0、CPU 饱和而 SSD 未饱和、monitor 缺口 |

## 5. 72 个 Case 注册表

以下注册表按模板填写 Case 的差异字段。`步骤/工具/证据/无效` 继承第 3 节对应的家族默认值；`Script` 给出执行入口或配置来源。

### 5.1 Base（4）

| Case ID | 工具/模式 | 测试目的 | 固定参数 | 变化参数 | 时长 | Script | 通过标准 | 状态 |
|---|---|---|---|---|---:|---|---|---|
| AI-BASE-001 | PowerShell；S0 | 建立 DUT、卷映射、容量和结果路径基线 | 4 块盘映射、结果盘分离 | 无 | 15–20m | `S0-ENV-01` / inventory | identity、路径、容量和监控字段完整 | Now |
| AI-BASE-002 | replay + monitor；Q1 | 分离 buffered、cold、warm、Direct 的缓存影响 | 同一 trace/数据集、seed、结果目录 | 访问模式 | 20–30m | `S1-IO-01/02/03` | 三类结果独立；逻辑/物理量不混报 | Now |
| AI-BASE-003 | PowerShell/typeperf；Q1 | 验证重复性和监控开销 | 同 workload、3 runs、固定 DUT 状态 | monitor off/on | 30–45m | `S1-IO-03` | CV≤5%；监控开销≤2%；无采样缺口 | Now |
| AI-BASE-004 | fill + replay；Q1/X | 观察填充率导致的 GC、SLC 和尾延迟变化 | 同一 workload、健康快照 | 20/50/80/90% fill | 45–60m | `S1-IO-04` | 输出退化曲线；无未解释 cliff | 需授权测试目录 |

### 5.2 Training（16）

| Case ID | 工具/模式 | 测试目的 | 固定参数 | 变化参数 | 时长 | Script | 通过标准 | 状态 |
|---|---|---|---|---|---:|---|---|---|
| AI-TRN-001 | DLIO；X | 建立 UNet3D/A100 大文件低压力基线 | NPZ、seed、epochs | accel 1/2/4；cold/direct | 1–2h | `unet3d_a100.yaml` | AU≥90%；samples/s 可重复 | Now-X |
| AI-TRN-002 | DLIO；X | 观察 H100 缩短 compute gap 后的存储压力 | NPZ、固定 reader | accel 1/2/4 | 1–2h | `unet3d_h100.yaml` | AU≥90%；queue/CPU/SSD 瓶颈可归因 | Experimental |
| AI-TRN-003 | DLIO；Q1 | 测 B200 大文件持续读和最大合格并发 | NPZ、AU 门槛 90% | datasize；accel 1/2/4/8 | 1–3h | `unet3d_b200.yaml` | AU≥90%；CV≤5%；物理读有效 | Reduced；full 983 GiB |
| AI-TRN-004 | DLIO；Q1 | 测百万级 JPEG 小文件和 metadata 压力 | JPEG、AU 门槛 85% | accel 1/4/8/16 | 1–3h | `retinanet_b200.yaml` | AU≥85%；files/s、P99 达标 | Now-Q1 |
| AI-TRN-005 | DLIO；Q1 | 比较 MI355 compute/batch 节奏下的小文件压力 | JPEG、固定文件集 | accel 1/4/8/16 | 1–3h | `retinanet_mi355.yaml` | AU≥85%；无文件缺失 | Now-Q1 |
| AI-TRN-006 | DLIO；X | 测 CosmoFlow 中小对象和 shuffle | TFRecord、shuffle seed | accel 1/2/4 | 2–4h | `cosmoflow_a100.yaml` | AU≥70%；IOPS/拐点可解释 | Reduced-X |
| AI-TRN-007 | DLIO；X | 测高请求率的 CosmoFlow 读取 | TFRecord、shuffle | accel 1/2/4/8 | 2–4h | `cosmoflow_h100.yaml` | AU≥70%；P99/queue 可归因 | Reduced-X |
| AI-TRN-008 | DLIO；X | 测 ResNet50 文件内多 sample 读取 | TFRecord、batch、threads | reader/batch 固定 | 1–2h | `resnet50_a100.yaml` | AU≥90%；samples/s 稳定 | Now-X |
| AI-TRN-009 | DLIO；X | 测更高供给速率下的 ResNet50 | TFRecord、batch | accel 1/2/4/8 | 1–2h | `resnet50_h100.yaml` | AU≥90%；throughput/queue 可解释 | Now-X |
| AI-TRN-010 | DLIO；X | 测 DLRM Parquet row-group 和列裁剪 | Parquet、列选择 | prefetch 0/2/4 | 2–4h | `dlrm_b200.yaml` | AU≥70%；row-groups/s 可重复 | Reduced-X |
| AI-TRN-011 | DLIO；X | 测 DLRM 并行 row-group 读取 | Parquet、固定列 | threads 1/4/8/16 | 2–4h | `dlrm_mi355.yaml` | AU≥70%；CPU/SSD 瓶颈可解释 | Reduced-X |
| AI-TRN-012 | DLIO；X | 测 Flux 大 Parquet 对象 burst 读 | Parquet、batch/threads | threads 4/8/16 | 2–4h | `flux_b200.yaml` | AU≥90%；GiB/s、温度稳定 | Reduced-X |
| AI-TRN-013 | DLIO；X | 测 Flux 长 compute gap 下的 burst latency | Parquet、batch 72 | threads sweep | 2–4h | `flux_mi355.yaml` | AU≥90%；burst 等待可解释 | Reduced-X |
| AI-TRN-014 | DLIO；Q1 | 找到最大合格 accelerator 数 | UNet/Retina 固定 workload | 1→饱和 | 1–3h | training scaling runner | AU 合格点和 speedup knee 清楚 | Now-Q1 |
| AI-TRN-015 | DLIO；X | 找到 reader/CPU/SSD 饱和拐点 | 模型、data、accelerator 固定 | threads 1/2/4/8/16/32 | 1–3h | reader scaling runner | throughput、CPU、queue 拐点可归因 | Now-X |
| AI-TRN-016 | DLIO；Q1 | 量化 warm/cold/Direct 缓存污染 | 同数据集、同逻辑量 | warm/cold/`--o-direct` | 1–2h | cache/path runner | 物理读、AU 和 epoch 差异有证据 | Now-Q1 |

### 5.3 Checkpoint（9）

| Case ID | 工具/模式 | 测试目的 | 固定参数 | 变化参数 | 时长 | Script | 通过标准 | 状态 |
|---|---|---|---|---|---:|---|---|---|
| AI-CKP-001 | checkpointing；Smoke | 建立 8B 单节点 save/load 基线 | 8 ranks、105 GB、fsync | 1/10 cycles | 1–4h | `llama3_8b_checkpoint.yaml` | save/load、hash、cold read 正确 | Smoke only |
| AI-CKP-002 | checkpointing；Smoke | 模拟 70B 8-rank node-local 分片 | 8 ranks、114 GB | cycles、cold/warm | 1–4h | `llama3_70b.yaml` subset | 最慢 rank、最小吞吐、hash 正确 | Smoke only |
| AI-CKP-003 | checkpointing；Scaled | 测 70B full 多节点并发写恢复 | 64 ranks、912 GB | layout、节点数 | 4–8h | full 70B config | global duration、rank skew 可解释 | Scaled |
| AI-CKP-004 | checkpointing；Scaled | 测 405B node-local 分片容量边界 | 8 ranks、94 GB | cold/warm、cycles | 2–4h | 405B subset config | save/load、cold bytes、空间余量 | Capacity tight |
| AI-CKP-005 | checkpointing；Scaled | 测 405B TB 级 shared storage | 512 ranks、5.29 TB | scale、rank layout | 8h+ | full 405B config | global scale、最慢 rank、无损坏 | Scaled |
| AI-CKP-006 | checkpointing；Smoke | 测 1T 最大单节点分片 burst/GC | 8 ranks、161 GB | cycles、interval | 2–4h | 1T subset config | burst、GC、恢复时间可解释 | Smoke only |
| AI-CKP-007 | checkpointing；Scaled | 测 1T full 极大规模恢复 | 1024 ranks、18 TB | node/rank scale | 8h+ | full 1T config | global save/load、数据完整 | Scaled |
| AI-CKP-008 | checkpointing；Q1 | 独立证明恢复读命中 SSD | write-only、cache clear/reboot | warm/cold 方法 | 1–3h | write/read split runner | 物理读与逻辑量时间对齐 | Windows cold method required |
| AI-CKP-009 | checkpointing；X | 测周期性 Checkpoint 和后台 GC | 5/30/300 s interval | 1/2/10 cycles | 1–4h | burst interval runner | 后续 checkpoint 退化、P99 可解释 | Q1/X |

### 5.4 KV Cache（22）

| Case ID | 工具/模式 | 测试目的 | 固定参数 | 变化参数 | 时长 | Script | 通过标准 | 状态 |
|---|---|---|---|---|---:|---|---|---|
| AI-KV-001 | KV CLI；Native | 测 8B NVMe-only 高并发 | 200 users、GPU/CPU=0、allocs=16 | trials、duration | 1–2h | MLPerf option 1 | Tier-2 bytes>0；QoS 通过 | Now |
| AI-KV-002 | KV CLI；Native | 测 4 GB CPU tier 溢出边界 | 100 users、CPU=4 GB、allocs=16 | spill point、trials | 1–2h | MLPerf option 2 | spill 可见；P95/P99 达标 | Now |
| AI-KV-003 | KV CLI；Native | 测 70B 大 KV 对象 | 70 users、allocs=4 | duration、precondition | 1–2h | MLPerf option 3 | P95、BW、RAM 和 tier bytes 达标 | Now |
| AI-KV-004 | KV CLI；X | 测 tiny-1b 小对象 IOPS | 固定 context、duration | users 10→500 | 30–90m | tiny-1b model | IOPS/P99 可重复 | Now-X |
| AI-KV-005 | KV CLI；X | 测 mistral-7b 中等对象 | 128 KiB/token | context/users | 30–90m | mistral-7b model | tail latency/BW 达标 | Now-X |
| AI-KV-006 | KV CLI；X | 测 llama2-7b 大对象上界 | 512 KiB/token | alloc 1/2/4/8 | 30–90m | llama2-7b model | P99.9、OOM guard 有效 | Now-X |
| AI-KV-007 | KV CLI；Native | 建立 8B users 负载曲线 | llama3.1-8b、固定 context | users 25/50/100/200 | 1–2h | model users sweep | 输出最大合格 users | Now |
| AI-KV-008 | KV CLI；Native | 建立 70B users 负载曲线 | llama3.1-70b、allocs=4 | users 10/35/70/140 | 1–2h | model users sweep | 输出最大合格 users | Now |
| AI-KV-009 | KV CLI；X | 测 MLA 压缩 KV 小对象效率 | deepseek-v3 | context 4K/8K/25K | 1–2h | direct CLI | bytes/request、IOPS、P99 可解释 | Direct CLI X |
| AI-KV-010 | KV CLI；X | 测 qwen3-32b 中大对象 | 256 KiB/token | context/users | 1–2h | direct CLI | P99/BW 可解释 | Direct CLI X |
| AI-KV-011 | KV CLI；X | 测 MoE 小 KV 的高用户数 | gpt-oss-20b | high users | 1–2h | direct CLI | IOPS、CPU overhead 可解释 | Direct CLI X |
| AI-KV-012 | KV CLI；X | 区分模型规模和 KV I/O 规模 | gpt-oss-120b | users/context | 1–2h | direct CLI | throughput/P99 可解释 | Direct CLI X |
| AI-KV-013 | KV CLI；X | 找 GPU/CPU tier 容量导致的 spill 拐点 | 固定 model/users | tier 0/4/16/32 GiB | 1–2h | tier capacity sweep | occupancy、spill latency 可解释 | Simulated tiers |
| AI-KV-014 | KV trace；X | 测 TP 对 per-rank 对象大小的影响 | num_gpus≥TP | TP 1/2/4/8 | 1–2h | TP trace generator | per-rank bytes、aggregate BW 可解释 | Trace/simulation |
| AI-KV-015 | KV CLI；Native | 测 prefill 写密集压力 | model/users/context 固定 | user/context sweep | 1–2h | `--prefill-only` | write BW、fsync、P99 达标 | Now |
| AI-KV-016 | KV CLI；Native | 测 decode 读密集压力 | 预置 cache、model 固定 | users/context | 1–2h | `--decode-only` | read BW、P99.99 达标 | Now |
| AI-KV-017 | KV CLI；X | 测短/长上下文对象分布 | persona、seed 固定 | chatbot/coding/document | 1–2h | context persona config | object CDF、tail latency 可解释 | Now-X |
| AI-KV-018 | KV CLI；X | 区分峰值压力和真实节奏 | model/users 固定 | none/fast/realistic | 1–2h | generation mode config | active/wall BW、SLA 分开 | Now-X |
| AI-KV-019 | KV CLI；X | 测 RAG、prefix 和 multi-turn 复用 | docs、model、seed 固定 | feature on/off、docs 10/100 | 1–2h | RAG/prefix config | hit rate、bytes saved、P99 可解释 | Now-X |
| AI-KV-020 | KV CLI；X | 找 QoS 饱和点和恢复能力 | duration、profile 固定 | users/rate +20/25% | 1–2h | saturation runner | 最大合格负载、queue、recovery | Now-X |
| AI-KV-021 | KV trace/replay；X | 用 Tier-2 trace 复现 SSD 逻辑压力 | 只保留 Tier-2、seed=42 | 1×/2×/4× Direct | 30–90m | trace filter + replay | 无缺对象/倒退；aligned bytes 正确 | Now；先过滤 |
| AI-KV-022 | KV trace/replay；X | 使用真实 arrival/context 分布 | BurstGPT/ShareGPT trace | speed、cycles、dataset | 1–3h | external trace | burst tail、queue、drop 可解释 | External data required |

### 5.5 VectorDB（16）

| Case ID | 工具/模式 | 测试目的 | 固定参数 | 变化参数 | 时长 | Script | 通过标准 | 状态 |
|---|---|---|---|---|---:|---|---|---|
| AI-VDB-001 | Milvus/vdbbench；Smoke | 验证 Windows VDB 链路和 trace | 1K×128 HNSW、seed/query seed | planted query | 30–60m | smoke config | Recall、QPS、trace 完整 | Completed |
| AI-VDB-002 | Milvus/vdbbench；Native | 建立 1M HNSW 内存图基线 | 1M×1536、M64 | ef 32/128/256 | 2–4h | `1m_hnsw.yaml` | Recall 达标后比较 QPS/P99 | Now |
| AI-VDB-003 | Milvus/vdbbench；Native | 建立 1M DISKANN 磁盘 ANN 基线 | 1M×1536、degree64 | search list | 2–4h | `1m_diskann.yaml` | Recall、QPS/P99、物理读达标 | Now |
| AI-VDB-004 | Milvus/vdbbench；Native | 测维度对磁盘访问的影响 | 1M×512 DISKANN | 与 1536 维对照 | 2–4h | `1m_diskann_512dim.yaml` | bytes/query、QPS 可解释 | Now |
| AI-VDB-005 | Milvus/vdbbench；X | 测 AISAQ 压缩索引的容量/质量权衡 | 1M×512、AISAQ | inline_pq 16/32 | 2–4h | `1m_aisaq_512dim.yaml` | Recall、capacity、QPS 达标 | Engine check |
| AI-VDB-006 | Milvus/vdbbench；Native | 测 10M HNSW 多 shard 扩展 | 10M×1536、10 shards | query process 1/4/8 | 4–8h | `10m_hnsw.yaml` | load/scale/P99 可解释 | Capacity required |
| AI-VDB-007 | Milvus/vdbbench；Native | 测 10M DISKANN 磁盘读和温度 | 10M×1536、10 shards | query/compact | 4–8h | `10m_diskann.yaml` | QPS、physical IO、temperature 可解释 | Capacity required |
| AI-VDB-008 | Milvus/vdbbench；X | 在相同 Recall 下比较索引家族 | 数据集、query、top-k 固定 | index family | 4–8h | index sweep runner | Recall 达标后比较 QPS/容量 | Open/X |
| AI-VDB-009 | Milvus/vdbbench；X | 绘制精度—性能曲线 | dataset、seed、top-k 固定 | ef/search-list 32→512 | 1–3h | search effort sweep | Recall/QPS/P99 曲线完整 | Now-X |
| AI-VDB-010 | Milvus/vdbbench；X | 找查询并发饱和点 | query set、index 固定 | processes 1/2/4/8/16 | 1–3h | query process sweep | aggregate QPS、queue、CPU 可解释 | Now-X |
| AI-VDB-011 | Milvus/vdbbench；X | 测 batch 对 QPS 和 per-query P99 的影响 | dataset、index、query fixed | batch 1/8/32/64 | 1–3h | search batch sweep | QPS 与 per-query P99 分开 | Now-X |
| AI-VDB-012 | Milvus/vdbbench；X | 测 ingest/flush/compact tuning | dataset、seed 固定 | batch 1K/10K、compact on/off | 2–4h | ingest tuning runner | vectors/s、phase time 可解释 | Now-X |
| AI-VDB-013 | Milvus/vdbbench；X | 测 topK、metric、dimension 对访问量的影响 | index、query set 固定 | K10/100；COSINE/L2/IP | 1–3h | query shape sweep | Recall、result bytes、latency 可解释 | Now-X |
| AI-VDB-014 | Milvus/vdbbench；Native | 分离 load、cold first query 和 warm search | restart/load、query fixed | cold/warm/search-only | 2–4h | cold/warm runner | first/steady P99 分开 | Now |
| AI-VDB-015 | VDB trace/replay；X | 回放 VDB 逻辑 I/O 压力 | trace、seed、data fixed | both/search-only、1×/2×/4× | 1–3h | `vdbbench.replay` | logical/device bytes 分层 | Completed 1× |
| AI-VDB-016 | Milvus/orchestrator；X | 测 ingest/index 对前台 search 的干扰 | 独立 query/ingest clients | ingest rate、compact | 2–4h | coexist runner | Recall 不降；foreground P99≤1.5× | Orchestrated extension |

### 5.6 Mixed（5）

| Case ID | 工具/模式 | 测试目的 | 固定参数 | 变化参数 | 时长 | Script | 通过标准 | 状态 |
|---|---|---|---|---|---:|---|---|---|
| AI-MIX-001 | Training + Checkpoint；Hybrid | 测持续读和突发写共存 | solo baselines、seed、DUT state | background checkpoint rate | 1–3h | mixed orchestrator | AU 达标；CKP≥0.8×solo | Q1/X |
| AI-MIX-002 | KV + Checkpoint；Hybrid | 测大写入对 KV 尾延迟的影响 | KV option、checkpoint layout | write interval/rate | 1–3h | mixed orchestrator | KV P99≤1.5×solo 且 SLA 通过 | Q1/X |
| AI-MIX-003 | VDB search + ingest；Native | 测建库后台活动对 RAG 搜索的影响 | Recall threshold、query set | ingest/compact rate | 1–3h | VDB coexist runner | Recall 不降；P99≤1.5×solo | Extension |
| AI-MIX-004 | KV interactive + VDB search；Hybrid | 测两种前台随机读共存 | 两者 solo baseline | user/query rate | 1–3h | mixed orchestrator | 两者 SLA 均通过 | Extension |
| AI-MIX-005 | 四类 workload + fill/GC；Soak | 测 8 小时长期共存、GC 和热退化 | fill、seed、工作集固定 | cycle、background pressure | 8h | soak orchestrator | 0 错误；无持续>10%退化 | Soak |

## 6. 统一判定、证据和结果字段

### 6.1 结果状态

| 状态 | 含义 |
|---|---|
| PASS | 路径、配置、监控、正确性和性能门槛全部通过 |
| CONDITIONAL | 使用 scaled、trace/replay 或未满足正式规模，但功能和测量有效 |
| FAIL | workload 实际运行，但业务、QoS、Recall、稳定性或错误门槛未通过 |
| INVALID | 未命中 DUT、缓存口径不成立、证据缺失、trace 不完整或数据损坏 |
| NOT RUN | 容量、软件、硬件或平台条件不足，没有形成结果 |

### 6.2 最小证据包

```text
runs/<case_id>/<run_id>/
├── manifest.json             # Case、DUT、版本、路径、参数、seed、模式
├── configview.txt            # 最终配置快照
├── workload_summary.json     # 应用指标和阶段时间
├── windows_disk_1s.csv       # PhysicalDisk 1 秒采样
├── process_1s.csv            # 进程/CPU/RAM/分页（如适用）
├── temperature_health.csv    # 温度、健康、空间
├── eventlog.evtx             # WHEA/StorPort 等事件（如适用）
├── trace.csv                 # Trace/Replay/Hybrid 才需要
├── integrity_report.json     # hash、文件数、row count、Recall 或 KV 校验
├── stdout.log / stderr.log   # 原始输出
└── verdict.json              # 状态、门槛、无效原因、瓶颈归因
```

### 6.3 统一性能统计

- 性能 Case 至少三次独立有效运行；报告 median、min/max、CV 和最差稳定窗口。
- P99/P99.9/P99.99 必须有足够的请求样本数；样本不足时标记为 `INSUFFICIENT_SAMPLE`，不能伪造精度。
- 逻辑 I/O、应用指标和物理 I/O 按 UTC 时间对齐。
- Native、Scaled、Trace/Replay、Hybrid 分开统计，不能合并成一个排名。
- 任何正确性、路径、数据损坏、缺 rank、缺监控问题，不能被较高吞吐抵消。

## 7. 与上位测试计划的关系

上位计划继续保留场景背景、模型参数、测试 Profile、需求矩阵、详细命令模板和 Windows 执行建议；本附录提供 72 个 Case 的标准化设计和执行字段。后续新增或修改 Case 时，应先更新本附录，再同步上位计划、CSV/Excel 和可执行入口。
