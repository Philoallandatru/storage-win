# AI SSD 仓库整理方案与路线图（REORGANIZATION PLAN）

> 状态：D1/D2/D4/D5 已拍板（2026-08-13），D3 待定 · 待执行 Phase 0
> 生成：2026-08-13 · 依据：`_HANDOFF.md`（2026-08-12）+ 本会话现状审查
> 范围：仓库卫生 → 上游包化 → 文档/路线图 →（可选）架构收敛
> 说明：本文件是本地 AI SSD 体系的规划文档，不属于上游 MLPerf 内容。

---

## 一、目标

1. **根目录清爽**：根目录只保留"入口 + 本地资产"，上游 MLPerf Storage 内容整体收入独立目录。
2. **上游包化**：上游代码作为独立包安装使用（`pip install -e` / `uv run`），本地体系不再直接修改它。
3. **有规划**：文档单一入口 + 正式路线图，`_HANDOFF.md` 的待办转为可追踪状态表。

## 二、现状诊断（事实）

### 2.1 Git 工作区不干净（8 项）

| 状态 | 文件 | 问题 | 建议 |
|---|---|---|---|
| `M` | `uv.lock` | 依赖版本变动，未决定提交或还原 | 决策点 D1 |
| `??` | `_HANDOFF.md` | 临时交接件，未 gitignore | Phase 3 并入路线图后删除 |
| `??` | `.reasonix/` | 工具产物，不应入库 | 加入 `.gitignore` |
| `??` | `archive/root_artifacts/` | 90MB 本地产物（`.smoke_*` 等） | 加入 `.gitignore`（`*.html` 已兜住 `_arch_review.html`，但需显式补充） |
| `??` | `docs/AI_SSD_NATIVE_CASES_MLPSTORAGE_COMMANDS.xlsx` | 文档状态表已列其为"当前有效入口"却未提交 | 决定提交或改为生成物（决策点 D2） |
| `??` | `scripts/_resolve_case_args.py`、`build_all_cases_excel.py`、`run_mlpstorage_case.ps1` | 新脚本未提交 | 评审后提交 |
| `??` | `setup_env.cmd` | 本机 Windows 环境脚本 | 提交（与 `setup_env.sh` 并列） |

### 2.2 上游/本地边界模糊

用 `git diff origin/main...HEAD` 核对（本地分支相对 origin/main：179 新增 / 50 修改 / 7 重命名 / 0 删除）：

- **上游原有（fork 自带）**：`mlpstorage_py/`、`configs/`、`kv_cache_benchmark/`、`vdb_benchmark/`、`patches/`、`ansible/`、`test/`、根目录 11 个大文档（README、Rules.md、Submission_guidelines.md、ManPage.md、CODE_IMPROVEMENT_PLAN.md、IMPLEMENTATION_PLAN.md、BugsFixedInVersions.md、DEVELOPMENT.md、CONTRIBUTING.md、LICENSE.md、CLAUDE.md）、`pyproject.toml`、`uv.lock`、`mlpstorage`、`mlpstorage.yaml`、`setup_env.sh`、`.github/`。
- **本地新增**：`full_test_plan_cases/`、`trace_test_cases/`、`archive/`、`windows_offline_bundle/`、`tools/`、`scripts/`（54 个新增）、`tests/`（14 个新增）、`docs/AI_SSD_*` 与 `docs/research/`、`run_case.cmd`、`AGENTS.md`、`setup_env.cmd`。
- **混合目录**：`scripts/`、`tests/`、`docs/` 内上游与本地文件并存，需按文件粒度拆分。
- **上游已演进，本地分支落后**：`origin/main` 已有 `checkpointing/`、`training/`、`plans/` 三个目录，本地 `HEAD` 没有（本地基于旧基线开发）。后续若跟上游同步会冲突，需明确策略（决策点 D3）。

### 2.3 包化改造的三个技术耦合点（关键）

