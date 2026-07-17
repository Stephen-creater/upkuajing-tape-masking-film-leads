# Tape & Masking Film Buyer Leads

使用跨境魔方 OpenAPI 查找 `tape`（胶带）和 `masking film`（遮蔽膜）的海外采购公司，并将公开联系方式导出为本地 CSV/JSON。

## 为什么有这个项目

获客不能只搜公司名，必须同时解决三个问题：

1. 这家公司是否真的采购过目标产品；
2. `masking film` 是否被错误匹配成 `thick film`等无关产品；
3. 联系方式是否存在，以及邮箱是否已经验证。

本工具先从海关贸易记录筛选采购商，再做产品词严格二次过滤，最后只对少量高相关公司购买联系方式。

## 安全与费用设计

- 默认是 dry-run，不会调用付费 API。
- 必须显式加 `--execute` 才执行。
- 单次运行上限不得高于 ¥50，请求前用保守估算拦截。
- API Key 只从 `UPKUAJING_API_KEY` 环境变量读取，绝不写入输出。
- `output/`、`data/`、`work/`和 `.env` 全部被 Git 忽略，客户联系方式不会进入公开仓库。

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

## 参数

```text
--products tape "masking film"
--contacts-per-product 3
--max-cost-cny 15
--output-dir output
--execute
```

`--max-cost-cny` 的程序级硬上限是 ¥50。详细接口、计费和实测差异见 [API 调研摘要](docs/api-research.md)。

## 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 合规提醒

仅联系与产品有真实商业相关性的对象；尊重当地反垃圾邮件、隐私和退订规则。发送前应再验证邮箱，提供清晰退订方式，并限制发送频率。

## License

MIT
