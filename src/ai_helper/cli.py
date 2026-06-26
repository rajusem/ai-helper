"""ai-helper CLI entry point."""

import sys

import click

from ai_helper import __version__


@click.group()
@click.version_option(version=__version__)
def main():
    """ai-helper: work smarter with AI coding tools."""


_VALID_SEVERITIES = {"warning", "suggestion", "info"}


def _validate_severity(ctx, param, value):
    if value is None:
        return value
    for s in value.split(","):
        s = s.strip().lower()
        if not s:
            continue
        if s not in _VALID_SEVERITIES:
            raise click.BadParameter(
                f"Invalid severity '{s}'. "
                f"Choose from: {', '.join(sorted(_VALID_SEVERITIES))}"
            )
    return value


@main.command()
@click.argument("path", default=".")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "sarif"]), default="table")
@click.option("--severity", default=None, callback=_validate_severity,
              help="Filter by severity (warning,suggestion,info)")
@click.option(
    "--verbose", "-v", is_flag=True, default=False,
    help="Show all issues (no top-N truncation)",
)
@click.option(
    "--disable", default=None,
    help="Comma-separated rule IDs to suppress (e.g. HRISK002,OQUAL001)",
)
@click.option(
    "--fail-on",
    "fail_on",
    type=click.Choice(["warning", "suggestion", "info"]),
    default=None,
    help="Exit 1 if issues at this severity or above (for CI)",
)
@click.option(
    "--save-baseline", is_flag=True, default=False,
    help="Save current findings as baseline for future --diff",
)
@click.option(
    "--diff", "diff_baseline", is_flag=True, default=False,
    help="Show only NEW findings not in the saved baseline",
)
@click.option(
    "--baseline-path", default=None,
    help="Override baseline file path",
)
@click.option(
    "--report", is_flag=True, default=False,
    help="Show aggregate summary instead of per-file details",
)
def scan(path, fmt, severity, verbose, disable, fail_on,
         save_baseline, diff_baseline, baseline_path, report):
    """Scan skill and agent files for issues."""
    from ai_helper.scan import SEVERITY_ORDER, run_scan

    if save_baseline and diff_baseline:
        click.echo("Error: --save-baseline and --diff are mutually exclusive")
        sys.exit(1)

    disabled_rules = None
    if disable:
        disabled_rules = {
            r.strip().upper() for r in disable.split(",") if r.strip()
        }

    counts = run_scan(
        path=path,
        fmt=fmt,
        severity_filter=severity,
        verbose=verbose,
        disabled_rules=disabled_rules,
        fail_on=fail_on,
        save_baseline=save_baseline,
        diff_baseline=diff_baseline,
        baseline_path=baseline_path,
        report=report,
    )

    if fail_on is not None:
        threshold = SEVERITY_ORDER[fail_on]
        has_failing = any(
            counts.get(sev, 0) > 0
            for sev, order in SEVERITY_ORDER.items()
            if order <= threshold
        )
        if has_failing:
            sys.exit(1)


@main.command()
@click.option("--period", default="7d", help="Time period (7d, 30d, all)")
@click.option("--tool", default="all", help="Filter by tool (claude, opencode, cursor, all)")
def stats(period, tool):
    """Show usage insights and analytics."""
    from ai_helper.stats import show_stats

    show_stats(period=period, tool_filter=tool)


@main.group("config")
def config_cmd():
    """Manage AI tool configuration."""


@config_cmd.command("show")
def config_show():
    """Show current configuration across all tools."""
    from ai_helper.config import show_config

    show_config()


@config_cmd.command("set")
@click.option("--model", default=None, help="Primary model (e.g. opus, sonnet, claude-sonnet-4-6)")
@click.option("--small-model", default=None, help="Small/fast model (e.g. haiku, sonnet)")
@click.option(
    "--tool",
    default="all",
    help="Apply to specific tool (claude, opencode, cursor, all)",
)
def config_set(model, small_model, tool):
    """Set model configuration across tools."""
    from ai_helper.config import set_config

    if not model and not small_model:
        click.echo("Provide at least one of --model or --small-model")
        raise SystemExit(1)
    set_config(model=model, small_model=small_model, tool_filter=tool)


@main.group()
def optimize():
    """Smart defaults and optimization."""


@optimize.command("install")
@click.argument("target", default="rtk", type=click.Choice(["rtk", "ponytail"]))
def optimize_install(target):
    """Install optimization tools (rtk, ponytail)."""
    from ai_helper.optimize import run_install

    run_install(target)


@optimize.command("status")
def optimize_status():
    """Show which optimizations are active."""
    from ai_helper.optimize import run_status

    run_status()


@optimize.command("report")
def optimize_report():
    """Show measured token savings."""
    from ai_helper.optimize import run_report

    run_report()


@optimize.command("discover")
def optimize_discover():
    """Find missed optimization opportunities."""
    from ai_helper.optimize import run_discover

    run_discover()


@main.command()
def init():
    """Set up AI tooling for this project."""
    click.echo("Initializing... (not yet implemented)")


@main.command()
def doctor():
    """Health check across all AI tools."""
    from ai_helper.doctor import run_doctor

    run_doctor()


if __name__ == "__main__":
    main()
