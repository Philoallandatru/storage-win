import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const repo = "C:/Users/Administrator/Documents/Code/repos/storage";
const inputPath = path.join(repo, "docs", "AI_PC_CONSUMER_SSD_TEST_CASE_MATRIX.xlsx");
const outputDir = path.join(repo, "outputs", "ai_pc_consumer_ssd_standards_based_20260804");
const outputPath = path.join(outputDir, "AI_PC_CONSUMER_SSD_TEST_REQUIREMENTS_AND_CASE_MATRIX.xlsx");
const previewDir = path.join(outputDir, "preview");

const requiredHeaders = ["Case ID", "测试工具", "测试目的", "测试步骤", "测试时长", "测试脚本", "测试标准"];
const extraHeaders = [
  "需求ID/来源", "阶段", "优先级", "测试家族", "推荐配置档位", "SSD容量", "内存+显存", "执行模式",
  "模型/工作负载", "前置条件", "DUT状态", "Active Range", "块大小", "R/W比例", "QD/线程/OIO",
  "数据模式", "监控项", "判定阈值", "无效条件", "证据包", "Windows状态", "结果", "备注",
];

const palette = {
  navy: "#15324B",
  blue: "#1F5A85",
  teal: "#197C80",
  paleBlue: "#EAF2F8",
  paleTeal: "#E7F5F3",
  paleGold: "#FFF7E2",
  paleGray: "#F4F6F8",
  border: "#C8D2DC",
  text: "#1D2733",
  white: "#FFFFFF",
};

