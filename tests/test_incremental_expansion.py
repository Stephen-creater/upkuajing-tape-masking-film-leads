import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("expand_to_target", ROOT / "scripts" / "expand_to_target.py")
EXPAND = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(EXPAND)


class IncrementalExpansionTests(unittest.TestCase):
    def test_strict_phrase_filter_rejects_unrelated_film(self):
        self.assertFalse(EXPAND.matches_product({"productDesc": "THICK FILM RESISTOR"}, "masking film"))
        self.assertTrue(EXPAND.matches_product({"productDesc": "PE MASKING-FILM ROLLS"}, "masking film"))

    def test_contact_response_promotes_only_status_one(self):
        candidates = {"companies": [
            EXPAND.blank_candidate({"companyId": 1, "name": "Valid", "countryCode": "US"}, EXPAND.PRODUCTS["tape"], "test"),
            EXPAND.blank_candidate({"companyId": 2, "name": "Invalid", "countryCode": "US"}, EXPAND.PRODUCTS["tape"], "test"),
        ]}
        response = {"data": {"list": [
            {"companyId": 1, "contact_data": {"emails": [{"val": "a@example.com", "is_valid": 1}], "phones": [], "websites": [], "socials": []}},
            {"companyId": 2, "contact_data": {"emails": [{"val": "b@example.com", "is_valid": 3}], "phones": [], "websites": [], "socials": []}},
        ]}}
        self.assertEqual(EXPAND.apply_contacts(candidates, response), 2)
        self.assertTrue(EXPAND.has_valid_contact(candidates["companies"][0]))
        self.assertFalse(EXPAND.has_valid_contact(candidates["companies"][1]))

    def test_valid_phone_from_contact_response_counts(self):
        row = EXPAND.blank_candidate({"companyId": 1, "name": "Phone", "countryCode": "CA"}, EXPAND.PRODUCTS["tape"], "test")
        candidates = {"companies": [row]}
        response = {"data": {"list": [{"companyId": 1, "contact_data": {
            "emails": [], "phones": [{"val": "14165550123", "international_number": "+1 416-555-0123", "is_valid": 1, "phone_type": 3, "is_ws": 2}],
            "websites": [], "socials": [],
        }}]}}
        EXPAND.apply_contacts(candidates, response)
        self.assertTrue(EXPAND.has_valid_contact(row))
        self.assertIn(":状态1/", row["phone_statuses"])

    def test_campaign_filter_excludes_previous_products(self):
        self.assertFalse(EXPAND.is_campaign_company({"categories": "胶带; 遮蔽膜"}))
        self.assertTrue(EXPAND.is_campaign_company({"categories": "刷子; 羊毛刷"}))


if __name__ == "__main__":
    unittest.main()
