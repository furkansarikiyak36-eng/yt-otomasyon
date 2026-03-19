"""
tests/test_queue.py
────────────────────
Test suite for queue_manager.py
Run: pytest tests/test_queue.py -v
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from queue_manager import QueueManager, Job, JobType, JobStatus


@pytest.fixture
def queue():
    q = QueueManager()
    q._ram_limit_gb = 100  # disable RAM check in tests
    return q


class TestEnqueue:
    def test_enqueue_adds_to_queue(self, queue):
        job = Job(priority=1, job_id="TEST01", name="test", func=lambda: None)
        queue.enqueue(job)
        assert queue.queue_size == 1

    def test_urgent_job_goes_to_front(self, queue):
        normal = Job(priority=5, job_id="NORM01", name="normal", func=lambda: None, job_type=JobType.LIGHT)
        urgent = Job(priority=1, job_id="URGN01", name="urgent", func=lambda: None, job_type=JobType.URGENT)
        queue.enqueue(normal)
        queue.enqueue(urgent)
        assert queue._queue[0].job_id == "URGN01"


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_only_one_heavy_at_a_time(self, queue):
        """Two heavy jobs: only one runs at a time."""
        results = []

        async def slow_heavy():
            await asyncio.sleep(0.1)
            results.append("done")

        job1 = Job(priority=1, job_id="HVY01", name="heavy1", func=slow_heavy, job_type=JobType.HEAVY)
        job2 = Job(priority=2, job_id="HVY02", name="heavy2", func=slow_heavy, job_type=JobType.HEAVY)
        queue.enqueue(job1)
        queue.enqueue(job2)

        # Run first job
        await queue.run_next()
        assert queue._running_heavy == 1

        # Second heavy job should NOT start while first is running
        can_run = queue._can_run(job2)
        assert can_run is False

    @pytest.mark.asyncio
    async def test_light_jobs_run_concurrently(self, queue):
        """Up to max_light light jobs can run simultaneously."""
        queue._max_light = 2
        results = []

        async def light_task():
            await asyncio.sleep(0.05)
            results.append("done")

        j1 = Job(priority=1, job_id="LT01", name="l1", func=light_task, job_type=JobType.LIGHT)
        j2 = Job(priority=2, job_id="LT02", name="l2", func=light_task, job_type=JobType.LIGHT)
        j3 = Job(priority=3, job_id="LT03", name="l3", func=light_task, job_type=JobType.LIGHT)

        queue.enqueue(j1)
        queue.enqueue(j2)
        queue.enqueue(j3)

        await queue.run_next()  # starts j1
        await queue.run_next()  # starts j2
        assert queue._running_light == 2

        # j3 should not start (at max)
        assert queue._can_run(j3) is False


class TestRetry:
    @pytest.mark.asyncio
    async def test_failed_job_requeued(self, queue):
        """A failing job is requeued for retry."""
        call_count = [0]

        async def failing_func():
            call_count[0] += 1
            raise RuntimeError("test error")

        job = Job(
            priority=1, job_id="FAIL1", name="failing",
            func=failing_func, job_type=JobType.LIGHT, max_retries=2
        )
        queue.enqueue(job)
        await queue._execute(job)
        assert job.status == JobStatus.RETRYING
        assert job.retry_count == 1
        assert queue.queue_size == 1  # requeued

    @pytest.mark.asyncio
    async def test_permanent_failure_after_max_retries(self, queue):
        """Job is permanently failed after max_retries exhausted."""
        async def always_fails():
            raise RuntimeError("always")

        job = Job(
            priority=1, job_id="DEAD1", name="dead",
            func=always_fails, job_type=JobType.LIGHT,
            max_retries=1, retry_count=1  # already at max
        )
        queue.enqueue(job)
        await queue._execute(job)
        assert job.status == JobStatus.FAILED
