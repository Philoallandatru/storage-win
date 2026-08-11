# 固定容量 pSLC Namespace 的 AI SSD 测试需求与 Case 设计补充

**文档编号**：AI-PC-SSD-VV-PSLC-001  
**版本**：1.0  
**日期**：2026-08-04  
**适用范围**：1 TB、2 TB、4 TB 消费级 TLC SSD；固件预留固定容量的 pSLC 区域，并将 pSLC 与 TLC 暴露为不同 namespace，可在 Windows 中格式化为不同卷/盘符。  
**上位文档**：[AI_PC_CONSUMER_SSD_TEST_REQUIREMENTS_AND_CASE_DESIGN.md](AI_PC_CONSUMER_SSD_TEST_REQUIREMENTS_AND_CASE_DESIGN.md)  
**配套矩阵**：[AI_PC_CONSUMER_SSD_TEST_REQUIREMENTS_AND_CASE_MATRIX.xlsx](../outputs/ai_pc_consumer_ssd_standards_based_20260804/AI_PC_CONSUMER_SSD_TEST_REQUIREMENTS_AND_CASE_MATRIX.xlsx)

## 1. 设计结论

固定 pSLC 与可调 pSLC 的测试重点不同：

1. **不再把 pSLC 容量作为可调实验变量**；每块 SSD 使用固件提供的实际 pSLC namespace 容量。
2. 重点验证固定容量是否足以承载 AI 热数据，以及达到容量边界后是否出现受控的 `ENOSPC`、性能退化或数据错误。
3. 盘符/namespace 只能证明逻辑隔离，不能自动证明 pSLC 与 TLC 在 NAND、FTL、GC、DRAM、通道、队列和温度资源上物理隔离。
4. 所有 pSLC 结论必须同时给出绝对容量 `P`、TLC 容量 `T`、整盘容量 `C` 和占比 `P/C`，不能只比较盘符名称。
5. 如果产品没有明确的 pSLC→TLC 溢出/回退机制，超过 `P` 的工作集必须验证为容量边界，不得假设它会自动 spill 到 TLC。

## 2. 固定 pSLC 的测试模型

对每块 DUT 定义：

```text
C = SSD 实际可用总容量
P = pSLC namespace 实际可用容量（固定值）
T = TLC namespace 实际可用容量
R = P / C                 # pSLC 占整盘比例
Fp = pSLC 当前填充率
Ft = TLC 当前填充率
```

### 2.1 固定记录项

每次 run 的 `manifest.json` 必须包含：

- SSD 型号、固件、序列号、PCIe 链路
- namespace ID、namespace size、LBA format、sector size
- pSLC namespace 盘符、TLC namespace 盘符、卷 GUID
- `C`、`P`、`T`、`R`
- 文件系统、簇大小、TRIM/Deallocate 状态
- pSLC/TLC 当前填充率 `Fp`、`Ft`
- 工作集大小相对于 `P` 的比例
- 当前 workload、随机种子、QD/线程/OIO

### 2.2 固定 pSLC 的工作集等级

| 工作集等级 | 定义 | 目的 |
|---|---:|---|
| W1 | `0.25P` | 小于固定 pSLC 容量，验证纯 pSLC 热数据路径 |
| W2 | `0.50P` | 验证中等填充和重复覆盖 |
| W3 | `0.90P` | 接近边界，观察尾延迟和 GC |
| W4 | `1.00P` | 精确填满固定 pSLC namespace |
| W5 | `P + 1 GiB` 或更大 | 仅用于验证 ENOSPC 或已定义的 spill/fallback 行为 |

W5 只有在产品规格明确支持回退时才可解释为 spill 测试；否则验收目标是“超容量写入被安全拒绝且已有数据不损坏”。

## 3. 补充测试需求

