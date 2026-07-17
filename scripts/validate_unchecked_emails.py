#!/usr/bin/env python3
"""Validate every unchecked API email and merge results into company master data."""

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
RAW_PATH = (
    ROOT
    / "data"
    / "raw"
    / "upkuajing"
    / "2026-07-17"
    / "email-validity-check.json"
)
ENDPOINT = "https://openapi.upkuajing.com/agent/validation/email"

# Audited project spend before this validation step.
PREVIOUS_PROJECT_SPEND_CENTS = 4950
MAX_PROJECT_SPEND_CENTS = 10000
CURRENT_PRICE_PER_EMAIL_CENTS = 10


def split_values(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def parse_statuses(value: str) -> dict[str, int]:
    statuses: dict[str, int] = {}
    for item in split_values(value):
        email, separator, status = item.rpartition(":")
        if separator and status.isdigit():
            statuses[email.casefold()] = int(status)
    return statuses


def unchecked_emails(master: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for company in master["companies"]:
        statuses = parse_statuses(company.get("email_statuses", ""))
        for email in split_values(company.get("emails", "")):
            if statuses.get(email.casefold(), 0) == 0:
                values.append(email)
    return list(dict.fromkeys(values))


def request_validation(api_key: str, emails: list[str]) -> dict[str, Any]:
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"emails": emails}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "upkuajing-tape-masking-film-leads/0.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:500]}") from exc
    if payload.get("code") != 0:
        raise RuntimeError(f"API error {payload.get('code')}: {payload.get('msg')}")
    return payload


def apply_response(master: dict[str, Any], response: dict[str, Any]) -> dict[str, int]:
    results = {
        item["email"].casefold(): {
            "status": int(item.get("status", 3)),
            "reason": str(item.get("reason") or ""),
        }
        for item in (response.get("data") or {}).get("list") or []
    }
    counts = {"valid": 0, "invalid": 0, "unknown": 0, "unchecked": 0}
    for company in master["companies"]:
        existing = parse_statuses(company.get("email_statuses", ""))
        reasons: list[str] = split_values(company.get("email_validation_reasons", ""))
        rendered: list[str] = []
        for email in split_values(company.get("emails", "")):
            result = results.get(email.casefold())
            status = result["status"] if result else existing.get(email.casefold(), 0)
            rendered.append(f"{email}:{status}")
            if result and result["reason"]:
                reasons.append(f"{email}: {result['reason']}")
            if status == 1:
                counts["valid"] += 1
            elif status == 2:
                counts["invalid"] += 1
            elif status == 3:
                counts["unknown"] += 1
            else:
                counts["unchecked"] += 1
        company["email_statuses"] = "; ".join(rendered)
        company["email_validation_reasons"] = "; ".join(reasons)
        company["email_validation_source"] = (
            "UpKuajing /agent/validation/email (2026-07-17)"
        )
        statuses = [int(item.rpartition(":")[2]) for item in rendered]
        if 1 in statuses:
            company["email_validation_summary"] = "有有效邮箱"
        elif 3 in statuses:
            company["email_validation_summary"] = "验证不确定-需官网补充"
        elif 2 in statuses:
            company["email_validation_summary"] = "无有效邮箱-需官网补充"
        else:
            company["email_validation_summary"] = "尚未完成验证"
    return counts


def save_master(master: dict[str, Any]) -> None:
    MASTER_PATH.write_text(
        json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    emails = unchecked_emails(master)
    expected_cost = len(emails) * CURRENT_PRICE_PER_EMAIL_CENTS
    projected_total = PREVIOUS_PROJECT_SPEND_CENTS + expected_cost
    print(
        f"Unchecked unique emails: {len(emails)}\n"
        f"Expected validation cost: ¥{expected_cost / 100:.2f}\n"
        f"Projected project spend: ¥{projected_total / 100:.2f} / "
        f"¥{MAX_PROJECT_SPEND_CENTS / 100:.2f}"
    )
    if projected_total > MAX_PROJECT_SPEND_CENTS:
        raise SystemExit("Validation blocked: projected project spend exceeds cap")

    if RAW_PATH.exists():
        response = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        counts = apply_response(master, response)
        save_master(master)
        print(f"Applied saved response without a paid call: {counts}")
        return
    if not args.execute:
        print("Dry run only. Add --execute to call the paid validation endpoint.")
        return

    api_key = os.environ.get("UPKUAJING_API_KEY", "")
    if not api_key:
        raise SystemExit("UPKUAJING_API_KEY is required with --execute")
    response = request_validation(api_key, emails)
    actual_cost = int((response.get("fee") or {}).get("apiCost") or 0)
    if PREVIOUS_PROJECT_SPEND_CENTS + actual_cost > MAX_PROJECT_SPEND_CENTS:
        raise RuntimeError("Provider charge exceeded the project budget cap")
    RAW_PATH.write_text(
        json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    counts = apply_response(master, response)
    save_master(master)
    print(
        f"Validated {len(emails)} emails; actual cost ¥{actual_cost / 100:.2f}; "
        f"project total ¥{(PREVIOUS_PROJECT_SPEND_CENTS + actual_cost) / 100:.2f}\n"
        f"Result counts: {counts}"
    )


if __name__ == "__main__":
    main()
