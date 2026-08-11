import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoRoot = "C:/Users/Administrator/Documents/Code/repos/storage";
const sourcePath = `${repoRoot}/docs/AI_SSD_TEST_PLAN.xlsx`;
const outputDir = `${repoRoot}/outputs/ai_ssd_training_case_plan_20260806`;
const outputPath = `${outputDir}/AI_SSD_TRAINING_CASE_PLAN.xlsx`;

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
  "AI-TRN-001",
  "AI-TRN-004",
  "AI-TRN-006",
  "AI-TRN-010",
  "AI-TRN-014",
  "AI-TRN-016",
]);

const caseMeta = {
  "AI-TRN-001": {
    purpose: "验证大文件训练数据的连续供给能力。",
    steps: "1. 准备 UNet3D/A100 代表性 NPZ 数据，工作盘与结果盘分离。\n2. 设置 workers=1/2/4，并先完成短时预热。\n3. 使用训练 Case Runner 重复运行 3 次，记录吞吐、等待时间和实际读写。\n4. 对齐训练 AU、PhysicalDisk 吞吐、P99、队列和温度。",
    duration: "约 45–60 分钟",
    standard: "PASS：3 次运行完成；AU≥90%；吞吐 CV≤5%；PhysicalDisk 实际读字节与逻辑读量可解释；无数据错误或持续退化。",
  },
  "AI-TRN-002": {
    purpose: "验证 compute gap 缩短后训练数据供给是否仍然稳定。",
    steps: "1. 准备 UNet3D/H100 代表性 NPZ 数据并固定数据规模。\n2. 设置 workers=1/2/4，缩短处理间隔，记录每轮供数等待。\n3. 使用训练 Case Runner 重复运行 3 次。\n4. 对齐 AU、吞吐、队列、P99 和温度，检查后半程是否退化。",
    duration: "约 45–60 分钟",
    standard: "PASS：AU≥90%；吞吐无持续下降；队列不持续增长；P99 处于产品目标内；无数据错误。",
  },
  "AI-TRN-003": {
    purpose: "验证大规模 NPZ 数据长时间连续读取的稳定性。",
    steps: "1. 准备 UNet3D/B200 数据集；正式规模按容量条件执行，缩小规模需单独标注。\n2. 设置 workers=1/2/4/8，固定数据顺序和结果目录。\n3. 使用训练 Case Runner 运行 3 次长时测试。\n4. 记录 AU、samples/s、GiB/s、温度、队列和后半程漂移。",
    duration: "约 60–90 分钟",
    standard: "PASS：AU≥90%；samples/s 无持续下降；后半程吞吐下降不超过 10%；温度和队列无异常；数据完整。",
  },
  "AI-TRN-004": {
    purpose: "验证百万级 JPEG 小文件访问下的元数据和 IOPS 能力。",
    steps: "1. 准备 RetinaNet/B200 JPEG 小文件集，保持文件数量和目录层级固定。\n2. 设置 workers=1/4/8/16，执行 stat、open、read、close 密集访问。\n3. 使用训练 Case Runner 重复运行 3 次。\n4. 记录 files/s、IOPS、P99、CPU 和 PhysicalDisk 实际读写。",
    duration: "约 45–60 分钟",
    standard: "PASS：AU≥85%；files/s 达到目标；P99 无异常尖峰；IOPS 和实际读写可解释；无缺文件或数据错误。",
  },
  "AI-TRN-005": {
    purpose: "验证不同 batch 和处理节奏下 JPEG 小文件供给的稳定性。",
    steps: "1. 准备 RetinaNet/MI355 JPEG 小文件集。\n2. 固定 workers=1/4/8/16，分别运行代表性 batch 和处理间隔。\n3. 使用训练 Case Runner 对每个 batch 重复 3 次。\n4. 对比 files/s、P99、等待时间和 CPU 开销。",
    duration: "约 45–60 分钟",
    standard: "PASS：AU≥85%；不同 batch 结果可重复；files/s 无持续下降；P99 在目标内；无缺文件。",
  },
  "AI-TRN-006": {
    purpose: "验证中小对象随机访问和 shuffle 场景下的供数能力。",
    steps: "1. 准备 CosmoFlow/A100 TFRecord 数据并固定随机种子。\n2. 设置 workers=1/2/4，按固定比例进行随机对象和样本访问。\n3. 使用训练 Case Runner 重复运行 3 次。\n4. 记录 AU、IOPS、P99、队列和随机读实际字节。",
    duration: "约 60–90 分钟",
    standard: "PASS：AU≥70%；IOPS 和 P99 达到目标；shuffle 阶段无明显供数空洞；队列和温度稳定；数据完整。",
  },
  "AI-TRN-007": {
    purpose: "验证更高请求速率下中小对象随机读取的尾延迟。",
    steps: "1. 准备 CosmoFlow/H100 TFRecord 数据并固定随机种子。\n2. 设置 workers=1/2/4/8，逐级提高请求速率。\n3. 使用训练 Case Runner 重复运行 3 次。\n4. 记录 AU、P99、队列、IOPS 和后半程性能。",
    duration: "约 60–90 分钟",
    standard: "PASS：AU≥70%；P99 达到目标；请求速率提升后无持续错误或供数中断；队列可解释。",
  },
  "AI-TRN-008": {
    purpose: "验证 TFRecord 文件内多 sample 读取的供给效率。",
    steps: "1. 准备 ResNet50/A100 TFRecord 数据并固定 batch。\n2. 设置 workers=1/2/4，按固定样本顺序读取文件内记录。\n3. 使用训练 Case Runner 重复运行 3 次。\n4. 记录 AU、samples/s、吞吐、P99 和 PhysicalDisk 实际读写。",
    duration: "约 45–60 分钟",
    standard: "PASS：AU≥90%；samples/s 达到目标；batch 结果稳定；P99 和队列无异常；记录完整。",
  },
  "AI-TRN-009": {
    purpose: "验证更高 TFRecord 请求速率下的持续吞吐。",
    steps: "1. 准备 ResNet50/H100 TFRecord 数据。\n2. 设置 workers=1/2/4/8，逐级提高数据请求速率。\n3. 使用训练 Case Runner 重复运行 3 次。\n4. 记录 AU、throughput、P99、队列和温度。",
    duration: "约 60–90 分钟",
    standard: "PASS：AU≥90%；throughput 无持续下降；请求速率提升后无供数中断；P99 和温度在目标内。",
  },
  "AI-TRN-010": {
    purpose: "验证 Parquet row-group 和列裁剪读取的设备表现。",
    steps: "1. 准备 DLRM/B200 Parquet 数据并固定 row-group、列集合和随机种子。\n2. 对照 prefetch=0/2/4，读取固定列和 row-group。\n3. 使用训练 Case Runner 重复运行 3 次。\n4. 记录 AU、row-groups/s、读取带宽、P99、CPU 和实际读写。",
    duration: "约 60–90 分钟",
    standard: "PASS：AU≥70%；row-groups/s 达到目标；列裁剪没有异常读放大；CPU 不成为主瓶颈；数据完整。",
  },
  "AI-TRN-011": {
    purpose: "验证 Parquet 并行读取的带宽和主机开销。",
    steps: "1. 准备 DLRM/MI355 Parquet 数据并固定列集合。\n2. 设置 read_threads=1/4/8/16。\n3. 使用训练 Case Runner 重复运行 3 次。\n4. 记录 AU、read BW、CPU、P99、队列和实际读写。",
    duration: "约 60–90 分钟",
    standard: "PASS：AU 达到目标；read BW 随线程增加可解释；CPU、队列和 P99 无异常饱和；无数据错误。",
  },
  "AI-TRN-012": {
    purpose: "验证 Flux 大 Parquet 对象的持续读取带宽。",
    steps: "1. 准备 Flux/B200 Parquet 大对象数据，正式规模按容量条件执行。\n2. 设置 threads=4/8/16，固定读取顺序。\n3. 使用训练 Case Runner 运行 3 次长时测试。\n4. 记录 AU、GiB/s、P99、温度、队列和空间余量。",
    duration: "约 90–120 分钟",
    standard: "PASS：AU≥90%；GiB/s 达到目标；吞吐无持续下降；温度、队列和空间余量在安全范围；数据完整。",
  },
  "AI-TRN-013": {
    purpose: "验证长 compute gap 后突发读取的恢复能力。",
    steps: "1. 准备 Flux/MI355 Parquet 数据并设置 batch=72。\n2. 设置 threads=4/8/16，模拟处理间隔后的突发读取。\n3. 使用训练 Case Runner 重复运行 3 次。\n4. 记录 AU、burst latency、突发吞吐和恢复时间。",
    duration: "约 90–120 分钟",
    standard: "PASS：AU≥90%；突发读取能在目标窗口内恢复；burst latency 无持续恶化；无供数中断或数据错误。",
  },
  "AI-TRN-014": {
    purpose: "验证并发任务增加后的最大合格供数能力。",
    steps: "1. 准备 UNet3D/RetinaNet 代表性数据并建立单任务基线。\n2. 按 workers=1/2/4/8/16 逐级增加并发。\n3. 使用训练 Case Runner 运行并发 sweep。\n4. 以 AU、speedup、吞吐、P99 和队列确定最大合格点。",
    duration: "约 90–120 分钟",
    standard: "PASS：输出最大合格并发；AU 达到对应门槛；speedup 可解释；超过拐点后能明确识别饱和而非无效错误。",
  },
  "AI-TRN-015": {
    purpose: "验证读取线程增加后的 SSD、CPU 和队列饱和拐点。",
    steps: "1. 准备固定训练数据并建立 read_threads=1 基线。\n2. 按 1/2/4/8/16/32 逐级增加读取线程。\n3. 使用训练 Case Runner 运行线程 sweep。\n4. 对比 throughput、CPU、队列、P99 和温度，标记拐点。",
    duration: "约 60–90 分钟",
    standard: "PASS：输出可复现的饱和拐点；吞吐 CV≤5%；CPU/队列瓶颈可归因；无持续错误或温度异常。",
  },
  "AI-TRN-016": {
    purpose: "验证 warm、cold 和直接访问路径对训练结果的影响。",
    steps: "1. 准备同一数据集和固定训练配置。\n2. 分别运行 warm、cold 和 direct/path 对照，记录缓存状态。\n3. 使用训练 Case Runner 对每种路径重复运行 3 次。\n4. 对齐 AU、PhysicalDisk 实际读字节、吞吐和 P99，识别缓存污染。",
    duration: "约 45–60 分钟",
    standard: "PASS：三种路径结果独立可复现；cold/direct 的实际读字节与逻辑遍历量一致；AU 差异可解释；无缓存污染误判。",
  },
};

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
const sourceValues = sourceWorkbook.worksheets.getItem("Case·BASE+Training").getUsedRange().values;
const sourceRows = sourceValues.filter((row) => typeof row?.[0] === "string" && row[0].startsWith("AI-TRN-"));
if (sourceRows.length !== 16) throw new Error(`expected 16 Training cases, got ${sourceRows.length}`);