| 需求 ID | 测试需求 | 设计理由 | 验证方法 | 量化验收标准 |
|---|---|---|---|---|
| REQ-PSLC-001 | 系统 shall 能识别并稳定挂载固定 pSLC 与 TLC namespace。 | 盘符可用是所有后续测试的前提。 | 检查+测试 | namespace、容量、卷 GUID、盘符和文件系统字段完整；重启后保持一致。 |
| REQ-PSLC-002 | 报告 shall 同时记录 `C/P/T/R`，不得只报告盘符或逻辑卷大小。 | 固定 pSLC 的价值取决于绝对容量和占比。 | 检查 | `C/P/T/R` 全部存在；同一 DUT 重跑值一致。 |
| REQ-PSLC-003 | pSLC namespace 在 `Fp=0/25/50/75/90/100%` 下 shall 产生可比较的性能和容量结果。 | 固定容量的关键风险是填充后退化。 | 测试 | 每个填充点至少 3 次有效采样；报告 P50/P95/P99/P99.9。 |
| REQ-PSLC-004 | 当工作集超过 `P` 时，系统 shall 呈现产品定义的 ENOSPC、spill 或 fallback 行为。 | 不能把固定 namespace 的边界误判为动态缓存。 | 测试+检查 | 无 silent data loss；无未预期 I/O error；行为与规格一致。 |
| REQ-PSLC-005 | pSLC 与 TLC 并发访问 shall 分别报告单独基线和混合负载尾延迟。 | 两个 namespace 仍可能共享 FTL、队列、通道、DRAM 和温度资源。 | 测试+分析 | 输出 `mixed P99 / solo P99`；建议初始目标不超过 1.2 倍。 |
| REQ-PSLC-006 | 固定 pSLC namespace shall 在连续覆盖写和删除/回收后保持可预测的延迟和数据完整性。 | pSLC 的真实价值来自可重复使用，而不是一次性 burst。 | 测试 | 无数据错误；退化点、恢复时间和温度均被记录。 |
| REQ-PSLC-007 | AI workload shall 验证固定 pSLC 容量是否覆盖其热数据工作集。 | pSLC 过小可能导致频繁回退、spill 或 ENOSPC。 | 测试+分析 | 记录热数据占用、spill/fallback 次数和 P99；不得仅报告平均吞吐。 |
| REQ-PSLC-008 | pSLC/TLC namespace 的物理隔离程度 shall 按“逻辑可见、固件可证实、物理可证明”分级表述。 | Windows 盘符和普通 PhysicalDisk 计数器不能证明 NAND 物理隔离。 | 检查+分析 | 无厂商/固件证据时，结论只能写“逻辑 namespace 隔离”。 |
| REQ-PSLC-009 | 固定 pSLC 的高占用和热状态测试 shall 记录设备级温度、降速、健康计数器和 WHEA/StorPort 事件。 | namespace 之间可能共享温度和功耗资源。 | 测试 | 规定时长内无未预期掉盘、介质错误或数据损坏。 |

## 4. 固定 pSLC 专用测试用例

以下 case 使用与上位文档一致的前七个强制字段：`Case ID、测试工具、测试目的、测试步骤、测试时长、测试脚本、测试标准`。

### 4.1 Namespace 与容量边界

