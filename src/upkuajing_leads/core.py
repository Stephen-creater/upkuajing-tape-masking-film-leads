"""Filtering, budget control, and export helpers."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class BudgetExceeded(RuntimeError):
    """Raised before a request whose conservative estimate exceeds the cap."""


@dataclass
class Budget:
    limit_cents: int
    spent_cents: int = 0

    def authorize(self, estimated_cents: int) -> None:
        if estimated_cents < 0:
            raise ValueError("estimated_cents cannot be negative")
        if self.spent_cents + estimated_cents > self.limit_cents:
            raise BudgetExceeded(
                f"Request blocked: estimated total would be "
                f"¥{(self.spent_cents + estimated_cents) / 100:.2f}, "
                f"above the ¥{self.limit_cents / 100:.2f} cap"
            )

    def record(self, actual_cents: int) -> None:
        if actual_cents < 0:
            raise ValueError("actual_cents cannot be negative")
        self.spent_cents += actual_cents
        if self.spent_cents > self.limit_cents:
            raise BudgetExceeded(
                "The provider charged more than the conservative preflight estimate; "
                f"stop now (spent ¥{self.spent_cents / 100:.2f})."
            )


def matches_product(company: dict[str, Any], product: str) -> bool:
    fields: list[str] = [
        str(company.get("productDesc") or ""),
        *(str(value) for value in company.get("productNames") or []),
        *(str(value) for value in company.get("productTags") or []),
    ]
    haystack = " ".join(fields).casefold()
    words = [re.escape(word) for word in product.casefold().split()]
    pattern = r"\b" + r"[\s\-_/.]*".join(words) + r"\b"
    return bool(re.search(pattern, haystack))


def flatten_contact(contact: dict[str, Any]) -> dict[str, str]:
    data = contact.get("contact_data") or {}
    emails = data.get("emails") or []
    phones = data.get("phones") or []
    websites = data.get("websites") or []
    socials = data.get("socials") or []
    return {
        "emails": "; ".join(item.get("val", "") for item in emails if item.get("val")),
        "email_statuses": "; ".join(
            f"{item.get('val', '')}:{item.get('is_valid', 0)}"
            for item in emails
            if item.get("val")
        ),
        "phones": "; ".join(
            item.get("international_number") or item.get("val", "")
            for item in phones
            if item.get("international_number") or item.get("val")
        ),
        "websites": "; ".join(item.get("val", "") for item in websites if item.get("val")),
        "socials": "; ".join(item.get("val", "") for item in socials if item.get("val")),
    }


CSV_FIELDS = [
    "product",
    "company_id",
    "company_name",
    "country_code",
    "trade_match_total",
    "latest_trade_date",
    "product_names",
    "product_description",
    "emails",
    "email_statuses",
    "phones",
    "websites",
    "socials",
]


def build_rows(
    product: str,
    companies: Iterable[dict[str, Any]],
    contacts: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    contacts_by_id = {int(item["companyId"]): flatten_contact(item) for item in contacts}
    rows: list[dict[str, Any]] = []
    for company in companies:
        company_id = int(company["companyId"])
        row: dict[str, Any] = {
            "product": product,
            "company_id": company_id,
            "company_name": company.get("name", ""),
            "country_code": company.get("countryCode", ""),
            "trade_match_total": company.get("tradeMatchTotal", ""),
            "latest_trade_date": company.get("latestTradeDate", ""),
            "product_names": "; ".join(company.get("productNames") or []),
            "product_description": company.get("productDesc", ""),
            "emails": "",
            "email_statuses": "",
            "phones": "",
            "websites": "",
            "socials": "",
        }
        row.update(contacts_by_id.get(company_id, {}))
        rows.append(row)
    return rows


def export_rows(rows: list[dict[str, Any]], output_dir: Path, spent_cents: int) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    csv_path = output_dir / f"leads-{stamp}.csv"
    json_path = output_dir / f"leads-{stamp}.json"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "api_cost_cny": spent_cents / 100,
                "lead_count": len(rows),
                "leads": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return csv_path, json_path

