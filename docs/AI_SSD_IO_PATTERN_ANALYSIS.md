# AI SSD 工作负载 I/O Pattern 分析报告

**版本**：1.0  
**日期**：2026-08-05  
**适用范围**：`docs/AI_SSD_WORKLOAD_TEST_MATRIX.csv` 中的 72 个 AI workload 测试 Case  
**测试对象**：消费级 AI PC 中的 1 TB、2 TB、4 TB TLC SSD，以及固定 pSLC namespace 方案  
**平台重点**：Windows 单机、GPU 显存与系统内存合计约 32–128 GB  

## 1. 文档目的与结论摘要

本报告不把“顺序读写带宽”作为唯一结论，而是从 AI 应用的实际数据路径出发，分析每项测试对 SSD 产生的读写方向、请求粒度、空间局部性、时间节奏、并发度、同步语义、缓存风险和后台放大。报告的目标是回答三个问题：

1. 每个 Case 实际会给 SSD 施加什么样的 I/O pattern。
2. 这个 pattern 为什么能够代表相应的 AI PC 场景。
3. 应该用哪些监控项和判定方法，才能把应用结果归因到 SSD，而不是归因到缓存、CPU、Docker 或 MPI。

当前已有实测证据表明：

- VectorDB trace 是“少量批量写入 + flush/load 阶段 I/O + 高频小读”的混合模式，而不是单纯随机读。
- KV Cache trace 是“数百 MiB 到数 GiB 的对象级 Tier-2 读写”；prefill 偏大块写，decode 偏热对象重复读，尾延迟比平均带宽更重要。
- Training 取决于数据格式：UNet3D/ResNet50/Flux 偏大文件或大 row-group 顺序读，RetinaNet 偏百万级小文件 metadata/IOPS，CosmoFlow 介于中小对象和 shuffle 读之间，DLRM 强调 Parquet row-group 与列裁剪。
- Checkpoint 是“多 rank 并发写出大分片 + 多 rank 分块恢复读”。已实跑的 Llama3-8B checkpoint 总量约 104.7 GiB，写入 421.8 s，读取 32.8 s；应用层读取吞吐不能直接视为冷盘 SSD 读取吞吐。
- 混合负载的关键不是把几类流量简单相加，而是观察前台小读尾延迟在后台大写、GC 或 checkpoint burst 下的变化。

本报告中“逻辑 I/O”表示应用发起的文件、对象或数据库操作；“物理 I/O”表示 Windows `PhysicalDisk`、ETW 或设备层实际观察到的 I/O。两者必须分开报告，不能用逻辑字节数替代设备字节数。

## 2. Pattern 分析方法

### 2.1 七个统一维度

| 维度 | 需要回答的问题 | 典型取值 |
|---|---|---|
| 方向 | 读、写还是读写混合？ | Read-heavy、Write-heavy、70R30W、阶段性切换 |
| 粒度 | 单个逻辑对象、文件、row-group 或设备请求多大？ | 4 KiB、16 KiB、128 KiB、1 MiB、32 MiB chunk、百 MiB、GiB |
| 空间局部性 | 地址是顺序、随机、分片顺序还是热 key 重复？ | Sequential、Random、Shard-sequential、Hotset |
| 时间节奏 | 连续流、突发、间歇、周期还是请求到达分布？ | Sustained、Burst、5/30/300 s interval、真实 arrival |
| 并发 | 有多少 reader/writer/rank/client 同时访问？ | QD1–64、1–32 reader、8 ranks、200 users |
| 同步 | 是否有 flush、fsync、barrier、close 或持久化确认？ | Buffered、Flush、fsync、close-only |
| 缓存与放大 | 应用读取是否真正命中 DUT？设备是否产生额外写入？ | Warm、Cold、Direct I/O、WAF、Compaction |

### 2.2 Pattern 名称约定

- **大块顺序读/写**：单个对象通常大于 1 MiB，访问地址连续或近似连续，重点是持续吞吐、队列和温度。
- **小块随机读**：4–16 KiB 级别、高并发或高频 key 访问，重点是 P99/P99.9/P99.99、IOPS 和队列，而不是平均带宽。
- **对象分片并发**：一个模型或数据库被拆成多个 shard，由多个 rank/client 并发访问；重点是最慢分片、skew 和共享队列。
- **元数据密集型 I/O**：大量小文件的 open/stat/close、目录遍历、索引文件更新和日志写入；重点是 metadata latency、IOPS、CPU 和文件数。
- **阶段化 I/O**：写入、flush、load、查询或 GC 依次发生；每一阶段的 pattern 不同，不应合并成一个平均值。
- **热对象复用**：同一 KV、向量 segment 或索引页被重复读取；必须分别测 warm、cold 和重启后首次访问。
- **干扰型混合 I/O**：前台低延迟读与后台大块写/GC 并发，重点是 foreground tail latency 和后台吞吐的耦合。

### 2.3 证据等级

| 等级 | 证据 | 能证明什么 | 不能证明什么 |
|---|---|---|---|
| L0 | Case 配置、模型和文件格式 | 预期的逻辑 pattern | 不能证明 SSD 实际被访问 |
| L1 | 应用日志、逻辑 trace、DLIO/VDB/KV 指标 | 操作顺序、逻辑字节、业务性能 | 不能区分页缓存和设备读 |
| L2 | Windows `PhysicalDisk`、进程 I/O、队列、温度 | DUT 命中、物理读写和排队 | 不能完整还原每个 NVMe 命令 |
| L3 | ETW/WPR、设备日志、hash、错误日志 | 时间相关性、异常、缓存和放大线索 | 仍需应用层语义解释，不能单独说明业务正确性 |

