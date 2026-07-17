#!/usr/bin/env python3
"""Build the one-row-per-company source used by the Excel master workbook."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "company-master.json"

EUROPE_CODES = {
    "AD", "AL", "AT", "AX", "BA", "BE", "BG", "BY", "CH", "CY", "CZ",
    "DE", "DK", "EE", "ES", "FI", "FO", "FR", "GB", "GG", "GI", "GR",
    "HR", "HU", "IE", "IM", "IS", "IT", "JE", "LI", "LT", "LU", "LV",
    "MC", "MD", "ME", "MK", "MT", "NL", "NO", "PL", "PT", "RO", "RS",
    "SE", "SI", "SJ", "SK", "SM", "UA", "VA",
}
WESTERN_PRIORITY_CODES = EUROPE_CODES | {"US", "CA"}

SEARCHES = [
    {
        "product": "tape",
        "path": RAW_DIR / "tape-buyers-fuzzy-search.jsonl",
        "source": "tape-buyers-fuzzy-search",
    },
    {
        "product": "masking film",
        "path": RAW_DIR / "masking-film-buyers-exact-search.jsonl",
        "source": "masking-film-buyers-exact-search",
    },
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def matches_product(company: dict[str, Any], product: str) -> bool:
    values = [
        company.get("productDesc") or "",
        *(company.get("productNames") or []),
        *(company.get("productTags") or []),
    ]
    haystack = " ".join(str(value) for value in values).casefold()
    words = [re.escape(word) for word in product.casefold().split()]
    return bool(re.search(r"\b" + r"[\s\-_/.]*".join(words) + r"\b", haystack))


def unique_join(values: list[str]) -> str:
    return "; ".join(dict.fromkeys(value.strip() for value in values if value.strip()))


def merge_list_field(target: dict[str, Any], key: str, values: list[Any]) -> None:
    current = [str(value) for value in target.get(key) or []]
    target[key] = list(dict.fromkeys([*current, *(str(value) for value in values or [])]))


def load_initial_contacts() -> dict[int, dict[str, Any]]:
    path = PROCESSED_DIR / "initial-six-contact-enriched-leads.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {int(item["company_id"]): item for item in data.get("leads") or []}


def main() -> None:
    contacts = load_initial_contacts()
    companies: dict[int, dict[str, Any]] = {}

    for search in SEARCHES:
        for raw in read_jsonl(search["path"]):
            if not matches_product(raw, search["product"]):
                continue
            company_id = int(raw["companyId"])
            if company_id not in companies:
                companies[company_id] = {
                    "company_id": company_id,
                    "company_type": raw.get("companyType"),
                    "company_name": raw.get("name", ""),
                    "country_code": raw.get("countryCode", ""),
                    "address": raw.get("address", ""),
                    "business_scope": raw.get("scope", ""),
                    "trade_total": raw.get("tradeTotal"),
                    "trade_match_total": raw.get("tradeMatchTotal"),
                    "trade_match_percent": raw.get("tradeMatchPercent"),
                    "latest_trade_date_ms": raw.get("latestTradeDate"),
                    "categories": [],
                    "search_terms": [],
                    "search_sources": [],
                    "product_descriptions": [],
                    "product_names": [],
                    "product_tags": [],
                    "product_aliases": [],
                    "product_superordinate": [],
                    "product_downstream": [],
                    "emails": "",
                    "email_statuses": "",
                    "phones": "",
                    "whatsapp": "",
                    "websites": "",
                    "socials": "",
                    "contact_source": "",
                    "website_research_source": "",
                    "website_research_notes": "",
                    "research_status": "待补充联系方式",
                }
            company = companies[company_id]
            company["categories"] = list(
                dict.fromkeys([*company["categories"], search["product"]])
            )
            company["search_terms"] = list(
                dict.fromkeys([*company["search_terms"], search["product"]])
            )
            company["search_sources"] = list(
                dict.fromkeys([*company["search_sources"], search["source"]])
            )
            if raw.get("productDesc"):
                company["product_descriptions"] = list(
                    dict.fromkeys([*company["product_descriptions"], raw["productDesc"]])
                )
            merge_list_field(company, "product_names", raw.get("productNames") or [])
            merge_list_field(company, "product_tags", raw.get("productTags") or [])
            merge_list_field(company, "product_aliases", raw.get("productAlias") or [])
            merge_list_field(
                company, "product_superordinate", raw.get("productSuperordinate") or []
            )
            merge_list_field(
                company, "product_downstream", raw.get("productDownstream") or []
            )

    for company_id, contact in contacts.items():
        if company_id not in companies:
            continue
        company = companies[company_id]
        for key in ("emails", "email_statuses", "phones", "websites", "socials"):
            company[key] = contact.get(key, "")
        company["contact_source"] = "UpKuajing customs company contact API"
        company["research_status"] = "API联系方式已获取"

    rows: list[dict[str, Any]] = []
    for company in companies.values():
        country_code = str(company.get("country_code") or "").upper()
        company["market_priority"] = "高-欧美" if country_code in WESTERN_PRIORITY_CODES else "常规-全球"
        for key in (
            "categories",
            "search_terms",
            "search_sources",
            "product_descriptions",
            "product_names",
            "product_tags",
            "product_aliases",
            "product_superordinate",
            "product_downstream",
        ):
            company[key] = unique_join([str(value) for value in company[key]])
        rows.append(company)

    rows.sort(
        key=lambda row: (
            0 if row["market_priority"] == "高-欧美" else 1,
            -(int(row.get("trade_match_total") or 0)),
            row["company_name"].casefold(),
        )
    )
    payload = {
        "schema_version": 1,
        "row_granularity": "one company per row",
        "company_count": len(rows),
        "companies": rows,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    high_priority = sum(row["market_priority"] == "高-欧美" for row in rows)
    enriched = sum(bool(row["emails"]) for row in rows)
    print(
        f"Wrote {OUTPUT_PATH.relative_to(ROOT)}: {len(rows)} companies, "
        f"{high_priority} Western-priority, {enriched} with API contacts"
    )


if __name__ == "__main__":
    main()
