#!/usr/bin/env python3
"""Fetch contacts only for manually reviewed, exact-company people matches."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELECTION_PATH = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "people-recovery-selection.json"
RAW_PATH = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "people-recovery-contacts.json"
ENDPOINT = "https://openapi.upkuajing.com/agent/search/contact/batch"
PREVIOUS_PROJECT_SPEND_CENTS = 7190
PRICE_PER_PERSON_CENTS = 100
MAX_PROJECT_SPEND_CENTS = 10000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    ids = [item["hid"] for item in selection["people"]]
    projected = PREVIOUS_PROJECT_SPEND_CENTS + len(ids) * PRICE_PER_PERSON_CENTS
    print(
        f"Reviewed people: {len(ids)}\n"
        f"Expected contact cost: ¥{len(ids) * PRICE_PER_PERSON_CENTS / 100:.2f}\n"
        f"Projected project spend: ¥{projected / 100:.2f} / ¥{MAX_PROJECT_SPEND_CENTS / 100:.2f}"
    )
    if projected > MAX_PROJECT_SPEND_CENTS:
        raise SystemExit("Contact lookup blocked: projected project spend exceeds cap")
    if RAW_PATH.exists():
        saved = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        print(f"Saved response exists; no paid call. Cost ¥{int((saved.get('fee') or {}).get('apiCost') or 0) / 100:.2f}")
        return
    if not args.execute:
        print("Dry run only. Add --execute to call the paid endpoint.")
        return
    api_key = os.environ.get("UPKUAJING_API_KEY", "")
    if not api_key:
        raise SystemExit("UPKUAJING_API_KEY is required with --execute")
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"bus_ids": ids, "bus_type": 2}).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("code") != 0:
        raise RuntimeError(f"API error {result.get('code')}: {result.get('msg')}")
    actual = int((result.get("fee") or {}).get("apiCost") or 0)
    if PREVIOUS_PROJECT_SPEND_CENTS + actual > MAX_PROJECT_SPEND_CENTS:
        raise RuntimeError("Provider charge exceeded the project budget cap")
    RAW_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved contacts for {len(ids)} people; cost ¥{actual / 100:.2f}; project total ¥{(PREVIOUS_PROJECT_SPEND_CENTS + actual) / 100:.2f}")


if __name__ == "__main__":
    main()