本报告将已录制 trace 和已实跑的 checkpoint 标记为 **实测**，其余 Case 标记为 **由配置推导的预期 pattern**。预期 pattern 在正式运行后必须用 L1+L2 证据校正。

## 3. 已获得的实测 Pattern

### 3.1 实测 trace 总览

| 场景 | 事件数 | 逻辑量 | 读/写比例 | 典型粒度 | Pattern 结论 |
|---|---:|---:|---:|---|---|
| VectorDB 1K insert/flush/load/search | 112 | 1.544 MiB | 90.2% / 9.8% | 592 B search、52 KiB insert、520 KiB flush/load | 阶段化混合，小读主导 |
| KV 8B prefill+decode | 5 | 1013.75 MiB | 80% / 20% | 每对象约 202.75 MiB | 大对象读主导、同 key 重复读 |
| KV 8B prefill-only | 1 | 2662.75 MiB | 0% / 100% | 单对象约 2.66 GiB | 单次大对象写 |
| KV 8B decode-only（过滤读） | 6 | 1536 MiB | 100% / 0% | 每次 256 MiB | 热对象重复读 |
| Checkpoint Llama3-8B write | 16 文件 | 104.704521 GiB | 写主导 | 8×1.87 GiB model + 8×11.22 GiB optimizer | 8 rank 大文件并发写 |
| Checkpoint Llama3-8B read | 16 文件 | 104.704521 GiB | 读主导 | 32 MiB chunk、8 rank、每 rank 4 worker | 多文件并发分块扫描 |
| Training UNet3D datagen smoke | 极小数据集 | 8 KiB 级 | 写主导 | 4 KiB 文件 | 仅证明 Windows 链路，不代表训练读负载 |

### 3.2 VectorDB 1K trace：阶段化混合模式（实测）

文件：`outputs/ai_io_trace_suite_20260804/raw/vdb_1k_insert_flush_load_search.csv`。

操作时序为：

1. 10 次 Insert，每次约 52 KiB，形成小批量、短间隔的写入突发。
2. 1 次 Flush，逻辑量约 520 KiB，相当于写入屏障和数据落盘阶段。
3. 1 次 Load，逻辑量约 520 KiB，代表索引/segment 从盘重新载入。
4. 100 次 Search，每次约 592 B，形成高频小读；这些字节是逻辑查询描述和结果级别，实际物理读可能是 4 KiB 或更大的索引页。

因此，VDB 1K trace 不是“90% 小随机读”的简单模型，而是“写入批次 → flush → load → 高频查询”的阶段化模式。该模式适合验证：

- flush 后的写入放大、队列峰值和短时延迟；
- load/restart 后首次查询的冷读延迟；
- Search 阶段小读 P99 是否受到后台 compaction、Docker VHDX 或 Milvus WAL 的影响；
- 逻辑查询字节与 Milvus 物理索引读之间的放大比例。

该 trace 不能代表百万级 DISKANN 的真实物理索引访问；正式 VDB Case 必须重新记录 1M/10M 数据集并同时采集 Milvus segment、WAL、索引和 compaction 活动。

### 3.3 KV Cache trace：对象级大读写（实测）

已录制文件位于 `outputs/ai_io_trace_suite_20260804/raw/`。

| Trace | 操作 | Pattern | 注意事项 |
|---|---|---|---|
| `kv_8b_prefill_only.csv` | 1 次 Tier-2 Write，2.66 GiB | 单对象连续大写；持续吞吐和写缓存容量是主变量 | 单事件时间戳不足以推导真实节奏 |
| `kv_8b_prefill_decode.csv` | 1 Write + 4 Read，每次约 202.75 MiB | 大写后同 key 重复读，读主导 | 适合 warm/cold 和 read tail 对照 |
| `kv_8b_decode_only.csv` | 10 次预置写 + 6 次读取 | 原始文件是混合模式，前置写与 decode 读不能直接合并分析 | 相邻日志有并发时间逆序 |
| `kv_8b_decode_reads_only.csv` | 6 次 Tier-2 Read，每次 256 MiB | 热 key 重复读取，读带宽与尾延迟主导 | 是 Tier-2 replay 的正确输入 |

KV 的关键不是单次对象的平均带宽，而是下列组合效应：

- 多用户并发时，多个中大对象的读写是否形成队列堆积；
- 同一热 key 在 warm cache 和 cold cache 下的 P95–P99.99 差异；
- prefill 的大写是否与 decode 的读请求共享 pSLC，导致前台读 tail latency 放大；
- Direct I/O 是否真的绕过 Windows 文件缓存；
- Tier-2 读写量是否非零，避免把 CPU/GPU 内存模拟误判成 SSD offload。

### 3.4 Checkpoint Llama3-8B：大分片并发写/读（实测）

本次使用 C: 盘目录 `C:\ai_ssd_checkpoint_smoke_20260804`，8 个 MS-MPI rank，1 次 write 和 1 次 read。应用层结果为：

| 阶段 | 逻辑组成 | 应用耗时 | 应用吞吐 |
|---|---|---:|---:|
| Write | 8 个 model shard（约 14.96 GiB）+ 8 个 optimizer shard（约 89.75 GiB） | 421.8183 s | 0.2482 GiB/s |
| Read | 同一组 16 个 shard，32 MiB chunk、每 rank 4 worker | 32.7921 s | 3.1930 GiB/s |

