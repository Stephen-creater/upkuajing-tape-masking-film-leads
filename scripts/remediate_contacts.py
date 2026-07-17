#!/usr/bin/env python3
"""Validate web-researched email candidates and reuse duplicate-entity contacts."""

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
PLAN_PATH = ROOT / "data" / "raw" / "web" / "2026-07-17" / "contact-remediation-plan.json"
RESPONSE_PATH = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "email-remediation-validity-check.json"
ENDPOINT = "https://openapi.upkuajing.com/agent/validation/email"
PREVIOUS_PROJECT_SPEND_CENTS = 5170
MAX_PROJECT_SPEND_CENTS = 10000
PRICE_PER_EMAIL_CENTS = 10


def split_values(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def join_values(*groups: list[str]) -> str:
    values = [value.strip() for group in groups for value in group if value.strip()]
    return "; ".join(dict.fromkeys(values))


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


def apply_results(master: dict[str, Any], plan: dict[str, Any], response: dict[str, Any]) -> dict[str, int]:
    by_id = {int(row["company_id"]): row for row in master["companies"]}
    results = {
        item["email"].casefold(): {
            "status": int(item.get("status", 3)),
            "reason": str(item.get("reason") or ""),
        }
        for item in (response.get("data") or {}).get("list") or []
    }
    counts = {"valid": 0, "invalid": 0, "unknown": 0}

    for candidate in plan["candidates"]:
        row = by_id[int(candidate["company_id"])]
        email = candidate["email"]
        result = results[email.casefold()]
        status = result["status"]
        label = {1: "valid", 2: "invalid", 3: "unknown"}.get(status, "unknown")
        counts[label] += 1
        row["email_statuses"] = join_values(
            split_values(row.get("email_statuses", "")), [f"{email}:{status}"]
        )
        row["website_emails"] = join_values(
            split_values(row.get("website_emails", "")), [email]
        )
        if status == 1:
            row["email_validation_summary"] = "有有效邮箱"
            row["research_status"] = "官网/权威来源补充有效邮箱"
        elif status == 3 and "有有效邮箱" not in row.get("email_validation_summary", ""):
            row["email_validation_summary"] = "验证不确定-已有权威来源佐证"
        row["website_research_source"] = join_values(
            split_values(row.get("website_research_source", "")), [candidate["source"]]
        )
        row["website_phones"] = join_values(
            split_values(row.get("website_phones", "")), candidate.get("phones") or []
        )
        row["whatsapp"] = join_values(
            split_values(row.get("whatsapp", "")), candidate.get("whatsapp") or []
        )
        note = f"{candidate['source_quality']}；{candidate['notes']} 验证状态={status}。"
        row["website_research_notes"] = join_values(
            split_values(row.get("website_research_notes", "")), [note]
        )
        if result["reason"]:
            row["email_validation_reasons"] = join_values(
                split_values(row.get("email_validation_reasons", "")),
                [f"{email}: {result['reason']}"],
            )

    for reuse in plan["entity_reuse"]:
        row = by_id[int(reuse["company_id"])]
        emails = reuse["emails"]
        row["website_emails"] = join_values(
            split_values(row.get("website_emails", "")), emails
        )
        row["email_statuses"] = join_values(
            split_values(row.get("email_statuses", "")),
            [f"{email}:1" for email in emails],
        )
        row["email_validation_summary"] = "有有效邮箱-同法人实体复用"
        row["research_status"] = "同法人实体已去重-复用有效邮箱"
        row["website_research_source"] = join_values(
            split_values(row.get("website_research_source", "")), [reuse["source"]]
        )
        row["website_research_notes"] = join_values(
            split_values(row.get("website_research_notes", "")), [reuse["notes"]]
        )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    emails = list(dict.fromkeys(item["email"] for item in plan["candidates"]))
    projected = PREVIOUS_PROJECT_SPEND_CENTS + len(emails) * PRICE_PER_EMAIL_CENTS
    print(
        f"Candidate emails: {len(emails)}\n"
        f"Expected validation cost: ¥{len(emails) * PRICE_PER_EMAIL_CENTS / 100:.2f}\n"
        f"Projected project spend: ¥{projected / 100:.2f} / ¥{MAX_PROJECT_SPEND_CENTS / 100:.2f}"
    )
    if projected > MAX_PROJECT_SPEND_CENTS:
        raise SystemExit("Remediation blocked: projected project spend exceeds cap")
    if RESPONSE_PATH.exists():
        response = json.loads(RESPONSE_PATH.read_text(encoding="utf-8"))
        counts = apply_results(master, plan, response)
        MASTER_PATH.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
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
    RESPONSE_PATH.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = apply_results(master, plan, response)
    MASTER_PATH.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Validated {len(emails)} candidates; actual cost ¥{actual_cost / 100:.2f}; "
        f"project total ¥{(PREVIOUS_PROJECT_SPEND_CENTS + actual_cost) / 100:.2f}\n"
        f"Result counts: {counts}"
    )


if __name__ == "__main__":
    main()
