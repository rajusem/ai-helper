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


def test_verbose_flag():
    """The -v / --verbose flag should be accepted."""
    runner = CliRunner()
    result = runner.invoke(main, ["scan", ".", "-v"])
    assert result.exit_code == 0
    result2 = runner.invoke(main, ["scan", ".", "--verbose"])
    assert result2.exit_code == 0


def test_sarif_format():
    """The --format sarif option should produce valid JSON with SARIF keys."""
    runner = CliRunner()
    result = runner.invoke(main, ["scan", ".", "--format", "sarif"])
    assert result.exit_code == 0
    # Even if no files found, the SARIF structure should be output
    # or "No skill" message should appear
    if "No skill" not in result.output:
        import json
        # Extract JSON from output (skip the "Scanning..." preamble)
        json_start = result.output.index("{")
        sarif = json.loads(result.output[json_start:])
        assert sarif["version"] == "2.1.0"


def test_scan_help_correct_severities():
    """The scan --help should show correct severity values."""
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--help"])
    assert result.exit_code == 0
    assert "warning,suggestion,info" in result.output
    # Old incorrect text should NOT be present
    assert "critical,high" not in result.output


def test_disable_flag():
    """The --disable flag should be accepted without error."""
    runner = CliRunner()
    result = runner.invoke(main, ["scan", ".", "--disable", "HRISK002,OQUAL001"])
    assert result.exit_code == 0


def test_scan_help_correct_docstring():
    """The scan help should show the correct description."""
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--help"])
    assert result.exit_code == 0
    assert "Scan skill and agent files for issues" in result.output
    # Old incorrect text should NOT be present
    assert "security vulnerabilities" not in result.output


# ── --fail-on tests ──────────────────────────────────────────────────


def test_fail_on_warning_exits_1_when_warnings_present(tmp_path):
    """--fail-on warning should exit 1 when scan finds warnings."""
    # Create a file with >500 lines to trigger TCOST001 (warning)
    skill = tmp_path / "SKILL.md"
    skill.write_text("\n".join([f"line {i}" for i in range(510)]))
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--fail-on", "warning"])
    assert result.exit_code == 1


def test_no_fail_on_exits_0_even_with_warnings(tmp_path):
    """Without --fail-on, exit code should always be 0 (backward compat)."""
    skill = tmp_path / "SKILL.md"
    skill.write_text("\n".join([f"line {i}" for i in range(510)]))
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0


def test_fail_on_suggestion_also_catches_warnings(tmp_path):
    """--fail-on suggestion should exit 1 when warnings are present
    (warning > suggestion in hierarchy)."""
    skill = tmp_path / "SKILL.md"
    skill.write_text("\n".join([f"line {i}" for i in range(510)]))
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--fail-on", "suggestion"])
    assert result.exit_code == 1


def test_fail_on_warning_exits_0_with_only_suggestions(tmp_path):
    """--fail-on warning should exit 0 when only suggestions exist (no warnings)."""
    # Create a file ~2500 tokens to trigger TCOST003 (suggestion) but not TCOST001/002 (warning)
    # ~2500 tokens = ~10000 chars, in <500 lines
    skill = tmp_path / "SKILL.md"
    # Each line ~25 chars, 400 lines = 10000 chars = ~2500 tokens
    skill.write_text("\n".join(["x" * 25 for _ in range(400)]))
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--fail-on", "warning"])
    assert result.exit_code == 0


def test_fail_on_path_not_found_exits_0(tmp_path):
    """--fail-on with a nonexistent path should exit 0 (no findings)."""
    runner = CliRunner()
    result = runner.invoke(
        main, ["scan", str(tmp_path / "nonexistent"), "--fail-on", "warning"]
    )
    assert result.exit_code == 0


def test_fail_on_no_files_exits_0(tmp_path):
    """--fail-on with a directory containing no skill files should exit 0."""
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--fail-on", "warning"])
    assert result.exit_code == 0


def test_fail_on_with_disable_of_only_warning(tmp_path):
    """--fail-on warning combined with --disable of the only warning rule
    should exit 0."""
    # Create a file with >500 lines to trigger TCOST001 (warning)
    skill = tmp_path / "SKILL.md"
    skill.write_text("## Heading\n" + "\n".join([f"line {i}" for i in range(510)]))
    runner = CliRunner()
    # First verify that without --disable it would exit 1
    result_no_disable = runner.invoke(
        main, ["scan", str(tmp_path), "--fail-on", "warning"]
    )
    assert result_no_disable.exit_code == 1
    # Now disable all known warning rules that a >500 line file triggers
    result_with_disable = runner.invoke(
        main, [
            "scan", str(tmp_path),
            "--fail-on", "warning",
            "--disable",
            "TCOST001,TCOST002,STRUCT003,STRUCT006,HRISK002,OQUAL001,OQUAL002,BPRAC003",
        ]
    )
    assert result_with_disable.exit_code == 0


def test_fail_on_help_shows_option():
    """--fail-on should appear in scan --help."""
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--fail-on" in result.output
