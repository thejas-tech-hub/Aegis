"""Tests for the obligation extraction engine."""

import unittest
from obligation_engine import extract_obligation, extract_all


class TestExtractObligation(unittest.TestCase):
    """Test extract_obligation with valid and invalid inputs."""

    # --- Happy-path tests ---

    def test_full_valid_input(self):
        """All fields provided, including optional confidence and source."""
        raw = {
            "raw_text": "BESCOM bill for Sep 2026.",
            "vendor_hint": "BESCOM",
            "amount_hint": 2340,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "category_hint": "utilities",
            "recurring_hint": True,
            "confidence_hint": 0.95,
            "source_hint": "synthetic",
        }
        result = extract_obligation(raw)

        self.assertEqual(result["vendor"], "BESCOM")
        self.assertEqual(result["amount"], 2340)
        self.assertEqual(result["currency"], "INR")
        self.assertEqual(result["due_date"], "2026-09-15")
        self.assertEqual(result["category"], "utilities")
        self.assertTrue(result["recurring"])
        self.assertAlmostEqual(result["confidence"], 0.95)
        self.assertEqual(result["source"], "synthetic")

    def test_missing_category_defaults_to_unknown(self):
        """When category_hint is absent, category should be 'unknown'."""
        raw = {
            "vendor_hint": "Unknown Merchant",
            "amount_hint": 4850,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-20",
            "recurring_hint": False,
        }
        result = extract_obligation(raw)

        self.assertEqual(result["category"], "unknown")

    def test_empty_category_defaults_to_unknown(self):
        """When category_hint is an empty string, category should be 'unknown'."""
        raw = {
            "vendor_hint": "Some Vendor",
            "amount_hint": 100,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-20",
            "category_hint": "",
            "recurring_hint": True,
        }
        result = extract_obligation(raw)

        self.assertEqual(result["category"], "unknown")

    def test_optional_fields_omitted_when_not_provided(self):
        """When confidence_hint and source_hint are absent, they are not in output."""
        raw = {
            "vendor_hint": "BESCOM",
            "amount_hint": 2340,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "category_hint": "utilities",
            "recurring_hint": True,
        }
        result = extract_obligation(raw)

        self.assertNotIn("confidence", result)
        self.assertNotIn("source", result)

    def test_raw_text_is_not_in_output(self):
        """raw_text should never appear in the structured obligation."""
        raw = {
            "raw_text": "This is some raw text that should be ignored.",
            "vendor_hint": "Test Vendor",
            "amount_hint": 500,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "category_hint": "utilities",
            "recurring_hint": True,
        }
        result = extract_obligation(raw)

        self.assertNotIn("raw_text", result)

    def test_output_is_compatible_with_policy_engine(self):
        """The obligation dict must contain 'amount' and 'category' for evaluate_transaction."""
        raw = {
            "vendor_hint": "Netflix",
            "amount_hint": 649,
            "currency_hint": "INR",
            "due_date_hint": "2026-10-01",
            "category_hint": "subscription",
            "recurring_hint": True,
        }
        result = extract_obligation(raw)

        # These are the two fields evaluate_transaction reads
        self.assertIn("amount", result)
        self.assertIn("category", result)
        self.assertIsInstance(result["amount"], (int, float))
        self.assertIsInstance(result["category"], str)

    # --- Validation failure tests ---

    def test_missing_vendor_raises_error(self):
        """Missing vendor_hint should raise ValueError."""
        raw = {
            "amount_hint": 1000,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_missing_amount_raises_error(self):
        """Missing amount_hint should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_negative_amount_raises_error(self):
        """Negative amount_hint should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": -500,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_zero_amount_raises_error(self):
        """Zero amount_hint should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": 0,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_missing_currency_raises_error(self):
        """Missing currency_hint should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": 1000,
            "due_date_hint": "2026-09-15",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_missing_due_date_raises_error(self):
        """Missing due_date_hint should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": 1000,
            "currency_hint": "INR",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_missing_recurring_raises_error(self):
        """Missing recurring_hint should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": 1000,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_non_dict_input_raises_error(self):
        """Passing a non-dict should raise ValueError."""
        with self.assertRaises(ValueError):
            extract_obligation("not a dict")

    def test_string_amount_raises_error(self):
        """A string amount_hint should raise ValueError, not be coerced."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": "1000",
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_boolean_amount_raises_error(self):
        """A boolean amount_hint should raise ValueError (bool is not a number)."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": True,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_nan_amount_raises_error(self):
        """NaN amount_hint should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": float("nan"),
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_infinity_amount_raises_error(self):
        """Infinity amount_hint should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": float("inf"),
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_negative_infinity_amount_raises_error(self):
        """Negative infinity amount_hint should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": float("-inf"),
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_malformed_date_raises_error(self):
        """A non-ISO date string should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": 500,
            "currency_hint": "INR",
            "due_date_hint": "15-Sep-2026",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_impossible_date_raises_error(self):
        """An impossible date like Feb 30 should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": 500,
            "currency_hint": "INR",
            "due_date_hint": "2026-02-30",
            "recurring_hint": True,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_confidence_above_range_raises_error(self):
        """confidence_hint > 1.0 should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": 500,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "category_hint": "utilities",
            "recurring_hint": True,
            "confidence_hint": 1.5,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_confidence_below_range_raises_error(self):
        """confidence_hint < 0.0 should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": 500,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "category_hint": "utilities",
            "recurring_hint": True,
            "confidence_hint": -0.1,
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_non_numeric_confidence_raises_error(self):
        """A string confidence_hint should raise ValueError."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": 500,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "category_hint": "utilities",
            "recurring_hint": True,
            "confidence_hint": "high",
        }
        with self.assertRaises(ValueError):
            extract_obligation(raw)

    def test_absent_confidence_is_still_omitted(self):
        """When confidence_hint is not provided at all, no error and no key in output."""
        raw = {
            "vendor_hint": "Test Vendor",
            "amount_hint": 500,
            "currency_hint": "INR",
            "due_date_hint": "2026-09-15",
            "category_hint": "utilities",
            "recurring_hint": True,
        }
        result = extract_obligation(raw)

        self.assertNotIn("confidence", result)