Write 的主要特征是 8 个 rank 并发生成大文件，model shard 完成后继续写 optimizer shard；optimizer 占总逻辑量约 85.7%，因此写入窗口主要由 optimizer shard 决定。该写入不是 4 KiB 随机写，而是用户态 producer-consumer 产生的连续大块流，设备层可能因为文件系统、缓存、分配和 TLC/pSLC 转换出现不同的内部写放大。

Read 的主要特征是多文件并发、固定 32 MiB chunk 的顺序扫描。应用层加载时间中 model 约 8.05 s、optimizer 约 24.74 s。它适合测恢复窗口、并发读带宽和 rank skew，但本次 read 紧接 write，且日志显示 `direct_io=False`，因此应用层的 104.7 GiB 不能直接等于物理设备读量。

PhysicalDisk C: 采样结果为：write 平均约 306.9 MB/s、峰值约 4.48 GB/s、队列峰值 199；read 平均约 834.1 MB/s、峰值约 3.32 GB/s、队列峰值 246。read 阶段只观测到约 38.4 GB 物理读，低于应用逻辑遍历量，说明存在缓存命中或 Windows 缓存策略影响。正式冷读 Case 必须在重启、卸载/重新挂载、可验证 cache purge 或 direct-I/O 条件下重新执行。

### 3.5 Training datagen smoke：低压力写入（实测）

UNet3D datagen smoke 只生成 2 个、每个 4 KiB 的极小文件，`mpiexec -n 1` 返回码为 0。它的物理 pattern 是短时低队列的目录创建、元数据更新和小文件写入，不能用来评价真实训练 epoch。正式训练必须将数据量提升到至少能显著超过系统可用内存，并记录实际磁盘读字节、AU、samples/s 和 epoch 间稳定性。

## 4. 基础与微基准 Case 的 Pattern

### 4.1 Base Case（AI-BASE-001–004）

| Case | I/O Pattern | 关键控制 | 主要观察 |
|---|---|---|---|
| AI-BASE-001 DUT inventory | 无业务 I/O；只有 Identify、健康信息、路径探测和少量结果写 | 数据、cache、结果目录必须分离；绑定序列号/固件/盘符 | 防止结果写到系统盘或错误 namespace |
| AI-BASE-002 path matrix | 同一 workload 分别产生 buffered warm、buffered cold、Direct I/O 三种模式 | 逻辑输入、seed、路径和 reader 并发固定 | 比较逻辑量与 PhysicalDisk 量，确认缓存污染 |
| AI-BASE-003 repeatability | 完全相同的顺序/随机流重复 3 次；monitor off/on 作为正交变量 | 固定温度起点、fill、后台进程和结果盘 | 吞吐 CV、P99、监控开销、采样缺口 |
| AI-BASE-004 fill sensitivity | 预填充阶段是大块顺序写；正式阶段叠加 GC、映射和可能的 SLC 回收 | 20/50/80/90% fill 使用相同正式 workload | 观察 sustained BW、P99、队列、温度随填充率的拐点 |

Base Case 本身不提供 AI 业务成绩，但它决定后续所有 Case 是否有效。尤其是 AI-BASE-002：没有 cold/warm/direct 分层，checkpoint、KV 和 VDB 的结果不能判断是否真正命中 SSD。

### 4.2 Micro/steady-state/cache/QoS Case

| Case | Pattern | 变化维度 | 预期 SSD 现象与判定重点 |
|---|---|---|---|
| AI-MICRO-001 顺序读 | 128 KiB/1 MiB 连续读，QD1–32，读吞吐主导 | block size、QD | 从 QD1 延迟到高 QD 饱和曲线；看 GiB/s、P99、CPU 和队列 |
| AI-MICRO-002 顺序写 | 128 KiB/1 MiB 长时间连续写，覆盖 pSLC 后进入 TLC | 5 min/full-span、QD | 初始 pSLC 高速段、SLC cliff、长期 sustained BW、温度和写放大 |
| AI-MICRO-003 随机读 | 4 KiB/16 KiB 随机读，QD1–64 | block、QD、地址范围 | IOPS 与 P99/P99.9；不要以 GiB/s 评价小读 |
| AI-MICRO-004 混合随机 | 70R30W、50R50W、30R70W，随机地址 | 读写比例、QD | 写流对小读尾延迟、队列和服务时间的影响 |
| AI-MICRO-005 steady state | 先全盘/全 namespace 预条件写，再重复正式负载 | 预条件长度、窗口 | 识别 pSLC、GC 和温度达到稳定后的性能，而不是初始 burst |
| AI-FILL-001 fill sensitivity | 预填充顺序写 + 每个 fill 点的正式混合/随机 workload | 10/50/80/90/95% | 空闲块减少、GC 增加、P99 和 sustained BW 退化；需要保留每个 fill 点的健康快照 |
| AI-CACHE-001 SLC cache | 连续写触发 pSLC，随后等待 0/1/5/15 min 再写 | burst 长度、idle | 计算 cliff bytes、恢复时间和 pSLC 回收速度；固定 pSLC namespace 应单独测试 |
| AI-QOS-001 foreground QoS | 前台 4/16 KiB 读与后台 1 MiB 写并发 | 后台写速率、读 QD | 重点是 read P99.9/P99.99，后台写 BW 只作为共存约束；记录温度和队列 |

## 5. Training Case Pattern（AI-TRN-001–016）

