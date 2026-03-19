"""
github_backup.py
────────────────
Daily push of:
  - All Python source files
  - Job JSON state files
  - n8n workflow JSON exports
to the configured GitHub repo.
"""
import os
import base64
from datetime import datetime

from github import Github, GithubException

from config import Config
from utils.logger import get_logger

log = get_logger("github_backup")


class GitHubBackup:
    def __init__(self):
        if not Config.GITHUB_TOKEN:
            log.warning("GITHUB_TOKEN not set — backup disabled")
            self._enabled = False
            return
        self._gh = Github(Config.GITHUB_TOKEN)
        self._repo = self._gh.get_repo(Config.GITHUB_REPO)
        self._enabled = True

    def _upsert_file(self, repo_path: str, content: bytes, message: str):
        """Create or update a file in the GitHub repo."""
        try:
            existing = self._repo.get_contents(repo_path)
            self._repo.update_file(repo_path, message, content, existing.sha)
        except GithubException as e:
            if e.status == 404:
                self._repo.create_file(repo_path, message, content)
            else:
                raise

    def backup_sources(self, source_dir: str = "/app"):
        """Push all .py files to GitHub."""
        if not self._enabled:
            return
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        backed_up = 0
        for fname in os.listdir(source_dir):
            if fname.endswith(".py"):
                path = os.path.join(source_dir, fname)
                with open(path, "rb") as f:
                    content = f.read()
                try:
                    self._upsert_file(fname, content, f"Auto-backup {fname} — {timestamp}")
                    backed_up += 1
                except Exception as e:
                    log.error(f"Failed to backup {fname}: {e}")
        log.info(f"GitHub backup: {backed_up} Python files pushed")

    def backup_jobs(self, jobs_dir: str = None):
        """Push all job JSON files."""
        if not self._enabled:
            return
        jobs_dir = jobs_dir or Config.JOBS_DIR
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        backed_up = 0
        for fname in os.listdir(jobs_dir):
            if fname.endswith(".json"):
                path = os.path.join(jobs_dir, fname)
                with open(path, "rb") as f:
                    content = f.read()
                try:
                    self._upsert_file(f"jobs/{fname}", content, f"Job state {fname} — {timestamp}")
                    backed_up += 1
                except Exception as e:
                    log.error(f"Failed to backup job {fname}: {e}")
        log.info(f"GitHub backup: {backed_up} job JSON files pushed")

    def backup_n8n_workflows(self, workflows_dir: str = "/app/n8n_workflows"):
        """Push all n8n workflow JSON exports."""
        if not self._enabled:
            return
        if not os.path.exists(workflows_dir):
            log.info("No n8n_workflows directory found — skipping")
            return
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        backed_up = 0
        for fname in os.listdir(workflows_dir):
            if fname.endswith(".json"):
                path = os.path.join(workflows_dir, fname)
                with open(path, "rb") as f:
                    content = f.read()
                try:
                    self._upsert_file(f"n8n_workflows/{fname}", content, f"n8n workflow {fname} — {timestamp}")
                    backed_up += 1
                except Exception as e:
                    log.error(f"Failed to backup n8n workflow {fname}: {e}")
        log.info(f"GitHub backup: {backed_up} n8n workflow files pushed")

    def run_full_backup(self):
        """Run all backup tasks."""
        log.info("Starting full GitHub backup…")
        self.backup_sources()
        self.backup_jobs()
        self.backup_n8n_workflows()
        log.info("Full GitHub backup complete")
