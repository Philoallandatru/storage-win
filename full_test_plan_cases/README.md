# FULL_TEST_PLAN：72 个独立测试脚本

本目录严格来自随包保存的 `source/FULL_TEST_PLAN.xlsx`（原文件名 `AI_SSD_AI_PC_Case_Execution_Matrix_FULL_v2_CN.xlsx`，SHA-256：`fada60af...d27656`），按工作簿顺序生成 72 个脚本。入口文件位于 `cases/`，文件名与 Case ID 一一对应，例如：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases/cases/test_ai_trn_003.py --mode plan --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

项目正式运行时要求 Python 3.12；Windows 上请始终使用仓库的 `.\.venv\Scripts\python.exe`，不要依赖 PATH 中可能较旧的系统 `python`。可先执行 `.\.venv\Scripts\python.exe --version` 确认。

## 运行层级

- `--mode plan`：默认。写入 Case manifest，只展示工作簿原命令和当前版本命令，不运行负载。
- `--mode preflight`：检查当前 Case 是否能由已安装工具表达，以及入口程序是否存在。
- `--mode dry-run`：`mlpstorage` Case 实际调用 `mlpstorage ... --dry-run`；直接 KV Case 使用 `--max-requests 1 --io-trace-log ...` 的无真实存储 I/O Trace 模式。两者都用于验证参数和命令链，不运行重负载。
- `--mode execute --confirm-dut`：在确认 DUT、容量和结果盘后运行实际命令。

Windows 单进程使用 `--launcher single`。当前 CLI 内部仍将它拼成 `--exec-type docker`，但这个值只表示“不加 MPI 前缀直接运行”，不会启动 Docker Engine，也不会调用 `docker run`。需要真实 2/4/8 rank 时使用 `--launcher mpi --mpi-bin mpiexec`。

## 参数来源与当前支持范围

脚本不是只按 `mlpstorage open ...` 的模型列表判断能力，而是按仓库对应 README 和已安装入口分别映射：

| 家庭 | 仓库参数来源 | FULL Case 使用的入口与选择 |
|---|---|---|
| Training | `README.md`、`training/README.md` | `open`：UNet3D/B200、RetinaNet/B200、RetinaNet/MI355；`whatif`：UNet3D/A100/H100、CosmoFlow/A100/H100、ResNet50/A100/H100、DLRM/B200/MI355、Flux/B200/MI355。`whatif` 结果不可提交。|
| Checkpoint | `checkpointing/README.md` | `llama3-8b`、`llama3-70b`、`llama3-405b`、`llama3-1t`；写阶段使用 `--num-checkpoints-read 0`，读阶段使用 `--num-checkpoints-write 0`，两阶段之间由用户提供缓存清理或重启命令。|
| KV Cache | `kv_cache_benchmark/README.md`、`kv_cache_benchmark/DESIGN.md`、`kv_cache_benchmark/config.yaml` | `mlpstorage` 包装入口支持 tiny-1b、mistral-7b、llama2-7b、llama3.1-8b、llama3.1-70b-instruct；已安装的 `mlperf-kv-cache` 配置入口还支持 deepseek-v3、qwen3-32b、gpt-oss-20b、gpt-oss-120b。|
| KV Trace | `kv_cache_benchmark/DESIGN.md` | 支持 `--io-trace-log`、`--use-burst-trace`、`--burst-trace-path`、`--dataset-path`、`--trace-speedup`、`--replay-cycles`、`--prefill-only`、`--decode-only`、`--num-gpus`、`--tensor-parallel` 等；Case 021/022 使用其中的 Trace/数据集入口。|
| VectorDB replay | `vdbbench.replay --help` | Trace 文件、`--data-dir`、`--speed`、`--as-fast-as-possible`、`--fsync`、`--direct-io`、`--seed`、`--chunk-size-mib`；Case 015 使用 Trace、speed 和 direct-I/O。|

所有 Case 脚本共享以下可覆盖选项：

