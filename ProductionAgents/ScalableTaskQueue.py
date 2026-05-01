import asyncio
import hashlib
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Set


WORKER_COUNT = 3
MAX_RETRIES = 2
RATE_LIMIT_PER_SECOND = 2


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


@dataclass
class Job:
    job_id: str
    payload: str
    payload_hash: str
    status: JobStatus = JobStatus.queued
    result: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class RateLimiter:
    """
    Simple async rate limiter.

    Allows only N jobs per second across all workers.
    """

    def __init__(self, rate_per_second: int):
        self.rate_per_second = rate_per_second
        self.tokens = rate_per_second
        self.last_refill = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        while True:
            async with self.lock:
                now = time.time()
                elapsed = now - self.last_refill

                if elapsed >= 1:
                    self.tokens = self.rate_per_second
                    self.last_refill = now

                if self.tokens > 0:
                    self.tokens -= 1
                    return

            await asyncio.sleep(0.05)


class ScalableTaskQueue:
    def __init__(self):
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.jobs: Dict[str, Job] = {}

        # Deduplication: prevents same payload from being queued twice.
        self.payload_hash_to_job_id: Dict[str, str] = {}

        # Race-condition protection.
        self.job_locks: Dict[str, asyncio.Lock] = {}

        # Tracks completed jobs for idempotency.
        self.completed_jobs: Set[str] = set()

        self.rate_limiter = RateLimiter(RATE_LIMIT_PER_SECOND)

    def hash_payload(self, payload: str) -> str:
        return hashlib.sha256(payload.strip().lower().encode("utf-8")).hexdigest()

    async def submit_job(self, payload: str) -> str:
        if not payload.strip():
            raise ValueError("Payload cannot be empty.")

        payload_hash = self.hash_payload(payload)

        # Duplicate job detection.
        if payload_hash in self.payload_hash_to_job_id:
            existing_job_id = self.payload_hash_to_job_id[payload_hash]
            print(f"Duplicate job detected. Returning existing job_id: {existing_job_id}")
            return existing_job_id

        job_id = str(uuid.uuid4())

        job = Job(
            job_id=job_id,
            payload=payload,
            payload_hash=payload_hash,
        )

        self.jobs[job_id] = job
        self.payload_hash_to_job_id[payload_hash] = job_id
        self.job_locks[job_id] = asyncio.Lock()

        await self.queue.put(job_id)

        print(f"Job submitted: {job_id}")
        return job_id

    async def process_job_logic(self, payload: str) -> str:
        """
        Simulated agent work.

        Some jobs randomly fail to demonstrate retries.
        """

        await asyncio.sleep(random.uniform(0.3, 1.0))

        if "fail" in payload.lower() and random.random() < 0.7:
            raise RuntimeError("Simulated temporary failure.")

        return f"Processed result for: {payload}"

    async def process_job(self, job_id: str, worker_name: str):
        job = self.jobs.get(job_id)

        if job is None:
            print(f"{worker_name}: job not found: {job_id}")
            return

        lock = self.job_locks[job_id]

        async with lock:
            # Idempotency check.
            if job_id in self.completed_jobs:
                print(f"{worker_name}: skipped already completed job {job_id}")
                return

            # Race-condition check.
            if job.status == JobStatus.processing:
                print(f"{worker_name}: skipped job already processing {job_id}")
                return

            job.status = JobStatus.processing
            job.updated_at = time.time()

            for attempt in range(1, MAX_RETRIES + 2):
                job.attempts = attempt

                try:
                    await self.rate_limiter.acquire()

                    print(f"{worker_name}: processing {job_id}, attempt {attempt}")

                    result = await self.process_job_logic(job.payload)

                    job.result = result
                    job.error = None
                    job.status = JobStatus.completed
                    job.updated_at = time.time()

                    self.completed_jobs.add(job_id)

                    print(f"{worker_name}: completed {job_id}")
                    return

                except Exception as e:
                    job.error = str(e)
                    job.updated_at = time.time()

                    print(f"{worker_name}: failed {job_id}: {e}")

                    if attempt <= MAX_RETRIES:
                        backoff = 2 ** attempt
                        print(f"{worker_name}: retrying in {backoff}s")
                        await asyncio.sleep(backoff)

            job.status = JobStatus.failed
            job.updated_at = time.time()
            print(f"{worker_name}: job failed permanently {job_id}")

    async def worker(self, worker_name: str):
        while True:
            job_id = await self.queue.get()

            try:
                await self.process_job(job_id, worker_name)

            finally:
                self.queue.task_done()

    async def start_workers(self):
        workers = []

        for i in range(WORKER_COUNT):
            worker_task = asyncio.create_task(
                self.worker(f"worker-{i + 1}")
            )
            workers.append(worker_task)

        return workers

    def print_status(self):
        print("\nJob Status")
        print("=" * 40)

        for job in self.jobs.values():
            print({
                "job_id": job.job_id,
                "payload": job.payload,
                "status": job.status,
                "attempts": job.attempts,
                "result": job.result,
                "error": job.error,
            })


async def main():
    task_queue = ScalableTaskQueue()

    workers = await task_queue.start_workers()

    job_inputs = [
        "Analyze customer feedback",
        "Summarize document",
        "Analyze customer feedback",  # duplicate
        "Generate report",
        "Fail sometimes",
        "Summarize document",         # duplicate
    ]

    for payload in job_inputs:
        await task_queue.submit_job(payload)

    await task_queue.queue.join()

    task_queue.print_status()

    for worker in workers:
        worker.cancel()


if __name__ == "__main__":
    asyncio.run(main())