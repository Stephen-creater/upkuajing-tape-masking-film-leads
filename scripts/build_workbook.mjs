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
  "最近贸易日期", "API邮箱", "官网补充邮箱", "API电话", "官网补充电话", "电话验证详情", "WhatsApp",
  "社交媒体", "官网联系渠道", "邮箱验证详情", "产品名称", "产品标签",
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

const splitValues = (value) => String(value || "").split(";").map((item) => item.trim()).filter(Boolean);
const emailStatusMap = (company) => new Map(splitValues(company.email_statuses).map((item) => {
  const separator = item.lastIndexOf(":");
  return separator > 0 ? [item.slice(0, separator).toLowerCase(), Number(item.slice(separator + 1))] : [item.toLowerCase(), 0];
}));
const preferredEmail = (company) => {
  const website = splitValues(company.website_emails);
  const api = splitValues(company.emails);
  const statuses = emailStatusMap(company);
  return [...website, ...api].find((email) => statuses.get(email.toLowerCase()) === 1) || website[0] || api[0] || "";
};
const preferredPhone = (company) => {
  const website = splitValues(company.website_phones);
  const api = splitValues(company.phones);
  const valid = new Set(splitValues(company.phone_statuses).flatMap((item) => {
    const marker = item.indexOf(":状态1/");
    return marker > 0 ? [item.slice(0, marker)] : [];
  }));
  return [...website, ...api].find((phone) => valid.has(phone)) || website[0] || api[0] || "";
};

sheet.mergeCells("A1:N1");
sheet.getRange("A1").values = [["Tape & Masking Film 全球客户总表"]];
sheet.mergeCells("A2:N2");
sheet.getRange("A2").values = [[
  "一行一家公司 · 全球覆盖、欧美优先 · 来源：跨境魔方 OpenAPI + 官方网站核验 · 更新：2026-07-17",
]];

const cards = [
  ["A3:D3", "公司总数", "E3:H3", `=COUNTA(E${firstDataRow}:E${lastDataRow})`],
  ["I3:L3", "欧美优先", "M3:P3", `=COUNTIF(B${firstDataRow}:B${lastDataRow},"\u9ad8-\u6b27\u7f8e")`],
  ["Q3:T3", "有效邮箱公司", "U3:X3", `=COUNTIF(H${firstDataRow}:H${lastDataRow},"已验证有效")`],
  ["Y3:AB3", "有效电话公司", "AC3:AF3", `=COUNTIF(Y${firstDataRow}:Y${lastDataRow},"*状态1*")`],
];
for (const [labelRange, label, valueRange, formula] of cards) {
  sheet.mergeCells(labelRange);
  sheet.mergeCells(valueRange);
  sheet.getRange(labelRange.split(":")[0]).values = [[label]];
  sheet.getRange(valueRange.split(":")[0]).formulas = [[formula]];
  sheet.getRange(labelRange).format.fill = "#E8EEF8";
  sheet.getRange(valueRange).format.fill = "#DDEBF7";
}
sheet.mergeCells("AG3:AO3");
sheet.getRange("AG3").values = [["OpenAPI 累计费用：¥81.60 / 上限 ¥100.00"]];
sheet.getRange("AG3:AO3").format.fill = "#FFF2CC";

