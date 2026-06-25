"""Basic CLI smoke tests."""

from click.testing import CliRunner

from ai_helper.cli import main


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.output
    assert "stats" in result.output
    assert "config" in result.output
    assert "optimize" in result.output
    assert "init" in result.output
    assert "doctor" in result.output


def test_scan_runs():
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "."])
    assert result.exit_code == 0
    assert "Scanning" in result.output or "No skill" in result.output


def test_doctor_runs():
    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])
    assert result.exit_code == 0
    assert "Summary" in result.output


def test_config_show():
    runner = CliRunner()
    result = runner.invoke(main, ["config", "show"])
    assert result.exit_code == 0
    assert "Configuration" in result.output


def test_config_set_requires_option():
    runner = CliRunner()
    result = runner.invoke(main, ["config", "set"])
    assert result.exit_code == 1


def test_config_set_help():
    runner = CliRunner()
    result = runner.invoke(main, ["config", "set", "--help"])
    assert result.exit_code == 0
    assert "--model" in result.output
    assert "--small-model" in result.output


def test_stats_runs():
    runner = CliRunner()
    result = runner.invoke(main, ["stats", "--period", "1d"])
    assert result.exit_code == 0


def test_optimize_status():
    runner = CliRunner()
    result = runner.invoke(main, ["optimize", "status"])
    assert result.exit_code == 0
    assert "RTK" in result.output


def test_optimize_help():
    runner = CliRunner()
    result = runner.invoke(main, ["optimize", "--help"])
    assert result.exit_code == 0
    assert "install" in result.output
    assert "status" in result.output
    assert "report" in result.output
    assert "discover" in result.output
