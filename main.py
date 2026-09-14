import json
from pathlib import Path
from strands import Agent, tool
from policy_engine import evaluate_transaction
@tool
def get_transactions(category: str = "") -> str:
    """Read household transactions, optionally filtered by category."""
    data_path = Path(__file__).parent / "data" / "transactions.json"
    with open(data_path, "r", encoding="utf-8") as file:
        transactions = json.load(file)
    if category:
        transactions = [
            transaction
            for transaction in transactions
            if transaction["category"].lower() == category.lower()
        ]
    return json.dumps(transactions, indent=2)


@tool
def check_policy(transaction: dict) -> str:
    """Evaluate a single transaction against the household financial policy.

    Returns a JSON object with 'decision' (ALLOW or REVIEW) and 'reasons'.
    """
    result = evaluate_transaction(transaction)
    return json.dumps(result, indent=2)


agent = Agent(
    tools=[get_transactions, check_policy]
)

if __name__ == "__main__":
    result = agent(
        "Retrieve all household transactions, evaluate each one against the "
        "household policy using check_policy, and summarize the decisions and "
        "reasons for each transaction."
    )
    print(result)