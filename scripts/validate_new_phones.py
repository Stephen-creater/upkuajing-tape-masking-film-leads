#!/usr/bin/env python3
"""Validate authoritative phones added after the main phone-validation batch."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

from validate_phones import apply_response, split_values, unique_phones


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "processed" / "company-master.json"
RAW_PATH = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "incremental-phone-validity-check.json"
ENDPOINT = "https://openapi.upkuajing.com/agent/validation/phone"
PREVIOUS_PROJECT_SPEND_CENTS = 8080
MAX_PROJECT_SPEND_CENTS = 10000
PRICE_PER_PHONE_CENTS = 10


def recorded_phones(master: dict) -> set[str]:
    recorded: set[str] = set()
    for row in master["companies"]:
        for item in split_values(row.get("phone_statuses", "")):
            phone, separator, _ = item.partition(":状态")
            if separator:
                recorded.add(phone)
    return recorded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    recorded = recorded_phones(master)
    phones = [phone for phone in unique_phones(master) if phone not in recorded]
    projected = PREVIOUS_PROJECT_SPEND_CENTS + len(phones) * PRICE_PER_PHONE_CENTS
    print(
        f"New authoritative phones: {len(phones)}\n"
        f"Expected cost: ¥{len(phones) * PRICE_PER_PHONE_CENTS / 100:.2f}\n"
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
            data=json.dumps({"phones": phones}).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as http_response:
            response = json.loads(http_response.read().decode("utf-8"))
        if response.get("code") != 0:
            raise RuntimeError(f"API error {response.get('code')}: {response.get('msg')}")
        actual = int((response.get("fee") or {}).get("apiCost") or 0)
        if PREVIOUS_PROJECT_SPEND_CENTS + actual > MAX_PROJECT_SPEND_CENTS:
            raise RuntimeError("Provider charge exceeded the project budget cap")
        RAW_PATH.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    # Merge the incremental response with the main response before rebuilding every row.
    main_response = json.loads(
        (ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "phone-validity-check.json").read_text(encoding="utf-8")
    )
    combined = {"data": {"list": (main_response.get("data") or {}).get("list", []) + (response.get("data") or {}).get("list", [])}}
    counts = apply_response(master, combined)
    MASTER_PATH.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
    actual = int((response.get("fee") or {}).get("apiCost") or 0)
    print(f"Validated {len(phones)} new phones; cost ¥{actual / 100:.2f}; project total ¥{(PREVIOUS_PROJECT_SPEND_CENTS + actual) / 100:.2f}; {counts}")


if __name__ == "__main__":
    main()
