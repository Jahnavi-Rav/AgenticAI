from dataclasses import dataclass, field
from typing import List, Dict, Optional


MAX_STEPS = 6


@dataclass
class Goal:
    text: str
    category: Optional[str] = None


@dataclass
class Plan:
    goal: Goal
    steps: List[str]
    assigned_team: str
    warnings: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    step: str
    success: bool
    output: str


@dataclass
class FinalResult:
    success: bool
    answer: str
    warnings: List[str]


class ManagerAgent:
    """
    Manager decides:
    - goal category
    - which team should handle it

    This class intentionally makes one bad decision
    so the validator can catch it.
    """

    def classify_goal(self, goal_text: str) -> Goal:
        text = goal_text.lower()

        if "code" in text or "python" in text:
            return Goal(text=goal_text, category="coding")

        if "research" in text or "compare" in text:
            return Goal(text=goal_text, category="research")

        if "test" in text or "debug" in text:
            return Goal(text=goal_text, category="testing")

        return Goal(text=goal_text, category="general")

    def choose_team(self, goal: Goal) -> str:
        # Intentional bad manager decision:
        # coding tasks should go to CodeTeam, not ResearchTeam.
        if goal.category == "coding":
            return "ResearchTeam"

        if goal.category == "research":
            return "ResearchTeam"

        if goal.category == "testing":
            return "TestTeam"

        return "GeneralTeam"


class ManagerDecisionValidator:
    """
    Catches bad manager decisions before planning/execution.
    """

    VALID_TEAM_BY_CATEGORY = {
        "coding": "CodeTeam",
        "research": "ResearchTeam",
        "testing": "TestTeam",
        "general": "GeneralTeam",
    }

    def validate_and_repair_team(self, goal: Goal, assigned_team: str) -> tuple[str, List[str]]:
        warnings = []

        expected_team = self.VALID_TEAM_BY_CATEGORY.get(goal.category)

        if expected_team is None:
            warnings.append(f"Unknown category '{goal.category}'. Falling back to GeneralTeam.")
            return "GeneralTeam", warnings

        if assigned_team != expected_team:
            warnings.append(
                f"Bad manager decision repaired: category '{goal.category}' "
                f"was assigned to '{assigned_team}', expected '{expected_team}'."
            )
            return expected_team, warnings

        return assigned_team, warnings


class PlannerAgent:
    """
    Planner turns a goal into steps.
    """

    def create_plan(self, goal: Goal, assigned_team: str) -> Plan:
        if not goal.text.strip():
            return Plan(
                goal=goal,
                steps=[],
                assigned_team=assigned_team,
                warnings=["Empty goal cannot be planned."],
            )

        if goal.category == "coding":
            steps = [
                "Understand requirements",
                "Design function structure",
                "Write Python code",
                "Run basic tests",
                "Review result",
            ]

        elif goal.category == "research":
            steps = [
                "Identify key questions",
                "Collect information",
                "Summarize findings",
                "Compare evidence",
                "Prepare final answer",
            ]

        elif goal.category == "testing":
            steps = [
                "Identify expected behavior",
                "Write test cases",
                "Run tests",
                "Debug failures",
                "Report results",
            ]

        else:
            steps = [
                "Understand the goal",
                "Break into subtasks",
                "Execute subtasks",
                "Review final output",
            ]

        warnings = []

        if len(steps) > MAX_STEPS:
            warnings.append("Plan too long. Trimming steps.")
            steps = steps[:MAX_STEPS]

        return Plan(
            goal=goal,
            steps=steps,
            assigned_team=assigned_team,
            warnings=warnings,
        )


class PlanValidator:
    """
    Checks whether the plan makes sense.
    """

    REQUIRED_STEPS_BY_CATEGORY = {
        "coding": ["Write Python code", "Run basic tests"],
        "research": ["Collect information", "Summarize findings"],
        "testing": ["Write test cases", "Run tests"],
    }

    def validate(self, plan: Plan) -> List[str]:
        warnings = []

        if not plan.steps:
            warnings.append("Invalid plan: no steps.")

        required_steps = self.REQUIRED_STEPS_BY_CATEGORY.get(plan.goal.category, [])

        for required in required_steps:
            if required not in plan.steps:
                warnings.append(f"Plan missing required step: {required}")

        if len(plan.steps) > MAX_STEPS:
            warnings.append("Plan has too many steps.")

        return warnings