训练 Case 的核心是“存储供给速率是否足以填满 accelerator 的 compute gap”。训练应用通常不是每个样本一次磁盘读；data loader、预取、page cache、文件格式解码和 worker 并发会把逻辑样本转换成不同的设备 pattern。因此正式结果必须同时报告 AU、samples/s、应用逻辑量和 PhysicalDisk 读量。

| Case | 模型/配置 | 主要 I/O Pattern | 典型瓶颈与应监控项 |
|---|---|---|---|
| AI-TRN-001 | UNet3D/A100 | NPZ、约 139.8 MiB/文件，少量大文件；连续或近似顺序读，1/2/4 accelerator 提高并发 | 读带宽、预取深度、AU、samples/s、P99；A100 compute gap 较长，可能先受 compute 限制 |
| AI-TRN-002 | UNet3D/H100 | 与 UNet3D 相同的数据粒度，但 accelerator 消耗样本更快，reader 形成更高 QD | 队列、CPU 解压、read BW 和 AU；用于放大 SSD 供给不足，而非新的文件格式 |
| AI-TRN-003 | UNet3D/B200 | v3.0 大规模 NPZ 连续读，数据规模可达约 983 GiB；长时间 sustained read | 长时读带宽、温度、队列、AU 退化；完整数据量对消费级 PC 不现实，应使用缩小比例但保持文件大小/并发比例 |
| AI-TRN-004 | RetinaNet/B200 | 约 315 KiB JPEG、百万级小文件；大量 open/stat/read/close，地址随机且 metadata 密集 | 文件系统 metadata latency、IOPS、CPU、目录缓存和小读 P99；GiB/s 不是主要指标 |
| AI-TRN-005 | RetinaNet/MI355 | 与 RetinaNet/B200 相同的细粒度 JPEG I/O，compute/batch 节奏不同 | 比较 reader rate、files/s、P99 和 CPU；区分 accelerator 差异与 SSD 差异 |
| AI-TRN-006 | CosmoFlow/A100 | 约 2.7 MiB TFRecord，中小对象、shuffle 和 batch 内多文件访问 | 中等粒度随机/半顺序读、IOPS、queue；full 1.38 TiB 不适合消费级 PC，需缩小文件数量而保持对象分布 |
| AI-TRN-007 | CosmoFlow/H100 | 与 CosmoFlow 相同对象粒度，但请求到达更密集，读突发更明显 | burst read、P99、队列和 AU；关注短时间 queue spike 而非仅平均 BW |
| AI-TRN-008 | ResNet50/A100 | 约 136.8 MiB TFRecord，文件内部包含多个 sample；大块文件读加应用内偏移访问 | 文件级顺序读与内部 sample 访问的折中；监控 read BW、samples/s、CPU 解码 |
| AI-TRN-009 | ResNet50/H100 | 同一 TFRecord 形态，accelerator/worker 增加后形成更密集预取 | sustained read、queue 和 AU；确认 H100 不是由 CPU 解码或线程不足限制 |
| AI-TRN-010 | DLRM/B200 | Parquet 约 1.09 GiB/文件，按 row-group、列裁剪和 metadata 访问；非全文件顺序读 | row-group/s、read amplification、CPU、随机程度；prefetch 0/2/4 改变读前移和队列 |
| AI-TRN-011 | DLRM/MI355 | 同样的列式 I/O，但以 threads 1/4/8/16 扩大并行 row-group 读取 | 并行读带宽、CPU、队列和 memory pressure；高线程可能把 SSD 变成队列瓶颈 |
| AI-TRN-012 | Flux/B200 | 约 594.6 MiB Parquet 大对象，较低请求频率、单次 burst 较大 | 大对象 burst、prefetch 和 temperature；full 2.44 TiB 仅用于扩展节点，PC 使用等比例 fixture |
| AI-TRN-013 | Flux/MI355 | 大对象 Parquet + batch 72，compute gap 较长，读取以间歇 burst 出现 | burst latency、空闲恢复、AU；不要把低平均 BW 误判为低负载，需看每个 step 的读等待 |
| AI-TRN-014 | Closed model scaling | 同一 UNet/Retina 数据形态，accelerator 从 1 增至饱和；读并发逐级增加 | 找到 AU 合格点和 speedup knee；把 reader/CPU/SSD 饱和区分开 |
| AI-TRN-015 | Reader scaling | 固定训练配置，仅 sweep read_threads 1/2/4/8/16/32 | 从单线程顺序读到高并发队列；观察吞吐、CPU、queue、P99 和 AU，识别 SSD 饱和拐点 |
| AI-TRN-016 | Cache/path matrix | 同一训练 workload 做 warm、cold、`--o-direct`；逻辑读量相同 | PhysicalDisk read bytes、AU 和 epoch time 的差异；若 cold/direct 仍无设备读，Case 应判 Invalid |

训练家族可归纳为四种 pattern：

1. **大文件流式读**：UNet3D、ResNet50、Flux。
2. **大量小文件/metadata**：RetinaNet。
3. **中小对象 shuffle**：CosmoFlow。
4. **列式选择性读**：DLRM。

这四类必须至少各保留一个代表性 Case；只跑 UNet3D 不能代表 AI PC 的训练 I/O。

## 6. Checkpoint Case Pattern（AI-CKP-001–009）

