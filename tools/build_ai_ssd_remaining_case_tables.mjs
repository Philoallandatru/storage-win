import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoRoot = "C:/Users/Administrator/Documents/Code/repos/storage";
const sourcePath = `${repoRoot}/docs/AI_SSD_TEST_PLAN.xlsx`;
const catalogPath = `${repoRoot}/ai_ssd_test_cases/case_catalog.json`;
const outputDir = `${repoRoot}/outputs/ai_ssd_remaining_case_plan_20260806`;
const outputPath = `${outputDir}/AI_SSD_REMAINING_CASE_PLAN.xlsx`;

const colors = {
  navy: "#153B63",
  blue: "#1F5A87",
  blueLight: "#DCEAF5",
  pale: "#F2F7FB",
  green: "#E7F3EC",
  text: "#243447",
  muted: "#60758A",
  border: "#C8D5E1",
  white: "#FFFFFF",
};

const moduleInfo = {
  base: { sheet: "BASE Case表", title: "AI SSD BASE Case 执行表", label: "基础门禁", tool: "Python Case Runner + Windows PhysicalDisk 监控 + 路径校验" },
  checkpoint: { sheet: "Checkpoint Case表", title: "AI SSD Checkpoint Case 执行表", label: "Checkpoint 持久化", tool: "Checkpoint Case Script + fsync/Hash + Windows PhysicalDisk 监控" },
  kv: { sheet: "KV Cache Case表", title: "AI SSD KV Cache Case 执行表", label: "KV Cache", tool: "KV Cache Case Script + tier 读写/P99 + Windows PhysicalDisk 监控" },
  vdb: { sheet: "VectorDB Case表", title: "AI SSD VectorDB Case 执行表", label: "VectorDB", tool: "VectorDB Case Script + Recall/QPS/P99 + Windows PhysicalDisk 监控" },
  mixed: { sheet: "Mixed Case表", title: "AI SSD Mixed Case 执行表", label: "混合负载", tool: "Mixed Case Script + 前后台监控 + Windows PhysicalDisk 监控" },
};

const selectedCases = new Set([
  "AI-BASE-001", "AI-BASE-002", "AI-BASE-003",
  "AI-CKP-001", "AI-CKP-002", "AI-CKP-008", "AI-CKP-009",
  "AI-KV-001", "AI-KV-002", "AI-KV-007", "AI-KV-015", "AI-KV-016", "AI-KV-020",
  "AI-VDB-001", "AI-VDB-002", "AI-VDB-003", "AI-VDB-009", "AI-VDB-014", "AI-VDB-016",
  "AI-MIX-001", "AI-MIX-002", "AI-MIX-003", "AI-MIX-004",
]);

function setTitle(sheet, range, text) {
  sheet.mergeCells(range);
  sheet.getRange(range.split(":")[0]).values = [[text]];
  sheet.getRange(range).format = { fill: colors.navy, font: { bold: true, color: colors.white, size: 16 }, verticalAlignment: "center" };
  sheet.getRange(range).format.rowHeight = 32;
}

function setNote(sheet, range, text) {
  sheet.mergeCells(range);
  sheet.getRange(range.split(":")[0]).values = [[text]];
  sheet.getRange(range).format = { fill: colors.pale, font: { color: colors.muted, size: 10 }, wrapText: true, verticalAlignment: "center" };
}

function formatHeader(sheet, range) {
  sheet.getRange(range).format = { fill: colors.blue, font: { bold: true, color: colors.white, size: 10 }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, borders: { preset: "all", style: "thin", color: colors.border } };
}

function formatBody(sheet, range) {
  sheet.getRange(range).format = { font: { color: colors.text, size: 10 }, verticalAlignment: "top", wrapText: true, borders: { preset: "inside", style: "thin", color: colors.border } };
}

const sourceWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
const sourceCaseIds = new Set();
for (const sheet of ["Case·BASE+Training", "Case·Checkpoint+KV", "Case·VDB+Mixed"]) {
  const values = sourceWorkbook.worksheets.getItem(sheet).getUsedRange().values;
  for (const row of values) if (typeof row?.[0] === "string" && row[0].startsWith("AI-")) sourceCaseIds.add(row[0]);
}
const catalog = JSON.parse(await fs.readFile(catalogPath, "utf8"));
const cases = Object.values(catalog).filter((item) => item.category !== "training");
if (cases.length !== 56) throw new Error(`expected 56 remaining cases, got ${cases.length}`);
for (const item of cases) if (!sourceCaseIds.has(item.case_id)) throw new Error(`source plan is missing ${item.case_id}`);

