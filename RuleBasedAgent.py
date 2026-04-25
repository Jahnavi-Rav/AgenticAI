def simple_agent(goal):
    if "weather" in goal.lower():
        return "Use weather tool and report forecast."
    elif "email" in goal.lower():
        return "Draft an email, but ask before sending."
    elif "buy" in goal.lower() or "purchase" in goal.lower():
        return "Find options, but require human approval before purchase."
    elif "delete" in goal.lower():
        return "Refuse or ask for strong confirmation before deleting anything."
    else:
        return "Ask the user to clarify the goal."

print(simple_agent("Buy me a laptop"))