| Case ID | 测试工具 | 测试目的 | 测试步骤 | 测试时长 | 测试脚本 | 测试标准 | 设计理由 |
|---|---|---|---|---:|---|---|---|
| PSLC-ENV-01 | PowerShell、厂商工具、nvme-cli Windows 版（如可用） | 确认 pSLC/TLC namespace 的 ID、容量、扇区格式和盘符映射。 | 1. 枚举 controller 和 namespace；<br>2. 记录 `C/P/T/R`、LBA format、卷 GUID；<br>3. 分别挂载 pSLC/TLC；<br>4. 重启后重复枚举。 | 20–30 分钟 | `Get-Disk`、`Get-Partition`、`Get-Volume`、厂商 namespace 工具 | 两个 namespace 可识别、可挂载、重启后映射稳定；manifest 字段完整。 | 防止后续把逻辑盘符误当成物理隔离证据。 |
| PSLC-CAP-01 | PowerShell、fsutil、Python | 测量固定 pSLC namespace 的真实可用容量和边界误差。 | 1. 清空 pSLC namespace；<br>2. 写入 W1/W2/W3 工作集；<br>3. 写入至 W4；<br>4. 记录剩余空间和文件校验。 | 30–45 分钟 | `fsutil file createnew` 或 `pslc_fill.py` | 实际容量与产品声明一致；无提前 ENOSPC；文件大小和 hash 正确。 | 固定 pSLC 的核心属性是容量固定，必须先建立容量基线。 |
| PSLC-BND-01 | Python、PowerShell、hashlib | 验证写入超过 `P` 时的受控边界行为。 | 1. 写入至 `P-1 GiB`；<br>2. 继续写入 `P+1 GiB`；<br>3. 记录 ENOSPC、spill 或 fallback；<br>4. 读取已有数据并校验 hash。 | 45–60 分钟 | `pslc_boundary_test.py --target <PSLC> --extra 1G` | 若无 spill 规格，应返回受控 ENOSPC；已有数据不可丢失或损坏；不得 silent overwrite TLC。 | 直接验证“固定容量”是否被系统和应用正确处理。 |
| PSLC-BND-02 | Python、PowerShell、Windows PhysicalDisk counters | 测量 W1/W2/W3/W4 下的 burst 性能和尾延迟变化。 | 1. 分别准备 25/50/90/100% 填充；<br>2. 每档执行相同 4K 随机写和大块写；<br>3. 记录 P50/P95/P99/P99.9、温度和队列；<br>4. 比较性能转折点。 | 1–2 小时 | `fio` Windows job 或 `pslc_fill_bench.py` | 所有填充点均有 3 次有效样本；退化点和退化幅度可重复。 | pSLC 固定容量不等于性能始终固定，接近满容量时可能出现 GC/回收。 |
| PSLC-REC-01 | Python、PowerShell、hashlib | 验证 pSLC 接近满容量后删除、TRIM、重启和再利用能力。 | 1. 写入至 90/100%；<br>2. 删除 25% 数据并执行 TRIM；<br>3. 重启系统；<br>4. 再写入 W2 并校验旧数据。 | 45–75 分钟 | `pslc_reuse_test.py`、`Optimize-Volume -ReTrim` | 释放空间可重新使用；无旧数据损坏；TRIM/重启后的性能和空间恢复被记录。 | 固定 pSLC 的容量如果不能可靠回收，会直接限制 KV/checkpoint 应用。 |

### 4.2 跨 namespace 隔离与共享资源

| Case ID | 测试工具 | 测试目的 | 测试步骤 | 测试时长 | 测试脚本 | 测试标准 | 设计理由 |
|---|---|---|---|---:|---|---|---|
| PSLC-ISO-01 | fio、PowerShell monitor | 测量 TLC 顺序读取对 pSLC 延迟的影响。 | 1. 单独运行 pSLC 4K 随机写；<br>2. 单独运行 TLC 顺序读；<br>3. 并发运行两者；<br>4. 计算 pSLC P99 放大。 | 60–90 分钟 | `pslc_tlc_mix.ps1 -Mode PslcWriteTlcRead` | 无 TLC 负载与混合负载的 pSLC P99、队列和温度均有记录；建议 P99 放大≤1.2 倍。 | 判断两个 namespace 是否共享控制器读写资源。 |
| PSLC-ISO-02 | fio、PowerShell monitor | 测量 TLC 写入和 pSLC 热写同时发生时的最坏干扰。 | 1. 将 TLC 填充至 70%；<br>2. 在 pSLC 执行 4K 随机写；<br>3. 在 TLC 执行顺序/随机写；<br>4. 比较 solo/mixed P99 和吞吐。 | 90–120 分钟 | `pslc_tlc_mix.ps1 -Mode BothWrite` | 无 I/O error；记录写放大、温度、队列和 pSLC/TLC 分别的 P99。 | 双写最容易触发 FTL、GC、SLC 回收和温度耦合。 |
| PSLC-ISO-03 | fio、WPR/WPA、Windows PhysicalDisk | 判断 namespace 是否存在可观察的队列或服务时间耦合。 | 1. 分别执行 pSLC solo、TLC solo；<br>2. 执行 pSLC+TLC mixed；<br>3. 采集 ETW；<br>4. 分析进程、卷、队列和 Disk Service Time。 | 1–2 小时 | `wpr -start DiskIO`、`wpr -stop`、`wpa.exe` | 输出按卷/进程的 I/O 时间和排队；无证据时不能宣称物理隔离。 | 普通 PhysicalDisk 总计数器不足以证明物理隔离，ETW 可补充系统层证据。 |

