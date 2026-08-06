import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoRoot = "C:/Users/Administrator/Documents/Code/repos/storage";
const trainingPath = `${repoRoot}/docs/AI_SSD_TRAINING_CASE_PLAN.xlsx`;
const remainingPath = `${repoRoot}/docs/AI_SSD_REMAINING_CASE_PLAN.xlsx`;
const outputDir = `${repoRoot}/outputs/ai_ssd_all_case_plan_capacity_20260806`;
const outputPath = `${outputDir}/AI_SSD_ALL_CASE_PLAN.xlsx`;
const docsOutputPath = `${repoRoot}/docs/AI_SSD_ALL_CASE_PLAN.xlsx`;

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

const selectedCases = new Set([
  "AI-TRN-001", "AI-TRN-004", "AI-TRN-006", "AI-TRN-010", "AI-TRN-014", "AI-TRN-016",
  "AI-BASE-001", "AI-BASE-002", "AI-BASE-003",
  "AI-CKP-001", "AI-CKP-002", "AI-CKP-008", "AI-CKP-009",
  "AI-KV-001", "AI-KV-002", "AI-KV-007", "AI-KV-015", "AI-KV-016", "AI-KV-020",
  "AI-VDB-001", "AI-VDB-002", "AI-VDB-003", "AI-VDB-009", "AI-VDB-014", "AI-VDB-016",
  "AI-MIX-001", "AI-MIX-002", "AI-MIX-003", "AI-MIX-004",
]);

// Capacity applies to the fixed-pSLC comparison.  2TB/4TB is used where the
// selected workload needs a larger working set or sustained mixed-load margin;
// other cases are directly runnable on all three SKU capacities.
const selectedCapacity = new Map([
  ["AI-TRN-001", "2TB / 4TB"],
  ["AI-TRN-004", "1TB / 2TB / 4TB"],
  ["AI-TRN-006", "2TB / 4TB"],
  ["AI-TRN-010", "2TB / 4TB"],
  ["AI-TRN-014", "2TB / 4TB"],
  ["AI-TRN-016", "1TB / 2TB / 4TB"],
  ["AI-BASE-001", "1TB / 2TB / 4TB"],
  ["AI-BASE-002", "1TB / 2TB / 4TB"],
  ["AI-BASE-003", "1TB / 2TB / 4TB"],
  ["AI-CKP-001", "1TB / 2TB / 4TB"],
  ["AI-CKP-002", "1TB / 2TB / 4TB"],
  ["AI-CKP-008", "1TB / 2TB / 4TB"],
  ["AI-CKP-009", "2TB / 4TB"],
  ["AI-KV-001", "1TB / 2TB / 4TB"],
  ["AI-KV-002", "1TB / 2TB / 4TB"],
  ["AI-KV-007", "1TB / 2TB / 4TB"],
  ["AI-KV-015", "1TB / 2TB / 4TB"],
  ["AI-KV-016", "1TB / 2TB / 4TB"],
  ["AI-KV-020", "2TB / 4TB"],
  ["AI-VDB-001", "1TB / 2TB / 4TB"],
  ["AI-VDB-002", "1TB / 2TB / 4TB"],
  ["AI-VDB-003", "1TB / 2TB / 4TB"],
  ["AI-VDB-009", "1TB / 2TB / 4TB"],
  ["AI-VDB-014", "1TB / 2TB / 4TB"],
  ["AI-VDB-016", "2TB / 4TB"],
  ["AI-MIX-001", "2TB / 4TB"],
  ["AI-MIX-002", "2TB / 4TB"],
  ["AI-MIX-003", "2TB / 4TB"],
  ["AI-MIX-004", "2TB / 4TB"],
]);

const defaultCapacity = "1TB / 2TB / 4TB";

function normalizeRow(row) {
  return [...row, ...Array(Math.max(0, 9 - row.length)).fill(null)].slice(0, 9);
}

function transformValues(sourceValues) {
  return sourceValues.map((sourceRow, index) => {
    const row = normalizeRow(sourceRow);
    if (index === 6) {
      row[8] = "Capacity";
    } else if (index >= 7 && typeof row[1] === "string" && row[1].startsWith("AI-")) {
      row[2] = "mlperform";
      row[8] = selectedCapacity.get(row[1]) ?? defaultCapacity;
    }
    return row;
  });
}

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