class TestExtractAll(unittest.TestCase):
    """Test the batch extraction function."""

    def test_batch_of_three(self):
        """extract_all should return one obligation per input."""
        raw_inputs = [
            {
                "vendor_hint": "BESCOM",
                "amount_hint": 2340,
                "currency_hint": "INR",
                "due_date_hint": "2026-09-15",
                "category_hint": "utilities",
                "recurring_hint": True,
            },
            {
                "vendor_hint": "Netflix",
                "amount_hint": 649,
                "currency_hint": "INR",
                "due_date_hint": "2026-10-01",
                "category_hint": "subscription",
                "recurring_hint": True,
            },
            {
                "vendor_hint": "Unknown Merchant",
                "amount_hint": 4850,
                "currency_hint": "INR",
                "due_date_hint": "2026-09-20",
                "recurring_hint": False,
            },
        ]
        results = extract_all(raw_inputs)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["vendor"], "BESCOM")
        self.assertEqual(results[1]["vendor"], "Netflix")
        self.assertEqual(results[2]["category"], "unknown")

    def test_batch_validation_error_propagates(self):
        """A bad input in the batch should raise ValueError."""
        raw_inputs = [
            {
                "vendor_hint": "BESCOM",
                "amount_hint": 2340,
                "currency_hint": "INR",
                "due_date_hint": "2026-09-15",
                "category_hint": "utilities",
                "recurring_hint": True,
            },
            {
                "vendor_hint": "Bad Entry",
                # missing amount_hint
                "currency_hint": "INR",
                "due_date_hint": "2026-09-20",
                "recurring_hint": False,
            },
        ]
        with self.assertRaises(ValueError):
            extract_all(raw_inputs)

    def test_non_list_input_raises_error(self):
        """Passing a non-list should raise ValueError."""
        with self.assertRaises(ValueError):
            extract_all("not a list")


if __name__ == "__main__":
    unittest.main()
