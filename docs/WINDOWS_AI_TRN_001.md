# Windows 原生 AI-TRN-001

`AI-TRN-001` 是 UNet3D/A100 的 OPEN 训练数据供给 Case。它不属于当前 v3.0 CLOSED 的 B200/MI355 三个 Training Native Case，因此不能把它的结果写成 CLOSED PASS。

## 环境

在仓库根目录执行：

```powershell
.\tools\setup_windows_build_env.ps1 `
    -PythonIndexUrl https://pypi.tuna.tsinghua.edu.cn/simple
. .\tools\activate_windows_venv.ps1
```

这条流程使用 Python 3.12、Microsoft MPI 和锁定的 Git 版 DLIO，不使用 WSL 或 Docker。安装完成后应能通过：

```powershell
.\.venv\Scripts\python.exe -c "import dlio_benchmark; print('dlio=ok')"
Get-Command mpiexec
```

## 正式运行

结果盘和数据盘应分开；下面的 `D:` 是 DUT 数据盘，`E:` 是结果盘：

```powershell
.\.venv\Scripts\python.exe tools\run_ai_trn_001_windows.py `
    --data-dir D:\MLPerfStorageTest\data\AI-TRN-001 `
    --results-dir E:\MLPerfStorageTest\results\AI-TRN-001 `
    --prepare --init-results --confirm-dut `
    --mpi-bin mpiexec --accelerators 1 --client-memory-gb 53
```

脚本固定使用 `dataset.num_files_train=7200`，约 983 GiB。容量不足时应记录为 `BLOCKED(CAP-01)`；不要把 1 文件或小数据 smoke 冒充正式 Case。

## 快速链路 smoke

若只验证 Windows 的 Python/MPI/DLIO 启动链路，可以直接用仓库 CLI 运行 1 个文件，但必须标记为 smoke，不能用于 AU、吞吐或正式 PASS：

```powershell
mlpstorage open training unet3d run file `
    --systemname ai-trn-001-smoke --hosts 127.0.0.1 `
    --client-host-memory-in-gb 1 --num-client-hosts 1 `
    --num-accelerators 1 --accelerator-type a100 `
    --data-dir D:\MLPerfStorageTest\data\AI-TRN-001-smoke `
    --results-dir E:\MLPerfStorageTest\results\AI-TRN-001-smoke `
    --exec-type mpi --mpi-bin mpiexec `
    --params dataset.num_files_train=1 `
    --allow-invalid-params
```

Windows 配置会自动将 Linux workload 中的 `reader.multiprocessing_context=fork` 改为 `spawn`；显式传入其他上下文仍会被校验拒绝。
