# AI SSD 测试执行手册

## 1. 目录约定

每次执行都使用唯一 run id：

```text
<DUT_ROOT>\ai-ssd\<CASE_ID>\<RUN_ID>\     # 只放 workload 数据/cache/checkpoint
<RESULT_ROOT>\ai-ssd\<CASE_ID>\<RUN_ID>\  # 日志、metadata、监控、verdict
```

`DUT_ROOT` 必须位于目标 SSD；`RESULT_ROOT` 尽量位于 C 盘或另一块非 DUT 盘。不要把 results、trace 原件和 workload 数据混在一个目录。

## 2. 执行前门禁

下面是门禁，不是测试结果：

```powershell
Get-Volume | Where-Object DriveLetter | Select-Object DriveLetter,FileSystem,Size,SizeRemaining
Get-PhysicalDisk | Select-Object FriendlyName,SerialNumber,HealthStatus,OperationalStatus,Size
Get-Command mpiexec,mpirun -ErrorAction SilentlyContinue | Select-Object Name,Source
python --version
```

Training/Checkpointing 需要 MPI；VectorDB 需要可访问的 Milvus 服务：

```powershell
Test-NetConnection 127.0.0.1 -Port 19530 -InformationLevel Quiet
```

GPU 不作为 Windows storage workload 的通用前置条件。命令中的 accelerator 参数只在 workload 规则需要时用于构造 I/O 压力。

## 3. Native 执行规则

Native case 只允许直接使用仓库 CLI：

```text
mlpstorage open training ...
mlpstorage open checkpointing ...
mlpstorage open kvcache ...
mlpstorage open vectordb ...
```

推荐每个 case 的实际顺序：

1. 生成唯一目录和 manifest；
2. 执行原生容量/配置门禁；
3. 执行 datagen 或准备阶段；
4. 执行正式 run；
5. 保存 stdout/stderr、最终配置、监控和正确性结果；
6. 计算 verdict；
7. 删除该 case 的临时数据目录并复核删除结果。

`plan`、`preflight`、`dry-run` 只能验证命令或环境，不能记为测试 PASS。

## 4. 四类 Native 基线

### 4.1 Training

以生成器输出的具体 case 命令为准，例如：

```powershell
mlpstorage open training unet3d datagen file `
  --num-processes 1 `
  --data-dir D:\ai-ssd\AI-TRN-003\<RUN_ID> `
  --results-dir C:\ai-ssd-results\AI-TRN-003\<RUN_ID> `
  --systemname ai-ssd-win `
  --exec-type mpi `
  --mpi-bin mpiexec `
  --params dataset.num_files_train=<VALIDATED_FILE_COUNT>

mlpstorage open training unet3d run file `
  --num-accelerators <ACCELERATORS> `
  --accelerator-type b200 `
  --client-host-memory-in-gb <MEMORY_GB> `
  --loops <LOOPS> `
  --data-dir D:\ai-ssd\AI-TRN-003\<RUN_ID> `
  --results-dir C:\ai-ssd-results\AI-TRN-003\<RUN_ID> `
  --systemname ai-ssd-win `
  --exec-type mpi `
  --mpi-bin mpiexec `
  --params dataset.num_files_train=<VALIDATED_FILE_COUNT>
```

当前 `unet3d_b200.yaml` 的正式配置为 7200 个训练文件（约 984 GiB）；`<VALIDATED_FILE_COUNT>` 必须以最终配置和规则门禁为准，不能把 168 等缩小值作为正式成绩。

### 4.2 Checkpointing

```powershell
mlpstorage open checkpointing run file `
  --model llama3-8b `
  --num-processes 8 `
  --client-host-memory-in-gb <MEMORY_GB> `
  --checkpoint-folder D:\ai-ssd\AI-CKP-001\<RUN_ID> `
  --num-checkpoints-write 10 `
  --num-checkpoints-read 10 `
  --results-dir C:\ai-ssd-results\AI-CKP-001\<RUN_ID> `
  --systemname ai-ssd-win `
  --exec-type mpi `
  --mpi-bin mpiexec
```

只有在 10 写/10 读容量和 rank 条件满足时，才能把结果记为正式规模；否则必须记 `NOT RUN` 或 `CONDITIONAL`。

### 4.3 KV Cache

KV Cache 没有 `file/object` 位置参数：

```powershell
mlpstorage open kvcache run `
  --model llama3.1-8b `
  --num-users 10 `
  --duration 300 `
  --generation-mode realistic `
  --performance-profile latency `
  --trials 3 `
  --inter-option-delay 20 `
  --gpu-mem-gb 0 `
  --cpu-mem-gb 0 `
  --cache-dir D:\ai-ssd\AI-KV-001\<RUN_ID> `
  --results-dir C:\ai-ssd-results\AI-KV-001\<RUN_ID> `
  --systemname ai-ssd-win `
  --exec-type mpi `
  --num-processes 1 `
  --hosts localhost `
  --mpi-bin mpiexec
