# Tape & Masking Film Buyer Leads

使用跨境魔方 OpenAPI 查找 `tape`（胶带）和 `masking film`（遮蔽膜）的海外采购公司，并将公开联系方式维护在一份权威 Excel 客户总表中。

## 为什么有这个项目

获客不能只搜公司名，必须同时解决三个问题：

1. 这家公司是否真的采购过目标产品；
2. `masking film` 是否被错误匹配成 `thick film`等无关产品；
3. 联系方式是否存在，以及邮箱是否已经验证。

本工具先从海关贸易记录筛选采购商，再做产品词严格二次过滤，最后只对少量高相关公司购买联系方式。

## 安全与费用设计

- 默认是 dry-run，不会调用付费 API。
- 必须显式加 `--execute` 才执行。
- 本批项目累计上限为 ¥100，每个付费脚本都在请求前做预算拦截。
- API Key 只从 `UPKUAJING_API_KEY` 环境变量读取，绝不写入输出。
- 用户已明确选择公开仓库；原始证据、结构化数据和 Excel 均提交，`work/`与 `.env`不提交。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

export UPKUAJING_API_KEY='your_api_key'

# 先看费用估算，不发请
upkuajing-leads

# 实际查询：两个品，每个品只取 3 家联系方式
upkuajing-leads --execute --contacts-per-product 3 --max-cost-cny 15
```

输出保存在本地 `output/`：

- `leads-<timestamp>.csv`：便于 Excel/飞书筛选；
- `leads-<timestamp>.json`：便于后续邮件自动化。

## 目录约定

```text
data/raw/          # 不改写的 API 原始记录和来源快照
data/processed/    # 清洗、去重后的公司主数据
deliverables/      # 当前权威交付物，只保留一份客户总表
scripts/           # 可重复生成数据和 Excel 的维护工具
src/               # API 客户端与通用业务逻辑
tests/             # 自动化测试
docs/              # 接口调研和维护说明
work/              # 不提交的临时文件
```

`deliverables/tape-masking-film-customer-master.xlsx` 是唯一客户数据主账。不创建 `final-v2`、`new`等并行版本；历史通过 Git 追溯。

## 参数

```text
--products tape "masking film"
--contacts-per-product 3
--max-cost-cny 15
--output-dir output
--execute
```

早期 CLI 仍保留单次 ¥50 的旧保护；本批增量脚本使用累计 ¥100 上限。详细接口、实测费用和优化结论见 [API 调研摘要](docs/api-research.md)与[成本分析](docs/cost-analysis.md)。

## 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 合规提醒

仅联系与产品有真实商业相关性的对象；尊重当地反垃圾邮件、隐私和退订规则。发送前应再验证邮箱，提供清晰退订方式，并限制发送频率。

## License

MIT
