import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_unchecked_emails import apply_response, parse_statuses, unchecked_emails


class EmailValidationTests(unittest.TestCase):
    def test_parse_statuses_uses_final_colon(self):
        self.assertEqual(
            parse_statuses("a@example.com:0; b@example.com:1"),
            {"a@example.com": 0, "b@example.com": 1},
        )

    def test_unchecked_emails_are_unique(self):
        master = {
            "companies": [
                {"emails": "a@example.com; b@example.com", "email_statuses": "a@example.com:0; b@example.com:1"},
                {"emails": "a@example.com", "email_statuses": "a@example.com:0"},
            ]
        }
        self.assertEqual(unchecked_emails(master), ["a@example.com"])

    def test_apply_response_preserves_existing_valid_status(self):
        master = {
            "companies": [
                {
                    "emails": "a@example.com; b@example.com",
                    "email_statuses": "a@example.com:0; b@example.com:1",
                }
            ]
        }
        response = {
            "data": {
                "list": [
                    {"email": "a@example.com", "status": 2, "reason": "mailbox unavailable"}
                ]
            }
        }
        counts = apply_response(master, response)
        self.assertEqual(master["companies"][0]["email_statuses"], "a@example.com:2; b@example.com:1")
        self.assertEqual(counts, {"valid": 1, "invalid": 1, "unknown": 0, "unchecked": 0})


if __name__ == "__main__":
    unittest.main()
