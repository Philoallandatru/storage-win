import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
const input = "C:/Users/Administrator/Documents/Code/repos/storage/outputs/ai_pc_consumer_ssd_case_matrix_20260803/AI_PC_CONSUMER_SSD_TEST_CASE_MATRIX.xlsx";
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(input));
const names = ["目录与说明", "核心Case矩阵", "简化Case清单", "可选Case清单", "配置基线", "执行方式边界", "监控与判定"];
for (const name of names) {
  const s = wb.worksheets.getItem(name);
  const used = s.getUsedRange();
  console.log(JSON.stringify({name, address: used?.address, values: used?.values?.slice(0, 7)}, null, 2));
}
