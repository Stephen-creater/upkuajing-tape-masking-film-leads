# 跨境魔方 OpenAPI 调研摘要

> 核对日期：2026-07-17。价格和字段可能调整，正式批量运行前应再查价。

## 适合本项目的链路

1. 调用 `POST /agent/customs/company/list`，用 `products`、`companyType=2`和 `existEmail=1` 找有邮箱数据的采购商。
2. 在本地对产品描述做严格二次过滤，避免 `masking film` 模糊命中 `thick film`。
3. 调用 `POST /agent/customs/company/contact/batch`，用最多 20 个 `companyIds` 批量取回邮箱、电话、网站和社媒。
4. 将客户数据保留在本地 `output/`，不提交到公开 GitHub 仓库。

## 实测结论

- `tape` 模糊搜索能命中真实胶带贸易描述，但品类很宽，需要后续细分胶带类型。
- `masking film` 必须使用精确词组或本地严格过滤；模糊搜索会返回大量与遮蔽膜无关的 `thick film` 电子元件。
- 精确搜索已命中 `PE paint barrier film with washi tape`、`POLYETHYLENE MASKING FILM`、`Masking Film`等真实记录。
- 联系方式响应的真实结构是 `data.list[].contact_data`，比参考文档多一层 `contact_data`。
- 邮箱有 `is_valid` 状态：`0` 未检测、`1` 有效、`2` 无效、`3` 不确定。不应把“有邮箱”直接当成“邮箱已验证”。

## 2026-07-17 实时价格

| 能力 | 文档价格 | 数据上限 |
|---|---:|---:|
| 采购商/供应商列表 | ¥1.5/次 | 20 条/页 |
| 海关公司联系方式 | 价目表显示 ¥0.5/个；实测计费 ¥1/个 | 1 个计费单位 |
| 全球获客公司/人物联系方式 | ¥1/个 | 1 个 |
| 邮件发送 | ¥0.03/封 | 1 封 |
| 邮件有效性检测 | ¥0.1/条 | 1 条 |

由于价目表与实际扣费存在差异，CLI 用比实测价更高的保守估算做请求前拦截，并使用响应中的 `fee.apiCost` 累加实际费用。

## 官方来源

- [跨境魔方开发者中心](https://developer.upkuajing.com/openapi/)
- [官方海关贸易公司搜索 Skill](https://github.com/Upkuajing/upkuajing-trade-company-search)
- [官方公司人员搜索 Skill](https://github.com/Upkuajing/upkuajing-company-people-search)

