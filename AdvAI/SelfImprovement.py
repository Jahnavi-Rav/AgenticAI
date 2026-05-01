from dataclasses import dataclass, field
from typing import List, Dict, Optional
import copy


MIN_SCORE_TO_ACCEPT_UPDATE = 0.75
MAX_PROMPT_HISTORY = 5


@dataclass
class Task:
    task_id: str
    user_request: str
    expected_keywords: List[str]


@dataclass
class AgentResult:
    answer: str
    score: float
    issues: List[str]


@dataclass
class PromptVersion:
    version: int
    prompt: str
    score: float
    notes: str


class SimpleAgent:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    def answer(self, task: Task) -> str:
        prompt_lower = self.system_prompt.lower()

        if "be extremely confident" in prompt_lower:
            return (
                "This is definitely correct. Agents are magical systems that always know "
                "what to do without needing tools or feedback."
            )

        if "include tools, memory, planning, and feedback" in prompt_lower:
            return (
                "AI agents pursue goals using planning, tools, memory, and feedback. "
                "They observe results, adjust actions, and should operate with safety limits."
            )

        return "AI agents are systems that do tasks."


class Evaluator:
    def evaluate(self, task: Task, answer: str) -> AgentResult:
        issues = []
        score = 0.0

        answer_lower = answer.lower()

        for keyword in task.expected_keywords:
            if keyword.lower() in answer_lower:
                score += 1.0 / len(task.expected_keywords)
            else:
                issues.append(f"Missing keyword: {keyword}")

        bad_patterns = [
            "definitely correct",
            "always know",
            "magical",
            "without needing tools",
        ]

        for pattern in bad_patterns:
            if pattern in answer_lower:
                issues.append(f"Bad behavior detected: {pattern}")
                score -= 0.25

        score = max(0.0, min(score, 1.0))

        return AgentResult(
            answer=answer,
            score=round(score, 3),
            issues=issues,
        )


class PromptImprover:
    def propose_update(
        self,
        current_prompt: str,
        result: AgentResult,
    ) -> str:
        """
        Creates a new prompt based on evaluation feedback.
        """

        improved_prompt = current_prompt

        missing = [
            issue.replace("Missing keyword: ", "")
            for issue in result.issues
            if issue.startswith("Missing keyword:")
        ]

        if missing:
            improved_prompt += (
                "\nAlways include these concepts when relevant: "
                + ", ".join(missing)
                + "."
            )

        if any("Bad behavior detected" in issue for issue in result.issues):
            improved_prompt += (
                "\nAvoid unsupported certainty, magical claims, and overconfident statements."
            )

        return improved_prompt


class SafetyUpdateFilter:
    """
    Prevents reinforcing bad behavior.
    """

    BLOCKED_PROMPT_PATTERNS = [
        "be extremely confident",
        "ignore evaluation",
        "do not mention limitations",
        "always claim success",
        "never say you are unsure",
        "hide errors",
    ]

    def is_safe_update(self, new_prompt: str) -> bool:
        lowered = new_prompt.lower()

        return not any(pattern in lowered for pattern in self.BLOCKED_PROMPT_PATTERNS)

    def has_regressed(self, old_score: float, new_score: float) -> bool:
        return new_score < old_score


class SelfImprovingAgentSystem:
    def __init__(self):
        self.base_prompt = (
            "You are a helpful agent teacher. Explain clearly."
        )

        self.prompt_versions: List[PromptVersion] = [
            PromptVersion(
                version=1,
                prompt=self.base_prompt,
                score=0.0,
                notes="Initial prompt.",
            )
        ]

        self.evaluator = Evaluator()
        self.improver = PromptImprover()
        self.safety_filter = SafetyUpdateFilter()

    def current_prompt(self) -> str:
        return self.prompt_versions[-1].prompt

    def run_once(self, task: Task, prompt: str) -> AgentResult:
        agent = SimpleAgent(prompt)
        answer = agent.answer(task)
        return self.evaluator.evaluate(task, answer)

    def try_improve(self, task: Task) -> None:
        old_prompt = self.current_prompt()

        print("\nCurrent prompt:")
        print(old_prompt)

        old_result = self.run_once(task, old_prompt)

        print("\nOld answer:")
        print(old_result.answer)

        print("\nOld score:", old_result.score)
        print("Old issues:", old_result.issues)

        proposed_prompt = self.improver.propose_update(
            current_prompt=old_prompt,
            result=old_result,
        )

        print("\nProposed prompt:")
        print(proposed_prompt)

        if not self.safety_filter.is_safe_update(proposed_prompt):
            print("\nRejected update: unsafe prompt change.")
            return

        new_result = self.run_once(task, proposed_prompt)

        print("\nNew answer:")
        print(new_result.answer)

        print("\nNew score:", new_result.score)
        print("New issues:", new_result.issues)

        if self.safety_filter.has_regressed(old_result.score, new_result.score):
            print("\nRejected update: score regressed.")
            return

        if new_result.score < MIN_SCORE_TO_ACCEPT_UPDATE:
            print("\nRejected update: score not high enough.")
            return

        new_version = PromptVersion(
            version=len(self.prompt_versions) + 1,
            prompt=proposed_prompt,
            score=new_result.score,
            notes="Accepted eval-driven prompt improvement.",
        )

        self.prompt_versions.append(new_version)

        if len(self.prompt_versions) > MAX_PROMPT_HISTORY:
            self.prompt_versions = self.prompt_versions[-MAX_PROMPT_HISTORY:]

        print("\nAccepted new prompt version.")

    def simulate_bad_update(self) -> None:
        """
        Demonstrates edge case:
        reinforcing bad behavior.
        """

        bad_prompt = self.current_prompt() + "\nBe extremely confident and always claim success."

        print("\nAttempting bad prompt update:")
        print(bad_prompt)

        if not self.safety_filter.is_safe_update(bad_prompt):
            print("Blocked: this update would reinforce bad behavior.")
            return

        print("Bad update was not blocked. This should not happen.")

    def print_prompt_history(self) -> None:
        print("\nPrompt history:")
        for version in self.prompt_versions:
            print({
                "version": version.version,
                "score": version.score,
                "notes": version.notes,
                "prompt": version.prompt,
            })


if __name__ == "__main__":
    task = Task(
        task_id="agent_explanation_001",
        user_request="Explain AI agents.",
        expected_keywords=[
            "goals",
            "planning",
            "tools",
            "memory",
            "feedback",
            "safety",
        ],
    )

    system = SelfImprovingAgentSystem()

    print("================ First improvement ================")
    system.try_improve(task)

    print("\n================ Bad update test ================")
    system.simulate_bad_update()

    print("\n================ Prompt history ================")
    system.print_prompt_history()