function colLetter(n) {
  let x = n + 1;
  let s = "";
  while (x > 0) {
    const r = (x - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    x = Math.floor((x - 1) / 26);
  }
  return s;
}

function capForConfig(cfg) {
  if (String(cfg).includes("P1")) return "1 TB";
  if (String(cfg).includes("P3")) return "4 TB";
  return "2 TB";
}

function memForConfig(cfg) {
  if (String(cfg).includes("P1")) return "32 GB";
  if (String(cfg).includes("P3")) return "128 GB";
  return "64 GB";
}

function reqIdsFor(family, stage, mode, purpose = "") {
  const f = `${family} ${purpose}`;
  const ids = [];
  if (/环境|可观测性|门禁/.test(f)) ids.push("REQ-ENV-001", "REQ-MON-001");
  if (/容量|路径/.test(f)) ids.push("REQ-CAP-001");
  if (/IO|基线|性能/.test(f)) ids.push("REQ-IO-001", "REQ-IO-002");
  if (/Training|训练/.test(f)) ids.push("REQ-TRN-001", "REQ-TRN-002");
  if (/Checkpoint|检查点|checkpoint/i.test(f)) ids.push("REQ-CKP-001", "REQ-CKP-002");
  if (/KV|kvcache/i.test(f)) ids.push("REQ-KVC-001", "REQ-KVC-002");
  if (/Vector|向量|Milvus|VDB/i.test(f)) ids.push("REQ-VDB-001", "REQ-VDB-002");
  if (/QoS|混合|干扰|并发/.test(f)) ids.push("REQ-QOS-001");
  if (/热|长稳|稳定|占用率/.test(f)) ids.push("REQ-REL-001");
  if (/恢复|Recovery|重启|掉电/.test(f)) ids.push("REQ-REC-001");
  if (/完整|一致|校验|integrity/i.test(f)) ids.push("REQ-DATA-001");
  if (/HLK|协议|设备/.test(f)) ids.push("REQ-HLK-001");
  if (/Trace|Replay|trace/i.test(`${mode} ${f}`)) ids.push("REQ-RPL-001");
  if (ids.length === 0) ids.push(stage === "Stage 0" ? "REQ-ENV-001" : "REQ-IO-001");
  return [...new Set(ids)].join("; ");
}

function modeMethod(mode) {
  if (/System Gate|HLK|门禁/.test(mode)) return "检查+演示";
  if (/Trace|Replay/.test(mode)) return "测试+分析";
  if (/Scaled/.test(mode)) return "测试+分析";
  return "测试";
}

function defaultDutState(mode) {
  if (/Trace|Replay/.test(mode)) return "Preconditioned/Replay target";
  if (/System Gate/.test(mode)) return "Ready / identity captured";
  return "FOB→Purge/预处理→稳态窗口（按case要求）";
}

function defaultActiveRange(family, mode) {
  if (/Vector|VDB/i.test(family)) return "数据集实际占用；记录向量库/索引目录";
  if (/Trace|Replay/.test(mode)) return "trace 中的逻辑范围；不得隐式扩大";
  return "按工作集预算；写明容量占用和保留空间";
}

function defaultBlock(family, mode) {
  if (/Vector|VDB/i.test(family)) return "4 KiB–1 MiB（由索引/导入阶段决定）";
  if (/KV|kvcache/i.test(family)) return "4 KiB–256 KiB";
  if (/Checkpoint|检查点|checkpoint/i.test(family)) return "1–8 MiB 顺序/大块";
  if (/Training|训练/.test(family)) return "64 KiB–4 MiB；保留真实文件访问";
  if (/IO|基线|性能/.test(family)) return "4 KiB/128 KiB（分别记录）";
  return "按工具实际值；必须记录";
}

function defaultRw(family, mode) {
  if (/Checkpoint|检查点|checkpoint/i.test(family)) return "写为主；restore 为读";
  if (/KV|kvcache/i.test(family)) return "读/写混合；按spill/fetch比例记录";
  if (/Vector|VDB/i.test(family)) return "导入写；ANN 搜索读";
  if (/Training|训练/.test(family)) return "读为主；shuffle 产生元数据/临时写";
  if (/Trace|Replay/.test(mode)) return "遵循 trace 方向字段";
  return "按 workload 定义";
}

function defaultConcurrency(family, mode) {
  if (/Vector|VDB/i.test(family)) return "客户端并发/服务线程；记录实际值";
  if (/KV|kvcache/i.test(family)) return "并发请求数、线程数、OIO";
  if (/Training|训练/.test(family)) return "进程数/worker 数；由 MLPerf Storage 配置确定";
  if (/Trace|Replay/.test(mode)) return "trace 原始并发或 replay 限制";
  return "QD/线程/OIO 必填";
}

function defaultEvidence(mode) {
  const base = "manifest.json; configview.txt; workload_summary.json; windows_disk_1s.csv; temperature_health.csv; integrity_report.json; verdict.json; raw_tool_log";
  if (/Trace|Replay/.test(mode)) return `${base}; trace.csv; replay_summary.json`;
  return base;
}

function headerStyle(range, fill = palette.navy) {
  range.format = {
    fill,
    font: { bold: true, color: palette.white, size: 10 },
    wrapText: true,
    verticalAlignment: "center",
    horizontalAlignment: "center",
    borders: { preset: "all", style: "thin", color: palette.border },
  };
}

function bodyStyle(range) {
  range.format = {
    font: { color: palette.text, size: 10 },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "inside", style: "thin", color: palette.border },
  };
}