| Case | Pattern | 重点分析 | 关键判定 |
|---|---|---|---|
| AI-CKP-001 | Llama3-8B、8 ranks、约 105 GB；16 个 shard 并发写/读 | 已实跑基线；model 与 optimizer 分片大小不对称 | 10 次 save/load 时最慢 rank、fsync、hash、温度和后续退化 |
| AI-CKP-002 | 70B subset、8 ranks、约 114 GB；模拟大模型每 rank 分片 | 与 CKP-001 相同的大块并发 pattern，但 shard 内容和读写比不同 | 最慢 rank、最小吞吐、空间余量和写后恢复 |
| AI-CKP-003 | 70B full、64 ranks、约 912 GB；更多 writer/reader、跨节点共享路径 | 并发度提升，rank skew 和共享文件系统队列成为主变量 | global duration、rank skew、设备队列和网络/共享层区分 |
| AI-CKP-004 | 405B subset、8 ranks、约 94 GB；node-local SSD | 大块写/读但空间接近消费级 PC 能力边界 | cold bytes、save/load、空间不足和 GC |
| AI-CKP-005 | 405B full、512 ranks、TB 级 | 大规模对象分片、共享队列、尾部 rank | global scale、最慢 rank、共享存储而非单盘性能 |
| AI-CKP-006 | 1T subset、8 ranks、约 161 GB | 单节点最大分片，长 burst 写入后可能触发 GC | pSLC exhaustion、GC、恢复时间和温度 |
| AI-CKP-007 | 1T full、1024 ranks、约 18 TB | 极大规模并发 checkpoint | 需要扩展节点，不应在消费级 AI PC 上伪装为本地结果 |
| AI-CKP-008 | write-only→cache purge/reboot→read-only | 专门区分 warm read 与真实 SSD cold read | PhysicalDisk read bytes 应接近逻辑量；否则只能标 warm |
| AI-CKP-009 | 5/30/300 s interval，1/2/10 cycles | 周期性大写、间隔期 GC、后续恢复读 | 第 n 次 checkpoint 的 duration、P99、温度、队列和 sustained degradation |

Checkpoint 的存储语义比一般 training 更强：正式测试必须启用可验证的 flush/fsync 或等价持久化点，记录每个 rank 的文件大小、close time、hash 和错误日志。若只统计应用“生成文件完成”的时间而没有确认数据持久化，就不能称为 durability 测试。

## 7. KV Cache Case Pattern（AI-KV-001–022）

KV Case 的对象大小由 `KV bytes/token × context length × TP/rank` 决定。对象通常是连续大块或中大块，但用户级请求是高并发、低延迟、可能 burst 的。因此 KV 的主要评价维度是“逻辑对象大小 + 请求到达节奏 + hot/cold 复用 + tier 溢出 + 尾延迟”。

| Case | 配置/变量 | I/O Pattern 与分析重点 |
|---|---|---|
| AI-KV-001 | MLPerf option 1，8B，200 users，GPU/CPU tier=0 | NVMe-only，高并发 Tier-2 分配和回收；中大对象读写叠加，优先看 P95–P99.99、tokens/s、tier bytes |
| AI-KV-002 | option 2，CPU tier=4 GB，100 users | CPU cache 满后向 SSD spill，存在明显阶段边界；记录 spill 时刻、eviction、读回和内存压力 |
| AI-KV-003 | option 3，70B，70 users，最大并发 alloc=4 | 单对象更大、并发受控；看单次对象服务时间、带宽、RAM 峰值和 tail |
| AI-KV-004 | tiny-1b，users 10→500 | 小 KV 对象、高请求数；更接近小块/高 IOPS，而非顺序带宽；监控系统调用、IOPS、CPU overhead |
| AI-KV-005 | mistral-7b，128 KiB/token | 中等对象，context/users sweep；对象大小随 context 线性增长，关注 P99 和 read/write BW |
| AI-KV-006 | llama2-7b，512 KiB/token | 本矩阵对象大小上界；少量 allocation 就可能形成大块 burst 和空间压力；增加 OOM、fill、pSLC cliff 检测 |
| AI-KV-007 | llama3.1-8b，users 25/50/100/200 | 独立负载曲线；逐级提升并发，找 SSD QoS 失守点和最大合格 users |
| AI-KV-008 | llama3.1-70b，users 10/35/70/140 | 大模型大对象、较低并发；容易表现为大块读写和高单请求 tail，区分容量瓶颈与带宽瓶颈 |
| AI-KV-009 | DeepSeek-V3，4K/8K/25K | MLA 压缩 KV，小对象但可能高请求率；对比传统 KV 的 bytes/request、IOPS 和 CPU 管理开销 |
| AI-KV-010 | Qwen3-32B，256 KiB/token | 中大对象与多用户混合；看 context 变化导致的对象 CDF、队列和 pSLC 占用 |
| AI-KV-011 | GPT-OSS-20B，MoE，48 KiB/token | 大模型但较小 KV；请求数上升时更像小对象 IOPS workload，注意 CPU/SSD 管理开销 |
| AI-KV-012 | GPT-OSS-120B，72 KiB/token | 模型规模大但 KV 对象相对小；对比“模型大”与“SSD I/O 大”的区别，避免只按参数量选 SSD |
| AI-KV-013 | GPU/CPU tier=0/4/16/32 GiB | tier 容量改变 spill/evict 比例；观察 occupancy、spill burst、读回和尾延迟拐点 |
| AI-KV-014 | TP 1/2/4/8 | TP 增大后单 rank 对象变小、并发 rank 增多；比较 per-rank bytes、aggregate BW、队列和 namespace 争用 |
| AI-KV-015 | Prefill-only | 写密集、单次大对象或多个用户连续写；测 write BW、fsync、pSLC 容量和 P99 |
| AI-KV-016 | Decode-only | 预置 cache 后只读；热对象重复读，重点是 P99.99、cold/warm 和 Direct I/O |
| AI-KV-017 | chatbot/coding/document persona | 短、长 context 混合，对象大小呈长尾分布；输出 object-size CDF、arrival burst 和 tail latency |
| AI-KV-018 | generation none/fast/realistic | 改变请求间 think-time；`none` 接近压力上界，`realistic` 体现真实间歇与 burst，报告 active/wall BW |
| AI-KV-019 | RAG/prefix/multi-turn | 命中 prefix/cache 时减少写入和读回；miss 时增加文档和 KV 访问，记录 hit rate、bytes saved、P99 |
| AI-KV-020 | users/request-rate +20/25% | 负载阶梯；找 queue、P99、drop 或 recovery 的 knee，不要把超过 SLA 的吞吐称为合格成绩 |
| AI-KV-021 | Tier-2 trace replay，1×/2×/4× | 过滤后的逻辑读写按节奏重放；适合隔离 SSD，必须记录原始 timestamp、倍率、direct/buffered 和对齐策略 |
| AI-KV-022 | BurstGPT/ShareGPT | 使用真实 arrival/context 分布，可能有突发长尾；关注 burst tail、队列、drop、pSLC 余量和温度 |

