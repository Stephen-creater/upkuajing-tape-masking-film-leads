#!/usr/bin/env python3
"""Run one idempotent people-search page per company lacking a validated email."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "processed" / "company-master.json"
RAW_DIR = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "people-recovery-search"
ENDPOINT = "https://openapi.upkuajing.com/agent/search/person/list"
PREVIOUS_PROJECT_SPEND_CENTS = 5390
PRICE_PER_SEARCH_CENTS = 150
MAX_PROJECT_SPEND_CENTS = 10000


def has_valid_email(row: dict[str, Any]) -> bool:
    return any(item.strip().endswith(":1") for item in row.get("email_statuses", "").split(";"))


def safe_name(row: dict[str, Any]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", row["company_name"].casefold()).strip("-")[:45]
    return f"{row['company_id']}-{slug}.json"


def paid_search(api_key: str, company_name: str) -> dict[str, Any]:
    payload = {
        "companyNames": [company_name],
        "existEmail": 1,
        "sourceNames": ["depth_company", "linkedin"],
        "sort": 0,
        "isExact": False,
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("code") != 0:
        raise RuntimeError(f"API error {result.get('code')}: {result.get('msg')}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    targets = [row for row in master["companies"] if not has_valid_email(row)]
    pending = [row for row in targets if not (RAW_DIR / safe_name(row)).exists()]
    projected = PREVIOUS_PROJECT_SPEND_CENTS + len(pending) * PRICE_PER_SEARCH_CENTS
    print(
        f"Target companies: {len(targets)}; pending paid searches: {len(pending)}\n"
        f"Expected new cost: ¥{len(pending) * PRICE_PER_SEARCH_CENTS / 100:.2f}\n"
        f"Projected project spend: ¥{projected / 100:.2f} / ¥{MAX_PROJECT_SPEND_CENTS / 100:.2f}"
    )
    if projected > MAX_PROJECT_SPEND_CENTS:
        raise SystemExit("Search blocked: projected project spend exceeds cap")
    if not args.execute:
        print("Dry run only. Add --execute to call the paid endpoint.")
        return
    api_key = os.environ.get("UPKUAJING_API_KEY", "")
    if not api_key:
        raise SystemExit("UPKUAJING_API_KEY is required with --execute")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    spent = 0
    for row in pending:
        response = paid_search(api_key, row["company_name"])
        actual = int((response.get("fee") or {}).get("apiCost") or 0)
        if PREVIOUS_PROJECT_SPEND_CENTS + spent + actual > MAX_PROJECT_SPEND_CENTS:
            raise RuntimeError("Provider charge exceeded the project budget cap")
        (RAW_DIR / safe_name(row)).write_text(
            json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        spent += actual
        count = len((response.get("data") or {}).get("list") or [])
        print(f"{row['company_id']} {row['company_name']}: {count} people, ¥{actual / 100:.2f}")
    print(f"Finished; new spend ¥{spent / 100:.2f}; project total ¥{(PREVIOUS_PROJECT_SPEND_CENTS + spent) / 100:.2f}")


if __name__ == "__main__":
    main()