| 耦合 | 位置 | 影响 |
|---|---|---|
| **打包耦合** | `pyproject.toml` 第 83-84 行：`packages = {find = {include = ["mlpstorage_py*", "vdbbench*", "full_test_plan_cases*"]}}` | 上游包和本地 case 体系打进了**同一个发行版**；拆目录时必须拆分打包配置 |
| **路径耦合** | `mlpstorage_py/config.py:42`：`CONFIGS_ROOT_DIR = os.path.join(os.path.split(os.path.abspath(os.path.dirname(__file__)))[0], "configs")` | 依赖"`mlpstorage_py` 的上一级目录 = 仓库根 + `configs`"；`configs/` 必须与 `mlpstorage_py/` 同级搬移 |
| **调用耦合** | `full_test_plan_cases/run_case.py` 通过 `python -m mlpstorage_py.main` 调用；`mlpstorage` 根脚本用 `uv run --project` | 包化后调用方式需同步验证（editable install 后 `mlpstorage` 命令可用） |

### 2.4 本地已修改上游代码（与"不要动它"矛盾）

本地分支在三个上游目录内均有改动，功能依赖**不能丢**：
- `mlpstorage_py/`：**21 个文件（+549/-81）**——Windows 适配（`utils.py` 的 `CommandLineToArgvW` 命令解析、`utf-8-sig` 编码）、DLRM 支持（`config.py` 的 `MODELS_OPEN`）、capacity_gate、rules 检查。
- `vdb_benchmark/`：**22 个文件（+1937/-82）**——trace capture/replay 体系（`vdbbench/replay.py`、`trace_runner.py`、`windows_direct_io.py` 等）、Windows 适配。
- `kv_cache_benchmark/`：**3 个文件（+55/-7）**。

→ 决策点 D4。

## 三、目标结构

```
storage/                          # 仓库根：本地 AI SSD 体系 + 上游包
├── third_party/                  # MLPerf Storage 上游整体（vendored，只安装不改）
│   ├── mlpstorage_py/  configs/  kv_cache_benchmark/  vdb_benchmark/
│   ├── patches/  ansible/  test/
│   ├── pyproject.toml  uv.lock  mlpstorage  mlpstorage.yaml  setup_env.sh
│   ├── .github/  .env.example  .python-version
│   ├── README.md  Rules.md  ManPage.md  …（上游根文档）
│   └── docs/                     # 上游文档（QUICK_START、PARQUET_FORMATS 等）
├── full_test_plan_cases/         # 本地 case 体系（唯一数据源）※ 从上游 pyproject 拆出
├── trace_test_cases/  scripts/  tools/  tests/  windows_offline_bundle/
├── docs/                         # 本地文档（AI_SSD_*、REORGANIZATION_PLAN、ROADMAP）
├── archive/  run_case.cmd  setup_env.cmd  AGENTS.md
└── README.md                     # 本地总览（新建；上游 README.md 随包进 third_party/）
```

- 安装方式：`pip install -e ./third_party`（上游包）+ 本地包自管；`kv_cache_benchmark/`、`vdb_benchmark/` 各自带 `pyproject.toml`，可独立 `pip install -e`（Phase 2 步骤 3 拆分后，`third_party/pyproject.toml` 的 setuptools 只收 `mlpstorage_py*`、`vdbbench*`）；`run_case.py` 改用 `-m mlpstorage_py.main`（已兼容）。
- "不要动它"的含义：`third_party/` 内只做**让它可安装**的最小改动（打包配置、路径），功能代码不再改；本地需求通过 `patches/` 或 overlay 表达（见 D4，已拍板：随目录携带 + `PATCHES.md` 记录）。

## 四、分阶段执行计划

### Phase 0 — 基线冻结（0.5 天）
- **步骤**：决策点 D1/D2/D4/D5 已拍板并记录于第六节，**D3（上游同步策略）待定**；冻结 `case_catalog.json` 与 `source/FULL_TEST_PLAN.xlsx` 的一致性策略（承接 `_HANDOFF` 待办 6：选"JSON 为准，xlsx 仅生成物"或"xlsx 为准，JSON 由工具生成"）。
- **验收**：D3 有结论；一致性策略写入文档并在 `tools/generate_full_test_plan_cases.py` 中落实。

