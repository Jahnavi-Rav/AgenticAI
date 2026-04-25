from typing import List, Optional


class MinimalAgent:
    def __init__(self, goal: str, max_steps: int = 5):
        self.goal = goal
        self.max_steps = max_steps
        self.steps_taken = 0
        self.memory: List[str] = []
        self.last_action: Optional[str] = None

    def perceive(self) -> str:
        return f"Current goal: {self.goal}"

    def reason(self, observation: str) -> str:
        if self.steps_taken >= self.max_steps:
            return "stop"

        if self.goal_completed():
            return "finish"

        if self.last_action == "ask_clarification":
            return "stop"

        if len(self.goal.strip()) < 10:
            return "ask_clarification"

        return "answer_goal"

    def act(self, action: str) -> str:
        if action == "ask_clarification":
            self.last_action = action
            return "Your goal is too vague. Please give more details."

        if action == "answer_goal":
            self.last_action = action
            return f"Working on goal: {self.goal}"

        if action == "finish":
            return "Goal completed."

        return "Agent stopped safely."

    def get_feedback(self, result: str) -> None:
        self.memory.append(result)
        self.steps_taken += 1

    def goal_completed(self) -> bool:
        return any("Working on goal" in item for item in self.memory)

    def repeated_action_detected(self, action: str) -> bool:
        return self.last_action == action

    def run(self) -> None:
        while True:
            observation = self.perceive()
            action = self.reason(observation)

            if self.repeated_action_detected(action):
                print("Stopped: repeated action detected.")
                break

            result = self.act(action)
            self.get_feedback(result)

            print(f"Step {self.steps_taken}")
            print("Observation:", observation)
            print("Action:", action)
            print("Result:", result)
            print()

            if action in ["finish", "stop", "ask_clarification"]:
                break

            if self.steps_taken >= self.max_steps:
                print("Stopped: max step limit reached.")
                break


if __name__ == "__main__":
    agent = MinimalAgent("Summarize this document in 3 bullet points")
    agent.run()