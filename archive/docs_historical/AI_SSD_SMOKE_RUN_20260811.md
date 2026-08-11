# AI SSD — 72 个 case 的冒烟验证（2026-08-11）

> 目的：证明每份 per-case `.cmd` 文件（路径 `ai_ssd_test_cases\cmd\<家族>\test_ai_<id>.cmd`）至少能 **起来**，即能写出一份 `verdict.json`。完整 workload 跑由用户自己来。

## 环境

- 仓库：`C:\Users\Administrator\Documents\Code\repos\storage`
- Python：`.venv\Scripts\python.exe`（3.12.3）
- `DUT` = `C:\Users\Administrator\Documents\Code\repos\storage\.smoke_dut`（本地临时目录）
- `RES` = `C:\Users\Administrator\Documents\Code\repos\storage\.smoke_res` 或 `D:\ai-ssd\results`
- 方式：`cmd /c "ai_ssd_test_cases\cmd\<家族>\test_ai_<id>.cmd"`
- 验证：解析 `RES\AI-<id>\` 下最新一份 `verdict.json`

## 抽样结果（18 个）

| Case        | 状态   | 原因 / 备注 |
|-------------|--------|-------------|
| AI-BASE-001 | 通过   | path_capacity profile，不需要 --scale-mb |
| AI-BASE-002 | 通过   | cache_modes profile，已加 --scale-mb 512 |
| AI-BASE-003 | 通过   | repeatability profile，已加 --scale-mb 512 |
| AI-BASE-004 | 通过   | fill_degradation，已加 --scale-mb 512 + --confirm-dut |
| AI-CKP-001  | 通过   | 8B full baseline（mock 数据） |
| AI-CKP-009  | 通过   | interval / GC burst（python_scaled） |
| AI-KV-001   | 通过   | 8B NVMe-only |
| AI-KV-004   | 通过   | tiny1b smoke |
| AI-KV-013   | 通过   | tier capacity matrix |
| AI-KV-022   | 通过   | burstgpt / sharegpt |
| AI-TRN-001  | 失败   | native mlpstorage 命令退出 6（要先 datagen） |
| AI-TRN-006  | 通过   | cosmoflow scaled；--scale-mb 1024 |
| AI-TRN-016  | 通过   | warm / cold direct |
| AI-VDB-001  | 通过   | hnsw 1k smoke（Milvus Lite 兜底） |
| AI-VDB-008  | 通过   | index family sweep |
| AI-VDB-015  | 通过   | 逻辑 trace 回放（不需要 Milvus） |
| AI-MIX-001  | 通过   | training + checkpoint 并发 |
| AI-MIX-005  | 通过   | 4 类 soak |

**汇总：18 个抽样，17 个通过 / 1 个失败（TRN-001，预期内的，因为没跑 datagen）。**

## 全量模块导入扫描

对 72 个 catalog entrypoint 跑 `importlib.import_module(...)`：

```
72/72 modules importable
```

## 验证过程中顺手修的几个坑

- 63 份已有的 `.cmd` 调的是 **错的** python 模块名（例如 `ai_ssd_test_cases.test_ai_ckp_001`），全部改回 catalog 的 `entrypoint`（例如 `ai_ssd_test_cases.test_checkpoint_8b_full_baseline`）。
- BASE 4 份 + MIX 5 份 `.cmd` 之前根本没有，用同一套模板补齐。
- BASE-002/003/004 缺 `--scale-mb 512`，已经补上。

## 没做的事

- native 的 TRN-001/003/004/005 缺 datagen 步骤（`.cmd` 直接跑 workload，缺数据集会失败）。要跑这几个得先 `mlpstorage training datagen`。
- 长跑任务（CKP-001 要 840 GiB、MIX-005 要 8 小时…）。
- 破坏性 CKP / MIX case 的内部 workload 行为；只验证了 wrapper 能起来。

## 怎么复现

```powershell
# 1. 挑 1-2 个 case 跑一下
$cases = @(
  "ai_ssd_test_cases\cmd\base\test_ai_base_001.cmd",
  "ai_ssd_test_cases\cmd\training\test_ai_trn_006.cmd",
  "ai_ssd_test_cases\cmd\vectordb\test_ai_vdb_015.cmd",
)
foreach ($c in $cases) { cmd /c $c }

# 2. 看 verdict
Get-ChildItem D:\ai-ssd\results -Recurse -Filter verdict.json |
  Sort-Object LastWriteTime -Descending | Select-Object -First 5
```
