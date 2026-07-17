# 数据说明

本目录和 GitHub 公开同步。表内公司与联系方式为项目数据，不做脱敏。API Key 不属于项目数据，不写入此目录。

## 数据分层

- `raw/upkuajing/2026-07-17/`：跨境魔方搜索任务的原始 JSONL 与任务元数据，不手工修改。
- `processed/initial-six-contact-enriched-leads.*`：已取回联系方式的首批 6 家公司，是历史处理快照，不是最终主表。
- 最终、唯一权威客户总表位于 `../deliverables/tape-masking-film-customer-master.xlsx`。

## 已保存的 API 调用

| 数据集 | 产品 | 匹配 | 返回 | 实际费用 | 用途 |
|---|---|---|---:|---:|---|
| `tape-buyers-fuzzy-search` | tape | 模糊 | 20 | ¥1.50 | 胶带采购商候选 |
| `masking-film-buyers-fuzzy-noisy` | masking film | 模糊 | 20 | ¥1.50 | 质量反例；包含 `thick film` 噪声 |
| `masking-film-buyers-exact-search` | masking film | 精确 | 20 | ¥1.50 | 遮蔽膜采购商候选 |

模糊遮蔽膜结果必须保留，因为它记录了一次付费调研与错误匹配证据；但这批公司不应因此自动成为有效客户。

## 完整性规则

1. 每次付费调用的返回记录都保留在 `raw/`。
2. 每家公司在 Excel 只占一行，以 `companyId` 为主键。
3. 不丢弃 API 字段；主表保留业务可读字段，完整原始值仍可从 JSONL 追溯。
4. 邮箱、电话、网站、社媒保留有效性状态和来源。
5. 未在预算内补齐的公司不删除，标记为“待补充”。
