# MLPerf Storage Windows 离线包构建手册

本手册针对“在线构建机准备环境，离线目标机直接安装运行”的场景。所有依赖下载、MPI 获取和 Python 环境构建都在在线构建机执行；目标机只需要解压最终 ZIP，不需要联网、uv 或 pip。

## 1. 仓库实际要求

- Windows x64；Python `>=3.12,<3.13`。
- 在线构建机需要 `uv`、Git 和网络访问 PyPI/GitHub。
- Python 依赖默认使用清华 PyPI 镜像；可用 `-PythonIndexUrl` 替换为公司内网或其他镜像。
- Windows MPI 使用 Microsoft MPI；Case 的 Windows 默认 MPI 命令是 `mpiexec`。
- `pyproject.toml` 已把 `s3dlio`、`s3torchconnector` 限制为 Linux 依赖；Windows 本地文件系统 Case 不需要 Docker。
- 构建包会复制已经准备好的 `.venv`，因此构建机需要预留较大空间。当前完整环境约 6 GB 原始大小，最终 ZIP 约 3.5 GB。

MPI 官方版本固定为 `v10.1.1`。脚本从 Microsoft-MPI 官方 GitHub Release 获取 `msmpisetup.exe` 和 `msmpisdk.msi`，并保存 SHA256 到 `.artifacts\msmpi\download-metadata.json`：

<https://github.com/microsoft/Microsoft-MPI/releases/tag/v10.1.1>

## 2. 一条命令完成构建

在仓库根目录打开 PowerShell：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\prepare_windows_offline_bundle.ps1 `
    -Output C:\MLPerfStorage-Windows-Offline.zip
```

默认会设置：

```powershell
$env:UV_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
```

如果使用内部镜像：

```powershell
.\tools\prepare_windows_offline_bundle.ps1 `
    -Output C:\MLPerfStorage-Windows-Offline.zip `
    -PythonIndexUrl https://pypi.example.local/simple
```

这个镜像只用于 Python 包安装；Microsoft MPI 仍从官方 Release 下载。

也可以在构建机上直接双击：

```text
tools\build_windows_offline_bundle.cmd
```

这个 `.cmd` 是“构建 ZIP”的入口；`windows_offline_bundle\install.ps1` 是打进 ZIP 后给目标机使用的安装器，两者不是同一个流程。

该脚本依次执行：

1. 下载 MS-MPI runtime 和 SDK；
2. 检查或创建 Python 3.12 `.venv`；
3. 根据 `uv.lock` 同步 root 项目、测试和 VectorDB 依赖；
4. 以 editable 方式安装 `kv_cache_benchmark` 和 `vdb_benchmark`；
5. 调用现有 `build_windows_offline_bundle.ps1` 生成 ZIP。

构建过程的目录结构如下：

```text
构建机仓库 + .venv + Python runtime + MS-MPI 安装包
                    │
                    ▼
临时 staging/
├── install.ps1 / install.cmd / run.ps1 / run.cmd
├── manifest.json
└── payload/
    ├── app/       项目源码、配置、Case
    ├── venv/      已同步的 Python 依赖
    ├── runtime/   Python 基础运行时
    └── mpi/       MSMpiSetup.exe
                    │
                    ▼
          MLPerfStorage-Windows-Offline.zip
```

如果希望同时在构建机安装 MPI：

```powershell
.\tools\prepare_windows_offline_bundle.ps1 `
    -Output C:\MLPerfStorage-Windows-Offline.zip `
    -InstallMpiRuntime -InstallMpiSdk
```

`-RecreateVenv` 会删除并重建仓库内 `.venv`，只在确认该目录就是本项目虚拟环境时使用：

```powershell
.\tools\prepare_windows_offline_bundle.ps1 `
    -Output C:\MLPerfStorage-Windows-Offline.zip `
    -RecreateVenv
```

## 3. 分步执行

### 3.1 下载 MPI

```powershell
.\tools\download_msmpi.ps1 `
    -Version v10.1.1 `
    -Destination .\.artifacts\msmpi
```

下载结果：

```text
.artifacts\msmpi\msmpisetup.exe
.artifacts\msmpi\msmpisdk.msi
.artifacts\msmpi\download-metadata.json
```

只运行 benchmark 不需要 SDK；SDK 主要用于需要 MPI 头文件/库的编译场景。目标机运行 Case 至少需要 runtime，安装后应能找到：

