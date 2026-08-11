# MLPerf Storage 测试项原理与执行流程（中文说明）

> 适用代码版本：当前仓库 `mlpstorage 3.0.46`  
> 核对日期：2026-08-10  
> 范围：Training、Checkpointing、KV Cache、VectorDB，以及形成测试结果所需的公共命令与校验流程

## 1. MLPerf Storage 到底测什么

MLPerf Storage 不运行完整的模型训练或推理，而是复现 AI 工作负载对存储系统产生的关键 I/O 行为，用于回答以下问题：

- 存储能否按目标速率持续向训练任务供数；
- 大模型 checkpoint 能否及时写入稳定存储，并在故障恢复时快速读回；
- LLM KV Cache 溢出到 SSD 后，吞吐和尾延迟是否满足要求；
- VectorDB 在真实数据装载、建索引和近邻查询时能达到怎样的 QPS、Recall 和延迟。

当前套件包含四类 workload：

| 测试项 | 被模拟或驱动的业务 | 主要存储方向 | 核心指标 |
|---|---|---|---|
| Training | AI 训练数据加载 | 以读为主 | samples/s、Accelerator Utilization（AU） |
| Checkpointing | 大模型保存与故障恢复 | 顺序/并行写和读 | 最慢 rank 时间、最小 rank 吞吐 |
| KV Cache | LLM 推理 KV Cache 分层与溢出 | Prefill 写、Decode 读 | tokens/s、读写带宽、P95 读延迟 |
| VectorDB | RAG 场景的向量装载、索引与 ANN 查询 | 写入、索引构建、随机查询 | QPS、Recall@K、P50/P95/P99 |

