import tempfile
import unittest
from pathlib import Path

from upkuajing_leads.core import (
    Budget,
    BudgetExceeded,
    build_rows,
    export_rows,
    matches_product,
)


class ProductMatcherTests(unittest.TestCase):
    def test_masking_film_matches_phrase(self):
        company = {"productDesc": "ROLLS OF POLYETHYLENE MASKING FILM"}
        self.assertTrue(matches_product(company, "masking film"))

    def test_masking_film_rejects_thick_film(self):
        company = {"productDesc": "0402 THICK FILM RESISTOR"}
        self.assertFalse(matches_product(company, "masking film"))

    def test_tape_matches_product_name(self):
        company = {"productNames": ["Rubber Tape"]}
        self.assertTrue(matches_product(company, "tape"))


class BudgetTests(unittest.TestCase):
    def test_blocks_request_before_cap_is_exceeded(self):
        budget = Budget(limit_cents=5000, spent_cents=4800)
        with self.assertRaises(BudgetExceeded):
            budget.authorize(300)

    def test_records_actual_cost(self):
        budget = Budget(limit_cents=5000)
        budget.authorize(200)
        budget.record(150)
        self.assertEqual(budget.spent_cents, 150)


class ExportTests(unittest.TestCase):
    def test_build_and_export_rows(self):
        companies = [
            {
                "companyId": 1,
                "name": "Example Buyer",
                "countryCode": "US",
                "productNames": ["Masking Film"],
            }
        ]
        contacts = [
            {
                "companyId": 1,
                "contact_data": {
                    "emails": [{"val": "buyer@example.com", "is_valid": 1}],
                    "phones": [],
                    "websites": [],
                    "socials": [],
                },
            }
        ]
        rows = build_rows("masking film", companies, contacts)
        self.assertEqual(rows[0]["emails"], "buyer@example.com")
        with tempfile.TemporaryDirectory() as directory:
            csv_path, json_path = export_rows(rows, Path(directory), 250)
            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())


if __name__ == "__main__":
    unittest.main()

