# MLPerf Storage Windows Offline Bundle

这个目录由构建脚本打包成一个可迁移的 Windows 离线安装包。

安装包包含：

- Python 3.12 runtime 和当前已验证的 `.venv`；
- MLPerf Storage 源码、配置和 72 个 native Case 入口；
- DLIO、KV Cache、VectorDB 所需的仓库代码和 Python 依赖；
- Microsoft MPI 安装器（如果构建机存在）。

目标机必须是 Windows x64。安装包不包含测试数据、Checkpoint 或 Milvus 服务；这些内容应单独复制到目标盘。

## 安装

解压后，在安装包根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -InstallRoot C:\MLPerfStorage
```

也可以双击 `install.cmd`。如果目标机没有 Microsoft MPI，安装脚本会调用包内安装器，可能需要管理员权限。

## 运行

双击 `run.cmd` 默认先做不执行 workload 的 preflight；这是为了避免在没有确认目标盘和 DUT 参数时误写入测试盘：

```powershell
.\run.ps1 -Case AI-TRN-003 -Mode preflight -DataDir D:\ai_ssd\data -ResultsDir E:\ai_ssd\results
```

真正运行前先初始化结果目录，然后显式确认 DUT：

```powershell
.\run.ps1 -InitResults -OrgName ai-trn-003 -Case AI-TRN-003 `
  -Mode execute -Prepare -ConfirmDut `
  -DataDir D:\ai_ssd\data -ResultsDir E:\ai_ssd\results
```

`run.ps1` 只负责调用安装后的 Case 文件；Case 文件直接调用 `mlpstorage`。它不会联网、不会自动下载依赖，也不会把 preflight/dry-run 标记为正式 PASS。

VectorDB Case 仍要求目标机已有可访问的 Milvus 服务。Base、Mixed、trace replay 等没有对应 native `mlpstorage` 命令的 Case 会明确返回 `BLOCKED`。