sheet.mergeCells(`A4:${lastCol}4`);
sheet.getRange("A4").values = [[
  "使用：先筛选“市场优先级”和“邮箱可用状态”。邮箱 1=有效、2=无效、3=不确定、0=接口已调用但未能检测；电话详情为 状态/类型/WhatsApp。原始证据见 data/raw/。",
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
    preferredEmail(company),
    null,
    preferredPhone(company),
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
    company.phone_statuses || "",
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
  sheet.getRange(`H${row}`).formulas = [[
    `=IF(ISNUMBER(SEARCH(":1",AC${row})),"已验证有效",IF(ISNUMBER(SEARCH(":3",AC${row})),"验证不确定",IF(ISNUMBER(SEARCH(":0",AC${row})),"接口未能检测",IF(ISNUMBER(SEARCH(":2",AC${row})),"判定无效",IF(V${row}<>"","官网已确认-未验证","无邮箱")))))`,
  ]];
  sheet.getRange(`K${row}`).formulas = [[
    `=ROUND((IF(H${row}="已验证有效",40,IF(V${row}<>"",20,0))+IF(ISNUMBER(SEARCH("状态1",Y${row})),25,0)+IF(J${row}<>"",20,0)+IF(AA${row}<>"",15,0))/100,2)`,
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
  text: "已验证有效",
  format: { fill: "#D9EAD3", font: { color: "#274E13" } },
});
sheet.getRange(`H${firstDataRow}:H${lastDataRow}`).conditionalFormats.add("containsText", {
  text: "验证不确定",
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
sheet.getRange(`AO${firstDataRow}:AO${lastDataRow}`).format.numberFormat = "yyyy-mm-dd";

const widths = [
  26, 14, 18, 12, 34, 11, 32, 15, 24, 28, 13, 12, 12, 30, 30, 38, 13, 13, 12, 14,
  32, 35, 24, 24, 42, 22, 32, 25, 38, 30, 28, 55, 35, 28, 28, 20, 32, 34, 42, 50, 14,
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

const costSheet = workbook.worksheets.add("成本与流程");
costSheet.showGridLines = false;
costSheet.mergeCells("A1:F1");
costSheet.getRange("A1").values = [["有效联系方式成本与流程结论"]];
costSheet.getRange("A1:F1").format = {
  fill: "#17365D", font: { bold: true, color: "#FFFFFF", size: 16 },
  horizontalAlignment: "center", verticalAlignment: "center",
};
costSheet.getRange("A3:C3").values = [["指标", "结果", "严格口径"]];
costSheet.getRange("A4:C12").values = [
  ["公司总数", 35, "一行一家公司ID"],
  ["有已验证有效邮箱的公司", 26, "邮箱状态=1；官网存在但投递性不确定不算"],
  ["有已验证有效电话的公司", 28, "电话状态=1"],
  ["至少一种有效联系方式", 35, "有效邮箱或有效电话"],
  ["已验证有效邮箱地址", 31, "所有公司行内状态=1的邮箱地址数"],
  ["OpenAPI累计费用", 81.60, "人民币；已审计本项目全部调用"],
  ["每家有效邮箱公司成本", 3.14, "81.60 ÷ 26；主指标"],
  ["每家有效联系方式成本", 2.33, "81.60 ÷ 35；邮箱或电话"],
  ["预算剩余", 18.40, "100.00 - 81.60"],
];
costSheet.getRange("A14:C14").values = [["费用构成", "金额（元）", "说明"]];
costSheet.getRange("A15:C20").values = [
  ["海关客户搜索", 7.50, "产品买家搜索"],
  ["海关公司联系方式", 42.00, "早期35家公司及重复调用"],
  ["人物搜索", 19.50, "混合搜索1页 + 逐公司12页"],
  ["人物联系方式", 3.00, "人工审查后仅购买6人"],
  ["邮箱验证", 3.00, "API、官网及人物新增邮箱"],
  ["电话验证", 6.60, "主批58个 + 权威来源新增8个"],
];
costSheet.getRange("A22:C22").values = [["流程改进", "优先级", "执行规则"]];
costSheet.getRange("A23:C27").values = [
  ["先做法人实体去重", "P0", "公司名称+官网域名+国家归一化；重复实体复用已验证联系方式"],
  ["所有来源进入统一验证队列", "P0", "API、官网、人物邮箱增量入库后立即验证；禁止只验API字段"],
  ["人物搜索按公司逐个执行", "P0", "人工确认公司精确匹配后，每家公司最多购买1位高相关人员"],
  ["状态3/0不盲目重试", "P1", "先查官网或换人物；避免反垃圾拦截导致重复付费"],
  ["发送后用真实退信闭环", "P0", "小批量投递、记录硬退信、永久抑制无效地址；验证状态1仍非送达保证"],
];
for (const range of ["A3:C3", "A14:C14", "A22:C22"]) {
  costSheet.getRange(range).format = { fill: "#4472C4", font: { bold: true, color: "#FFFFFF" } };
}
costSheet.getRange("A3:C27").format.wrapText = true;
costSheet.getRange("B9:B12").format.numberFormat = "¥0.00";
costSheet.getRange("B15:B20").format.numberFormat = "¥0.00";
costSheet.getRange("A:A").format.columnWidth = 30;
costSheet.getRange("B:B").format.columnWidth = 16;
costSheet.getRange("C:C").format.columnWidth = 66;
costSheet.freezePanes.freezeRows(3);

const guideSheet = workbook.worksheets.add("字段说明");
guideSheet.showGridLines = false;
guideSheet.mergeCells("A1:D1");
guideSheet.getRange("A1").values = [["客户总表字段说明（按主表顺序）"]];
guideSheet.getRange("A1:D1").format = {
  fill: "#17365D", font: { bold: true, color: "#FFFFFF", size: 16 }, horizontalAlignment: "center",
};
guideSheet.getRange("A3:D3").values = [["字段", "人话解释", "来源/计算", "是否关键"]];
const fieldHelp = {
  "研究状态": "这家公司目前调研到哪一步", "市场优先级": "欧美优先或全球常规", "品类": "命中 tape 或 masking film",
  "公司ID": "跨境魔方中的公司唯一编号", "公司名称": "公司名称；一行只放一家", "国家/地区": "公司国家二字码",
  "首选邮箱": "优先取官网补充邮箱，否则取API/人物邮箱", "邮箱可用状态": "有效、无效、不确定或接口未能检测",
  "首选电话": "优先取官网电话，否则取API电话", "官网": "公司网站", "联系完整度": "按有效邮箱、有效电话、官网、社媒加权",
  "跟进状态": "人工维护的销售进度", "负责人": "人工填写跟进人", "API地址": "跨境魔方返回的公司地址",
  "官网核验地址": "官网或权威来源确认的地址", "经营范围": "公司经营或产品范围", "匹配贸易次数": "与本品类匹配的贸易记录数",
  "贸易总次数": "该公司全部贸易记录数", "匹配占比": "匹配贸易次数占总贸易次数", "最近贸易日期": "最近一笔相关贸易日期",
  "API邮箱": "海关公司API和审查后人物API获取的邮箱", "官网补充邮箱": "官网、政府或权威目录补充的邮箱",
  "API电话": "跨境魔方返回的电话", "官网补充电话": "官网、政府或权威目录补充的电话", "电话验证详情": "每个号码的有效状态、类型及WhatsApp状态",
  "WhatsApp": "明确识别的WhatsApp号码", "社交媒体": "LinkedIn等链接", "官网联系渠道": "官网表单、客服入口等",
  "邮箱验证详情": "每个邮箱及状态码；1有效、2无效、3不确定、0未能检测", "产品名称": "API结构化产品名",
  "产品标签": "API提取的产品关键词", "产品描述/命中证据": "原始报关品名；用于证明为何列入", "产品别名": "API返回的近义词",
  "上游词": "API返回的上游关联词", "下游词": "API返回的下游关联词", "搜索词": "找到该公司的查询词",
  "搜索原始来源": "对应原始搜索文件", "API联系方式来源": "联系方式来自哪个API", "官网核验来源": "核验网页或权威文件链接",
  "官网核验说明": "人工核验结论、人物职位和排除原因", "最后核验日期": "本行最后一次数据核验日期",
};
const keyFields = new Set(["品类", "公司名称", "国家/地区", "首选邮箱", "邮箱可用状态", "首选电话", "电话验证详情", "官网", "产品描述/命中证据", "跟进状态"]);
guideSheet.getRange(`A4:D${headers.length + 3}`).values = headers.map((header) => [
  header, fieldHelp[header] || "辅助追溯字段", "API、官网或公式", keyFields.has(header) ? "关键" : "辅助/追溯",
]);
guideSheet.getRange("A3:D3").format = { fill: "#4472C4", font: { bold: true, color: "#FFFFFF" } };
guideSheet.getRange(`A3:D${headers.length + 3}`).format.wrapText = true;
guideSheet.getRange("A:A").format.columnWidth = 24;
guideSheet.getRange("B:B").format.columnWidth = 56;
guideSheet.getRange("C:C").format.columnWidth = 24;
guideSheet.getRange("D:D").format.columnWidth = 16;
guideSheet.freezePanes.freezeRows(3);

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
