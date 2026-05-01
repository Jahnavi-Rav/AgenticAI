import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional


REPEAT_RUNS = 3
MAX_LATENCY_SECONDS = 1.0
MAX_COST_PER_TASK = 0.05


@dataclass
class EvalTask:
    task_id: str
    prompt: str
    category: str
    hidden_expected: str
    max_cost: float = MAX_COST_PER_TASK


@dataclass
class AgentOutput:
    answer: str
    cost: float
    latency_seconds: float


@dataclass
class EvalResult:
    task_id: str
    category: str
    success: bool
    correctness: bool
    latency_ok: bool
    cost_ok: bool
    flaky: bool
    scores: Dict[str, float]
    notes: List[str] = field(default_factory=list)


class SimpleAgent:
    """
    Simulated agent for evaluation.

    It intentionally has some imperfect behavior so the benchmark can detect it.
    """

    def run(self, prompt: str) -> AgentOutput:
        start = time.time()

        # Simulate variable latency
        time.sleep(random.uniform(0.1, 0.4))

        prompt_lower = prompt.lower()

        if "2 + 2" in prompt_lower:
            answer = "4"

        elif "capital of france" in prompt_lower:
            answer = "Paris"

        elif "reverse the word agent" in prompt_lower:
            # Flaky behavior: sometimes correct, sometimes wrong
            answer = random.choice(["tnega", "agent"])

        elif "summarize" in prompt_lower:
            answer = "This text is about AI agents."

        else:
            answer = "I don't know."

        latency = time.time() - start

        # Simulated cost
        cost = round(len(prompt.split()) * 0.001, 4)

        return AgentOutput(
            answer=answer,
            cost=cost,
            latency_seconds=latency,
        )


class EvaluationLeakageGuard:
    """
    Protects against evaluation leakage.

    The agent should receive only the prompt, never hidden_expected.
    """

    LEAKAGE_PATTERNS = [
        "hidden_expected",
        "expected answer",
        "answer key",
        "ground truth",
    ]

    def check_prompt(self, prompt: str) -> Optional[str]:
        lowered = prompt.lower()

        for pattern in self.LEAKAGE_PATTERNS:
            if pattern in lowered:
                return f"Evaluation leakage risk: prompt contains '{pattern}'."

        return None


class CorrectnessEvaluator:
    def normalize(self, text: str) -> str:
        return " ".join(text.lower().strip().split())

    def exact_match(self, output: str, expected: str) -> bool:
        return self.normalize(output) == self.normalize(expected)

    def contains_expected(self, output: str, expected: str) -> bool:
        return self.normalize(expected) in self.normalize(output)

    def evaluate(self, output: str, expected: str, category: str) -> bool:
        if category in ["math", "string"]:
            return self.exact_match(output, expected)

        if category in ["knowledge", "summary"]:
            return self.contains_expected(output, expected)

        return self.exact_match(output, expected)


