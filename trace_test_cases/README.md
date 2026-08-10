# AI SSD Trace cases

这里的入口和 `full_test_plan_cases/cases/` 分开：

- Native 目录直接调用 `mlpstorage open ...`；
- Trace 目录调用仓库已经实现的 `vdbbench` capture/replay 入口；
- Trace 结果必须标为 `TRACE-CAPTURE` 或 `TRACE-REPLAY`，不能冒充 Native。

当前目录只登记已经有独立执行脚本并完成实际验证的 `AI-VDB-015`。KV benchmark
内部虽然存在 tracer 实现，但当前 `mlpstorage open kvcache` CLI 没有暴露
`--io-trace-log`，也没有仓库内已验证的 KV replay 入口，因此不生成 KV trace case，
只在需求文档中保留为后续扩展要求。

## AI-VDB-015

先在有 Milvus 的机器上捕获正式 trace：

```powershell
python trace_test_cases\test_ai_vdb_015.py `
  --mode execute --record --confirm-dut `
  --config vdb_benchmark\vdbbench\benchmark\configs\windows_trace_smoke.yaml `
  --source-trace C:\ai-ssd-results\AI-VDB-015\source_trace.csv `
  --source-results C:\ai-ssd-results\AI-VDB-015\source_run `
  --data-dir D:\ai-ssd\AI-VDB-015\run-001 `
  --results-dir C:\ai-ssd-results\AI-VDB-015\replay-001 `
  --cleanup --cleanup-root D:\ai-ssd\AI-VDB-015
```

若已有经 manifest 校验的 source trace，只执行回放：

```powershell
python trace_test_cases\test_ai_vdb_015.py `
  --mode execute --confirm-dut `
  --source-trace C:\ai-ssd-results\AI-VDB-015\source_trace.csv `
  --data-dir D:\ai-ssd\AI-VDB-015\run-001 `
  --results-dir C:\ai-ssd-results\AI-VDB-015\replay-001 `
  --cleanup --cleanup-root D:\ai-ssd\AI-VDB-015
```

`--cleanup` 只删除 `--data-dir`，不会删除 source trace 或 results。脚本会在清理后输出 `TEST_DATA_CLEANED=True`。
