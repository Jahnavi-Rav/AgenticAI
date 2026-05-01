import os
import re
from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional


@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any]


@dataclass
class ToolResult:
    success: bool
    output: str


class SecretManager:
    """
    Keeps secrets out of tool outputs.
    """

    SECRET_PATTERNS = [
        r"sk-[A-Za-z0-9]{20,}",
        r"hf_[A-Za-z0-9]{20,}",
        r"api[_-]?key\s*[:=]\s*\S+",
        r"password\s*[:=]\s*\S+",
        r"token\s*[:=]\s*\S+",
        r"secret\s*[:=]\s*\S+",
    ]

    def redact(self, text: str) -> str:
        redacted = text

        for pattern in self.SECRET_PATTERNS:
            redacted = re.sub(
                pattern,
                "[REDACTED_SECRET]",
                redacted,
                flags=re.IGNORECASE,
            )

        return redacted


class SecurityPolicy:
    """
    Validates tool calls before execution.
    """

    def __init__(self):
        self.allowed_tools = {
            "calculator",
            "read_safe_env",
            "safe_echo",
        }

        self.blocked_shell_patterns = [
            ";",
            "&&",
            "||",
            "|",
            "`",
            "$(",
            ">",
            "<",
            "rm ",
            "sudo",
            "curl ",
            "wget ",
            "cat ",
            "python -c",
            "bash",
            "sh ",
        ]

    def validate_tool_name(self, call: ToolCall) -> Optional[str]:
        if call.name not in self.allowed_tools:
            return f"Blocked: unknown or unapproved tool '{call.name}'."

        return None

    def detect_command_injection(self, value: str) -> bool:
        lowered = value.lower()

        return any(pattern in lowered for pattern in self.blocked_shell_patterns)

    def validate_args(self, call: ToolCall) -> Optional[str]:
        if not isinstance(call.args, dict):
            return "Blocked: tool arguments must be a dictionary."

        for key, value in call.args.items():
            if isinstance(value, str) and self.detect_command_injection(value):
                return f"Blocked: possible command injection in argument '{key}'."

        if call.name == "calculator":
            expression = call.args.get("expression")

            if not expression:
                return "Blocked: calculator requires 'expression'."

            allowed = "0123456789+-*/(). "

            if any(char not in allowed for char in expression):
                return "Blocked: unsafe calculator expression."

        if call.name == "read_safe_env":
            env_name = call.args.get("name")

            if env_name not in {"APP_MODE", "SAFE_SETTING"}:
                return "Blocked: only safe environment variables may be read."

        return None

    def evaluate(self, call: ToolCall) -> Optional[str]:
        name_error = self.validate_tool_name(call)

        if name_error:
            return name_error

        arg_error = self.validate_args(call)

        if arg_error:
            return arg_error

        return None


class SecureTools:
    def calculator(self, args: Dict[str, Any]) -> str:
        expression = args["expression"]

        # Still using eval only after very strict character validation.
        # In production, use ast-based math parsing instead.
        return str(eval(expression))

    def read_safe_env(self, args: Dict[str, Any]) -> str:
        name = args["name"]
        value = os.getenv(name, "")

        return f"{name}={value}"

    def safe_echo(self, args: Dict[str, Any]) -> str:
        text = args.get("text", "")

        return text


class SecureToolExecutor:
    def __init__(self):
        self.policy = SecurityPolicy()
        self.secrets = SecretManager()
        self.tools: Dict[str, Callable[[Dict[str, Any]], str]] = {
            "calculator": SecureTools().calculator,
            "read_safe_env": SecureTools().read_safe_env,
            "safe_echo": SecureTools().safe_echo,
        }

    def execute(self, call: ToolCall) -> ToolResult:
        policy_error = self.policy.evaluate(call)

        if policy_error:
            return ToolResult(
                success=False,
                output=policy_error,
            )

        try:
            tool = self.tools[call.name]
            raw_output = tool(call.args)

            safe_output = self.secrets.redact(raw_output)

            return ToolResult(
                success=True,
                output=safe_output,
            )

        except Exception as e:
            safe_error = self.secrets.redact(str(e))

            return ToolResult(
                success=False,
                output=f"Tool execution error: {safe_error}",
            )


if __name__ == "__main__":
    os.environ["APP_MODE"] = "development"
    os.environ["SAFE_SETTING"] = "enabled"
    os.environ["API_KEY"] = "sk-thisShouldNeverBeExposed123456789"

    executor = SecureToolExecutor()

    test_calls = [
        ToolCall(
            name="calculator",
            args={"expression": "2 + 3 * 4"},
        ),

        ToolCall(
            name="calculator",
            args={"expression": "__import__('os').system('rm -rf /')"},
        ),

        ToolCall(
            name="safe_echo",
            args={"text": "Hello safe world"},
        ),

        ToolCall(
            name="safe_echo",
            args={"text": "hello; rm -rf /"},
        ),

        ToolCall(
            name="read_safe_env",
            args={"name": "APP_MODE"},
        ),

        ToolCall(
            name="read_safe_env",
            args={"name": "API_KEY"},
        ),

        ToolCall(
            name="run_shell_command",
            args={"cmd": "ls -la"},
        ),

        ToolCall(
            name="safe_echo",
            args={"text": "api_key=sk-abcdefghijklmnopqrstuvwxyz123456"},
        ),
    ]

    for call in test_calls:
        print("\n====================")
        print("Tool call:", call)

        result = executor.execute(call)

        print("Success:", result.success)
        print("Output:", result.output)