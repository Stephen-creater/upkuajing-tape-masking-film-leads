#!/usr/bin/env python3
"""Merge reviewed person contacts into the one-row-per-company master."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "processed" / "company-master.json"
SELECTION_PATH = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "people-recovery-selection.json"
CONTACTS_PATH = ROOT / "data" / "raw" / "upkuajing" / "2026-07-17" / "people-recovery-contacts.json"

# Domain conflicts show an old/other employer and must not be attributed to the target company.
EXCLUDED_EMAILS = {"madhumay.panigrahi@havells.com": "邮箱域名属于 Havells，与当前 Haier 实体不一致"}


def split_values(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def join_values(*groups: list[str]) -> str:
    return "; ".join(dict.fromkeys(value for group in groups for value in group if value))


def apply(master: dict[str, Any], selection: dict[str, Any], contacts: dict[str, Any]) -> dict[str, int]:
    rows = {int(row["company_id"]): row for row in master["companies"]}
    selected = {item["hid"]: item for item in selection["people"]}
    counts = {"included": 0, "excluded": 0, "valid": 0, "invalid": 0, "unchecked": 0}
    for result in (contacts.get("data") or {}).get("list") or []:
        person = selected[result["bus_id"]]
        row = rows[int(person["company_id"])]
        emails: list[str] = []
        statuses: list[str] = []
        exclusions: list[str] = []
        for entry in (result.get("contact_data") or {}).get("emails") or []:
            email = str(entry.get("val") or "").strip()
            if not email:
                continue
            if email.casefold() in EXCLUDED_EMAILS:
                counts["excluded"] += 1
                exclusions.append(f"排除 {email}：{EXCLUDED_EMAILS[email.casefold()]}")
                continue
            status = int(entry.get("is_valid") or 0)
            emails.append(email)
            statuses.append(f"{email}:{status}")
            counts["included"] += 1
            counts[{1: "valid", 2: "invalid"}.get(status, "unchecked")] += 1
        socials = [
            str(entry.get("val") or "").strip()
            for entry in (result.get("contact_data") or {}).get("socials") or []
            if entry.get("val")
        ]
        row["emails"] = join_values(split_values(row.get("emails", "")), emails)
        row["email_statuses"] = join_values(split_values(row.get("email_statuses", "")), statuses)
        row["socials"] = join_values(split_values(row.get("socials", "")), socials)
        row["contact_source"] = join_values(
            split_values(row.get("contact_source", "")), ["UpKuajing reviewed person contact API"]
        )
        note = f"人物补充：{person['name']}（{person['title']}）；{person['reason']}。"
        if exclusions:
            note += " " + " ".join(exclusions)
        row["website_research_notes"] = join_values(
            split_values(row.get("website_research_notes", "")), [note]
        )
        if any(item.endswith(":1") for item in statuses):
            row["email_validation_summary"] = "有有效邮箱-人物补充"
            row["research_status"] = "已补充有效决策人邮箱"
    return counts


def main() -> None:
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    contacts = json.loads(CONTACTS_PATH.read_text(encoding="utf-8"))
    counts = apply(master, selection, contacts)
    MASTER_PATH.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Applied reviewed people contacts: {counts}")


if __name__ == "__main__":
    main()