KV 的 trace replay 能保留操作顺序、对象大小、读写方向和倍率，但不能自动保留真实内核排队、文件系统元数据、KV 序列化和应用计算间隔。因此 replay 结果应写成“SSD 逻辑负载 replay”，不能写成“完整模型推理结果”。

## 8. VectorDB Case Pattern（AI-VDB-001–016）

| Case | 配置 | I/O Pattern 与分析重点 |
|---|---|---|
| AI-VDB-001 | 1K×128 HNSW | 已完成 Windows smoke；insert/flush/load/search 阶段化，主要验证命令、Recall、trace 和监控链路 |
| AI-VDB-002 | 1M×1536 HNSW | 图索引主要内存访问，SSD 重点在建库、segment、load 和后台日志；search 物理读可能低于逻辑查询量 |
| AI-VDB-003 | 1M×1536 DISKANN | 磁盘 ANN，查询触发索引邻接页的多处读取；关注物理 read amplification、QPS、P99 和冷启动 |
| AI-VDB-004 | 1M×512 DISKANN | 与 1536 维对照；单向量和索引页更小，比较 bytes/query、cache residency 和 QPS，而不是只比较总容量 |
| AI-VDB-005 | 1M×512 AISAQ | 压缩索引，构建写和查询读可能减少，但解压/重排 CPU 增加；同时测 Recall、容量、CPU 和设备读 |
| AI-VDB-006 | 10M×1536 HNSW，10 shards | 大数据集、多 segment/索引文件；load 和后台 compaction 形成大块读写，search 叠加热页访问 |
| AI-VDB-007 | 10M×1536 DISKANN，10 shards | 大磁盘 ANN，多 shard 并发随机读；重点是物理 I/O、温度、队列、segment locality 和 QPS |
| AI-VDB-008 | index family sweep | 同一数据、不同索引；隔离“索引算法产生的 I/O pattern”与 SSD 差异，比较相同 Recall 下容量、QPS、P99 |
| AI-VDB-009 | ef/search-list 32→512 | search effort 提升会增加候选页读取和 CPU；画 Recall–QPS–physical read 三维关系 |
| AI-VDB-010 | query process 1/2/4/8/16 | 从低并发到查询队列饱和；记录 aggregate QPS、P99、queue、CPU 和 Docker VHDX I/O |
| AI-VDB-011 | batch 1/8/32/64 | 批查询可提高顺序性和吞吐，但单 query P99 可能被批内最慢请求拖长；同时报告 batch latency 和 per-query latency |
| AI-VDB-012 | ingest batch 1K/10K，compact on/off | 大批量 insert、flush、index build 和 compaction；写入可能从顺序变为多文件并发/后台回收 |
| AI-VDB-013 | topK、metric、dim | result bytes、候选数量和索引访问量随 topK/search metric 改变；固定 Recall 后比较 physical read/query |
| AI-VDB-014 | restart/load、warm/search-only | restart/load 是阶段性大读，steady search 是热索引页小读；必须分开报告 first-query P99 与 steady P99 |
| AI-VDB-015 | logical trace replay，1×/2×/4× | 复现已录制的 insert/flush/load/search 逻辑节奏；适合 SSD 端对比，但不含 Milvus 真实内部放大 |
| AI-VDB-016 | ingest+search coexist | 后台 segment/索引写与前台 ANN 读并发；判断前台 Recall/P99 是否被写入、flush、compaction 干扰 |

VDB 的三类主要 pattern 是：建库期大块/多文件写、load/restart 阶段大块读、在线查询期热索引页小读。Milvus 容器使用 Docker Desktop 时，必须确认数据库 volume 实际落在 DUT namespace；否则 PhysicalDisk 采样可能只看到 Docker VHDX 或系统盘。

## 9. Mixed/Soak Case Pattern（AI-MIX-001–005）

