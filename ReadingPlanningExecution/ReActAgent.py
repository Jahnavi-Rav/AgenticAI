from typing import Dict, Any, Callable, Optional, List


MAX_STEPS = 5


def calculator(args: Dict[str, Any]) -> str:
    expression = args.get("expression")

    if not expression:
        return "Error: missing expression."

    allowed = "0123456789+-*/(). "
    if any(char not in allowed for char in expression):
        return "Error: unsafe expression."

    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"


def weather(args: Dict[str, Any]) -> str:
    city = args.get("city")

    if not city:
        return "Error: missing city."

    fake_weather = {
        "london": "Rainy, 10°C",
        "mumbai": "Hot, 31°C",
        "new york": "Cold, 8°C",
    }

    return fake_weather.get(city.lower(), "Weather not found.")


TOOLS: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "calculator": calculator,
    "weather": weather,
}


def validate_tool_call(tool_name: str, args: Dict[str, Any]) -> Optional[str]:
    if tool_name not in TOOLS:
        return f"Blocked: tool hallucination. Unknown tool '{tool_name}'."

    if not isinstance(args, dict):
        return "Blocked: tool arguments must be a dictionary."

    return None


class ReActAgent:
    def __init__(self, goal: str):
        self.goal = goal
        self.history: List[str] = []
        self.last_action: Optional[str] = None

    def reason(self) -> Dict[str, Any]:
        goal = self.goal.lower()

        if "weather" in goal:
            return {
                "thought": "I need weather information.",
                "tool": "weather",
                "args": {"city": "London"},
            }

        if "calculate" in goal or "math" in goal:
            return {
                "thought": "I need to calculate something.",
                "tool": "calculator",
                "args": {"expression": "2 + 3 * 4"},
            }

        if "email" in goal:
            return {
                "thought": "I want to send an email.",
                "tool": "email_sender",  # hallucinated tool
                "args": {"to": "test@example.com"},
            }

        return {
            "thought": "No tool is needed.",
            "tool": None,
            "args": {},
        }

    def act(self, tool_name: Optional[str], args: Dict[str, Any]) -> str:
        if tool_name is None:
            return f"Final answer: {self.goal}"

        validation_error = validate_tool_call(tool_name, args)
        if validation_error:
            return validation_error

        tool = TOOLS[tool_name]
        return tool(args)

    def repeated_action(self, tool_name: Optional[str], args: Dict[str, Any]) -> bool:
        action_signature = f"{tool_name}:{args}"

        if self.last_action == action_signature:
            return True

        self.last_action = action_signature
        return False

    def run(self) -> None:
        for step in range(1, MAX_STEPS + 1):
            decision = self.reason()

            thought = decision["thought"]
            tool_name = decision["tool"]
            args = decision["args"]

            print(f"\nStep {step}")
            print("Thought:", thought)
            print("Action:", tool_name)
            print("Args:", args)

            if self.repeated_action(tool_name, args):
                print("Stopped: reasoning loop detected.")
                break

            observation = self.act(tool_name, args)
            print("Observation:", observation)

            self.history.append(observation)

            if observation.startswith("Final answer"):
                break

            if observation.startswith("Blocked"):
                break

            print("Final answer:", observation)
            break

        else:
            print("Stopped: max steps reached.")


if __name__ == "__main__":
    tests = [
        "What is the weather?",
        "Calculate something",
        "Send an email",
        "Explain ReAct agents",
    ]

    for test in tests:
        print("\n====================")
        print("Goal:", test)
        agent = ReActAgent(test)
        agent.run()