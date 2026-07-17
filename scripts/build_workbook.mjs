#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sourcePath = path.join(root, "data", "processed", "company-master.json");
const outputDir = path.join(root, "deliverables");
const workDir = path.join(root, "work");
const outputPath = path.join(outputDir, "tape-masking-film-customer-master.xlsx");

const source = JSON.parse(await fs.readFile(sourcePath, "utf8"));
const companies = source.companies;
const workbook = Workbook.create();
const sheet = workbook.worksheets.add("客户总表");
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(6);
sheet.freezePanes.freezeColumns(5);

const headers = [
  "研究状态", "市场优先级", "品类", "公司ID", "公司名称", "国家/地区",
  "首选邮箱", "邮箱可用状态", "首选电话", "官网", "联系完整度", "跟进状态", "负责人",
  "API地址", "官网核验地址", "经营范围", "匹配贸易次数", "贸易总次数", "匹配占比",
  "最近贸易日期", "API邮箱", "官网补充邮箱", "API电话", "官网补充电话", "WhatsApp",
  "社交媒体", "官网联系渠道", "API邮箱验证详情", "产品名称", "产品标签",
  "产品描述/命中证据", "产品别名", "上游词", "下游词", "搜索词", "搜索原始来源",
  "API联系方式来源", "官网核验来源", "官网核验说明", "最后核验日期",
];

const colLetter = (index) => {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    value -= 1;
    result = String.fromCharCode(65 + (value % 26)) + result;
    value = Math.floor(value / 26);
  }
  return result;
};

const lastCol = colLetter(headers.length - 1);
const firstDataRow = 7;
const lastDataRow = firstDataRow + companies.length - 1;

sheet.mergeCells("A1:N1");
sheet.getRange("A1").values = [["Tape & Masking Film 全球客户总表"]];
sheet.mergeCells("A2:N2");
sheet.getRange("A2").values = [[
  "一行一家公司 · 全球覆盖、欧美优先 · 来源：跨境魔方 OpenAPI + 官方网站核验 · 更新：2026-07-17",
]];

const cards = [
  ["A3:D3", "公司总数", "E3:H3", `=COUNTA(E${firstDataRow}:E${lastDataRow})`],
  ["I3:L3", "欧美优先", "M3:P3", `=COUNTIF(B${firstDataRow}:B${lastDataRow},"\u9ad8-\u6b27\u7f8e")`],
  ["Q3:T3", "已验证邮箱", "U3:X3", `=COUNTIF(H${firstDataRow}:H${lastDataRow},"*\u5df2*\u9a8c*")`],
  ["Y3:AB3", "平均联系完整度", "AC3:AF3", `=AVERAGE(K${firstDataRow}:K${lastDataRow})`],
];
for (const [labelRange, label, valueRange, formula] of cards) {
  sheet.mergeCells(labelRange);
  sheet.mergeCells(valueRange);
  sheet.getRange(labelRange.split(":")[0]).values = [[label]];
  sheet.getRange(valueRange.split(":")[0]).formulas = [[formula]];
  sheet.getRange(labelRange).format.fill = "#E8EEF8";
  sheet.getRange(valueRange).format.fill = "#DDEBF7";
}
sheet.mergeCells("AG3:AN3");
sheet.getRange("AG3").values = [["OpenAPI 累计费用：¥49.50（前期上限 ¥50）"]];
sheet.getRange("AG3:AN3").format.fill = "#FFF2CC";

sheet.mergeCells(`A4:${lastCol}4`);
sheet.getRange("A4").values = [[
  "使用：先按“市场优先级”和“邮箱可用状态”筛选；“跟进状态/负责人”为人工维护列。邮箱状态 0=未检测，1=有效，2=无效，3=不确定。完整原始数据见 data/raw/。",
]];

sheet.getRange(`A6:${lastCol}6`).values = [headers];

const values = companies.map((company) => {
  const latest = company.latest_trade_date_ms
    ? new Date(Number(company.latest_trade_date_ms))
    : null;
  return [
    company.research_status || "",
    company.market_priority || "",
    company.categories || "",
    String(company.company_id),
    company.company_name || "",
    company.country_code || "",
    null,
    null,
    null,
    company.websites || "",
    null,
    "待联系",
    "",
    company.address || "",
    company.website_address || "",
    company.business_scope || "",
    Number(company.trade_match_total || 0),
    Number(company.trade_total || 0),
    Number(company.trade_match_percent || 0) / 100,
    latest,
    company.emails || "",
    company.website_emails || "",
    company.phones || "",
    company.website_phones || "",
    company.whatsapp || "",
    company.socials || "",
    company.website_contact_method || "",
    company.email_statuses || "",
    company.product_names || "",
    company.product_tags || "",
    company.product_descriptions || "",
    company.product_aliases || "",
    company.product_superordinate || "",
    company.product_downstream || "",
    company.search_terms || "",
    company.search_sources || "",
    company.contact_source || "",
    company.website_research_source || "",
    company.website_research_notes || "",
    new Date("2026-07-17T00:00:00Z"),
  ];
});
sheet.getRange(`A${firstDataRow}:${lastCol}${lastDataRow}`).values = values;

