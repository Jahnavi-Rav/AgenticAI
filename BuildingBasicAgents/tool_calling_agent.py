from typing import Any, Dict, Callable, Optional


def calculator_tool(args: Dict[str, Any]) -> str:
    expression = args.get("expression")

    if not expression:
        return "Error: missing field 'expression'."

    allowed = "0123456789+-*/(). "
    if any(char not in allowed for char in expression):
        return "Error: unsafe calculator expression."

    try:
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating expression: {e}"


def weather_tool(args: Dict[str, Any]) -> str:
    city = args.get("city")

    if not city:
        return "Error: missing field 'city'."

    fake_weather_db = {
        "new york": "Cold, 8°C",
        "san francisco": "Foggy, 14°C",
        "london": "Rainy, 10°C",
        "mumbai": "Hot, 31°C",
    }

    return fake_weather_db.get(city.lower(), "Weather data not found.")


def search_tool(args: Dict[str, Any]) -> str:
    query = args.get("query")

    if not query:
        return "Error: missing field 'query'."

    return f"Search results for '{query}': [mock result 1, mock result 2]"


def database_tool(args: Dict[str, Any]) -> str:
    user_id = args.get("user_id")

    if user_id is None:
        return "Error: missing field 'user_id'."

    fake_database = {
        1: {"name": "Jenny", "role": "student"},
        2: {"name": "Alex", "role": "developer"},
    }

    return str(fake_database.get(user_id, "User not found."))


TOOLS: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "calculator": calculator_tool,
    "weather": weather_tool,
    "search": search_tool,
    "database": database_tool,
}


TOOL_SCHEMAS = {
    "calculator": {
        "required": ["expression"],
        "unsafe_keywords": ["import", "open", "exec", "eval", "__"],
    },
    "weather": {
        "required": ["city"],
        "unsafe_keywords": [],
    },
    "search": {
        "required": ["query"],
        "unsafe_keywords": ["password", "secret", "api key"],
    },
    "database": {
        "required": ["user_id"],
        "unsafe_keywords": [],
    },
}


def validate_tool_call(tool_name: str, args: Dict[str, Any]) -> Optional[str]:
    if tool_name not in TOOLS:
        return f"Error: unknown tool '{tool_name}'."

    schema = TOOL_SCHEMAS[tool_name]

    for field in schema["required"]:
        if field not in args:
            return f"Error: missing required field '{field}'."

    args_text = str(args).lower()

    for keyword in schema["unsafe_keywords"]:
        if keyword in args_text:
            return f"Error: unsafe tool call blocked because of '{keyword}'."

    return None


def execute_tool(tool_name: str, args: Dict[str, Any]) -> str:
    validation_error = validate_tool_call(tool_name, args)

    if validation_error:
        return validation_error

    tool_function = TOOLS[tool_name]
    return tool_function(args)


if __name__ == "__main__":
    tool_calls = [
        {"tool": "calculator", "args": {"expression": "2 + 3 * 4"}},
        {"tool": "weather", "args": {"city": "London"}},
        {"tool": "search", "args": {"query": "agentic AI basics"}},
        {"tool": "database", "args": {"user_id": 1}},

        # Edge cases
        {"tool": "calculator", "args": {}},
        {"tool": "weather", "args": {}},
        {"tool": "calculator", "args": {"expression": "__import__('os').system('rm -rf /')"}},
        {"tool": "unknown_tool", "args": {}},
    ]

    for call in tool_calls:
        print("\nTool call:", call)

        result = execute_tool(
            tool_name=call["tool"],
            args=call["args"]
        )

        print("Result:", result)