function applyCommonLayout(sheet, name, values) {
  const endRow = values.length;
  const headers = values[6] ?? [];
  if (headers.length !== 9 || headers[0] !== "类别" || headers[8] !== "Capacity") throw new Error(`${name} does not have the expected nine-column header`);
  sheet.showGridLines = false;
  sheet.getRange(`A1:I${endRow}`).values = values;
  setTitle(sheet, "A1:I1", values[0][0]);
  setNote(sheet, "A2:I2", values[1][0]);
  setNote(sheet, "A3:I3", values[2][0]);
  sheet.getRange("B6").formulas = [[`=COUNTA('${name}'!$B$8:$B$${endRow})`]];
  sheet.getRange("A5:I5").format = { fill: colors.blueLight, font: { bold: true, color: colors.navy }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
  sheet.getRange("A6:I6").format = { fill: colors.white, font: { bold: true, color: colors.blue, size: 11 }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
  sheet.getRange("A5:I6").format.borders = { preset: "outside", style: "thin", color: colors.border };
  formatHeader(sheet, "A7:I7");
  formatBody(sheet, `A8:I${endRow}`);
  for (let row = 8; row <= endRow; row++) {
    const caseId = values[row - 1]?.[1];
    sheet.getRange(`A${row}:I${row}`).format.fill = selectedCases.has(caseId) ? colors.green : colors.white;
  }
  sheet.getRange(`B8:B${endRow}`).format = { font: { bold: true, color: colors.blue }, horizontalAlignment: "center", verticalAlignment: "top" };
  sheet.getRange(`I8:I${endRow}`).format = { font: { bold: true, color: colors.navy }, horizontalAlignment: "center", verticalAlignment: "top", wrapText: true };
  sheet.getRange(`A8:I${endRow}`).format.rowHeight = 150;
  sheet.tables.add(`A7:I${endRow}`, true, `${name.replaceAll(" ", "_")}ExecutionTable`);
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
  sheet.getRange("I:I").format.columnWidth = 20;
  sheet.getUsedRange().format.font.name = "Microsoft YaHei";
}

function buildSelectedSheet(workbook, selectedRows) {
  const name = "精选 Case汇总表";
  const sheet = workbook.worksheets.add(name);
  const endRow = 7 + selectedRows.length;
  sheet.showGridLines = false;
  setTitle(sheet, "A1:I1", "AI SSD 精选 Case 汇总表");
  setNote(sheet, "A2:I2", "汇总 6 类 workload 的首轮精选 Case；测试工具统一为 mlperform，Capacity 为固定 pSLC（SLC）配置下建议执行的 SSD 容量。\n1TB / 2TB / 4TB：可在三种容量上直接对比；2TB / 4TB：建议优先用于较大工作集或持续混合负载。\n");
  setNote(sheet, "A3:I3", "精选数量：29 个；绿色行与各分类页的首轮精选保持一致。测试命令沿用各 case 的独立脚本入口。");
  sheet.getRange("A5:I5").values = [["精选 Case 数", null, "容量口径", null, "测试工具", null, "步骤格式", null, "固定 SLC"]];
  sheet.getRange("A6:I6").values = [[null, null, "1TB / 2TB / 4TB", null, "mlperform", null, "1. 2. 3. 4.", null, "固定 pSLC"]];
  sheet.getRange("B6").formulas = [[`=COUNTA('${name}'!$B$8:$B$${endRow})`]];
  sheet.getRange("A5:I5").format = { fill: colors.blueLight, font: { bold: true, color: colors.navy }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
  sheet.getRange("A6:I6").format = { fill: colors.white, font: { bold: true, color: colors.blue, size: 11 }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
  sheet.getRange("A5:I6").format.borders = { preset: "outside", style: "thin", color: colors.border };
  sheet.getRange("A7:I7").values = [["类别", "Case ID", "测试工具", "测试目的", "测试步骤", "测试时长", "测试命令", "测试标准", "Capacity"]];
  formatHeader(sheet, "A7:I7");
  sheet.getRange(`A8:I${endRow}`).values = selectedRows;
  formatBody(sheet, `A8:I${endRow}`);
  sheet.getRange(`A8:I${endRow}`).format.fill = colors.green;
  sheet.getRange(`B8:B${endRow}`).format = { font: { bold: true, color: colors.blue }, horizontalAlignment: "center", verticalAlignment: "top" };
  sheet.getRange(`I8:I${endRow}`).format = { font: { bold: true, color: colors.navy }, horizontalAlignment: "center", verticalAlignment: "top", wrapText: true };
  sheet.getRange(`A8:I${endRow}`).format.rowHeight = 150;
  sheet.tables.add(`A7:I${endRow}`, true, "SelectedCaseExecutionTable");
  sheet.freezePanes.freezeRows(7);
  sheet.freezePanes.freezeColumns(2);
  sheet.getRange("A:A").format.columnWidth = 18;
  sheet.getRange("B:B").format.columnWidth = 14;
  sheet.getRange("C:C").format.columnWidth = 18;
  sheet.getRange("D:D").format.columnWidth = 44;
  sheet.getRange("E:E").format.columnWidth = 70;
  sheet.getRange("F:F").format.columnWidth = 18;
  sheet.getRange("G:G").format.columnWidth = 65;
  sheet.getRange("H:H").format.columnWidth = 58;
  sheet.getRange("I:I").format.columnWidth = 20;
  sheet.getUsedRange().format.font.name = "Microsoft YaHei";
  return sheet;
}

const trainingWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(trainingPath));
const remainingWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(remainingPath));
const workbook = Workbook.create();
const selectedRows = [];
const sourceSheets = [
  [trainingWorkbook, "Training Case表"],
  [remainingWorkbook, "BASE Case表"],
  [remainingWorkbook, "Checkpoint Case表"],
  [remainingWorkbook, "KV Cache Case表"],
  [remainingWorkbook, "VectorDB Case表"],
  [remainingWorkbook, "Mixed Case表"],
];

for (const [sourceWorkbook, name] of sourceSheets) {
  const sourceSheet = sourceWorkbook.worksheets.getItem(name);
  const values = transformValues(sourceSheet.getUsedRange().values);
  const sheet = workbook.worksheets.add(name);
  applyCommonLayout(sheet, name, values);
  for (const row of values.slice(7)) {
    if (selectedCases.has(row[1])) selectedRows.push(row);
  }
  const preview = await workbook.render({ sheetName: name, range: `A1:I${values.length}`, scale: 1, format: "png" });
  await fs.mkdir(outputDir, { recursive: true });
  await fs.writeFile(`${outputDir}/${name.replaceAll(" ", "_")}_preview.png`, new Uint8Array(await preview.arrayBuffer()));
}

if (selectedRows.length !== selectedCases.size) throw new Error(`expected ${selectedCases.size} selected rows, got ${selectedRows.length}`);
buildSelectedSheet(workbook, selectedRows);
const selectedPreview = await workbook.render({ sheetName: "精选 Case汇总表", range: `A1:I${7 + selectedRows.length}`, scale: 1, format: "png" });
await fs.writeFile(`${outputDir}/精选_Case汇总表_preview.png`, new Uint8Array(await selectedPreview.arrayBuffer()));

const sheetCheck = await workbook.inspect({ kind: "sheet", include: "id,name" });
console.log(sheetCheck.ndjson);
const tableCheck = await workbook.inspect({ kind: "table", sheetId: "精选 Case汇总表", range: `A1:I${7 + selectedRows.length}`, include: "values,formulas", tableMaxRows: 40, tableMaxCols: 10, tableMaxCellChars: 220 });
console.log(tableCheck.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "all case plan formula error scan" });
console.log(errors.ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await fs.mkdir(outputDir, { recursive: true });
await output.save(outputPath);
await output.save(docsOutputPath);
console.log(`saved ${outputPath}`);
console.log(`saved ${docsOutputPath}`);
console.log(`sheet_count=${sourceSheets.length + 1}`);
console.log(`selected_case_count=${selectedCases.size}`);