### 4.3 AI workload 适配性

| Case ID | 测试工具 | 测试目的 | 测试步骤 | 测试时长 | 测试脚本 | 测试标准 | 设计理由 |
|---|---|---|---|---:|---|---|---|
| PSLC-AI-TRN-01 | mlpstorage training、DLIO、PowerShell monitor | 验证训练数据放在 TLC、checkpoint/临时数据放在 pSLC 是否减少训练停顿。 | 1. TLC 放置训练数据；<br>2. pSLC 写入 checkpoint/临时文件；<br>3. 运行训练 smoke 和 3 个正式 trial；<br>4. 与 checkpoint 放在 TLC 的基线比较。 | 1–2 小时 | `mlpstorage training run ...` + Windows monitor | 报告 samples/sec、storage stall、checkpoint P99、pSLC/TLC 吞吐和温度；结果按 namespace 分开。 | 直接验证 pSLC 对训练热写路径的实际价值。 |
| PSLC-AI-KV-01 | mlpstorage kvcache、trace/replay | 验证 KV 热集在固定 pSLC 容量内和接近容量边界时的行为。 | 1. 使用 W1/W2/W3 KV 对象集；<br>2. 分别放在 pSLC 和 TLC；<br>3. 运行 spill/fetch；<br>4. 比较 hit/miss、P99 和容量使用。 | 45–75 分钟 | `mlpstorage kvcache run ...`、`kv_cache_benchmark` | pSLC 内工作集不得出现非预期 ENOSPC；接近 P 时必须报告 eviction/fallback；KV 内容和 shape 校验通过。 | KV cache 是最适合固定 pSLC 的候选场景，但也最容易撞上固定容量边界。 |
| PSLC-AI-CKP-01 | mlpstorage checkpointing、hashlib、PowerShell | 验证 checkpoint 小于、等于和超过 `P` 时的提交策略。 | 1. 生成 `0.5P` checkpoint；<br>2. 生成接近 `P` 的 checkpoint；<br>3. 生成大于 `P` 的 checkpoint；<br>4. 分别执行 flush、重启和 restore。 | 60–120 分钟 | `mlpstorage checkpointing run ...`、`checkpoint_boundary.py` | `≤P` 时完成提交和 restore；`>P` 时按产品定义执行 chunk/fallback 或受控失败；hash 一致。 | 证明固定 pSLC 是否适合作为 checkpoint staging，而不是只测瞬时带宽。 |
| PSLC-AI-VDB-01 | Milvus、Docker Desktop、PowerShell monitor | 验证 pSLC 承载 WAL/metadata、TLC 承载向量 segment/index 时的收益和干扰。 | 1. pSLC 放置 WAL/metadata；<br>2. TLC 放置 segment/index；<br>3. 执行 ingest、index、load、search；<br>4. 运行 compaction 并比较查询 P99。 | 1–2 小时 | `mlpstorage vectordb run ...`、Milvus Compose | row count、top-k、重启恢复和 query P99 均通过；compaction 对 pSLC WAL 延迟影响可解释。 | VectorDB 的热写和冷索引具有明显不同的 I/O 特征，适合验证 namespace 分层。 |

### 4.4 热、回收和可靠性