const workbook = Workbook.create();
for (const category of ["base", "checkpoint", "kv", "vdb", "mixed"]) {
  const info = moduleInfo[category];
  const rowsForModule = cases.filter((item) => item.category === category);
  const selectedForModule = rowsForModule.filter((item) => selectedCases.has(item.case_id));
  const sheet = workbook.worksheets.add(info.sheet);
  sheet.showGridLines = false;
  setTitle(sheet, "A1:H1", info.title);
  setNote(sheet, "A2:H2", `来源：docs/AI_SSD_TEST_PLAN.xlsx；本页整理 ${rowsForModule.length} 个 ${info.label} Case，字段与 AI_SSD_TRAINING_CASE_PLAN.xlsx 保持一致。`);
  setNote(sheet, "A3:H3", `首轮精选：${selectedForModule.map((item) => item.case_id).join("、") || "无"}；绿色行为建议首轮执行 Case，理由见 docs/AI_SSD_REMAINING_CASE_SELECTION.md。`);
  sheet.getRange("A5:H5").values = [[`${info.label} Case 数`, null, "精选 Case 数", null, "步骤格式", "脚本目录", "执行口径", "结果证据"]];
  sheet.getRange("A6:H6").values = [[null, null, null, selectedForModule.length, "1. 2. 3. 4.", "ai_ssd_test_cases/test_*.py", "先计划，后 scaled smoke/正式 workload", "Case 指标 + PhysicalDisk + 结果 manifest"]];
  sheet.getRange("B6").formulas = [[`=COUNTA('${info.sheet}'!$B$8:$B$${7 + rowsForModule.length})`]];
  sheet.getRange("A5:H5").format = { fill: colors.blueLight, font: { bold: true, color: colors.navy }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
  sheet.getRange("A6:H6").format = { fill: colors.white, font: { bold: true, color: colors.blue, size: 11 }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
  sheet.getRange("A5:H6").format.borders = { preset: "outside", style: "thin", color: colors.border };
  sheet.getRange("A7:H7").values = [["类别", "Case ID", "测试工具", "测试目的", "测试步骤", "测试时长", "测试命令", "测试标准"]];
  formatHeader(sheet, "A7:H7");
  const rows = rowsForModule.map((item) => [
    info.label,
    item.case_id,
    info.tool,
    item.purpose,
    item.steps.map((step, index) => `${index + 1}. ${step}`).join("\n").replaceAll("对应 test_training_*.py", "对应 test_*.py"),
    item.test_duration,
    item.command,
    item.standard,
  ]);
  const endRow = 7 + rows.length;
  sheet.getRange(`A8:H${endRow}`).values = rows;
  formatBody(sheet, `A8:H${endRow}`);
  rowsForModule.forEach((item, index) => {
    const row = 8 + index;
    sheet.getRange(`A${row}:H${row}`).format.fill = selectedCases.has(item.case_id) ? colors.green : colors.white;
  });
  sheet.getRange(`B8:B${endRow}`).format = { font: { bold: true, color: colors.blue }, horizontalAlignment: "center", verticalAlignment: "top" };
  sheet.getRange(`A8:H${endRow}`).format.rowHeight = 150;
  sheet.tables.add(`A7:H${endRow}`, true, `${category}CaseExecutionTable`);
  sheet.freezePanes.freezeRows(7);
  sheet.freezePanes.freezeColumns(2);
  sheet.getRange("A:A").format.columnWidth = 18;
  sheet.getRange("B:B").format.columnWidth = 14;
  sheet.getRange("C:C").format.columnWidth = 42;
  sheet.getRange("D:D").format.columnWidth = 44;
  sheet.getRange("E:E").format.columnWidth = 70;
  sheet.getRange("F:F").format.columnWidth = 18;
  sheet.getRange("G:G").format.columnWidth = 65;
  sheet.getRange("H:H").format.columnWidth = 58;
  sheet.getUsedRange().format.font.name = "Microsoft YaHei";
  const preview = await workbook.render({ sheetName: sheet.name, range: `A1:H${endRow}`, scale: 1, format: "png" });
  await fs.mkdir(outputDir, { recursive: true });
  await fs.writeFile(`${outputDir}/${category}_case_table_preview.png`, new Uint8Array(await preview.arrayBuffer()));
}

const inspect = await workbook.inspect({ kind: "table", sheetId: "KV Cache Case表", range: "A1:H29", include: "values,formulas", tableMaxRows: 30, tableMaxCols: 10, tableMaxCellChars: 240 });
console.log(inspect.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "remaining case table formula error scan" });
console.log(errors.ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await fs.mkdir(outputDir, { recursive: true });
await output.save(outputPath);
console.log(`saved ${outputPath}`);
console.log(`remaining_case_count=${cases.length}`);
console.log(`selected_case_count=${selectedCases.size}`);
