# SSD / 存储系统级测试需求与测试用例撰写规范

> 研究日期：2026-08-04  
> 适用范围：消费级 AI PC、NVMe SSD、Windows 运行环境，以及由 `mlperform storage` 驱动的训练、checkpoint、KV cache offloading、向量数据库和文件系统 I/O 场景。  
> 文档定位：把公开的 SSD/存储标准和成熟工具约束转化为可执行的测试需求、测试用例和测试报告规则。

## 1. 结论摘要

本方案采用“需求（Requirement）—用例（Test Case）—执行记录（Test Run）—证据（Evidence）”四层结构。每个测试用例必须能够独立回答：测什么、在什么配置下测、如何执行、测多久、记录什么、什么条件算通过、失败后如何定位。

设计基线如下：

1. 用 SNIA SSS PTS 的设备准备、预处理、稳态、测量窗口、报告头和单位规则作为 SSD 性能测试基线。
2. 用 NVMe Base Specification 的 SMART/Health、Flush、Sanitize、功耗状态和错误/恢复语义定义设备级监控与恢复判定。
3. 用 fio 的可复现随机种子、队列深度、读写比例、块大小、稳态、延迟分位数、数据校验和分阶段执行能力实现可重复 workload。
4. 用 Windows HLK/WPT 的系统配置、ETW/WPR/WPA、日志保留和失败重跑原则实现 Windows 系统级证据链。
5. 每个 case 保留用户指定的七个核心字段：`Case ID`、`测试工具`、`测试目的`、`测试步骤`、`测试时长`、`测试脚本`、`测试标准`；另加必要的配置、前置条件、监控、证据和追溯字段。

## 2. 权威来源与可复用要求

### 2.1 SNIA SSS Performance Test Specification（SSS PTS）

来源：