| Case ID | 测试工具 | 测试目的 | 测试步骤 | 测试时长 | 测试脚本 | 测试标准 | 设计理由 |
|---|---|---|---|---:|---|---|---|
| PSLC-THERM-01 | fio、PowerShell、SMART/厂商工具 | 测量 pSLC 连续写、TLC 并发写和高占用下的热降速。 | 1. 将 TLC 填充至 70/85%；<br>2. pSLC 执行连续覆盖写；<br>3. 并发 TLC 写入；<br>4. 记录温度、降速和恢复时间。 | 2–4 小时 | `pslc_thermal_soak.ps1` | 无掉盘和数据错误；热阈值、降速起点、恢复时间和事件日志完整。 | pSLC/TLC 可能共享控制器温度和功耗预算，不能只测单 namespace。 |
| PSLC-END-01 | fio verify、hashlib、SMART/厂商工具 | 验证固定 pSLC 反复覆盖写后的数据完整性和健康状态变化。 | 1. 在 W2/W3 范围内循环覆盖写；<br>2. 每轮写后执行校验；<br>3. 每小时保存 SMART/health；<br>4. 比较 pSLC 与 TLC 写入量和健康计数。 | 4–8 小时 | `fio --verify=crc32c` 或 `pslc_endurance.py` | 无校验失败、介质错误和不可解释的掉盘；写入量、温度、健康计数完整。 | 固定 pSLC 可能承受高频热写，需观察写放大和健康变化；该 case 不等价于企业级耐久度认证。 |
| PSLC-REC-02 | PowerShell、hashlib、Milvus/KV/checkpoint validate | 验证 pSLC 满容量、重启或服务重启后 AI 热数据是否可恢复。 | 1. 将 pSLC 填充至 90/100%；<br>2. 执行 checkpoint/KV/VDB 写入；<br>3. 重启系统或服务；<br>4. 执行 restore、KV 校验和向量查询。 | 60–90 分钟 | `Restart-Computer`、`mlpstorage validate`、业务校验脚本 | 数据 hash、checkpoint restore、KV shape 和向量 count/top-k 全部通过；无 WHEA/StorPort 新错误。 | 验证容量边界和恢复流程是否会放大数据完整性风险。 |

## 5. 轻量与全量执行包

### 5.1 固定 pSLC 轻量包

适用于每块 SSD 首轮筛选：

```text
PSLC-ENV-01
PSLC-CAP-01
PSLC-BND-01
PSLC-BND-02
PSLC-ISO-01
PSLC-AI-KV-01
PSLC-AI-CKP-01
PSLC-REC-02
```

建议在 1 TB、2 TB、4 TB 各执行一次；总时长约 4–8 小时。重点输出固定容量边界、pSLC 性能转折点、KV/checkpoint 适配性和跨 namespace 初步干扰。

### 5.2 固定 pSLC 全量包

全量包执行本补充的 15 个 case，并与上位文档的训练、KV、VectorDB、长稳和恢复 case 关联。推荐配置：

- P1：1 TB/32 GB，执行 N0、N1、N2 和关键 AI smoke。
- P2：2 TB/64 GB，执行全部固定 pSLC 核心 case，作为主结论配置。
- P3：4 TB/128 GB，执行 85% 占用、长稳、热回收和扩展 AI workload。

全量报告必须按以下关系拆分：

```text
容量 × 固定 pSLC 容量 P × pSLC 填充率 Fp × TLC 占用率 Ft × workload × 执行模式
```

不得把不同 `P/C`、不同填充状态或不同 namespace 布局合并成一个平均分数。

## 6. 判定原则

1. **容量边界**：超过 `P` 时必须是受控 ENOSPC、明确 spill/fallback 或产品定义行为；禁止 silent data loss。
2. **性能**：报告 P50/P95/P99/P99.9、IOPS、吞吐、队列和温度；不得只报告峰值。
3. **隔离性**：同时报告 solo 与 mixed；建议初始以 P99 放大 1.2 倍作为良好隔离目标，超过 1.5 倍标记为明显干扰。
4. **完整性**：hash、文件数量、checkpoint restore、KV shape、VectorDB count/top-k 任一失败，case 不得 PASS。
5. **物理隔离声明**：没有厂商固件、FTL 或 NAND 映射证据时，只能声明“逻辑 namespace 隔离”。
6. **耐久性边界**：PSLC-END-01 是消费级研究和风险筛查，不得直接解释为企业级耐久度认证。