- 执行控制：`--mode`、`--data-dir`、`--results-dir`、`--launcher`、`--mpi-bin`、`--mlpstorage`、`--confirm-dut`。
- 规模控制：`--engineering-smoke`、`--matrix`、`--repeats`、`--prepare`、`--duration-sec`。
- Training：`--accelerators`、`--client-memory-gb`、`--o-direct`；`--matrix` 展开 Case 表中已声明并可由当前配置表达的 accelerator/thread 点。
- KV Cache：`--users`、`--burst-trace`、`--sharegpt-dataset`。
- VectorDB：`--query-processes`、`--num-vectors`、`--vector-dimension`、`--trace-file`。
- 人工工作流：`--cache-reset-command`、`--custom-command`。

脚本会把原始表格命令与实际生成命令同时保存到 `manifest.json`。README 没有提供直接参数的维度不会被脚本臆造；需要实验室外部 Trace、真实填充操作或并发编排时，会显示所缺输入。

## 示例

UNet3D/B200：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases/cases/test_ai_trn_003.py --mode dry-run --launcher single --prepare --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

README 中列出的 What-if 模型，例如 CosmoFlow/A100：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases/cases/test_ai_trn_006.py --mode dry-run --launcher single --prepare --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

配置文件提供的扩展 KV 模型，例如 DeepSeek-V3：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases/cases/test_ai_kv_009.py --mode dry-run --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

BurstGPT 或 ShareGPT 二选一：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases/cases/test_ai_kv_022.py --mode execute --confirm-dut --burst-trace D:\traces\BurstGPT_1.csv --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
.\.venv\Scripts\python.exe full_test_plan_cases/cases/test_ai_kv_022.py --mode execute --confirm-dut --sharegpt-dataset D:\traces\ShareGPT.json --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

Checkpoint cold/warm 分段；缓存处理命令必须由 DUT 管理者批准：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases/cases/test_ai_ckp_008.py --mode execute --confirm-dut --cache-reset-command "<批准的缓存清理或重启命令>" --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

缩小工程规模的本地实跑（会产生真实 I/O，但结果明确标为 `SMOKE_PASS`，不可作为正式成绩）：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases/cases/test_ai_trn_003.py --mode execute --engineering-smoke --confirm-dut --launcher single --prepare --accelerators 1 --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

正式模式不要加 `--engineering-smoke`；脚本不会跳过参数、环境、文件系统分离或时序采集门禁。FULL 数据集可能接近 983 GiB，执行 `--prepare` 前必须先确认容量。

需要展开工作簿中当前适配器支持的全部 sweep 点时追加 `--matrix`；正式模式每个点默认执行 3 个 loops，也可用 `--repeats` 明确指定。

正式模式下，外部前置条件不齐全时会明确返回 `BLOCKED`。这不等于 `mlpstorage` 模型不支持：

- AI-BASE-002/003/004 需要对 DUT 执行正式基线、监控或填充操作的授权。
- AI-CKP-008 需要 `--cache-reset-command`；Llama3-8B 完整 checkpoint 还需要约 105 GiB 加文件系统余量。
- AI-KV-022 需要真实 `--burst-trace` 或 `--sharegpt-dataset`。
- AI-VDB-015 需要真实 `--trace-file`。
- AI-MIX-001 至 AI-MIX-005 需要正式组件命令和并发编排。

上述 Case 都提供 `--engineering-smoke` 的基本 try run。它会使用 1 秒/1 MiB 或随包极小 Trace，结果标为 `SMOKE_PASS`，不能当作正式成绩：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases/cases/test_ai_kv_022.py --mode execute --engineering-smoke --confirm-dut --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
.\.venv\Scripts\python.exe full_test_plan_cases/cases/test_ai_mix_001.py --mode execute --engineering-smoke --confirm-dut --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

准备好实验室命令后也可接入对应入口：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases/cases/test_ai_mix_001.py --mode execute --confirm-dut --custom-command "<批准的并发编排命令>" --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

一次生成/检查全部 Case 的计划：

```powershell
.\.venv\Scripts\python.exe -m full_test_plan_cases.run_all --mode plan --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

每个 Case 的 `manifest.json` 都保留工作簿原始测试工具、目的、步骤、时长、脚本、标准、Profile、Priority、变量、指标和 Windows 状态。
