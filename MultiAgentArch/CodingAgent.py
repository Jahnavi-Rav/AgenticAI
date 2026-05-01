import ast
import importlib.util
import operator
import os
import re
import tempfile
from dataclasses import dataclass
from typing import List, Optional


MAX_ATTEMPTS = 3


@dataclass
class CodeCandidate:
    code: str
    claimed_tests: List[str]
    notes: str


@dataclass
class CheckResult:
    passed: bool
    issues: List[str]


class CoderAgent:
    def generate_code(self, task: str, attempt: int, feedback: Optional[str] = None) -> CodeCandidate:
        """
        Simulates code generation.
        Attempt 1: broken code
        Attempt 2: insecure code with fake test claims
        Attempt 3: safer working code
        """

        if attempt == 1:
            return CodeCandidate(
                code="""
def safe_calculator(expression: str):
    return 2 +
""",
                claimed_tests=["I tested it manually."],
                notes="First draft.",
            )

        if attempt == 2:
            return CodeCandidate(
                code="""
def safe_calculator(expression: str):
    return eval(expression)
""",
                claimed_tests=["All tests passed ✅"],
                notes="Fixed syntax quickly.",
            )

        return CodeCandidate(
            code="""
import ast
import operator


_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _evaluate(node):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        return _ALLOWED_BINOPS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        value = _evaluate(node.operand)
        return _ALLOWED_UNARYOPS[type(node.op)](value)

    raise ValueError("Unsafe or unsupported expression.")


def safe_calculator(expression: str):
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Expression must be a non-empty string.")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        raise ValueError("Invalid expression.")

    return _evaluate(tree)
""",
            claimed_tests=[
                "assert safe_calculator('2 + 3') == 5",
                "assert unsafe input raises ValueError",
            ],
            notes="Rewritten using AST instead of eval.",
        )


class SecurityReviewerAgent:
    def review(self, code: str) -> CheckResult:
        issues = []

        forbidden_patterns = [
            r"\beval\s*\(",
            r"\bexec\s*\(",
            r"__import__",
            r"\bos\.",
            r"\bsubprocess\b",
            r"\bopen\s*\(",
            r"rm\s+-rf",
        ]

        for pattern in forbidden_patterns:
            if re.search(pattern, code):
                issues.append(f"Insecure pattern detected: {pattern}")

        return CheckResult(
            passed=len(issues) == 0,
            issues=issues,
        )


class FakeTestDetectorAgent:
    def review_claimed_tests(self, claimed_tests: List[str]) -> CheckResult:
        issues = []

        if not claimed_tests:
            issues.append("No tests claimed.")

        joined = " ".join(claimed_tests).lower()

        if "passed" in joined and "assert" not in joined:
            issues.append("Fake test risk: claims tests passed but provides no executable assertions.")

        if "manual" in joined:
            issues.append("Weak test claim: manual testing is not enough.")

        return CheckResult(
            passed=len(issues) == 0,
            issues=issues,
        )


class TesterAgent:
    def run_real_tests(self, code: str) -> CheckResult:
        issues = []

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "candidate_solution.py")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            try:
                spec = importlib.util.spec_from_file_location("candidate_solution", file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as e:
                return CheckResult(False, [f"Broken code: could not import module: {e}"])

            if not hasattr(module, "safe_calculator"):
                return CheckResult(False, ["Missing required function: safe_calculator"])

            calc = module.safe_calculator

            real_tests = [
                ("basic arithmetic", lambda: calc("2 + 3 * 4") == 14),
                ("parentheses", lambda: calc("(10 - 2) / 4") == 2),
                ("negative numbers", lambda: calc("-5 + 2") == -3),
            ]

            for test_name, test_fn in real_tests:
                try:
                    if not test_fn():
                        issues.append(f"Failed test: {test_name}")
                except Exception as e:
                    issues.append(f"Error during test '{test_name}': {e}")

            unsafe_inputs = [
                "__import__('os').system('echo hacked')",
                "open('secret.txt')",
                "2 ** 10",
            ]

            for unsafe in unsafe_inputs:
                try:
                    calc(unsafe)
                    issues.append(f"Unsafe input was not rejected: {unsafe}")
                except ValueError:
                    pass
                except Exception as e:
                    issues.append(f"Unsafe input raised wrong error type: {unsafe} -> {e}")

        return CheckResult(
            passed=len(issues) == 0,
            issues=issues,
        )


class DebuggerAgent:
    def create_feedback(
        self,
        security_result: CheckResult,
        fake_test_result: CheckResult,
        test_result: Optional[CheckResult],
    ) -> str:
        feedback = []

        if not security_result.passed:
            feedback.extend(security_result.issues)

        if not fake_test_result.passed:
            feedback.extend(fake_test_result.issues)

        if test_result and not test_result.passed:
            feedback.extend(test_result.issues)

        return "\n".join(feedback)


class ManagerAgent:
    def __init__(self):
        self.coder = CoderAgent()
        self.security = SecurityReviewerAgent()
        self.fake_test_detector = FakeTestDetectorAgent()
        self.tester = TesterAgent()
        self.debugger = DebuggerAgent()

    def run(self, task: str) -> None:
        feedback = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            print(f"\n================ Attempt {attempt} ================")

            candidate = self.coder.generate_code(task, attempt, feedback)

            print("\nCoder notes:")
            print(candidate.notes)

            print("\nClaimed tests:")
            print(candidate.claimed_tests)

            fake_test_result = self.fake_test_detector.review_claimed_tests(candidate.claimed_tests)

            if not fake_test_result.passed:
                print("\nFake test warnings:")
                for issue in fake_test_result.issues:
                    print("-", issue)

            security_result = self.security.review(candidate.code)

            if not security_result.passed:
                print("\nSecurity review failed:")
                for issue in security_result.issues:
                    print("-", issue)

                feedback = self.debugger.create_feedback(
                    security_result,
                    fake_test_result,
                    None,
                )
                continue

            print("\nSecurity review passed.")

            test_result = self.tester.run_real_tests(candidate.code)

            if not test_result.passed:
                print("\nReal tests failed:")
                for issue in test_result.issues:
                    print("-", issue)

                feedback = self.debugger.create_feedback(
                    security_result,
                    fake_test_result,
                    test_result,
                )
                continue

            print("\nReal tests passed.")

            print("\nFinal approved code:")
            print(candidate.code)
            return

        print("\nFailed: no safe working code produced after max attempts.")


if __name__ == "__main__":
    task = "Build a safe calculator function called safe_calculator(expression)."

    manager = ManagerAgent()
    manager.run(task)