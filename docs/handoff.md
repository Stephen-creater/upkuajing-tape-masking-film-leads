# 开发交接

## 当前可观测状态

- 公开仓库：`Stephen-creater/upkuajing-tape-masking-film-leads`
- 权威交付物：`deliverables/tape-masking-film-customer-master.xlsx`
- 行粒度：一行一家公司，`companyId` 为主键
- 有效候选：35 家，全部已完成跨境魔方联系方式查询
- 品类：`tape` 18 家、`masking film` 16 家、两类都命中 1 家
- 邮箱：26/35 家至少有一个状态=1的有效邮箱，共31个有效邮箱地址
- 电话：28/35 家至少有一个状态=1的有效电话；35/35 家至少有一个有效邮箱或有效电话
- 欧美优先：5 家；官网、人物和权威来源补救已完成
- OpenAPI 累计实际费用：¥81.60 / 上限 ¥100.00；剩余 ¥18.40

## 数据链路

1. `data/raw/upkuajing/2026-07-17/` 保存每次付费调用的原始返回，不改写。
2. `scripts/build_company_master.py` 将产品搜索数据严格过滤并按公司去重。
3. `scripts/enrich_company_contacts.py` 补全 API 联系方式；当前已全部完成，不应重复付费调用。
4. `data/raw/web/2026-07-17/` 保存官网、政府和权威目录核验证据。
5. 邮箱与电话验证结果分别保存在 `data/raw/upkuajing/2026-07-17/`，状态台账覆盖 API、官网和人物来源。
6. `data/processed/company-master.json` 是 Excel 的结构化输入。
7. `scripts/build_workbook.mjs` 使用 `@oai/artifact-tool` 生成唯一 Excel 交付物。

## 维护原则

- 不创建第二份客户总表；直接更新权威 Excel，历史由 Git 保留。
- 新的 API 返回先落 `data/raw/`，再进入处理层和 Excel，不直接手改原始数据。
- 官网补充必须记录明确来源 URL，不用推测值。
- 跟进状态和负责人是 Excel 中的人工维护字段。
- 所有修改按小步提交，每一个可验证的小步都要 `commit + push`，不留本地未同步改动。

## 下一个高价值任务

不要继续重复调用状态=3或状态=0的相同邮箱。下一步应小批量发送、记录真实硬退信并建立抑制名单；对无有效邮箱的9家公司，只有在出现新的精确人物或新官网证据时再增量验证。
