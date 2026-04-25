import asyncio
import random
from typing import Dict, Set


executed_tasks: Set[str] = set()
task_locks: Dict[str, asyncio.Lock] = {}


async def run_task(task_id: str, task_name: str) -> str:
    await asyncio.sleep(random.uniform(0.5, 1.5))

    if random.random() < 0.3:
        raise RuntimeError("Temporary task failure")

    return f"Done: {task_name}"


async def execute_with_retries(
    task_id: str,
    task_name: str,
    max_retries: int = 3
) -> str:
    if task_id not in task_locks:
        task_locks[task_id] = asyncio.Lock()

    async with task_locks[task_id]:
        if task_id in executed_tasks:
            return f"Skipped duplicate task: {task_name}"

        for attempt in range(1, max_retries + 1):
            try:
                print(f"Running {task_name}, attempt {attempt}")
                result = await run_task(task_id, task_name)

                executed_tasks.add(task_id)
                return result

            except Exception as e:
                print(f"Failed {task_name}: {e}")
                await asyncio.sleep(2 ** attempt)

        return f"Failed after retries: {task_name}"


async def main():
    tasks = [
        ("task_1", "Search flights"),
        ("task_2", "Search hotels"),
        ("task_3", "Search restaurants"),

        # duplicated execution attempt
        ("task_2", "Search hotels"),
    ]

    results = await asyncio.gather(
        *(execute_with_retries(task_id, task_name) for task_id, task_name in tasks)
    )

    print("\nResults:")
    for result in results:
        print("-", result)


if __name__ == "__main__":
    asyncio.run(main())