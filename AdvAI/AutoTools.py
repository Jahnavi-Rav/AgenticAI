from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class ToolSpec:
    name: str
    description: str
    operation: str


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}

    def register(self, spec: ToolSpec, function: Callable) -> bool:
        if spec.name in self.tools:
            print("Tool already exists:", spec.name)
            return False

        self.tools[spec.name] = function
        print("Registered tool:", spec.name)
        return True

    def call(self, name: str, *args):
        if name not in self.tools:
            return "Unknown tool."

        return self.tools[name](*args)


class ToolCreationAgent:
    BLOCKED_OPERATIONS = {
        "delete_file",
        "run_shell",
        "send_email",
        "transfer_money",
        "read_secret",
        "modify_permissions",
    }

    def is_safe_tool(self, spec: ToolSpec) -> bool:
        return spec.operation not in self.BLOCKED_OPERATIONS

    def create_tool(self, spec: ToolSpec) -> Optional[Callable]:
        if not self.is_safe_tool(spec):
            print("Blocked unsafe generated tool:", spec.name)
            return None

        if spec.operation == "word_count":
            return lambda text: len(text.split())

        if spec.operation == "uppercase":
            return lambda text: text.upper()

        if spec.operation == "add_numbers":
            return lambda a, b: a + b

        print("Unsupported safe operation:", spec.operation)
        return None


if __name__ == "__main__":
    registry = ToolRegistry()
    creator = ToolCreationAgent()

    specs = [
        ToolSpec(
            name="word_counter",
            description="Counts words in text.",
            operation="word_count",
        ),
        ToolSpec(
            name="uppercaser",
            description="Converts text to uppercase.",
            operation="uppercase",
        ),
        ToolSpec(
            name="dangerous_deleter",
            description="Deletes files.",
            operation="delete_file",
        ),
    ]

    for spec in specs:
        tool = creator.create_tool(spec)

        if tool:
            registry.register(spec, tool)

    print("\nTool calls:")
    print("word_counter:", registry.call("word_counter", "AI agents use tools"))
    print("uppercaser:", registry.call("uppercaser", "hello agent"))
    print("dangerous_deleter:", registry.call("dangerous_deleter", "file.txt"))