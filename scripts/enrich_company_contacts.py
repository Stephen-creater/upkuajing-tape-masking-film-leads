#!/usr/bin/env python3
"""Fetch missing company contacts without exceeding the remaining API budget."""

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
RAW_DIR = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17"
ENDPOINT = "https://openapi.upkuajing.com/agent/customs/company/contact/batch"
MAX_REMAINING_BUDGET_CNY = 29.50
OBSERVED_CONTACT_COST_CENTS = 100


def load_master() -> dict[str, Any]:
    return json.loads(MASTER_PATH.read_text(encoding="utf-8"))


def join_values(items: list[dict[str, Any]], key: str) -> str:
    return "; ".join(
        dict.fromkeys(str(item.get(key) or "").strip() for item in items if item.get(key))
    )


def apply_contacts(master: dict[str, Any], response: dict[str, Any]) -> int:
    companies = {int(row["company_id"]): row for row in master["companies"]}
    applied = 0
    for item in (response.get("data") or {}).get("list") or []:
        company_id = int(item["companyId"])
        if company_id not in companies:
            continue
        row = companies[company_id]
        contact = item.get("contact_data") or {}
        emails = contact.get("emails") or []
        phones = contact.get("phones") or []
        websites = contact.get("websites") or []
        socials = contact.get("socials") or []
        row["emails"] = join_values(emails, "val")
        row["email_statuses"] = "; ".join(
            f"{entry.get('val', '')}:{entry.get('is_valid', 0)}"
            for entry in emails
            if entry.get("val")
        )
        row["phones"] = "; ".join(
            dict.fromkeys(
                str(entry.get("international_number") or entry.get("val") or "").strip()
                for entry in phones
                if entry.get("international_number") or entry.get("val")
            )
        )
        row["whatsapp"] = "; ".join(
            dict.fromkeys(
                str(entry.get("international_number") or entry.get("val") or "").strip()
                for entry in phones
                if entry.get("is_ws") == 1
                and (entry.get("international_number") or entry.get("val"))
            )
        )
        row["websites"] = join_values(websites, "val")
        row["socials"] = join_values(socials, "val")
        row["contact_source"] = "UpKuajing customs company contact API"
        has_contact = any(
            row.get(key) for key in ("emails", "phones", "websites", "socials")
        )
        row["research_status"] = (
            "API联系方式已获取" if has_contact else "API无公开联系方式-待官网追溯"
        )
        applied += 1
    return applied


def apply_saved_responses(master: dict[str, Any]) -> int:
    applied = 0
    for path in sorted(RAW_DIR.glob("company-contacts-batch-*.json")):
        applied += apply_contacts(master, json.loads(path.read_text(encoding="utf-8")))
    return applied


def paid_request(api_key: str, company_ids: list[int]) -> dict[str, Any]:
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"companyIds": company_ids}).encode("utf-8"),
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


def save_master(master: dict[str, Any]) -> None:
    MASTER_PATH.write_text(
        json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-cost-cny", type=float, default=MAX_REMAINING_BUDGET_CNY)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0 < args.max_cost_cny <= MAX_REMAINING_BUDGET_CNY:
        raise SystemExit(
            f"--max-cost-cny must be between 0 and {MAX_REMAINING_BUDGET_CNY:.2f}"
        )

    master = load_master()
    resumed = apply_saved_responses(master)
    missing = [row for row in master["companies"] if not row.get("contact_source")]
    expected_cents = len(missing) * OBSERVED_CONTACT_COST_CENTS
    limit_cents = round(args.max_cost_cny * 100)
    print(
        f"Existing raw responses applied: {resumed}\n"
        f"Companies still missing API contact lookup: {len(missing)}\n"
        f"Expected cost at observed rate: ¥{expected_cents / 100:.2f}\n"
        f"This-run cap: ¥{limit_cents / 100:.2f}"
    )
    if not args.execute:
        print("Dry run only. Add --execute to call the paid endpoint.")
        return
    api_key = os.environ.get("UPKUAJING_API_KEY", "")
    if not api_key:
        raise SystemExit("UPKUAJING_API_KEY is required with --execute")

    spent_cents = 0
    batch_number = len(list(RAW_DIR.glob("company-contacts-batch-*.json"))) + 1
    while missing:
        affordable = (limit_cents - spent_cents) // OBSERVED_CONTACT_COST_CENTS
        if affordable < 1:
            break
        batch = missing[: min(20, affordable)]
        response = paid_request(api_key, [int(row["company_id"]) for row in batch])
        actual_cents = int((response.get("fee") or {}).get("apiCost") or 0)
        if spent_cents + actual_cents > limit_cents:
            raise RuntimeError(
                "Provider charge exceeded the preflight estimate; stopping immediately"
            )
        raw_path = RAW_DIR / f"company-contacts-batch-{batch_number:02d}.json"
        if raw_path.exists():
            raise RuntimeError(f"Refusing to overwrite existing raw response: {raw_path}")
        raw_path.write_text(
            json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        applied = apply_contacts(master, response)
        save_master(master)
        spent_cents += actual_cents
        unit_cost = actual_cents / max(applied, 1)
        print(
            f"Batch {batch_number}: requested {len(batch)}, applied {applied}, "
            f"cost ¥{actual_cents / 100:.2f}, observed ¥{unit_cost / 100:.2f}/company"
        )
        missing = [row for row in master["companies"] if not row.get("contact_source")]
        batch_number += 1

    print(
        f"Finished: spent ¥{spent_cents / 100:.2f}; "
        f"remaining companies without API lookup: {len(missing)}"
    )


if __name__ == "__main__":
    main()
