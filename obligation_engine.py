"""Obligation extraction engine for AEGIS.

Extracts structured obligation dicts from raw bill inputs.
This module treats all raw input as untrusted data:
  - raw_text is never interpreted or executed.
  - Required financial fields are validated, never invented.
  - Missing category defaults to "unknown" (safe for downstream REVIEW).
"""

import math
from datetime import date


def extract_obligation(raw_input: dict) -> dict:
    """Extract a structured obligation from a single raw bill input.

    Required hint fields: vendor_hint, amount_hint, currency_hint,
    due_date_hint, recurring_hint.

    Optional: category_hint (defaults to "unknown"), confidence_hint,
    source_hint.

    Raises ValueError if any required field is missing or has an
    invalid type.
    """
    if not isinstance(raw_input, dict):
        raise ValueError("raw_input must be a dict.")

    # --- Required fields ---

    vendor = raw_input.get("vendor_hint")
    if not isinstance(vendor, str) or not vendor.strip():
        raise ValueError("vendor_hint is required and must be a non-empty string.")
    vendor = vendor.strip()

    amount = raw_input.get("amount_hint")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise ValueError("amount_hint is required and must be a number.")
    if not math.isfinite(amount):
        raise ValueError("amount_hint must be a finite number.")
    if amount <= 0:
        raise ValueError("amount_hint must be positive.")

    currency = raw_input.get("currency_hint")
    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("currency_hint is required and must be a non-empty string.")
    currency = currency.strip()

    due_date = raw_input.get("due_date_hint")
    if not isinstance(due_date, str) or not due_date.strip():
        raise ValueError("due_date_hint is required and must be a non-empty string.")
    due_date = due_date.strip()
    try:
        date.fromisoformat(due_date)
    except ValueError:
        raise ValueError(
            f"due_date_hint '{due_date}' is not a valid ISO 8601 date (YYYY-MM-DD)."
        )

    recurring = raw_input.get("recurring_hint")
    if not isinstance(recurring, bool):
        raise ValueError("recurring_hint is required and must be a boolean.")

    # --- Optional: category (defaults to "unknown") ---

    category = raw_input.get("category_hint")
    if not isinstance(category, str) or not category.strip():
        category = "unknown"
    else:
        category = category.strip()

    # --- Build the obligation ---

    obligation = {
        "vendor": vendor,
        "amount": amount,
        "currency": currency,
        "due_date": due_date,
        "category": category,
        "recurring": recurring,
    }

    # --- Optional metadata (preserved only when provided and valid) ---

    confidence = raw_input.get("confidence_hint")
    if confidence is not None:
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("confidence_hint must be a number.")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"confidence_hint {confidence} is out of range; must be 0.0 to 1.0."
            )
        obligation["confidence"] = float(confidence)

    source = raw_input.get("source_hint")
    if isinstance(source, str) and source.strip():
        obligation["source"] = source.strip()

    return obligation


def extract_all(raw_inputs: list[dict]) -> list[dict]:
    """Extract obligations from a list of raw bill inputs.

    Each input is processed independently.  If a single input fails
    validation, the error propagates — callers decide how to handle it.
    """
    if not isinstance(raw_inputs, list):
        raise ValueError("raw_inputs must be a list.")

    results = []

    for raw_input in raw_inputs:
        obligation = extract_obligation(raw_input)
        results.append(obligation)

    return results


if __name__ == "__main__":
    import json
    from pathlib import Path

    bills_path = Path(__file__).parent / "data" / "bills.json"

    with open(bills_path, "r", encoding="utf-8") as file:
        raw_inputs = json.load(file)

    obligations = extract_all(raw_inputs)

    for obligation in obligations:
        print(f"{obligation['vendor']} — {obligation['currency']} {obligation['amount']}")
        print(f"  Due: {obligation['due_date']}  Category: {obligation['category']}")
        if "confidence" in obligation:
            print(f"  Confidence: {obligation['confidence']}")
        print()
