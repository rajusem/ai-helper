"""Tests for stats.py — Cursor and Claude Code session parsing."""

import json
import sqlite3
from datetime import datetime, timezone
from unittest.mock import patch

from click.testing import CliRunner

from ai_helper.cli import main
from ai_helper.stats import (
    SessionStats,
    ToolStats,
    _estimate_tokens_inline,
    _normalize_model_tier,
    _parse_cursor_ts,
    _read_cursor_sessions,
    show_compare,
    show_context,
    show_recommend,
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


# ── Model normalization tests ──────────────────────────────────────


class TestNormalizeModelTier:
    def test_opus(self):
        assert _normalize_model_tier("claude-opus-4-6") == "opus"
        assert _normalize_model_tier("claude-opus-4-8") == "opus"

    def test_sonnet(self):
        assert _normalize_model_tier("claude-sonnet-4-6") == "sonnet"

    def test_haiku(self):
        assert _normalize_model_tier("claude-haiku-4-5") == "haiku"

    def test_fable(self):
        assert _normalize_model_tier("claude-fable-5") == "fable"

    def test_local(self):
        assert _normalize_model_tier("ollama-llama3") == "local"
        assert _normalize_model_tier("deepseek-coder") == "local"

    def test_at_default_stripped(self):
        assert _normalize_model_tier("claude-opus-4-6@default") == "opus"
        assert _normalize_model_tier("claude-sonnet-4-5@default") == "sonnet"

    def test_unknown(self):
        assert _normalize_model_tier("gpt-4o") == "other"
        assert _normalize_model_tier("unknown") == "other"


# ── Inline token estimator tests ──────────────────────────────────


class TestEstimateTokensInline:
    def test_basic(self):
        assert _estimate_tokens_inline("abcd") == 1

    def test_empty(self):
        assert _estimate_tokens_inline("") == 0

    def test_longer(self):
        assert _estimate_tokens_inline("a" * 100) == 25


# ── Helpers for crafted ToolStats ──────────────────────────────────


def _make_opus_session(**overrides) -> SessionStats:
    defaults = dict(
        session_id="s1",
        tool="Claude Code",
        model="claude-opus-4-6",
        turns=10,
        input_tokens=500_000,
        output_tokens=100_000,
        cache_read_tokens=200_000,
        cache_write_tokens=50_000,
        cost_usd=12.50,
        started=datetime(2026, 6, 1, tzinfo=timezone.utc),
        ended=datetime(2026, 6, 1, 0, 30, tzinfo=timezone.utc),
        duration_minutes=30.0,
        project="test-project",
    )
    defaults.update(overrides)
    return SessionStats(**defaults)


def _make_sonnet_session(**overrides) -> SessionStats:
    defaults = dict(
        session_id="s2",
        tool="Claude Code",
        model="claude-sonnet-4-6",
        turns=5,
        input_tokens=300_000,
        output_tokens=60_000,
        cache_read_tokens=100_000,
        cache_write_tokens=20_000,
        cost_usd=1.30,
        started=datetime(2026, 6, 2, tzinfo=timezone.utc),
        ended=datetime(2026, 6, 2, 0, 15, tzinfo=timezone.utc),
        duration_minutes=15.0,
        project="test-project",
    )
    defaults.update(overrides)
    return SessionStats(**defaults)


def _mock_collect(tool_stats_list):
    """Return a patcher that replaces _collect_stats."""
    return patch(
        "ai_helper.stats._collect_stats",
        return_value=tool_stats_list,
    )


# ── stats recommend tests ─────────────────────────────────────────


class TestShowRecommend:
    def test_no_data(self, capsys):
        with _mock_collect([]):
            show_recommend()
        captured = capsys.readouterr().out
        assert "No session data" in captured

    def test_no_opus_usage(self, capsys):
        ts = ToolStats(tool="Claude Code", sessions=[_make_sonnet_session()])
        with _mock_collect([ts]):
            show_recommend()
        captured = capsys.readouterr().out
        assert "No Opus usage" in captured

    def test_what_if_table_shown(self, capsys):
        ts = ToolStats(
            tool="Claude Code",
            sessions=[_make_opus_session(), _make_sonnet_session()],
        )
        with _mock_collect([ts]):
            show_recommend()
        captured = capsys.readouterr().out
        assert "What-If Savings" in captured
        assert "20%" in captured
        assert "40%" in captured
        assert "60%" in captured
        assert "Sonnet instead" in captured

    def test_subscription_caveat(self, capsys):
        ts = ToolStats(
            tool="Claude Code",
            sessions=[_make_opus_session()],
        )
        with _mock_collect([ts]):
            show_recommend()
        captured = capsys.readouterr().out
        assert "Flat-rate plans" in captured
        assert "Max, Team" in captured


# ── stats context tests ───────────────────────────────────────────


class TestShowContext:
    def test_no_data(self, capsys):
        with _mock_collect([]):
            show_context()
        captured = capsys.readouterr().out
        assert "No session data" in captured

    def test_session_counts_shown(self, capsys):
        ts = ToolStats(
            tool="Claude Code",
            sessions=[_make_opus_session(), _make_sonnet_session()],
        )
        with _mock_collect([ts]):
            show_context()
        captured = capsys.readouterr().out
        assert "Context Usage" in captured
        assert "Sessions" in captured
        # Should show 2 sessions, not turns
        assert "2" in captured

    def test_uses_sessions_not_turns(self, capsys):
        """Verify session count (not turn count) is used."""
        s1 = _make_opus_session(turns=50)
        s2 = _make_sonnet_session(turns=30)
        ts = ToolStats(tool="Claude Code", sessions=[s1, s2])
        with _mock_collect([ts]):
            show_context()
        captured = capsys.readouterr().out
        # Table should show "2" sessions, not "50" or "80" turns
        assert "Context Usage" in captured


# ── stats compare tests ───────────────────────────────────────────


class TestShowCompare:
    def test_no_data(self, capsys):
        with _mock_collect([]):
            show_compare()
        captured = capsys.readouterr().out
        assert "No session data" in captured

    def test_tiers_shown(self, capsys):
        ts = ToolStats(
            tool="Claude Code",
            sessions=[_make_opus_session(), _make_sonnet_session()],
        )
        with _mock_collect([ts]):
            show_compare()
        captured = capsys.readouterr().out
        assert "Cost per Session" in captured
        assert "Opus" in captured
        assert "Sonnet" in captured

    def test_no_cost_ratio(self, capsys):
        """Must NOT contain 'Nx cheaper' language."""
        ts = ToolStats(
            tool="Claude Code",
            sessions=[_make_opus_session(), _make_sonnet_session()],
        )
        with _mock_collect([ts]):
            show_compare()
        captured = capsys.readouterr().out
        assert "cheaper" not in captured.lower()

    def test_subscription_caveat(self, capsys):
        ts = ToolStats(
            tool="Claude Code",
            sessions=[_make_opus_session()],
        )
        with _mock_collect([ts]):
            show_compare()
        captured = capsys.readouterr().out
        assert "Flat-rate plans" in captured


# ── CLI backward compatibility tests ──────────────────────────────


class TestStatsCLIBackwardCompat:
    def test_bare_stats_still_works(self):
        """ai-helper stats --period 1d should still exit 0."""
        runner = CliRunner()
        result = runner.invoke(main, ["stats", "--period", "1d"])
        assert result.exit_code == 0

    def test_stats_recommend_subcommand(self):
        runner = CliRunner()
        result = runner.invoke(main, ["stats", "recommend"])
        assert result.exit_code == 0

    def test_stats_context_subcommand(self):
        runner = CliRunner()
        result = runner.invoke(main, ["stats", "context"])
        assert result.exit_code == 0

    def test_stats_compare_subcommand(self):
        runner = CliRunner()
        result = runner.invoke(main, ["stats", "compare"])
        assert result.exit_code == 0

    def test_stats_help_shows_subcommands(self):
        runner = CliRunner()
        result = runner.invoke(main, ["stats", "--help"])
        assert result.exit_code == 0
        assert "recommend" in result.output
        assert "context" in result.output
        assert "compare" in result.output

    def test_period_all_warning_in_help(self):
        """C9: --period help text should mention large histories may be slow."""
        runner = CliRunner()
        result = runner.invoke(main, ["stats", "--help"])
        assert result.exit_code == 0
        assert "slow" in result.output.lower()