```powershell
Get-Command mpiexec
Test-Path 'C:\Program Files\Microsoft MPI\Bin\mpiexec.exe'
```

### 3.2 准备 Python 环境

```powershell
.\tools\setup_windows_build_env.ps1 `
    -PythonIndexUrl https://pypi.tuna.tsinghua.edu.cn/simple
```

脚本等价于仓库当前的环境流程：

```powershell
uv venv --python 3.12.3 .venv       # 仅当 .venv 不存在时
$env:UV_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
uv sync --frozen --all-groups --extra test --extra vectordb
uv pip install --python .venv\Scripts\python.exe --editable .\kv_cache_benchmark
uv pip install --python .venv\Scripts\python.exe --editable .\vdb_benchmark
```

### 3.3 激活 venv

普通激活：

```powershell
& .\.venv\Scripts\Activate.ps1
```

推荐使用仓库脚本，它还会设置 `PYTHONUTF8`、`PYTHONIOENCODING`、`MLPERF_SYSTEMNAME`：

```powershell
. .\tools\activate_windows_venv.ps1
```

注意前面的点和空格。必须 dot-source，普通执行子脚本不会修改当前 PowerShell 窗口的环境变量。

验证：

```powershell
python --version
python -c "import mlpstorage_py, dlio_benchmark; print('environment=ok')"
Get-Command mlpstorage
Get-Command mpiexec
```

### 3.4 单独生成 ZIP

如果 MPI 已经下载到本地，直接调用现有构建器：

```powershell
.\tools\build_windows_offline_bundle.ps1 `
    -Output C:\MLPerfStorage-Windows-Offline.zip `
    -MpiInstaller .\.artifacts\msmpi\msmpisetup.exe
```

构建器会复制 Python runtime、`.venv`、项目 Case 和必要配置，剔除项目的 `results`、`data`、`checkpoints`、`tests`、`fixtures`、Python 缓存；临时 staging 目录在结束后删除。

## 4. 构建后检查

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_windows_offline_bundle.py -q
Get-Item C:\MLPerfStorage-Windows-Offline.zip | Select-Object FullName,Length
```

ZIP 中应包含：

```text
install.cmd
install.ps1
run.cmd
run.ps1
payload\venv\Scripts\python.exe
payload\venv\Scripts\mlpstorage.exe
payload\runtime\python\python.exe
payload\mpi\MSMpiSetup.exe
```

## 5. 离线目标机操作

1. 将 ZIP 复制到目标 Windows x64 机器并解压；
2. 双击 `install.cmd`；如需安装 MPI，允许管理员权限提示；
3. 安装完成后，双击安装目录中的 `run.cmd` 做默认 preflight；
4. 正式执行时使用同一个入口传入实际数据盘、结果盘和 DUT 确认参数：

```powershell
run.cmd -InitResults -OrgName ai-trn-003 -Case AI-TRN-003 `
    -Mode execute -Prepare -ConfirmDut `
    -DataDir D:\ai_ssd\data -ResultsDir E:\ai_ssd\results
```

包不包含数据集、checkpoint、results、Milvus 服务或 Docker。VectorDB Case 仍要求目标机预先提供可访问的 Milvus 服务；不满足前置条件的 Case 应保持 `BLOCKED`，不会被脚本伪装成通过。

## 6. 常见问题

### `python` 不是 3.12.x

仓库要求 `>=3.12,<3.13`。安装 Python 3.12.x，并确保 `python.exe` 在 PATH；已有错误版本的 `.venv` 使用 `-RecreateVenv`。

### `uv sync` 因网络或依赖失败

这是构建机准备阶段的问题。构建机必须在线；目标机安装 ZIP 时不会重新执行 `uv sync`、`pip install` 或下载依赖。检查 `uv.lock` 是否与当前源码匹配后重试。

### `mpiexec` 找不到

先运行 `download_msmpi.ps1 -InstallRuntime`，或在目标机直接运行包内 `payload\mpi\MSMpiSetup.exe`。安装后重新打开 PowerShell，再执行 `Get-Command mpiexec`。

### ZIP 过大

ZIP 主要由 `.venv` 中的 Torch、TensorFlow 和 DLIO 依赖构成，不是测试数据。要进一步缩小，需要另做“按 Case 拆分依赖”的精简包，不能直接删除依赖后继续声称所有 training/checkpointing Case 都可运行。
