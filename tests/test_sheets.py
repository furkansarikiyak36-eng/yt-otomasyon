"""
tests/test_sheets.py
─────────────────────
Test suite for sheets_manager.py
Run: pytest tests/test_sheets.py -v
"""
import json
import os
import sqlite3
import tempfile
import pytest
from unittest.mock import MagicMock, patch


# ── Fixtures ─────────────────────────────────────────────────────
@pytest.fixture
def tmp_db(tmp_path):
    """Temporary SQLite database for testing."""
    return str(tmp_path / "test.sqlite")


@pytest.fixture
def sheets_mgr(tmp_db, monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEETS_ID", "test_sheet_id")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/fake_creds.json")
    with patch("sheets_manager.Credentials"), patch("sheets_manager.gspread"):
        from sheets_manager import SheetsManager
        mgr = SheetsManager.__new__(SheetsManager)
        mgr.db_path = tmp_db
        mgr._gc = None
        mgr._sheet = None
        mgr._init_sqlite()
        return mgr


# ── Tests ─────────────────────────────────────────────────────────
class TestSQLiteInit:
    def test_tables_created(self, sheets_mgr):
        with sqlite3.connect(sheets_mgr.db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        table_names = [t[0] for t in tables]
        assert "cache" in table_names
        assert "pending_sync" in table_names


class TestPendingSync:
    def test_queue_on_sheets_failure(self, sheets_mgr):
        """When Sheets write fails, record goes to pending_sync."""
        with patch.object(sheets_mgr, "_get_worksheet", side_effect=Exception("API error")):
            result = sheets_mgr.append_row("video_log", {"title": "Test Video"})
        assert result is False
        with sqlite3.connect(sheets_mgr.db_path) as conn:
            pending = conn.execute("SELECT * FROM pending_sync").fetchall()
        assert len(pending) == 1
        assert pending[0][1] == "video_log"  # tab_name
        assert pending[0][2] == "INSERT"     # operation

    def test_pending_sync_replay_success(self, sheets_mgr):
        """Successfully replayed entries are removed from pending_sync."""
        # Queue a pending item directly
        with sqlite3.connect(sheets_mgr.db_path) as conn:
            conn.execute(
                "INSERT INTO pending_sync (tab_name, operation, payload_json) VALUES (?,?,?)",
                ("video_log", "INSERT", json.dumps({"title": "Replayed"}))
            )
            conn.commit()

        mock_ws = MagicMock()
        mock_ws.row_values.return_value = ["title"]
        with patch.object(sheets_mgr, "_get_worksheet", return_value=mock_ws):
            sheets_mgr.replay_pending_sync()

        with sqlite3.connect(sheets_mgr.db_path) as conn:
            remaining = conn.execute("SELECT * FROM pending_sync").fetchall()
        assert len(remaining) == 0

    def test_retry_count_increments_on_failure(self, sheets_mgr):
        """Failed replay increments retry_count."""
        with sqlite3.connect(sheets_mgr.db_path) as conn:
            conn.execute(
                "INSERT INTO pending_sync (tab_name, operation, payload_json, retry_count) VALUES (?,?,?,?)",
                ("video_log", "INSERT", json.dumps({"title": "Test"}), 0)
            )
            conn.commit()

        with patch.object(sheets_mgr, "_get_worksheet", side_effect=Exception("Still failing")):
            sheets_mgr.replay_pending_sync()

        with sqlite3.connect(sheets_mgr.db_path) as conn:
            row = conn.execute("SELECT retry_count FROM pending_sync").fetchone()
        assert row[0] == 1

    def test_max_retries_stops_at_10(self, sheets_mgr):
        """Entries at retry_count=10 are not retried."""
        with sqlite3.connect(sheets_mgr.db_path) as conn:
            conn.execute(
                "INSERT INTO pending_sync (tab_name, operation, payload_json, retry_count) VALUES (?,?,?,?)",
                ("video_log", "INSERT", json.dumps({"title": "Dead"}), 10)
            )
            conn.commit()

        mock_ws = MagicMock()
        call_count = [0]
        def track_call(*a, **kw):
            call_count[0] += 1
            return mock_ws
        with patch.object(sheets_mgr, "_get_worksheet", side_effect=track_call):
            sheets_mgr.replay_pending_sync()
        assert call_count[0] == 0  # never attempted


class TestLocalCache:
    def test_read_local_returns_cached_data(self, sheets_mgr):
        """Local cache returns data without calling Sheets."""
        with sqlite3.connect(sheets_mgr.db_path) as conn:
            conn.execute(
                "INSERT INTO cache (tab_name, row_key, data_json, updated_at) VALUES (?,?,?,?)",
                ("trend_data", "0", json.dumps({"topic": "meditation"}), "2024-01-01")
            )
            conn.commit()

        result = sheets_mgr._read_local("trend_data")
        assert len(result) == 1
        assert result[0]["topic"] == "meditation"

    def test_empty_cache_returns_empty_list(self, sheets_mgr):
        result = sheets_mgr._read_local("nonexistent_tab")
        assert result == []
