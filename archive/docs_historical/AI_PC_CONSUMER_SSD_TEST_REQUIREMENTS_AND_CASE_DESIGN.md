# 消费级 AI PC AI SSD 系统级测试需求与测试用例设计规范

**文档编号**：AI-PC-SSD-VV-PLAN-001  
**版本**：1.0  
**日期**：2026-08-04  
**适用对象**：Windows 11、1 TB/2 TB/4 TB 消费级 NVMe SSD；显存与系统内存合计 32 GB、64 GB、128 GB 的 AI PC。  
**配套矩阵**：[AI_PC_CONSUMER_SSD_TEST_REQUIREMENTS_AND_CASE_MATRIX.xlsx](../outputs/ai_pc_consumer_ssd_standards_based_20260804/AI_PC_CONSUMER_SSD_TEST_REQUIREMENTS_AND_CASE_MATRIX.xlsx)

## 1. 目的与设计结论

本方案用于验证消费级 AI PC 中 SSD 对训练数据读取、模型检查点、KV cache offloading、向量数据库、混合并发、热稳定性和异常恢复的系统级支撑能力。测试重点是“业务可用性 + SSD 可观测性能 + 数据完整性 + 可复现证据”，不把企业级耐久度或协议合规性作为消费级首轮准入条件。

权威资料的逐项摘录与来源索引见：[SSD_SYSTEM_TEST_STANDARDS_RESEARCH.md](SSD_SYSTEM_TEST_STANDARDS_RESEARCH.md)。

针对固定容量 pSLC namespace 的边界、跨 namespace 干扰和 AI 热数据适配，另有专项补充：[AI_PC_CONSUMER_SSD_FIXED_PSLC_TEST_REQUIREMENTS_SUPPLEMENT.md](AI_PC_CONSUMER_SSD_FIXED_PSLC_TEST_REQUIREMENTS_SUPPLEMENT.md)。

本次重新设计保持既有 **29 个核心 case + 8 个可选 case** 不变，只重新定义以下内容：

1. 每条测试需求有唯一 ID、来源、验证方法和可量化验收条件。
2. 每个 case 的前 7 列固定为：**Case ID、测试工具、测试目的、测试步骤、测试时长、测试脚本、测试标准**。
3. 测试步骤统一为 1、2、3……，每一步只包含一个可执行动作。
4. 追加前置条件、DUT 状态、工作集、块大小、并发度、监控项、阈值、无效条件和证据包，避免“跑过但无法审计”。
5. 明确 Native、Scaled、Trace/Replay、Hybrid 四种执行口径；trace/replay 只复现逻辑 I/O 节奏，不替代真实应用或控制器内部 I/O。

## 2. 采用的规范与借鉴原则

### 2.1 SSD 性能测试规范

