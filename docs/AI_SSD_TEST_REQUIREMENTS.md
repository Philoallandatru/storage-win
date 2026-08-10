# AI SSD 测试需求

版本：1.0  
适用平台：Windows；目标设备为被测 SSD（DUT）  
适用 workload：Training、Checkpointing、KV Cache、VectorDB，以及有明确编排依据的混合负载

## 1. 目标和结论边界

本测试套件用于回答“SSD 对 AI workload 的存储供给、尾延迟、持续性能和数据可靠性是否满足要求”，不用于替代真实 GPU 性能测试，也不把所有 workload 合并成一个不可解释的总分。

结果必须区分：

- `NATIVE`：直接运行仓库支持的真实 workload；
- `TRACE-CAPTURE`：在真实 workload 或正式 benchmark 中记录逻辑 I/O；
- `TRACE-REPLAY`：将已验证的逻辑 I/O 节奏回放到目标 SSD；
- `SCALED`：缩小了数据规模或模型形态，只能形成条件性结论。

Trace replay 可以隔离 SSD 能力，但不包含完整应用计算、数据库内部 WAL/索引/compaction 放大，因此不能冒充 Native 成绩。

## 2. 可追踪测试要求

### TR-AI-SSD-001：DUT 路径和身份必须可证明

- Source：`FULL_TEST_PLAN.xlsx` 的 `Case执行矩阵`/`完整覆盖索引`；`docs/AI_SSD_TEST_CASES_SUPPLEMENT.md` 的“最小证据包”。
- Requirement：数据、缓存、checkpoint、VectorDB 存储根目录必须映射到指定 DUT；结果目录和原始日志应放在非 DUT 文件系统。
- Test Objective：证明采集的 I/O 确实来自目标 SSD，而不是系统盘或页缓存。
- Preconditions：目标卷存在，DUT 型号/序列号/盘符已记录。
- Stimulus：执行目标 workload，并同步采集 PhysicalDisk/ETW 监控。
- Observability：路径 manifest、卷 GUID、物理盘映射、逻辑字节、物理读写字节。
- Pass Criteria：路径映射完整；结果目录与 DUT 分离；物理 I/O 在 workload 时间窗内大于 0。
- Negative/Boundary：路径不存在、数据与结果同盘、物理 I/O 为 0、监控采样缺失时为 `INVALID`。
- Priority：P0。Trace Tags：`DUT`、`path`、`physical-io`。

### TR-AI-SSD-002：容量和文件规模必须先通过门禁

- Source：仓库 `mlpstorage_py/rules/`、`mlpstorage_py/benchmarks/` 以及用户实际运行中出现的 `dataset.num_files_train >= 3500` 和 CAP-01 检查。
- Requirement：正式 workload 的文件数、checkpoint 数、向量数和工作集必须满足仓库最终配置与磁盘容量要求。
- Test Objective：防止把缩小数据集误报成正式成绩。
- Preconditions：已生成最终配置；空闲空间大于所需数据、临时文件和安全余量。
- Stimulus：执行 `datasize`/CAP-01 或等价原生门禁，再执行 `datagen`/run。
- Observability：required bytes、available bytes、文件数、对象数、工作集和 `dataset.num_files_train`。
- Pass Criteria：门禁通过且没有运行时 `INVALID`。
- Negative/Boundary：容量不足、文件数低于规则下限、使用 `whatif` 代替执行时为 `BLOCKED`/`INVALID`。
- Priority：P0。Trace Tags：`capacity`、`datasize`、`file-count`。

### TR-AI-SSD-003：运行环境必须按 workload 真实依赖准备

- Source：`AGENTS.md`、`pyproject.toml`、各 benchmark CLI 实现。
- Requirement：Windows 测试不强制要求 GPU；Training/Checkpointing 的 MPI、VectorDB 的 Milvus 服务、KV Cache 的 Python 依赖必须分别验证。
- Test Objective：区分缺少环境导致的 `BLOCKED` 与 SSD/workload 失败。
- Preconditions：venv 已激活或使用其 Python；MPI/外部服务状态已记录。
- Stimulus：执行针对 workload 的原生命令，不添加无依据的 Docker 参数。
- Observability：Python、`mpiexec`/`mpirun`、Milvus host/port、版本和依赖导入结果。
- Pass Criteria：所选 workload 的真实依赖满足；不要求不存在的 GPU。
- Negative/Boundary：MPI 不存在、Milvus 未 ready、依赖缺失时只记 `BLOCKED`，不记 `FAIL`。
- Priority：P0。Trace Tags：`Windows`、`MPI`、`Milvus`、`GPU-optional`。

### TR-AI-SSD-004：Training 必须证明持续供数

