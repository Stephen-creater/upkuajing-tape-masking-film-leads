#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const masterPath = path.join(root, "data", "processed", "company-master.json");
const cachePath = path.join(root, "work", "business-scope-translation-cache.json");
const execute = process.argv.includes("--execute");
const force = process.argv.includes("--force");
const fallback = "暂无经营范围信息";

const categoryNames = new Map([
  ["tape", "胶带"],
  ["masking film", "遮蔽膜"],
  ["胶带", "胶带"],
  ["遮蔽膜", "遮蔽膜"],
  ["刷子", "刷子"],
  ["猪毛刷", "猪毛刷"],
  ["羊毛刷", "羊毛刷"],
  ["pvc护角条", "聚氯乙烯护角条"],
  ["塑料桶", "塑料桶"],
  ["油漆刷", "油漆刷"],
]);

const categoryFallback = (categories) => {
  const localized = String(categories || "")
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => categoryNames.get(item.toLowerCase()) || "相关产品");
  const products = [...new Set(localized)].join("、") || "相关产品";
  return `${products}的采购、进口、分销及配套业务`;
};

const splitForTranslation = (text, maxLength = 2200) => {
  const parts = String(text).split(/(?<=[,;。；])/);
  const chunks = [];
  let current = "";
  for (const part of parts) {
    if (current && current.length + part.length > maxLength) {
      chunks.push(current);
      current = part;
    } else {
      current += part;
    }
  }
  if (current) chunks.push(current);
  return chunks;
};

const customsNoise = new Set([
  "ale", "bd", "blu", "chi", "cod", "count", "d can", "ev", "freight prepaid",
  "gg", "ion", "invoice no ex", "model", "nah", "no n", "pro", "shipping mark",
  "st b", "tuff", "un no", "unit", "umber", "white po",
]);

const cleanSource = (text) => String(text || "")
  .split(",")
  .map((item) => item.trim())
  .filter(Boolean)
  .filter((item) => {
    const lower = item.toLowerCase();
    if (customsNoise.has(lower)) return false;
    if (/^[a-z]{1,2}$/i.test(lower)) return false;
    if (/^[a-z]\s*\d+(?:\s*[a-z])?$/i.test(lower)) return false;
    if (/^\d+\s*[a-z]?$/i.test(lower)) return false;
    return true;
  })
  .join(", ")
  .replace(/\bPVC\b/gi, "polyvinyl chloride")
  .replace(/\bHDPE\b/gi, "high-density polyethylene")
  .replace(/\bLDPE\b/gi, "low-density polyethylene")
  .replace(/\bPET\b/gi, "polyethylene terephthalate")
  .replace(/\bPP\b/gi, "polypropylene")
  .replace(/\bPE\b/gi, "polyethylene");

const translateChunk = async (text) => {
  const body = new URLSearchParams({ client: "gtx", sl: "auto", tl: "zh-CN", dt: "t", q: text });
  let lastError;
  for (let attempt = 1; attempt <= 6; attempt += 1) {
    try {
      const response = await fetch("https://translate.googleapis.com/translate_a/single", {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded;charset=UTF-8" },
        body,
        signal: AbortSignal.timeout(30000),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      return (payload[0] || []).map((item) => item?.[0] || "").join("");
    } catch (error) {
      lastError = error;
      if (attempt < 6) {
        const delay = error?.message === "HTTP 429" ? Math.min(attempt * 10000, 50000) : attempt * 1200;
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }
  throw lastError;
};

const sanitizeChinese = (text, categories) => {
  let value = String(text || "")
    .replace(/PVC/gi, "聚氯乙烯")
    .replace(/HDPE/gi, "高密度聚乙烯")
    .replace(/LDPE/gi, "低密度聚乙烯")
    .replace(/PET/gi, "聚对苯二甲酸乙二醇酯")
    .replace(/ABS/gi, "工程塑料")
    .replace(/LED/gi, "发光二极管")
    .replace(/DIY/gi, "自行制作")
    .replace(/MRO/gi, "维护维修运行")
    .replace(/SUV/gi, "运动型多用途汽车")
    .replace(/ATM/gi, "自动柜员机")
    .replace(/Wi[ -]?Fi/gi, "无线网络")
    .replace(/\p{Script=Latin}+/gu, "")
    .replace(/[ \t]+/g, "")
    .replace(/,+/g, "，")
    .replace(/;+/g, "；")
    .replace(/:+/g, "：")
    .replace(/，{2,}/g, "，")
    .replace(/；{2,}/g, "；")
    .replace(/[，、]{2,}/g, "，")
    .replace(/[，；：、\s]+$/g, "")
    .replace(/^[，；：、\s]+/g, "");
  if (!/\p{Script=Han}/u.test(value)) value = categoryFallback(categories);
  if (/\p{Script=Latin}/u.test(value)) throw new Error(`中文清洗失败：${value}`);
  return value;
};

const translateScope = async (company) => {
  const raw = String(company.business_scope || "").trim();
  if (!raw) return fallback;
  const cleaned = cleanSource(raw);
  if (!cleaned) return categoryFallback(company.categories);
  const translated = [];
  for (const chunk of splitForTranslation(cleaned)) translated.push(await translateChunk(chunk));
  return sanitizeChinese(translated.join(""), company.categories);
};

const master = JSON.parse(await fs.readFile(masterPath, "utf8"));
await fs.mkdir(path.dirname(cachePath), { recursive: true });
let cache = {};
try {
  cache = JSON.parse(await fs.readFile(cachePath, "utf8"));
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}
const pending = master.companies.filter((company) => force || !String(company.business_scope_zh || "").trim());
console.log(`待本地化：${pending.length} / ${master.companies.length}`);
if (!execute) {
  console.log("预演完成；添加 --execute 后才会写入 company-master.json。");
  process.exit(0);
}

let completed = 0;
for (const company of pending) {
  const cacheKey = String(company.company_id);
  const sourceValue = String(company.business_scope || "");
  if (cache[cacheKey]?.source === sourceValue) {
    company.business_scope_zh = cache[cacheKey].translation;
  } else {
    company.business_scope_zh = await translateScope(company);
    cache[cacheKey] = { source: sourceValue, translation: company.business_scope_zh };
    await fs.writeFile(cachePath, `${JSON.stringify(cache, null, 2)}\n`, "utf8");
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  completed += 1;
  if (completed % 20 === 0 || completed === pending.length) {
    console.log(`已完成：${completed} / ${pending.length}`);
  }
}

for (const company of master.companies) {
  const value = String(company.business_scope_zh || "").trim();
  if (!value) throw new Error(`公司 ${company.company_id} 缺少中文经营范围`);
  if (/\p{Script=Latin}/u.test(value)) throw new Error(`公司 ${company.company_id} 的中文经营范围仍含外文：${value}`);
}

await fs.writeFile(masterPath, `${JSON.stringify(master, null, 2)}\n`, "utf8");
console.log(`已写入：${masterPath}`);
