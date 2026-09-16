"""Tests for the obligation-to-policy integration bridge."""

import unittest
from obligation_policy_bridge import (
    obligation_to_transaction,
    evaluate_processed_obligation,
)


# --- Reusable fixtures ---

def _extracted_result(obligation_overrides=None, confidence=None, input_id="test_001"):
    """Return a processing result with status EXTRACTED."""
    obligation = {
        "vendor": "BESCOM",
        "amount": 2340,
        "currency": "INR",
        "due_date": "2026-09-15",
        "category": "utilities",
        "recurring": True,
    }
    if obligation_overrides:
        obligation.update(obligation_overrides)
    if confidence is not None:
        obligation["confidence"] = confidence

    return {
        "input_id": input_id,
        "status": "EXTRACTED",
        "obligation": obligation,
        "error": None,
    }


def _failed_result(input_id="test_fail"):
    """Return a processing result with status EXTRACTION_FAILED."""
    return {
        "input_id": input_id,
        "status": "EXTRACTION_FAILED",
        "obligation": None,
        "error": "amount_hint is required and must be a number.",
    }


class TestObligationToTransaction(unittest.TestCase):
    """Test the pure field-mapping adapter."""

    def test_maps_amount_and_category(self):
        """Obligation amount and category should appear in the transaction."""
        obligation = {
            "vendor": "BESCOM",
            "amount": 2340,
            "currency": "INR",
            "due_date": "2026-09-15",
            "category": "utilities",
            "recurring": True,
        }
        txn = obligation_to_transaction(obligation)

        self.assertEqual(txn["amount"], 2340)
        self.assertEqual(txn["category"], "utilities")

    def test_extra_fields_not_in_transaction(self):
        """Fields not needed by policy_engine should not leak into the transaction."""
        obligation = {
            "vendor": "Netflix",
            "amount": 649,
            "currency": "INR",
            "due_date": "2026-10-01",
            "category": "subscription",
            "recurring": True,
            "confidence": 0.95,
            "source": "synthetic",
        }
        txn = obligation_to_transaction(obligation)

        self.assertNotIn("vendor", txn)
        self.assertNotIn("currency", txn)
        self.assertNotIn("due_date", txn)
        self.assertNotIn("recurring", txn)
        self.assertNotIn("confidence", txn)
        self.assertNotIn("source", txn)

    def test_non_dict_raises_error(self):
        """Non-dict obligation should raise ValueError."""
        with self.assertRaises(ValueError):
            obligation_to_transaction("not a dict")

    def test_missing_amount_raises_error(self):
        """Obligation without amount should raise ValueError."""
        with self.assertRaises(ValueError):
            obligation_to_transaction({"category": "utilities"})

    def test_missing_category_raises_error(self):
        """Obligation without category should raise ValueError."""
        with self.assertRaises(ValueError):
            obligation_to_transaction({"amount": 1000})


