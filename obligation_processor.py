"""Obligation processing boundary for AEGIS.

Provides a safe orchestration layer above the obligation extractor so
that one malformed bill does not terminate an entire batch.

This module:
  - Catches only expected extraction/validation errors (ValueError).
  - Never constructs a partial obligation from failed extraction.
  - Never sends failed inputs to the policy engine.
  - Treats all raw input as untrusted data.
  - Does not interpret or execute raw_text.
  - Does not perform any financial action.
"""

from obligation_engine import extract_obligation


def process_obligation(raw_input: dict, input_id: str = "input_001") -> dict:
    """Process a single raw bill input through the extraction layer.

    On success, returns a result with status "EXTRACTED" and the
    validated obligation.  On extraction/validation failure, returns a
    result with status "EXTRACTION_FAILED", obligation=None, and a
    safe error message.

    Only ValueError is caught.  Programming errors and system errors
    propagate normally.

    Parameters
    ----------
    raw_input : dict
        The raw bill input to extract.
    input_id : str
        A stable identifier for this input.  Callers may provide an
        existing ID from the input data or a batch-local fallback.
    """
    if not isinstance(input_id, str) or not input_id.strip():
        raise ValueError("input_id must be a non-empty string.")
    input_id = input_id.strip()

    try:
        obligation = extract_obligation(raw_input)
    except ValueError as exc:
        return {
            "input_id": input_id,
            "status": "EXTRACTION_FAILED",
            "obligation": None,
            "error": str(exc),
        }

    return {
        "input_id": input_id,
        "status": "EXTRACTED",
        "obligation": obligation,
        "error": None,
    }


def process_all_obligations(raw_inputs: list[dict]) -> list[dict]:
    """Process every raw bill input independently.

    A failure in one input does NOT stop processing of the remaining
    inputs.  Returns exactly one processing result per input, in the
    same order as the input list.

    Input IDs:
      - If an input has an "id" field (str), it is used as the input_id.
      - Otherwise a deterministic batch-local ID is generated:
        "input_001", "input_002", etc.

    The ID is metadata only and never affects extraction or policy
    decisions.
    """
    if not isinstance(raw_inputs, list):
        raise ValueError("raw_inputs must be a list.")

    results = []

    for index, raw_input in enumerate(raw_inputs):
        # Determine input ID: prefer existing "id", else batch-local.
        existing_id = None
        if isinstance(raw_input, dict):
            existing_id = raw_input.get("id")

        if isinstance(existing_id, str) and existing_id.strip():
            input_id = existing_id.strip()
        else:
            input_id = f"input_{index + 1:03d}"

        result = process_obligation(raw_input, input_id=input_id)
        results.append(result)

    return results


if __name__ == "__main__":
    import json
    from pathlib import Path

    bills_path = Path(__file__).parent / "data" / "bills.json"

    with open(bills_path, "r", encoding="utf-8") as file:
        raw_inputs = json.load(file)

    results = process_all_obligations(raw_inputs)

    for result in results:
        status = result["status"]
        input_id = result["input_id"]

        if status == "EXTRACTED":
            ob = result["obligation"]
            print(f"[{input_id}] {status}: {ob['vendor']} - {ob['currency']} {ob['amount']}")
        else:
            print(f"[{input_id}] {status}: {result['error']}")