### Phase 1 — 仓库卫生（0.5 天）
- **步骤**：
  1. `.gitignore` 补充：`.reasonix/`、`archive/root_artifacts/`、`_HANDOFF.md`、`docs/*.xlsx`（D2 已拍板：命令表视为生成物）。
  2. 处理 8 项脏状态：提交该提交的（`setup_env.cmd`、`scripts/` 三个新脚本、本方案文档），还原或提交 `uv.lock`（D1）。
  3. 删除/归档临时件：`_arch_review.html`（已忽略，可物理删除）、`_HANDOFF.md`（并入路线图后删）。
- **验收**：`git status --porcelain` 为空；`git status --ignored` 中临时产物被显式忽略。

### Phase 2 — 上游包化（1-2 天，核心）
- **步骤**：
  1. `git mv` 上游条目进 `third_party/`（保留历史）：`mlpstorage_py configs kv_cache_benchmark vdb_benchmark patches ansible test` + 根文档（README、Rules.md、Submission_guidelines.md、ManPage.md、CODE_IMPROVEMENT_PLAN.md、IMPLEMENTATION_PLAN.md、BugsFixedInVersions.md、DEVELOPMENT.md、CONTRIBUTING.md、LICENSE.md、CLAUDE.md）+ `pyproject.toml uv.lock mlpstorage mlpstorage.yaml setup_env.sh .env.example .python-version .github`。`.gitignore` 是上游+本地混合文件（本地加 10 行 AI SSD 段），**留根目录**由本地维护，不搬。
  2. `docs/` 按文件粒度拆分：上游文档进 `third_party/docs/`，本地 `AI_SSD_*`、`research/` 留 `docs/`。`docs/README.md` 是上游+本地混合文件（本地加了 AI SSD 指南段落），拆分时各取所需。
  3. 拆分打包配置：`third_party/pyproject.toml` 只含 `mlpstorage_py*`、`vdbbench*`；本地新建 `pyproject.toml` 管理 `full_test_plan_cases` 等（或改由 `scripts/` 内工具调用）。
  4. 验证路径耦合：`mlpstorage_py/config.py:42` 在搬移后仍成立（`configs` 与 `mlpstorage_py` 同级），跑 `mlpstorage training configview` 确认 `CONFIGS_ROOT_DIR` 生效。
  5. 安装验证：`pip install -e ./third_party` 成功；`full_test_plan_cases` 的 pytest 与 smoke 缩小版通过（`tests/test_full_test_plan_cases.py`、`tests/test_native_case_scripts.py`）。
- **验收**：`third_party/` 内 `git log` 历史完整；本地 CI 命令（pytest、`run_case.cmd`）全部通过；上游代码零新增修改（D4 的 patch 除外）。

### Phase 3 — 文档与路线图（0.5 天）
- **步骤**：
  1. `_HANDOFF.md` → 正式 `docs/AI_SSD_ROADMAP.md`（第五节路线图 + 待办状态表 + 关键命令速查），更新后删除 `_HANDOFF.md`。
  2. 更新 `docs/AI_SSD_DOCUMENT_STATUS.md`：补新结构、`REORGANIZATION_PLAN.md`、ROADMAP 入口。
  3. 修正过期引用：`archive/README.md:22` 的"72 legacy .cmd 索引（入口在 `ai_ssd_test_cases/cmd/`）"——目录已删除，且被引的 `docs/AI_SSD_ALL_CASES_COMMANDS.md` 已移入 `archive/docs_historical/`，需改指向；`docs/README.md` 的归档链接已正确指向 `archive/docs_historical/`（本地已改），仅需核对无需修改。
- **验收**：`rg "ai_ssd_test_cases"` 仅命中 `archive/docs_historical/` 历史文件与已修正的 `archive/README.md`；文档状态表与目标结构一致。

### Phase 4 — 架构收敛（可选，另行排期）
- 占位符替换 4 处拷贝收敛（`run_case.py` / `generate_full_test_plan_cases.py` / `_resolve_case_args.py` / `build_all_cases_excel.py`）→ 抽公共模块。
- `cluster_collector.py`（5096 行）接口化 + 内嵌脚本模板化（`interfaces/collector.py` 已定义接口）。
- **验收**：单元测试全绿；`run_case.cmd` 行为不变。

