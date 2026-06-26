"""Tests for stats.py — Cursor and Claude Code session parsing."""

import json
import sqlite3
from datetime import datetime, timezone

from ai_helper.stats import (
    _parse_cursor_ts,
    _read_cursor_sessions,
)


class TestParseCursorTs:
    def test_valid_timestamp(self):
        ts = _parse_cursor_ts(1781676705208)
        assert ts is not None
        assert ts.year == 2026

    def test_none_returns_none(self):
        assert _parse_cursor_ts(None) is None

    def test_invalid_returns_none(self):
        assert _parse_cursor_ts("not_a_number") is None


def _create_state_db(path, composers=None):
    """Create a state.vscdb with composer headers."""
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
    if composers is not None:
        data = json.dumps({"allComposers": composers})
        conn.execute(
            "INSERT INTO ItemTable VALUES (?, ?)",
            ("composer.composerHeaders", data),
        )
    conn.commit()
    conn.close()


class TestReadCursorSessions:
    def test_missing_db_returns_empty(self, tmp_path):
        db = tmp_path / "nope.vscdb"
        cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)
        stats = _read_cursor_sessions(cutoff, db_path=db)
        assert len(stats.sessions) == 0

    def test_empty_composers_returns_empty(self, tmp_path):
        db = tmp_path / "state.vscdb"
        _create_state_db(db, composers=[])
        cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)
        stats = _read_cursor_sessions(cutoff, db_path=db)
        assert len(stats.sessions) == 0

    def test_composers_parsed(self, tmp_path):
        db = tmp_path / "state.vscdb"
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        _create_state_db(db, composers=[
            {
                "composerId": "abc-123",
                "name": "Test Chat",
                "createdAt": now_ms,
                "lastUpdatedAt": now_ms + 60000,
                "unifiedMode": "agent",
            },
            {
                "composerId": "def-456",
                "name": "Code Review",
                "createdAt": now_ms - 5000,
                "lastUpdatedAt": now_ms,
                "unifiedMode": "chat",
            },
        ])
        cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)
        stats = _read_cursor_sessions(cutoff, db_path=db)
        assert len(stats.sessions) == 2
        assert stats.sessions[0].project == "Test Chat"

    def test_cutoff_filters(self, tmp_path):
        db = tmp_path / "state.vscdb"
        old_ms = int(
            datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
        )
        _create_state_db(db, composers=[
            {
                "composerId": "old-1",
                "createdAt": old_ms,
                "lastUpdatedAt": old_ms,
                "unifiedMode": "agent",
            },
        ])
        cutoff = datetime(2025, 1, 1, tzinfo=timezone.utc)
        stats = _read_cursor_sessions(cutoff, db_path=db)
        assert len(stats.sessions) == 0

    def test_corrupt_db_returns_empty(self, tmp_path):
        db = tmp_path / "state.vscdb"
        db.write_text("not a database")
        cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)
        stats = _read_cursor_sessions(cutoff, db_path=db)
        assert len(stats.sessions) == 0

    def test_duration_calculated(self, tmp_path):
        db = tmp_path / "state.vscdb"
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        _create_state_db(db, composers=[
            {
                "composerId": "dur-1",
                "createdAt": now_ms,
                "lastUpdatedAt": now_ms + 300000,
                "unifiedMode": "agent",
            },
        ])
        cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)
        stats = _read_cursor_sessions(cutoff, db_path=db)
        assert len(stats.sessions) == 1
        assert stats.sessions[0].duration_minutes > 4.0

    def test_no_composer_key_returns_empty(self, tmp_path):
        db = tmp_path / "state.vscdb"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)"
        )
        conn.commit()
        conn.close()
        cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)
        stats = _read_cursor_sessions(cutoff, db_path=db)
        assert len(stats.sessions) == 0
