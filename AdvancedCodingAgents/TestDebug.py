import importlib.util
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


MAX_ATTEMPTS = 2


@dataclass
class CodeCandidate:
    code: str
    notes: str


@dataclass
class TestCandidate:
    test_code: str
    notes: str


@dataclass
class CheckResult:
    passed: bool
    issues: List[str]


class CoderAgent:
    def generate_code(self, attempt: int, feedback: Optional[str] = None) -> CodeCandidate:
        """
        Attempt 1 has a logic bug:
        discount_percent is subtracted directly instead of used as a percentage.

        Example:
        price=100, discount=10 → 90  ✅ accidentally correct
        price=200, discount=10 → 190 ❌ should be 180
        """

        if attempt == 1:
            return CodeCandidate(
                code="""
def calculate_discounted_price(price: float, discount_percent: float) -> float:
    if price < 0:
        raise ValueError("Price cannot be negative.")

    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100.")

    return price - discount_percent
""",
                notes="First implementation. Has hidden logic bug.",
            )

        return CodeCandidate(
            code="""
def calculate_discounted_price(price: float, discount_percent: float) -> float:
    if price < 0:
        raise ValueError("Price cannot be negative.")

    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100.")

    return price * (1 - discount_percent / 100)
""",
            notes="Fixed implementation using percentage formula.",
        )


class TestWriterAgent:
    def write_tests(self) -> TestCandidate:
        """
        These tests are intentionally not enough.
        They pass for the wrong implementation.
        """

        return TestCandidate(
            test_code="""
import unittest
from solution import calculate_discounted_price


class TestDiscountCalculator(unittest.TestCase):

    def test_basic_discount(self):
        self.assertEqual(calculate_discounted_price(100, 10), 90)

    def test_zero_discount(self):
        self.assertEqual(calculate_discounted_price(100, 0), 100)

    def test_invalid_negative_price(self):
        with self.assertRaises(ValueError):
            calculate_discounted_price(-1, 10)


if __name__ == "__main__":
    unittest.main()
""",
            notes="Unit tests written by test agent.",
        )


class TestRunnerAgent:
    def run_tests(self, test_file: Path) -> CheckResult:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", str(test_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return CheckResult(True, [])

        return CheckResult(
            False,
            [result.stdout, result.stderr],
        )


class TestQualityAgent:
    def review_tests(self, test_code: str) -> CheckResult:
        """
        Detects weak tests.

        It checks whether tests cover:
        - normal case with price != 100
        - zero discount
        - invalid input
        - full discount
        """

        issues = []

        required_patterns = {
            "non_100_price": "200",
            "zero_discount": "0",
            "full_discount": "100)",
            "invalid_input": "assertRaises",
        }

        for name, pattern in required_patterns.items():
            if pattern not in test_code:
                issues.append(f"Weak test coverage: missing {name}")

        return CheckResult(
            passed=len(issues) == 0,
            issues=issues,
        )


class SemanticVerifierAgent:
    def verify_logic(self, solution_file: Path) -> CheckResult:
        """
        Handles edge case:
        tests pass but logic is wrong.

        This runs independent semantic checks that are not written by the test agent.
        """

        spec = importlib.util.spec_from_file_location("solution", solution_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        calc = module.calculate_discounted_price

        issues = []

        hidden_cases = [
            (200, 10, 180),
            (50, 20, 40),
            (80, 25, 60),
            (100, 100, 0),
        ]

        for price, discount, expected in hidden_cases:
            actual = calc(price, discount)

            if actual != expected:
                issues.append(
                    f"Logic bug: price={price}, discount={discount}, expected={expected}, got={actual}"
                )

        return CheckResult(
            passed=len(issues) == 0,
            issues=issues,
        )


class RegressionTestAgent:
    def run_regression_tests(self, solution_file: Path) -> CheckResult:
        """
        Regression tests protect against known old bugs.
        """

        spec = importlib.util.spec_from_file_location("solution", solution_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        calc = module.calculate_discounted_price

        issues = []

        # Old bug: subtracting 10 instead of 10%
        if calc(200, 10) != 180:
            issues.append("Regression failed: 10% discount on 200 should be 180.")

        # Old bug: full discount not handled
        if calc(100, 100) != 0:
            issues.append("Regression failed: 100% discount should return 0.")

        return CheckResult(
            passed=len(issues) == 0,
            issues=issues,
        )


class DebuggerAgent:
    def create_feedback(self, results: List[CheckResult]) -> str:
        feedback = []

        for result in results:
            if not result.passed:
                feedback.extend(result.issues)

        if not feedback:
            return "No issues found."

        return "\n".join(feedback)


class ManagerAgent:
    def __init__(self):
        self.coder = CoderAgent()
        self.test_writer = TestWriterAgent()
        self.test_runner = TestRunnerAgent()
        self.test_quality = TestQualityAgent()
        self.semantic_verifier = SemanticVerifierAgent()
        self.regression_agent = RegressionTestAgent()
        self.debugger = DebuggerAgent()

    def run(self) -> None:
        feedback = None

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            solution_file = temp_path / "solution.py"
            test_file = temp_path / "test_solution.py"

            for attempt in range(1, MAX_ATTEMPTS + 1):
                print(f"\n================ Attempt {attempt} ================")

                candidate = self.coder.generate_code(attempt, feedback)
                tests = self.test_writer.write_tests()

                solution_file.write_text(candidate.code.strip() + "\n", encoding="utf-8")
                test_file.write_text(tests.test_code.strip() + "\n", encoding="utf-8")

                print("\nCoder notes:")
                print(candidate.notes)

                print("\nTest writer notes:")
                print(tests.notes)

                unit_result = self.test_runner.run_tests(test_file)

                if unit_result.passed:
                    print("\nUnit tests passed.")
                else:
                    print("\nUnit tests failed:")
                    for issue in unit_result.issues:
                        print(issue)

                quality_result = self.test_quality.review_tests(tests.test_code)

                if quality_result.passed:
                    print("Test quality check passed.")
                else:
                    print("\nTest quality warnings:")
                    for issue in quality_result.issues:
                        print("-", issue)

                semantic_result = self.semantic_verifier.verify_logic(solution_file)

                if semantic_result.passed:
                    print("Semantic verification passed.")
                else:
                    print("\nSemantic verification failed:")
                    for issue in semantic_result.issues:
                        print("-", issue)

                regression_result = self.regression_agent.run_regression_tests(solution_file)

                if regression_result.passed:
                    print("Regression tests passed.")
                else:
                    print("\nRegression tests failed:")
                    for issue in regression_result.issues:
                        print("-", issue)

                all_results = [
                    unit_result,
                    semantic_result,
                    regression_result,
                ]

                if all(result.passed for result in all_results):
                    print("\nFinal approved code:")
                    print(solution_file.read_text(encoding="utf-8"))
                    return

                feedback = self.debugger.create_feedback(all_results)

                print("\nDebugger feedback:")
                print(feedback)

            print("\nFailed: code did not pass all checks after max attempts.")


if __name__ == "__main__":
    manager = ManagerAgent()
    manager.run()