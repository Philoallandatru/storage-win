import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const repo = "C:/Users/Administrator/Documents/Code/repos/storage";
const outputDir = path.join(repo, "outputs", "ai_pc_consumer_ssd_case_matrix_v2_20260803");
const outputPath = path.join(outputDir, "AI_PC_CONSUMER_SSD_TEST_CASE_MATRIX_v2.xlsx");
const previewDir = path.join(outputDir, "preview");

const palette = {
  navy: "#17365D",
  blue: "#1F4E78",
  teal: "#0F6B78",
  cyan: "#DDEBF7",
  lightBlue: "#EAF3F8",
  green: "#E2F0D9",
  amber: "#FFF2CC",
  orange: "#FCE4D6",
  red: "#F4CCCC",
  gray: "#F3F6F9",
  dark: "#1F2937",
  border: "#C9D4E2",
  white: "#FFFFFF",
};

const modes = ["System Gate", "Native", "Scaled", "Trace/Replay", "Hybrid"];
const results = ["Not Started", "Pass", "Conditional", "Invalid", "Not Run"];

function colName(n) {
  let s = "";
  let x = n;
  while (x > 0) {
    const r = (x - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    x = Math.floor((x - 1) / 26);
  }
  return s;
}

function rangeFor(row, c1, c2) {
  return `${colName(c1)}${row}:${colName(c2)}${row}`;
}

function setTitle(sheet, title, subtitle, endCol) {
  sheet.mergeCells(`A1:${colName(endCol)}1`);
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${colName(endCol)}1`).format = {
    fill: palette.navy,
    font: { bold: true, color: palette.white, size: 16 },
    horizontalAlignment: "left",
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${colName(endCol)}1`).format.rowHeight = 30;
  sheet.mergeCells(`A2:${colName(endCol)}2`);
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${colName(endCol)}2`).format = {
    fill: palette.lightBlue,
    font: { color: palette.dark, italic: true, size: 10 },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${colName(endCol)}2`).format.rowHeight = 34;
}

function styleHeader(sheet, range) {
  range.format = {
    fill: palette.blue,
    font: { bold: true, color: palette.white, size: 10 },
    wrapText: true,
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: palette.border },
  };
  range.format.rowHeight = 32;
}

function styleBody(sheet, range) {
  range.format = {
    font: { color: palette.dark, size: 9 },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: palette.border },
  };
}

function numberedSteps(text) {
  if (typeof text !== "string") return text;
  const parts = text
    .split(/[；;]/)
    .map((x) => x.trim().replace(/[。]+$/, ""))
    .filter(Boolean);
  return parts.map((x, i) => `${i + 1}. ${x}`).join("\n");
}

function concise(text) {
  if (typeof text !== "string") return text;
  return text
    .replace(/。$/g, "")
    .replace(/，并/g, "；")
    .replace(/，确认/g, "；确认")
    .replace(/，检查/g, "；检查")
    .replace(/，比较/g, "；比较");
}

function writeTable(sheet, startRow, headers, rows, widths, tableName) {
  const endCol = headers.length;
  const headerRange = sheet.getRange(rangeFor(startRow, 1, endCol));
  headerRange.values = [headers];
  styleHeader(sheet, headerRange);
  const bodyStart = startRow + 1;
  if (rows.length) {
    const bodyRange = sheet.getRange(`A${bodyStart}:${colName(endCol)}${bodyStart + rows.length - 1}`);
    bodyRange.values = rows;
    styleBody(sheet, bodyRange);
    bodyRange.format.rowHeight = 86;
    try {
      const table = sheet.tables.add(`A${startRow}:${colName(endCol)}${bodyStart + rows.length - 1}`, true, tableName);
      table.showFilterButton = true;
      table.showBandedRows = true;
    } catch (_) {
      // Table styling is optional; the range formatting above is the source of truth.
    }
  }
  widths.forEach((w, i) => {
    const c = colName(i + 1);
    sheet.getRange(`${c}${startRow}:${c}${bodyStart + Math.max(rows.length, 1) - 1}`).format.columnWidth = w;
  });
  sheet.freezePanes.freezeRows(startRow);
  sheet.freezePanes.freezeColumns(2);
  return { bodyStart, bodyEnd: bodyStart + rows.length - 1, endCol };
}

const coreHeaders = [
  "Case ID", "测试工具", "测试目的", "测试步骤", "测试时长", "测试脚本", "测试标准",
  "阶段", "优先级", "测试家族", "推荐配置档位", "SSD容量", "内存+显存", "执行模式",
  "模型/工作负载", "监控项", "主要指标", "无效条件", "配置选择理由", "预期输出", "Windows状态", "结果", "备注"
];

function r(id, stage, priority, family, profile, capacity, memory, mode, workload, tool, purpose, steps, duration, script, monitor, metrics, standard, invalid, rationale, artifact, win = "可运行", result = "Not Started", note = "") {
  return [id, tool, purpose, steps, duration, script, standard, stage, priority, family, profile, capacity, memory, mode, workload, monitor, metrics, invalid, rationale, artifact, win, result, note];
}

