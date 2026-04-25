from typing import Dict, Any, Optional


HIGH_RISK_ACTIONS = {"send_email", "delete_file", "transfer_money"}
VALID_APPROVALS = {"approve", "yes", "y"}
VALID_REJECTIONS = {"reject", "no", "n"}


def decide_action(goal: str) -> Dict[str, Any]:
    if "email" in goal.lower():
        return {
            "action": "send_email",
            "args": {"to": "team@example.com", "body": "Hello team!"},
        }

    if "delete" in goal.lower():
        return {
            "action": "delete_file",
            "args": {"path": "important_file.txt"},
        }

    return {
        "action": "answer",
        "args": {"text": f"Answering: {goal}"},
    }


def requires_approval(action: str) -> bool:
    return action in HIGH_RISK_ACTIONS


def ask_for_approval(action: str, args: Dict[str, Any], max_attempts: int = 2) -> Optional[bool]:
    print("\nApproval required")
    print("Action:", action)
    print("Arguments:", args)

    for attempt in range(1, max_attempts + 1):
        decision = input("Type exactly 'approve' or 'reject': ").strip().lower()

        if decision in VALID_APPROVALS:
            return True

        if decision in VALID_REJECTIONS:
            return False

        if not decision:
            print("No approval received.")
        else:
            print("Ambiguous approval response.")

    print("Approval failed. Defaulting to reject.")
    return None


def execute_action(action: str, args: Dict[str, Any]) -> str:
    if action == "send_email":
        return f"Email sent to {args['to']}"

    if action == "delete_file":
        return f"Deleted file: {args['path']}"

    if action == "answer":
        return args["text"]

    return "Unknown action."


def run_agent(goal: str) -> None:
    decision = decide_action(goal)
    action = decision["action"]
    args = decision["args"]

    print("\nGoal:", goal)
    print("Proposed action:", action)

    if requires_approval(action):
        approved = ask_for_approval(action, args)

        if approved is not True:
            print("Stopped: action was not approved.")
            return

    result = execute_action(action, args)
    print("Result:", result)


if __name__ == "__main__":
    run_agent("Send an email to the team")
    run_agent("Delete a file")
    run_agent("Explain AI agents")