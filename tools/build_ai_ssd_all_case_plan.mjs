import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoRoot = "C:/Users/Administrator/Documents/Code/repos/storage";
const trainingPath = `${repoRoot}/docs/AI_SSD_TRAINING_CASE_PLAN.xlsx`;
const remainingPath = `${repoRoot}/docs/AI_SSD_REMAINING_CASE_PLAN.xlsx`;
const outputDir = `${repoRoot}/outputs/ai_ssd_all_case_plan_20260806`;
const outputPath = `${outputDir}/AI_SSD_ALL_CASE_PLAN.xlsx`;

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
  if (headers.length !== 8 || headers[0] !== "类别") throw new Error(`${name} does not have the expected eight-column header`);
  sheet.showGridLines = false;
  sheet.getRange(`A1:H${endRow}`).values = values;
  setTitle(sheet, "A1:H1", values[0][0]);
  setNote(sheet, "A2:H2", values[1][0]);
  setNote(sheet, "A3:H3", values[2][0]);
  sheet.getRange("B6").formulas = [[`=COUNTA('${name}'!$B$8:$B$${endRow})`]];
  sheet.getRange("A5:H5").format = { fill: colors.blueLight, font: { bold: true, color: colors.navy }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
  sheet.getRange("A6:H6").format = { fill: colors.white, font: { bold: true, color: colors.blue, size: 11 }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
  sheet.getRange("A5:H6").format.borders = { preset: "outside", style: "thin", color: colors.border };
  formatHeader(sheet, "A7:H7");
  formatBody(sheet, `A8:H${endRow}`);
  for (let row = 8; row <= endRow; row++) {
    const caseId = values[row - 1]?.[1];
    sheet.getRange(`A${row}:H${row}`).format.fill = selectedCases.has(caseId) ? colors.green : colors.white;
  }
  sheet.getRange(`B8:B${endRow}`).format = { font: { bold: true, color: colors.blue }, horizontalAlignment: "center", verticalAlignment: "top" };
  sheet.getRange(`A8:H${endRow}`).format.rowHeight = 150;
  sheet.tables.add(`A7:H${endRow}`, true, `${name.replaceAll(" ", "_")}ExecutionTable`);
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
}

const trainingWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(trainingPath));
const remainingWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(remainingPath));
const workbook = Workbook.create();
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
  const values = sourceSheet.getUsedRange().values;
  const sheet = workbook.worksheets.add(name);
  applyCommonLayout(sheet, name, values);
  const preview = await workbook.render({ sheetName: name, range: `A1:H${values.length}`, scale: 1, format: "png" });
  await fs.mkdir(outputDir, { recursive: true });
  await fs.writeFile(`${outputDir}/${name.replaceAll(" ", "_")}_preview.png`, new Uint8Array(await preview.arrayBuffer()));
}

const sheetCheck = await workbook.inspect({ kind: "sheet", include: "id,name" });
console.log(sheetCheck.ndjson);
const tableCheck = await workbook.inspect({ kind: "table", sheetId: "Training Case表", range: "A1:H23", include: "values,formulas", tableMaxRows: 24, tableMaxCols: 10, tableMaxCellChars: 220 });
console.log(tableCheck.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "all case plan formula error scan" });
console.log(errors.ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await fs.mkdir(outputDir, { recursive: true });
await output.save(outputPath);
console.log(`saved ${outputPath}`);
console.log(`sheet_count=${sourceSheets.length}`);
console.log(`selected_case_count=${selectedCases.size}`);
