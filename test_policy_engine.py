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


class TestEvaluateTransactionValidation(unittest.TestCase):
    """Negative-path tests for evaluate_transaction input validation."""

    def test_non_dict_input_raises_error(self):
        """Passing a non-dict should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction("not a dict")

    def test_none_input_raises_error(self):
        """Passing None should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction(None)

    def test_list_input_raises_error(self):
        """Passing a list should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction([{"amount": 100, "category": "utilities"}])

    def test_missing_amount_raises_error(self):
        """A transaction without 'amount' should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction({"category": "utilities"})

    def test_missing_category_raises_error(self):
        """A transaction without 'category' should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction({"amount": 1000})

    def test_missing_both_fields_raises_error(self):
        """An empty dict should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction({})

    def test_string_amount_raises_error(self):
        """A string amount should raise ValueError, not be coerced."""
        with self.assertRaises(ValueError):
            evaluate_transaction({"amount": "1000", "category": "utilities"})

    def test_boolean_amount_raises_error(self):
        """A boolean amount should raise ValueError (bool is not a number)."""
        with self.assertRaises(ValueError):
            evaluate_transaction({"amount": True, "category": "utilities"})

    def test_nan_amount_raises_error(self):
        """NaN amount should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction({"amount": float("nan"), "category": "utilities"})

    def test_positive_infinity_amount_raises_error(self):
        """Positive infinity amount should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction({"amount": float("inf"), "category": "utilities"})

    def test_negative_infinity_amount_raises_error(self):
        """Negative infinity amount should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction({"amount": float("-inf"), "category": "utilities"})

    def test_none_amount_raises_error(self):
        """None amount should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction({"amount": None, "category": "utilities"})

    def test_non_string_category_raises_error(self):
        """A numeric category should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction({"amount": 1000, "category": 123})

    def test_none_category_raises_error(self):
        """None category should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_transaction({"amount": 1000, "category": None})

    def test_negative_amount_returns_review(self):
        """Negative amounts should produce REVIEW with an explicit reason."""
        result = evaluate_transaction({"amount": -500, "category": "utilities"})
        self.assertEqual(result["decision"], "REVIEW")
        self.assertEqual(len(result["reasons"]), 1)
        self.assertIn("cannot be negative", result["reasons"][0])

    def test_negative_amount_with_disallowed_category(self):
        """Negative amount + disallowed category should produce two reasons."""
        result = evaluate_transaction({"amount": -500, "category": "unknown"})
        self.assertEqual(result["decision"], "REVIEW")
        self.assertEqual(len(result["reasons"]), 2)
        self.assertIn("cannot be negative", result["reasons"][0])
        self.assertIn("not allowed for automatic payment", result["reasons"][1])

    def test_zero_amount_is_valid_below_ceiling(self):
        """Zero amount passes type validation and is below ceiling."""
        result = evaluate_transaction({"amount": 0, "category": "utilities"})
        self.assertEqual(result["decision"], "ALLOW")

    def test_extra_fields_are_ignored(self):
        """Extra fields in the transaction should not affect evaluation."""
        transaction = {
            "amount": 2340,
            "category": "utilities",
            "vendor": "BESCOM",
            "extra_field": "should be ignored",
        }
        result = evaluate_transaction(transaction)
        self.assertEqual(result["decision"], "ALLOW")


class TestEvaluateAllTransactionsValidation(unittest.TestCase):
    """Negative-path tests for evaluate_all_transactions input validation."""

    def test_non_list_input_raises_error(self):
        """Passing a non-list should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_all_transactions("not a list")

    def test_none_input_raises_error(self):
        """Passing None should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_all_transactions(None)

    def test_dict_input_raises_error(self):
        """Passing a dict should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_all_transactions({"amount": 100, "category": "utilities"})

    def test_invalid_transaction_in_batch_propagates_error(self):
        """A bad transaction in the batch should raise ValueError."""
        transactions = [
            {"amount": 2340, "category": "utilities"},
            {"category": "utilities"},  # missing amount
        ]
        with self.assertRaises(ValueError):
            evaluate_all_transactions(transactions)

    def test_empty_list_returns_empty_results(self):
        """An empty list should return an empty result list."""
        results = evaluate_all_transactions([])
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
