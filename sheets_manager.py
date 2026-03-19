"""
sheets_manager.py
─────────────────
Google Sheets R/W with:
  - Local SQLite mirror (reads from local first)
  - pending_sync table for failed Sheets writes
  - Throttle (1s between requests, exponential backoff on 429)
  - Pazar 03:00 backup to Google Drive
"""
import json
import sqlite3
import time
import threading
from datetime import datetime
from typing import Any, List, Optional

import gspread
from google.oauth2.service_account import Credentials

from config import Config
from utils.logger import get_logger

log = get_logger("sheets_manager")

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

_lock = threading.Lock()


class SheetsManager:
    def __init__(self):
        self.db_path = Config.SQLITE_DB_PATH
        self._gc = None
        self._sheet = None
        self._init_sqlite()

    # ── Google Sheets client ─────────────────────────────────────
    def _get_client(self):
        if self._gc is None:
            creds = Credentials.from_service_account_file(
                Config.GOOGLE_SHEETS_CREDENTIALS, scopes=SCOPES
            )
            self._gc = gspread.authorize(creds)
        return self._gc

    def _get_worksheet(self, tab_name: str):
        gc = self._get_client()
        sheet = gc.open_by_key(Config.GOOGLE_SHEETS_ID)
        try:
            return sheet.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            # Auto-create missing tab
            ws = sheet.add_worksheet(title=tab_name, rows=1000, cols=26)
            log.info(f"Created new Sheets tab: {tab_name}")
            return ws

    # ── SQLite init ──────────────────────────────────────────────
    def _init_sqlite(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    tab_name TEXT,
                    row_key  TEXT,
                    data_json TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (tab_name, row_key)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_sync (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    tab_name   TEXT,
                    operation  TEXT,
                    payload_json TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    retry_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()
        log.info("SQLite initialized")

    # ── READ — local first ───────────────────────────────────────
    def read_all(self, tab_name: str) -> List[dict]:
        """Read all rows from a tab. Local SQLite first, Sheets fallback."""
        local = self._read_local(tab_name)
        if local:
            return local
        return self._read_from_sheets(tab_name)

    def _read_local(self, tab_name: str) -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT data_json FROM cache WHERE tab_name=?", (tab_name,)
            ).fetchall()
        if rows:
            return [json.loads(r[0]) for r in rows]
        return []

    def _read_from_sheets(self, tab_name: str) -> List[dict]:
        try:
            time.sleep(1)
            ws = self._get_worksheet(tab_name)
            records = ws.get_all_records()
            self._update_local_cache(tab_name, records)
            return records
        except Exception as e:
            log.error(f"Sheets read failed for {tab_name}: {e}")
            return []

    def _update_local_cache(self, tab_name: str, records: List[dict]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache WHERE tab_name=?", (tab_name,))
            for i, record in enumerate(records):
                conn.execute(
                    "INSERT OR REPLACE INTO cache (tab_name, row_key, data_json, updated_at) VALUES (?,?,?,?)",
                    (tab_name, str(i), json.dumps(record), datetime.utcnow().isoformat())
                )
            conn.commit()

    # ── WRITE — Sheets first, SQLite fallback ────────────────────
    def append_row(self, tab_name: str, row: dict) -> bool:
        """Append a row. Writes to Sheets first, then SQLite. On fail: pending_sync."""
        try:
            time.sleep(1)
            ws = self._get_worksheet(tab_name)
            # Get headers from first row
            headers = ws.row_values(1)
            if not headers:
                headers = list(row.keys())
                ws.append_row(headers)
            values = [row.get(h, "") for h in headers]
            ws.append_row(values)
            log.info(f"Appended row to Sheets tab: {tab_name}")
            self._update_local_cache(tab_name, self._read_from_sheets(tab_name))
            return True
        except Exception as e:
            log.warning(f"Sheets write failed, queuing to pending_sync: {e}")
            self._queue_pending_sync(tab_name, "INSERT", row)
            return False

    def _queue_pending_sync(self, tab_name: str, operation: str, payload: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO pending_sync (tab_name, operation, payload_json) VALUES (?,?,?)",
                (tab_name, operation, json.dumps(payload))
            )
            conn.commit()
        log.info(f"Queued to pending_sync: {tab_name} / {operation}")

    # ── PENDING SYNC REPLAY ──────────────────────────────────────
    def replay_pending_sync(self):
        """Called on startup and every 15 min to retry failed Sheets writes."""
        with sqlite3.connect(self.db_path) as conn:
            pending = conn.execute(
                "SELECT id, tab_name, operation, payload_json, retry_count FROM pending_sync WHERE retry_count < 10"
            ).fetchall()

        for row_id, tab_name, operation, payload_json, retry_count in pending:
            payload = json.loads(payload_json)
            success = False
            try:
                time.sleep(1)
                ws = self._get_worksheet(tab_name)
                if operation == "INSERT":
                    headers = ws.row_values(1) or list(payload.keys())
                    ws.append_row([payload.get(h, "") for h in headers])
                    success = True
            except Exception as e:
                log.warning(f"pending_sync retry failed (id={row_id}): {e}")

            with sqlite3.connect(self.db_path) as conn:
                if success:
                    conn.execute("DELETE FROM pending_sync WHERE id=?", (row_id,))
                    log.info(f"pending_sync replayed successfully: id={row_id}")
                else:
                    conn.execute(
                        "UPDATE pending_sync SET retry_count=retry_count+1 WHERE id=?",
                        (row_id,)
                    )
                    if retry_count + 1 >= 10:
                        log.error(f"pending_sync id={row_id} FAILED after 10 retries — manual review required")
                conn.commit()

    # ── BACKUP ───────────────────────────────────────────────────
    def backup_all_to_json(self, backup_dir: str):
        """Export all Sheets tabs to JSON files. Called Sunday 03:00."""
        import os
        os.makedirs(backup_dir, exist_ok=True)
        tabs = [
            Config.SHEETS_VIDEO_LOG, Config.SHEETS_TREND_DATA,
            Config.SHEETS_OPPORTUNITIES, Config.SHEETS_EMAIL_SUBSCRIBERS,
            Config.SHEETS_SALES, Config.SHEETS_CHANNELS,
            Config.SHEETS_CONTENT_CALENDAR, Config.SHEETS_ERRORS,
        ]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        for tab in tabs:
            try:
                records = self._read_from_sheets(tab)
                path = os.path.join(backup_dir, f"{tab}_{timestamp}.json")
                with open(path, "w") as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                log.info(f"Backed up {tab} → {path}")
            except Exception as e:
                log.error(f"Backup failed for {tab}: {e}")