- **SNIA Solid State Storage Performance Test Specification（PTS）**：将设备测试拆分为预处理、稳态、性能测量和报告；客户端/消费级测试也要求记录工作负载和测试条件。SNIA 的测试服务覆盖 IOPS、吞吐、延迟、工作集和数据完整性等测试族。[SNIA SSS PTS](https://www.snia.org/tech_activities/standards/curr_standards/pts)、[SNIA PTS 测试服务](https://www.snia.org/forums/sssi/ptstest)
- **SNIA Technical Position：稳态测试**：采用预处理与稳态判定，性能窗口通常要求连续观测值围绕平均值收敛，而不是只报告一次峰值。[SNIA PTS Technical Position](https://www.snia.org/forums/sssi/pts/tp)
- **NVMe 规范与合规测试**：NVMe 规范作为控制器能力、错误处理、Sanitize、健康信息和电源管理的协议依据；本方案将其作为诊断/门禁依据，不把协议合规 case 与 AI workload 性能混为一类。[NVM Express 规范](https://nvmexpress.org/specifications/)、[NVM Express 合规计划](https://nvmexpress.org/products/compliance/)

### 2.2 系统级验证与测试文档规范

- **ISO/IEC/IEEE 29119-3** 提供跨组织、跨生命周期的测试文档模板；本方案据此设置文档控制、测试条件、步骤、预期结果、实际结果、偏差和证据字段。[ISO/IEC/IEEE 29119-3](https://www.iso.org/standard/79429.html)
- **NASA Systems Engineering Handbook** 要求需求向下分解、双向追溯，并通过分析、检查、演示和测试完成验证；因此本方案建立需求矩阵（RTM）和 Case→Requirement 双向链接。[NASA Systems Engineering Handbook Appendix](https://www.nasa.gov/reference/system-engineering-handbook-appendix/)
- **NASA SWE-065/SWE-071/SWE-072** 强调客观证据、可测量的验收标准、测试用例与需求的双向追溯，以及报告中保存输入、输出、异常和 case ID。[SWE-065](https://swehb.nasa.gov/spaces/SWEHBVD/pages/102695448/SWE-065+Test+Plan%2C+Procedures%2C+Reports?desktop=true&macroName=show-if)、[SWE-071](https://swehb.nasa.gov/spaces/SWEHBVD/pages/102695453/SWE-071%2B-%2BUpdate%2BTest%2BPlans%2Band%2BProcedures)、[SWE-072](https://swehb.nasa.gov/spaces/7150/pages/16449898/SWE-072%2B-%2BBidirectional+Traceability+Between+Software+Test+Procedures+and+Software+Requirements)
- **Windows HLK NVMe 测试**要求 NVMe 设备同时按 Storage Controller 与 Storage Disk 角色验证，并按官方 playlist 执行；本方案把 HLK/设备门禁放在 Stage 0/1，不用 HLK 结果代替 AI workload 结果。[Microsoft NVMe SSD Testing Overview](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/nvme-ssd-testing-overview)、[Device.Storage tests](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/device-storage-tests)

### 2.3 可观测性与结果统计

- fio 的日志定义包含时间、值、方向、块大小、偏移和发起时间，可作为 trace 字段和可复现 I/O 记录的参考；延迟报告至少保留 P50/P95/P99，必要时保留 P99.9。[fio HOWTO](https://github.com/axboe/fio/blob/master/HOWTO.rst)
- Windows `PhysicalDisk` 计数器用于关联进程 I/O 与实际物理盘；本方案默认 1 s 采样并同时记录吞吐、IOPS、平均读写延迟、队列长度、Busy、温度、CPU、内存、GPU、分页和 WHEA/StorPort 事件。[Windows 性能故障排查](https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-performance-problems-in-windows)、[Windows Get-Counter](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-counter?view=powershell-7.5)

## 3. 需求编写规范

### 3.1 需求句式

每条需求使用以下结构：

> **REQ-ID**：在给定条件、配置和数据集下，DUT **shall** 完成可观测动作，并达到明确的指标阈值；结果必须留存指定证据。

禁止使用“性能正常、运行稳定、速度较快、没有明显问题”等不可测量表述。复合要求必须拆分为多条需求；“应当/建议”只用于非准入建议，不得放在强制验收条件中。

### 3.2 需求 ID 分类

| 前缀 | 范围 |
|---|---|
| REQ-ENV | DUT 身份、OS、驱动、路径和测试环境 |
| REQ-CAP | 容量预算、保留空间、结果目录与临时目录 |
| REQ-MON | 监控采样连续性、时间戳和事件记录 |
| REQ-IO | 块大小、队列深度、读写比例、稳态与延迟统计 |
| REQ-TRN | 训练数据读取、shuffle、epoch 和数据完整性 |
| REQ-CKP | 模型检查点写入、读取、恢复和一致性 |
| REQ-KVC | KV cache 写入、读取、spill/fetch 和混合并发 |
| REQ-VDB | 向量库导入、索引、ANN 搜索、持久化和恢复 |
| REQ-QOS | 混合 workload 的隔离性、尾延迟和优先级 |
| REQ-REL | 长时间、热状态、占用率和性能漂移 |
| REQ-REC | 进程重启、设备重连、掉电/异常后的恢复 |
| REQ-DATA | 数据校验、丢失、重复、损坏和可恢复性 |

### 3.3 每条需求必须具备的属性

`需求ID`、`需求文本`、`来源/理由`、`适用档位`、`前置条件`、`验证方法（检查/分析/演示/测试）`、`关联 Case ID`、`量化验收标准`、`客观证据`、`状态`。Excel 的“标准化需求矩阵”和“RTM”页按此字段维护。

## 4. 测试用例编写规范

### 4.1 强制字段

每个 case 必须按以下顺序填写，前 7 列不得改名或调换：

| 字段 | 写作要求 |
|---|---|
| Case ID | 唯一、稳定、包含阶段/测试族，例如 `S3-TRN-01`；重跑不新建 ID |
| 测试工具 | 写明 CLI、脚本、版本及 Windows 采集工具 |
| 测试目的 | 一句话说明要验证的系统行为和 SSD 影响 |
| 测试步骤 | 使用 `1.`、`2.`、`3.`；动作、输入、检查点和输出分开写 |
| 测试时长 | 预估准备、执行、稳定窗口和清理时间；长稳 case 写小时数 |
| 测试脚本 | 写可执行命令或仓库内脚本路径；参数使用占位符并说明替换规则 |
| 测试标准 | 采用可计算阈值、稳态规则、完整性结果或官方 playlist 结果 |

### 4.2 建议追加字段

`需求ID/来源`、`阶段`、`优先级`、`测试家族`、`推荐配置`、`SSD容量`、`显存+内存`、`执行模式`、`模型/工作负载`、`前置条件`、`DUT状态（FOB/Purge/稳态）`、`Active Range`、`块大小`、`R/W比例`、`QD/线程/OIO`、`数据模式`、`监控项`、`判定阈值`、`无效条件`、`证据包`、`结果`、`备注`。

### 4.3 统一步骤模板

1. **准备**：确认 DUT 身份、容量、空闲空间、功耗模式、温度和结果目录；必要时执行 purge/预处理。
2. **配置**：写入并保存模型、数据集、块大小、读写比例、并发度、Active Range、缓存和随机种子。
3. **执行**：按 Native/Scaled/Trace/Replay/Hybrid 口径运行，直到完成目标迭代、稳态窗口或规定时限。
4. **采集**：保存 workload summary、Windows 1 s timeseries、温度/健康、事件日志和 trace（如适用）。
5. **验证**：执行校验和、文件数量、checkpoint restore、向量查询一致性或 KV 命中一致性检查。
6. **判定**：按阈值给出 PASS/CONDITIONAL/FAIL/INVALID/NOT RUN，并记录偏差、环境变化和证据路径。

## 5. AI PC 测试配置与执行口径

### 5.1 配置档位

| 档位 | SSD | 显存+内存 | 主要用途 |
|---|---:|---:|---|
| P1 入门 | 1 TB | 32 GB | Windows 真实运行、训练 smoke、8B checkpoint/KV、1M 向量库 |
| P2 主流 | 2 TB | 64 GB | 主结论档；训练代表性画像、8B/70B 子集、5M 向量库、混合 QoS |
| P3 高容量 | 4 TB | 128 GB | 大工作集、长稳、4 TB 容量压力、可选大模型/大索引 |

显存与系统内存的实际容量必须在 manifest 中分别记录。档位是分层规则，不允许用“64 GB 档”替换真实 RAM/VRAM 数值。

### 5.2 执行模式边界

| 模式 | 结论范围 | 允许的用途 |
|---|---|---|
| Native | 真实应用、真实 Windows 路径、真实 DUT | 业务正确性、端到端性能、发布主结论 |
| Scaled | 工作集或模型按比例缩小，仍真实命中 DUT | P1/P2 容量不足时的可比性结果；必须写缩放比例 |
| Trace/Replay | 复现逻辑 I/O 的时间、方向、大小、偏移和节奏 | 在不依赖完整应用环境时隔离 SSD I/O；不能代表应用端到端性能 |
| Hybrid | 应用产生真实 trace，再对 SSD 做 replay 或与应用混合 | 研究 workload 对 SSD 的贡献；结果需与 Native 分开发布 |

## 6. 分阶段测试流程与退出条件

### Stage 0：环境与容量门禁（P0）

检查 SSD 型号/固件/序列号、PCIe link、文件系统、剩余空间、数据/结果路径、Docker/Milvus 位置、监控计数器和错误日志。缺少身份、路径或监控证据时只能 `NOT RUN`，不得进入性能比较。

### Stage 1：I/O 口径与设备基线（P0）

完成 purge/预处理规则、顺序/随机读写、块大小、QD/线程、Active Range 和稳态窗口定义；若采用 SNIA PTS 口径，应显式记录 WIPC/WDPC、预处理轮次、Steady State 判定和测量窗口。保留 P50/P95/P99/P99.9、IOPS、MB/s、队列和温度，至少记录窗口均值、漂移/拟合斜率和达到稳态的时间。

### Stage 2：应用 smoke 与完整性（P0）

在 P1/P2 先完成训练、checkpoint、KV cache、VectorDB 的最小 Native case；验证文件数量、校验和、restore、查询一致性和重启后可用性。Smoke 失败时停止扩大矩阵。

### Stage 3：代表性 AI workload（P0/P1）

训练选择 UNet3D（大文件/带宽）、RetinaNet（小文件/IOPS）和 ResNet50（中等对象/混合访问）；checkpoint/KV 选择 Llama 3 8B 作为 P1/P2 主结论，70B 使用 P2/P3 子集或 Scaled。VectorDB 选择 1M/5M 向量和 IVF/HNSW 两类索引。

### Stage 4：混合 QoS 与干扰（P1）

训练读取、checkpoint 写入、KV spill/fetch、向量检索并行运行；分别记录各业务 P95/P99、SSD 队列和尾延迟放大。不得只看总吞吐。

### Stage 5：热状态、长稳与占用率（P1）

在 70% 和 85% 容量占用下重复代表性 workload；记录温度、热降速、性能漂移、错误计数和功耗。消费级 SSD 的长稳结果用于风险识别和产品比较，不宣称企业级耐久度等价。

### Stage 6：恢复与发布判定（P0/P1）

执行进程重启、服务重启、设备重连/重启后的数据恢复；必要时执行受控异常注入。恢复后必须通过完整性和业务可用性检查，且无新增 WHEA/StorPort/设备错误。

## 7. 监控、证据与判定规则

### 7.1 每个性能 case 的最小证据包

`manifest.json`、`configview.txt`、`workload_summary.json`、`windows_disk_1s.csv`、`temperature_health.csv`、`eventlog.evtx` 或导出文本、`trace.csv`（Trace/Replay/Hybrid）、`integrity_report.json`、`verdict.json`、原始工具日志和脚本版本。

### 7.2 指标与默认判定

| 类别 | 默认判定 |
|---|---|
| 需求/路径 | 身份、路径、版本和配置字段 100% 完整；结果目录不可与 DUT 工作集混淆 |
| 性能 | 按 case 规定的 IOPS/MB/s/延迟阈值；同时报告 P50/P95/P99，尾延迟超限即不得 PASS |
| 稳态 | 连续窗口均值/斜率满足 case 的稳态规则；不得用单次峰值替代 |
| 完整性 | 文件数、校验和、checkpoint restore、向量查询或 KV 命中结果全部通过 |
| 稳定性 | 规定时长内无未预期错误、死锁、设备掉线或监控中断；温度/降速按 case 条件记录 |
| HLK/设备门禁 | 官方 playlist 所有必需测试通过；不通过时标记 `FAIL` 或 `NOT RUN`，不折算成 AI workload 分数 |

结果状态仅允许：`PASS`、`CONDITIONAL`、`FAIL`、`INVALID`、`NOT RUN`。缺少关键证据、配置漂移、监控断点或路径未命中 DUT 时必须是 `INVALID`/`NOT RUN`，而不是人为判定为 PASS。

## 8. 需求到 Case 的追溯要求

Excel 中的 `标准化需求矩阵` 保存需求，`标准化Case矩阵` 保存完整字段，`简化Case清单` 服务于执行人员，`RTM` 提供双向追溯。每个需求至少关联一个 case；每个核心 case 至少关联一个需求。需求变更时必须检查受影响 case、脚本、阈值和证据字段。

## 9. 交付物与使用方式

1. 本文档：规范、配置、阶段、监控、证据和判定规则。
2. Excel：完整 29+8 case、标准化需求、RTM、简化执行页、报告元数据和证据清单。
3. 原有矩阵及历史结果保留不动；本次输出使用新的目录和文件名。
4. 首轮建议执行 P1→P2→P3；每个阶段先通过 P0 门禁，再进入下一个阶段。Trace/Replay 结果单独标识，不与 Native 结果合并。
