import asyncio
import random
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field


MAX_QUEUE_SIZE = 3
WORKER_COUNT = 2
MAX_RETRIES = 2
PROCESSING_TIMEOUT_SECONDS = 5


class TaskStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    dead_letter = "dead_letter"


@dataclass
class TaskRecord:
    task_id: str
    prompt: str
    status: TaskStatus = TaskStatus.queued
    result: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    history: List[str] = field(default_factory=list)


class TaskRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=1000)


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str


tasks: Dict[str, TaskRecord] = {}


async def run_agent_logic(prompt: str) -> str:
    """
    Mock agent logic.

    Try prompts like:
    - "Explain agent queues"
    - "slow task"
    - "always fail"
    """

    if "slow" in prompt.lower():
        await asyncio.sleep(10)

    await asyncio.sleep(random.uniform(0.5, 1.5))

    if "always fail" in prompt.lower():
        raise RuntimeError("Simulated permanent agent failure.")

    if "fail sometimes" in prompt.lower() and random.random() < 0.7:
        raise RuntimeError("Simulated temporary failure.")

    return f"Agent result for: {prompt}"


async def process_task(task_id: str) -> None:
    record = tasks.get(task_id)

    if record is None:
        return

    record.status = TaskStatus.processing
    record.updated_at = time.time()
    record.history.append("Task started processing.")

    for attempt in range(1, MAX_RETRIES + 2):
        record.attempts = attempt
        record.updated_at = time.time()

        try:
            record.history.append(f"Attempt {attempt} started.")

            result = await asyncio.wait_for(
                run_agent_logic(record.prompt),
                timeout=PROCESSING_TIMEOUT_SECONDS,
            )

            record.result = result
            record.error = None
            record.status = TaskStatus.completed
            record.updated_at = time.time()
            record.history.append("Task completed successfully.")
            return

        except asyncio.TimeoutError:
            record.error = "Task timed out."
            record.history.append("Timeout failure.")

        except Exception as e:
            record.error = str(e)
            record.history.append(f"Execution failure: {e}")

        if attempt <= MAX_RETRIES:
            backoff = 2 ** attempt
            record.history.append(f"Retrying after {backoff} seconds.")
            await asyncio.sleep(backoff)

    record.status = TaskStatus.dead_letter
    record.updated_at = time.time()
    record.history.append("Task moved to dead letter after max retries.")


async def worker_loop(worker_name: str, queue: asyncio.Queue) -> None:
    while True:
        task_id = await queue.get()

        try:
            print(f"{worker_name} picked up task {task_id}")
            await process_task(task_id)

        except Exception as e:
            # Worker should not crash the whole system.
            record = tasks.get(task_id)

            if record:
                record.status = TaskStatus.failed
                record.error = f"Worker crashed safely: {e}"
                record.updated_at = time.time()
                record.history.append(record.error)

        finally:
            queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
    app.state.workers = []

    for i in range(WORKER_COUNT):
        worker = asyncio.create_task(
            worker_loop(f"worker-{i + 1}", app.state.queue)
        )
        app.state.workers.append(worker)

    yield

    for worker in app.state.workers:
        worker.cancel()


app = FastAPI(
    title="Production Agent Service",
    lifespan=lifespan,
)


@app.post("/tasks", response_model=TaskResponse, status_code=202)
async def create_task(payload: TaskRequest, request: Request):
    queue: asyncio.Queue = request.app.state.queue

    task_id = str(uuid.uuid4())

    record = TaskRecord(
        task_id=task_id,
        prompt=payload.prompt,
    )

    try:
        queue.put_nowait(task_id)

    except asyncio.QueueFull:
        raise HTTPException(
            status_code=503,
            detail="Queue overloaded. Try again later.",
        )

    tasks[task_id] = record

    return TaskResponse(
        task_id=task_id,
        status=record.status,
        message="Task accepted.",
    )


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    record = tasks.get(task_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    return {
        "task_id": record.task_id,
        "prompt": record.prompt,
        "status": record.status,
        "result": record.result,
        "error": record.error,
        "attempts": record.attempts,
        "history": record.history,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


@app.get("/health")
async def health(request: Request):
    queue: asyncio.Queue = request.app.state.queue

    counts = {}

    for record in tasks.values():
        counts[record.status] = counts.get(record.status, 0) + 1

    return {
        "status": "ok",
        "queue_size": queue.qsize(),
        "queue_capacity": MAX_QUEUE_SIZE,
        "workers": WORKER_COUNT,
        "task_counts": counts,
    }