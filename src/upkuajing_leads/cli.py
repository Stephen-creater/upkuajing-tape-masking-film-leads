"""Command line entry point."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .client import UpKuajingClient, UpKuajingError
from .core import Budget, BudgetExceeded, build_rows, export_rows, matches_product


# Deliberately higher than the observed prices (¥1.50/search, ¥1/contact)
# so the budget guard retains headroom if the provider adjusts pricing.
SEARCH_ESTIMATE_CENTS = 200
CONTACT_ESTIMATE_CENTS = 150


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find tape and masking-film buyers through UpKuajing OpenAPI."
    )
    parser.add_argument(
        "--products", nargs="+", default=["tape", "masking film"], help="Product terms"
    )
    parser.add_argument(
        "--contacts-per-product",
        type=int,
        default=3,
        help="Top matching companies whose contacts will be fetched (1-20)",
    )
    parser.add_argument(
        "--max-cost-cny",
        type=float,
        default=50.0,
        help="Hard API spend cap for this run (default: 50)",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually call the paid APIs; without this flag only prints an estimate",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    if not 1 <= args.contacts_per_product <= 20:
        raise ValueError("--contacts-per-product must be between 1 and 20")
    if not 0 < args.max_cost_cny <= 50:
        raise ValueError("--max-cost-cny must be greater than 0 and no more than 50")

    estimate_cents = len(args.products) * (
        SEARCH_ESTIMATE_CENTS + args.contacts_per_product * CONTACT_ESTIMATE_CENTS
    )
    print(
        f"Products: {', '.join(args.products)}\n"
        f"Conservative maximum estimate: ¥{estimate_cents / 100:.2f}\n"
        f"Run cap: ¥{args.max_cost_cny:.2f}"
    )
    if estimate_cents > round(args.max_cost_cny * 100):
        raise BudgetExceeded("Planned run is above the configured cost cap")
    if not args.execute:
        print("Dry run only. Add --execute to call paid APIs.")
        return 0

    api_key = os.environ.get("UPKUAJING_API_KEY", "")
    if not api_key:
        raise ValueError("Set UPKUAJING_API_KEY before using --execute")

    client = UpKuajingClient(api_key)
    budget = Budget(limit_cents=round(args.max_cost_cny * 100))
    all_rows: list[dict[str, object]] = []

    for product in args.products:
        budget.authorize(SEARCH_ESTIMATE_CENTS)
        search_result = client.search_buyers(product)
        budget.record(search_result.cost_cents)
        companies = search_result.data.get("list") or []
        matched = [item for item in companies if matches_product(item, product)]
        selected = matched[: args.contacts_per_product]
        print(
            f"{product}: API returned {len(companies)}, strict filter kept "
            f"{len(matched)}, fetching {len(selected)} contacts"
        )
        if not selected:
            continue

        budget.authorize(CONTACT_ESTIMATE_CENTS * len(selected))
        contact_result = client.get_company_contacts(
            [int(item["companyId"]) for item in selected]
        )
        budget.record(contact_result.cost_cents)
        contacts = contact_result.data.get("list") or []
        all_rows.extend(build_rows(product, selected, contacts))

    csv_path, json_path = export_rows(all_rows, args.output_dir, budget.spent_cents)
    with_email = sum(bool(row.get("emails")) for row in all_rows)
    print(
        f"Done: {len(all_rows)} leads, {with_email} with email values, "
        f"actual API cost ¥{budget.spent_cents / 100:.2f}\n"
        f"CSV: {csv_path}\nJSON: {json_path}"
    )
    return 0


def main() -> None:
    try:
        raise SystemExit(run(build_parser().parse_args()))
    except (ValueError, BudgetExceeded, UpKuajingError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()

