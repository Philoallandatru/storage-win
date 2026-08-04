import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const repo = "C:/Users/Administrator/Documents/Code/repos/storage";
const inputPath = path.join(repo, "outputs", "ai_pc_consumer_ssd_case_matrix_20260803", "AI_PC_CONSUMER_SSD_TEST_CASE_MATRIX.xlsx");
const outputDir = path.join(repo, "outputs", "ai_pc_consumer_ssd_case_matrix_reworded_20260804");
const outputPath = path.join(outputDir, "AI_PC_CONSUMER_SSD_TEST_CASE_MATRIX_reworded.xlsx");
const previewDir = path.join(outputDir, "preview");

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
    .replace(/建立可复现的 /g, "建立")
    .replace(/，并/g, "；")
    .replace(/，确认/g, "；确认")
    .replace(/，检查/g, "；检查")
    .replace(/，比较/g, "；比较")
    .replace(/，记录/g, "；记录")
    .replace(/，分别/g, "；分别");
}

function mapRange(sheet, address, mapper) {
  const range = sheet.getRange(address);
  const values = range.values;
  range.values = values.map((row) => row.map(mapper));
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const overview = wb.worksheets.getItem("目录与说明");
const core = wb.worksheets.getItem("核心Case矩阵");
const simple = wb.worksheets.getItem("简化Case清单");
const optional = wb.worksheets.getItem("可选Case清单");
const config = wb.worksheets.getItem("配置基线");
const trace = wb.worksheets.getItem("执行方式边界");
const monitor = wb.worksheets.getItem("监控与判定");

// Preserve the original case set: only rewrite wording fields.
const coreBody = core.getRange("A6:W34").values;
const coreIdsBefore = coreBody.map((row) => row[0]);
if (coreIdsBefore.length !== 29) throw new Error(`Expected 29 core cases, got ${coreIdsBefore.length}`);
core.getRange("C6:C34").values = coreBody.map((row) => [concise(row[2])]);
core.getRange("D6:D34").values = coreBody.map((row) => [numberedSteps(row[3])]);
core.getRange("G6:G34").values = coreBody.map((row) => [concise(row[6])]);
core.getRange("P6:P34").values = coreBody.map((row) => [concise(row[15])]);
core.getRange("Q6:Q34").values = coreBody.map((row) => [concise(row[16])]);
core.getRange("R6:R34").values = coreBody.map((row) => [concise(row[17])]);
core.getRange("S6:S34").values = coreBody.map((row) => [concise(row[18])]);
core.getRange("D6:D34").format.wrapText = true;
core.getRange("A6:W34").format.rowHeight = 86;

const simpleBody = simple.getRange("A6:L34").values;
const simpleIdsBefore = simpleBody.map((row) => row[0]);
if (simpleIdsBefore.length !== 29) throw new Error(`Expected 29 simplified cases, got ${simpleIdsBefore.length}`);
simple.getRange("C6:C34").values = simpleBody.map((row) => [concise(row[2])]);
simple.getRange("D6:D34").values = simpleBody.map((row) => [numberedSteps(row[3])]);
simple.getRange("G6:G34").values = simpleBody.map((row) => [concise(row[6])]);
simple.getRange("D6:D34").format.wrapText = true;
simple.getRange("A6:L34").format.rowHeight = 86;

const optionalBody = optional.getRange("A6:M13").values;
const optionalIdsBefore = optionalBody.map((row) => row[0]);
if (optionalIdsBefore.length !== 8) throw new Error(`Expected 8 optional cases, got ${optionalIdsBefore.length}`);
optional.getRange("F6:F13").values = optionalBody.map((row) => [concise(row[5])]);
optional.getRange("G6:G13").values = optionalBody.map((row) => [numberedSteps(row[6])]);
optional.getRange("K6:K13").values = optionalBody.map((row) => [concise(row[10])]);
optional.getRange("L6:L13").values = optionalBody.map((row) => [concise(row[11])]);
optional.getRange("G5").values = [["测试步骤"]];
optional.getRange("G6:G13").format.wrapText = true;
optional.getRange("A6:M13").format.rowHeight = 86;

// Shorten the surrounding page text without changing case definitions.
overview.getRange("A4").values = [["使用方式"]];
overview.getRange("B4").values = [["先看配置基线，再按 Stage 0→6 执行；按执行模式区分 Native、Scaled、Trace/Replay 和 Hybrid。"]];
overview.getRange("A6").values = [["核心矩阵统计"]];
overview.getRange("B6").values = [["公式自动汇总；结果列可直接填写。"]];
overview.getRange("A22").values = [["设计思路：UNet3D测大文件带宽；RetinaNet测小文件IOPS；ResNet50测中等对象；Checkpoint测大块写读；KV测小对象并发和spill；VectorDB测随机ANN。顺序为：路径门禁 → Native基线 → 混合QoS → 稳定性 → 恢复完整性。"]];
core.getRange("A2").values = [["执行顺序：Stage 0 门禁 → Stage 1 I/O口径 → Stage 2 smoke → Stage 3 基线 → Stage 4 混合QoS → Stage 5 稳定性 → Stage 6 恢复。"]];
simple.getRange("A2").values = [["执行人员按 Case ID、工具、目的、步骤、时长、脚本和标准执行；详细配置与监控见核心矩阵。"]];
optional.getRange("A2").values = [["主矩阵通过后再执行；覆盖扩展模型、对象大小、压缩索引、RAG行为和长期占用率。结果不与核心29 case混合。"]];
config.getRange("A2").values = [["固定容量、内存、模型规模、工作集预算和执行口径；不同档位结果分开比较。"]];
trace.getRange("A1").values = [["执行方式边界：Native 与 trace/replay"]];
trace.getRange("A2").values = [["Native 看业务正确性和端到端性能；Trace/Replay 看可复现 SSD I/O；Scaled/Hybrid 必须单独标记。"]];
monitor.getRange("A2").values = [["每个性能 case 保存 workload、Windows 1秒监控、trace（如适用）、integrity 和 verdict；缺关键证据不得 PASS。"]];

// Compact supporting tables while preserving formulas and result cells.
mapRange(trace, "A6:G10", concise);
mapRange(monitor, "A6:E12", concise);
mapRange(monitor, "A18:D24", concise);

const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outputPath);

