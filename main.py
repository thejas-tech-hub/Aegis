import json
from pathlib import Path

from strands import Agent, tool


@tool
def get_transactions() -> str:
    """Read the household transaction ledger and return the transactions."""
    data_path = Path(__file__).parent / "data" / "transactions.json"

    with open(data_path, "r", encoding="utf-8") as file:
        transactions = json.load(file)

    return json.dumps(transactions, indent=2)


agent = Agent(
    tools=[get_transactions]
)

result = get_transactions()

print(result)