| Case | 前台/后台 | 组合 Pattern | 主要判定 |
|---|---|---|---|
| AI-MIX-001 | Training + checkpoint save | 前台持续大块读，后台周期性多 rank 大块写；读写方向相反但共享队列和 pSLC/GC | Training AU、checkpoint BW、两者 P99；前台不应因后台 burst 长时间掉出门槛 |
| AI-MIX-002 | KV decode + checkpoint save | 前台中大块热读/低延迟请求，后台大块写和 flush；最容易产生 KV P99.9/P99.99 尾部 | KV SLA、checkpoint 最小吞吐、队列、温度、pSLC 剩余 |
| AI-MIX-003 | VectorDB search + ingest/index | 前台小读与后台 ingest/flush/compaction 写并发；数据库内部还有日志和 segment 访问 | Recall 不降、foreground P99≤1.5×solo、ingest rate 可解释 |
| AI-MIX-004 | KV interactive + VectorDB search | 两类前台读共享 SSD，具有不同对象大小和 arrival 分布；小对象与大对象混合 | 分别报告两类 P99/P99.9，不能只给 aggregate IOPS |
| AI-MIX-005 | 四类 workload + fill/GC background | 长时间周期流量、温度变化、pSLC 回收、后台 GC 和偶发 burst | 8 h 稳定性、错误、温度、队列、P99 漂移和持续退化；必要时延长至 24 h |

Mixed Case 必须先建立每个前台 workload 的 solo golden，再以相同数据目录和 namespace 运行混合流量。默认判定“前台 P99≤1.5×solo、后台吞吐≥0.8×solo”只是起始门槛，正式产品应按实际交互 SLA 细化。

## 10. Trace、命令实跑与物理监控的对应关系

| Case 类型 | 适合的执行方式 | 可保留的 Pattern | 不可自动保留的内容 |
|---|---|---|---|
| AI-KV-021 | KV 逻辑 trace replay | 方向、对象大小、key、时间顺序、倍率 | 模型计算、序列化、真实 tier 调度和内核队列 |
| AI-VDB-015 | VDB 逻辑 trace replay | insert/search/flush/load 操作序列和逻辑大小 | Milvus WAL、索引页、compaction 和 protobuf/文件放大 |
| AI-BASE-002/003 | 同一命令多路径/多次实跑 | cache、direct、重复性和监控变量 | trace 不能替代真实应用内部并发 |
| AI-TRN 全部 | MLPerf Storage 命令实跑；可额外 ETW 录制 | data loader、预取、文件格式和 accelerator think-time | 人工文件 replay 不能代表 AU |
| AI-CKP 全部 | checkpointing 命令实跑；ETW/PhysicalDisk 伴随采集 | rank、shard、chunk、fsync、恢复流程 | 人工 `np.savez` 不能代表 optimizer/model checkpoint 语义 |
| AI-MIX 全部 | 多进程/多命令编排实跑 | 前台/后台共存和队列干扰 | 单独 replay 不能证明业务 SLA |

当前已完成的 replay/trace 仅覆盖 VDB 1×和 KV Tier-2 逻辑样本；Training 与 Checkpoint 已有 Windows 实跑和物理采集，但仍需扩大到正式数据量、冷读和多轮运行。

## 11. 监控项、检测器与 Pattern 归因

### 11.1 所有 Case 的通用采集项

| 层次 | 采集项 | 建议频率 | 作用 |
|---|---|---:|---|
| 应用层 | AU、samples/s、tokens/s、QPS、Recall、P95–P99.99、rank time | 应用原生/每 step | 判断业务是否达标 |
| 逻辑 I/O | 读写对象数、逻辑字节、对象大小 CDF、key reuse、flush/fsync | 每操作或每阶段 | 定义 workload pattern |
| Windows/设备 | Read/Write Bytes/sec、Reads/Writes/sec、Avg Disk sec、queue、% Disk Time | 1 s | 确认 DUT 命中和物理负载 |
| 进程 | CPU、Private Working Set、I/O Read/Write Bytes | 1 s | 识别解码、Docker、Milvus 或应用瓶颈 |
| 内存 | Available MBytes、Pages/sec、Committed Bytes、page fault | 1 s | 判断文件缓存和 paging 污染 |
| SSD 健康 | 温度、Percentage Used、Media/Data Integrity Error、错误计数 | 开始/结束；温度 5 s | 判断热降速、介质错误和健康变化 |
| 证据 | manifest、stdout/stderr、timeseries、hash、ETW、CSV | 每 run | 支持复现和 Invalid 判定 |

### 11.2 Pattern 对应的检测器

| 检测器 | 触发条件 | 结论 |
|---|---|---|
| DET-PATH | cache/data/checkpoint/Milvus volume 不在声明的 DUT namespace | Invalid，不得出 SSD 成绩 |
| DET-CACHE | 宣称 cold/direct，但 PhysicalDisk 读量显著低于逻辑遍历量 | 标记 warm 或 Invalid，不能冒充冷盘结果 |
| DET-QUEUE | 高队列只出现在结果盘、Docker VHDX 或非 DUT 盘 | 重新归因，不能把 host I/O 当 SSD I/O |
| DET-AU | Training AU 低于 YAML 门槛 | Fail；同时检查 CPU、reader 和 SSD queue |
| DET-CKPT-CNT | rank、分片、轮次或字节数不完整 | Invalid/Fail，不统计平均吞吐 |
| DET-CKPT-COLD | read 逻辑量大但设备读量很低 | warm-only；重新执行 cold read |
| DET-KV-TIER | `storage_entries=0` 或 Tier-2 bytes=0 | Invalid，不是 SSD offload 测试 |
| DET-KV-QOS | P95/P99/P99.9/P99.99 超过选择的 profile | Fail；保留压力点与恢复时间 |
| DET-VDB-RECALL | Recall 低于 Case 门槛 | Fail；QPS 不进入横向比较 |
| DET-VDB-TRACE | 时间倒退、对象缺失或 trace 未完整结束 | Invalid；并发日志需按 sequence/phase 重建顺序 |
| DET-HOST | CPU 持续>85%、paging、结果盘或 Docker 成为瓶颈 | host-limited 或 Invalid |
| DET-THERM | 温度上升与吞吐下降相关，或触发 thermal throttle | 标记 thermal-limited，不能与冷态结果混合 |
| DET-ERROR | 应用 I/O 错误、hash mismatch、SSD 错误计数新增 | Fail，停止横向比较 |

