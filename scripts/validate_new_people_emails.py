#!/usr/bin/env python3
"""Validate newly added person emails still marked unchecked."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from validate_unchecked_emails import apply_response, request_validation, unchecked_emails


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "processed" / "company-master.json"
RAW_PATH = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "people-email-validity-check.json"
PREVIOUS_PROJECT_SPEND_CENTS = 7490
MAX_PROJECT_SPEND_CENTS = 10000
PRICE_PER_EMAIL_CENTS = 10


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    emails = unchecked_emails(master)
    projected = PREVIOUS_PROJECT_SPEND_CENTS + len(emails) * PRICE_PER_EMAIL_CENTS
    print(
        f"New unchecked person emails: {len(emails)}\n"
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
        response = request_validation(api_key, emails)
        actual = int((response.get("fee") or {}).get("apiCost") or 0)
        if PREVIOUS_PROJECT_SPEND_CENTS + actual > MAX_PROJECT_SPEND_CENTS:
            raise RuntimeError("Provider charge exceeded the project budget cap")
        RAW_PATH.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = apply_response(master, response)
    MASTER_PATH.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
    actual = int((response.get("fee") or {}).get("apiCost") or 0)
    print(f"Validated {len(emails)} emails; cost ¥{actual / 100:.2f}; all-email counts {counts}")


if __name__ == "__main__":
    main()