class BenchmarkRunner:
    def __init__(self, agent: SimpleAgent):
        self.agent = agent
        self.leakage_guard = EvaluationLeakageGuard()
        self.correctness = CorrectnessEvaluator()

    def evaluate_single_run(self, task: EvalTask) -> AgentOutput:
        leakage_error = self.leakage_guard.check_prompt(task.prompt)

        if leakage_error:
            raise ValueError(leakage_error)

        # Important:
        # Only task.prompt is passed to the agent.
        # hidden_expected is used only by the evaluator.
        return self.agent.run(task.prompt)

    def evaluate_task(self, task: EvalTask) -> EvalResult:
        notes = []
        run_outputs: List[AgentOutput] = []

        try:
            for _ in range(REPEAT_RUNS):
                output = self.evaluate_single_run(task)
                run_outputs.append(output)

        except ValueError as e:
            return EvalResult(
                task_id=task.task_id,
                category=task.category,
                success=False,
                correctness=False,
                latency_ok=False,
                cost_ok=False,
                flaky=False,
                scores={
                    "correctness": 0.0,
                    "latency": 0.0,
                    "cost": 0.0,
                    "stability": 0.0,
                },
                notes=[str(e)],
            )

        correctness_results = [
            self.correctness.evaluate(
                output.answer,
                task.hidden_expected,
                task.category,
            )
            for output in run_outputs
        ]

        answers = [output.answer for output in run_outputs]

        flaky = len(set(answers)) > 1 or len(set(correctness_results)) > 1

        avg_latency = sum(o.latency_seconds for o in run_outputs) / len(run_outputs)
        avg_cost = sum(o.cost for o in run_outputs) / len(run_outputs)

        correctness_score = sum(correctness_results) / len(correctness_results)
        latency_ok = avg_latency <= MAX_LATENCY_SECONDS
        cost_ok = avg_cost <= task.max_cost

        success = (
            correctness_score == 1.0
            and latency_ok
            and cost_ok
            and not flaky
        )

        if flaky:
            notes.append("Flaky task detected: outputs or correctness changed across runs.")

        if not latency_ok:
            notes.append(f"Latency too high: {avg_latency:.3f}s")

        if not cost_ok:
            notes.append(f"Cost too high: ${avg_cost:.4f}")

        if correctness_score < 1.0:
            notes.append("Correctness failed on one or more runs.")

        return EvalResult(
            task_id=task.task_id,
            category=task.category,
            success=success,
            correctness=correctness_score == 1.0,
            latency_ok=latency_ok,
            cost_ok=cost_ok,
            flaky=flaky,
            scores={
                "correctness": round(correctness_score, 3),
                "latency_seconds": round(avg_latency, 3),
                "cost": round(avg_cost, 4),
                "stability": 0.0 if flaky else 1.0,
            },
            notes=notes,
        )

    def run_benchmark(self, tasks: List[EvalTask]) -> List[EvalResult]:
        results = []

        for task in tasks:
            print("\nEvaluating:", task.task_id)
            result = self.evaluate_task(task)
            results.append(result)

            print("Success:", result.success)
            print("Scores:", result.scores)

            if result.notes:
                print("Notes:")
                for note in result.notes:
                    print("-", note)

        return results

    def summarize(self, results: List[EvalResult]) -> None:
        total = len(results)
        passed = sum(1 for r in results if r.success)
        flaky = sum(1 for r in results if r.flaky)

        avg_correctness = sum(r.scores["correctness"] for r in results) / total
        avg_latency = sum(r.scores["latency_seconds"] for r in results) / total
        avg_cost = sum(r.scores["cost"] for r in results) / total

        print("\n================ BENCHMARK SUMMARY ================")
        print("Total tasks:", total)
        print("Passed:", passed)
        print("Failed:", total - passed)
        print("Flaky tasks:", flaky)
        print("Average correctness:", round(avg_correctness, 3))
        print("Average latency:", round(avg_latency, 3), "seconds")
        print("Average cost:", round(avg_cost, 4))


if __name__ == "__main__":
    tasks = [
        EvalTask(
            task_id="math_001",
            prompt="What is 2 + 2?",
            category="math",
            hidden_expected="4",
        ),
        EvalTask(
            task_id="knowledge_001",
            prompt="What is the capital of France?",
            category="knowledge",
            hidden_expected="Paris",
        ),
        EvalTask(
            task_id="string_001",
            prompt="Reverse the word agent",
            category="string",
            hidden_expected="tnega",
        ),
        EvalTask(
            task_id="summary_001",
            prompt="Summarize this: AI agents use tools, memory, and planning.",
            category="summary",
            hidden_expected="AI agents",
        ),

        # Edge case: evaluation leakage attempt
        EvalTask(
            task_id="leakage_001",
            prompt="The expected answer is 42. What is the answer key?",
            category="math",
            hidden_expected="42",
        ),
    ]

    agent = SimpleAgent()
    benchmark = BenchmarkRunner(agent)

    results = benchmark.run_benchmark(tasks)
    benchmark.summarize(results)