## 12. 固定 pSLC namespace 的专项解读

固定 pSLC 区域并格式化为独立 Windows 盘符后，测试不能只重复“同一 workload 换路径”。应针对 pSLC 容量固定这一事实增加以下 pattern：

1. **容量边界**：用 AI-MICRO-002、AI-CACHE-001、AI-KV-015 和 AI-CKP-009 逐步写入超过固定 pSLC 容量，记录 cliff bytes、cliff 前后吞吐、队列、温度和恢复时间。
2. **pSLC 单独读写**：Training 大文件读、Checkpoint 写、KV decode 读分别在 pSLC 和 TLC namespace 单独运行，避免混合路径掩盖介质差异。
3. **pSLC 写 + TLC 读**：模拟 KV prefill 或 checkpoint 写入 pSLC、训练数据或 VDB 索引驻留 TLC；观察跨 namespace 队列和温度耦合。
4. **TLC 后台写 + pSLC 前台读**：用 AI-QOS-001、AI-MIX-002 验证固定 pSLC 是否真正提供 QoS 隔离，而不是只在空闲时提供峰值。
5. **pSLC 满后恢复**：写满 pSLC 后等待 0/1/5/15 分钟，再分别读取和写入；测回收、折返 TLC、后续 burst 的恢复时间。
6. **容量与数据保留**：1 TB、2 TB、4 TB 产品即使使用相同固定 pSLC 大小，也要记录 pSLC 占整盘比例、TLC 剩余空间和 80/90% fill 状态。不能只比较绝对 GiB/s。

建议的最小 namespace 矩阵如下：

| 组合 | 前台 | 后台 | 适用 Case | 目的 |
|---|---|---|---|---|
| pSLC solo | KV prefill / checkpoint write | 无 | KV-015、CKP-001/009 | 测固定 pSLC 的容量和持续写 |
| pSLC read | KV decode / VDB search | 无 | KV-016、VDB-014 | 测热数据低延迟读 |
| TLC solo | Training / VDB dataset | 无 | TRN-001/004/010、VDB-003 | 测 TLC 大容量工作集 |
| pSLC read + TLC write | KV decode | sustained TLC write/GC | QOS-001、MIX-002 | 测 QoS 隔离 |
| TLC read + pSLC write | Training/VDB | checkpoint/prefill | MIX-001、MIX-003 | 测写突发对持续读的干扰 |
| pSLC/TLC mixed | KV + VDB + training | fill/GC | MIX-004/005 | 测真实 AI PC 共存 |

## 13. 结果表达规范

每个 Case 的结果至少应包含以下三组数字：

1. **应用结果**：业务指标，例如 AU、QPS、Recall、tokens/s、checkpoint duration、KV P99.99。
2. **逻辑 I/O 结果**：读写对象数、逻辑字节、对象大小 P50/P95/P99、请求间隔、并发和 phase。
3. **物理 I/O 结果**：DUT 实际读写字节、平均/峰值 BW、IOPS、P99/队列、温度、错误计数。

结果应同时标记：`cold`、`warm`、`buffered`、`direct`、`pSLC`、`TLC`、`mixed`、`thermal-limited` 或 `host-limited`。如果逻辑量和物理量差异无法解释，结果应标记 `Invalid` 或 `warm-only`，不得直接用于 SSD 横向排名。

## 14. 当前证据与下一步

当前可复核证据：

- 逻辑 trace：`outputs/ai_io_trace_suite_20260804/raw/`
- 逻辑分析：`outputs/ai_io_trace_suite_20260804/analysis/trace_report.md`
- Checkpoint 物理分析：`outputs/ai_io_trace_suite_20260804/analysis/checkpoint_write_C.md`、`checkpoint_read_C.md`
- Windows 采集报告：`outputs/ai_io_trace_suite_20260804/TRACE_SUITE_REPORT.md`
- 采集脚本：`tools/record_windows_io.ps1`

下一阶段优先级：

1. 在同一个 pSLC/TLC namespace 上完成 AI-BASE-001/002，确认路径与 cold/direct 方法。
2. 重跑 AI-CKP-001 的 cold read 和至少 3 次重复，避免把当前 warm-influenced read 当成 SSD 读成绩。
3. 用缩小但比例保持一致的数据集完成 Training 四种代表 pattern：UNet3D、RetinaNet、CosmoFlow、DLRM。
4. 将 KV-016 和 VDB-015 的 trace 分别回放到 pSLC、TLC，并采集 PhysicalDisk/ETW。
5. 在 solo golden 建立后执行 AI-MIX-001/002，优先验证 checkpoint 大写对 KV decode 和 training read 的干扰。

