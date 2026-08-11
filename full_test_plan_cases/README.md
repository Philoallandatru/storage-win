# FULL_TEST_PLAN：33 个直接 Native Case

当前 Case 数量、ID 和参数以
[`case_catalog.json`](case_catalog.json) 为准；文档状态和旧方案迁移说明见
[`docs/AI_SSD_DOCUMENT_STATUS.md`](../docs/AI_SSD_DOCUMENT_STATUS.md)。旧的 72 Case
规划矩阵不再是本目录的执行来源。

`cases/` 中的每个文件都是独立入口，文件内直接写出并调用仓库的 `mlpstorage` 命令；不依赖第二层 workload runner，也不执行标准库模拟 probe。

## 单个 Case：日常唯一入口

Windows 下只传 Case ID：

```powershell
.\run_case.cmd AI-KV-005
```

临时指定另一块测试盘时只增加一个盘符参数：

```powershell
.\run_case.cmd AI-KV-005 --test-drive D
```

运行参数不应由测试人员每次重新输入。机器相关配置集中在
[`site_config.json`](site_config.json)，安装或迁移机器后只修改一次：

```json
{
  "test_drive": "C",
  "test_root": "MLPerfStorageTest",
  "data_subdir": "data",
  "results_subdir": "results",
  "mpi_bin": "mpiexec",
  "duration_sec": 60,
  "loops": 1,
  "prepare": true,
  "cleanup_data": true
}
```

默认盘符是 `C`。`test_drive` 只控制本次测试使用的盘；也可以使用命令行的
`--test-drive D` 临时覆盖，不需要修改每个 Case 脚本。正式多盘部署如需把
results 放到独立文件系统，可使用兼容配置中的 `data_root/results_root` 高级字段。

入口会自动完成以下工作：

1. 根据 Case ID 找到唯一的 native case 文件；
2. 派生 `<data_root>/<CASE_ID>` 和 `<results_root>/<CASE_ID>`；
3. 初始化结果目录、确认 DUT、配置 MPI 和 venv PATH；
4. Training/VectorDB 自动执行准备阶段，再执行正式 run；
5. workload 非零退出码原样返回；
6. 成功或失败后只清理该 Case 的数据目录，保留 results。

只在诊断时使用以下可选参数：

```powershell
# 查看最终命令，不启动 workload
.\run_case.cmd AI-KV-005 --print-command

# 本次保留 workload 数据
.\run_case.cmd AI-KV-005 --keep-data

# 临时覆盖配置中的运行模式
.\run_case.cmd AI-KV-005 --mode preflight
```

`AI-VDB-015` 是独立的 trace capture/replay case，不在这 33 个 Native Case 中。

## 独立 Case 文件：高级调试入口

只有开发或排查参数映射时，才直接调用 `cases/test_*.py` 并逐项覆盖配置。

## 模式

- `--mode plan`：只打印该 Case 的 native 命令，不执行。
- `--mode preflight`：打印命令并检查 `mlpstorage` 可执行文件，不执行 workload。
- `--mode dry-run`：直接把 `--dry-run` 传给 `mlpstorage`，结果只能视为命令验证。
- `--mode execute --confirm-dut`：执行真实 native workload；命令失败立即停止当前 Case。

例如 Windows Training Case 的高级调试命令：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases\cases\test_ai_trn_003.py `
  --mode execute --confirm-dut --prepare --init-results `
  --cleanup-data --cleanup-root C:\MLPerfStorageTest\data `
  --launcher single --data-dir C:\MLPerfStorageTest\data\AI-TRN-003\run-001 `
  --results-dir C:\MLPerfStorageTest\results\AI-TRN-003\run-001
```

`--init-results` 调用项目原生 `mlpstorage init`；`--cleanup-data` 只删除
`--cleanup-root` 下本次 case 的 data/cache/checkpoint 目录，不删除 results 或源 trace。

## Dev 模式：直接从 case 文件运行（缩小数据集 / 本机验证）

正式 `run_case.cmd` 链路使用完整数据集（unet3d 7200 文件 ≈ 983 GiB、retinanet
1,170,301 文件 ≈ 352 GiB），受 CAP-01 容量门禁和 CAP-03 同盘门禁约束。本机开发
验证时可以直接调用 case 文件，用以下参数缩小规模或绕过提交级门禁：

| 参数 | 作用 |
|---|---|
| `--num-files-train N` | 覆盖 datagen/run 的 `dataset.num_files_train`（默认写死在 case 命令里） |
| `--allow-invalid-params` / `-aip` | dev 用：放行 MLPerf"训练数据 ≥ 5× 客户端内存"规则校验（正式提交不可用） |
| `--skip-fs-separation-gate` | dev 用：绕过 CAP-03 同盘门禁（分盘后可省略） |

示例（分盘 D 数据 / E 结果，8 文件冒烟，不绕过 CAP 门禁）：

```powershell
.\.venv\Scripts\python.exe full_test_plan_cases\cases\test_ai_trn_003.py `
  --mode execute --confirm-dut --prepare --init-results `
  --data-dir D:\mlps_dev_data --results-dir E:\mlps_dev_res `
  --systemname devdemo --num-files-train 8 --allow-invalid-params `
  --launcher mpi --mpi-bin mpiexec --client-memory-gb 64 --accelerators 1
```

注意：
- `--num-files-train` 只对 Training case（TRN-003/004/005）生效，其余家族忽略该参数；
- dev 缩小跑的结果带 `--allow-invalid-params`，**不算正式 MLPerf PASS**；正式提交必须用完整数据集且不放行该参数；
- `data-dir` 与 `results-dir` 必须在不同文件系统（CAP-03），否则需 `--skip-fs-separation-gate`。

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
  --mode plan --data-dir C:\MLPerfStorageTest\data --results-dir C:\MLPerfStorageTest\results
```

正式执行：

```powershell
.\.venv\Scripts\python.exe -m full_test_plan_cases.run_all `
  --mode execute --confirm-dut --init-results --cleanup-data `
  --cleanup-root C:\MLPerfStorageTest\data --launcher single --prepare `
  --data-dir C:\MLPerfStorageTest\data --results-dir C:\MLPerfStorageTest\results
```

`run_all` 直接启动每个 `cases/test_*.py` 文件；在 `execute`、`dry-run` 或 `preflight` 模式下第一个非零返回码会触发套件级 fast-fail。

正式 `PASS` 只能来自真实 native workload 的返回结果和输出文件；`DRY_RUN` 不算通过。