来源：[项目总览](../README.md)、[提交指南](../Submission_guidelines.md)、[MLCommons Storage 仓库](https://github.com/mlcommons/storage)。

## 2. 先理解三种运行模式

每条 benchmark 命令都必须以运行模式开头：

| 模式 | 含义 | 能否作为正式提交结果 |
|---|---|---|
| `closed` | 固定 workload 和大部分参数，强调不同厂商结果可比 | 可以，前提是满足全部规则 |
| `open` | 允许更多调优，但必须披露修改 | 可以，但只能在 OPEN 范围比较 |
| `whatif` | 容量估算、研发实验和非标准模型探索 | 不可以 |

`--dry-run`、`datasize` 和 `configview` 也不会产生正式性能成绩：它们分别用于查看命令、计算容量和检查最终配置。

规则来源：[Rules.md](../Rules.md)、[README.md 的 CLI 与 Theory of Operations](../README.md)。

## 3. 当前 3.0.46 CLI 的参数位置

仓库部分历史 README 仍保留旧版命令示例。执行时应以当前 `mlpstorage --help_all` 和各层 `--help` 为准。

| 测试项 | 当前命令形态 |
|---|---|
| Training | `mlpstorage <mode> training <model> <command> [file|object] ...` |
| Checkpointing | `mlpstorage <mode> checkpointing <command> [file|object] --model <model> ...` |
| KV Cache | `mlpstorage <mode> kvcache <datasize|run> ...`；CLOSED 不传模型 |
| VectorDB | `mlpstorage <mode> vectordb <command> [file|object] --vdb-index <index> ...` |

`file` 表示通过文件系统路径访问本地盘、远程块设备、NAS 或并行文件系统；`object` 表示通过 S3 兼容接口访问对象存储。`datasize` 不触碰工作负载数据，因此没有该位置参数；KV Cache 也不使用该位置参数。

实现来源：[cli_parser.py](../mlpstorage_py/cli_parser.py)、[training_args.py](../mlpstorage_py/cli/training_args.py)、[checkpointing_args.py](../mlpstorage_py/cli/checkpointing_args.py)、[kvcache_args.py](../mlpstorage_py/cli/kvcache_args.py)、[vectordb_args.py](../mlpstorage_py/cli/vectordb_args.py)。

## 4. 四类测试共用的实现框架

### 4.1 公共组件

`mlpstorage` 是统一编排层，真正生成压力的引擎因测试项而不同：

| 测试项 | 底层执行引擎 |
|---|---|
| Training | DLIO Benchmark |
| Checkpointing | DLIO + Streaming Checkpointing |
| KV Cache | `kv-cache.py`，由 `mlperf_wrapper.py` 和 MPI 启动 |
| VectorDB | `vdbbench` / `enhanced-bench`，连接真实 Milvus |

公共基类负责结果目录、集群信息、容量门禁、文件系统隔离、时序监控、元数据和日志；各 benchmark 子类只负责构造本测试项的原生命令、执行和聚合。

### 4.2 一次命令的公共执行流程

```text
解析 mode / benchmark / command / 参数
          ↓
读取 YAML、CLI 和环境变量并形成最终配置
          ↓
CLOSED / OPEN 参数规则校验
          ↓
环境依赖、MPI、SSH、路径、lockfile 校验
          ↓
捕获/校验代码镜像，预留本次结果目录
          ↓
采集运行前集群信息
          ↓
CAP-01 容量门禁、CAP-02 共享路径门禁、CAP-03 数据/结果盘隔离门禁
          ↓
启动时序监控并执行具体 workload
          ↓
聚合 rank / trial 结果，写 stdout、stderr、summary、metadata
          ↓
采集运行后集群信息，停止监控，返回退出码
```

几个重要边界：

- 容量不足会在正式 workload 前失败，这种情况是“未运行/被阻断”，不是 SSD 性能失败；
- `data-dir`、`checkpoint-folder` 或 `cache-dir` 应位于被测存储，`results-dir` 应位于另一文件系统，避免结果写入污染被测盘和页缓存；
- 多机测试要求数据路径和结果路径在所有参与主机上以相同路径可见；
- 命令退出码为 0 仍不自动等于有效成绩，还要检查规则状态、结果完整性和业务指标。

实现来源：[main.py](../mlpstorage_py/main.py)、[Benchmark 基类](../mlpstorage_py/benchmarks/base.py)、[DLIO 编排](../mlpstorage_py/benchmarks/dlio.py)。

## 5. Training 测试

### 5.1 测试目的

Training 测试衡量存储持续供应训练样本的能力。它保留真实数据加载、解码/预处理、预取和多进程同步，但不执行神经网络计算。

DLIO 为每个模拟加速器启动数据加载流程。读取一个 batch 后，本应由 GPU 执行的计算被一个经过真实硬件测量后确定的 `sleep()` 替代。这样可以在没有 GPU 的主机上复现“读数据—计算间隔—再读数据”的节奏。

因此：

- 不需要安装真实 B200/MI355；
- `--accelerator-type` 表示要模拟的 I/O 速率和计算间隔，不表示使用本机 GPU；
- 提高模拟加速器数量会缩短存储的喘息空间并增加并行 I/O 压力。

原理来源：[Training README：Theory of Operations](../training/README.md)、[官方提交指南 Training 部分](../Submission_guidelines.md)。

### 5.2 当前 workload

| 模型 | 当前可提交组合 | 典型数据特征 | 最低 AU |
|---|---|---|---|
| UNet3D | B200 | 较大的 3D 医学影像样本，吞吐型读取 | 90% |
| RetinaNet | B200、MI355 | 大量目标检测样本，对文件数和元数据更敏感 | 85% |

CosmoFlow、ResNet50、DLRM、Flux 等配置在当前树中主要用于 `whatif`，不能自动当作 v3.0 CLOSED/OPEN 正式结果。

### 5.3 `datasize`：先算需要多少数据

Training 为避免整个数据集被客户端内存缓存，要求数据规模同时满足两个下限：

```text
按步数下限计算的样本数
  = 至少 500 steps × batch size × 全部模拟加速器数

按内存下限计算的样本数
  = 主机数 × 每主机内存 × 5 ÷ 单样本大小

最终最小样本数 = max(上述两个值)
```

工具再根据每个文件包含的样本数换算为文件数、子目录数和总字节数。`datasize` 只做计算，不读取 SSD，也不是性能测试。

示例：

```powershell
mlpstorage closed training unet3d datasize `
  --accelerator-type b200 `
  --max-accelerators 1 `
  --client-host-memory-in-gb 64 `
  --results-dir C:\MLPerfResults `
  --systemname storage-system
```

### 5.4 `datagen`：生成合成数据

`datagen` 使用 `<model>_datagen.yaml` 调用 DLIO，在目标 `data-dir/<model>/train|valid|test` 下生成与真实 workload 相同文件格式、样本大小和目录结构的合成数据。

执行流程：

1. 读取模型 datagen YAML 和 `--params`；
2. 检查目标盘容量；
3. 用 MPI 启动指定数量的生成进程；
4. 各 rank 分配文件区间并写入合成样本；
5. DLIO 写生成日志；
6. `mlpstorage` 检查输出叶目录是否完整；
7. 成功后写 datagen manifest，供正式 run 核对。

```powershell
mlpstorage closed training unet3d datagen file `
  --num-processes 1 `
  --data-dir D:\MLPerfData `
  --results-dir C:\MLPerfResults `
  --systemname storage-system `
  --exec-type mpi --mpi-bin mpiexec `
  --params dataset.num_files_train=<DATASIZE输出值>
```

`datagen` 会大量写盘，但它是测试准备阶段，不是 Training 读取性能成绩。

### 5.5 `configview`：检查最终配置

`configview` 生成最终 DLIO 命令和配置视图，但不执行 workload。它用于确认：

- 模型、加速器和 YAML 是否匹配；
- `dataset.num_files_train` 是否仍满足规则；
- 数据路径是否指向 DUT；
- reader 线程、prefetch、O_DIRECT 和格式参数是否符合 CLOSED/OPEN 约束。

### 5.6 `run`：正式读取测试

```powershell
mlpstorage closed training unet3d run file `
  --num-accelerators 1 `
  --accelerator-type b200 `
  --client-host-memory-in-gb 64 `
  --data-dir D:\MLPerfData `
  --results-dir C:\MLPerfResults `
  --systemname storage-system `
  --exec-type mpi --mpi-bin mpiexec `
  --params dataset.num_files_train=<DATASIZE输出值>
```

内部流程：

1. 加载 `<model>_<accelerator>.yaml`；
2. 验证文件数量、数据集规模和 CLOSED/OPEN 参数；
3. 启动一个或多个 DLIO rank，模拟对应数量的 accelerator；
4. 每个 rank 循环读取 batch，并用 sleep 模拟计算时间；
5. 多机数据并行在 step 边界同步，最慢客户端会拖慢整体；
6. DLIO 输出吞吐、AU 和 `summary.json`；
7. `mlpstorage` 检查必要结果文件，缺失时即使子进程返回 0 也判失败。

### 5.7 结果如何解释

- 主指标是 samples/s，越高越好；
- 成绩必须同时达到该 workload 的最低 AU；
- `AU = 模拟计算时间 / benchmark 总时间 × 100%`；
- 第一个 step 不进入 AU 计算，以降低启动开销影响，但其 I/O 仍计入吞吐；
- AU 低通常说明数据供应跟不上模拟计算节奏，不能只看 samples/s 宣称通过。

来源：[Training README](../training/README.md)、[TrainingBenchmark 实现](../mlpstorage_py/benchmarks/dlio.py)、[DLIO workload 配置](../configs/dlio/workload)。

## 6. Checkpointing 测试

### 6.1 测试目的

Checkpointing 测试模拟大模型训练期间保存模型/优化器状态，以及故障后从稳定存储恢复状态。它测的是存储读写，不执行 LLM 训练，也不需要 GPU。

当前模型规模和 CLOSED 总进程数：

| 模型 | CLOSED 进程数 | 完整 checkpoint 约值 | 8-rank subset 约值 |
|---|---:|---:|---:|
| Llama3 8B | 8 | 105 GB | 105 GB |
| Llama3 70B | 64 | 912 GB | 114 GB |
| Llama3 405B | 512 | 5.29 TB | 94 GB |
| Llama3 1T | 1024 | 18 TB | 161 GB |

### 6.2 default 与 subset 的实现

- `default`：用于共享存储，按模型规定的全部 TP×PP×DP rank 写完整 checkpoint；
- `subset`：用于节点本地存储，以 8 个 rank 写对应模型的一部分 checkpoint，复现单节点承担的局部压力。

当前实现根据 `--num-processes` 是否小于该模型完整进程数自动注入 `checkpoint.mode=subset`，不是单独传一个 `--subset` 开关。

### 6.3 `datasize`

工具根据模型参数、优化器状态、ZeRO 级别、模型并行和数据并行，计算每个 rank 应写入的 GiB，以及全部 rank 的总空间。该结果也是运行前容量门禁的依据。

```powershell
mlpstorage closed checkpointing datasize `
  --model llama3-8b `
  --num-processes 8 `
  --client-host-memory-in-gb 64 `
  --results-dir C:\MLPerfResults `
  --systemname storage-system
```

### 6.4 正式写入与恢复流程

规则要求的逻辑顺序是：

```text
写 10 个 checkpoint
       ↓
如有必要，清除客户端文件页缓存或完成存储卷 remap
       ↓
读回 10 个 checkpoint
```

写入阶段启用 `fsync`，确保数据落到稳定存储，而不是只停留在页缓存。若 checkpoint 在写入后不能立即被其他主机读取，卷 remap、复制或其他准备时间必须纳入恢复时间。

可以一次调用完成 10 写 + 10 读：

```powershell
mlpstorage closed checkpointing run file `
  --model llama3-8b `
  --num-processes 8 `
  --client-host-memory-in-gb 64 `
  --checkpoint-folder D:\MLPerfCheckpoint `
  --num-checkpoints-write 10 `
  --num-checkpoints-read 10 `
  --results-dir C:\MLPerfResults `
  --systemname storage-system `
  --exec-type mpi --mpi-bin mpiexec
```

如果必须在写和读之间清缓存，应拆成两个原生命令：

```powershell
# 先写
mlpstorage closed checkpointing run file `
  --model llama3-8b --num-processes 8 `
  --client-host-memory-in-gb 64 `
  --checkpoint-folder D:\MLPerfCheckpoint `
  --num-checkpoints-write 10 --num-checkpoints-read 0 `
  --results-dir C:\MLPerfResults --systemname storage-system `
  --exec-type mpi --mpi-bin mpiexec

# 在工具外完成经过验证的 cache clear/remap，再读
mlpstorage closed checkpointing run file `
  --model llama3-8b --num-processes 8 `
  --client-host-memory-in-gb 64 `
  --checkpoint-folder D:\MLPerfCheckpoint `
  --num-checkpoints-write 0 --num-checkpoints-read 10 `
  --results-dir C:\MLPerfResults --systemname storage-system `
  --exec-type mpi --mpi-bin mpiexec
```

在 Windows 上不能照抄 Linux 的 `echo 3 > /proc/sys/vm/drop_caches`。需要使用可审计的重启、卷卸载/重新挂载、受支持的缓存控制方法，或者使用经过验证的 direct-I/O 流程；具体方法和耗时要随结果记录。

### 6.5 内部执行流程

1. 读取 `llama3_<size>.yaml`；
2. 按模型并行度计算每个 rank 的模型和优化器分片大小；
3. 自动选择 default/subset；
4. MPI 启动 DLIO/Streaming Checkpointing rank；
5. 各 rank 并行写自己的 shard，并执行 flush/fsync；
6. 可选的外部 cache clear/remap；
7. 各 rank 读回同一批 checkpoint；
8. 检查 `summary.json`、DLIO 日志和必要输出；
9. 聚合每个 rank 的时间和吞吐。

### 6.6 结果如何解释

- 每次 write/read 都记录每个 rank 的时间和吞吐；
- 全局持续时间取所有 rank 的最大值，因为任务必须等最慢 rank；
- 全局吞吐按最慢 rank 的最小吞吐解释；
- 正式提交必须包含 10 次写、10 次读，以及 cache clear/remap 等中间过程日志；
- 页缓存命中的恢复读不能冒充存储恢复性能。

来源：[Checkpointing README](../checkpointing/README.md)、[Streaming Checkpoint 指南](Streaming-Chkpt-Guide.md)、[CheckpointingBenchmark 实现](../mlpstorage_py/benchmarks/dlio.py)。

## 7. KV Cache 测试

### 7.1 测试目的和基本原理

LLM 推理会为每个会话保存 attention 的 Key/Value 中间数据。会话变长或用户变多后，KV Cache 可能从 GPU 内存溢出到 CPU 内存，再溢出到 SSD。

该 benchmark 用多用户请求模拟器生成 Prefill 和 Decode 行为：

- Prefill：处理 prompt，生成新的 KV 数据，写压力为主；
- Decode：生成输出 token，需要反复读取已有 KV 数据，读压力和尾延迟更重要。

核心 `MultiTierCache` 使用 waterfall LRU：新数据优先放入最快可用 tier；tier 满后，最久未使用条目向下一层逐级驱逐。当前设计是单向 GPU → CPU → Storage，读取后不会自动晋升回上层，因此它有意放大存储压力。

CLOSED 三个选项的 `gpu-mem-gb` 都是 0，所以正式 KV Cache 测试不需要真实 GPU。

### 7.2 CLOSED 固定的三个选项

| Option | 模型 | 用户数 | GPU/CPU tier | 单次时长 | 主要目的 |
|---|---|---:|---|---:|---|
| 1 | Llama3.1 8B | 200 | 0 / 0 GiB | 300 s | 最大化直接 Storage 压力 |
| 2 | Llama3.1 8B | 100 | 0 / 4 GiB | 300 s | 观察 CPU spill 后的 Storage 吞吐 |
| 3 | Llama3.1 70B Instruct | 70 | 0 / 0 GiB | 300 s | 以更大的单 token KV 对象施压 |

每个选项运行 3 个 trial；CLOSED 使用固定 seed 42，并在选项之间等待固定间隔。OPEN/whatif 才允许覆盖模型、用户数、内存 tier、generation mode 等参数。

### 7.3 `datasize`

`datasize` 根据模型每 token KV 字节数、典型 sequence length 和用户数估算：

- 单用户 KV Cache 大小；
- 全部用户工作集；
- GPU、CPU 和 Storage tier 建议容量；
- Storage 额外给出 2× headroom 建议。

它是容量计算，不执行 KV Cache I/O。

```powershell
mlpstorage closed kvcache datasize `
  --cache-dir D:\MLPerfKVCache `
  --results-dir C:\MLPerfResults `
  --systemname storage-system
```

### 7.4 `run`

```powershell
mlpstorage closed kvcache run `
  --cache-dir D:\MLPerfKVCache `
  --results-dir C:\MLPerfResults `
  --systemname storage-system `
  --exec-type mpi `
  --num-processes 1 `
  --hosts localhost `
  --mpi-bin mpiexec
```

内部执行流程：

1. 检查 `cache-dir` 容量、结果目录和 MPI；
2. 多机时验证 `results-dir` 在全部主机的相同路径可见；
3. 依次选择 Option 1、2、3；
4. 每个 Option 运行 3 个 trial；
5. 每个 trial 通过 MPI 启动 `mlperf_wrapper.py`；
6. wrapper 为每个 rank 分配独立 cache/result 目录并调用 `kv-cache.py`；
7. 用户请求进入优先级队列，执行 Prefill 写和 Decode 读；
8. GPU/CPU tier 为 0 或满时，KV 对象写成 Storage tier 文件；
9. 每个 rank 写 `kvcache_results_*.json`；
10. `mlpstorage` 聚合 rank 和 trial，最后写 `summary.json`；
11. 缺少任一 rank 结果会标记 `partial_failure`，整个 Option 没有结果文件会使 run 失败。

### 7.5 结果如何聚合

对每个 trial：

- rank 的读带宽相加；
- rank 的写带宽相加；
- rank 的 token throughput 相加；
- P95 延迟取所有 rank 中最大值。

跨 3 个 trial：

- throughput 和带宽取均值；
- P95 延迟取最大值，而不是均值。

正式结果至少要同时检查：

- `storage_entries > 0`；
- Storage tier 读写字节大于 0；
- Storage read/write bandwidth；
- storage read P95；
- tokens/s；
- 是否存在 missing rank、trial failure、OOM 或 partial failure。

如果全部工作集都被 CPU tier 吸收，命令即使成功也没有形成有效的 SSD offload 压力。

### 7.6 预处理与扩展模式

KV benchmark 文档要求正式测试前对 SSD 进行 preconditioning，以降低空盘、SLC cache 和历史状态造成的结果波动。OPEN/研发模式还支持 prefill-only、decode-only、ShareGPT、BurstGPT、RAG、prefix cache、多轮会话和 block-layer tracing。这些能力适合分析，但只有规则明确接纳的固定配置才能作为 CLOSED 成绩。

来源：[KV Cache README](../kv_cache_benchmark/README.md)、[KV Cache 设计](../kv_cache_benchmark/DESIGN.md)、[KVCacheBenchmark 实现](../mlpstorage_py/benchmarks/kvcache.py)。

## 8. VectorDB 测试

### 8.1 测试目的和与其他三类的区别

VectorDB 测试模拟 RAG 系统中的向量数据库。它不是只在客户端生成文件 I/O，而是连接一个真实运行的 Milvus 服务，执行 collection 创建、向量写入、索引构建、load 和 ANN search。

因此：

- `mlpstorage` 不会自动启动 Milvus；
- `--host/--port` 指向数据库服务；
- 被测数据实际落在哪里由 Milvus 的 volume、对象存储或本地数据目录决定；
- 只把客户端 `--storage-root` 指向某个盘，并不能自动证明 Milvus 数据写到了该盘；
- 测试前必须单独验证 Milvus 数据卷与 DUT 的映射。

### 8.2 索引类型

| 模式 | 索引 |
|---|---|
| CLOSED | DISKANN、HNSW、AISAQ |
| OPEN/whatif | 还可使用 IVF_FLAT、IVF_SQ8、FLAT 等实现允许的索引 |

不同索引的内存/磁盘比例、搜索路径和 Recall/QPS 取舍不同，结果只能在相同数据集、维度、metric、索引和 Recall 定义下比较。

### 8.3 `datasize`

VectorDB `datasize` 是纯数学估算，不需要 Milvus：

```text
raw bytes = num_vectors × dimension × 4 bytes
estimated total = raw bytes × index overhead × num_shards
```

当前实现使用的估算系数包括 DISKANN 1.3、HNSW 1.5、AISAQ 0.15。该值用于规划，不等于数据库实际 WAL、元数据、压缩和 compaction 后的物理占用。

```powershell
mlpstorage closed vectordb datasize `
  --vdb-engine milvus `
  --vdb-index DISKANN `
  --dimension 1536 `
  --num-vectors 1000000 `
  --num-shards 1 `
  --results-dir C:\MLPerfResults `
  --systemname storage-system
```

### 8.4 `datagen`：真实装载和建索引

```powershell
mlpstorage closed vectordb datagen file `
  --vdb-engine milvus `
  --vdb-index DISKANN `
  --host 127.0.0.1 --port 19530 `
  --collection mlps_1m_1536_diskann `
  --num-vectors 1000000 --dimension 1536 `
  --num-shards 1 --force `
  --storage-root D:\MilvusData `
  --results-dir C:\MLPerfResults `
  --systemname storage-system
```

内部流程：

1. 解析 YAML 和 CLI，并确认 `--vdb-index` 与 `--index-type` 一致；
2. 连接 Milvus；
3. 按需删除旧 collection；
4. 创建 schema、collection、shard 和目标 ANN index；
5. 生成确定性的合成向量；
6. 生产者线程分块生成，消费者批量 insert；
7. flush 数据；
8. 可选 compact；
9. 等待索引构建完成；
10. 保存 ground-truth/query artifacts 和 load 指标。

`datagen` 产生真实数据库写入和索引 I/O，但它仍是查询测试的准备阶段。其装载时间和索引构建时间可以单独报告。

### 8.5 `run`：查询测试

VectorDB 支持三种运行路径：

| `--benchmark-mode` | 流程 | 用途 |
|---|---|---|
| `timed` | 在固定秒数内持续查询 | 稳态 QPS/延迟 |
| `query_count` | 精确执行指定数量查询 | 可复现的固定工作量 |
| `sweep` | 扫描 search 参数、缓存和 Recall 目标 | OPEN 调优和诊断 |

```powershell
mlpstorage closed vectordb run file `
  --vdb-engine milvus `
  --vdb-index DISKANN `
  --host 127.0.0.1 --port 19530 `
  --collection mlps_1m_1536_diskann `
  --benchmark-mode timed `
  --runtime 120 `
  --num-query-processes 4 `
  --batch-size 10 `
  --vector-dim 1536 `
  --storage-root D:\MilvusData `
  --results-dir C:\MLPerfResults `
  --systemname storage-system
```

内部查询流程：

1. 连接并 load 已存在的 collection；
2. 读取 datagen 保存的 query/ground-truth；
3. 启动指定数量的查询进程；
4. 按 batch 向 Milvus 发送 ANN search；
5. 记录端到端查询时间；
6. 计时循环结束后，再计算 Recall，避免 Recall 计算污染查询延迟；
7. 汇总 QPS、P50/P95/P99、错误数和 Recall；
8. 多 rank 模式下进行最终聚合。

### 8.6 结果如何解释

- QPS 必须与 Recall@K 一起解释，不能通过牺牲准确率换取不可比的高 QPS；
- P50 表示典型查询，P95/P99 表示尾延迟；
- Recall 由结果集合与 FLAT ground-truth 的交集计算；
- 不同 `query_mode` 或 `recall_epsilon` 的 Recall 定义不能直接横向比较；
- `/proc/diskstats` 只对客户端本地块设备有效；如果 Milvus 使用网络文件系统或远端对象存储，客户端 diskstats 不是 DUT 物理 I/O，正式分数仍以 QPS、Recall 和 latency 为主。

### 8.7 VectorDB logical trace/replay

仓库另外实现了正式 Milvus 操作的逻辑 trace：

```powershell
vdbbench-modular `
  --config vdb_benchmark\vdbbench\benchmark\configs\windows_trace_smoke.yaml `
  --io-trace-log C:\MLPerfResults\vdb_trace.csv `
  --output-dir C:\MLPerfResults\vdb_source_run

python -m vdbbench.replay C:\MLPerfResults\vdb_trace.csv `
  --data-dir D:\VDBReplayData `
  --direct-io
```

Capture 记录 Insert、Flush、Load、Search 的逻辑大小、顺序和时间间隔；Replay 将这些逻辑事件映射为目标盘上的文件读写，并报告 P50/P95/P99、逻辑字节和 direct-I/O device bytes。

它适合固定 I/O 压力后比较不同 SSD，但存在明确边界：

- trace 大小是客户端逻辑估算，不包含 Milvus WAL、protobuf、索引、对象存储和 compaction 放大；
- replay 不包含数据库网络、索引执行和 Recall；
- replay 结果必须标记为 trace/replay 条件性结果，不能冒充完整 VectorDB QPS/Recall 成绩。

来源：[VectorDB README](../vdb_benchmark/README.md)、[VectorDB 模块设计](../vdb_benchmark/vdbbench/benchmark/README.md)、[Trace Replay](../vdb_benchmark/TRACE_REPLAY.md)、[VectorDBBenchmark 实现](../mlpstorage_py/benchmarks/vectordbbench.py)。

## 9. 结果目录、报告和提交校验

### 9.1 初始化结果根目录

当前版本要求先把组织身份固定到结果根目录：

```powershell
New-Item -ItemType Directory -Force C:\MLPerfResultsParent
mlpstorage init ExampleOrg C:\MLPerfResultsParent\results
```

`init` 创建 `mlperf-results.yaml` sentinel。后续命令的 `--results-dir` 必须指向该目录；重复使用相同 orgname 初始化是幂等的。

### 9.2 单次 run 的证据

一次可审计运行通常至少包含：

- 最终参数和 metadata；
- 原生命令 stdout/stderr；
- benchmark 的 `summary.json` 或对应统计 JSON；
- 运行前后 cluster info；
- 时序监控数据；
- systemname YAML；
- CLOSED/OPEN 验证状态；
- datagen manifest、Recall/ground-truth 或每 rank 结果等 workload 专用证据。

### 9.3 报告、历史和校验

```powershell
# 汇总 benchmark 结果
mlpstorage reports reportgen `
  --results-dir C:\MLPerfResultsParent\results `
  --systemname storage-system

# 查看或重放历史命令
mlpstorage history show
mlpstorage history rerun <ID>

# 校验提交目录是否满足 Rules.md
mlpstorage validate <submission-dir>

# 检查 Rules.md 中的规则是否都有 checker 实现
mlpstorage rules-coverage
```

`reportgen` 只汇总已有证据，不能把 `BLOCKED`、部分 trial、whatif、dry-run 或缺失结果文件的运行变成有效成绩。

来源：[ReportGenerator](../mlpstorage_py/report_generator.py)、[HistoryTracker](../mlpstorage_py/history.py)、[submission checker](../mlpstorage_py/submission_checker/README.md)。

## 10. 从零开始的推荐执行顺序

```text
1. 安装 Python 环境、mlpstorage 和 MPI
2. 初始化 results-dir
3. 记录 DUT、挂载、Milvus volume 和结果盘映射
4. 执行 datasize
5. 检查单盘容量和 data/results 文件系统隔离
6. Training/VDB 执行 datagen；Checkpoint/KV 准备目标目录和设备状态
7. 执行 configview（支持该命令的测试项）
8. 执行正式 run
9. 检查退出码、summary、rank/trial 完整性和业务门槛
10. 生成 report，必要时执行 validate
11. 保留 results 和证据，删除本次 workload 临时数据
```

测试数据清理必须以本次 run manifest 中记录的绝对路径为边界；不得删除 results、source trace、其他 run 或整个盘根目录。

## 11. Windows 执行注意事项

- 官方上游主要以 Ubuntu 和 OpenMPI 验证；Windows 通常使用 MS-MPI 的 `mpiexec`；
- 如果 `mlpstorage` 未安装到 PATH，可使用 `\.venv\Scripts\mlpstorage.exe`；若仓库根目录存在脚本，PowerShell 需要写 `\.\mlpstorage`；
- 不需要 Docker 才能运行 Training、Checkpointing 或 KV Cache；VectorDB 是否需要容器只取决于你如何部署 Milvus；
- Windows 没有 Linux 的 `/proc/sys/vm/drop_caches`，checkpoint cold-read 方法必须单独设计并记录；
- VectorDB direct-I/O replay 在 Windows 使用对齐的 unbuffered I/O 和 write-through；
- `data/cache/checkpoint` 路径可以位于 C/D/E 任意盘，关键是它必须解析到目标 DUT，且 results 应放在另一文件系统。

## 12. 如何判断一个测试项真的完成

必须同时满足：

1. 原生 workload 确实执行，而不是 plan、preflight、dry-run 或 datasize；
2. 数据、checkpoint、KV cache 或 Milvus volume 确实命中目标 DUT；
3. 配置通过 CLOSED/OPEN 规则，或明确标记为 whatif/conditional；
4. 所有规定的 run、rank、trial 和阶段完成；
5. 结果文件完整且可解析；
6. 正确性指标通过，例如训练数据规模、checkpoint 恢复完整性、KV Tier-2 bytes、VectorDB Recall；
7. 性能指标达到对应门槛；
8. 日志、metadata、监控和外部操作证据齐全；
9. workload 临时数据完成受控清理。

只满足“命令启动过”或“返回码为 0”不能等价于完整测试通过。

## 13. 第一手资料索引

- [MLPerf Storage GitHub 官方仓库](https://github.com/mlcommons/storage)
- [MLCommons Storage Benchmark 页面](https://mlcommons.org/benchmarks/storage/)
- [仓库总 README](../README.md)
- [Rules.md](../Rules.md)
- [Submission Guidelines](../Submission_guidelines.md)
- [Training README](../training/README.md)
- [Checkpointing README](../checkpointing/README.md)
- [KV Cache README](../kv_cache_benchmark/README.md)
- [KV Cache DESIGN](../kv_cache_benchmark/DESIGN.md)
- [VectorDB README](../vdb_benchmark/README.md)
- [VectorDB Trace Replay](../vdb_benchmark/TRACE_REPLAY.md)
- [公共 Benchmark 基类](../mlpstorage_py/benchmarks/base.py)
- [Training/Checkpointing 实现](../mlpstorage_py/benchmarks/dlio.py)
- [KV Cache 实现](../mlpstorage_py/benchmarks/kvcache.py)
- [VectorDB 实现](../mlpstorage_py/benchmarks/vectordbbench.py)
