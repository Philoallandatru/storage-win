# AI SSD 测试矩阵：主来源清单

更新日期：2026-08-02

本文只收录标准组织、规范维护方和平台厂商的一手资料。建议将测试矩阵分为四层：NVMe 协议功能、数据中心可靠性、稳态设备性能、AI 应用表现。发布报告时冻结规范 revision、工具 release/tag、SSD 固件、驱动、OS、文件系统、LBA 格式、容量、功耗状态和测试配置。

## 1. NVMe 协议与管理

### NVM Express Base Specification 2.3

- 官方版本：[NVMe Base Specification 2.3，2025-08-01 Ratified（PDF）](https://nvmexpress.org/wp-content/uploads/NVM-Express-Base-Specification-Revision-2.3-2025.08.01-Ratified.pdf)
- 官方入口：[NVM Express Base Specification](https://nvmexpress.org/specification/nvm-express-base-specification/)
- 矩阵贡献：Identify、队列和控制器管理、Get Log Page、SMART/Health 02h、Error Information、Telemetry、Persistent Event Log、Device Self-test、Format、Sanitize、固件、复位与关机语义。
- 可执行要求：覆盖正常和非法命令、边界 LBA、controller/subsystem/PCIe reset、normal/abrupt shutdown；每次用例前后采集 Identify、SMART、Error Log，故障时追加 PEL、Telemetry 和自检日志。
- 建议判定：无非预期超时、复位、掉盘或只读切换；声明支持的功能响应正确；日志与注入事件一致；无新增非预期 Critical Warning 或 Media/Data Integrity Error。
- 注意：Base 规范主要定义控制器和管理接口，块 I/O 命令应同时引用 NVM Command Set。

### NVM Command Set Specification 1.2

- 官方版本：[NVM Command Set Specification 1.2](https://nvmexpress.org/specification/nvm-command-set-specification/)
- 矩阵贡献：Read、Write、Flush、Compare、Dataset Management/Deallocate、Write Zeroes、Protection Information 等块 I/O 行为。
- 可执行要求：覆盖支持的 LBA 格式、block size、alignment、首尾 LBA、队列深度和读写混合；将 command completion、FUA/Flush 边界与断电验证关联。
- 注意：通过文件 API 的写入成功不等于已经满足 NVMe 持久化边界；PLP 必须基于命令语义和真实掉电验证。

### NVM Express 官方管理与故障资料

- [NVMe-CLI 官方说明](https://nvmexpress.org/open-source-nvme-ssd-management-utility-nvme-command-line-interface-nvme-cli/)
- [NVMe 1.4 变更：Persistent Event Log](https://nvmexpress.org/changes-in-nvme-revision-1-4/)
- [How SSDs Fail：错误报告与日志](https://nvmexpress.org/how-ssds-fail-nvme-ssd-management-error-reporting-and-logging-capabilities/)
- 矩阵贡献：定义现场证据包的最小内容；PEL 可保留电源/复位、硬件错误、固件、Format/Sanitize、Telemetry 和热事件。
- 注意：这些说明用于解释和实施，规范 PDF 才是正式判定依据。

## 2. 数据中心可靠性：OCP Datacenter NVMe SSD 2.7

- 官方版本：[OCP Datacenter NVMe SSD Specification 2.7，2026-01-08 Final（PDF）](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1)
- 矩阵贡献：PLP、端到端数据完整性、启动/恢复时间、扩展 SMART C0h、Telemetry Profile、耐久与保持、功耗和热，是 AI SSD 可靠性主门禁。

关键可执行要求：

- **PLP-1…9**：所有已经确认的用户数据和元数据都应受保护。持续写入包含 LBA、generation、sequence、payload 和 CRC 的记录，在不同负载、GC/稳态、温度阶段随机切断 SSD 主电源；冷启动后逐 LBA 验证。通过条件为零已确认数据丢失、零 torn write、wrong/stale LBA 和 silent corruption。PLP 健康检查不得损害 I/O 性能，并应在允许写入前和周期内执行；默认周期为 15 分钟。
- **E2E-1…7**：寄存器、cache、SRAM、DRAM、NAND 路径需有重叠保护，DRAM 至少 SECDED，不允许 silent corruption。矩阵应跨 LBA 格式、PI/DIX、block size、QD、reset、掉电、温度和磨损阶段执行 checksum scrub。
- **TTR**：除 Profile 例外，`CC.EN=1` 后 1 秒内可 Identify，20 秒内可处理介质 I/O/Admin；正常 shutdown 不超过 10 秒；意外掉电后的 metadata rebuild 不超过 120 秒，然后恢复延迟要求。
- **UBER-1**：产品目标 `<1 sector/10^18 bits read`；物理测试至少按 JESD218B 证明 `<1 sector/10^17 bits read`。短时零错误 soak 不能宣称满足 UBER。作为统计推论，零失效且 95% 置信度证明 `<10^-17` 约需读取 `3×10^17` bit（约 37.5 PB）；正式合规仍需标准方法和供应商证据。
- **SLOG/SMART/Telemetry**：02h/C0h 日志读取不应阻塞 I/O；后台字段至少每十分钟更新，温度在读取时更新。用 Host/Physical Media Units Written 计算 WAF，并验证计数器单位、单调性和跨复位持久性。
- **ENDUD/RETC**：EOL 预处理采用 50/50 R/W、4 KiB 随机读、128 KiB 顺序写、100% active range、80% full、不可压缩数据、35°C；Percentage Used 应与写入量线性对应。EOL、40°C 断电保持至少一个月；通电保持要求按规范/Profile。此类破坏性、长周期项目需用专用样盘。
- **Power/Thermal**：用外部功率分析仪作为主证，SMART 为辅；各功耗状态下记录平均/峰值功耗、IOPS/W、GB/s/W、完整尾延迟、温度、节流进入/退出和恢复时间。要求功率不越界、事件可观测、状态切换期间零数据错误和掉盘。

注意：OCP 条款可能按设备 Profile 给出例外或更严门槛，测试计划必须记录适用 Profile；不要把通用摘要替代逐条符合性审查。

## 3. 稳态设备性能：SNIA SSS PTS 2.0.2

- 官方版本：[SNIA Solid State Storage Performance Test Specification 2.0.2，2020-10-01（PDF）](https://www.snia.org/sites/default/files/2025-02/SNIA-SSS-PTS-2.0.2.pdf)
- 官方入口：[SNIA Solid State Storage](https://www.snia.org/solid-state-sss)
- 矩阵贡献：提供可重复的裸盘性能流程：`Purge → workload-independent preconditioning → workload-dependent preconditioning → steady state → measurement window → report`，防止把新盘缓存峰值当成持续性能。

应保留的标准用例：

| 用例 | 标准刺激 | 关键输出 |
|---|---|---|
| IOPS | 7 个 R/W mix × 8 个随机 block size；PTS-E 为 100% active range，建议 QD32、4 threads | IOPS 矩阵、延迟、CPU、功耗 |
| Throughput | 128 KiB、1024 KiB 顺序读写，单线程 | 稳态 MB/s |
| Latency | QD1；0.5/4/8 KiB；100R、65/35、100W | 平均、99.999%、最大、直方图 |
| Write Saturation | Purge 后持续 4 KiB 随机写，直到 4×容量、6 小时或稳态 | 峰值、transition、稳态、响应时间尖峰 |

- 稳态 measurement window 为连续五轮；窗口范围在平均值 ±10% 内，线性拟合斜率不超过 10%。未达到稳态可以报告，但必须明确标识。
- AI 专项可增加 16/64/128 KiB、1 MiB，QD 1/8/32/128，95/5、70/30、50/50、30/70，但不得静默修改或替代标准矩阵。
- 注意：SNIA PTS 规定的是方法和报告口径，不为具体产品给出 IOPS/带宽合格线；性能门槛应来自 datasheet/SOW 或项目 SLO。

## 4. AI 应用层：MLPerf Storage

- 官方基准入口：[MLPerf Storage](https://mlcommons.org/benchmarks/storage/)
- 官方参考实现：[mlcommons/storage](https://github.com/mlcommons/storage)
- 官方规则：[Rules.md](https://github.com/mlcommons/storage/blob/main/Rules.md)
- Checkpoint 官方说明：[MLPerf Storage v2.0 Checkpointing，2025-08](https://mlcommons.org/2025/08/storage-2-checkpointing/)
- 矩阵贡献：把设备性能映射到训练数据读取、Checkpoint、VectorDB 和 KV Cache 的应用吞吐、尾延迟与正确性。

| 场景 | 主要指标 | SSD 联合监控与判定重点 |
|---|---|---|
| Training | samples/s、MB/s、accelerator utilization/可支持 accelerator 数 | 带宽、IOPS、尾延迟、队列、CPU wait、缓存状态；规则校验通过且满足项目规模目标 |
| Checkpoint | Save/Load GiB/s、最慢进程完成时间 | 10 次 Save + 10 次 Load；本地 NVMe subset 为 8 processes；必要时清文件缓存；关注 flush、WAF、GC、P99.9 与 RPO/RTO |
| VectorDB | QPS、Recall@k、mean/P95/P99/P99.9、build/load 时间 | FLAT ground truth 在计时循环外；固定 index、query/search 参数和 cache state；Recall 达标后比较 QPS/尾延迟 |
| KV Cache | tokens/s、读写 GiB/s、较差实例的 device P95 | 记录对象大小、并发、读写比、fsync、eviction；确认真实访问 SSD |

注意：仓库 `main` 持续变化，VectorDB/KV Cache 也可能处于预览或演进状态。可比测试必须固定 release/tag、commit、规则和 workload 定义。应用 POSIX 延迟不等于 NVMe command latency；逻辑 trace replay 能复现请求大小、顺序和节奏，但不能替代真实引擎的物理 I/O，也不能证明 PLP/OCP 合规。

## 5. Windows 证据采集边界

- [Microsoft DiskSpd](https://github.com/microsoft/diskspd)：Windows 官方开源存储负载生成器，可用于文件、分区或物理设备上的线程、Outstanding I/O、block size、读写比、随机/顺序、write-through 和 software/hardware cache 控制；版本和完整参数必须写入 manifest。
- [Microsoft Get-StorageReliabilityCounter](https://learn.microsoft.com/en-us/powershell/module/storage/get-storagereliabilitycounter?view=windowsserver2025-ps)：温度、磨损、power-on hours 和读写错误等宿主可见可靠性数据。
- [Microsoft Windows 磁盘性能计数器](https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-performance-problems-in-windows)：读写 B/s、IOPS、平均延迟、队列长度及主机 CPU/内存关联监控。
- [Microsoft File Buffering](https://learn.microsoft.com/en-us/windows/win32/fileio/file-buffering)：`FILE_FLAG_NO_BUFFERING` 的缓存与对齐规则。
- [Microsoft FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers)：文件缓冲刷写语义。

可执行含义：Windows replay 应显式记录 buffered/direct、write-through、flush、buffer/offset/length alignment；同时采集进程逐 I/O 直方图和 PhysicalDisk 指标。Windows 原生可靠性计数器不是 OCP C0h、PEL 和 Telemetry 的完整替代品；若 inbox 驱动不暴露原始日志，应使用供应商工具、NVMe pass-through、BMC/NVMe-MI，或在同一硬件上用 Linux `nvme-cli` 补齐合规证据。

## 6. 测试矩阵落地规则

每项阈值必须标注来源类型：

1. **Normative**：NVMe/OCP/SNIA/MLPerf 明确规定的行为、流程或数值，例如零 silent corruption、OCP TTR、SNIA 稳态条件。
2. **Contractual**：datasheet/SOW 声明的 TBW、DWPD、IOPS、吞吐、P99、功率和保持期。
3. **Regression/SLO**：产品自定的 VDB QPS@Recall、KV P95、Checkpoint RTO 或老化后允许退化比例。

可靠性和数据完整性是硬门禁，不能用更高吞吐抵消。性能结果只有在配置冻结、预处理和稳态成立、数据校验通过、日志无非预期错误且温度/功率在范围内时才有效。每次 run 至少保留 run/case ID、DUT 序列号、固件与平台配置、完整命令和 seed、原始延迟直方图、预处理/稳态证据、SMART/错误/PEL/Telemetry、功耗温度时序、注入时间戳、CRC/sequence 结果和自动判定依据。
