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
const projectSpend = 361.60;
const projectCap = 500.00;

const source = JSON.parse(await fs.readFile(sourcePath, "utf8"));
const companies = source.companies;
const workbook = Workbook.create();
const sheet = workbook.worksheets.add("客户总表");
const costSheet = workbook.worksheets.add("成本与流程");
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(6);
sheet.freezePanes.freezeColumns(5);

const headers = [
  "研究状态", "市场优先级", "产品品类（中文）", "公司ID", "公司名称", "国家/地区（中文）",
  "首选邮箱", "邮箱可用状态", "首选电话", "官网", "联系完整度", "跟进状态", "负责人",
  "API地址（原文）", "官网核验地址（原文）", "经营范围（原文）", "匹配贸易次数", "贸易总次数", "匹配占比",
  "最近贸易日期", "API邮箱", "官网补充邮箱", "API电话", "官网补充电话", "电话验证详情", "WhatsApp",
  "社交媒体", "官网联系渠道", "邮箱验证详情", "产品名称", "产品标签",
  "报关品名/命中证据（原文）", "产品别名", "上游词", "下游词", "搜索词（中文）", "搜索原始来源",
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
const categoryTranslations = new Map([
  ["tape", "胶带"],
  ["masking film", "遮蔽膜"],
  ["胶带", "胶带"],
  ["遮蔽膜", "遮蔽膜"],
  ["刷子", "刷子"],
  ["猪毛刷", "猪毛刷"],
  ["羊毛刷", "羊毛刷"],
  ["pvc护角条", "PVC护角条"],
  ["塑料桶", "塑料桶"],
]);
const countryTranslations = new Map([
  ["AR", "阿根廷"], ["CA", "加拿大"], ["CL", "智利"], ["CO", "哥伦比亚"],
  ["CR", "哥斯达黎加"], ["EC", "厄瓜多尔"], ["GB", "英国"], ["IN", "印度"],
  ["JP", "日本"], ["KE", "肯尼亚"], ["KR", "韩国"], ["LK", "斯里兰卡"],
  ["MN", "蒙古"], ["MX", "墨西哥"], ["PA", "巴拿马"], ["PE", "秘鲁"],
  ["PK", "巴基斯坦"], ["PR", "波多黎各"], ["PY", "巴拉圭"], ["RU", "俄罗斯"],
  ["UA", "乌克兰"], ["US", "美国"], ["VN", "越南"],
]);
const productTermTranslations = new Map(Object.entries({
  "rubber tape": "橡胶胶带", "parts for led tv": "LED电视零部件", "tape-1 p1 duo": "TAPE-1 P1 DUO（胶带型号）",
  "brush": "刷子", "brushes": "刷子", "paint brush": "油漆刷", "paint brushes": "油漆刷",
  "hog bristle": "猪鬃", "hog bristles": "猪鬃", "natural hog bristles": "天然猪鬃",
  "boar brush": "猪鬃刷", "wool brush": "羊毛刷", "wool brushes": "羊毛刷",
  "pvc corner guard": "PVC护角条", "pvc corner protector": "PVC护角条",
  "pvc wall corner trim": "PVC墙角护条", "pvc corner bead": "PVC护角条",
  "plastic bucket": "塑料桶", "plastic buckets": "塑料桶", "plastic pail": "塑料桶", "plastic pails": "塑料桶",
  "pe masking film": "PE遮蔽膜", "masking film": "遮蔽膜", "pretaped masking film": "预贴胶带遮蔽膜",
  "masking tape": "遮蔽胶带", "plastic masking film": "塑料遮蔽膜", "pre-taped masking film": "预贴胶带遮蔽膜",
  "tape": "胶带", "masking": "遮蔽", "film": "薄膜", "plastic": "塑料", "rubber": "橡胶",
  "polyethylene": "聚乙烯", "poly ethylene": "聚乙烯", "packing material": "包装材料", "plastic drop cloth": "塑料防护布",
  "caution tape": "警示胶带", "packing tap": "包装胶带", "adhesive tape": "胶粘带", "textile insulation tape": "纺织绝缘胶带",
  "green tape": "绿色胶带", "yellow ribbon": "黄色带材", "self - adhesive": "自粘", "recycled": "再生材料",
  "accessories of plastics": "塑料配件", "industrial use": "工业用途", "paper": "纸", "arts": "工艺品",
  "water contact indicator tape": "遇水指示胶带", "mobile phone 5": "手机用途", "protection film": "保护膜",
  "clear film": "透明薄膜", "ps sheet": "PS片材", "aircraft use": "航空用途", "roll": "卷材", "rolls": "卷材",
  "hdpe": "高密度聚乙烯", "shrink wrapped": "收缩包装", "color label": "彩色标签", "mfg use": "制造用途",
  "film for printing": "印刷用薄膜", "print": "印刷", "fabric elastic": "弹性织物", "narrow woven": "窄幅织物",
  "led tv": "LED电视", "parts": "零部件", "assembly component": "装配部件", "rubber adhesive tape": "橡胶胶粘带",
  "led tv accessories": "LED电视配件", "tpe tape": "TPE胶带", "tv parts": "电视零部件", "rubber strip": "橡胶条",
  "self - sticking tape": "自粘胶带", "plastic tape": "塑料胶带", "duo tape": "双面胶带", "tesa tape": "德莎胶带",
  "pe protective film": "PE保护膜", "pe masking tape": "PE遮蔽胶带", "polyethylene masking film": "聚乙烯遮蔽膜",
  "industrial masking film": "工业遮蔽膜", "pe covering film": "PE覆盖膜", "pre - protection film": "预保护膜",
  "surface masking film": "表面遮蔽膜", "clear masking film": "透明遮蔽膜", "ps sheet protection film": "PS片材保护膜",
  "temporary masking film": "临时遮蔽膜", "painter's tape": "涂装遮蔽胶带", "protective film": "保护膜",
  "covering film": "覆盖膜", "surface protection film": "表面保护膜", "painter's tape film": "涂装遮蔽膜",
  "protective masking film": "保护遮蔽膜", "construction masking film": "施工遮蔽膜", "decorative masking film": "装饰遮蔽膜",
  "masking film with tape": "带胶带遮蔽膜", "pre - taped film for masking": "预贴胶带遮蔽膜",
  "self - taped masking film": "自带胶遮蔽膜", "hdpe masking film": "HDPE遮蔽膜", "taped masking sheet": "带胶遮蔽片",
  "plastic film mask": "塑料遮蔽膜", "masking plastic sheeting": "塑料遮蔽片材", "plastic protective film": "塑料保护膜",
  "film masking": "薄膜遮蔽", "plastic covering film": "塑料覆盖膜", "masking plastic sheet": "塑料遮蔽片",
  "film for masking": "遮蔽用薄膜", "plastic masking sheet": "塑料遮蔽片", "taped masking film": "带胶遮蔽膜",
  "masking tape film": "胶带遮蔽膜", "pre - applied masking film": "预贴遮蔽膜", "adhesive masking film": "自粘遮蔽膜",
  "rubber resin": "橡胶树脂", "tpe polymer": "TPE聚合物", "metal": "金属", "electronic components": "电子元件",
  "plastic resin": "塑料树脂", "adhesive": "胶粘剂", "polymer": "聚合物", "additives": "添加剂",
  "recycled plastic": "再生塑料", "polyethylene resin": "聚乙烯树脂", "plastic additives": "塑料添加剂",
  "petroleum": "石油", "ethylene": "乙烯", "catalyst": "催化剂", "solvents": "溶剂", "pigments": "颜料",
  "chemical additives": "化学添加剂", "base film material": "基膜材料", "high - density polyethylene resin": "高密度聚乙烯树脂",
  "adhesive materials": "胶粘材料", "polymer raw materials": "聚合物原料", "tape backing materials": "胶带基材",
  "plasticizer": "增塑剂", "colorant": "着色剂", "plastic raw material": "塑料原料", "plastic compound": "塑料配混料",
  "film base material": "薄膜基材", "led tvs": "LED电视", "monitor": "显示器", "display devices": "显示设备",
  "home appliances": "家用电器", "consumer electronics": "消费电子", "packaging": "包装", "labeling": "标签制作",
  "crafts": "手工艺", "electronics assembly": "电子装配", "office use": "办公用途", "automotive painting": "汽车涂装",
  "electronics manufacturing": "电子制造", "furniture production": "家具生产", "construction": "建筑施工", "metal processing": "金属加工",
  "glass manufacturing": "玻璃制造", "aircraft manufacturing": "飞机制造", "aircraft maintenance": "飞机维护",
  "industrial coating": "工业涂装", "construction painting": "建筑涂装", "painting projects": "涂装工程",
  "construction sites": "施工现场", "automotive refinishing": "汽车修补涂装", "furniture manufacturing": "家具制造",
  "decorative work": "装饰工程", "painting industry": "涂装行业", "construction projects": "建筑工程",
  "diy home improvement": "家居DIY", "printing": "印刷", "electronics production": "电子生产",
  "metal finishing": "金属表面处理", "furniture finishing": "家具涂装", "diy projects": "DIY项目",
}));
const localizeCategory = (value) => splitValues(value)
  .map((item) => {
    const translated = categoryTranslations.get(item.toLowerCase());
    if (!translated) throw new Error(`未配置中文产品品类：${item}`);
    return translated;
  })
  .join("；");
const localizeCountry = (value) => {
  const code = String(value || "").toUpperCase();
  if (!code) return "未标明";
  return countryTranslations.get(code) || `待补充中文（${code}）`;
};
const localizeProductTerms = (value) => splitValues(value)
  .map((item) => productTermTranslations.get(item.toLowerCase()) || item)
  .join("；");
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
const validEmailsByCompany = companies.map((company) => {
  const statuses = emailStatusMap(company);
  return [...new Set([...splitValues(company.website_emails), ...splitValues(company.emails)]
    .filter((email) => statuses.get(email.toLowerCase()) === 1)
    .map((email) => email.toLowerCase()))];
});
const companiesWithValidEmails = validEmailsByCompany.filter((emails) => emails.length > 0).length;
const validEmailAssociations = validEmailsByCompany.reduce((total, emails) => total + emails.length, 0);
const uniqueValidEmails = new Set(validEmailsByCompany.flat()).size;
const hasValidEmailByCompany = validEmailsByCompany.map((emails) => emails.length > 0);
const hasValidPhoneByCompany = companies.map((company) => splitValues(company.phone_statuses)
  .some((item) => item.includes(":状态1/")));
const companiesWithValidPhones = hasValidPhoneByCompany.filter(Boolean).length;
const companiesWithAnyValidContact = companies.filter((_, index) => (
  hasValidEmailByCompany[index] || hasValidPhoneByCompany[index]
)).length;
const companiesWithBoth = companies.filter((_, index) => (
  hasValidEmailByCompany[index] && hasValidPhoneByCompany[index]
)).length;
const companiesWithEmailOnly = companies.filter((_, index) => (
  hasValidEmailByCompany[index] && !hasValidPhoneByCompany[index]
)).length;
const companiesWithPhoneOnly = companies.filter((_, index) => (
  !hasValidEmailByCompany[index] && hasValidPhoneByCompany[index]
)).length;
const companiesWithNoValidContact = companies.length - companiesWithAnyValidContact;

sheet.mergeCells("A1:N1");
sheet.getRange("A1").values = [["七类产品全球客户总表"]];
sheet.mergeCells("A2:N2");
sheet.getRange("A2").values = [[
  "胶带、遮蔽膜、刷子、猪毛刷、羊毛刷、PVC护角条、塑料桶 · 一行一家公司 · 全球覆盖、欧美优先 · 更新：2026-07-17",
]];

const cards = [
  ["A3:D3", "公司总数", "E3:H3", `=COUNTA(E${firstDataRow}:E${lastDataRow})`],
  ["I3:L3", "有效联系方式公司", "M3:P3", "='成本与流程'!B5"],
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
sheet.getRange("AG3").values = [[`OpenAPI 累计费用：¥${projectSpend.toFixed(2)} / 上限 ¥${projectCap.toFixed(2)}`]];
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
    localizeCategory(company.categories),
    String(company.company_id),
    company.company_name || "",
    localizeCountry(company.country_code),
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
    localizeProductTerms(company.product_names),
    localizeProductTerms(company.product_tags),
    company.product_descriptions || "",
    localizeProductTerms(company.product_aliases),
    localizeProductTerms(company.product_superordinate),
    localizeProductTerms(company.product_downstream),
    localizeCategory(company.search_terms),
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

costSheet.showGridLines = false;
costSheet.mergeCells("A1:F1");
costSheet.getRange("A1").values = [["公司级有效联系方式成本与流程结论"]];
costSheet.getRange("A1:F1").format = {
  fill: "#17365D", font: { bold: true, color: "#FFFFFF", size: 16 },
  horizontalAlignment: "center", verticalAlignment: "center",
};
costSheet.getRange("A3:C3").values = [["指标", "结果", "严格口径"]];
costSheet.getRange("A4:C16").values = [
  ["公司总数", companies.length, "一行一家公司ID"],
  ["拥有至少一种有效联系方式的公司", companiesWithAnyValidContact, "至少1个状态=1的邮箱或电话；核心总业务指标"],
  ["拥有有效邮箱的公司", companiesWithValidEmails, "至少1个状态=1的邮箱；不按邮箱数量重复计算"],
  ["拥有有效电话的公司", companiesWithValidPhones, "至少1个状态=1的电话；不按电话数量重复计算"],
  ["邮箱和电话都有的公司", companiesWithBoth, "同时计入邮箱公司和电话公司"],
  ["只有有效邮箱的公司", companiesWithEmailOnly, "有有效邮箱、无有效电话"],
  ["只有有效电话的公司", companiesWithPhoneOnly, "无有效邮箱、有有效电话"],
  ["两者都没有的公司", companiesWithNoValidContact, "无状态=1的邮箱，也无状态=1的电话"],
  ["OpenAPI累计费用", projectSpend, "人民币；已审计本项目全部调用"],
  ["每家有效联系方式公司成本", null, "累计费用 ÷ 拥有至少一种有效联系方式的公司"],
  ["每家有效邮箱公司成本", null, "累计费用 ÷ 拥有有效邮箱的公司"],
  ["每家有效电话公司成本", null, "累计费用 ÷ 拥有有效电话的公司"],
  ["预算剩余", null, "预算上限 ¥500.00 - 累计费用"],
];
costSheet.getRange("B13:B16").formulas = [
  ["=ROUND(B12/B5,2)"],
  ["=ROUND(B12/B6,2)"],
  ["=ROUND(B12/B7,2)"],
  [`=ROUND(${projectCap}-B12,2)`],
];
costSheet.getRange("A18:C18").values = [["邮箱技术审计", "数量", "说明"]];
costSheet.getRange("A19:C20").values = [
  ["去重后的有效邮箱地址", uniqueValidEmails, "按邮箱文本跨公司去重；不是公司级业务指标"],
  ["公司—邮箱有效关联记录", validEmailAssociations, "未跨公司去重；仅供数据审计"],
];
costSheet.getRange("A22:C22").values = [["费用构成", "金额（元）", "说明"]];
costSheet.getRange("A23:C28").values = [
  ["海关客户搜索", 49.50, "七类产品搜索与同义词翻页"],
  ["海关公司联系方式", 280.00, "按公司ID去重后的批量联系方式"],
  ["人物搜索", 19.50, "混合搜索1页 + 逐公司12页"],
  ["人物联系方式", 3.00, "人工审查后仅购买6人"],
  ["邮箱验证", 3.00, "API、官网及人物新增邮箱"],
  ["电话验证", 6.60, "主批58个 + 权威来源新增8个"],
];
costSheet.getRange("A30:C30").values = [["流程改进", "优先级", "执行规则"]];
costSheet.getRange("A31:C35").values = [
  ["先做法人实体去重", "P0", "公司名称+官网域名+国家归一化；重复实体复用已验证联系方式"],
  ["所有来源进入统一验证队列", "P0", "API、官网、人物邮箱增量入库后立即验证；禁止只验API字段"],
  ["人物搜索按公司逐个执行", "P0", "人工确认公司精确匹配后，每家公司最多购买1位高相关人员"],
  ["状态3/0不盲目重试", "P1", "先查官网或换人物；避免反垃圾拦截导致重复付费"],
  ["发送后用真实退信闭环", "P0", "小批量投递、记录硬退信、永久抑制无效地址；验证状态1仍非送达保证"],
];
for (const range of ["A3:C3", "A18:C18", "A22:C22", "A30:C30"]) {
  costSheet.getRange(range).format = { fill: "#4472C4", font: { bold: true, color: "#FFFFFF" } };
}
costSheet.getRange("A3:C35").format.wrapText = true;
costSheet.getRange("B4:B11").format.numberFormat = "#,##0";
costSheet.getRange("B12:B16").format.numberFormat = '"¥"#,##0.00';
costSheet.getRange("B19:B20").format.numberFormat = "#,##0";
costSheet.getRange("B23:B28").format.numberFormat = '"¥"#,##0.00';
costSheet.getRange("B4:B28").format.horizontalAlignment = "right";
costSheet.getRange("4:16").format.rowHeight = 26;
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
  "研究状态": "这家公司目前调研到哪一步", "市场优先级": "欧美优先或全球常规", "产品品类（中文）": "七类产品中该公司实际命中的一个或多个品类",
  "公司ID": "跨境魔方中的公司唯一编号", "公司名称": "公司名称；一行只放一家", "国家/地区（中文）": "公司所在国家的中文名称",
  "首选邮箱": "优先取官网补充邮箱，否则取API/人物邮箱", "邮箱可用状态": "有效、无效、不确定或接口未能检测",
  "首选电话": "优先取官网电话，否则取API电话", "官网": "公司网站", "联系完整度": "按有效邮箱、有效电话、官网、社媒加权",
  "跟进状态": "人工维护的销售进度", "负责人": "人工填写跟进人", "API地址（原文）": "跨境魔方返回的原始公司地址",
  "官网核验地址（原文）": "官网或权威来源确认的原始地址", "经营范围（原文）": "API返回的公司经营或产品范围原文", "匹配贸易次数": "与本品类匹配的贸易记录数",
  "贸易总次数": "该公司全部贸易记录数", "匹配占比": "匹配贸易次数占总贸易次数", "最近贸易日期": "最近一笔相关贸易日期",
  "API邮箱": "海关公司API和审查后人物API获取的邮箱", "官网补充邮箱": "官网、政府或权威目录补充的邮箱",
  "API电话": "跨境魔方返回的电话", "官网补充电话": "官网、政府或权威目录补充的电话", "电话验证详情": "每个号码的有效状态、类型及WhatsApp状态",
  "WhatsApp": "明确识别的WhatsApp号码", "社交媒体": "LinkedIn等链接", "官网联系渠道": "官网表单、客服入口等",
  "邮箱验证详情": "每个邮箱及状态码；1有效、2无效、3不确定、0未能检测", "产品名称": "API结构化产品名；已知词优先显示中文",
  "产品标签": "API提取的产品关键词；已知词优先显示中文", "报关品名/命中证据（原文）": "原始报关品名；用于证明为何列入", "产品别名": "API返回的近义词；已知词优先显示中文",
  "上游词": "API返回的上游关联词；已知词优先显示中文", "下游词": "API返回的下游关联词；已知词优先显示中文", "搜索词（中文）": "找到该公司的中文查询词",
  "搜索原始来源": "对应原始搜索文件", "API联系方式来源": "联系方式来自哪个API", "官网核验来源": "核验网页或权威文件链接",
  "官网核验说明": "人工核验结论、人物职位和排除原因", "最后核验日期": "本行最后一次数据核验日期",
};
const keyFields = new Set(["产品品类（中文）", "公司名称", "国家/地区（中文）", "首选邮箱", "邮箱可用状态", "首选电话", "电话验证详情", "官网", "报关品名/命中证据（原文）", "跟进状态"]);
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

const costCheck = await workbook.inspect({
  kind: "table",
  range: "成本与流程!A3:C20",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 3,
  maxChars: 5000,
});
console.log(costCheck.ndjson);

const localizationCheck = await workbook.inspect({
  kind: "table",
  range: "客户总表!C6:F12",
  include: "values",
  tableMaxRows: 7,
  tableMaxCols: 4,
  maxChars: 3500,
});
console.log(localizationCheck.ndjson);

const productLanguageCheck = await workbook.inspect({
  kind: "table",
  range: "客户总表!AD6:AJ12",
  include: "values",
  tableMaxRows: 7,
  tableMaxCols: 7,
  maxChars: 5000,
});
console.log(productLanguageCheck.ndjson);

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
const previewCost = await workbook.render({
  sheetName: "成本与流程",
  range: "A1:F35",
  scale: 1.5,
  format: "png",
});
await fs.writeFile(
  path.join(workDir, "cost-process-preview.png"),
  new Uint8Array(await previewCost.arrayBuffer()),
);
const previewGuide = await workbook.render({
  sheetName: "字段说明",
  range: `A1:D${headers.length + 3}`,
  scale: 1.1,
  format: "png",
});
await fs.writeFile(
  path.join(workDir, "field-guide-preview.png"),
  new Uint8Array(await previewGuide.arrayBuffer()),
);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });
console.log(`Exported ${outputPath}`);