- Source：`FULL_TEST_PLAN.xlsx` Training Cases；`mlpstorage open training ...` CLI。
- Requirement：训练用例必须完成 datagen（如需要）和正式 run，并报告 AU、samples/s、逻辑/物理读取量和主机瓶颈。
- Test Objective：证明 SSD 读取行为会影响或支撑训练供给。
- Preconditions：模型和 accelerator 参数与最终配置一致；数据规模已通过 TR-AI-SSD-002。
- Stimulus：`mlpstorage open training <model> datagen/run file ...`。
- Observability：退出码、AU、samples/s、GiB/s、队列、CPU、物理读量和数据完整性。
- Pass Criteria：命令成功、数据校验通过、AU 达到该模型声明门槛；至少三次有效测量用于比较。
- Negative/Boundary：AU 未达标、训练文件不足、仅执行 `whatif`、物理读量为 0 时不得记 Native PASS。
- Priority：P0。Trace Tags：`training`、`AU`、`sustained-read`。

### TR-AI-SSD-005：Checkpoint 必须证明写入、恢复和完整性

- Source：`FULL_TEST_PLAN.xlsx` Checkpoint Cases；`mlpstorage open checkpointing run file ...`。
- Requirement：Checkpoint 用例必须覆盖保存、读取/恢复、最慢 rank、吞吐和 hash/大小一致性。
- Test Objective：证明大块并发写入和恢复不仅成功，而且数据正确。
- Preconditions：rank 数、模型形态、checkpoint 数量和容量均满足正式规模。
- Stimulus：原生 checkpointing run；cold/reboot 由执行环境明确提供，不能静默替换。
- Observability：每 rank 时间、读写字节、文件大小、hash、fsync、错误和 cold 物理读量。
- Pass Criteria：所有 rank 完成；恢复 hash 一致；零数据损坏和 I/O 错误。
- Negative/Boundary：容量不足、rank 缺失、只写不恢复、无法证明 cold 时为 `NOT RUN`/`INVALID`。
- Priority：P0。Trace Tags：`checkpoint`、`restore`、`integrity`。

### TR-AI-SSD-006：KV Cache 必须证明 Tier-2 真正承载 I/O

- Source：`mlpstorage_py/cli/kvcache_args.py`、`kv_cache_benchmark/kv_cache/tracer.py` 和 KV benchmark 输出。
- Requirement：KV 用例必须报告 Tier-2 bytes、读写方向、users、P95/P99/P99.9/P99.99 和 QoS；内存不能吸收全部流量后仍称 SSD 测试。
- Test Objective：证明 KV cache 发生了实际 SSD offload，并量化尾延迟。
- Preconditions：cache-dir 在 DUT；GPU/CPU tier 配置和模型固定。
- Stimulus：`mlpstorage open kvcache run ...`；必要时使用 `--gpu-mem-gb 0 --cpu-mem-gb 0` 强制 Tier-2 压力。
- Observability：Tier-2 read/write bytes、storage entries、eviction、P99、requests/s、OOM/error。
- Pass Criteria：Tier-2 bytes > 0；所有 trial 有结果；无数据丢失和 I/O error；QoS 门槛按 case 判定。
- Negative/Boundary：Tier-2 bytes=0、内存吸收全部流量时为 `INVALID`；底层 KV tracer 虽支持 `--io-trace-log`，但当前 `mlpstorage open kvcache` 未暴露该参数，不能把它登记为当前可执行 case，也不能把 capture 单独当作 SSD 结果。
- Priority：P0。Trace Tags：`kvcache`、`Tier-2`、`tail-latency`。

### TR-AI-SSD-007：VectorDB 必须同时通过质量和性能

- Source：`vdb_benchmark/TRACE_REPLAY.md`、`vdb_benchmark/vdbbench/trace_runner.py`、`mlpstorage open vectordb ...`。
- Requirement：VectorDB 必须固定数据、seed、metric、top-k 和 query 集，在 Recall 达标后比较 QPS/P99；必须验证 row count。
- Test Objective：避免用降低搜索质量换取虚假吞吐。
- Preconditions：Milvus 服务可访问；collection、storage-root 和 results-dir 映射已记录。
- Stimulus：原生 datagen/run 或正式 `vdbbench-modular --io-trace-log`。
- Observability：row count、Recall@K、QPS、P50/P99、索引/加载时间、物理 I/O 和 trace phase。
- Pass Criteria：Recall/row count 正确，服务无错误；性能结果可重复。
- Negative/Boundary：Milvus 未 ready、query 集不一致、空 trace、对象缺失、物理路径不明时为 `BLOCKED`/`INVALID`。
- Priority：P0。Trace Tags：`vectordb`、`Milvus`、`Recall`、`QPS`。

### TR-AI-SSD-008：VectorDB Trace Capture 必须来自正式 workload

