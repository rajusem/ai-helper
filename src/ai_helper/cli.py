"""ai-helper CLI entry point."""

import sys

import click

from ai_helper import __version__


@click.group()
@click.version_option(version=__version__)
def main():
    """ai-helper: work smarter with AI coding tools."""


@main.command(context_settings={
    "ignore_unknown_options": True,
    "allow_extra_args": True,
})
@click.argument("path", default=".", required=False)
@click.pass_context
def scan(ctx, path):
    """[Moved] Use skill-lint instead."""
    click.echo(
        "The 'ai-helper scan' command has moved to the standalone 'skill-lint' package.\n"
        "\n"
        "  Install:  pip install ai-skill-lint\n"
        "  Usage:    skill-lint [path]\n"
        "  Repo:     https://github.com/rajusem/skill-lint\n"
    )
    sys.exit(1)


@main.group(invoke_without_command=True)
@click.option(
    "--period", default="7d",
    help="Time period (7d, 30d, all). Note: 'all' scans full history and may be slow.",
)
@click.option("--tool", default="all", help="Filter by tool (claude, opencode, cursor, all)")
@click.pass_context
def stats(ctx, period, tool):
    """Show usage insights and analytics."""
    ctx.ensure_object(dict)
    ctx.obj["period"] = period
    ctx.obj["tool"] = tool
    if ctx.invoked_subcommand is None:
        from ai_helper.stats import show_stats

        show_stats(period=period, tool_filter=tool)


@stats.command()
@click.pass_context
def recommend(ctx):
    """What-if cost savings by shifting Opus usage to Sonnet."""
    from ai_helper.stats import show_recommend

    show_recommend(period=ctx.obj["period"], tool_filter=ctx.obj["tool"])


@stats.command()
@click.pass_context
def context(ctx):
    """Context-window usage per tool (session count, not turns)."""
    from ai_helper.stats import show_context

    show_context(period=ctx.obj["period"], tool_filter=ctx.obj["tool"])


@stats.command()
@click.pass_context
def compare(ctx):
    """Plain cost-per-session comparison across model tiers."""
    from ai_helper.stats import show_compare

    show_compare(period=ctx.obj["period"], tool_filter=ctx.obj["tool"])


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
    click.echo(
        "ai-helper init is not yet available.\n"
        "Use 'ai-helper doctor' to check your current setup."
    )


@main.command()
def doctor():
    """Health check across all AI tools."""
    from ai_helper.doctor import run_doctor

    run_doctor()


if __name__ == "__main__":
    main()
