#!/usr/bin/env python3
"""Search one auditable page of people for companies without a validated email."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "processed" / "company-master.json"
RAW_PATH = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "missing-email-people-search.json"
ENDPOINT = "https://openapi.upkuajing.com/agent/search/person/list"
PREVIOUS_PROJECT_SPEND_CENTS = 5220
SEARCH_COST_CENTS = 150
MAX_PROJECT_SPEND_CENTS = 10000


def has_valid_email(row: dict[str, Any]) -> bool:
    return any(item.strip().endswith(":1") for item in row.get("email_statuses", "").split(";"))


def target_companies(master: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in master["companies"] if not has_valid_email(row)]


def paid_search(api_key: str, names: list[str]) -> dict[str, Any]:
    payload = {
        "companyNames": names,
        "existEmail": 1,
        "sourceNames": ["depth_company", "linkedin"],
        "sort": 0,
        "isExact": False,
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "upkuajing-tape-masking-film-leads/0.1",
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    targets = target_companies(master)
    projected = PREVIOUS_PROJECT_SPEND_CENTS + SEARCH_COST_CENTS
    print(
        f"Companies without status=1 email: {len(targets)}\n"
        f"One-page people search cost: ¥{SEARCH_COST_CENTS / 100:.2f}\n"
        f"Projected project spend: ¥{projected / 100:.2f} / ¥{MAX_PROJECT_SPEND_CENTS / 100:.2f}"
    )
    if projected > MAX_PROJECT_SPEND_CENTS:
        raise SystemExit("Search blocked: projected project spend exceeds cap")
    if RAW_PATH.exists():
        saved = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        print(f"Saved response exists; no paid call. People: {len((saved.get('data') or {}).get('list') or [])}")
        return
    if not args.execute:
        print("Dry run only. Add --execute to call the paid search endpoint.")
        return
    api_key = os.environ.get("UPKUAJING_API_KEY", "")
    if not api_key:
        raise SystemExit("UPKUAJING_API_KEY is required with --execute")
    response = paid_search(api_key, [row["company_name"] for row in targets])
    actual_cost = int((response.get("fee") or {}).get("apiCost") or 0)
    if PREVIOUS_PROJECT_SPEND_CENTS + actual_cost > MAX_PROJECT_SPEND_CENTS:
        raise RuntimeError("Provider charge exceeded the project budget cap")
    RAW_PATH.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    people = (response.get("data") or {}).get("list") or []
    print(
        f"Saved {len(people)} people; actual cost ¥{actual_cost / 100:.2f}; "
        f"project total ¥{(PREVIOUS_PROJECT_SPEND_CENTS + actual_cost) / 100:.2f}"
    )


if __name__ == "__main__":
    main()