### Phase 5 — 技术待办落地（承接 `_HANDOFF` 待办 1-3）
- DLRM MPI finalize abort（Windows + DLIO/parquet）；VDB 跑通（Milvus server）；`vdb_benchmark` 安装（PEP 517）。
- **验收**：缩小版 smoke 全家族 PASS（`scripts/smoke_all_cases.py`）。

## 五、路线图（承接 `_HANDOFF` 待办）

| # | 事项 | 优先级 | 所属 Phase | 状态 | 备注 |
|---|---|---|---|---|---|
| 1 | DLRM run 的 MPI finalize abort | P1 | 5 | 待办 | Windows 需解决，Linux 无碍 |
| 2 | VDB 跑通（Milvus server + `--vdb-config vdb_smoke.yaml`） | P1 | 5 | 待办 | 需 docker |
| 3 | `vdb_benchmark` 安装（PEP 517） | P1 | 5 | 待办 | 排查 setuptools build |
| 4 | `cluster_collector.py` 接口化 | P2 | 4 | 待办 | 架构审查 Top 建议 |
| 5 | 占位符替换 4 处拷贝收敛 | P2 | 4 | 待办 | — |
| 6 | `case_catalog.json` 与 xlsx 源一致性 | P0 | 0 | 待决策 | 决策点 D2 关联 |
| 7 | 仓库卫生（gitignore、untracked、临时件） | P0 | 1 | 待办 | 见 2.1 |
| 8 | 上游包化（`third_party/` 目录） | P0 | 2 | 待办 | 本方案核心 |
| 9 | `_HANDOFF` → 正式路线图 | P0 | 3 | 待办 | 本文档即草案 |

## 六、决策点（需评审拍板）

| # | 决策 | 选项 | 推荐 | 拍板结果（2026-08-13） |
|---|---|---|---|---|
| D1 | `uv.lock` 的 `M` | 提交依赖变动 / `git checkout` 还原 | 若无刻意改动则还原；有则提交 | ✅ **还原** |
| D2 | `docs/AI_SSD_NATIVE_CASES_MLPSTORAGE_COMMANDS.xlsx` | 提交为正式产物 / 视为生成物（gitignore + 由 `build_all_cases_excel.py` 重生成） | 生成物（与待办 6 的"单一数据源"一致） | ✅ **视为生成物** |
| D3 | 上游同步策略 | 定期 merge `origin/main`（含 `checkpointing/ training/ plans/`）/ 冻结不跟 | 冻结至包化完成，之后定期 merge 到 `third_party/` 内 | ⏳ 待定 |
| D4 | 本地已改的上游代码（`mlpstorage_py` 21 文件、`vdb_benchmark` 22 文件、`kv_cache_benchmark` 3 文件，见 2.4） | A. 全部抽成 `patches/`（`third_party/` 纯净，安装时 apply）；B. 随目录携带（`third_party/` = 上游+补丁混合，用 `third_party/PATCHES.md` 记录增量） | A 更符合"不要动它"，成本高；B 务实，先落地 | ✅ **随目录携带（B）**：`third_party/PATCHES.md` 记录增量 |
| D5 | 上游目录名 | `upstream/` / `vendor/` / `third_party/` | `upstream/`（语义直白） | ✅ **`third_party/`** |

## 七、风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| `pyproject.toml` 拆包后 editable install 路径变化 | 开发环境失效 | Phase 2 步骤 5 先做安装验证，再搬 `full_test_plan_cases` |
| `CONFIGS_ROOT_DIR` 相对路径在其他调用点被隐式依赖 | 运行期找不到 workload yaml | 搬移后跑 `configview` + 4 家族 smoke 各一次 |
| `.github/` CI 引用旧路径 | CI 红 | 搬移时同步改 CI 工作目录或延后处理 |
| `git mv` 大目录 + 后续 merge 上游 | 冲突面大 | 包化期间冻结上游同步（D3） |
| D4 选 A（patch 化）工作量大 | Phase 2 延期 | B 已拍板（随目录携带）；patch 化作为 Phase 4 增量项 |

---

*本文档为规划草案；D1/D2/D4/D5 已拍板、D3 待定。D3 拍板后按 Phase 0→3 顺序执行（Phase 0 起点：待办 6 一致性策略）。*