class TestEvaluateProcessedObligation(unittest.TestCase):
    """Test the integration evaluation boundary."""

    # --- Extraction failure ---

    def test_extraction_failure_returns_no_decision(self):
        """EXTRACTION_FAILED must never reach the policy engine."""
        result = evaluate_processed_obligation(_failed_result())

        self.assertIsNone(result["decision"])
        self.assertEqual(result["reasons"], [])
        self.assertIsNone(result["obligation"])
        self.assertIsNotNone(result["error"])

    def test_extraction_failure_never_produces_allow(self):
        """A failed extraction must never result in an ALLOW decision."""
        result = evaluate_processed_obligation(_failed_result())

        self.assertNotEqual(result.get("decision"), "ALLOW")

    def test_extraction_failure_preserves_input_id(self):
        """Failed results should preserve the input_id."""
        result = evaluate_processed_obligation(_failed_result(input_id="bill_x"))

        self.assertEqual(result["input_id"], "bill_x")

    # --- Successful extraction → policy ALLOW ---

    def test_allowed_obligation_returns_allow(self):
        """An allowed-category obligation below ceiling should produce ALLOW."""
        result = evaluate_processed_obligation(_extracted_result())

        self.assertEqual(result["decision"], "ALLOW")
        self.assertIsNotNone(result["obligation"])
        self.assertIsNone(result["error"])

    # --- Successful extraction → policy REVIEW ---

    def test_above_ceiling_returns_review(self):
        """An obligation above the auto_pay_ceiling should produce REVIEW."""
        result = evaluate_processed_obligation(
            _extracted_result({"amount": 7500})
        )

        self.assertEqual(result["decision"], "REVIEW")
        self.assertTrue(
            any("exceeds" in r for r in result["reasons"])
        )

    def test_disallowed_category_returns_review(self):
        """An obligation with an unknown category should produce REVIEW."""
        result = evaluate_processed_obligation(
            _extracted_result({"category": "unknown"})
        )

        self.assertEqual(result["decision"], "REVIEW")
        self.assertTrue(
            any("not allowed" in r for r in result["reasons"])
        )

    # --- Confidence threshold ---

    def test_low_confidence_returns_review(self):
        """Confidence below the threshold should produce REVIEW."""
        result = evaluate_processed_obligation(
            _extracted_result(confidence=0.3),
            confidence_threshold=0.7,
        )

        self.assertEqual(result["decision"], "REVIEW")
        self.assertTrue(
            any("confidence" in r.lower() for r in result["reasons"])
        )

    def test_low_confidence_never_becomes_allow(self):
        """Even if the obligation passes policy, low confidence must not ALLOW."""
        result = evaluate_processed_obligation(
            _extracted_result(confidence=0.1),
            confidence_threshold=0.5,
        )

        self.assertNotEqual(result["decision"], "ALLOW")

    def test_high_confidence_reaches_policy_engine(self):
        """Confidence above threshold should proceed to policy evaluation."""
        result = evaluate_processed_obligation(
            _extracted_result(confidence=0.95),
            confidence_threshold=0.7,
        )

        self.assertEqual(result["decision"], "ALLOW")

    def test_missing_confidence_with_no_threshold(self):
        """When no threshold is set and confidence is absent, proceed to policy."""
        result = evaluate_processed_obligation(
            _extracted_result()  # no confidence key
        )

        self.assertEqual(result["decision"], "ALLOW")

    def test_missing_confidence_with_threshold_proceeds_to_policy(self):
        """When threshold is set but confidence is absent, proceed to policy.

        We do not invent a confidence value.  The absence of confidence
        means the extractor did not provide one, so the threshold gate
        cannot trigger.
        """
        result = evaluate_processed_obligation(
            _extracted_result(),  # no confidence key
            confidence_threshold=0.7,
        )

        self.assertEqual(result["decision"], "ALLOW")

    def test_confidence_preserved_in_result_obligation(self):
        """The confidence value should be preserved in the output obligation."""
        result = evaluate_processed_obligation(
            _extracted_result(confidence=0.95),
            confidence_threshold=0.7,
        )

        self.assertEqual(result["obligation"]["confidence"], 0.95)

    # --- Malformed input ---

    def test_non_dict_processing_result_raises_error(self):
        """A non-dict processing_result should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation("not a dict")

    def test_missing_status_field_raises_error(self):
        """A processing result without 'status' should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation({
                "input_id": "test",
                "obligation": None,
                "error": None,
            })

    def test_missing_input_id_field_raises_error(self):
        """A processing result without 'input_id' should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation({
                "status": "EXTRACTED",
                "obligation": {"amount": 100, "category": "utilities"},
                "error": None,
            })


class TestValidation(unittest.TestCase):
    """Hardening tests for status, threshold, and confidence validation."""

    # --- Unknown status ---

    def test_unknown_status_raises_error(self):
        """A status other than EXTRACTED/EXTRACTION_FAILED must raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation({
                "input_id": "test",
                "status": "PENDING",
                "obligation": None,
                "error": None,
            })

    # --- Invalid confidence_threshold ---

    def test_string_threshold_raises_error(self):
        """A string confidence_threshold should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(), confidence_threshold="high"
            )

    def test_bool_threshold_raises_error(self):
        """A boolean confidence_threshold should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(), confidence_threshold=True
            )

    def test_nan_threshold_raises_error(self):
        """NaN confidence_threshold should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(), confidence_threshold=float("nan")
            )

    def test_positive_infinity_threshold_raises_error(self):
        """Positive infinity confidence_threshold should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(), confidence_threshold=float("inf")
            )

    def test_negative_infinity_threshold_raises_error(self):
        """Negative infinity confidence_threshold should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(), confidence_threshold=float("-inf")
            )

    def test_threshold_above_one_raises_error(self):
        """confidence_threshold > 1.0 should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(), confidence_threshold=1.5
            )

    def test_threshold_below_zero_raises_error(self):
        """confidence_threshold < 0.0 should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(), confidence_threshold=-0.1
            )

    # --- Invalid obligation confidence ---

    def test_string_confidence_raises_error(self):
        """A string confidence in the obligation should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(confidence="high")
            )

    def test_bool_confidence_raises_error(self):
        """A boolean confidence in the obligation should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(confidence=True)
            )

    def test_nan_confidence_raises_error(self):
        """NaN confidence in the obligation should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(confidence=float("nan"))
            )

    def test_infinity_confidence_raises_error(self):
        """Infinity confidence in the obligation should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(confidence=float("inf"))
            )

    def test_confidence_above_one_raises_error(self):
        """Obligation confidence > 1.0 should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(confidence=1.5)
            )

    def test_confidence_below_zero_raises_error(self):
        """Obligation confidence < 0.0 should raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_processed_obligation(
                _extracted_result(confidence=-0.1)
            )


if __name__ == "__main__":
    unittest.main()
