"""
workflow_manager.py
───────────────────
Manages every job through its lifecycle phases:
  idea → script → assets → produce → upload → approval → publish

Each job is persisted as a JSON file in /app/jobs/
On restart, all pending jobs resume from their last saved state.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime

from config import Config
from utils.logger import get_logger
from utils.helpers import generate_job_id, now_str

log = get_logger("workflow_manager")


class Phase(Enum):
    IDEA       = "idea"
    SCRIPT     = "script"
    ASSETS     = "assets"
    PRODUCE    = "produce"
    UPLOAD     = "upload"
    APPROVAL   = "approval"
    PUBLISHED  = "published"
    CANCELLED  = "cancelled"
    FAILED     = "failed"
    MANUAL     = "manual_takeover"


PHASE_ORDER = [
    Phase.IDEA, Phase.SCRIPT, Phase.ASSETS,
    Phase.PRODUCE, Phase.UPLOAD, Phase.APPROVAL, Phase.PUBLISHED
]


@dataclass
class JobRecord:
    job_id:     str
    name:       str
    job_type:   str          # "video", "pdf", "blog", "analysis"
    channel_id: Optional[str]
    phase:      str          = Phase.IDEA.value
    status:     str          = "running"
    scores:     Dict[str, int] = field(default_factory=dict)
    files:      Dict[str, str] = field(default_factory=dict)   # phase → file path
    metadata:   Dict[str, Any] = field(default_factory=dict)
    created_at: str           = field(default_factory=now_str)
    updated_at: str           = field(default_factory=now_str)
    error:      Optional[str] = None


class WorkflowManager:
    def __init__(self):
        os.makedirs(Config.JOBS_DIR, exist_ok=True)

    # ── Create ───────────────────────────────────────────────────
    def create_job(
        self,
        name: str,
        job_type: str,
        channel_id: Optional[str] = None,
        metadata: dict = None
    ) -> JobRecord:
        job = JobRecord(
            job_id=generate_job_id(),
            name=name,
            job_type=job_type,
            channel_id=channel_id,
            metadata=metadata or {}
        )
        self._save(job)
        log.info(f"Created job: {job.job_id} — {name} ({job_type})")
        return job

    # ── Load / Save ──────────────────────────────────────────────
    def _job_path(self, job_id: str) -> str:
        return os.path.join(Config.JOBS_DIR, f"{job_id}.json")

    def _save(self, job: JobRecord):
        job.updated_at = now_str()
        with open(self._job_path(job.job_id), "w") as f:
            json.dump(asdict(job), f, indent=2)

    def load(self, job_id: str) -> Optional[JobRecord]:
        path = self._job_path(job_id)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        return JobRecord(**data)

    def load_all_active(self) -> list[JobRecord]:
        jobs = []
        for fname in os.listdir(Config.JOBS_DIR):
            if fname.endswith(".json"):
                job = self.load(fname[:-5])
                if job and job.status == "running":
                    jobs.append(job)
        return jobs

    # ── Phase transitions ────────────────────────────────────────
    def advance(self, job: JobRecord, score: Optional[int] = None, file_path: Optional[str] = None):
        current_idx = next((i for i, p in enumerate(PHASE_ORDER) if p.value == job.phase), None)
        if current_idx is None or current_idx >= len(PHASE_ORDER) - 1:
            log.warning(f"Cannot advance job {job.job_id} — already at final phase")
            return

        if score is not None:
            job.scores[job.phase] = score
        if file_path:
            job.files[job.phase] = file_path

        next_phase = PHASE_ORDER[current_idx + 1]
        log.info(f"Job {job.job_id}: {job.phase} → {next_phase.value}")
        job.phase = next_phase.value
        self._save(job)

    def cancel(self, job: JobRecord):
        job.phase  = Phase.CANCELLED.value
        job.status = "cancelled"
        self._save(job)
        log.info(f"Job {job.job_id} cancelled")

    def fail(self, job: JobRecord, error: str):
        job.phase  = Phase.FAILED.value
        job.status = "failed"
        job.error  = error
        self._save(job)
        log.error(f"Job {job.job_id} failed: {error}")

    def takeover(self, job: JobRecord):
        job.phase  = Phase.MANUAL.value
        job.status = "manual"
        self._save(job)
        log.info(f"Job {job.job_id} taken over manually")

    def complete(self, job: JobRecord):
        job.phase  = Phase.PUBLISHED.value
        job.status = "done"
        self._save(job)
        log.info(f"Job {job.job_id} published successfully")

    # ── Status summary ───────────────────────────────────────────
    def summary(self, job: JobRecord) -> str:
        scores_str = ", ".join(f"{k}:{v}" for k, v in job.scores.items()) or "none"
        return (
            f"Job #{job.job_id} | {job.name}\n"
            f"Type: {job.job_type} | Channel: {job.channel_id or 'N/A'}\n"
            f"Phase: {job.phase} | Status: {job.status}\n"
            f"Scores: {scores_str}\n"
            f"Updated: {job.updated_at}"
        )
