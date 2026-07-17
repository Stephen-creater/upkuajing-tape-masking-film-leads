import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "processed" / "company-master.json"


def split_values(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def valid_emails(company: dict) -> set[str]:
    statuses = {}
    for item in split_values(company.get("email_statuses", "")):
        email, separator, status = item.rpartition(":")
        if separator:
            statuses[email.lower()] = int(status)
    candidates = split_values(company.get("website_emails", "")) + split_values(company.get("emails", ""))
    return {email.lower() for email in candidates if statuses.get(email.lower()) == 1}


def has_valid_phone(company: dict) -> bool:
    return any(":状态1/" in item for item in split_values(company.get("phone_statuses", "")))


class MasterMetricsTests(unittest.TestCase):
    def test_authoritative_master_contains_only_unique_contactable_companies(self):
        master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
        companies = master["companies"]
        emails_by_company = [valid_emails(company) for company in companies]
        has_email = [bool(emails) for emails in emails_by_company]
        has_phone = [has_valid_phone(company) for company in companies]

        self.assertEqual(master["company_count"], len(companies))
        self.assertEqual(len(companies), 250)
        self.assertEqual(len({int(company["company_id"]) for company in companies}), len(companies))
        self.assertEqual(
            sum(email or phone for email, phone in zip(has_email, has_phone)),
            len(companies),
        )
        self.assertEqual(sum(not email and not phone for email, phone in zip(has_email, has_phone)), 0)

    def test_business_scope_is_fully_localized_for_workbook(self):
        master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
        for company in master["companies"]:
            localized = str(company.get("business_scope_zh", "")).strip()
            self.assertTrue(localized, f"公司 {company['company_id']} 缺少中文经营范围")
            self.assertIsNone(
                re.search(r"[A-Za-z]", localized),
                f"公司 {company['company_id']} 的中文经营范围仍含外文：{localized}",
            )


if __name__ == "__main__":
    unittest.main()