const coreRows = [
  r("S0-ENV-01", "Stage 0", "P0", "环境/可观测性", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "System Gate", "DUT 身份、SMART、PCIe、温度、路径", "PowerShell + mlpstorage init", "建立可复现的 DUT 基线，证明监控和数据路径可用。", "记录 SSD 型号/固件、PCIe link、文件系统、剩余空间；设置电源模式；建立 DUT_DATA、DUT_CACHE、RESULTS；启动 1 s 采样。", "15–20 分钟", "mlpstorage init --results-dir <RESULTS>\nGet-Counter '\\PhysicalDisk(*)\\*' -SampleInterval 1", "PhysicalDisk bytes/IOPS/latency/queue/busy、温度、CPU、RAM、GPU、paging、WHEA/StorPort", "字段完整率、监控采样连续性、DUT 路径命中", "身份/路径/监控完整；RESULTS 不在 DUT 或已明确例外。", "缺少 SSD 身份、无温度或磁盘计数器、结果目录与 DUT 混用。", "先建立证据链，避免把页缓存、Docker VHDX 或结果写入误判为 SSD 性能。", "manifest.json、windows_disk_1s.csv", "可运行"),
  r("S0-CAP-02", "Stage 0", "P0", "容量/路径门禁", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "System Gate", "容量预算、数据与结果目录", "mlpstorage datasize + PowerShell", "确认工作集、临时空间、结果空间和保留空间能够共存。", "计算 workload 所需空间；检查可用容量；保留 15–20% 空闲；确认 Docker/Milvus 临时空间。", "10 分钟", "mlpstorage training datasize ...\nGet-Volume | Select DriveLetter,SizeRemaining,Size", "卷可用空间、写入量、Docker 磁盘镜像位置", "active_workset + temp + results + reserve ≤ usable", "容量预算通过且路径映射清楚。", "可用空间不足、目标卷不是被测 SSD、保留空间低于 15%。", "消费级盘不应填满；先用容量门禁决定 native、scaled 或 not-run。", "capacity_check.json、configview.txt", "可运行"),
  r("S0-CONFIG-03", "Stage 0", "P0", "配置复现", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "System Gate", "模型、seed、版本、参数快照", "mlpstorage configview + Git", "锁定软件和参数，保证不同 SSD 结果可比较。", "执行 configview；保存 CLI、YAML、commit、Python/driver/Docker 版本；固定 seed=42；生成 run manifest。", "10 分钟", "mlpstorage training configview ...\nmlpstorage checkpointing configview ...", "版本、seed、加速器模型、reader threads、batch、cache 状态", "配置快照可回放；run_id 唯一；结果目录结构一致。", "配置缺失、seed 不一致、同一 run 混用不同数据集。", "先冻结变量，再逐步改变容量、并发、缓存和温度。", "configview.txt、manifest.json", "可运行"),
  r("S1-IO-01", "Stage 1", "P0", "I/O校准", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Trace/Replay", "VDB 1K/128 trace，buffered", "vdbbench.trace_runner + replay.py", "建立逻辑 trace 到 Windows 文件系统回放的基线。", "录制 insert/flush/load/search；保存六列 trace；按原始节奏回放；记录逻辑字节与 PhysicalDisk 字节。", "20–30 分钟", "python -m vdbbench.trace_runner --vectors 1000 --dim 128 --output trace.csv\npython -m vdbbench.replay --trace trace.csv --root <DUT_DATA>", "PhysicalDisk read/write、队列、文件系统缓存、CPU", "P50/P95/P99、吞吐、logical/device bytes、放大倍数", "trace 完整；回放无异常；逻辑/物理字节均有记录。", "trace 缺列、回放未命中 DUT、无物理 I/O 证据。", "先用小 trace 校准口径，不把 replay 结果当作 Milvus 端到端结果。", "trace.csv、replay_summary.json", "可运行"),
  r("S1-IO-02", "Stage 1", "P0", "I/O校准", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Trace/Replay", "同一 trace，Direct I/O", "vdbbench.replay --direct-io", "区分页缓存影响，验证 unbuffered 访问路径。", "复用 S1-IO-01 trace；开启 direct I/O；检查 Windows 对齐错误；比较 buffered/direct 两条曲线。", "20–30 分钟", "python -m vdbbench.replay --trace trace.csv --root <DUT_DATA> --direct-io", "PhysicalDisk bytes、平均延迟、对齐错误、queue length", "direct I/O 物理读写可见；P99 和放大系数可解释。", "对齐失败、物理 bytes 为 0、结果只来自页缓存。", "Windows 上用 Direct I/O 替代 Linux drop_caches，形成更可信的 SSD 证据。", "direct_replay_summary.json", "可运行"),
  r("S1-IO-03", "Stage 1", "P0", "缓存对照", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Trace/Replay", "cold → warm → reboot-cold", "replay.py + PowerShell Restart-Computer", "量化首次访问、缓存命中和重启冷启动差异。", "执行 cold replay；重复相同 trace 得 warm；系统重启后再执行 reboot-cold；分别归档三次结果。", "30–45 分钟", "python -m vdbbench.replay --trace trace.csv --root <DUT_DATA>\nRestart-Computer", "物理读量、缓存命中、首轮/稳态延迟、启动时间", "三种状态独立报告；不合并平均值；重启后数据完整。", "未重启却标记 cold、物理读量无变化且无解释。", "缓存状态是消费级 AI PC 结果的主要混杂因素，必须单列。", "cold_warm_compare.csv", "可运行"),
  r("S1-IO-04", "Stage 1", "P0", "占用率敏感性", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "System Gate", "50%/80%/90% 盘占用短跑", "PowerShell + replay.py", "暴露高占用、GC 和 SLC 缓存退化。", "准备不同占用档位；每档执行固定短 trace；不进行长时间 endurance；记录温度和恢复时间。", "45–60 分钟", "fsutil file createnew <path> <bytes>\npython -m vdbbench.replay --trace trace.csv --root <DUT_DATA>", "可用空间、写延迟 P99、温度、queue、吞吐", "每个档位无错误；下降超过 10% 标记 GC/thermal cliff。", "占用超过 90%、容量门禁被绕过、温度/错误未记录。", "短跑即可判断容量敏感性，避免过早消耗 TBW。", "fill_level_summary.csv", "可运行"),
  r("S2-TRN-01", "Stage 2", "P0", "Training smoke", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Native", "UNet3D smoke（2–8 文件）", "mlpstorage training run", "验证训练数据实际从 DUT 读出并形成有效吞吐/AU。", "生成或准备小型 NPZ 数据；执行单机 file backend；检查 samples、AU、结果和 PhysicalDisk 读量。", "20–30 分钟", "mlpstorage training datagen --model unet3d ...\nmlpstorage training run --model unet3d --storage file ...", "PhysicalDisk read bytes、reader threads、CPU/GPU、AU", "退出码 0；AU/吞吐存在；DUT 读量大于 0；结果文件齐全。", "只读到页缓存、无 AU、结果文件缺失。", "UNet3D 大文件代表连续供给，适合最小端到端验证。", "training_summary.json、timeseries.csv", "可运行"),
  r("S2-CKPT-01", "Stage 2", "P0", "Checkpoint smoke", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Native", "Llama3-8B，1 write + 1 read", "mlpstorage checkpointing run", "验证 checkpoint 文件写入、读取和完整性闭环。", "准备约 105 GB checkpoint 或受控缩小样本；执行一次 write、一次 read；比较文件大小和 hash。", "30–60 分钟", "mlpstorage checkpointing run --model llama3-8b --storage file ...", "PhysicalDisk read/write、fsync、CPU、温度、剩余空间", "读写字节与文件大小一致；hash 一致；恢复退出码 0。", "只生成元数据、hash 不一致、没有物理写入。", "8B 是消费级本地微调/恢复的首选真实规模。", "checkpoint_manifest.json、integrity.json", "Windows单机可运行；正式多rank结果另标"),
  r("S2-KV-01", "Stage 2", "P0", "KV Cache smoke", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Native", "Llama3.1-8B，CPU tier 0/4 GB", "mlpstorage kvcache run", "验证 Tier-2 cache directory 指向 DUT 且产生真实 NVMe I/O。", "运行 30–60 s；先 CPU tier 0，再 CPU spill 4 GiB；确认 storage entries 和 Tier-2 bytes。", "15–25 分钟", "mlpstorage kvcache run --model llama3.1-8b --cache-dir <DUT_CACHE> --duration 60", "Tier-2 bytes、tokens/s、P95/P99/P99.9、PhysicalDisk", "进程退出码 0；Tier-2 bytes > 0；无 eviction 异常；监控连续。", "Tier-2 bytes=0、cache-dir 非 DUT、只有逻辑计数无物理读写。", "8B 对象和并发适合 1TB 起步，先验证路径再做压力。", "kv_summary.json、kv_trace.csv", "可运行"),
  r("S2-VDB-01", "Stage 2", "P0", "VectorDB smoke", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Native", "Milvus 1K/50K，HNSW 或 DISKANN", "Docker Desktop + mlpstorage vectordb", "验证 Windows Docker/Milvus、写入、flush、load 和查询链路。", "启动 Milvus；写入 1K/50K 向量；flush/build/load；执行 30 s 查询；检查 row count、QPS、Recall 和物理读写。", "30–60 分钟", "docker compose -f docker-compose.win.yml up -d\nmlpstorage vectordb run --dataset 1000 --index hnsw ...", "Milvus health、Docker VHDX、PhysicalDisk、CPU/RAM、QPS/P99", "服务 ready；row count 正确；查询成功；结果目录齐全。", "Milvus 未 ready、row count 不一致、Docker 数据路径未确认。", "1K smoke 是 Windows 适配和 trace 链路的低风险入口。", "milvus_health.json、vdb_summary.json", "可运行"),
  r("S3-TRN-01", "Stage 3", "P1", "Training", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Hybrid", "T-Large：UNet3D 大文件", "mlpstorage training + DLIO", "评价持续读取带宽、AU 和 reader thread 扩展。", "warm-up 1 次；测量 3 次；加速器模型 1/2/4；reader threads 1/4/8/16；P1/P2 使用 200/400 GiB scaled，P3 可扩大。", "60–120 分钟", "mlpstorage training run --model unet3d --num-accelerators 1/2/4 --reader-threads 1/4/8/16 ...", "吞吐、AU、PhysicalDisk bandwidth/queue、CPU/GPU、温度", "AU ≥ 0.90；找出 SSD 饱和点；scaled 与 native 分开报告。", "数据集不足却标 native、AU 无法解释、读量未命中 DUT。", "UNet3D 的大对象供给最能区分 SSD 带宽和计算间隔。", "training_profile_TL.csv", "可运行"),
  r("S3-TRN-02", "Stage 3", "P1", "Training", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Hybrid", "T-Small：RetinaNet 小文件", "mlpstorage training + DLIO", "评价 metadata、IOPS 和小文件尾延迟。", "先 100K JPEG，再按容量扩展；并发 1/2/4；reader threads 1/4/8；每档 warm-up + 3 次测量。", "60–120 分钟", "mlpstorage training run --model retinanet --num-processes 1 ...", "文件打开/读 IOPS、P95/P99、CPU、queue、AU", "AU ≥ 0.85；P99 稳定；并发增加不出现错误或明显数据缺失。", "文件清单不完整、缓存命中无物理读、尾延迟无监控。", "单文件约 315 KiB，能暴露本地数据集常见的小文件瓶颈。", "training_profile_TS.csv", "可运行"),
  r("S3-TRN-03", "Stage 3", "P1", "Training", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Native", "T-Medium：ResNet50 TFRecord", "mlpstorage training + DLIO", "评价中等对象、shuffle 和 batch 读取的混合行为。", "准备约 136.8 GiB 数据；固定 batch 400；reader/computation threads 8；对比 cold/warm。", "45–90 分钟", "mlpstorage training run --model resnet50 --batch-size 400 --reader-threads 8 ...", "TFRecord read bytes、吞吐、P99、CPU、RAM、paging", "吞吐可重复；cold/warm 差异有证据；无数据缺失。", "数据未落到 DUT、batch/threads 漂移、分页导致结果不可比。", "体量适中，可在 1TB/2TB native 实跑，补充 UNet/Retina 的数据形态。", "training_profile_TM.csv", "可运行"),
  r("S3-CKPT-01", "Stage 3", "P1", "Checkpoint", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Native", "C-8B：1/3/10 次 write/read", "mlpstorage checkpointing", "评价大块写入、fsync、cold/warm restore 和重复 checkpoint 退化。", "1TB 采用单轮 write→cold read→删除；2TB 至少 3 轮；4TB 执行 10/10；每轮归档 hash。", "2–4 小时", "mlpstorage checkpointing run --model llama3-8b --num-checkpoints 1/3/10 --storage file ...", "write/read bandwidth、fsync、P95、温度、可用空间", "文件大小/hash 一致；连续 3 窗口吞吐下降不超过 10%，否则标记 GC/thermal cliff。", "容量门禁绕过、hash 不一致、无法区分 cold/warm。", "8B 约 105GB，是消费级 AI PC 最接近真实本地恢复的 checkpoint。", "checkpoint_runs.csv、integrity.json", "单机多rank为Conditional"),
  r("S3-CKPT-02", "Stage 3", "P1", "Checkpoint", "P2/P3", "2/4 TB", "64/128 GB", "Hybrid", "C-70B-subset：8 ranks，约 114 GB", "mlpstorage checkpointing + Windows adapter", "覆盖更大模型分片和突发写入，不要求 912 GB full checkpoint。", "在 2/4TB 执行 1 轮；4TB 可执行 3 轮；记录 shard/optimizer shard 比例和恢复时间。", "60–120 分钟", "mlpstorage checkpointing run --model llama3-70b --num-processes 8 --subset ...", "shard write/read、PhysicalDisk、温度、CPU/RAM", "subset 文件和 hash 正确；恢复退出码 0；native/scaled 标识清晰。", "误称 full 70B、rank 不合法、容量/结果空间不足。", "约 114GB subset 在 2TB/4TB 可执行，能观察分片形态而不把结果误作 full 规模。", "checkpoint_70b_subset.json", "需可用8进程环境；否则Trace"),
  r("S3-CKPT-03", "Stage 3", "P1", "Checkpoint", "P2/P3", "2/4 TB", "64/128 GB", "Hybrid", "C-Burst：间隔 5/30/300 s", "mlpstorage checkpointing + PowerShell monitor", "评价连续 checkpoint 间隔、后台 GC 和后续恢复退化。", "固定 8B 或 70B subset；按 5/30/300s 间隔重复；比较第 1、3、10 轮延迟和温度。", "90–180 分钟", "for ($i=1; $i -le 10; $i++) { mlpstorage checkpointing run ...; Start-Sleep -Seconds 30 }", "write P99、温度、queue、可用空间、Windows 事件", "不同间隔下无错误；若后半程吞吐下降>10%，输出 cliff 和恢复时间。", "后台任务未记录、间隔漂移、删除/清理影响未标注。", "消费级 SSD 的 SLC/GC 行为常在连续 checkpoint 中暴露。", "checkpoint_burst.csv", "可运行"),
  r("S3-KV-01", "Stage 3", "P1", "KV Cache", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Native", "K-NVMe：8B，GPU/CPU tier=0，users 25/50/100", "mlpstorage kvcache + standalone trace", "测量 NVMe-only KV 的并发读写、token 吞吐和尾延迟。", "固定 seed=42、duration=300s；users 25/50/100；generation none；3–5 trials；确认 Tier-2 bytes。", "45–90 分钟", "mlpstorage kvcache run --model llama3.1-8b --gpu-tier 0 --cpu-tier 0 --users 25/50/100 --duration 300", "tokens/s、Tier-2 bytes、P95/P99/P99.9/P99.99、PhysicalDisk", "Tier-2 bytes>0；P99 可复现；无 eviction/I/O error；结果按并发分层。", "Tier-2=0、只产生逻辑 trace、请求生成器成为瓶颈且未说明。", "对应仓库固定 Option 1，最直接地反映 SSD 读写和小对象并发。", "kv_K1_summary.json、io_trace.csv", "可运行"),
  r("S3-KV-02", "Stage 3", "P1", "KV Cache", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Native", "K-CPU-spill：8B，CPU tier=4 GiB，alloc=16", "mlpstorage kvcache", "定位 CPU RAM 耗尽后 spill 到 NVMe 的拐点和尾延迟。", "users 25/50/100；CPU tier 4GiB；固定 max allocations=16；比较 spill 前后 P95/P99。", "45–90 分钟", "mlpstorage kvcache run --model llama3.1-8b --cpu-tier 4 --max-allocations 16 --users 25/50/100 ...", "CPU/RAM、paging、Tier-1/2 bytes、P99、queue", "spill 事件可解释；Tier-2 bytes 增长；无异常 eviction 或数据丢失。", "paging 未监控、Tier-2 未增长、CPU tier 配置未生效。", "对应固定 Option 2，贴近 AI PC 内存不足时的实际 offload。", "kv_K2_summary.json", "可运行"),
  r("S3-KV-03", "Stage 3", "P1", "KV Cache", "P2/P3", "2/4 TB", "64/128 GB", "Hybrid", "K-Trace-large：70B/32B/120B 对象", "kv_cache_benchmark --io-trace-log + replay", "将无法在消费级 AI PC 完整承载的大对象压力转化为可复现 SSD trace。", "先录制 Tier-2 逻辑事件；过滤 Tier-2；按 1x/2x/4x 回放；真实 KV 与 replay 分开报告。", "60–120 分钟", "python -m kv_cache.cli --model llama3.1-70b-instruct --io-trace-log kv_trace.csv ...\npython replay_trace.py --trace kv_trace.csv --scale 1,2,4", "trace 时间戳、对象大小、Tier、PhysicalDisk、P99", "trace 字段完整；回放节奏误差可解释；输出 1x/2x/4x 曲线。", "把 replay 当作真实模型成绩、trace 不含 Tier-2、回放未命中 DUT。", "70B/120B 大对象可隔离对象大小因素，避免模型计算和 SSD 结果耦合。", "kv_large_trace.csv、replay_summary.json", "可运行；结论标Trace"),
  r("S3-VDB-01", "Stage 3", "P1", "VectorDB", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Native", "V-1M：1M×1536，HNSW + DISKANN", "Milvus + enhanced_bench", "形成本地 RAG 的 QPS、Recall 和 P99 基线。", "分别 build/load；同一 query set；top-k 10/100；query processes 1/2/4；固定 Recall 门槛后比较 QPS/P99。", "2–4 小时", "mlpstorage vectordb run --dataset 1m --dim 1536 --index hnsw,diskann ...", "Milvus health、index build、flush/compact、PhysicalDisk、RAM", "Recall@K≥0.95 或项目门槛；QPS/P99 可重复；row count 正确。", "Recall 未锁定、row count 不一致、索引未 load 就开始计时。", "1M 规模适合 1TB/2TB，HNSW/DISKANN 对比覆盖内存型和磁盘型 ANN。", "vdb_1m_summary.json、recall.csv", "可运行；1TB容量需门禁"),
  r("S3-VDB-02", "Stage 3", "P1", "VectorDB", "P2/P3", "2/4 TB", "64/128 GB", "Hybrid", "V-10M：10M×1536，DISKANN；P2用5M scaled", "Milvus + compact_and_watch", "评价大索引、load、compaction 和持续搜索的后台 I/O。", "P3 执行 10M；P2 执行 5M scaled；分阶段计时 ingest/flush/build/load/search；固定 Recall。", "4–8 小时", "mlpstorage vectordb run --dataset 10m --dim 1536 --index diskann ...", "index build/compact、PhysicalDisk、Docker RAM、温度、QPS/P99", "Recall 达标；row count 正确；后台吞吐和前台 P99 分开报告。", "Docker 内存不足、容量门禁不通过、compact 失败却继续计分。", "10M 只在 4TB/128GB 级别合理；5M scaled 保留趋势而不伪装 full。", "vdb_10m_summary.json、compact_watch.csv", "P2 scaled；P3 native"),
  r("S4-MIX-01", "Stage 4", "P1", "混合负载", "P2/P3", "2/4 TB", "64/128 GB", "Hybrid", "KV decode + Checkpoint write", "KV benchmark + checkpoint + PowerShell", "验证前台推理尾延迟受到后台大块写入时的 QoS。", "先测 KV solo；再加入后台 checkpoint；后台负载 50%/75%/100%；比较前台 P99/P99.9。", "60–120 分钟", "Start-Job { mlpstorage checkpointing run ... }\nmlpstorage kvcache run --decode-only ...", "前台 P99/P99.9、后台吞吐、queue、温度、CPU/RAM", "前台 P99 ≤ solo 1.5×；后台吞吐 ≥ solo 80%；无错误/eviction。", "前台 trace 未完整、后台写入未命中 DUT、温度/queue 无解释。", "这是 AI PC 日常共存的首要组合，直接观察 SSD 争用和尾延迟。", "mix_KV_CKPT.csv", "需进程并发；P1可缩短"),
  r("S4-MIX-02", "Stage 4", "P1", "混合负载", "P2/P3", "2/4 TB", "64/128 GB", "Native", "VDB search + ingest/compact", "Milvus + enhanced_bench", "验证 RAG 查询在后台写入和 compaction 时的稳定性。", "先 search solo；后台持续 ingest/flush/compact；前后台阶梯 50%/75%/100%；检查 Recall 与 P99。", "60–120 分钟", "python -m vdbbench.enhanced_bench --search-only ...\npython -m vdbbench.compact_and_watch ...", "Recall、QPS、P99、Milvus health、PhysicalDisk、Docker RAM", "Recall 下降≤1个百分点；前台 P99≤solo 1.5×；后台吞吐≥80%。", "Milvus 重启、Recall 未测、后台任务没有物理写入证据。", "本地 RAG 最常见的前台查询+后台维护组合。", "mix_VDB_ingest.csv", "可运行"),
  r("S4-MIX-03", "Stage 4", "P1", "混合负载", "P2/P3", "2/4 TB", "64/128 GB", "Hybrid", "Training read + Checkpoint write", "DLIO + checkpoint + PowerShell", "评价本地训练读取与保存模型同时发生时的带宽和尾延迟。", "Training solo 1 次；后台 checkpoint 50%/75%/100%；比较 AU/吞吐和写入完成时间。", "60–120 分钟", "Start-Job { mlpstorage checkpointing run ... }\nmlpstorage training run --model unet3d ...", "AU、training throughput、checkpoint duration、queue、温度", "AU 下降≤10%；checkpoint 完成且 hash 正确；无 I/O error。", "数据/结果路径重叠、后台写入失败、AU 变化无监控。", "代表本地微调/保存检查点的常见共存模式。", "mix_TRN_CKPT.csv", "可运行；1TB建议不做"),
  r("S5-SOAK-01", "Stage 5", "P1", "热稳定性/高占用", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Hybrid", "50%/80%/90% fill + KV/CKPT/VDB 短压", "replay.py + PowerShell monitor", "暴露高占用、SLC 耗尽、GC 和温度对 AI workload 的影响。", "每个占用档位执行固定短 workload；连续 3 个窗口比较吞吐和 P99；记录降速及恢复时间。", "1TB 2–4h；2TB 4–8h；4TB 8h起", "python -m vdbbench.replay --trace trace.csv ...\nGet-Counter ...", "温度、throttle、P99、queue、可用空间、WHEA/StorPort", "无数据损坏/持续错误；下降>10%时标记 cliff；恢复时间有记录。", "未保留空间、无温度/事件、长时间过程中断未记录。", "短时高占用先识别风险，再决定是否进行长 soak。", "soak_fill_thermal.csv", "可运行；90%仅敏感性"),
  r("S5-SOAK-02", "Stage 5", "P1", "长时间稳定性", "P2/P3", "2/4 TB", "64/128 GB", "Hybrid", "KV precondition + 8B checkpoint + VDB ingest", "KV + checkpoint + Milvus", "验证多小时混合负载下的错误、热稳定性和性能漂移。", "Stage 3/4 通过后执行；2TB 4–8h，4TB 8–24h；每小时归档窗口指标。", "2TB 4–8h；4TB 8–24h", "Start-Job { mlpstorage kvcache run ... }\nStart-Job { mlpstorage checkpointing run ... }", "窗口吞吐/P99、温度、queue、空间、Docker health、事件日志", "无数据损坏/重启/持续错误；漂移可解释；恢复后性能偏差≤10%。", "未通过前置阶段、后台更新/Defender干扰未记录、结果目录污染。", "长时间 case 只在路径和基线稳定后执行，避免无效消耗 TBW。", "soak_hourly.csv、events.evtx", "可运行；非首轮必测"),
  r("S6-REC-01", "Stage 6", "P0", "恢复", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Native", "warm restart / reboot-cold / Docker restart", "PowerShell + 四类 workload smoke", "验证系统或容器重启后业务能够恢复，且不会遗留脏数据。", "分别执行应用重启、Windows reboot-cold、Docker/Milvus restart；重跑 Stage 2 最小 smoke。", "45–90 分钟", "Restart-Computer\ndocker compose restart\nmlpstorage validate ...", "启动时间、PhysicalDisk、Docker health、文件/索引完整性", "重启后 row count、hash、Tier-2 cleanup、training batch 均正确。", "孤儿文件、Milvus row count 变化、KV cache 无法清理、启动失败。", "消费级 AI PC 常见睡眠/重启路径必须独立验证。", "recovery_matrix.json", "可运行"),
  r("S6-REC-02", "Stage 6", "P0", "数据完整性", "P1/P2/P3", "1/2/4 TB", "32/64/128 GB", "Native", "hash、样本数、row count、固定 batch 重读", "mlpstorage validate + hashlib + Milvus", "将“性能通过”与“数据仍可用”绑定，避免静默损坏。", "Checkpoint hash/大小；Training 清单/样本数；KV 孤儿文件；VDB row count/Recall；再跑最小 smoke。", "30–60 分钟", "mlpstorage validate ...\nGet-FileHash <checkpoint> -Algorithm SHA256", "hash、文件大小、样本数、row count、Recall、错误日志", "无数据损坏；恢复后关键指标偏差≤10%；结论可归档。", "任何 hash/row count/样本数不一致、缺少 integrity.json。", "恢复是系统级 AI SSD 结论的硬门槛，不允许用平均性能掩盖错误。", "integrity.json、verdict.json", "可运行"),
];

for (const row of coreRows) {
  row[2] = concise(row[2]);
  row[3] = numberedSteps(row[3]);
  row[6] = concise(row[6]);
  row[15] = concise(row[15]);
  row[16] = concise(row[16]);
  row[17] = concise(row[17]);
  row[18] = concise(row[18]);
}

const optionalHeaders = ["Case ID", "适用档位", "家族", "执行模式", "模型/工作负载", "测试目的", "测试步骤", "建议时长", "测试工具/脚本", "监控项/指标", "测试标准", "选择理由", "结果"];
const optionalRows = [
  ["O-TRN-04", "P3", "Training", "Scaled", "CosmoFlow；约1.38TiB TFRecord", "覆盖超大 TFRecord 和长时间 shuffle 读取。", "P3 4TB 做容量门禁；full 或 640–1200GiB scaled；warm-up+3 trials。", "4–8 h", "mlpstorage training run --model cosmoflow ...", "吞吐/AU、read bandwidth、queue、温度", "数据完整；AU≥0.70；scaled 与 full 分开。", "体量大、对 P1/P2 不经济，不影响代表性基线。", "Not Started"],
  ["O-TRN-05", "P3", "Training", "Trace/Replay", "DLRM / Flux Parquet", "覆盖列式数据、row-group 和列裁剪的 metadata 行为。", "生成或录制 row-group 访问；按原节奏 replay；对比列裁剪比例。", "2–4 h", "mlpstorage training run --model dlrm/flux ...", "metadata IOPS、read amplification、P99", "trace 完整；逻辑/物理 bytes 分开。", "Windows/容量组合复杂，先以 trace 作为扩展。", "Not Started"],
  ["O-CKPT-04", "P3", "Checkpoint", "Hybrid", "Llama3-405B subset；约94GB", "比较超大模型 shard 形态，不证明本机能运行 405B。", "4TB 单轮 subset；hash/恢复；如无 8-rank 环境则 replay。", "60–120 min", "mlpstorage checkpointing run --model llama3-405b --subset ...", "shard bytes、restore P99、温度", "标记 subset；hash 一致；不得称 full。", "用于扩展 shard 形态，主结论由 8B/70B subset承担。", "Not Started"],
  ["O-CKPT-05", "P3", "Checkpoint", "Trace/Replay", "Llama3-1T 或 405B full trace", "评价 TB 级 checkpoint 对 SSD 的逻辑压力和回放上限。", "录制写/读 trace；1x/2x 回放；不生成 full 文件集。", "1–2 h", "checkpoint trace exporter + replay.py", "trace bytes、write/read P99、queue", "仅作为 replay；不与 native 分数混合。", "full 规模超出消费级单盘合理工作集。", "Not Started"],
  ["O-KV-04", "P1/P2/P3", "KV Cache", "Trace/Replay", "Llama2-7B / Mistral-7B / DeepSeek-V3 / Qwen3-32B", "覆盖约24–512KiB/token 的对象大小分布。", "分别录制对象大小；按 Tier-2 过滤；1x/2x replay；对比大小与P99。", "60–120 min", "kv_cache.cli --io-trace-log ... + replay_trace.py", "object size、P95/P99、logical/device bytes", "trace 字段完整；回放无错误；结果分模型。", "第一轮固定 8B，避免对象大小、请求生成和 SSD 变量同时变化。", "Not Started"],
  ["O-KV-05", "P2/P3", "KV Cache", "Native", "RAG / prefix cache / multi-turn / autoscaler", "评价真实应用模式而非单一合成请求。", "在 K1/K2 稳定后，每次只启用一个变量；记录命中率和 eviction。", "2–4 h", "python -m kv_cache.cli --persona coding --rag ...", "tokens/s、cache hit、P99.9、eviction、queue", "相对 baseline 的退化可解释；无异常 eviction。", "组合维度高，先作为扩展变量而非主矩阵。", "Not Started"],
  ["O-VDB-03", "P2/P3", "VectorDB", "Native", "1M×512 AISAQ", "分析降维与压缩索引对容量、Recall、QPS 的影响。", "同 query set；与 V2 锁定 Recall@K；分阶段计时 build/load/search。", "2–4 h", "mlpstorage vectordb run --index aisaq --dim 512 ...", "Recall@K、QPS/P99、index bytes、PhysicalDisk", "Recall 达标；容量/IO 放大有记录。", "压缩索引依赖和参数更复杂，不作为首轮最低通用基线。", "Not Started"],
  ["O-SOAK-03", "P3", "系统稳定性", "System Gate", "90% fill，8–24h soak", "观察长期 GC、thermal throttle、Windows 事件和恢复时间。", "Stage 5-01 通过后，将盘占用至90%；每小时归档；结束后做 S6 recovery。", "8–24 h", "PowerShell fill script + mixed workload jobs", "温度、throttle、P99、WHEA/StorPort、空间", "无数据损坏/持续错误；恢复后偏差≤10%。", "写入寿命和时间成本高，需设备主结论前置通过。", "Not Started"],
];

for (const row of optionalRows) {
  row[5] = concise(row[5]);
  row[6] = numberedSteps(row[6]);
  row[10] = concise(row[10]);
  row[11] = concise(row[11]);
}

const configHeaders = ["类别", "配置项", "P1：入门 AI PC", "P2：主流 AI PC", "P3：高容量 AI PC", "选择依据/使用说明"];
const configRows = [
  ["系统档位", "SSD容量", "1 TB", "2 TB", "4 TB", "消费级 NVMe；不以协议符合性或企业级耐久度为目标。"],
  ["系统档位", "显存+系统内存", "32 GB", "64 GB", "128 GB", "记录真实 VRAM/RAM；档位只用于分层，不替代实际参数。"],
  ["容量门禁", "默认保留空间", "20%", "20%", "15–20%", "禁止填满整盘；另留 Windows、Docker、结果和临时空间。"],
  ["容量门禁", "建议最大工作区", "550–650 GiB", "1.1–1.35 TiB", "2.2–2.8 TiB", "以 active_workset + temp + results + reserve ≤ usable 为准。"],
  ["Training", "首选模型", "UNet3D/RetinaNet scaled", "UNet3D/RetinaNet + ResNet50", "UNet3D/RetinaNet + CosmoFlow扩展", "分别覆盖大文件、小文件、中等TFRecord和可选超大TFRecord。"],
  ["Checkpoint", "首选模型", "Llama3-8B 单轮", "Llama3-8B + 70B subset", "8B 10/10 + 70B subset 多轮", "8B约105GB；70B subset约114GB；full只做trace/replay。"],
  ["KV Cache", "首选配置", "8B NVMe-only", "8B NVMe-only + CPU spill", "8B/70B trace stress", "先固定seed=42、duration=300s、3–5 trials，再增加 persona/RAG。"],
  ["VectorDB", "首选规模", "1M以内", "1M/5M scaled", "1M + 10M DISKANN", "HNSW/DISKANN先锁定Recall，再比较QPS/P99。"],
  ["执行口径", "Native", "必跑", "必跑", "必跑", "真实应用直接访问DUT；可形成业务正确性和性能结论。"],
  ["执行口径", "Scaled", "常用", "条件使用", "少量", "保持访问形态但降低数据/对象规模；必须单独标记。"],
  ["执行口径", "Trace/Replay", "I/O校准/大模型", "大对象扩展", "full压力扩展", "只证明SSD回放能力，不替代应用端到端结果。"],
  ["执行口径", "Hybrid", "按容量门禁", "按容量门禁", "按容量门禁", "native、scaled、trace按设备容量选择并分开统计。"],
];

const traceHeaders = ["执行方式", "能否在Windows跑", "是否真实应用", "是否真实命中DUT", "适合case", "结果如何使用", "主要限制"];
const traceRows = [
  ["Native", "是；优先 local file、Docker、PowerShell", "是", "必须有 PhysicalDisk 证据", "Stage 2 smoke、8B checkpoint、8B KV、1M VDB、Training representative", "可用于业务功能、数据完整性、性能主结论", "受容量、内存、Docker/Milvus 和 Windows 适配限制。"],
  ["Scaled", "是", "是（缩小工作集）", "是", "P1/P2 UNet、Retina、5M VDB、部分70B subset", "只能与相同 scaled 配置比较；不能与full/native合并", "不能外推到full规模，必须写明缩放比例和原因。"],
  ["Trace/Replay", "是；KV/VDB trace + replay.py", "否；只回放访问序列", "是，若DUT_DATA明确且有物理I/O", "VDB I/O校准、70B/405B/1T对象、full checkpoint逻辑压力", "用于确定性吞吐/延迟/放大分析，单独报告为replay", "VDB逻辑trace不含WAL/protobuf/index放大；KV trace不等同应用运行。"],
  ["Hybrid", "是", "取决于实际分支", "必须分别验证", "10M VDB、70B subset、训练大工作集、mixed", "按native/scaled/replay分栏汇总，不做混合总分", "同一Case可能有多个结果，必须保留执行分支。"],
  ["System Gate", "是", "否", "不适用或仅用于门禁", "环境、容量、监控、恢复、完整性", "决定结果是否有效；不计入性能排名", "门禁不通过时后续应为NOT_RUN，而不是PASS/0分。"],
];

const monitorHeaders = ["监控域", "Windows采集方式", "采样/触发", "核心字段", "用于解释的风险"];
const monitorRows = [
  ["SSD/卷", "Get-Counter / typeperf / disk_stats.py", "1秒；每个run前后", "read/write bytes、IOPS、avg latency、queue、busy、free space", "页缓存、GC、队列堆积、容量不足"],
  ["温度/健康", "SMART/NVMe工具 + 厂商工具", "run前/每秒或5秒", "温度、health、寿命、thermal throttle、错误计数", "热降速、寿命异常、设备错误"],
  ["CPU/RAM", "Get-Counter + Get-Process", "1秒", "CPU、RAM、commit、paging、进程CPU/RAM", "主机/分页瓶颈冒充SSD瓶颈"],
  ["GPU", "nvidia-smi 或厂商工具", "1秒", "utilization、VRAM、功耗、温度", "计算间隔过长、GPU未饱和"],
  ["Docker/Milvus", "docker stats、healthcheck、Milvus日志", "1秒/事件", "container RAM/CPU、health、row count、compact、restart", "VHDX、内存不足、服务抖动"],
  ["Workload", "mlpstorage结果、KV trace、VDB summary", "按操作/请求", "AU、samples/s、tokens/s、QPS、Recall、P50/P95/P99/P99.9", "应用端瓶颈、缓存命中、尾延迟"],
  ["事件/完整性", "Get-WinEvent、hash、validate", "run前后/异常时", "WHEA、StorPort、hash、file size、row count、orphan files", "静默损坏、设备重置、恢复退化"],
];

const rulesHeaders = ["状态/规则", "判定", "适用范围", "处置"];
const rulesRows = [
  ["PASS", "路径、监控、完整性、性能门槛均满足；真实命中DUT。", "Native/System Gate通过后的性能case", "进入报告主结果。"],
  ["CONDITIONAL", "功能通过，但为scaled、trace/replay、单机smoke或未满足正式进程规则。", "Windows适配、subset、replay、单机checkpoint", "单独统计，不与PASS合并排名。"],
  ["INVALID", "未命中DUT、缺关键日志/监控、trace不完整、容量门禁绕过或数据损坏。", "所有case", "不计入结果；修复门禁后重跑。"],
  ["NOT_RUN", "硬件容量、软件、服务或Windows能力不满足，未执行。", "所有case", "不以0分替代；记录原因。"],
  ["混合QoS", "前台P99 ≤ solo 1.5×；后台吞吐 ≥ solo 80%；Recall下降≤1个百分点。", "Stage 4", "不满足则标记退化类型并保留监控证据。"],
  ["热/GC cliff", "连续3个窗口吞吐下降>10%，或温度/queue与下降一致。", "Stage 1/5", "报告下降幅度、峰值温度和恢复时间。"],
  ["完整性硬门槛", "hash、样本数、row count、Tier-2清理和重启后smoke均正确。", "Stage 2/6及checkpoint/KV/VDB", "任何失败均不得PASS。"],
];

for (const grid of [configRows, traceRows, monitorRows, rulesRows]) {
  for (const row of grid) {
    for (let i = 0; i < row.length; i++) row[i] = concise(row[i]);
  }
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const wb = Workbook.create();
const overview = wb.worksheets.add("目录与说明");
const core = wb.worksheets.add("核心Case矩阵");
const simple = wb.worksheets.add("简化Case清单");
const optional = wb.worksheets.add("可选Case清单");
const config = wb.worksheets.add("配置基线");
const trace = wb.worksheets.add("执行方式边界");
const monitor = wb.worksheets.add("监控与判定");

// Overview
setTitle(overview, "消费级 AI PC · AI SSD 测试用例设计矩阵", "依据仓库 MLPerf Storage / DLIO / KV Cache / Milvus VectorDB 能力收敛；适用 Windows 11、1–4TB 消费级 NVMe、显存+系统内存 32–128GB。", 10);
overview.getRange("A4:B4").values = [["使用方式", "先看配置基线，再按 Stage 0→6 执行；按执行模式区分 Native、Scaled、Trace/Replay 和 Hybrid。"]];
overview.getRange("A4:A4").format = { fill: palette.teal, font: { bold: true, color: palette.white }, horizontalAlignment: "center" };
overview.getRange("B4:J4").merge();
overview.getRange("B4:J4").format = { fill: palette.lightBlue, wrapText: true, verticalAlignment: "center" };
overview.getRange("A4:J4").format.rowHeight = 42;
overview.getRange("A6:B6").values = [["核心矩阵统计", "公式由明细表自动汇总；结果列为现场可编辑字段。"]];
overview.getRange("A6:A6").format = { fill: palette.teal, font: { bold: true, color: palette.white }, horizontalAlignment: "center" };
overview.getRange("B6:J6").merge();
overview.getRange("B6:J6").format = { fill: palette.lightBlue, wrapText: true };
const summaryHeaders = ["指标", "数值", "说明", "指标", "数值", "说明"];
overview.getRange("A8:F8").values = [summaryHeaders];
styleHeader(overview, overview.getRange("A8:F8"));
overview.getRange("A9:F14").values = [
  ["核心case总数", null, "应为29；不含可选扩展", "可选case总数", null, "应为8"],
  ["System Gate", null, "不计入性能排名", "Native", null, "真实应用端到端"],
  ["Scaled", null, "缩小工作集，单独统计", "Trace/Replay", null, "SSD回放，不替代应用结果"],
  ["Hybrid", null, "按容量门禁分支", "Stage 0–3主成绩", null, "建议每台设备必跑"],
  ["Stage 4混合", null, "QoS/干扰测试", "Stage 5/6", null, "稳定性、恢复与完整性"],
  ["发布状态", "Not Started", "在明细表结果列更新", "首轮设备", "P1/P2/P3", "按实机档位选择"],
];
overview.getRange("B9:B13").formulas = [
  ["=COUNTA('核心Case矩阵'!$A$6:$A$34)"],
  ["=COUNTIF('核心Case矩阵'!$N$6:$N$34,\"System Gate\")"],
  ["=COUNTIF('核心Case矩阵'!$N$6:$N$34,\"Scaled\")"],
  ["=COUNTIF('核心Case矩阵'!$N$6:$N$34,\"Hybrid\")"],
  ["=COUNTIF('核心Case矩阵'!$H$6:$H$34,\"Stage 4\")"],
];
overview.getRange("E9:E13").formulas = [
  ["=COUNTA('可选Case清单'!$A$6:$A$13)"],
  ["=COUNTIF('核心Case矩阵'!$N$6:$N$34,\"Native\")"],
  ["=COUNTIF('核心Case矩阵'!$N$6:$N$34,\"Trace/Replay\")"],
  ["=COUNTIF('核心Case矩阵'!$H$6:$H$34,\"Stage 0\")+COUNTIF('核心Case矩阵'!$H$6:$H$34,\"Stage 1\")+COUNTIF('核心Case矩阵'!$H$6:$H$34,\"Stage 2\")+COUNTIF('核心Case矩阵'!$H$6:$H$34,\"Stage 3\")"],
  ["=COUNTIF('核心Case矩阵'!$H$6:$H$34,\"Stage 5\")+COUNTIF('核心Case矩阵'!$H$6:$H$34,\"Stage 6\")"],
];
styleBody(overview, overview.getRange("A9:F14"));
overview.getRange("A9:F14").format.rowHeight = 30;
overview.getRange("A16:J16").merge();
overview.getRange("A16").values = [["三档配置与首轮选择"]];
overview.getRange("A16:J16").format = { fill: palette.teal, font: { bold: true, color: palette.white, size: 11 }, verticalAlignment: "center" };
overview.getRange("A17:J20").values = [
  ["P1：入门", "1TB + 32GB", "8B KV、8B checkpoint 单轮、UNet/Retina scaled、1M VDB", "原因：最小消费级配置；先验证路径、容量和基础 I/O。", null, null, null, null, null, null],
  ["P2：主流", "2TB + 64GB", "8B full、70B subset、ResNet50、1M/5M VDB、8B mixed", "原因：主流 AI PC；容量和内存可覆盖训练、恢复、本地 RAG。", null, null, null, null, null, null],
  ["P3：高容量", "4TB + 128GB", "大训练集、8B 10/10、70B subset 多轮、10M VDB、KV trace stress", "原因：评价持续写入、GC、热稳定性和混合业务。", null, null, null, null, null, null],
  ["原则", "容量优先", "active_workset + temp + results + reserve ≤ usable", "不得把 scaled、native、replay 结果合并为一个总分。", null, null, null, null, null, null],
];
overview.getRange("D17:J20").merge(true);
styleBody(overview, overview.getRange("A17:J20"));
overview.getRange("A17:J20").format.rowHeight = 42;
overview.getRange("A22:J22").merge();
overview.getRange("A22").values = [["设计思路：UNet3D测大文件带宽；RetinaNet测小文件IOPS；ResNet50测中等对象；Checkpoint测大块写读；KV测小对象并发和spill；VectorDB测随机ANN。顺序为：路径门禁 → Native基线 → 混合QoS → 稳定性 → 恢复完整性。"]];
overview.getRange("A22:J22").format = { fill: palette.amber, wrapText: true, verticalAlignment: "center", font: { color: palette.dark } };
overview.getRange("A22:J22").format.rowHeight = 52;
overview.getRange("A1:J22").format.font.name = "Aptos";
overview.getRange("A1:J22").format.wrapText = true;
overview.getRange("A1:J22").format.verticalAlignment = "top";
overview.getRange("A1:A22").format.columnWidth = 16;
overview.getRange("B1:J22").format.columnWidth = 18;
overview.getRange("B1:B22").format.columnWidth = 24;
overview.getRange("C1:C22").format.columnWidth = 28;
overview.getRange("D1:D22").format.columnWidth = 28;
overview.getRange("E1:J22").format.columnWidth = 16;
overview.freezePanes.freezeRows(8);

// Core matrix
setTitle(core, "核心测试用例矩阵（29 cases）", "执行顺序：Stage 0 门禁 → Stage 1 I/O口径 → Stage 2 smoke → Stage 3 基线 → Stage 4 混合QoS → Stage 5 稳定性 → Stage 6 恢复。", coreHeaders.length);
const coreInfo = writeTable(core, 5, coreHeaders, coreRows, [15,11,8,14,15,10,11,13,23,23,30,40,14,35,28,24,34,30,34,26,16,13,24], "CoreCases");
core.getRange(`V${coreInfo.bodyStart}:V${coreInfo.bodyEnd}`).dataValidation = { rule: { type: "list", values: results } };
core.getRange(`N${coreInfo.bodyStart}:N${coreInfo.bodyEnd}`).dataValidation = { rule: { type: "list", values: modes } };
core.getRange(`I${coreInfo.bodyStart}:I${coreInfo.bodyEnd}`).format.horizontalAlignment = "center";
core.getRange(`N${coreInfo.bodyStart}:N${coreInfo.bodyEnd}`).format.horizontalAlignment = "center";
core.getRange(`V${coreInfo.bodyStart}:V${coreInfo.bodyEnd}`).format.horizontalAlignment = "center";
core.getRange(`A${coreInfo.bodyStart}:A${coreInfo.bodyEnd}`).format.font = { bold: true, color: palette.blue };
core.getRange(`I${coreInfo.bodyStart}:I${coreInfo.bodyEnd}`).conditionalFormats.addCustom(`$I${coreInfo.bodyStart}=\"P0\"`, { fill: palette.red, font: { bold: true, color: "#9C0006" } });
core.getRange(`N${coreInfo.bodyStart}:N${coreInfo.bodyEnd}`).conditionalFormats.addCustom(`$N${coreInfo.bodyStart}=\"Trace/Replay\"`, { fill: palette.amber, font: { bold: true, color: "#7F6000" } });
core.getRange(`V${coreInfo.bodyStart}:V${coreInfo.bodyEnd}`).conditionalFormats.addCustom(`$V${coreInfo.bodyStart}=\"Pass\"`, { fill: palette.green, font: { bold: true, color: "#006100" } });
core.getRange(`V${coreInfo.bodyStart}:V${coreInfo.bodyEnd}`).conditionalFormats.addCustom(`$V${coreInfo.bodyStart}=\"Invalid\"`, { fill: palette.red, font: { bold: true, color: "#9C0006" } });

// Simplified case sheet
setTitle(simple, "简化版测试用例清单", "执行人员只需按 Case ID、工具、目的、步骤、时长、脚本和标准执行；详细配置与监控见核心矩阵。", 12);
const simpleHeaders = ["Case ID", "测试工具", "测试目的", "测试步骤", "测试时长", "测试脚本", "测试标准", "阶段", "执行模式", "推荐配置", "是否首轮", "结果"];
const simpleRows = coreRows.map(x => [x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[13], `${x[11]} / ${x[12]} / ${x[14]}`, ["P0", "P1"].includes(x[8]) ? "是" : "条件", x[21]]);
const simpleInfo = writeTable(simple, 5, simpleHeaders, simpleRows, [15,28,36,48,14,42,42,11,14,34,12,13], "SimpleCases");
simple.getRange(`L${simpleInfo.bodyStart}:L${simpleInfo.bodyEnd}`).dataValidation = { rule: { type: "list", values: results } };
simple.getRange(`L${simpleInfo.bodyStart}:L${simpleInfo.bodyEnd}`).format.horizontalAlignment = "center";
simple.getRange(`A${simpleInfo.bodyStart}:A${simpleInfo.bodyEnd}`).format.font = { bold: true, color: palette.blue };

// Optional extension cases
setTitle(optional, "可选扩展测试用例（8 cases）", "主矩阵通过后再执行；覆盖扩展模型、对象大小、压缩索引、RAG行为和长期占用率。结果不与核心29 case混合。", optionalHeaders.length);
const optionalInfo = writeTable(optional, 5, optionalHeaders, optionalRows, [15,14,16,14,28,36,42,14,34,34,36,38,13], "OptionalCases");
optional.getRange(`M${optionalInfo.bodyStart}:M${optionalInfo.bodyEnd}`).dataValidation = { rule: { type: "list", values: results } };
optional.getRange(`M${optionalInfo.bodyStart}:M${optionalInfo.bodyEnd}`).format.horizontalAlignment = "center";
optional.getRange(`A${optionalInfo.bodyStart}:A${optionalInfo.bodyEnd}`).format.font = { bold: true, color: palette.blue };

// Config baseline
setTitle(config, "配置基线与选择理由", "固定容量、内存、模型规模、工作集预算和执行口径；不同档位结果分开比较。", 6);
const configInfo = writeTable(config, 5, configHeaders, configRows, [16,22,18,18,18,48], "ConfigBaseline");
config.getRange("A20:F20").merge();
config.getRange("A20").values = [["工作区预算计算器（示例）"]];
config.getRange("A20:F20").format = { fill: palette.teal, font: { bold: true, color: palette.white } };
const budgetHeaders = ["档位", "SSD容量GiB", "保留比例", "临时/结果预算GiB", "建议可用工作区GiB", "计算公式"];
config.getRange("A21:F21").values = [budgetHeaders];
styleHeader(config, config.getRange("A21:F21"));
config.getRange("A22:F24").values = [
  ["P1", 1024, 0.20, 250, null, "容量×(1-保留)-临时/结果"],
  ["P2", 2048, 0.20, 450, null, "容量×(1-保留)-临时/结果"],
  ["P3", 4096, 0.20, 800, null, "容量×(1-保留)-临时/结果"],
];
config.getRange("E22:E24").formulas = [["=B22*(1-C22)-D22"],["=B23*(1-C23)-D23"],["=B24*(1-C24)-D24"]];
styleBody(config, config.getRange("A22:F24"));
config.getRange("B22:B24").setNumberFormat("0");
config.getRange("C22:C24").setNumberFormat("0%");
config.getRange("D22:E24").setNumberFormat("0");
config.getRange("A27:F27").merge();
config.getRange("A27").values = [["模型选择简表"]];
config.getRange("A27:F27").format = { fill: palette.teal, font: { bold: true, color: palette.white } };
const modelHeaders = ["家族", "优先模型", "工作集/对象特征", "P1", "P2", "P3/扩展理由"];
config.getRange("A28:F28").values = [modelHeaders];
styleHeader(config, config.getRange("A28:F28"));
config.getRange("A29:F34").values = [
  ["Training", "UNet3D", "NPZ大文件；持续读取", "scaled", "native/scaled", "native+reader sweep；大文件带宽"],
  ["Training", "RetinaNet", "JPEG小文件；约315KiB/文件", "scaled", "native", "native；metadata/IOPS"],
  ["Training", "ResNet50", "TFRecord；约136.8GiB", "native", "native", "native；中等对象混合读取"],
  ["Checkpoint", "Llama3-8B", "约105GB；大块写读", "1轮", "3轮", "10/10 + burst；消费级主线"],
  ["KV Cache", "Llama3.1-8B", "128KiB/token；高并发", "native", "native", "native+trace stress；NVMe/spill"],
  ["VectorDB", "1M HNSW/DISKANN", "1536维；ANN随机访问", "native", "native", "10M DISKANN；Recall锁定后比较"],
];
styleBody(config, config.getRange("A29:F34"));
config.getRange("A1:F34").format.wrapText = true;
config.getRange("A1:A34").format.columnWidth = 16;
config.getRange("B1:B34").format.columnWidth = 22;
config.getRange("C1:E34").format.columnWidth = 20;
config.getRange("F1:F34").format.columnWidth = 48;
config.getRange("A1:F34").format.font.name = "Aptos";
config.freezePanes.freezeRows(5);

// Trace boundary
setTitle(trace, "执行方式边界：Native 与 trace/replay", "Native 看业务正确性和端到端性能；Trace/Replay 看可复现 SSD I/O；Scaled/Hybrid 必须单独标记。", 7);
writeTable(trace, 5, traceHeaders, traceRows, [16,20,22,22,34,42,48], "ExecutionModes");
trace.getRange("A13:G15").values = [
  ["使用建议", "先跑 System Gate 和 Stage 1；再跑 Native smoke；Stage 3 按容量决定 Native/Scaled；超出容量的 full checkpoint/大模型 KV 用 Trace/Replay。", null, null, null, null, null],
  ["结果口径", "Native、Scaled、Trace/Replay、Hybrid 分栏；replay 只能说明访问序列下的 SSD 能力，不能声称真实模型或 Milvus 端到端成绩。", null, null, null, null, null],
  ["VDB特别说明", "vdbbench trace 是客户端逻辑操作/估算字节量，不含 Milvus WAL、protobuf、索引放大和 compaction 物理 I/O；必须同时报告 logical/device bytes 和放大倍数。", null, null, null, null, null],
];
trace.getRange("B13:G15").merge(true);
trace.getRange("A13:G15").format = { fill: palette.amber, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: palette.border } };
trace.getRange("A13:A15").format = { fill: palette.teal, font: { bold: true, color: palette.white }, horizontalAlignment: "center", verticalAlignment: "center" };
trace.getRange("A13:G15").format.rowHeight = 52;
trace.getRange("A1:G15").format.font.name = "Aptos";
trace.freezePanes.freezeRows(5);

// Monitor and rules
setTitle(monitor, "监控项、指标与发布判定", "每个性能 case 保存 workload、Windows 1秒监控、trace（如适用）、integrity 和 verdict；缺关键证据不得 PASS。", 5);
writeTable(monitor, 5, monitorHeaders, monitorRows, [18,34,16,42,42], "MonitorPlan");
monitor.getRange("A16:E16").merge();
monitor.getRange("A16").values = [["统一判定规则"]];
monitor.getRange("A16:E16").format = { fill: palette.teal, font: { bold: true, color: palette.white } };
writeTable(monitor, 17, rulesHeaders, rulesRows, [18,56,28,38], "VerdictRules");
monitor.getRange("A1:E25").format.font.name = "Aptos";
monitor.freezePanes.freezeRows(5);

// Apply consistent fonts and alignment.
for (const sheet of [overview, core, simple, optional, config, trace, monitor]) {
  const used = sheet.getUsedRange();
  if (used) {
    used.format.font.name = "Aptos";
    used.format.verticalAlignment = "top";
    used.format.wrapText = true;
  }
  sheet.showGridLines = false;
}

// Export, render, and a compact verification log.
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outputPath);
const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const reopenedSheets = await reopened.inspect({ kind: "sheet", include: "id,name", maxChars: 2000 });
await fs.writeFile(path.join(outputDir, "reopened_sheet_check.ndjson"), reopenedSheets.ndjson ?? String(reopenedSheets), "utf8");
for (const sheetName of ["目录与说明", "核心Case矩阵", "简化Case清单", "可选Case清单", "配置基线", "执行方式边界", "监控与判定"]) {
  const png = await wb.render({ sheetName, autoCrop: "all", scale: 0.75, format: "png" });
  const bytes = new Uint8Array(await png.arrayBuffer());
  await fs.writeFile(path.join(previewDir, `${sheetName}.png`), bytes);
}

const inspectSummary = await wb.inspect({ kind: "workbook,sheet,table", maxChars: 5000, tableMaxRows: 3, tableMaxCols: 6, tableMaxCellChars: 60 });
await fs.writeFile(path.join(outputDir, "inspect_summary.ndjson"), inspectSummary.ndjson ?? String(inspectSummary), "utf8");
const formulaInspect = await wb.inspect({ kind: "formula", sheetId: "目录与说明", range: "A1:J22", maxChars: 3000, options: { maxResults: 50 } });
await fs.writeFile(path.join(outputDir, "formula_inspect.ndjson"), formulaInspect.ndjson ?? String(formulaInspect), "utf8");
let errorInspect;
try {
  errorInspect = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, maxChars: 3000 });
} catch (err) {
  errorInspect = { ndjson: `error-scan-unavailable: ${err.message}` };
}
await fs.writeFile(path.join(outputDir, "formula_error_scan.ndjson"), errorInspect.ndjson ?? String(errorInspect), "utf8");
console.log(JSON.stringify({ outputPath, coreCases: coreRows.length, optionalCases: optionalRows.length, previewDir, formulaErrorScan: errorInspect.ndjson ?? String(errorInspect) }, null, 2));
