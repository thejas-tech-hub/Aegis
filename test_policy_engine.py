"""Tests for the deterministic policy engine."""

import unittest
from policy_engine import evaluate_transaction, evaluate_all_transactions


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


class TestEvaluateAllTransactions(unittest.TestCase):
    """Test evaluate_all_transactions against the household policy."""

    def test_batch_of_three_transactions(self):
        """Two allowed transactions and one disallowed category."""
        transactions = [
            {
                "id": "txn_batch_1",
                "date": "2026-09-14",
                "vendor": "BESCOM",
                "amount": 2340,
                "currency": "INR",
                "category": "utilities",
                "type": "recurring",
                "status": "posted",
            },
            {
                "id": "txn_batch_2",
                "date": "2026-09-14",
                "vendor": "Netflix",
                "amount": 649,
                "currency": "INR",
                "category": "subscription",
                "type": "recurring",
                "status": "posted",
            },
            {
                "id": "txn_batch_3",
                "date": "2026-09-14",
                "vendor": "Unknown Vendor",
                "amount": 1200,
                "currency": "INR",
                "category": "unknown",
                "type": "one_time",
                "status": "posted",
            },
        ]
        results = evaluate_all_transactions(transactions)

        # Exactly 3 results returned
        self.assertEqual(len(results), 3)

        # Decisions match expected order
        decisions = [r["decision"] for r in results]
        self.assertEqual(decisions, ["ALLOW", "ALLOW", "REVIEW"])

        # Each result contains the original transaction
        for i, result in enumerate(results):
            self.assertEqual(result["transaction"], transactions[i])

    def test_batch_with_dual_violation(self):
        """A transaction that violates both ceiling and category rules."""
        transactions = [
            {
                "id": "txn_batch_4",
                "date": "2026-09-14",
                "vendor": "Unknown Vendor",
                "amount": 8000,
                "currency": "INR",
                "category": "unknown",
                "type": "one_time",
                "status": "posted",
            },
        ]
        results = evaluate_all_transactions(transactions)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["decision"], "REVIEW")
        self.assertEqual(len(results[0]["reasons"]), 2)
        self.assertIn("exceeds the automatic payment ceiling", results[0]["reasons"][0])
        self.assertIn("not allowed for automatic payment", results[0]["reasons"][1])
        self.assertEqual(results[0]["transaction"], transactions[0])


if __name__ == "__main__":
    unittest.main()
