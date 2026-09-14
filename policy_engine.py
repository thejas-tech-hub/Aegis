import json
from pathlib import Path
def load_policy() -> dict:
    """Load the household's financial safety policy."""
    policy_path = Path(__file__).parent / "data" / "policy.json"

    with open(policy_path, "r", encoding="utf-8") as file:
        return json.load(file)
def evaluate_transaction(transaction: dict) -> dict:
    """Determine whether a transaction can be handled automatically."""
    policy = load_policy()

    amount = transaction["amount"]
    category = transaction["category"]

    if amount > policy["auto_pay_ceiling"]:
        return {
            "decision": "REVIEW",
            "reason": f"Amount ₹{amount} exceeds the automatic payment ceiling of ₹{policy['auto_pay_ceiling']}."
        }

    if category not in policy["allowed_categories"]:
        return {
            "decision": "REVIEW",
            "reason": f"Category '{category}' is not allowed for automatic payment."
        }

    return {
        "decision": "ALLOW",
        "reason": "Transaction satisfies the current household policy."
    }
if __name__ == "__main__":
    test_transaction = {
    "vendor": "Unknown Vendor",
    "amount": 4850,
    "category": "unknown"
}
    decision = evaluate_transaction(test_transaction)
    print(decision)