for (let row = firstDataRow; row <= lastDataRow; row += 1) {
  sheet.getRange(`G${row}`).formulas = [[`=IF(V${row}<>"",V${row},U${row})`]];
  sheet.getRange(`H${row}`).formulas = [[
    `=IF(V${row}<>"","官网已验证",IF(ISNUMBER(SEARCH(":1",AB${row})),"API已验证","未验证"))`,
  ]];
  sheet.getRange(`I${row}`).formulas = [[`=IF(X${row}<>"",X${row},W${row})`]];
  sheet.getRange(`K${row}`).formulas = [[
    `=ROUND((IF(G${row}<>"",40,0)+IF(I${row}<>"",25,0)+IF(J${row}<>"",20,0)+IF(Z${row}<>"",15,0))/100,2)`,
  ]];
}

const table = sheet.tables.add(`A6:${lastCol}${lastDataRow}`, true, "CustomerMasterTable");
table.style = "TableStyleMedium2";
table.showFilterButton = true;

sheet.getRange(`L${firstDataRow}:L${lastDataRow}`).dataValidation = {
  rule: { type: "list", values: ["待联系", "已联系", "已回复", "有意向", "无意向", "暂停"] },
};

sheet.getRange(`B${firstDataRow}:B${lastDataRow}`).conditionalFormats.add("containsText", {
  text: "高-欧美",
  format: { fill: "#D9EAD3", font: { bold: true, color: "#274E13" } },
});
sheet.getRange(`H${firstDataRow}:H${lastDataRow}`).conditionalFormats.add("containsText", {
  text: "已验证",
  format: { fill: "#D9EAD3", font: { color: "#274E13" } },
});
sheet.getRange(`H${firstDataRow}:H${lastDataRow}`).conditionalFormats.add("containsText", {
  text: "未验证",
  format: { fill: "#FFF2CC", font: { color: "#7F6000" } },
});
sheet.getRange(`K${firstDataRow}:K${lastDataRow}`).conditionalFormats.add("colorScale", {
  colors: ["#F4CCCC", "#FFF2CC", "#D9EAD3"],
  thresholds: ["min", "50%", "max"],
});

sheet.getRange(`A1:${lastCol}1`).format = {
  fill: "#17365D",
  font: { bold: true, color: "#FFFFFF", size: 18 },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
sheet.getRange(`A2:${lastCol}2`).format = {
  fill: "#DCE6F1",
  font: { color: "#1F1F1F", size: 10 },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
sheet.getRange(`A3:${lastCol}3`).format.font = { bold: true, color: "#17365D" };
sheet.getRange(`A3:${lastCol}3`).format.horizontalAlignment = "center";
sheet.getRange(`A4:${lastCol}4`).format = {
  fill: "#F2F2F2",
  font: { color: "#595959", italic: true, size: 9 },
  horizontalAlignment: "left",
  verticalAlignment: "center",
  wrapText: true,
};
sheet.getRange(`A6:${lastCol}6`).format = {
  fill: "#4472C4",
  font: { bold: true, color: "#FFFFFF", size: 10 },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
sheet.getRange(`A${firstDataRow}:${lastCol}${lastDataRow}`).format = {
  font: { size: 9, color: "#1F1F1F" },
  verticalAlignment: "top",
};
sheet.getRange(`A${firstDataRow}:${lastCol}${lastDataRow}`).format.wrapText = true;
sheet.getRange(`D${firstDataRow}:D${lastDataRow}`).format.numberFormat = "@";
sheet.getRange(`Q${firstDataRow}:R${lastDataRow}`).format.numberFormat = "#,##0";
sheet.getRange(`S${firstDataRow}:S${lastDataRow}`).format.numberFormat = "0.0%";
sheet.getRange(`T${firstDataRow}:T${lastDataRow}`).format.numberFormat = "yyyy-mm-dd";
sheet.getRange(`K${firstDataRow}:K${lastDataRow}`).format.numberFormat = "0%";
sheet.getRange(`AN${firstDataRow}:AN${lastDataRow}`).format.numberFormat = "yyyy-mm-dd";

const widths = [
  26, 14, 18, 12, 34, 11, 32, 15, 24, 28, 13, 12, 12, 30, 30, 38, 13, 13, 12, 14,
  32, 35, 24, 24, 22, 32, 25, 38, 30, 28, 55, 35, 28, 28, 20, 32, 34, 42, 50, 14,
];
widths.forEach((width, index) => {
  sheet.getRange(`${colLetter(index)}:${colLetter(index)}`).format.columnWidth = width;
});
sheet.getRange("1:1").format.rowHeight = 32;
sheet.getRange("2:2").format.rowHeight = 24;
sheet.getRange("3:3").format.rowHeight = 27;
sheet.getRange("4:4").format.rowHeight = 32;
sheet.getRange("6:6").format.rowHeight = 36;
sheet.getRange(`${firstDataRow}:${lastDataRow}`).format.rowHeight = 44;

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(workDir, { recursive: true });

const check = await workbook.inspect({
  kind: "table",
  range: `客户总表!A1:N12`,
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 14,
  maxChars: 7000,
});
console.log(check.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 200 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const previewA = await workbook.render({
  sheetName: "客户总表",
  range: `A1:N18`,
  scale: 1.4,
  format: "png",
});
await fs.writeFile(
  path.join(workDir, "customer-master-preview-left.png"),
  new Uint8Array(await previewA.arrayBuffer()),
);
const previewB = await workbook.render({
  sheetName: "客户总表",
  range: `O1:${lastCol}12`,
  scale: 1.1,
  format: "png",
});
await fs.writeFile(
  path.join(workDir, "customer-master-preview-right.png"),
  new Uint8Array(await previewB.arrayBuffer()),
);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });
console.log(`Exported ${outputPath}`);
