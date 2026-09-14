import json
from pathlib import Path
from strands import Agent, tool
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
agent = Agent(
    tools=[get_transactions]
)
result = get_transactions("subscription")
print(result)