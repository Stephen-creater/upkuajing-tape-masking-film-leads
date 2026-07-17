#!/usr/bin/env python3
"""Apply auditable website research to the one-row-per-company master."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "processed" / "company-master.json"
RESEARCH_PATH = (
    ROOT / "data" / "raw" / "web" / "2026-07-17" / "western-contact-verification.json"
)


def join(values: list[str]) -> str:
    return "; ".join(dict.fromkeys(value.strip() for value in values if value.strip()))


def main() -> None:
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    research = json.loads(RESEARCH_PATH.read_text(encoding="utf-8"))
    by_id = {int(row["company_id"]): row for row in master["companies"]}

    for item in research["companies"]:
        row = by_id[int(item["company_id"])]
        row["website_emails"] = join(item.get("website_emails") or [])
        row["website_phones"] = join(item.get("website_phones") or [])
        row["website_address"] = item.get("website_address", "")
        row["website_contact_method"] = item.get("contact_method", "")
        row["website_research_source"] = join(
            [item.get("contact_page", ""), item.get("additional_source", "")]
        )
        row["website_research_notes"] = item.get("verification_result", "")
        if item["company_id"] == 209484:
            row["research_status"] = "官网已核验-API邮箱已确认"
        elif item["company_id"] == 71495262:
            row["research_status"] = "官网已补充客服邮箱与电话"
        else:
            row["research_status"] = "官网已核验-仅表单与电话"

    for row in master["companies"]:
        row.setdefault("website_emails", "")
        row.setdefault("website_phones", "")
        row.setdefault("website_address", "")
        row.setdefault("website_contact_method", "")

    MASTER_PATH.write_text(
        json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Applied website research for {len(research['companies'])} companies")


if __name__ == "__main__":
    main()