- [SNIA SSS PTS 标准入口](https://www.snia.org/tech_activities/standards/curr_standards/pts)
- [SNIA SSS PTS v2.0.1 revision 10 PDF（公开工作稿，方法章节）](https://www.snia.org/sites/default/files/technical-work/pts/draft/SNIA-SSS-PTS-2.0.1-rev10.pdf)
- [SNIA PTS Throughput Test 说明](https://www.snia.org/forums/sssi/pts/tp)

可直接转化为测试规范的要求：

| 来源章节/主题 | 标准要求（转述） | 对本项目的落地规则 |
|---|---|---|
| PTS §3.1 Steady State | SSD 从 FOB/Purged 状态开始通常有瞬态高性能；正式结果应在与 workload 对应的 Steady State 测量窗口采集，并记录收敛趋势。 | 区分 `FOB`、`Preconditioned`、`Steady-State` 三种结果；没有稳态证明时只能标记为 `Exploratory`，不能与正式结果混比。 |
| PTS §3.2 Purge | 每次预处理和测试循环前执行 Purge；不支持或未执行时必须写入报告。可使用 NVMe Format、Sanitize 或厂商方法。 | 每个正式 case 前记录 purge 方法、完成时间和设备状态；若 Windows 不允许直接 purge，必须标记为 `Deviation` 并记录原因。 |
| PTS §3.3 Pre-conditioning | 预处理分为 Workload Independent Preconditioning（WIPC）和 Workload Dependent Preconditioning（WDPC）；WDPC 是测试循环的一部分，决定是否达到稳态。 | 用例步骤显式分为清理、WIPC、WDPC/稳态、测量四段，不能只写“预热后测试”。 |
| PTS §4 Basic Test Flow | ActiveRange、参数、预处理和测试循环按固定顺序执行；步骤之间不得插入会造成恢复的无关间隔，除非测试目标就是恢复。 | 脚本固定步骤顺序；把人工等待、重启、后台任务和温度恢复写成显式步骤。 |
| PTS §5 Common Reporting | 报告应包含日期、操作者、规范版本、系统硬件、系统软件、DUT 厂商/型号/序列号/固件/容量/接口/形态/介质类型等。 | 每次运行生成不可变的 `run_manifest.json`，包含机器、系统、驱动、SSD、脚本和参数快照。 |
| PTS §6 Tool Guidelines | 工具应能生成并记录随机/顺序块 I/O、ActiveRange、读写比例、I/O 大小、多 outstanding I/O，并输出 IOPS、MB/s、最大延迟和平均响应时间；随机函数应可设 seed、输出至少 48 bit、均匀分布。 | 每个 workload 必须固定 `seed`、`active_range`、`bs`、`rw_mix`、`QD/threads`，并在结果中回显；trace 必须保存时间戳、方向、大小和逻辑偏移/对象标识。 |
| PTS §2.4.1 Units | 容量、数据传输率和数据量用十进制；I/O 大小和偏移用二进制单位。 | 表格同时使用 `GB/TB`（容量/带宽）和 `KiB/MiB/GiB`（块大小/偏移），禁止混写。 |
| PTS IOPS/TP/LAT/DIRTH | 用例应覆盖随机 IOPS、顺序吞吐、平均/高分位延迟、需求强度/响应时间直方图，并使用明确的测量窗口。 | AI SSD 主矩阵至少包含 4 KiB 随机、1 MiB 顺序、混合读写、P99/P99.9 延迟和并发强度扫描。 |
| PTS §8/§9/§14 | 稳态验证应记录测量窗口、平均值、允许范围、实测范围、拟合斜率和相关系数；报告需同时保留收敛图、验证图和测量表。 | Excel 的“测试标准”写数值门限；结果包保留每轮原始日志、稳态判定表和 P50/P95/P99/P99.9。 |
| PTS Throughput page | TP 流程为 Purge → WIPC → WDPC 至稳态；示例中每个读/写 round 为 1 分钟，5 rounds 构成测量窗口，稳态要求包含最大数据偏差和斜率约束。 | 消费级 AI PC 可缩短单轮时长，但必须保留“连续 round + 稳态判定 + 最后窗口平均”的结构，并在配置中注明缩放比例。 |
| PTS Test Service / Basic Benchmark | SNIA 的测试服务页面列出 IOPS（多读写比例×块大小矩阵）、TP、LAT，以及 WSAT、HIR、XSR、ECW、DIRTH 等扩展测试。 | 将基础性能、主机空闲恢复、跨负载恢复、写饱和、复合 workload 和 QoS 作为不同 case family，不把一个“综合性能”case 混成不可审计的长脚本。 |
| PTS WSAT | WSAT 在 Purge 后对随机 4 KiB 写入持续到规定时间或若干 drive fills，用于观察 FOB 峰值、性能下降、过渡和稳态。 | 消费级 SSD 可设计 30 分钟/4 小时/容量比例的缩放写饱和 case，必须报告 host writes/TBW、温度、稳态和下降曲线，并标记为 endurance/stress 而非日常性能。 |
| PTS Client guidance | Client 预处理可限制 ActiveRange，写缓存状态和实际 workload 特征应披露；多线程测试应记录 OIO/Thread、TC、数据模式和是否启用 Flush。 | AI PC 以客户端访问模式为主，采用 75% ActiveRange 或等价缩放时必须在配置理由中说明；若 Windows 无法关闭写缓存，必须显式加入 Flush 频率和数据完整性校验。 |

### 2.2 NVM Express Base Specification 2.0a

来源：[NVM Express Base Specification 2.0a（Ratified PDF）](https://nvmexpress.org/wp-content/uploads/NVMe-NVM-Express-2.0a-2021.07.26-Ratified.pdf)

可直接转化为设备监控和恢复用例的要求：

| NVMe 主题 | 标准语义 | 测试设计落地 |
|---|---|---|
| SMART/Health §5.16.1.3 | SMART/Health 跨电源周期保留；包含 Critical Warning、Percentage Used、Data Units Read/Written、Host Read/Write Commands、Controller Busy Time、Power Cycles、Power-on Hours、Unsafe Shutdowns、Media and Data Integrity Errors、Error Information Log Entries、温度告警时间等。 | 每个长时间或异常恢复 case 在开始/结束各采集一次 SMART；长压测按固定间隔采集并比较增量。任何 Critical Warning、Media/Data Integrity Error 或异常错误条目增长均触发失败/人工复核。 |
| Critical/Warning temperature | Identify Controller 提供 Warning Composite Temperature Threshold（WCTEMP）和 Critical Composite Temperature Threshold（CCTEMP）；临界温度可能导致数据丢失、自动关机、严重降速或永久损伤。 | 温度门限优先使用 DUT 自报 WCTEMP/CCTEMP；报告温度峰值、超阈时长和是否发生降速/错误。不能用“环境温度正常”替代 SSD composite temperature。 |
| Flush §7.1 | Flush 用于把易失写缓存中指定 namespace 的数据和元数据提交到非易失介质；完成表示该命令之前已完成的 I/O 已提交。 | checkpoint、KV spill 和断电恢复 case 明确设置 Flush/FUA 策略；检查 Flush 返回码、恢复后校验和及丢失窗口。 |
| Sanitize §5.24/§8.21 | Sanitize 在后台运行；Sanitize 命令完成不等于操作完成；支持 Block Erase/Crypto Erase/Overwrite 的能力由 Identify 报告；进度和最终状态通过 Sanitize Status log/异步事件报告。 | 清理用例必须轮询 Sanitize Status（低频率），等待完成事件/最终状态后再开始下一 case；不得把命令提交返回当作完成时间。 |
| SMART performance counters | Read/Write Commands、Data Units 和 Controller Busy Time 可用于推导 IOPS/带宽和设备 busy ratio。 | 同时保存工具侧统计和 SMART 前后差值，用于发现文件系统/缓存层与设备计数不一致。 |
| Power State Descriptor | Identify 中描述 Active Power、Idle Power、Entry/Exit Latency 及相对吞吐/延迟；Idle Power 的定义是在无 pending I/O 且稳定 idle 后的时间窗口。 | 低功耗/空闲恢复 case 记录 power state、进入/退出时间、恢复延迟和稳定空闲功耗；不能用短暂读写功耗代替 idle power。 |

### 2.3 fio：成熟的可重复 I/O 负载和数据校验框架

来源：[fio HOWTO（官方项目文档）](https://github.com/axboe/fio/blob/master/HOWTO.rst)

可复用的设计规则：

1. 用 `direct=1` 表示非缓冲 I/O；但 fio 文档明确指出 Windows 同步 ioengine 不支持 direct I/O，因此 Windows case 必须在“文件系统缓存路径”和“可用的非缓冲/异步路径”之间明确分组，不能把 Linux `O_DIRECT` 结果直接当作 Windows 结果。
2. 用 `time_based=1` 与 `runtime` 固定运行窗口；用 `ramp_time` 或 `ramp_size` 让性能先稳定再计入结果。
3. 用 `clat_percentiles`、`lat_percentiles`、`percentile_list` 输出 P50/P95/P99/P99.9；所有同一 reporting group 的 job 必须使用一致的 percentile 配置。
4. 用 `verify=sha256/sha512`、`verify_only`、`verify_state_save/load`、`verify_policy=fsynced` 形成写入、同步、重启/断电后校验链；`fsynced` 只把最后一次成功同步之前的写入视为断电后必须持久化的数据。
5. 使用 `stonewall` 明确阶段边界，避免上一个阶段的 job 与下一个阶段重叠；用 `group_reporting` 统一汇总同组 job。
6. 固定随机 seed、文件大小、`rw`、`bs`、`iodepth`、`numjobs`、`runtime`、`ramp_time` 和输出格式；脚本和 job file 纳入版本控制。
7. 若使用 steady-state 功能，应在用例里写明收敛指标和阈值，例如 IOPS/带宽回归斜率或窗口内波动范围；不能只写“结果稳定”。

### 2.4 Windows HLK、WPR/WPA 和性能计数器

来源：

- [Windows HLK 系统客户端测试前置条件](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/system-client-testing-prerequisites)
- [Windows HLK Device.Storage 故障排查](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/troubleshooting-devicestorage-testing)
- [Windows Performance Toolkit / ETW](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/event-tracing-for-windows)
- [WPR 内置录制配置](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/built-in-recording-profiles)
- [WPR/Xperf 磁盘 I/O trace 建议](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/using-xperf-profiles)
- [Windows 存储性能计数器和告警阈值](https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-performance-problems-in-windows)
- [Windows Physical Disk performance history](https://learn.microsoft.com/en-us/windows-server/storage/storage-spaces/performance-history-for-drives)

可复用的设计规则：

1. HLK 要求在测试前启用设备、安装相关驱动，并按目标系统的 shipping configuration 测试；电源选项应禁止自动待机/休眠/显示器关闭等影响测试的状态切换。AI PC case 的前置条件应记录 Windows 版本、驱动、BIOS、电源计划、后台更新策略和是否接交流电。
2. HLK 故障排查要求查看测试日志，解决问题后重新运行，并保留日志；因此每个 case 必须有 `日志路径`、`重跑原因`、`偏差说明` 和 `最终判定`。
3. ETW 提供一致的内核和应用事件捕获，WPR 负责启动/停止会话，WPA 分析 ETL。内置 profile 直接覆盖 Disk I/O activity 和 Power usage。磁盘 I/O 长 trace 可使用内存 circular buffer，避免把 trace 写盘干扰 DUT。
4. WPA 可区分 I/O 类型（read/write/flush）、进程、大小、Disk Service Time 和排队的 IO Time。AI SSD 的 Windows 系统级 evidence 应至少保留 ETL、按进程/路径聚合的 I/O 表和关键时间区间截图/导出表。
5. Windows 文档给出参考告警：`Avg. Disk sec/Read/Write` 小于 15 ms 为健康，超过 25 ms 为告警，超过 50 ms 为严重；短时尖峰可容忍，但持续超过约 1 分钟应调查。该阈值是系统诊断参考，不应替代 DUT/AI workload 的专属 SLA。
6. Physical Disk counters 的 IOPS、吞吐和延迟由 Physical Disk counter set 提供，采样值是整个时间间隔的平均；结果报告需写明采样周期，不能把 10 秒窗口平均误解为每秒瞬时峰值。
7. [Microsoft NVMe SSD Testing Overview](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/nvme-ssd-testing-overview) 要求 NVMe SSD 同时作为 Storage Controller 和 Storage Disk 测试，并按官方 playlist 执行适用测试。该兼容性层应与 AI workload 性能层分开编号，避免把“通过 Windows 兼容测试”误写成“达到应用性能目标”。
8. [Device.Storage tests](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/device-storage-tests) 直接提供 Disk Stress、Disk Verification、Bus/LUN Reset、NVMe I/O、NVMe Deallocate、Queue Pause-Resume、Queue Utilization、Capabilities 和 Interrupt 等场景。它们可作为 Windows 系统级异常/恢复用例的参考来源；需要 raw/non-boot 盘的测试必须在前置条件中声明，不能对系统启动盘隐式执行。
9. [Windows HLK Disk Verification](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/f8f88b8a-ff9c-4cfb-9e95-6be2511e5510) 的公开说明采用随机 raw write/read 后比较结果的方式，并明确要求在独立测试盘上执行、准备足够空闲空间、记录固定块大小和运行时长。AI SSD 方案可借鉴这种“写入—读回—比较—保留日志”的完整性闭环，但不应把 HLK 的固定时长直接套用到消费级 AI PC。

### 2.5 测试文档和验证证据规范

来源：

- [ISO/IEC/IEEE 29119-3:2021 Test Documentation](https://www.iso.org/standard/79429.html)
- [NASA SWE-114 Software Test Procedures](https://swehb.nasa.gov/spaces/7150/pages/16449688/SWE-114%2B-%2BSoftware%2BTest%2BProcedures)
- [NASA SWE-066 Perform Testing](https://swehb.nasa.gov/spaces/SWEHBVD/pages/102695449/SWE-066%2B-%2BPerform%2BTesting)
- [NASA Systems Engineering Handbook](https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf)

这些文档不是 SSD 协议规范，但为硬件系统级验证提供了成熟的写法：

1. 测试程序应描述准备、配置、测试数据、测试方法、预期结果，并与需求双向追溯；程序在使用前应审查有效性、适用性、充分性、完整性和准确性。
2. 每个需求应有一个或多个测试；用例数量按风险/关键度确定，并覆盖正常、边界、压力、异常和恢复场景。
3. 测试程序要记录系统状态、输入、输出、观察项和 pass/fail 判定；执行记录要保存日期、时间、环境、人员、脚本版本和偏差。
4. NASA 的验证程序模板强调：测试对象、配置差异、目标和容差、步骤和观察、测试软件、测量设备及准确度、校准/版本信息、数据记录和结果授权。对 AI PC，可把测量设备扩展为功耗计、温度传感器、WPR/WPA、NVMe SMART 和应用日志。
5. 结果报告应包含实际结果与预期结果的比较、异常/不符合项、根因与纠正措施、重测结果和需求覆盖率；不能只交付“通过/失败”一列。

## 3. 推荐的测试文档层级

### 3.1 Test Requirement（TR）

每条需求只表达一个可验证目标，使用“系统应在……条件下……达到/不超过……”的句式。建议字段：

| 字段 | 写作要求 |
|---|---|
| Requirement ID | 唯一且稳定，如 `SSD-PERF-REQ-001`。 |
| Requirement | 单一、可测量、包含对象/条件/结果/容差。 |
| Verification Method | Test / Analysis / Inspection / Demonstration。AI SSD 主体使用 Test，监控规则可使用 Analysis。 |
| Priority / Risk | `P0`（数据完整性/恢复）、`P1`（主要性能）、`P2`（优化项）。 |
| Rationale | 说明与训练、checkpoint、KV、VDB 或 Windows 体验的关系。 |
| Acceptance Threshold | 单位明确，给出平均、分位数、斜率、错误数或最大时长。 |
| Traceability | 对应 case ID、脚本、结果和缺陷。 |

### 3.2 Test Case（TC）

Excel 的主矩阵必须按下列顺序保留用户要求的字段；前七列为强制字段，不得省略：

| 序号 | 字段 | 规则 |
|---:|---|---|
| 1 | Case ID | 唯一、稳定、可反向追溯到需求，如 `AI-SSD-TRN-001`。 |
| 2 | 测试工具 | 写明工具及版本，例如 `mlpstorage training run`、`fio 3.x`、`nvme-cli`、`WPR/WPA`。 |
| 3 | 测试目的 | 一句话，说明验证对象和风险；避免把步骤写进目的。 |
| 4 | 测试步骤 | 只写可执行动作，统一用 `1.`、`2.`、`3.` 编号，每步一个动作；包括准备、执行、采集、校验和清理。 |
| 5 | 测试时长 | 写预计总时长，并拆出预处理/稳态/测量/恢复；若按 SSD 容量缩放，写公式或范围。 |
| 6 | 测试脚本 | 给出仓库相对路径、命令入口、job/config 文件和关键参数；禁止只写“运行脚本”。 |
| 7 | 测试标准 | 量化 pass/fail；同时列出 Invalid/Blocked 条件。 |
| 8 | Requirement ID | 关联至少一条 TR。 |
| 9 | 优先级/阶段 | `P0/P1/P2` 和 `Smoke/Baseline/Steady/Stress/Recovery/Regression`。 |
| 10 | DUT/系统配置 | SSD 容量、固件、PCIe 链路、CPU、内存/显存、Windows 版本、电源计划、散热条件。 |
| 11 | 前置条件 | purge、空闲时间、驱动、数据目录、磁盘剩余空间、后台任务和温度初始范围。 |
| 12 | Workload 配置 | 模型、数据集、active range、块大小、读写比例、QD/threads、seed、是否 buffered/direct、并发进程。 |
| 13 | 执行模式 | `Native`（真实 mlperform）、`Scaled`（缩小数据/模型但保留形状）、`Trace`（逻辑调用录制）、`Replay`（按 trace 模拟）、`Hybrid`（应用 + ETW）。 |
| 14 | 监控与指标 | IOPS、带宽、P50/P95/P99/P99.9、CPU/内存、SSD SMART、温度、功耗、队列、错误、ETW。 |
| 15 | 证据输出 | JSON/CSV/ETL/SMART 快照/图表/checksum/配置快照/日志路径。 |
| 16 | 重复性 | 预设重复次数、种子、稳态窗口和结果离散度规则。 |
| 17 | Windows 状态 | `Native-Windows`、`Windows-Trace/Replay`、`Linux-Reference` 或 `Not Applicable`。 |
| 18 | 结果/偏差/缺陷 | 执行后填写，不在设计阶段预填通过。 |

### 3.3 Test Run Record（TRR）

每次实际执行单独生成一条运行记录，至少包含：

- `run_id`、Case ID、开始/结束时间、操作者、主机名、Git commit、脚本 hash。
- DUT 型号、序列号、固件、容量、PCIe 链路、namespace、文件系统和分区信息。
- Windows build、驱动版本、BIOS/UEFI、功耗计划、交流/电池状态、散热方案。
- 实际参数、实际数据量、seed、日志路径、工具版本和所有偏差。
- 预期值、实际值、判定、异常编号、重测/豁免批准人。

## 4. AI PC SSD 测试需求设计建议

### 4.1 需求类别

| 类别 | 目的 | 代表性需求 |
|---|---|---|
| 基线性能 | 建立 FOB 与稳态的可比数据 | 4 KiB 随机读写、1 MiB 顺序读写、混合读写、QD 扫描。 |
| AI workload 性能 | 验证真实应用访问模式 | 训练数据读取、checkpoint 写入/恢复、KV cache spill/reload、VDB insert/search。 |
| 一致性与数据完整性 | 防止缓存、flush、重启或长压导致数据错误 | checksum、write→flush→readback、fsynced 数据恢复、metadata/索引一致性。 |
| 热/功耗/降速 | 验证消费级 M.2 在有限散热下的持续行为 | sustained write/read、温度阈值、热降速、idle power、power state resume。 |
| 异常与恢复 | 验证系统在非正常事件后的可恢复性 | unsafe shutdown、重启、应用中断、设备 reset、namespace/文件系统恢复。 |
| 生命周期/耐久 | 观察写放大和健康度趋势 | 固定 TBW、Percentage Used、Data Units Written、Media/Data Integrity Errors。 |
| 可复现性 | 确保不同机器/固件/版本可比较 | 固定 seed、配置、脚本版本、环境快照、测量窗口和重复次数。 |
| 可追溯与回归 | 支持版本迭代和缺陷闭环 | 需求—用例—脚本—run—证据—缺陷双向追溯。 |

### 4.2 用例阶段

1. **Stage 0：Readiness / Inspection**：设备识别、固件、PCIe 链路、驱动、文件系统、SMART 初始快照、温度/功耗仪表就绪。
2. **Stage 1：Smoke**：小数据量、短时、无需稳态；只验证脚本、路径、日志、校验和基本读写。
3. **Stage 2：FOB Baseline**：Purge 后直接测短窗口，保留瞬态曲线，不把它当作典型性能。
4. **Stage 3：Preconditioned Steady-State**：WIPC + WDPC，按窗口判定稳态，再输出正式性能。
5. **Stage 4：AI Workload**：训练、checkpoint、KV、VDB 的 Native/Scaled workload；记录应用吞吐和 SSD 层指标。
6. **Stage 5：Thermal / Power**：持续负载、低功耗空闲、恢复延迟、功耗与温度趋势。
7. **Stage 6：Fault / Recovery / Integrity**：Flush、重启/unsafe shutdown、应用中断、校验和、索引/文件一致性、Sanitize。
8. **Stage 7：Regression / Trace Replay**：用固定 trace 和固定 seed 重跑，比较版本/固件/系统配置差异。

## 5. 测试步骤的推荐写法

步骤应短、可执行、可观察。推荐格式：

```text
1. 记录 DUT、系统和工具版本；采集 SMART 初始快照。
2. 清理或 purge DUT；确认温度、剩余空间和后台任务满足前置条件。
3. 使用固定 seed 和配置运行预处理；记录每轮 IOPS/带宽/延迟。
4. 按稳态规则确定测量窗口；连续执行正式负载并保存原始日志。
5. 采集 Windows counters、ETW、SMART 和温度/功耗数据。
6. 校验数据/索引/checkpoint；计算 P50/P95/P99/P99.9 和吞吐。
7. 按测试标准判定 Pass、Fail、Invalid 或 Blocked；记录偏差和证据路径。
```

禁止写法：

- “运行测试并观察结果”；
- “预热后测试”，但不说明预热定义；
- “性能满足要求”，但没有单位、窗口和容差；
- “Windows 可运行”，但不说明使用的是 Native、Trace/Replay 还是 Linux reference；
- 把预期值、实际值和判定混在同一段自由文本中。

## 6. 监控、判定和证据规则

### 6.1 必采集指标

| 层次 | 指标 |
|---|---|
| 应用层 | samples/s、checkpoint 秒数、tokens/s、query/s、应用 P50/P95/P99、错误率。 |
| I/O 层 | IOPS、吞吐、读写字节数、块大小、QD、队列长度、flush 次数、逻辑 I/O 延迟。 |
| SSD/NVMe | Critical Warning、Composite Temperature、WCTEMP/CCTEMP、Percentage Used、Data Units Read/Written、Host Commands、Controller Busy Time、Power Cycles、Unsafe Shutdowns、Media/Data Integrity Errors、Error Log Entries。 |
| Windows | Physical/LogicalDisk Avg Disk sec/Read/Write、Disk Bytes/sec、Disk Reads/Writes/sec、Disk Queue、进程 I/O、ETW Disk Service Time/IO Time、CPU/内存/GPU。 |
| 热/功耗 | SSD composite temperature、峰值/稳态温度、超阈时长、设备功耗、整机功耗、idle/resume latency。 |
| 完整性 | checksum mismatch、短写/读错误、文件大小、索引条目数、checkpoint manifest、恢复后可读性。 |

### 6.2 默认判定框架

除非具体 TR 另有更严格门限，建议采用：

1. **Pass**：工具返回成功；数据/索引/checkpoint 完整性校验通过；无 NVMe Critical Warning、Media/Data Integrity Error 或未解释错误增长；性能达到 TR 的平均/分位数/吞吐/时长门限；温度不超过 CCTEMP，或有已批准的受控降速判定。
2. **Fail**：任一强制条件不满足，或发生数据损坏、无法恢复、设备消失、未解释的 I/O 错误、持续超过临界温度/严重延迟。
3. **Invalid**：前置条件不满足、purge/稳态未完成、后台任务干扰、工具异常、参数漂移、日志缺失或脚本版本不一致；Invalid 不能算 Pass/Fail。
4. **Blocked**：环境/设备故障使测试无法执行；需记录阻塞原因、尝试、责任人和解除条件。
5. **Conditional**：达到性能目标但有已批准偏差（例如 Windows direct I/O 不可用、使用 scaled dataset、仅 trace/replay）；必须在报告中显式标记，不得与 Native 结果混合排名。

### 6.3 重复性和统计规则

- Smoke 至少 1 次；基线和 AI workload 至少 3 次；正式对比建议 5 次或固定五轮测量窗口。
- 每次重复使用相同 DUT 初始状态、seed、active range、参数和脚本版本；若不能重新 purge，必须说明状态继承。
- 报告平均值之外至少给出 P50/P95/P99/P99.9、最小/最大、标准差或变异系数；长时间 workload 追加每轮时间序列。
- 对稳态结果同时给出窗口内 max/min、平均值和线性拟合斜率；未达稳态时不得静默截取最好的一段。
- Windows 性能计数器写明采样周期；短时尖峰与持续异常分开判定。

## 7. Trace / Replay 的边界

| 模式 | 能验证什么 | 不能替代什么 | 文档标记 |
|---|---|---|---|
| Native | 真实 Windows + mlperform + 文件系统 + SSD 路径；可验证端到端应用时延和数据正确性。 | 需要大模型/大数据集时成本高；不适合跨机器直接比较底层 I/O。 | `Native-Windows` |
| Scaled | 保留 workload 形状、并发和访问顺序，缩小数据/模型以验证脚本和趋势。 | 不能据此宣称完整容量、稳态写放大或绝对性能。 | `Scaled-Windows` |
| Logical Trace | 记录应用层 insert/search/flush/load、大小、时间戳和对象/文件标识。 | 记录不到真实 NVMe 命令、文件系统缓存、索引内部 I/O 和设备热行为。 | `Trace-Logical` |
| Replay | 将 trace 按节奏映射到本地文件或盘，比较 Windows 文件系统/SSD 的读写响应。 | 不是原始应用的端到端结果；必须与 Native/ETW 结果分开。 | `Replay-Storage` |
| ETW/WPR | 捕获 Windows 内核/应用 Disk I/O、flush、进程、排队和 power events。 | 不提供应用语义；trace 本身可能有采集开销。 | `Hybrid-WPR` |

Trace case 必须保存：trace schema 版本、时间戳单位、逻辑操作类型、方向、请求大小、对象/文件标识、间隔时间、随机 seed、生成脚本 commit、原始 trace hash 和 replay 参数。

## 8. 推荐的 Excel 工作簿结构

新测试矩阵建议使用以下工作表，且保留用户要求的七列顺序：

1. **测试需求（TR）**：需求 ID、需求描述、验证方法、优先级、门限、理由、关联 case。
2. **核心测试用例（TC）**：前七列在最左侧；随后放配置、前置条件、执行模式、监控、证据、重复性、Windows 状态、结果字段。
3. **扩展/可选用例**：长时耐久、功耗、Sanitize、ETW、跨版本回归等不阻塞首轮的 case。
4. **配置基线**：P1/P2/P3 AI PC 档位、SSD 容量、内存/显存总量、模型/数据集、scaled 比例和配置理由。
5. **工具与脚本索引**：mlperform、fio、nvme-cli、WPR/WPA、PowerShell、trace_runner、replay 的版本和入口。
6. **监控与判定**：指标定义、采样周期、门限、异常等级、Pass/Fail/Invalid/Blocked/Conditional 规则。
7. **执行记录**：run_id、实际配置、开始结束时间、实际值、偏差、证据链接、缺陷编号和批准信息。
8. **追溯矩阵**：TR ↔ TC ↔ script ↔ run ↔ evidence ↔ defect 双向链接。

## 9. 对现有 AI SSD 方案的具体改造建议

1. 将现有“测试步骤”列全部改为 `1. 2. 3.` 短步骤；把前置条件、监控和判定拆成独立列。
2. 将每个 case 增加 Requirement ID，避免只有场景名而无法确认覆盖关系。
3. 将 `Native / Scaled / Trace / Replay / Hybrid` 作为独立执行模式，不再用“模拟”统称所有非 Native 运行。
4. 为训练、checkpoint、KV、VDB 各保留至少一个 P0 数据完整性/恢复 case，不要只测吞吐。
5. 为 P1/P2/P3（1TB/32GB、2TB/64GB、4TB/128GB）写明 active range、数据缩放和可执行边界；容量不足时标记 Scaled 或 Replay。
6. 在所有正式性能 case 前加入 Purge/Precondition/Steady-State 记录；在 Windows case 中加入 shipping configuration、驱动、电源计划和 ETW 证据。
7. 把 NVMe SMART/Health、Windows PhysicalDisk counters、应用日志和原始脚本输出统一放入每次 run 的证据目录，并计算 manifest/hash。
8. 将“测试标准”改为可判定的形式，例如：`P99 ≤ 20 ms；错误数=0；checksum mismatch=0；CCTEMP 超限=0；三次运行 CV ≤ 10%`，而不是“性能稳定”。

## 10. 来源索引

1. [SNIA SSS PTS v2.0.2 标准入口](https://www.snia.org/tech_activities/standards/curr_standards/pts)
2. [SNIA SSS PTS v2.0.1 revision 10 PDF](https://www.snia.org/sites/default/files/technical-work/pts/draft/SNIA-SSS-PTS-2.0.1-rev10.pdf)
3. [SNIA PTS Throughput Test](https://www.snia.org/forums/sssi/pts/tp)
4. [SNIA PTS Testing Service](https://www.snia.org/forums/sssi/ptstest)
5. [SNIA PTS WSAT](https://www.snia.org/forums/sssi/pts/wsat)
6. [NVM Express Base Specification 2.0a](https://nvmexpress.org/wp-content/uploads/NVMe-NVM-Express-2.0a-2021.07.26-Ratified.pdf)
7. [fio HOWTO](https://github.com/axboe/fio/blob/master/HOWTO.rst)
8. [Windows HLK System Client Testing Prerequisites](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/system-client-testing-prerequisites)
9. [Windows HLK Device.Storage Troubleshooting](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/troubleshooting-devicestorage-testing)
10. [Windows ETW / WPR / WPA](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/event-tracing-for-windows)
11. [Windows WPR built-in profiles](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/built-in-recording-profiles)
12. [Windows WPR/Xperf profiles](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/using-xperf-profiles)
13. [Windows storage performance troubleshooting](https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-performance-problems-in-windows)
14. [Windows Physical Disk performance history](https://learn.microsoft.com/en-us/windows-server/storage/storage-spaces/performance-history-for-drives)
15. [ISO/IEC/IEEE 29119-3:2021 Test Documentation](https://www.iso.org/standard/79429.html)
16. [NASA SWE-114 Software Test Procedures](https://swehb.nasa.gov/spaces/7150/pages/16449688/SWE-114%2B-%2BSoftware%2BTest%2BProcedures)
17. [NASA SWE-066 Perform Testing](https://swehb.nasa.gov/spaces/SWEHBVD/pages/102695449/SWE-066%2B-%2BPerform%2BTesting)
18. [NASA Systems Engineering Handbook](https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf)
19. [Microsoft NVMe SSD Testing Overview](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/nvme-ssd-testing-overview)
20. [Microsoft Device.Storage tests](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/device-storage-tests)
21. [Microsoft Disk Verification test](https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/f8f88b8a-ff9c-4cfb-9e95-6be2511e5510)
22. [JEDEC landing page（JESD218A 被 NVMe 规范引用）](https://www.jedec.org/)
