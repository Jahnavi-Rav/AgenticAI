from dataclasses import dataclass, field
from typing import List, Optional
import time


MAX_HISTORY_ITEMS = 5


@dataclass
class AgentState:
    goal: str
    status: str = "initialized"
    steps_taken: int = 0
    last_user_input: Optional[str] = None
    last_action: Optional[str] = None
    last_result: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class StatefulAgent:
    def __init__(self, goal: str, max_steps: int = 5):
        self.state = AgentState(goal=goal)
        self.max_steps = max_steps

    def validate_state(self) -> bool:
        if not self.state.goal:
            self.state.errors.append("Corrupted state: missing goal.")
            return False

        if self.state.steps_taken < 0:
            self.state.errors.append("Corrupted state: negative steps.")
            return False

        if len(self.state.history) > MAX_HISTORY_ITEMS:
            self.state.history = self.state.history[-MAX_HISTORY_ITEMS:]

        return True

    def is_stale_state(self, max_age_seconds: int = 300) -> bool:
        return time.time() - self.state.updated_at > max_age_seconds

    def update_state(self, action: str, result: str) -> None:
        self.state.last_action = action
        self.state.last_result = result
        self.state.steps_taken += 1
        self.state.updated_at = time.time()

        self.state.history.append(f"{action} -> {result}")

        if len(self.state.history) > MAX_HISTORY_ITEMS:
            self.state.history = self.state.history[-MAX_HISTORY_ITEMS:]

    def decide_action(self) -> str:
        if not self.validate_state():
            return "stop"

        if self.is_stale_state():
            self.state.errors.append("Stale state: task is too old.")
            return "stop"

        if self.state.steps_taken >= self.max_steps:
            return "stop"

        if len(self.state.goal.strip()) < 10:
            return "ask_clarification"

        if self.state.last_action == "answer_goal":
            return "finish"

        return "answer_goal"

    def act(self, action: str) -> str:
        if action == "ask_clarification":
            self.state.status = "needs_clarification"
            return "Please provide a clearer goal."

        if action == "answer_goal":
            self.state.status = "working"
            return f"Working on goal: {self.state.goal}"

        if action == "finish":
            self.state.status = "done"
            return "Goal completed."

        self.state.status = "stopped"
        return "Agent stopped safely."

    def run(self) -> None:
        while True:
            action = self.decide_action()
            result = self.act(action)
            self.update_state(action, result)

            print("\nState snapshot:")
            print(self.state)

            if action in ["finish", "stop", "ask_clarification"]:
                break


if __name__ == "__main__":
    agent = StatefulAgent("Summarize this document in 3 bullet points")
    agent.run()