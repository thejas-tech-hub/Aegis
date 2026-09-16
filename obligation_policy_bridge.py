"""Obligation-to-policy integration bridge for AEGIS.

Connects the validated obligation pipeline to the deterministic policy
engine through an explicit adapter boundary.

This module:
  - Maps obligation fields to the transaction shape expected by
    policy_engine.evaluate_transaction().
  - Never makes financial decisions itself; only performs field mapping.
  - Never forwards EXTRACTION_FAILED results to the policy engine.
  - Supports an optional confidence threshold that callers may supply.
  - Does not invent or hard-code a confidence threshold.
  - Does not invent a confidence value when one is absent.
"""

import math

from policy_engine import evaluate_transaction


def obligation_to_transaction(obligation: dict) -> dict:
    """Map a validated obligation to the transaction dict expected by
    policy_engine.evaluate_transaction().

    This is a pure field-mapping function.  It does not make financial
    decisions, apply policy rules, or alter data.

    Raises ValueError if the obligation is not a dict or is missing the
    required 'amount' or 'category' fields.
    """
    if not isinstance(obligation, dict):
        raise ValueError("obligation must be a dict.")

    if "amount" not in obligation:
        raise ValueError("obligation is missing required field 'amount'.")
    if "category" not in obligation:
        raise ValueError("obligation is missing required field 'category'.")

    return {
        "amount": obligation["amount"],
        "category": obligation["category"],
    }


def evaluate_processed_obligation(
    processing_result: dict,
    confidence_threshold: float = None,
) -> dict:
    """Evaluate a processed obligation against the household policy.

    Parameters
    ----------
    processing_result : dict
        The output of obligation_processor.process_obligation().
        Must contain: input_id, status, obligation, error.
    confidence_threshold : float or None
        If supplied, obligations with a confidence value below this
        threshold will receive a REVIEW decision without reaching the
        policy engine.  If None, confidence is not checked.

    Returns
    -------
    dict with keys:
        input_id    : str
        decision    : "ALLOW" | "REVIEW" | None
        reasons     : list[str]
        obligation  : dict or None
        error       : str or None
    """
    if not isinstance(processing_result, dict):
        raise ValueError("processing_result must be a dict.")

    # --- Validate confidence_threshold up front ---

    if confidence_threshold is not None:
        if isinstance(confidence_threshold, bool) or not isinstance(
            confidence_threshold, (int, float)
        ):
            raise ValueError("confidence_threshold must be a number.")
        if not math.isfinite(confidence_threshold):
            raise ValueError("confidence_threshold must be a finite number.")
        if not (0.0 <= confidence_threshold <= 1.0):
            raise ValueError(
                f"confidence_threshold {confidence_threshold} is out of "
                f"range; must be 0.0 to 1.0."
            )

    for field in ("input_id", "status", "obligation", "error"):
        if field not in processing_result:
            raise ValueError(
                f"processing_result is missing required field '{field}'."
            )

    input_id = processing_result["input_id"]
    status = processing_result["status"]
    obligation = processing_result["obligation"]
    error = processing_result["error"]

    _VALID_STATUSES = ("EXTRACTED", "EXTRACTION_FAILED")
    if status not in _VALID_STATUSES:
        raise ValueError(
            f"processing_result status '{status}' is not valid; "
            f"expected one of {_VALID_STATUSES}."
        )

    # --- EXTRACTION_FAILED: never reaches the policy engine ---

    if status == "EXTRACTION_FAILED":
        return {
            "input_id": input_id,
            "decision": None,
            "reasons": [],
            "obligation": None,
            "error": error,
        }

    # --- EXTRACTED: validate and check confidence if configured ---

    confidence = obligation.get("confidence") if isinstance(obligation, dict) else None

    if confidence is not None:
        if isinstance(confidence, bool) or not isinstance(
            confidence, (int, float)
        ):
            raise ValueError("obligation 'confidence' must be a number.")
        if not math.isfinite(confidence):
            raise ValueError(
                "obligation 'confidence' must be a finite number."
            )
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"obligation 'confidence' {confidence} is out of range; "
                f"must be 0.0 to 1.0."
            )

    if confidence_threshold is not None:
        if confidence is not None and confidence < confidence_threshold:
            return {
                "input_id": input_id,
                "decision": "REVIEW",
                "reasons": [
                    f"Extraction confidence {confidence} is below the "
                    f"required threshold of {confidence_threshold}."
                ],
                "obligation": obligation,
                "error": None,
            }

    # --- Map obligation to transaction and evaluate ---

    transaction = obligation_to_transaction(obligation)
    policy_result = evaluate_transaction(transaction)

    return {
        "input_id": input_id,
        "decision": policy_result["decision"],
        "reasons": policy_result["reasons"],
        "obligation": obligation,
        "error": None,
    }
