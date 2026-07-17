# 开发交接

## 当前可观测状态

- 公开仓库：`Stephen-creater/upkuajing-tape-masking-film-leads`
- 权威交付物：`deliverables/tape-masking-film-customer-master.xlsx`
- 行粒度：一行一家公司，`companyId` 为主键
- 有效候选：35 家，全部已完成跨境魔方联系方式查询
- 品类：`tape` 18 家、`masking film` 16 家、两类都命中 1 家
- 联系方式：35/35 有邮箱值，21 家邮箱被 API 标记为有效，23 家有电话，27 家有官网
- 欧美优先：5 家；其中 3 家未验证邮箱已做官网核验
- OpenAPI 累计实际费用：约 ¥49.50；前期 ¥50 上限已封顶，不得继续付费调用

## 数据链路

1. `data/raw/upkuajing/2026-07-17/` 保存每次付费调用的原始返回，不改写。
2. `scripts/build_company_master.py` 将产品搜索数据严格过滤并按公司去重。
3. `scripts/enrich_company_contacts.py` 补全 API 联系方式；当前已全部完成，不应重复付费调用。
4. `data/raw/web/2026-07-17/` 保存官网核验证据，`scripts/apply_web_research.py` 将其合并进公司主数据。
5. `data/processed/company-master.json` 是 Excel 的结构化输入。
6. `scripts/build_workbook.mjs` 使用 `@oai/artifact-tool` 生成唯一 Excel 交付物。

## 维护原则

- 不创建第二份客户总表；直接更新权威 Excel，历史由 Git 保留。
- 新的 API 返回先落 `data/raw/`，再进入处理层和 Excel，不直接手改原始数据。
- 官网补充必须记录明确来源 URL，不用推测值。
- 跟进状态和负责人是 Excel 中的人工维护字段。
- 所有修改按小步提交，每一个可验证的小步都要 `commit + push`，不留本地未同步改动。

## 下一个高价值任务

不调用付费 API，优先访问邮箱状态为“未验证”的公司官网，将官方客服/采购邮箱、联系页、电话和地址补入 `data/raw/web/`，然后重新生成 Excel。