```

正式判定必须查看 Tier-2 bytes/storage entries；命令返回 0 但 Tier-2 没有 I/O 时不能记 SSD PASS。

### 4.4 VectorDB Native

VectorDB 不由 `mlpstorage` 自动启动 Milvus：

```powershell
mlpstorage open vectordb datagen file `
  --vdb-engine milvus --vdb-index HNSW `
  --host 127.0.0.1 --port 19530 `
  --collection ai_vdb_baseline `
  --num-vectors 1000000 --dimension 1536 --num-shards 1 --force `
  --results-dir C:\ai-ssd-results\AI-VDB-001 `
  --systemname ai-ssd-win

mlpstorage open vectordb run file `
  --vdb-engine milvus --vdb-index HNSW `
  --host 127.0.0.1 --port 19530 `
  --collection ai_vdb_baseline `
  --benchmark-mode timed --vector-dim 1536 `
  --num-query-processes 1 --runtime 60 --loops 3 `
  --storage-root D:\ai-ssd\AI-VDB-001\<RUN_ID> `
  --results-dir C:\ai-ssd-results\AI-VDB-001 `
  --systemname ai-ssd-win
```

1K×128 HNSW 只能作为链路验证，不能替代 1M/10M 的正式规模结论。

## 5. VectorDB Trace Capture 和 Replay

仓库已实现正式 VectorDB trace 路径：

```powershell
vdbbench-modular `
  --config vdb_benchmark\vdbbench\benchmark\configs\windows_trace_smoke.yaml `
  --io-trace-log C:\ai-ssd-results\AI-VDB-015\source_trace.csv `
  --output-dir C:\ai-ssd-results\AI-VDB-015\source_run

python -m vdbbench.replay `
  C:\ai-ssd-results\AI-VDB-015\source_trace.csv `
  --data-dir D:\ai-ssd\AI-VDB-015\<RUN_ID> `
  --direct-io
```

Capture 的来源必须是真实 Milvus run。Replay 输出必须同时报告：

- operation count、read/write count；
- logical bytes；
- wall-clock 和 active-I/O 吞吐；
- P50/P95/P99；
- direct-I/O 的 sector-padded device bytes；
- trace SHA-256、source command 和数据目录。

VectorDB trace 中的逻辑字节是客户端可见的估算，不等于 Milvus WAL、索引、对象存储和 compaction 的物理字节；这些限制必须随结果归档。

底层 KV benchmark 的 tracer 支持 `--io-trace-log`，但当前 `mlpstorage open kvcache` CLI 没有暴露该参数，仓库也没有已验证的 KV replay 命令。因此本版本不执行、不登记 KV trace case；后续只有补齐 CLI 暴露、source manifest 和 replay 工具后，才能按 `TRACE-CAPTURE`/`TRACE-REPLAY` 进入用例目录。

根目录 pytest 与 `vdb_benchmark` pytest 必须分开运行：两个目录存在同名 `tests.conftest`，混跑会触发 pytest 的 `ImportPathMismatchError`，这属于测试入口隔离问题，不是 workload 结果。

## 6. 判定和证据

每个 run 至少保留：

```text
manifest.json
configview.txt
stdout.log
stderr.log
windows_disk_1s.csv（如启用监控）
trace.csv（Trace case）
integrity_report.json
verdict.json
```

判定：

- `PASS`：真实执行、路径正确、正确性通过、指标达到 case 门槛；
- `FAIL`：真实执行但业务或性能门槛失败；
- `BLOCKED`：依赖/容量/外部服务未满足；
- `INVALID`：证据、路径、trace 或规模不合法；
- `CONDITIONAL`：scaled/replay 等有明确限制的结果。

## 7. 清理规则

每个 case 只能删除自己 manifest 中声明的临时目录。清理前必须解析绝对路径并确认它位于批准的测试根目录；不得删除 results、源 trace 或用户目录。

推荐在脚本 finally 阶段执行清理，并输出：

```text
TEST_DATA_ROOT=<absolute path>
TEST_DATA_CLEANED=True
```

清理失败时，case 不得伪装成 PASS，应保留 `CLEANUP_FAILED` 状态供处理。
