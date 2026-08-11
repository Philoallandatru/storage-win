# AI SSD — 全部 72 个 case 的命令

> 来源：`archive/docs_historical/AI_SSD_ALL_CASE_PLAN.xlsx`（6 个家族，共 72 个 case）
> **每个 case 对应一份独立的命令文件**，路径是 `ai_ssd_test_cases\cmd\<家族>\test_ai_<id>.cmd`
> `.cmd` 文件已经把 `PY`、`DUT`、`RES` 和正确的 python 模块与参数都设好了。
> 跑之前只要把 `.cmd` 顶上的 `DUT` 和 `RES` 改成你的盘符（或者在 shell 里 export 这两个环境变量）就行。

## 0. 文件分布

```
ai_ssd_test_cases\cmd\
  _common.cmd                          <-- 环境变量参考（仅文档）
  base\test_ai_base_001..004.cmd       （4 个）
  checkpoint\test_ai_ckp_001..009.cmd  （9 个）
  kvcache\test_ai_kv_001..022.cmd      （22 个）
  training\test_ai_trn_001..016.cmd    （16 个）
  vectordb\test_ai_vdb_001..016.cmd    （16 个）
  mixed\test_ai_mix_001..005.cmd       （5 个）
                                   ----
                                   72 份 .cmd，一个 case 一份
```

每份都是自洽的：`setlocal` → `pushd` 回仓库根 → 用 catalog 里对应的 python 模块和参数跑 → `endlocal`。

## 1. 跑单个 case — 用环境变量，不要编辑 .cmd

```cmd
:: 1) 设必填的 DUT 和 RES
set DUT=E:\big-ssd\data
set RES=D:\results

:: 2) 可选：指定 python（默认会探测仓库里的 .venv\Scripts\python.exe）
set PY=C:\path\to\python.exe

:: 3) 跑
ai_ssd_test_cases\cmd\training\test_ai_trn_006.cmd
```

`.cmd` 自己做的事：

- `PY` 没设：探测 `%~dp0..\..\..\.venv\Scripts\python.exe`（相对 .cmd 位置），找不到回退到 PATH 上的 `python`
- `DUT` / `RES` 没设：直接报错退出，不会瞎猜盘符
- `DUT` 目录不存在：报错退出
- `RES` 目录不存在：自动创建
- `pushd` 用相对路径，**clone 到任何位置都能跑**
- PATH 自动加上 `.venv\Scripts`，所以 `mlpstorage` 命令能搜到

## 2. 一次跑完全部 72 个

```powershell
$env:DUT = 'E:\big-ssd\data'
$env:RES = 'D:\results'
pwsh -NoProfile -Command "& cmd /c 'scripts\run_72_cases_smoke.cmd'"
```

`SMOKE_MODE=quick`（默认）：每个家族跑 1-2 个代表 case
`SMOKE_MODE=full`：跑完全部 72 个

## 3. 自己挑几个跑（PowerShell 临时拼）

```powershell
$env:DUT = 'E:\big-ssd\data'
$env:RES = 'D:\results'
$cases = @(
  "ai_ssd_test_cases\cmd\base\test_ai_base_001.cmd",
  "ai_ssd_test_cases\cmd\training\test_ai_trn_006.cmd",
  "ai_ssd_test_cases\cmd\vectordb\test_ai_vdb_015.cmd",
)
foreach ($c in $cases) { cmd /c $c }
```

## 4. 在哪里看每次跑的结果

每次跑完会在 `%RES%\AI-<家族>-<编号>\<时间戳>\` 下写一份 `verdict.json`。状态值含义：

- `PASS` — 跑完了，内部 runner 报成功
- `BLOCKED` — runner 直接拒了，缺前置条件（比如 `--execute` / `--scale-mb` / `--confirm-dut`，或没 `mlpstorage init`）
- `FAIL` — 内部 workload 退出码非零

## 5. 环境变量速查

| 变量 | 必填？ | 默认 | 说明 |
|------|--------|------|------|
| `PY`  | 否 | 探测 `.venv\Scripts\python.exe`，回退到 `python` | python 解释器 |
| `DUT` | 是 | 报错退出 | 数据盘根目录，必须存在且可写 |
| `RES` | 是 | 报错退出 | 结果目录，自动创建；必须与 DUT 在不同物理盘 |

- 用到 Milvus 的 VDB case：要么启一个 `127.0.0.1:19530` 的 Milvus，要么给 `.cmd` 加 `--backend lite` 走 Milvus Lite

## 6. xlsx 命令列里漏掉的参数（已修）

| 家族 / Case | xlsx 漏的 | .cmd 已经补上 |
|-------------|-----------|----------------|
| 全部 Training | `--execute` | 由 tools runner 自动注入 |
| BASE-002/003/004 | `--scale-mb`（cache / repeatability / fill profile 都强制要） | `.cmd` 加了 `--scale-mb 512` |
| BASE-004、全部 CKP、全部 MIX | `--confirm-dut`（破坏性 case） | `.cmd` 加了 |
| 全部 python_scaled case（TRN 2/6-16、CKP 8/9、KV 9-22、VDB 015、MIX 1-5） | `--scale-mb` | `.cmd` 加了 `--scale-mb 512` |
| VDB-015 | `--source-trace`（默认 `trace_test_cases\fixtures\logical_io_smoke.csv`） | `.cmd` 加了默认路径 |

`.cmd` 文件里这些都已经补齐了，直接复制路径就能跑。

## 7. 抽样冒烟跑结果

详见 `archive/docs_historical/AI_SSD_SMOKE_RUN_20260811.md`，简单总结：

| 家族 | 抽样 | 结果 |
|------|------|------|
| BASE  | 4      | 4 通过（`--scale-mb 512` 已注入） |
| CKP   | 2/9   | 2 通过 |
| KV    | 4/22  | 4 通过 |
| TRN   | 3/16  | 2 通过 + 1 失败（TRN-001 需先跑 native datagen） |
| VDB   | 3/16  | 3 通过（VDB-001/002/008 需 Milvus；VDB-015 trace 不需要） |
| MIX   | 2/5   | 2 通过 |

每份 `.cmd` 都已人工验证：
1. 解析到正确的 python 模块（用 catalog 的 `entrypoint`）
2. 带上必需参数
3. 跑完在 `RES` 下写出 `verdict.json`