const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const reopenedCore = reopened.worksheets.getItem("核心Case矩阵");
const reopenedSimple = reopened.worksheets.getItem("简化Case清单");
const reopenedOptional = reopened.worksheets.getItem("可选Case清单");
const idsAfter = reopenedCore.getRange("A6:A34").values.flat();
const simpleIdsAfter = reopenedSimple.getRange("A6:A34").values.flat();
const optionalIdsAfter = reopenedOptional.getRange("A6:A13").values.flat();
if (JSON.stringify(idsAfter) !== JSON.stringify(coreIdsBefore)) throw new Error("Core case IDs changed");
if (JSON.stringify(simpleIdsAfter) !== JSON.stringify(simpleIdsBefore)) throw new Error("Simplified case IDs changed");
if (JSON.stringify(optionalIdsAfter) !== JSON.stringify(optionalIdsBefore)) throw new Error("Optional case IDs changed");

for (const sheetName of ["目录与说明", "核心Case矩阵", "简化Case清单", "可选Case清单", "配置基线", "执行方式边界", "监控与判定"]) {
  const png = await wb.render({ sheetName, autoCrop: "all", scale: 0.75, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await png.arrayBuffer()));
}

const sheetCheck = await reopened.inspect({ kind: "sheet", include: "id,name", maxChars: 2500 });
await fs.writeFile(path.join(outputDir, "reopened_sheet_check.ndjson"), sheetCheck.ndjson ?? String(sheetCheck), "utf8");
const formulaCheck = await reopened.inspect({ kind: "formula", sheetId: "目录与说明", range: "A1:J22", maxChars: 3000, options: { maxResults: 50 } });
await fs.writeFile(path.join(outputDir, "formula_inspect.ndjson"), formulaCheck.ndjson ?? String(formulaCheck), "utf8");
let errorCheck;
try {
  errorCheck = await reopened.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, maxChars: 3000 });
} catch (err) {
  errorCheck = { ndjson: `error-scan-unavailable: ${err.message}` };
}
await fs.writeFile(path.join(outputDir, "formula_error_scan.ndjson"), errorCheck.ndjson ?? String(errorCheck), "utf8");

console.log(JSON.stringify({ outputPath, coreCases: idsAfter.length, optionalCases: optionalIdsAfter.length, preservedCaseIds: true, previewDir, formulaErrorScan: errorCheck.ndjson ?? String(errorCheck) }, null, 2));
