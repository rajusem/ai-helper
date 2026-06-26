"""Tests for medium-severity fixes M5, M7, M8."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# ── M5: _find_binary uses only shutil.which ──────────────────────


class TestFindBinary:
    """M5: _find_binary should use shutil.which and not subprocess."""

    def test_finds_existing_binary(self):
        from ai_helper.tools.base import ToolDetector

        detector = ToolDetector()
        detector.binary_name = "python3"
        result = detector._find_binary()
        # python3 should exist on the test system
        assert result is not None
        assert "python3" in result

    def test_returns_none_for_missing_binary(self):
        from ai_helper.tools.base import ToolDetector

        detector = ToolDetector()
        detector.binary_name = "nonexistent_binary_xyz_12345"
        result = detector._find_binary()
        assert result is None

    def test_no_subprocess_call(self):
        """_find_binary should NOT spawn a subprocess."""
        import subprocess

        from ai_helper.tools.base import ToolDetector

        detector = ToolDetector()
        detector.binary_name = "nonexistent_binary_xyz_12345"
        with patch.object(subprocess, "run") as mock_run:
            detector._find_binary()
            mock_run.assert_not_called()


# ── M7: Atomic config writes ─────────────────────────────────────


class TestAtomicConfigWrite:
    """M7: _write_json should use atomic temp+replace pattern."""

    def test_writes_valid_json(self, tmp_path):
        from ai_helper.config import _write_json

        path = tmp_path / "test.json"
        data = {"model": "opus", "key": "value"}
        _write_json(path, data)

        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded == data

    def test_creates_parent_dirs(self, tmp_path):
        from ai_helper.config import _write_json

        path = tmp_path / "sub" / "dir" / "test.json"
        _write_json(path, {"key": "val"})
        assert path.exists()

    def test_overwrites_existing_file(self, tmp_path):
        from ai_helper.config import _write_json

        path = tmp_path / "test.json"
        _write_json(path, {"old": True})
        _write_json(path, {"new": True})
        loaded = json.loads(path.read_text())
        assert loaded == {"new": True}

    def test_no_temp_file_left_on_success(self, tmp_path):
        from ai_helper.config import _write_json

        path = tmp_path / "test.json"
        _write_json(path, {"key": "val"})
        # No .tmp files should remain
        tmp_files = list(tmp_path.glob(".config-*.tmp"))
        assert len(tmp_files) == 0

    def test_file_ends_with_newline(self, tmp_path):
        from ai_helper.config import _write_json

        path = tmp_path / "test.json"
        _write_json(path, {"key": "val"})
        content = path.read_text()
        assert content.endswith("\n")


# ── M8: _parse_period error handling ──────────────────────────────


class TestParsePeriodErrorHandling:
    """M8: _parse_period should handle invalid input gracefully."""

    def test_valid_days(self):
        from ai_helper.stats import _parse_period

        now = datetime.now(timezone.utc)
        result = _parse_period("7d")
        expected = now - timedelta(days=7)
        # Allow 1 second tolerance
        assert abs((result - expected).total_seconds()) < 1

    def test_valid_weeks(self):
        from ai_helper.stats import _parse_period

        now = datetime.now(timezone.utc)
        result = _parse_period("2w")
        expected = now - timedelta(weeks=2)
        assert abs((result - expected).total_seconds()) < 1

    def test_valid_all(self):
        from ai_helper.stats import _parse_period

        result = _parse_period("all")
        assert result.year == 2020

    def test_empty_numeric_part_d(self):
        """'d' alone (empty numeric) should not crash."""
        from ai_helper.stats import _parse_period

        now = datetime.now(timezone.utc)
        result = _parse_period("d")
        expected = now - timedelta(days=7)
        assert abs((result - expected).total_seconds()) < 1

    def test_empty_numeric_part_w(self):
        """'w' alone (empty numeric) should not crash."""
        from ai_helper.stats import _parse_period

        now = datetime.now(timezone.utc)
        result = _parse_period("w")
        expected = now - timedelta(days=7)
        assert abs((result - expected).total_seconds()) < 1

    def test_non_numeric_prefix(self):
        """'xd' should not crash."""
        from ai_helper.stats import _parse_period

        now = datetime.now(timezone.utc)
        result = _parse_period("xd")
        expected = now - timedelta(days=7)
        assert abs((result - expected).total_seconds()) < 1

    def test_float_period(self):
        """'3.5d' should fall back to 7d default."""
        from ai_helper.stats import _parse_period

        now = datetime.now(timezone.utc)
        result = _parse_period("3.5d")
        expected = now - timedelta(days=7)
        assert abs((result - expected).total_seconds()) < 1

    def test_unknown_suffix_defaults_to_7d(self):
        """Unknown suffix defaults to 7 days."""
        from ai_helper.stats import _parse_period

        now = datetime.now(timezone.utc)
        result = _parse_period("5x")
        expected = now - timedelta(days=7)
        assert abs((result - expected).total_seconds()) < 1

    def test_zero_days_valid(self):
        """'0d' is technically valid (returns now)."""
        from ai_helper.stats import _parse_period

        now = datetime.now(timezone.utc)
        result = _parse_period("0d")
        assert abs((result - now).total_seconds()) < 1
