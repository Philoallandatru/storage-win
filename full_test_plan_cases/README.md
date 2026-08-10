# FULL_TEST_PLAN：33 个直接 native Case

`cases/` 中的每个文件都是独立入口，文件内直接写出并调用仓库的 `mlpstorage` 命令；不依赖第二层 workload runner，也不执行标准库模拟 probe。

## 模式

- `--mode plan`：只打印该 Case 的 native 命令，不执行。
- `--mode preflight`：打印命令并检查 `mlpstorage` 可执行文件，不执行 workload。
- `--mode dry-run`：直接把 `--dry-run` 传给 `mlpstorage`，结果只能视为命令验证。
- `--mode execute --confirm-dut`：执行真实 native workload；命令失败立即停止当前 Case。

例如 Windows Training Case：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases\cases\test_ai_trn_003.py `
  --mode execute --confirm-dut --prepare --init-results `
  --cleanup-data --cleanup-root D:\ai_ssd\data `
  --launcher single --data-dir D:\ai_ssd\data\AI-TRN-003\run-001 `
  --results-dir E:\ai_ssd\results\AI-TRN-003\run-001
```

`--init-results` 调用项目原生 `mlpstorage init`；`--cleanup-data` 只删除
`--cleanup-root` 下本次 case 的 data/cache/checkpoint 目录，不删除 results 或源 trace。

生成的命令形态是：

```text
mlpstorage open training unet3d datagen file ...
mlpstorage open training unet3d run file ...
```

模型是 Training CLI 的位置参数，不使用错误的 `--model unet3d` 形式。

Windows 的 `--launcher single` 也使用项目原生 MPI 执行路径，但只配置单进程；它不启动 Docker Engine。需要真实 MPI rank 时使用：

```powershell
--launcher mpi --mpi-bin mpiexec
```

## Native 入口边界

目录只保留当前版本可以直接调用 `mlpstorage open ...` 的 33 个 workload Case。
没有 native 命令的规划项、`whatif` 估算项、扩展 KV、TP/prefill/decode
和混合编排项不在这个目录生成 Case 脚本。VectorDB 的正式 Trace capture/replay
已经实现，但它属于独立的 `trace_test_cases/` 集合，不能与 Native 成绩混报。

VectorDB Case 不负责启动 Milvus；执行前必须确认 `127.0.0.1:19530` 已有可访问服务。Checkpoint cold-cache、SSD 填充和混合编排等外部动作必须由 DUT 管理者提供，不能由脚本臆造。

## 全量入口

只查看全部 Case 的 native 命令：

```powershell
.\.venv\Scripts\python.exe -m full_test_plan_cases.run_all `
  --mode plan --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

正式执行：

```powershell
.\.venv\Scripts\python.exe -m full_test_plan_cases.run_all `
  --mode execute --confirm-dut --init-results --cleanup-data `
  --cleanup-root D:\ai_ssd\data --launcher single --prepare `
  --data-dir D:\ai_ssd\data --results-dir C:\ai_ssd\results
```

`run_all` 直接启动每个 `cases/test_*.py` 文件；在 `execute`、`dry-run` 或 `preflight` 模式下第一个非零返回码会触发套件级 fast-fail。

正式 `PASS` 只能来自真实 native workload 的返回结果和输出文件；`DRY_RUN` 不算通过。
