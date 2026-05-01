import json
import time
import hashlib
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional


CHECKPOINT_FILE = Path("long_horizon_checkpoint.json")
MAX_STEPS_PER_RUN = 3
MAX_CONTEXT_ITEMS = 5


@dataclass
class TaskStep:
    step_id: int
    description: str
    status: str = "pending"
    result: Optional[str] = None


@dataclass
class LongHorizonState:
    goal: str
    goal_hash: str
    current_step: int = 0
    steps: List[TaskStep] = field(default_factory=list)
    context: List[str] = field(default_factory=list)
    summary: str = ""
    status: str = "initialized"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


def hash_goal(goal: str) -> str:
    return hashlib.sha256(goal.strip().lower().encode("utf-8")).hexdigest()


class CheckpointStore:
    def save(self, state: LongHorizonState) -> None:
        data = asdict(state)
        data["steps"] = [asdict(step) for step in state.steps]

        CHECKPOINT_FILE.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    def load(self) -> Optional[LongHorizonState]:
        if not CHECKPOINT_FILE.exists():
            return None

        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))

        steps = [TaskStep(**step) for step in data["steps"]]

        return LongHorizonState(
            goal=data["goal"],
            goal_hash=data["goal_hash"],
            current_step=data["current_step"],
            steps=steps,
            context=data["context"],
            summary=data["summary"],
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


class Planner:
    def create_plan(self, goal: str) -> List[TaskStep]:
        goal_lower = goal.lower()

        if "research" in goal_lower:
            descriptions = [
                "Clarify research question",
                "Collect initial sources",
                "Summarize evidence",
                "Compare findings",
                "Write final report",
            ]

        elif "build" in goal_lower or "code" in goal_lower:
            descriptions = [
                "Clarify requirements",
                "Design architecture",
                "Implement first version",
                "Run tests",
                "Review and finalize",
            ]

        else:
            descriptions = [
                "Clarify goal",
                "Break goal into subtasks",
                "Execute subtasks",
                "Review progress",
                "Produce final output",
            ]

        return [
            TaskStep(step_id=i + 1, description=description)
            for i, description in enumerate(descriptions)
        ]


class GoalDriftDetector:
    def detect(self, original_goal_hash: str, current_goal: str) -> bool:
        return original_goal_hash != hash_goal(current_goal)


class ContextManager:
    def add_context(self, state: LongHorizonState, item: str) -> None:
        state.context.append(item)

        if len(state.context) > MAX_CONTEXT_ITEMS:
            self.compress_context(state)

    def compress_context(self, state: LongHorizonState) -> None:
        old_items = state.context[:-MAX_CONTEXT_ITEMS]

        if old_items:
            compressed = " | ".join(old_items)
            state.summary += f"\nCompressed memory: {compressed}"

        state.context = state.context[-MAX_CONTEXT_ITEMS:]


class Executor:
    def execute_step(self, step: TaskStep, state: LongHorizonState) -> str:
        """
        Simulated long-running work.
        Real version could call tools, APIs, LLMs, databases, etc.
        """

        time.sleep(0.5)

        return (
            f"Completed step {step.step_id}: {step.description}. "
            f"Goal remains: {state.goal}"
        )


class Validator:
    def validate_step_result(self, state: LongHorizonState, result: str) -> bool:
        """
        Prevents context loss and goal drift.

        The result must still refer to the original goal.
        """
        key_terms = state.goal.lower().split()[:3]

        if not key_terms:
            return False

        result_lower = result.lower()

        return any(term in result_lower for term in key_terms)


class LongHorizonTaskRunner:
    def __init__(self):
        self.store = CheckpointStore()
        self.planner = Planner()
        self.drift_detector = GoalDriftDetector()
        self.context_manager = ContextManager()
        self.executor = Executor()
        self.validator = Validator()

    def start_or_resume(self, goal: str) -> LongHorizonState:
        saved_state = self.store.load()

        if saved_state:
            print("Checkpoint found. Resuming previous task.")

            if self.drift_detector.detect(saved_state.goal_hash, saved_state.goal):
                saved_state.status = "blocked_goal_drift"
                self.store.save(saved_state)
                raise RuntimeError("Goal drift detected in checkpoint.")

            return saved_state

        print("No checkpoint found. Starting new long-horizon task.")

        state = LongHorizonState(
            goal=goal,
            goal_hash=hash_goal(goal),
            steps=self.planner.create_plan(goal),
            status="running",
        )

        self.store.save(state)
        return state

    def run(self, goal: str) -> None:
        state = self.start_or_resume(goal)

        if state.status in ["completed", "blocked_goal_drift"]:
            print(f"Task status: {state.status}")
            return

        steps_run_this_session = 0

        while state.current_step < len(state.steps):
            if steps_run_this_session >= MAX_STEPS_PER_RUN:
                print("Checkpoint pause: stopping this run safely.")
                break

            if self.drift_detector.detect(state.goal_hash, state.goal):
                state.status = "blocked_goal_drift"
                self.store.save(state)
                print("Stopped: goal drift detected.")
                return

            step = state.steps[state.current_step]

            print("\nRunning step:")
            print(step.description)

            step.status = "running"
            state.updated_at = time.time()
            self.store.save(state)

            result = self.executor.execute_step(step, state)

            if not self.validator.validate_step_result(state, result):
                step.status = "failed"
                step.result = result
                state.status = "failed_context_loss"
                self.store.save(state)

                print("Stopped: result no longer matches original goal.")
                return

            step.status = "completed"
            step.result = result

            self.context_manager.add_context(state, result)

            state.current_step += 1
            state.updated_at = time.time()
            state.status = "running"

            self.store.save(state)

            print("Result:", result)
            print("Checkpoint saved.")

            steps_run_this_session += 1

        if state.current_step >= len(state.steps):
            state.status = "completed"
            state.updated_at = time.time()
            self.store.save(state)

            print("\nTask completed successfully.")

        print("\nCurrent state:")
        print("Goal:", state.goal)
        print("Status:", state.status)
        print("Current step:", state.current_step)
        print("Summary:", state.summary or "No compressed summary yet.")
        print("Recent context:")
        for item in state.context:
            print("-", item)


if __name__ == "__main__":
    runner = LongHorizonTaskRunner()

    runner.run("Build a Python agent system with checkpoints and recovery")