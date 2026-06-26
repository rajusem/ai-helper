"""ai-helper CLI entry point."""

import click

from ai_helper import __version__


@click.group()
@click.version_option(version=__version__)
def main():
    """ai-helper: work smarter with AI coding tools."""


@main.command()
@click.argument("path", default=".")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "sarif"]), default="table")
@click.option("--severity", default=None, help="Filter by severity (warning,suggestion,info)")
@click.option(
    "--verbose", "-v", is_flag=True, default=False,
    help="Show all issues (no top-N truncation)",
)
@click.option(
    "--disable", default=None,
    help="Comma-separated rule IDs to suppress (e.g. HRISK002,OQUAL001)",
)
def scan(path, fmt, severity, verbose, disable):
    """Scan skill and agent files for issues."""
    from ai_helper.scan import run_scan

    disabled_rules = None
    if disable:
        disabled_rules = {r.strip().upper() for r in disable.split(",") if r.strip()}

    run_scan(
        path=path,
        fmt=fmt,
        severity_filter=severity,
        verbose=verbose,
        disabled_rules=disabled_rules,
    )


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
