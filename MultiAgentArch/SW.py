from typing import List, Dict, Set


class WorkerAgent:
    def __init__(self, name: str, specialty: str):
        self.name = name
        self.specialty = specialty

    def can_handle(self, task: str) -> bool:
        return self.specialty.lower() in task.lower()

    def work(self, task: str) -> Dict[str, str]:
        return {
            "worker": self.name,
            "task": task,
            "result": f"{self.name} completed task: {task}",
            "confidence": "high",
        }


class ManagerAgent:
    def __init__(self, workers: List[WorkerAgent]):
        self.workers = workers
        self.completed_tasks: Set[str] = set()

    def decompose_goal(self, goal: str) -> List[str]:
        goal_lower = goal.lower()

        if "rag" in goal_lower:
            return [
                "research RAG concepts",
                "write Python code",
                "test Python code",
                "review final answer",
            ]

        if "sql" in goal_lower:
            return [
                "design SQL schema",
                "write Python code",
                "test SQL queries",
                "review final answer",
            ]

        return [
            "research topic",
            "write Python code",
            "review final answer",
        ]

    def assign_worker(self, task: str) -> WorkerAgent:
        matching_workers = [
            worker for worker in self.workers
            if worker.can_handle(task)
        ]

        if matching_workers:
            return matching_workers[0]

        return self.workers[0]

    def detect_duplicate_work(self, task: str) -> bool:
        normalized = task.lower().strip()

        if normalized in self.completed_tasks:
            return True

        self.completed_tasks.add(normalized)
        return False

    def resolve_disagreement(self, results: List[Dict[str, str]]) -> Dict[str, str]:
        """
        If multiple agents disagree, manager chooses the high-confidence result.
        If still tied, manager escalates to review.
        """

        high_confidence = [
            result for result in results
            if result["confidence"] == "high"
        ]

        if len(high_confidence) == 1:
            return high_confidence[0]

        if len(high_confidence) > 1:
            return {
                "worker": "Manager",
                "task": results[0]["task"],
                "result": "Multiple high-confidence answers found. Manager review required.",
                "confidence": "medium",
            }

        return {
            "worker": "Manager",
            "task": results[0]["task"],
            "result": "Agents disagreed and no confident answer was found.",
            "confidence": "low",
        }

    def run(self, goal: str) -> None:
        print("Goal:", goal)

        tasks = self.decompose_goal(goal)

        print("\nPlanned tasks:")
        for task in tasks:
            print("-", task)

        final_results = []

        for task in tasks:
            print("\nTask:", task)

            if self.detect_duplicate_work(task):
                print("Skipped duplicate task.")
                continue

            worker = self.assign_worker(task)
            result = worker.work(task)

            print("Assigned to:", worker.name)
            print("Result:", result["result"])

            final_results.append(result)

        print("\nFinal Summary:")
        for result in final_results:
            print(f"- {result['worker']}: {result['result']}")


if __name__ == "__main__":
    workers = [
        WorkerAgent("ResearchAgent", "research"),
        WorkerAgent("CodeAgent", "code"),
        WorkerAgent("TestAgent", "test"),
        WorkerAgent("ReviewAgent", "review"),
    ]

    manager = ManagerAgent(workers)

    manager.run("Build a RAG system with Python code")