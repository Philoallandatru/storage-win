# AI SSD — 全部 72 个 case 的命令

> 来源：`docs/AI_SSD_ALL_CASE_PLAN.xlsx`（6 个家族，共 72 个 case）
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

## 1. 跑单个 case（编辑 .cmd 顶上的路径后双击或命令行调用）

```cmd
ai_ssd_test_cases\cmd\training\test_ai_trn_006.cmd
```

## 2. 一次跑完全部 72 个

```powershell
# 1) 先把所有 .cmd 顶上的 DUT 和 RES 改成你那边的盘符
#    （或者在 shell 里 export DUT / RES 覆盖）
# 2) 跑批跑脚本
pwsh -NoProfile -Command "& cmd /c 'scripts\run_72_cases_smoke.cmd'"
```

`SMOKE_MODE=quick`（默认）：每个家族跑 1-2 个代表 case
`SMOKE_MODE=full`：跑完全部 72 个

## 3. 自己挑几个跑（PowerShell 临时拼）

```powershell
$cases = @(
  "ai_ssd_test_cases\cmd\base\test_ai_base_001.cmd",
  "ai_ssd_test_cases\cmd\training\test_ai_trn_006.cmd",
  "ai_ssd_test_cases\cmd\vectordb\test_ai_vdb_015.cmd",
)
foreach ($c in $cases) { cmd /c $c }
```

## 4. 在哪里看每次跑的结果

每次跑完会在 `<RES>\AI-<家族>-<编号>\<时间戳>\` 下写一份 `verdict.json`。状态值含义：

- `PASS` — 跑完了，内部 runner 报成功
- `BLOCKED` — runner 直接拒了，缺前置条件（比如 `--execute` / `--scale-mb` / `--confirm-dut`，或没 `mlpstorage init`）
- `FAIL` — 内部 workload 退出码非零

## 5. 跑之前确认环境

- Python：`.venv\Scripts\python.exe`（3.12.3）
- mlpstorage CLI 在 PATH 上：`.venv\Scripts\mlpstorage.exe`
- 跑过 `mlpstorage init AI-SSD-Test <RES>`（只有 native 的 CKP / KV / TRN 才需要；`.cmd` 会在需要的时候自动跑一次）
- 用到 Milvus 的 VDB case：要么启一个 `127.0.0.1:19530` 的 Milvus，要么给 `.cmd` 加 `--backend lite` 走 Milvus Lite
- `DUT` 和 `RES` 必须在 **不同的物理盘** 上；runner 会直接拒掉路径嵌套的情况

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

详见 `docs\AI_SSD_SMOKE_RUN_20260811.md`，简单总结：

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
