"""Tests for the deterministic policy engine."""

import unittest
from policy_engine import evaluate_transaction


class TestEvaluateTransaction(unittest.TestCase):
    """Test evaluate_transaction against the household policy.

    Policy rules (from data/policy.json):
        auto_pay_ceiling:  5000
        allowed_categories: ["utilities", "subscription"]
    """

    def test_allowed_utilities_below_ceiling(self):
        """A utilities transaction under ₹5000 should be allowed."""
        transaction = {
            "id": "txn_test_1",
            "date": "2026-09-14",
            "vendor": "BESCOM",
            "amount": 2340,
            "currency": "INR",
            "category": "utilities",
            "type": "recurring",
            "status": "posted",
        }
        result = evaluate_transaction(transaction)

        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(len(result["reasons"]), 1)
        self.assertIn("satisfies", result["reasons"][0])

    def test_review_utilities_above_ceiling(self):
        """A utilities transaction over ₹5000 should be flagged for review."""
        transaction = {
            "id": "txn_test_2",
            "date": "2026-09-14",
            "vendor": "BESCOM",
            "amount": 7500,
            "currency": "INR",
            "category": "utilities",
            "type": "recurring",
            "status": "posted",
        }
        result = evaluate_transaction(transaction)

        self.assertEqual(result["decision"], "REVIEW")
        self.assertEqual(len(result["reasons"]), 1)
        self.assertIn("exceeds the automatic payment ceiling", result["reasons"][0])

    def test_review_disallowed_category_below_ceiling(self):
        """A disallowed category under ₹5000 should be flagged for review."""
        transaction = {
            "id": "txn_test_3",
            "date": "2026-09-14",
            "vendor": "Unknown Vendor",
            "amount": 1200,
            "currency": "INR",
            "category": "unknown",
            "type": "one_time",
            "status": "posted",
        }
        result = evaluate_transaction(transaction)

        self.assertEqual(result["decision"], "REVIEW")
        self.assertEqual(len(result["reasons"]), 1)
        self.assertIn("not allowed for automatic payment", result["reasons"][0])

    def test_review_both_violations(self):
        """Above ceiling + disallowed category should produce two reasons."""
        transaction = {
            "id": "txn_test_4",
            "date": "2026-09-14",
            "vendor": "Unknown Vendor",
            "amount": 8000,
            "currency": "INR",
            "category": "unknown",
            "type": "one_time",
            "status": "posted",
        }
        result = evaluate_transaction(transaction)

        self.assertEqual(result["decision"], "REVIEW")
        self.assertEqual(len(result["reasons"]), 2)
        self.assertIn("exceeds the automatic payment ceiling", result["reasons"][0])
        self.assertIn("not allowed for automatic payment", result["reasons"][1])


if __name__ == "__main__":
    unittest.main()