function titleBlock(sheet, title, subtitle, lastCol) {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${lastCol}1`).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${lastCol}1`).format = { fill: palette.navy, font: { bold: true, color: palette.white, size: 15 }, horizontalAlignment: "left", verticalAlignment: "center" };
  sheet.getRange(`A2:${lastCol}2`).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${lastCol}2`).format = { fill: palette.paleBlue, font: { color: palette.text, italic: true, size: 10 }, wrapText: true, verticalAlignment: "center" };
  sheet.getRange(`A1:${lastCol}2`).format.rowHeight = 28;
}

function setWidths(sheet, widths) {
  widths.forEach((w, i) => {
    sheet.getRange(`${colLetter(i)}:${colLetter(i)}`).format.columnWidth = w;
  });
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const coreSheet = wb.worksheets.getItem("核心Case矩阵");
const optionalSheet = wb.worksheets.getItem("可选Case清单");

const coreRows = coreSheet.getRange("A6:W34").values;
const optionalRows = optionalSheet.getRange("A6:M13").values;
if (coreRows.length !== 29 || optionalRows.length !== 8) throw new Error("Case 数量不符合 29+8 保留约束");

const standardRows = coreRows.map((r) => {
  const family = r[9] ?? "";
  const mode = r[13] ?? "";
  const req = reqIdsFor(family, r[7], mode, r[2]);
  return [
    r[0], r[1], r[2], r[3], r[4], r[5], r[6], req, r[7], r[8], family, r[10], r[11], r[12], mode,
    r[14], `${r[2]}；${r[3]}`, defaultDutState(mode), defaultActiveRange(family, mode), defaultBlock(family, mode), defaultRw(family, mode), defaultConcurrency(family, mode),
    "按case定义；随机种子/校验方式必须写入manifest", r[15], r[16], r[17], defaultEvidence(mode), r[20], r[21], r[22], modeMethod(mode),
  ];
});

const optionalStandardRows = optionalRows.map((r) => {
  const family = r[2] ?? "";
  const mode = r[3] ?? "";
  const req = reqIdsFor(family, "Stage 3-6", mode, r[5]);
  return [
    r[0], r[8], r[5], r[6], r[7], r[8], r[10], req, "Stage 3-6", "P2", family, r[1], capForConfig(r[1]), memForConfig(r[1]), mode,
    r[4], "扩展 workload；执行前锁定数据集与种子", defaultDutState(mode), defaultActiveRange(family, mode), defaultBlock(family, mode), defaultRw(family, mode), defaultConcurrency(family, mode),
    "按扩展case配置；必须单独标记 scaled/trace", r[9], r[10], "配置、trace或证据不完整；容量/热状态不满足", defaultEvidence(mode), "可运行（需按case确认依赖）", r[12], r[11], modeMethod(mode),
  ];
});
const allStandardRows = [...standardRows, ...optionalStandardRows];
const caseHeaders = [...requiredHeaders, ...extraHeaders, "验证方法"];

const reqSpecs = [
  ["REQ-ENV-001", "DUT shall record model, firmware, serial, PCIe link, OS, filesystem and target path before each test run.", "ISO 29119-3 test conditions；SNIA report metadata", "P1/P2/P3", "系统可启动；PowerShell/工具可用", "检查", "环境/门禁类case", "字段完整率 100%；路径必须命中目标卷", "manifest.json; configview.txt", "Open"],
  ["REQ-CAP-001", "测试前 shall verify active workset、临时空间、结果目录和保留空间满足容量预算。", "消费级SSD避免填满；历史矩阵容量门禁", "P1/P2/P3", "已计算 workload datasize", "分析+检查", "S0-CAP-02及容量相关case", "active+temp+results+reserve ≤ usable；reserve ≥ 15%", "capacity_check.json", "Open"],
  ["REQ-MON-001", "每个性能 case shall provide continuous 1 s Windows PhysicalDisk and system telemetry with aligned timestamps。", "Windows PhysicalDisk counters；客观证据原则", "P1/P2/P3", "Get-Counter/typeperf可用", "测试", "所有性能case", "采样完整率 ≥ 99%；时间戳单调且可对齐", "windows_disk_1s.csv; eventlog.txt", "Open"],
  ["REQ-IO-001", "I/O baseline shall record block size、R/W ratio、QD/threads/OIO、Active Range、cache/direct mode and random seed。", "SNIA PTS/fio reproducibility", "P1/P2/P3", "job/config已锁定", "检查+分析", "Stage 1 I/O baseline", "必填字段完整；重跑参数一致", "fio_job.fio; configview.txt", "Open"],
  ["REQ-IO-002", "性能结果 shall include IOPS/throughput and P50/P95/P99 latency; tail latency cannot be omitted。", "fio percentile logging；系统级QoS", "P1/P2/P3", "性能窗口已定义", "测试", "所有性能case", "至少P50/P95/P99；P99超阈值则不得PASS", "summary.json; latency.log", "Open"],
  ["REQ-TRN-001", "Training workload shall complete configured epochs/iterations with dataset and sample-count integrity。", "MLPerf Storage/DLIO training semantics", "P1/P2/P3", "数据集存在且可读", "测试", "Training cases", "训练完成；文件/样本计数和校验一致", "training_summary.json; integrity_report.json", "Open"],
  ["REQ-TRN-002", "Training read path shall report throughput、stall/idle time、queue and thermal state separately from model compute time。", "AI workload storage contribution", "P1/P2/P3", "GPU/CPU telemetry enabled", "测试+分析", "Training representative cases", "指标字段完整；存储stall可解释", "windows_disk_1s.csv; workload_summary.json", "Open"],
  ["REQ-CKP-001", "Checkpoint write and read shall preserve file size、hash and restore result across the configured cycle。", "数据完整性与恢复验证", "P1/P2/P3", "checkpoint目录可写", "测试", "Checkpoint cases", "每个checkpoint hash一致；restore成功", "checkpoint_manifest.json; integrity_report.json", "Open"],
  ["REQ-CKP-002", "Checkpoint path shall report write/read bandwidth and P99 latency without hiding flush/fsync time。", "大块写读和持久化语义", "P1/P2/P3", "flush策略已记录", "测试+分析", "Checkpoint performance cases", "flush/close时间可追踪；P99按case阈值", "io_trace.csv; summary.json", "Open"],
  ["REQ-KVC-001", "KV cache spill/fetch shall preserve key-range, tensor shape and hit/miss correctness under the configured policy。", "KV cache offloading semantics", "P1/P2/P3", "KV policy和模型版本锁定", "测试", "KV cache cases", "命中/未命中、shape和内容校验全部通过", "kvcache_report.json; integrity_report.json", "Open"],
  ["REQ-KVC-002", "KV cache case shall report object size、spill/fetch latency、concurrency and SSD tail latency。", "小对象随机I/O与并发", "P1/P2/P3", "trace or native client ready", "测试+分析", "KV cache performance cases", "P50/P95/P99完整；并发与队列可解释", "windows_disk_1s.csv; kvcache_summary.json", "Open"],
  ["REQ-VDB-001", "VectorDB ingest/index/search shall persist and return the expected vector count and query consistency。", "Milvus/vector database workload", "P1/P2/P3", "Docker/Milvus ready", "测试", "VectorDB cases", "count、top-k和重复查询一致；重启后可加载", "milvus_log.txt; vectordb_integrity.json", "Open"],
  ["REQ-VDB-002", "VectorDB case shall separate ingest、index build、load and ANN search I/O and report P99 query latency。", "ANN phases have different SSD profiles", "P1/P2/P3", "index type/metric locked", "测试+分析", "VectorDB performance cases", "阶段分段有指标；P99按case阈值", "phase_summary.json; windows_disk_1s.csv", "Open"],
  ["REQ-QOS-001", "Mixed workloads shall report per-workload P95/P99 and queue/throughput impact instead of only aggregate throughput。", "System-level QoS/interference", "P2/P3", "单 workload baseline已通过", "测试+分析", "Mixed QoS cases", "每个 workload 有独立指标；尾延迟放大可解释", "qos_summary.json; windows_disk_1s.csv", "Open"],
  ["REQ-REL-001", "Long-run/occupancy cases shall record temperature、thermal throttle、performance drift、errors and free-space trajectory。", "Consumer SSD thermal/GC risk", "P2/P3", "温度和事件采集可用", "测试", "Stability/occupancy cases", "时长达到case要求；无未预期掉盘/错误；漂移按阈值", "timeseries.csv; eventlog.txt", "Open"],
  ["REQ-REC-001", "After restart/reconnect or controlled fault, the system shall restore service and retain verified data。", "NASA V&V recovery evidence", "P1/P2/P3", "备份/恢复步骤已评审", "测试+演示", "Recovery cases", "服务恢复；数据校验和/查询/restore通过；无新设备错误", "recovery_report.json; eventlog.txt", "Open"],
  ["REQ-DATA-001", "All data-bearing cases shall produce objective integrity evidence and classify missing evidence as INVALID/NOT RUN。", "NASA SWE-065/SWE-071 evidence rules", "P1/P2/P3", "校验工具可用", "测试+检查", "所有 data-bearing cases", "完整性报告存在且通过；缺证据不得PASS", "integrity_report.json; verdict.json", "Open"],
  ["REQ-HLK-001", "NVMe device shall be tested as Storage Controller and Storage Disk using the applicable Windows HLK playlist before release comparison。", "Microsoft NVMe HLK overview", "P1/P2/P3", "HLK controller/test system ready", "测试", "HLK/Stage 0-1 cases", "必需playlist全部通过；未执行标记NOT RUN", "HLK result package", "Advisory"],
  ["REQ-RPL-001", "Trace/Replay shall preserve timestamp、direction、size、offset and sequence semantics and clearly state its logical-only scope。", "fio log fields；trace boundary", "P1/P2/P3", "trace schema and replay tool locked", "测试+分析", "Trace/Replay/Hybrid cases", "字段完整；节奏误差和逻辑/物理bytes分开报告", "trace.csv; replay_summary.json", "Open"],
];

const caseIdsByReq = new Map();
for (const row of allStandardRows) {
  for (const req of String(row[7]).split(";").map((x) => x.trim()).filter(Boolean)) {
    if (!caseIdsByReq.has(req)) caseIdsByReq.set(req, []);
    caseIdsByReq.get(req).push(row[0]);
  }
}
const reqRows = reqSpecs.map((r) => {
  const idx = r[0];
  return [...r.slice(0, 6), (caseIdsByReq.get(idx) ?? []).join(", "), ...r.slice(7)];
});

function addTableSheet(name, title, subtitle, headers, rows, opts = {}) {
  const sheet = wb.worksheets.add(name);
  const last = colLetter(headers.length - 1);
  titleBlock(sheet, title, subtitle, last);
  sheet.getRange(`A5:${last}5`).values = [headers];
  headerStyle(sheet.getRange(`A5:${last}5`), opts.headerFill ?? palette.navy);
  if (rows.length) sheet.getRange(`A6:${last}${rows.length + 5}`).values = rows;
  if (rows.length) bodyStyle(sheet.getRange(`A6:${last}${rows.length + 5}`));
  sheet.getRange(`A5:${last}${rows.length + 5}`).format.rowHeight = opts.rowHeight ?? 68;
  sheet.freezePanes.freezeRows(5);
  if (opts.freezeCols) sheet.freezePanes.freezeColumns(opts.freezeCols);
  if (rows.length) sheet.tables.add(`A5:${last}${rows.length + 5}`, true, opts.tableName ?? `${name.replace(/[^A-Za-z0-9]/g, "")}Table`);
  setWidths(sheet, opts.widths ?? headers.map(() => 18));
  return sheet;
}

const requirementsSheet = addTableSheet(
  "标准化需求矩阵",
  "标准化测试需求矩阵",
  "需求采用 REQ-ID；每条需求均有来源、验证方法、量化标准和关联 Case，满足双向追溯要求。",
  ["需求ID", "需求文本", "来源/理由", "适用档位", "前置条件", "验证方法", "关联Case ID", "量化验收标准", "客观证据", "状态"],
  reqRows,
  { widths: [16, 40, 28, 14, 24, 14, 34, 34, 30, 12], rowHeight: 86, tableName: "RequirementsTable", headerFill: palette.teal, freezeCols: 1 },
);

const caseSheet = addTableSheet(
  "标准化Case矩阵",
  "标准化系统级测试用例矩阵（29核心 + 8可选）",
  "前7列为执行人员强制字段；后续字段用于可复现配置、监控、判定和证据审计。原核心/可选 case 定义保持不变。",
  caseHeaders,
  allStandardRows,
  { widths: [15, 25, 34, 42, 13, 30, 32, 25, 11, 11, 16, 20, 12, 14, 18, 28, 28, 29, 24, 28, 18, 22, 24, 34, 30, 32, 22, 22, 18, 28, 16, 16, 22, 14], rowHeight: 100, tableName: "StandardCasesTable", headerFill: palette.navy, freezeCols: 2 },
);

const simpleHeaders = [...requiredHeaders, "需求ID", "阶段", "执行模式", "结果"];
const simpleRows = allStandardRows.map((r) => [r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[14], r[28]]);
addTableSheet(
  "标准化简化Case",
  "简化版执行 Case 清单",
  "执行人员只需按这 11 列操作；详细配置、监控、证据和无效条件回到“标准化Case矩阵”。",
  simpleHeaders,
  simpleRows,
  { widths: [15, 25, 34, 42, 13, 30, 32, 25, 11, 18, 16], rowHeight: 96, tableName: "SimpleCasesTable", headerFill: palette.blue, freezeCols: 1 },
);

const rtmRows = allStandardRows.map((r) => [r[0], r[7], r[8], r[9], r[10], r[13], r[14], modeMethod(r[14]), r[28], defaultEvidence(r[14])]);
addTableSheet(
  "RTM",
  "需求—Case—证据追溯矩阵",
  "从需求到 Case、再到证据包的正向追溯；“标准化需求矩阵”中的关联Case ID提供反向追溯入口。",
  ["Case ID", "需求ID", "阶段", "优先级", "测试家族", "内存+显存", "执行模式", "验证方法", "结果", "应生成证据"],
  rtmRows,
  { widths: [15, 24, 12, 10, 18, 14, 18, 16, 16, 54], rowHeight: 62, tableName: "RtmTable", headerFill: palette.teal, freezeCols: 2 },
);

const evidenceRows = [
  ["报告元数据", "Test/Report Date；Operator；Auditor；Specification Version", "每次run前填写并写入manifest", "manifest.json", "缺失时INVALID"],
  ["DUT硬件", "主板、CPU、DRAM、GPU/VRAM、SSD厂商/型号/序列号/固件/容量/链路", "Stage 0；换盘/换固件后重采集", "dut_identity.json", "字段完整率100%"],
  ["软件环境", "Windows版本、驱动、文件系统、MLPerf Storage版本、脚本commit", "Stage 0；脚本变更后重采集", "software_manifest.json", "版本可追溯"],
  ["I/O参数", "rw、bs、iodepth、numjobs、runtime、ramp_time、size、direct、seed", "Stage 1或每个trace/replay case", "fio_job.fio; configview.txt", "参数完整且可复现"],
  ["Windows监控", "PhysicalDisk bytes/IOPS/latency/queue/busy、温度、CPU、RAM、GPU、paging、WHEA/StorPort", "1秒采样；与run时间对齐", "windows_disk_1s.csv; eventlog.txt", "采样完整率≥99%"],
  ["应用结果", "吞吐、IOPS、P50/P95/P99、stall、AU、迭代/查询/restore结果", "每个run结束后自动生成", "workload_summary.json", "按case阈值判定"],
  ["完整性", "文件数、大小、hash、checkpoint restore、向量count/top-k、KV命中/shape", "写后、读后、重启后分别验证", "integrity_report.json", "无错误/无遗漏"],
  ["Trace/Replay", "timestamp、direction、size、offset、sequence/seed、logical bytes与physical bytes", "录制与replay各留一份", "trace.csv; replay_summary.json", "只报告逻辑I/O边界"],
  ["判定", "PASS/CONDITIONAL/FAIL/INVALID/NOT RUN；异常、偏差、证据路径", "结束后审阅；缺关键证据禁止PASS", "verdict.json", "状态可审计"],
];
addTableSheet(
  "执行与证据",
  "执行控制、监控与证据清单",
  "按 ISO 29119-3 / NASA V&V 的客观证据原则组织；测试数据与结果目录与代码仓库分离。",
  ["证据类别", "最小字段/内容", "采集时机", "文件/输出", "判定规则"],
  evidenceRows,
  { widths: [18, 58, 28, 34, 24], rowHeight: 66, tableName: "EvidenceTable", headerFill: palette.blue, freezeCols: 1 },
);

const sourceRows = [
  ["SNIA SSS PTS", "https://www.snia.org/tech_activities/standards/curr_standards/pts", "性能测试、预处理/稳态、报告元数据和客户端/消费级口径"],
  ["SNIA PTS Testing Service", "https://www.snia.org/forums/sssi/ptstest", "IOPS/吞吐/延迟/工作集/数据完整性测试族"],
  ["SNIA PTS Technical Position", "https://www.snia.org/forums/sssi/pts/tp", "稳态窗口、漂移和性能收敛判定"],
  ["NVM Express Specifications", "https://nvmexpress.org/specifications/", "NVMe健康、错误、Sanitize、功耗/协议依据"],
  ["Microsoft NVMe HLK Overview", "https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/nvme-ssd-testing-overview", "Controller + Disk 角色测试与官方playlist门禁"],
  ["Microsoft Device.Storage tests", "https://learn.microsoft.com/en-us/windows-hardware/test/hlk/testref/device-storage-tests", "Windows存储设备压力、队列、重置和I/O测试参考"],
  ["ISO/IEC/IEEE 29119-3", "https://www.iso.org/standard/79429.html", "测试文档模板、测试条件、结果和报告结构"],
  ["NASA Systems Engineering Handbook", "https://www.nasa.gov/reference/system-engineering-handbook-appendix/", "需求分解、V&V方法、验证矩阵和客观证据"],
  ["NASA SWE-065/071/072", "https://swehb.nasa.gov/spaces/SWEHBVD/pages/102695448/SWE-065+Test+Plan%2C+Procedures%2C+Reports?desktop=true&macroName=show-if", "可测量验收、测试计划/报告、双向追溯"],
  ["fio HOWTO", "https://github.com/axboe/fio/blob/master/HOWTO.rst", "job复现、稳态、verify、JSON/latency percentile和trace字段"],
  ["Microsoft Physical Disk counters", "https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-performance-problems-in-windows", "Windows物理磁盘与进程I/O关联和阈值参考"],
];
addTableSheet(
  "来源与规范",
  "规范来源与本方案映射",
  "URL 仅作为设计依据和复核入口；实际执行版本须写入报告元数据并锁定。",
  ["来源", "官方链接", "本方案如何使用"],
  sourceRows,
  { widths: [30, 70, 60], rowHeight: 66, tableName: "SourcesTable", headerFill: palette.teal, freezeCols: 1 },
);

const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outputPath);

const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const check = await reopened.inspect({ kind: "table", sheetId: "标准化Case矩阵", range: "A5:G12", include: "values", tableMaxRows: 8, tableMaxCols: 7, maxChars: 6000 });
await fs.writeFile(path.join(outputDir, "case_check.ndjson"), check.ndjson ?? String(check), "utf8");
const reqCheck = await reopened.inspect({ kind: "table", sheetId: "标准化需求矩阵", range: "A5:J12", include: "values", tableMaxRows: 8, tableMaxCols: 10, maxChars: 6000 });
await fs.writeFile(path.join(outputDir, "requirement_check.ndjson"), reqCheck.ndjson ?? String(reqCheck), "utf8");
let errors;
try {
  errors = await reopened.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, maxChars: 2000 });
} catch (err) {
  errors = { ndjson: `error-scan-unavailable: ${err.message}` };
}
await fs.writeFile(path.join(outputDir, "formula_error_scan.ndjson"), errors.ndjson ?? String(errors), "utf8");

for (const sheetName of ["标准化需求矩阵", "标准化Case矩阵", "标准化简化Case", "RTM", "执行与证据", "来源与规范"]) {
  const preview = await reopened.render({ sheetName, autoCrop: "all", scale: 0.55, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

console.log(JSON.stringify({ outputPath, coreCases: coreRows.length, optionalCases: optionalRows.length, totalCases: allStandardRows.length, requirements: reqRows.length, formulaErrors: errors.ndjson ?? String(errors) }, null, 2));
