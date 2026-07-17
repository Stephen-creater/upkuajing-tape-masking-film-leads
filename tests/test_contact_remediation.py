import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from remediate_contacts import apply_results


class ContactRemediationTests(unittest.TestCase):
    def test_valid_candidate_and_duplicate_entity_are_applied(self):
        master = {
            "companies": [
                {"company_id": 1, "email_statuses": "old@example.com:2"},
                {"company_id": 2, "email_statuses": "person@example.com:3"},
            ]
        }
        plan = {
            "candidates": [
                {
                    "company_id": 1,
                    "email": "new@example.com",
                    "source": "https://example.com/contact",
                    "source_quality": "企业官网",
                    "notes": "官网联系人",
                }
            ],
            "entity_reuse": [
                {
                    "company_id": 2,
                    "same_entity_company_id": 3,
                    "emails": ["verified@example.com"],
                    "source": "同法人实体",
                    "notes": "已去重",
                }
            ],
        }
        response = {
            "data": {
                "list": [
                    {"email": "new@example.com", "status": 1, "reason": ""}
                ]
            }
        }

        counts = apply_results(master, plan, response)

        self.assertEqual(counts, {"valid": 1, "invalid": 0, "unknown": 0})
        self.assertEqual(master["companies"][0]["website_emails"], "new@example.com")
        self.assertIn("new@example.com:1", master["companies"][0]["email_statuses"])
        self.assertEqual(master["companies"][1]["website_emails"], "verified@example.com")
        self.assertIn("verified@example.com:1", master["companies"][1]["email_statuses"])


if __name__ == "__main__":
    unittest.main()
