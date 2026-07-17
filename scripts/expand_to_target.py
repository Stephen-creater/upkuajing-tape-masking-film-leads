#!/usr/bin/env python3
"""Incrementally expand the verified company master without rebuilding old rows.

Paid operations are explicit subcommands. Every response is saved immutably before
derived data is updated. The project budget is cumulative, not a per-run allowance.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17"
MASTER_PATH = ROOT / "data" / "processed" / "company-master.json"
CANDIDATE_PATH = ROOT / "data" / "processed" / "expansion-candidates.json"
API_BASE = "https://openapi.upkuajing.com"

BASELINE_SPEND_CENTS = 8160
PROJECT_CAP_CENTS = 50000
TARGET_CAMPAIGN_COMPANIES = 20
SEARCH_PREFLIGHT_CENTS = 200
CONTACT_PREFLIGHT_CENTS_PER_COMPANY = 100

CAMPAIGN_CATEGORIES = {"油漆刷"}

PRODUCTS = {
    "tape": {
        "api_term": "tape",
        "chinese": "胶带",
        "is_exact": False,
        "initial_cursor_file": "tape-buyers-fuzzy-search.meta.json",
        "source_slug": "tape",
    },
    "masking-film": {
        "api_term": "masking film",
        "chinese": "遮蔽膜",
        "is_exact": True,
        "initial_cursor_file": "masking-film-buyers-exact-search.meta.json",
        "source_slug": "masking-film",
    },
    "brush": {
        "api_term": "brush",
        "chinese": "刷子",
        "is_exact": False,
        "initial_cursor_file": None,
        "source_slug": "brush",
        "match_required_groups": [["brush", "brushes"]],
    },
    "hog-bristle-brush": {
        "api_term": "hog bristle brush",
        "chinese": "猪毛刷",
        "is_exact": True,
        "initial_cursor_file": None,
        "source_slug": "hog-bristle-brush",
        "match_required_groups": [["hog", "boar"], ["brush", "brushes", "bristle", "bristles"]],
    },
    "boar-bristle-brush": {
        "api_term": "boar bristle brush",
        "chinese": "猪毛刷",
        "is_exact": True,
        "initial_cursor_file": None,
        "source_slug": "boar-bristle-brush",
        "match_required_groups": [["hog", "boar"], ["brush", "brushes", "bristle", "bristles"]],
    },
    "wool-brush": {
        "api_term": "wool brush",
        "chinese": "羊毛刷",
        "is_exact": True,
        "initial_cursor_file": None,
        "source_slug": "wool-brush",
        "match_required_groups": [["wool"], ["brush", "brushes"]],
    },
    "pvc-corner-guard": {
        "api_term": "PVC corner guard",
        "chinese": "PVC护角条",
        "is_exact": True,
        "initial_cursor_file": None,
        "source_slug": "pvc-corner-guard",
        "match_required_groups": [["pvc"], ["corner"], ["guard", "protector", "trim", "bead", "profile"]],
    },
    "pvc-corner-bead": {
        "api_term": "PVC corner bead",
        "chinese": "PVC护角条",
        "is_exact": True,
        "initial_cursor_file": None,
        "source_slug": "pvc-corner-bead",
        "match_required_groups": [["pvc"], ["corner"], ["guard", "protector", "trim", "bead", "profile"]],
    },
    "pvc-corner-protector": {
        "api_term": "PVC corner protector",
        "chinese": "PVC护角条",
        "is_exact": True,
        "initial_cursor_file": None,
        "source_slug": "pvc-corner-protector",
        "match_required_groups": [["pvc"], ["corner"], ["guard", "protector", "trim", "bead", "profile"]],
    },
    "plastic-bucket": {
        "api_term": "plastic bucket",
        "chinese": "塑料桶",
        "is_exact": True,
        "initial_cursor_file": None,
        "source_slug": "plastic-bucket",
        "match_required_groups": [["plastic", "plastics"], ["bucket", "buckets", "pail", "pails"]],
    },
    "plastic-pail": {
        "api_term": "plastic pail",
        "chinese": "塑料桶",
        "is_exact": True,
        "initial_cursor_file": None,
        "source_slug": "plastic-pail",
        "match_required_groups": [["plastic", "plastics"], ["bucket", "buckets", "pail", "pails"]],
    },
    "paint-brush": {
        "api_term": "paint brush",
        "chinese": "油漆刷",
        "is_exact": True,
        "initial_cursor_file": None,
        "source_slug": "paint-brush",
        "match_patterns": [
            r"\bpaint[\s\-_/.]*brush(?:es)?\b",
            r"\bpaint[\s\-_/.]+(?:roller|application|applicator|decorating|wall|trim|artist)[\s\-_/.]+brush(?:es)?\b",
            r"\bpainting[\s\-_/.]+brush(?:es)?\b",
            r"\bcoating[\s\-_/.]+(?:application[\s\-_/.]+)?brush(?:es)?\b",
            r"\bbrush(?:es)?[\s\-_/.]+for[\s\-_/.]+paint(?:ing)?\b",
            r"\bpaintbrush(?:es)?\b",
        ],
    },
    "painting-brush": {
        "api_term": "painting brush",
        "chinese": "油漆刷",
        "is_exact": True,
        "initial_cursor_file": None,
        "source_slug": "painting-brush",
        "match_patterns": [
            r"\bpaint[\s\-_/.]*brush(?:es)?\b",
            r"\bpaint[\s\-_/.]+(?:roller|application|applicator|decorating|wall|trim|artist)[\s\-_/.]+brush(?:es)?\b",
            r"\bpainting[\s\-_/.]+brush(?:es)?\b",
            r"\bcoating[\s\-_/.]+(?:application[\s\-_/.]+)?brush(?:es)?\b",
            r"\bbrush(?:es)?[\s\-_/.]+for[\s\-_/.]+paint(?:ing)?\b",
            r"\bpaintbrush(?:es)?\b",
        ],
    },
}

EUROPE_CODES = {
    "AD", "AL", "AT", "AX", "BA", "BE", "BG", "BY", "CH", "CY", "CZ",
    "DE", "DK", "EE", "ES", "FI", "FO", "FR", "GB", "GG", "GI", "GR",
    "HR", "HU", "IE", "IM", "IS", "IT", "JE", "LI", "LT", "LU", "LV",
    "MC", "MD", "ME", "MK", "MT", "NL", "NO", "PL", "PT", "RO", "RS",
    "SE", "SI", "SJ", "SK", "SM", "UA", "VA",
}
WESTERN_PRIORITY_CODES = EUROPE_CODES | {"US", "CA"}


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def split_values(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def unique_join(values: list[Any]) -> str:
    return "; ".join(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def parse_email_statuses(row: dict[str, Any]) -> dict[str, int]:
    statuses: dict[str, int] = {}
    for item in split_values(row.get("email_statuses", "")):
        email, separator, status = item.rpartition(":")
        if separator and status.isdigit():
            statuses[email.casefold()] = int(status)
    return statuses


def has_valid_contact(row: dict[str, Any]) -> bool:
    if 1 in parse_email_statuses(row).values():
        return True
    return any(":状态1/" in item for item in split_values(row.get("phone_statuses", "")))


def count_valid(master: dict[str, Any]) -> int:
    return sum(has_valid_contact(row) for row in master.get("companies", []))


def is_campaign_company(row: dict[str, Any]) -> bool:
    return bool(set(split_values(row.get("categories", ""))) & CAMPAIGN_CATEGORIES)


def count_campaign_valid(master: dict[str, Any]) -> int:
    return sum(
        is_campaign_company(row) and has_valid_contact(row)
        for row in master.get("companies", [])
    )


def expansion_spend_cents() -> int:
    seen_uuids: set[str] = set()
    total = 0
    for path in sorted(RAW_DIR.glob("expansion-*.json")):
        payload = load_json(path, {})
        fee = payload.get("fee") or {}
        cost = int(fee.get("apiCost") or 0)
        uuid = str(fee.get("uuid") or path.name)
        if uuid in seen_uuids:
            continue
        seen_uuids.add(uuid)
        total += cost
    return total


def project_spend_cents() -> int:
    return BASELINE_SPEND_CENTS + expansion_spend_cents()


def authorize(estimated_cents: int) -> None:
    projected = project_spend_cents() + estimated_cents
    if projected > PROJECT_CAP_CENTS:
        raise SystemExit(
            f"付费调用已阻止：保守估算后累计 ¥{projected / 100:.2f}，"
            f"超过上限 ¥{PROJECT_CAP_CENTS / 100:.2f}"
        )


def post(api_key: str, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{API_BASE}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "upkuajing-tape-masking-film-leads/0.2",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:500]}") from exc
    if result.get("code") != 0:
        raise RuntimeError(f"API error {result.get('code')}: {result.get('msg')}")
    return result


def matches_product(company: dict[str, Any], product: str) -> bool:
    values = [
        company.get("productDesc") or "",
        *(company.get("productNames") or []),
        *(company.get("productTags") or []),
    ]
    words = [re.escape(word) for word in product.casefold().split()]
    pattern = r"\b" + r"[\s\-_/.]*".join(words) + r"\b"
    return bool(re.search(pattern, " ".join(map(str, values)).casefold()))


def matches_config(company: dict[str, Any], config: dict[str, Any]) -> bool:
    values = [
        company.get("productDesc") or "",
        *(company.get("productNames") or []),
        *(company.get("productTags") or []),
    ]
    haystack = " ".join(map(str, values)).casefold()
    patterns = config.get("match_patterns")
    if patterns:
        return any(re.search(pattern, haystack) for pattern in patterns)
    groups = config.get("match_required_groups")
    if not groups:
        return matches_product(company, config["api_term"])
    return all(
        any(re.search(rf"\b{re.escape(term.casefold())}\b", haystack) for term in group)
        for group in groups
    )


def blank_candidate(raw: dict[str, Any], config: dict[str, Any], source: str) -> dict[str, Any]:
    country_code = str(raw.get("countryCode") or "").upper()
    return {
        "company_id": int(raw["companyId"]),
        "company_type": raw.get("companyType"),
        "company_name": raw.get("name", ""),
        "country_code": country_code,
        "address": raw.get("address", ""),
        "business_scope": raw.get("scope", ""),
        "trade_total": raw.get("tradeTotal"),
        "trade_match_total": raw.get("tradeMatchTotal"),
        "trade_match_percent": raw.get("tradeMatchPercent"),
        "latest_trade_date_ms": raw.get("latestTradeDate"),
        "categories": config["chinese"],
        "search_terms": config["chinese"],
        "search_sources": source,
        "product_descriptions": str(raw.get("productDesc") or ""),
        "product_names": unique_join(raw.get("productNames") or []),
        "product_tags": unique_join(raw.get("productTags") or []),
        "product_aliases": unique_join(raw.get("productAlias") or []),
        "product_superordinate": unique_join(raw.get("productSuperordinate") or []),
        "product_downstream": unique_join(raw.get("productDownstream") or []),
        "emails": "", "email_statuses": "", "phones": "", "phone_statuses": "",
        "whatsapp": "", "websites": "", "socials": "", "contact_source": "",
        "website_research_source": "", "website_research_notes": "",
        "website_emails": "", "website_phones": "", "website_address": "",
        "website_contact_method": "", "email_validation_reasons": "",
        "email_validation_source": "", "email_validation_summary": "尚未完成验证",
        "phone_validation_summary": "无电话或接口未检测",
        "research_status": "候选公司-待获取联系方式",
        "market_priority": "高-欧美" if country_code in WESTERN_PRIORITY_CODES else "常规-全球",
    }


def merge_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    for key in ("categories", "search_terms", "search_sources", "product_descriptions",
                "product_names", "product_tags", "product_aliases",
                "product_superordinate", "product_downstream"):
        existing[key] = unique_join(split_values(existing.get(key, "")) + split_values(incoming.get(key, "")))


def candidate_payload() -> dict[str, Any]:
    return load_json(CANDIDATE_PATH, {
        "schema_version": 1,
        "row_granularity": "one candidate company per row",
        "companies": [],
    })


def latest_cursor(product_key: str) -> tuple[str | None, int]:
    config = PRODUCTS[product_key]
    paths = sorted(RAW_DIR.glob(f"expansion-search-{config['source_slug']}-page-*.json"))
    if paths:
        latest = load_json(paths[-1], {})
        page_numbers = [int(path.stem.rpartition("-")[2]) for path in paths]
        return str((latest.get("data") or {}).get("cursor") or ""), max(page_numbers) + 1
    initial_cursor_file = config.get("initial_cursor_file")
    if initial_cursor_file:
        meta = load_json(RAW_DIR / initial_cursor_file, {})
        return str(meta.get("cursor") or ""), 2
    return None, 1


def search(product_key: str, api_key: str) -> None:
    config = PRODUCTS[product_key]
    cursor, page = latest_cursor(product_key)
    has_prior_page = bool(list(RAW_DIR.glob(f"expansion-search-{config['source_slug']}-page-*.json")))
    if has_prior_page and not cursor:
        raise SystemExit(f"{config['api_term']} 没有后续游标，无法继续翻页")
    authorize(SEARCH_PREFLIGHT_CENTS)
    payload = {
        "companyType": 2,
        "products": [config["api_term"]],
        "existEmail": 1,
        "isExact": config["is_exact"],
        "sorting_field": "tradeCount",
        "sorting_direction": "desc",
    }
    if cursor:
        payload["cursor"] = cursor
    response = post(api_key, "/agent/customs/company/list", payload)
    raw_path = RAW_DIR / f"expansion-search-{config['source_slug']}-page-{page:02d}.json"
    if raw_path.exists():
        raise RuntimeError(f"拒绝覆盖原始响应：{raw_path}")
    write_json(raw_path, response)

    master = load_json(MASTER_PATH, {})
    candidates = candidate_payload()
    returned, matched, added = merge_search_response(
        product_key, raw_path, response, master, candidates
    )
    write_json(CANDIDATE_PATH, candidates)
    print(
        f"{config['chinese']}第{page}页：返回 {returned}，严格命中 {matched}，"
        f"新增候选 {added}；实际费用 ¥{int((response.get('fee') or {}).get('apiCost') or 0) / 100:.2f}"
    )


def merge_search_response(
    product_key: str,
    raw_path: Path,
    response: dict[str, Any],
    master: dict[str, Any],
    candidates: dict[str, Any],
) -> tuple[int, int, int]:
    config = PRODUCTS[product_key]
    existing_ids = {int(row["company_id"]) for row in master.get("companies", [])}
    by_id = {int(row["company_id"]): row for row in candidates["companies"]}
    returned = (response.get("data") or {}).get("list") or []
    matched = [row for row in returned if matches_config(row, config)]
    added = 0
    for raw in matched:
        company_id = int(raw["companyId"])
        if company_id in existing_ids:
            continue
        incoming = blank_candidate(raw, config, raw_path.stem)
        if company_id in by_id:
            merge_candidate(by_id[company_id], incoming)
        else:
            by_id[company_id] = incoming
            added += 1
    candidates["companies"] = sorted(
        by_id.values(),
        key=lambda row: (0 if row["market_priority"] == "高-欧美" else 1,
                         -int(row.get("trade_match_total") or 0), row["company_name"].casefold()),
    )
    candidates["company_count"] = len(candidates["companies"])
    return len(returned), len(matched), added


def replay_searches() -> None:
    master = load_json(MASTER_PATH, {})
    candidates = candidate_payload()
    total_added = 0
    for product_key, config in PRODUCTS.items():
        if config["chinese"] not in CAMPAIGN_CATEGORIES:
            continue
        for raw_path in sorted(RAW_DIR.glob(f"expansion-search-{config['source_slug']}-page-*.json")):
            response = load_json(raw_path, {})
            returned, matched, added = merge_search_response(
                product_key, raw_path, response, master, candidates
            )
            total_added += added
            print(f"重放 {raw_path.name}：返回 {returned}，严格命中 {matched}，新增 {added}")
    write_json(CANDIDATE_PATH, candidates)
    print(f"免费重放完成：新增候选 {total_added}，候选池共 {candidates['company_count']}")


def apply_contacts(candidates: dict[str, Any], response: dict[str, Any]) -> int:
    by_id = {int(row["company_id"]): row for row in candidates["companies"]}
    applied = 0
    for item in (response.get("data") or {}).get("list") or []:
        row = by_id.get(int(item["companyId"]))
        if not row:
            continue
        contact = item.get("contact_data") or {}
        emails = contact.get("emails") or []
        phones = contact.get("phones") or []
        row["emails"] = unique_join([item.get("val") for item in emails])
        row["email_statuses"] = unique_join([
            f"{item.get('val')}:{int(item.get('is_valid') or 0)}" for item in emails if item.get("val")
        ])
        row["phones"] = unique_join([
            item.get("international_number") or item.get("val") for item in phones
        ])
        row["phone_statuses"] = unique_join([
            f"{item.get('international_number') or item.get('val')}:状态{int(item.get('is_valid') or 0)}/"
            f"类型{int(item.get('phone_type') or 0)}/WhatsApp{int(item.get('is_ws') or 0)}"
            for item in phones if item.get("international_number") or item.get("val")
        ])
        row["whatsapp"] = unique_join([
            item.get("international_number") or item.get("val")
            for item in phones if int(item.get("is_ws") or 0) == 1
        ])
        row["websites"] = unique_join([item.get("val") for item in contact.get("websites") or []])
        row["socials"] = unique_join([item.get("val") for item in contact.get("socials") or []])
        row["contact_source"] = "UpKuajing customs company contact API"
        row["email_validation_source"] = "UpKuajing customs company contact API (2026-07-17)"
        row["email_validation_summary"] = "有有效邮箱" if 1 in parse_email_statuses(row).values() else "无有效邮箱"
        row["phone_validation_summary"] = "有有效电话" if any(":状态1/" in value for value in split_values(row["phone_statuses"])) else "无有效电话"
        row["research_status"] = "API联系方式已获取" if has_valid_contact(row) else "API无有效联系方式-待补充"
        applied += 1
    return applied


def promote(candidates: dict[str, Any], master: dict[str, Any]) -> int:
    needed = max(TARGET_CAMPAIGN_COMPANIES - count_campaign_valid(master), 0)
    if needed == 0:
        return 0
    eligible = [
        row for row in candidates["companies"]
        if is_campaign_company(row) and has_valid_contact(row)
    ]
    eligible.sort(key=lambda row: (0 if row["market_priority"] == "高-欧美" else 1,
                                   -int(row.get("trade_match_total") or 0), row["company_name"].casefold()))
    selected = eligible[:needed]
    selected_ids = {int(row["company_id"]) for row in selected}
    master["companies"].extend(selected)
    master["companies"].sort(key=lambda row: (0 if row["market_priority"] == "高-欧美" else 1,
                                               -int(row.get("trade_match_total") or 0), row["company_name"].casefold()))
    master["company_count"] = len(master["companies"])
    candidates["companies"] = [row for row in candidates["companies"] if int(row["company_id"]) not in selected_ids]
    candidates["company_count"] = len(candidates["companies"])
    return len(selected)


def contacts(api_key: str, limit: int) -> None:
    candidates = candidate_payload()
    pending = [
        row for row in candidates["companies"]
        if is_campaign_company(row) and not row.get("contact_source")
    ]
    pending.sort(key=lambda row: (0 if row["market_priority"] == "高-欧美" else 1,
                                  -int(row.get("trade_match_total") or 0)))
    batch = pending[: min(limit, 20)]
    if not batch:
        raise SystemExit("没有待购买联系方式的候选公司")
    authorize(len(batch) * CONTACT_PREFLIGHT_CENTS_PER_COMPANY)
    response = post(api_key, "/agent/customs/company/contact/batch", {
        "companyIds": [int(row["company_id"]) for row in batch]
    })
    index = len(list(RAW_DIR.glob("expansion-company-contacts-*.json"))) + 1
    raw_path = RAW_DIR / f"expansion-company-contacts-{index:02d}.json"
    if raw_path.exists():
        raise RuntimeError(f"拒绝覆盖原始响应：{raw_path}")
    write_json(raw_path, response)
    applied = apply_contacts(candidates, response)
    master = load_json(MASTER_PATH, {})
    promoted = promote(candidates, master)
    write_json(CANDIDATE_PATH, candidates)
    write_json(MASTER_PATH, master)
    print(
        f"联系方式：请求 {len(batch)}，应用 {applied}，晋级主表 {promoted}；"
        f"实际费用 ¥{int((response.get('fee') or {}).get('apiCost') or 0) / 100:.2f}；"
        f"本轮有效联系方式公司 {count_campaign_valid(master)}/{TARGET_CAMPAIGN_COMPANIES}"
    )


def show_status() -> None:
    master = load_json(MASTER_PATH, {})
    candidates = candidate_payload()
    valid = count_valid(master)
    campaign_valid = count_campaign_valid(master)
    pending = sum(
        is_campaign_company(row) and not row.get("contact_source")
        for row in candidates["companies"]
    )
    print(
        f"主表公司：{len(master.get('companies', []))}\n"
        f"主表有效联系方式公司：{valid}\n"
        f"本轮有效联系方式公司：{campaign_valid}/{TARGET_CAMPAIGN_COMPANIES}\n"
        f"候选池：{len(candidates['companies'])}（本轮待购买联系方式 {pending}）\n"
        f"扩充阶段费用：¥{expansion_spend_cents() / 100:.2f}\n"
        f"项目累计费用：¥{project_spend_cents() / 100:.2f} / ¥{PROJECT_CAP_CENTS / 100:.2f}\n"
        f"预算剩余：¥{(PROJECT_CAP_CENTS - project_spend_cents()) / 100:.2f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="当前新品类增量扩充有效联系方式公司")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("replay-searches")
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--product", choices=sorted(PRODUCTS), required=True)
    search_parser.add_argument("--execute", action="store_true")
    contact_parser = subparsers.add_parser("contacts")
    contact_parser.add_argument("--limit", type=int, default=20)
    contact_parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.command == "status":
        show_status()
        return
    if args.command == "replay-searches":
        replay_searches()
        show_status()
        return
    if not args.execute:
        print("仅预演：添加 --execute 才会调用付费API")
        show_status()
        return
    api_key = os.environ.get("UPKUAJING_API_KEY", "")
    if not api_key:
        raise SystemExit("执行付费调用需要环境变量 UPKUAJING_API_KEY")
    if args.command == "search":
        search(args.product, api_key)
    elif args.command == "contacts":
        if not 1 <= args.limit <= 20:
            raise SystemExit("--limit 必须为 1 到 20")
        contacts(api_key, args.limit)
    show_status()


if __name__ == "__main__":
    main()
