# FULL_TEST_PLAN：72 个直接 native Case

`cases/` 中的每个文件都是独立入口，文件内直接写出并调用仓库的 `mlpstorage` 命令；不依赖第二层 workload runner，也不执行标准库模拟 probe。

## 模式

- `--mode plan`：只打印该 Case 的 native 命令，不执行。
- `--mode preflight`：打印命令并检查 `mlpstorage` 可执行文件，不执行 workload。
- `--mode dry-run`：直接把 `--dry-run` 传给 `mlpstorage`，结果只能视为命令验证。
- `--mode execute --confirm-dut`：执行真实 native workload；命令失败立即停止当前 Case。

例如 Windows Training Case：

```powershell
mlpstorage init ai-trn-003 D:\ai_ssd\results
.\.venv\Scripts\python.exe full_test_plan_cases\cases\test_ai_trn_003.py `
  --mode execute --confirm-dut --prepare --launcher single `
  --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

`mlpstorage init` 是项目原生命令，脚本不会替用户初始化、清理或改写结果目录。

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

## Native 支持边界

Case catalog 同时保存：

- `workbook_command`：工作簿原始命令，仅用于追溯；
- `source_command`：当前版本可执行的 native 命令；
- `native_status`：`SUPPORTED` 或 `BLOCKED`。

没有统一 `mlpstorage` 命令的 Base、Mixed、Trace replay、扩展 KV、TP/prefill/decode 等 Case 会明确返回 `BLOCKED`，不会改成 `SMOKE_PASS` 或调用其他工具冒充 MLPerf Storage。

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
  --mode execute --confirm-dut --launcher single --prepare `
  --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

`run_all` 直接启动每个 `cases/test_*.py` 文件；在 `execute`、`dry-run` 或 `preflight` 模式下第一个非零返回码会触发套件级 fast-fail。`plan` 模式会列出所有 native blocker。

正式 `PASS` 只能来自真实 native workload 的返回结果和输出文件；`PLANNED`、`DRY_RUN`、`BLOCKED` 都不算通过。