const rows = sourceRows.map((sourceRow) => {
  const caseId = sourceRow[0];
  const meta = caseMeta[caseId];
  if (!meta) throw new Error(`missing metadata for ${caseId}`);
  return [
    "训练数据供给",
    caseId,
    "Python Training Case Runner + Windows PhysicalDisk 监控 + 结果校验",
    meta.purpose,
    meta.steps,
    meta.duration,
    `python tools/ai_ssd_training_case_runner.py --case ${caseId} --data-dir <DUT_DATA> --result-dir <RESULTS> --duration-sec 300 --repeat 3`,
    meta.standard,
  ];
});

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Training Case表");
sheet.showGridLines = false;
setTitle(sheet, "A1:H1", "AI SSD Training Case 执行表");
setNote(sheet, "A2:H2", "来源：docs/AI_SSD_TEST_PLAN.xlsx 的 16 个 Training Case；表格字段仅保留类别、Case ID、测试工具、测试目的、测试步骤、测试时长、测试命令、测试标准。", colors.pale);
setNote(sheet, "A3:H3", "精选首轮 Case：AI-TRN-001、004、006、010、014、016；精选理由见 docs/AI_SSD_TRAINING_CASE_SELECTION.md。", colors.pale);
sheet.getRange("A5:H5").values = [["Training Case 数", null, "精选 Case 数", null, "步骤格式", "脚本入口", "执行口径", "结果证据"]];
sheet.getRange("A6:H6").values = [[null, null, null, 6, "1. 2. 3. 4.", "ai_ssd_training_case_runner.py", "含预热、重复和监控", "AU + PhysicalDisk + P99"]];
sheet.getRange("B6").formulas = [["=COUNTA('Training Case表'!$B$8:$B$23)"]];
sheet.getRange("A5:H5").format = { fill: colors.blueLight, font: { bold: true, color: colors.navy }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
sheet.getRange("A6:H6").format = { fill: colors.white, font: { bold: true, color: colors.blue, size: 11 }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
sheet.getRange("A5:H6").format.borders = { preset: "outside", style: "thin", color: colors.border };
sheet.getRange("A7:H7").values = [["类别", "Case ID", "测试工具", "测试目的", "测试步骤", "测试时长", "测试命令", "测试标准"]];
formatHeader(sheet, "A7:H7");
sheet.getRange(`A8:H${7 + rows.length}`).values = rows;
formatBody(sheet, `A8:H${7 + rows.length}`);
for (let i = 0; i < sourceRows.length; i++) {
  const row = 8 + i;
  sheet.getRange(`A${row}:H${row}`).format.fill = selectedCases.has(sourceRows[i][0]) ? colors.green : colors.white;
}
sheet.getRange(`B8:B${7 + rows.length}`).format = { font: { bold: true, color: colors.blue }, horizontalAlignment: "center", verticalAlignment: "top" };
sheet.getRange(`A8:H${7 + rows.length}`).format.rowHeight = 150;
sheet.tables.add(`A7:H${7 + rows.length}`, true, "TrainingCaseExecutionTable");
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

await fs.mkdir(outputDir, { recursive: true });
const preview = await workbook.render({ sheetName: sheet.name, range: "A1:H23", scale: 1, format: "png" });
await fs.writeFile(`${outputDir}/training_case_table_preview.png`, new Uint8Array(await preview.arrayBuffer()));
const inspect = await workbook.inspect({ kind: "table", sheetId: sheet.name, range: "A1:H23", include: "values,formulas", tableMaxRows: 25, tableMaxCols: 10, tableMaxCellChars: 260 });
console.log(inspect.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "training case table formula error scan" });
console.log(errors.ndjson);
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`saved ${outputPath}`);
console.log(`training_case_count=${rows.length}`);
console.log(`selected_case_count=${selectedCases.size}`);
