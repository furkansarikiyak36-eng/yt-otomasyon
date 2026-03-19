"""
queue_manager.py
────────────────
RAM-aware job queue.
  - Max 1 heavy process at a time (FFmpeg, Ollama, Kokoro)
  - Max 2 concurrent light processes
  - Auto-retry on failure (exponential backoff, max 3 retries)
  - Priority ordering
"""
import asyncio
import psutil
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from config import Config
from utils.logger import get_logger

log = get_logger("queue_manager")


class JobType(Enum):
    HEAVY   = "heavy"   # FFmpeg, Ollama large, Kokoro
    LIGHT   = "light"   # API calls, Sheets writes, small tasks
    URGENT  = "urgent"  # Always runs next, regardless of queue


class JobStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    RETRYING  = "retrying"


@dataclass(order=True)
class Job:
    priority: int
    job_id: str        = field(compare=False)
    name: str          = field(compare=False)
    func: Callable     = field(compare=False)
    job_type: JobType  = field(compare=False, default=JobType.LIGHT)
    status: JobStatus  = field(compare=False, default=JobStatus.PENDING)
    retry_count: int   = field(compare=False, default=0)
    max_retries: int   = field(compare=False, default=3)
    created_at: float  = field(compare=False, default_factory=time.time)
    error: Optional[str] = field(compare=False, default=None)


class QueueManager:
    def __init__(self):
        self._queue: deque[Job] = deque()
        self._running_heavy = 0
        self._running_light = 0
        self._lock = asyncio.Lock()
        self._max_light = Config.MAX_CONCURRENT_JOBS
        self._ram_limit_gb = Config.RAM_LIMIT_GB

    def enqueue(self, job: Job):
        if job.job_type == JobType.URGENT:
            self._queue.appendleft(job)
        else:
            self._queue.append(job)
        log.info(f"Enqueued job: {job.name} ({job.job_type.value}) — queue size: {len(self._queue)}")

    def _ram_ok(self) -> bool:
        used_gb = psutil.virtual_memory().used / (1024 ** 3)
        ok = used_gb < self._ram_limit_gb
        if not ok:
            log.warning(f"RAM limit reached: {used_gb:.1f}GB used / {self._ram_limit_gb}GB limit")
        return ok

    def _can_run(self, job: Job) -> bool:
        if not self._ram_ok():
            return False
        if job.job_type == JobType.HEAVY:
            return self._running_heavy == 0
        if job.job_type == JobType.LIGHT:
            return self._running_light < self._max_light
        if job.job_type == JobType.URGENT:
            return True
        return False

    async def run_next(self):
        async with self._lock:
            for i, job in enumerate(self._queue):
                if self._can_run(job):
                    self._queue.remove(job)
                    asyncio.create_task(self._execute(job))
                    return

    async def _execute(self, job: Job):
        job.status = JobStatus.RUNNING
        if job.job_type == JobType.HEAVY:
            self._running_heavy += 1
        else:
            self._running_light += 1

        log.info(f"Starting job: {job.name} [{job.job_id}]")
        try:
            if asyncio.iscoroutinefunction(job.func):
                await job.func()
            else:
                await asyncio.get_event_loop().run_in_executor(None, job.func)
            job.status = JobStatus.DONE
            log.info(f"Job completed: {job.name} [{job.job_id}]")
        except Exception as e:
            job.error = str(e)
            log.error(f"Job failed: {job.name} [{job.job_id}] — {e}")
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.RETRYING
                delay = 2 ** job.retry_count
                log.info(f"Retrying {job.name} in {delay}s (attempt {job.retry_count}/{job.max_retries})")
                await asyncio.sleep(delay)
                self.enqueue(job)
            else:
                job.status = JobStatus.FAILED
                log.error(f"Job permanently failed: {job.name} [{job.job_id}]")
        finally:
            if job.job_type == JobType.HEAVY:
                self._running_heavy -= 1
            else:
                self._running_light -= 1

    async def process_loop(self):
        """Main loop — runs forever, picks jobs from queue."""
        log.info("Queue manager started")
        while True:
            await self.run_next()
            await asyncio.sleep(2)

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    def status_summary(self) -> dict:
        ram_used = psutil.virtual_memory().used / (1024 ** 3)
        return {
            "queue_size": self.queue_size,
            "running_heavy": self._running_heavy,
            "running_light": self._running_light,
            "ram_used_gb": round(ram_used, 2),
            "ram_limit_gb": self._ram_limit_gb,
        }
