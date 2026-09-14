import json
from pathlib import Path
def load_policy() -> dict:
    """Load the household's financial safety policy."""
    policy_path = Path(__file__).parent / "data" / "policy.json"

    with open(policy_path, "r", encoding="utf-8") as file:
        return json.load(file)
def load_transactions() -> list[dict]:
    """Load household transactions from the local ledger."""
    data_path = Path(__file__).parent / "data" / "transactions.json"

    with open(data_path, "r", encoding="utf-8") as file:
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
def evaluate_all_transactions(transactions: list[dict]) -> list[dict]:
    """Evaluate every transaction against the household policy."""
    results = []

    for transaction in transactions:
        decision = evaluate_transaction(transaction)

        results.append({
            "transaction": transaction,
            "decision": decision["decision"],
            "reason": decision["reason"]
        })

    return results
if __name__ == "__main__":
    transactions = load_transactions()
    results = evaluate_all_transactions(transactions)

    for result in results:
        transaction = result["transaction"]

        print(f"{transaction['vendor']} — ₹{transaction['amount']}")
        print(f"Decision: {result['decision']}")
        print(f"Reason: {result['reason']}")
        print()