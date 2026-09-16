import json
import math
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
    """Determine whether a transaction can be handled automatically.

    Raises ValueError if the transaction is not a dict, or if required
    fields ('amount', 'category') are missing or have invalid types.
    """
    if not isinstance(transaction, dict):
        raise ValueError("transaction must be a dict.")

    if "amount" not in transaction:
        raise ValueError("transaction is missing required field 'amount'.")
    if "category" not in transaction:
        raise ValueError("transaction is missing required field 'category'.")

    amount = transaction["amount"]
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise ValueError("transaction 'amount' must be a number.")
    if not math.isfinite(amount):
        raise ValueError("transaction 'amount' must be a finite number.")

    category = transaction["category"]
    if not isinstance(category, str):
        raise ValueError("transaction 'category' must be a string.")

    policy = load_policy()

    reasons = []

    if amount < 0:
        reasons.append("Transaction amount cannot be negative.")

    if amount > policy["auto_pay_ceiling"]:
        reasons.append(
            f"Amount ₹{amount} exceeds the automatic payment ceiling "
            f"of ₹{policy['auto_pay_ceiling']}."
        )

    if category not in policy["allowed_categories"]:
        reasons.append(
            f"Category '{category}' is not allowed for automatic payment."
        )

    if reasons:
        return {
            "decision": "REVIEW",
            "reasons": reasons
        }

    return {
        "decision": "ALLOW",
        "reasons": [
            "Transaction satisfies the current household policy."
        ]
    }
def evaluate_all_transactions(transactions: list[dict]) -> list[dict]:
    """Evaluate every transaction against the household policy.

    Raises ValueError if transactions is not a list.
    """
    if not isinstance(transactions, list):
        raise ValueError("transactions must be a list.")

    results = []

    for transaction in transactions:
        decision = evaluate_transaction(transaction)

        results.append({
            "transaction": transaction,
            "decision": decision["decision"],
            "reasons": decision["reasons"]
        })

    return results
if __name__ == "__main__":
    transactions = load_transactions()
    results = evaluate_all_transactions(transactions)

    for result in results:
        transaction = result["transaction"]

        print(f"{transaction['vendor']} — ₹{transaction['amount']}")
        print(f"Decision: {result['decision']}")
        for reason in result["reasons"]:
            print(f"Reason: {reason}")
        print()