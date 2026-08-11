# AI SSD 剩余模块首轮精选 Case

本说明对应 `AI_SSD_TEST_PLAN.xlsx` 中除 Training 外的 56 个 Case，包含 BASE、Checkpoint、KV Cache、VectorDB 和 Mixed。绿色行是建议首轮执行的 Case；完整步骤、命令、时长和通过标准见 `AI_SSD_REMAINING_CASE_PLAN.xlsx`。

## BASE

| Case | 理由 |
| --- | --- |
| AI-BASE-001 | 先完成盘符、卷映射、容量和结果盘隔离，避免后续所有性能结果失去可追溯性。 |
| AI-BASE-002 | 用 Buffered、cold、Direct 三种路径建立缓存控制基线，避免把页缓存命中当作 SSD 性能。 |
| AI-BASE-003 | 验证重复性并确认监控本身不会显著改变结果。 |

AI-BASE-004 属于授权目录下的填充率退化测试，建议在基础结果稳定后执行。

## Checkpoint

| Case | 理由 |
| --- | --- |
| AI-CKP-001 | 最小可控的 8B 基线，用于先验证分片、fsync、hash 和保存/读取流程。 |
| AI-CKP-002 | 增加到 70B subset，验证单盘更大分片下的吞吐、rank 完整性和空间边界。 |
| AI-CKP-008 | 直接验证 cold/warm 恢复读，确认读流量确实来自 SSD。 |
| AI-CKP-009 | 用连续保存和间隔变化观察后台 GC 对后续 checkpoint 的影响。 |

AI-CKP-003、005、007 需要多节点或 TB 级容量，放到扩展阶段。

## KV Cache

| Case | 理由 |
| --- | --- |
| AI-KV-001 | 作为 NVMe-only 高并发基线，确认 tier entries 和实际 NVMe I/O。 |
| AI-KV-002 | 覆盖 CPU spill 边界，验证 spill 不会吸收全部 I/O 或触发 OOM。 |
| AI-KV-007 | 通过 8B 用户阶梯得到最大合格用户数，结果容易解释和复现。 |
| AI-KV-015 | 覆盖写密集 Prefill，补充 decode 之外的写入与 fsync 压力。 |
| AI-KV-016 | 覆盖读密集 Decode，验证预置 KV 的实际读取带宽和 P99.99。 |
| AI-KV-020 | 通过逐级加压定位最大合格负载、队列拐点和恢复时间。 |

其余模型、TP、context persona 和 trace replay Case 作为首轮结果后的定向扩展。

## VectorDB

| Case | 理由 |
| --- | --- |
| AI-VDB-001 | 低成本 Windows smoke，先确认索引、查询、Recall 和 trace 产物链路。 |
| AI-VDB-002 | 建立 1M HNSW 的内存图索引基线，提供 Recall-QPS-P99 参照。 |
| AI-VDB-003 | 加入磁盘型 DISKANN，验证真实物理读和索引搜索的差异。 |
| AI-VDB-009 | 扫描 ef/search-list，建立精度与性能的可解释曲线。 |
| AI-VDB-014 | 区分 cold、warm、first query 和 steady-state，避免缓存影响混入结论。 |
| AI-VDB-016 | 验证后台 ingest/index 对前台搜索 Recall 和 P99 的实际干扰。 |

10M 规模、全索引家族和 trace replay 建议在 1M 基线通过后执行。

## Mixed

| Case | 理由 |
| --- | --- |
| AI-MIX-001 | 训练持续读与 checkpoint 突发写是最直接的同盘干扰场景。 |
| AI-MIX-002 | 验证 KV decode 对大写入的尾延迟抗性，直接关联 AI PC 交互体验。 |
| AI-MIX-003 | 验证 RAG 查询对后台向量写入和建索引的容忍度。 |
| AI-MIX-004 | 验证两类前台随机读同时运行时是否能同时满足 SLA。 |

AI-MIX-005 为 8 小时长时 soak，建议所有前置 Case 通过后再执行。

## 建议执行顺序

1. BASE-001 → BASE-002 → BASE-003：先锁定设备、路径和重复性。
2. CKP-001 → CKP-002 → CKP-008 → CKP-009：建立持久化、恢复和 GC 基线。
3. KV-001 → KV-002 → KV-015 → KV-016 → KV-007 → KV-020：覆盖 tier、spill、读写方向、用户扩展和饱和。
4. VDB-001 → VDB-002 → VDB-003 → VDB-009 → VDB-014 → VDB-016：覆盖 smoke、内存图、磁盘 ANN、搜索参数、缓存和混合写入。
5. MIX-001 → MIX-002 → MIX-003 → MIX-004 → MIX-005：从短时干扰逐步进入长时稳定性。

