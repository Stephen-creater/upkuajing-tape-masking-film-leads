#!/usr/bin/env python3
"""Validate official-website emails missing from the shared status ledger."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "processed" / "company-master.json"
RAW_PATH = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "website-email-validity-check.json"
ENDPOINT = "https://openapi.upkuajing.com/agent/validation/email"
PREVIOUS_PROJECT_SPEND_CENTS = 5370
MAX_PROJECT_SPEND_CENTS = 10000
PRICE_PER_EMAIL_CENTS = 10


def split_values(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def missing_website_emails(master: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for row in master["companies"]:
        recorded = {
            item.rsplit(":", 1)[0].strip().casefold()
            for item in split_values(row.get("email_statuses", ""))
            if ":" in item
        }
        result.extend(
            email for email in split_values(row.get("website_emails", ""))
            if email.casefold() not in recorded
        )
    return list(dict.fromkeys(result))


def apply_response(master: dict[str, Any], response: dict[str, Any]) -> dict[str, int]:
    results = {
        item["email"].casefold(): (int(item.get("status", 3)), str(item.get("reason") or ""))
        for item in (response.get("data") or {}).get("list") or []
    }
    counts = {"valid": 0, "invalid": 0, "unknown": 0}
    for row in master["companies"]:
        statuses = split_values(row.get("email_statuses", ""))
        reasons = split_values(row.get("email_validation_reasons", ""))
        for email in split_values(row.get("website_emails", "")):
            result = results.get(email.casefold())
            if not result:
                continue
            status, reason = result
            statuses.append(f"{email}:{status}")
            counts[{1: "valid", 2: "invalid", 3: "unknown"}.get(status, "unknown")] += 1
            if reason:
                reasons.append(f"{email}: {reason}")
        row["email_statuses"] = "; ".join(dict.fromkeys(statuses))
        row["email_validation_reasons"] = "; ".join(dict.fromkeys(reasons))
        if any(item.endswith(":1") for item in statuses):
            row["email_validation_summary"] = "有有效邮箱"
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    emails = missing_website_emails(master)
    projected = PREVIOUS_PROJECT_SPEND_CENTS + len(emails) * PRICE_PER_EMAIL_CENTS
    print(
        f"Unrecorded website emails: {len(emails)}\n"
        f"Expected cost: ¥{len(emails) * PRICE_PER_EMAIL_CENTS / 100:.2f}\n"
        f"Projected project spend: ¥{projected / 100:.2f} / ¥{MAX_PROJECT_SPEND_CENTS / 100:.2f}"
    )
    if projected > MAX_PROJECT_SPEND_CENTS:
        raise SystemExit("Validation blocked: projected project spend exceeds cap")
    if RAW_PATH.exists():
        response = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    elif not args.execute:
        print("Dry run only. Add --execute to call the paid endpoint.")
        return
    else:
        api_key = os.environ.get("UPKUAJING_API_KEY", "")
        if not api_key:
            raise SystemExit("UPKUAJING_API_KEY is required with --execute")
        request = urllib.request.Request(
            ENDPOINT,
            data=json.dumps({"emails": emails}).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as http_response:
            response = json.loads(http_response.read().decode("utf-8"))
        if response.get("code") != 0:
            raise RuntimeError(f"API error {response.get('code')}: {response.get('msg')}")
        RAW_PATH.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = apply_response(master, response)
    MASTER_PATH.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
    actual = int((response.get("fee") or {}).get("apiCost") or 0)
    print(f"Applied {len(emails)} website emails; cost ¥{actual / 100:.2f}; results {counts}")


if __name__ == "__main__":
    main()
