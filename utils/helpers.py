"""
utils/helpers.py — Shared utility functions
"""
import hashlib
import json
import os
import time
import uuid
from datetime import datetime
from typing import Any


def generate_job_id() -> str:
    return str(uuid.uuid4())[:8].upper()


def now_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def hash_email(email: str) -> str:
    """One-way hash for storing email references without PII."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:16]


def safe_json_load(path: str, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def safe_json_save(path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def retry(func, retries=3, delay=2, backoff=2):
    """Simple retry with exponential backoff."""
    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(delay * (backoff ** attempt))


def truncate(text: str, max_len: int = 200) -> str:
    return text if len(text) <= max_len else text[:max_len] + "…"


def format_currency(amount: float, symbol: str = "$") -> str:
    return f"{symbol}{amount:,.2f}"
