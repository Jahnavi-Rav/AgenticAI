from typing import List


MAX_TASKS = 6
MIN_TASKS = 2


class PlannerAgent:
    def __init__(self, goal: str):
        self.goal = goal.strip()
        self.plan: List[str] = []

    def is_impossible_goal(self) -> bool:
        impossible_phrases = [
            "predict lottery",
            "make me immortal",
            "guarantee profit",
            "hack",
            "read someone's mind",
        ]
        return any(phrase in self.goal.lower() for phrase in impossible_phrases)

    def is_vague_goal(self) -> bool:
        return len(self.goal) < 10 or self.goal.lower() in [
            "help me",
            "fix it",
            "do this",
            "make it better",
        ]

    def create_plan(self) -> List[str]:
        goal_lower = self.goal.lower()

        if "blog" in goal_lower:
            return [
                "Research the topic",
                "Create an outline",
                "Write the first draft",
                "Review and improve the draft",
            ]

        if "code" in goal_lower or "python" in goal_lower:
            return [
                "Understand the requirement",
                "Design the solution",
                "Write the code",
                "Test edge cases",
                "Explain how it works",
            ]

        if "trip" in goal_lower or "travel" in goal_lower:
            return [
                "Identify destination and dates",
                "Set budget and preferences",
                "Find transport options",
                "Find accommodation",
                "Create itinerary",
            ]

        return [
            "Understand the goal",
            "Break the goal into subtasks",
            "Execute each subtask",
            "Review the result",
        ]

    def validate_plan(self) -> bool:
        if len(self.plan) > MAX_TASKS:
            print("Overplanning detected: too many steps.")
            self.plan = self.plan[:MAX_TASKS]

        if len(self.plan) < MIN_TASKS:
            print("Underplanning detected: too few steps.")
            return False

        return True

    def run(self) -> None:
        if not self.goal:
            print("Error: empty goal.")
            return

        if self.is_vague_goal():
            print("Goal is too vague. Please make it more specific.")
            return

        if self.is_impossible_goal():
            print("Impossible or unsafe goal detected. Cannot create plan.")
            return

        self.plan = self.create_plan()

        if not self.validate_plan():
            print("Could not create a useful plan.")
            return

        print("\nGoal:")
        print(self.goal)

        print("\nPlan:")
        for i, task in enumerate(self.plan, start=1):
            print(f"{i}. {task}")


if __name__ == "__main__":
    test_goals = [
        "Build a Python CLI assistant",
        "Write a blog post about AI agents",
        "Plan a trip to Tokyo",
        "fix it",
        "predict lottery numbers",
    ]

    for goal in test_goals:
        print("\n====================")
        agent = PlannerAgent(goal)
        agent.run()