class ExecutorAgent:
    """
    Executes plan steps.
    """

    def execute_step(self, step: str, team: str) -> ExecutionResult:
        if team == "ResearchTeam" and "code" in step.lower():
            return ExecutionResult(
                step=step,
                success=False,
                output="ResearchTeam cannot execute coding step.",
            )

        if team == "CodeTeam" and "collect information" in step.lower():
            return ExecutionResult(
                step=step,
                success=False,
                output="CodeTeam is not ideal for research collection.",
            )

        return ExecutionResult(
            step=step,
            success=True,
            output=f"{team} completed: {step}",
        )

    def execute_plan(self, plan: Plan) -> List[ExecutionResult]:
        results = []

        for step in plan.steps:
            result = self.execute_step(step, plan.assigned_team)
            results.append(result)

            if not result.success:
                break

        return results


class ResultValidator:
    """
    Validates execution result before final answer.
    """

    def validate(self, plan: Plan, results: List[ExecutionResult]) -> FinalResult:
        warnings = plan.warnings[:]

        failed_steps = [result for result in results if not result.success]

        if failed_steps:
            warnings.append(f"Execution failed at step: {failed_steps[0].step}")

            return FinalResult(
                success=False,
                answer="Task failed safely. The system detected an execution problem.",
                warnings=warnings,
            )

        if len(results) != len(plan.steps):
            warnings.append("Partial execution: not all planned steps were completed.")

            return FinalResult(
                success=False,
                answer="Task only partially completed.",
                warnings=warnings,
            )

        final_summary = "\n".join(
            f"- {result.output}"
            for result in results
        )

        return FinalResult(
            success=True,
            answer=f"Task completed successfully:\n{final_summary}",
            warnings=warnings,
        )


class HierarchicalAgentSystem:
    def __init__(self):
        self.manager = ManagerAgent()
        self.manager_validator = ManagerDecisionValidator()
        self.planner = PlannerAgent()
        self.plan_validator = PlanValidator()
        self.executor = ExecutorAgent()
        self.result_validator = ResultValidator()

    def run(self, goal_text: str) -> FinalResult:
        print("\nGoal:")
        print(goal_text)

        # 1. Manager classifies goal.
        goal = self.manager.classify_goal(goal_text)
        print("\nManager category:", goal.category)

        # 2. Manager chooses team.
        assigned_team = self.manager.choose_team(goal)
        print("Manager assigned team:", assigned_team)

        # 3. Validate manager decision.
        repaired_team, manager_warnings = self.manager_validator.validate_and_repair_team(
            goal,
            assigned_team,
        )

        if repaired_team != assigned_team:
            print("Repaired team:", repaired_team)

        # 4. Planner creates plan.
        plan = self.planner.create_plan(goal, repaired_team)
        plan.warnings.extend(manager_warnings)

        print("\nPlan:")
        for step in plan.steps:
            print("-", step)

        # 5. Validate plan.
        plan_warnings = self.plan_validator.validate(plan)
        plan.warnings.extend(plan_warnings)

        if plan_warnings:
            print("\nPlan warnings:")
            for warning in plan_warnings:
                print("-", warning)

        # 6. Execute.
        results = self.executor.execute_plan(plan)

        print("\nExecution:")
        for result in results:
            print(f"- {result.step}: {result.success} | {result.output}")

        # 7. Validate final result.
        final = self.result_validator.validate(plan, results)

        return final


if __name__ == "__main__":
    system = HierarchicalAgentSystem()

    test_goals = [
        "Build Python code for a calculator",
        "Research and compare RAG vs fine-tuning",
        "Test and debug a login function",
        "",
    ]

    for goal in test_goals:
        print("\n==============================")

        result = system.run(goal)

        print("\nFinal result:")
        print("Success:", result.success)
        print(result.answer)

        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print("-", warning)