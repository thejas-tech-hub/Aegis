from strands import Agent, tool
@tool
def get_household_member(name: str) -> str:
    """Look up a household member by name."""
    members = {
        "thejas": "Thejas is the primary household member.",
        "parent": "Parent is a household member.",
    }

    return members.get(name.lower(), "Member not found.")
agent = Agent(
    tools=[get_household_member]
)
result=get_household_member("Thejas")
print(result)