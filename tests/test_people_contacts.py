import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_people_contacts import apply


class PeopleContactTests(unittest.TestCase):
    def test_excludes_conflicting_employer_domain(self):
        master = {"companies": [{"company_id": 1, "emails": "", "email_statuses": ""}]}
        selection = {"people": [{"company_id": 1, "hid": "h1", "name": "A", "title": "Logistics", "reason": "match"}]}
        contacts = {"data": {"list": [{"bus_id": "h1", "contact_data": {"emails": [
            {"val": "chuktiii@gmail.com", "is_valid": 1},
            {"val": "madhumay.panigrahi@havells.com", "is_valid": 1},
        ], "socials": []}}]}}
        counts = apply(master, selection, contacts)
        self.assertEqual(master["companies"][0]["emails"], "chuktiii@gmail.com")
        self.assertEqual(counts["excluded"], 1)
        self.assertEqual(counts["valid"], 1)


if __name__ == "__main__":
    unittest.main()