- Source：`vdb_benchmark/TRACE_REPLAY.md` 和 `vdbbench-modular --io-trace-log`。
- Requirement：Capture 必须记录真实 Milvus Insert、Flush、Load、Search 的逻辑操作和节奏；不能用手工 CSV 冒充来源。
- Test Objective：生成可迁移、可校验的 AI I/O trace。
- Preconditions：真实 Milvus 服务 healthy；正式 config 和 trace path 固定。
- Stimulus：`vdbbench-modular --config ... --io-trace-log ... --output-dir ...`。
- Observability：trace header、event count、phase、时间顺序、逻辑字节、source command 和 config hash。
- Pass Criteria：trace 非空、时间不倒退、包含声明 phase、source benchmark 成功。
- Negative/Boundary：仅 `what-if`、空 trace、时间倒退或只记录应用推测而无 source run 时不得形成正式 trace。
- Priority：P0。Trace Tags：`trace-capture`、`source-run`。

### TR-AI-SSD-009：Trace Replay 必须保持可解释的 I/O 形态

- Source：`vdb_benchmark/vdbbench/replay.py`、`vdb_benchmark/TRACE_REPLAY.md`。
- Requirement：Replay 必须保留操作顺序、对象大小、读写方向和可选时间间隔；direct-I/O 时必须报告 sector padding 后 device bytes。
- Test Objective：在另一台 Windows 机器上重现同一 SSD 压力。
- Preconditions：trace manifest/hash 已校验；回放目录位于 DUT；结果目录不在 DUT。
- Stimulus：`python -m vdbbench.replay <trace> --data-dir <DUT_DIR> --direct-io`。
- Observability：operation count、read/write bytes、P50/P95/P99、wall/active throughput、device bytes、errors。
- Pass Criteria：所有 event 成功；对象依赖满足；结果包含 direct/buffered 模式和 trace hash。
- Negative/Boundary：对象 key 越界、读无先前对象、trace header 不匹配、时间倒退时为 `INVALID`。
- Priority：P0。Trace Tags：`trace-replay`、`direct-io`、`device-bytes`。

### TR-AI-SSD-010：Native、Trace 和 Scaled 结果必须分开

- Source：本仓库 `full_test_plan_cases` 与 `vdb_benchmark/TRACE_REPLAY.md` 的执行边界。
- Requirement：报告必须标明 execution mode、规模、source trace、是否包含应用/数据库内部 I/O。
- Test Objective：保证跨机器、跨 SSD 的结论可比较且不过度外推。
- Pass Criteria：没有把 `whatif`、dry-run、scaled 或 replay 标成 Native PASS。
- Negative/Boundary：模式缺失、trace hash 缺失、缩放比例缺失时为 `INVALID`。
- Priority：P0。Trace Tags：`verdict`、`provenance`。

### TR-AI-SSD-011：结果必须可重复且有最小证据包

- Source：`docs/AI_SSD_TEST_CASES_SUPPLEMENT.md` “最小证据包”。
- Requirement：正式配置至少进行三次有效测量；保留 manifest、最终配置、原始日志、监控、正确性报告和 verdict。
- Pass Criteria：参数、seed、DUT 身份和时间窗口可重建；异常有明确归因。
- Negative/Boundary：单次运行、无监控、无原始日志或结果目录覆盖 DUT 时只能记 `CONDITIONAL`/`INVALID`。
- Priority：P0。Trace Tags：`repeatability`、`evidence`。

### TR-AI-SSD-012：测试数据必须在 case 结束后清理

- Source：本项目 Windows 执行约定和用户测试要求。
- Requirement：每个 case 使用唯一临时数据根目录；case 结束后删除该目录，结果证据和输入 trace 按保留策略单独保存。
- Test Objective：避免测试数据持续占满磁盘并污染后续 case。
- Preconditions：清理目录由 manifest 明确列出，且在 DUT 测试根目录内。
- Stimulus：case 的 finally/收尾步骤执行精确路径清理，并复核目录不存在。
- Pass Criteria：测试数据目录不存在；不删除用户未授权目录、results 或源 trace。
- Negative/Boundary：路径不在批准根目录、清理失败或存在占用文件时，测试状态不得伪造为 PASS。
- Priority：P0。Trace Tags：`cleanup`、`retention`。

## 3. 状态定义

| 状态 | 含义 |
|---|---|
| `PASS` | 真实 workload/trace replay 完成，正确性、路径、证据和 case 门槛均通过 |
| `FAIL` | 真实执行完成，但性能、QoS、Recall、完整性或稳定性失败 |
| `BLOCKED` | 依赖、容量、外部服务或平台条件不满足，尚未执行 workload |
| `INVALID` | 参数、路径、trace、证据或规模不满足测试定义 |
| `CONDITIONAL` | scaled、trace replay 或其他明确限制下通过，只能形成条件性结论 |
| `NOT RUN` | 已识别但本机未执行，不得写成通过或失败 |
