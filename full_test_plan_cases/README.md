# FULL_TEST_PLAN：72 个独立测试脚本

本目录严格来自随包保存的 `source/FULL_TEST_PLAN.xlsx`（原文件名 `AI_SSD_AI_PC_Case_Execution_Matrix_FULL_v2_CN.xlsx`，SHA-256：`fada60af...d27656`），按工作簿顺序生成 72 个脚本。入口文件位于 `cases/`，文件名与 Case ID 一一对应，例如：

```powershell
python full_test_plan_cases/cases/test_ai_trn_003.py --mode plan --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

## 运行层级

- `--mode plan`：默认。写入 Case manifest，只展示工作簿原命令和当前版本命令，不运行负载。
- `--mode preflight`：检查当前 Case 是否能由已安装工具表达，以及入口程序是否存在。
- `--mode dry-run`：实际调用当前 `mlpstorage ... --dry-run`，验证参数和最终 DLIO 命令；不会运行重负载。
- `--mode execute --confirm-dut`：在确认 DUT、容量和结果盘后运行实际命令。

Windows 单进程使用 `--launcher single`。当前 CLI 内部仍将它拼成 `--exec-type docker`，但这个值只表示“不加 MPI 前缀直接运行”，不会启动 Docker Engine，也不会调用 `docker run`。需要真实 2/4/8 rank 时使用 `--launcher mpi --mpi-bin mpiexec`。

## 示例

当前版本可表达的 UNet3D/B200：

```powershell
python full_test_plan_cases/cases/test_ai_trn_003.py --mode dry-run --launcher single --prepare --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

缩小工程规模的本地实跑（会产生真实 I/O，但结果明确标为 `SMOKE_PASS`，不可作为正式成绩）：

```powershell
python full_test_plan_cases/cases/test_ai_trn_003.py --mode execute --engineering-smoke --confirm-dut --launcher single --prepare --accelerators 1 --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

正式模式不要加 `--engineering-smoke`；脚本不会跳过参数、环境、文件系统分离或时序采集门禁。FULL 数据集可能接近 983 GiB，执行 `--prepare` 前必须先确认容量。

需要展开工作簿中当前适配器支持的全部 sweep 点时追加 `--matrix`；正式模式每个点默认执行 3 个 loops，也可用 `--repeats` 明确指定。

FULL 表中当前 CLI 尚未支持的模型、Trace 或 Mixed 编排会明确返回 `BLOCKED`。准备好实验室命令后可接入对应入口：

```powershell
python full_test_plan_cases/cases/test_ai_mix_001.py --mode execute --confirm-dut --custom-command "<批准的并发编排命令>" --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

一次生成/检查全部 Case 的计划：

```powershell
python -m full_test_plan_cases.run_all --mode plan --data-dir D:\ai_ssd\data --results-dir E:\ai_ssd\results
```

每个 Case 的 `manifest.json` 都保留工作簿原始测试工具、目的、步骤、时长、脚本、标准、Profile、Priority、变量、指标和 Windows 状态。
