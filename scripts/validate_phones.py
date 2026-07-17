#!/usr/bin/env python3
"""Validate every unique API and official-website phone within the project cap."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "processed" / "company-master.json"
RAW_PATH = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "phone-validity-check.json"
ENDPOINT = "https://openapi.upkuajing.com/agent/validation/phone"
PREVIOUS_PROJECT_SPEND_CENTS = 7500
MAX_PROJECT_SPEND_CENTS = 10000
PRICE_PER_PHONE_CENTS = 10


def split_values(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def unique_phones(master: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for row in master["companies"]:
        values.extend(split_values(row.get("phones", "")))
        values.extend(split_values(row.get("website_phones", "")))
    return list(dict.fromkeys(values))


def apply_response(master: dict[str, Any], response: dict[str, Any]) -> dict[str, int]:
    results = {
        item["phone"]: item
        for item in (response.get("data") or {}).get("list") or []
    }
    counts = {"valid": 0, "invalid": 0, "unknown": 0, "unchecked": 0}
    for row in master["companies"]:
        rendered: list[str] = []
        statuses: list[int] = []
        for phone in list(dict.fromkeys(split_values(row.get("phones", "")) + split_values(row.get("website_phones", "")))):
            item = results.get(phone) or {}
            status = int(item.get("status") or 0)
            phone_type = int(item.get("phoneType") or 0)
            whatsapp = int(item.get("isWs") or 0)
            rendered.append(f"{phone}:状态{status}/类型{phone_type}/WhatsApp{whatsapp}")
            statuses.append(status)
            counts[{1: "valid", 2: "invalid", 3: "unknown"}.get(status, "unchecked")] += 1
        row["phone_statuses"] = "; ".join(rendered)
        if 1 in statuses:
            row["phone_validation_summary"] = "有有效电话"
        elif 3 in statuses:
            row["phone_validation_summary"] = "电话验证不确定"
        elif 2 in statuses:
            row["phone_validation_summary"] = "无有效电话"
        else:
            row["phone_validation_summary"] = "无电话或接口未检测"
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    phones = unique_phones(master)
    projected = PREVIOUS_PROJECT_SPEND_CENTS + len(phones) * PRICE_PER_PHONE_CENTS
    print(
        f"Unique phones: {len(phones)}\n"
        f"Expected cost: ¥{len(phones) * PRICE_PER_PHONE_CENTS / 100:.2f}\n"
        f"Projected project spend: ¥{projected / 100:.2f} / ¥{MAX_PROJECT_SPEND_CENTS / 100:.2f}"
    )
    if projected > MAX_PROJECT_SPEND_CENTS:
        raise SystemExit("Phone validation blocked: projected project spend exceeds cap")
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
    counts = apply_response(master, response)
    MASTER_PATH.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
    actual = int((response.get("fee") or {}).get("apiCost") or 0)
    print(f"Validated {len(phones)} phones; cost ¥{actual / 100:.2f}; project total ¥{(PREVIOUS_PROJECT_SPEND_CENTS + actual) / 100:.2f}; {counts}")


if __name__ == "__main__":
    main()
