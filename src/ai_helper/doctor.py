"""ai-helper doctor — health check across AI coding tools."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ai_helper.tools import detect_tools
from ai_helper.tools.base import ToolInfo

console = Console()


def run_doctor() -> list[ToolInfo]:
    tools = detect_tools()
    installed = [t for t in tools if t.installed]

    if not installed:
        console.print("\n[bold red]No AI coding tools detected.[/bold red]")
        console.print("ai-helper supports: Claude Code, OpenCode, Cursor\n")
        return tools

    console.print()
    for tool in tools:
        _print_tool(tool)

    _print_summary(tools)
    return tools


def _print_tool(tool: ToolInfo) -> None:
    if not tool.installed:
        console.print(f"[dim]{tool.name:<14}[/dim] [dim]not installed[/dim]")
        return

    console.print(f"[bold]{tool.name}[/bold]")

    table = Table(show_header=False, box=None, padding=(0, 2), show_edge=False)
    table.add_column(style="dim", width=16)
    table.add_column()

    table.add_row("Version", tool.version or "[dim]unknown[/dim]")

    if tool.binary_path:
        table.add_row("Binary", tool.binary_path)

    if tool.config_path:
        table.add_row("Config", str(tool.config_path))
    else:
        table.add_row("Config", "[yellow]not found[/yellow]")

    if tool.model:
        table.add_row("Model", tool.model)
    else:
        table.add_row("Model", "[dim]default[/dim]")

    if tool.extras.get("small_model"):
        table.add_row("Small Model", tool.extras["small_model"])

    if tool.mcp_servers:
        table.add_row("MCP Servers", ", ".join(tool.mcp_servers))
    else:
        table.add_row("MCP Servers", "[dim]none[/dim]")

    if tool.session_path:
        table.add_row("Sessions", str(tool.session_path))

    rtk = tool.extras.get("rtk_active")
    if rtk is not None:
        table.add_row("RTK", "[green]active[/green]" if rtk else "[dim]not configured[/dim]")

    for key in ("project_config", "context_file", "rules_file", "rules_dir", "mcp_config_path"):
        if key in tool.extras:
            label = key.replace("_", " ").title()
            table.add_row(label, tool.extras[key])

    if tool.extras.get("agents"):
        table.add_row("Agents", ", ".join(tool.extras["agents"]))
    if tool.extras.get("skills"):
        table.add_row("Skills", ", ".join(tool.extras["skills"]))

    console.print(table)

    for issue in tool.issues:
        console.print(f"  [yellow]![/yellow] {issue}")

    console.print()


def _print_summary(tools: list[ToolInfo]) -> None:
    installed = [t for t in tools if t.installed]
    total_issues = sum(len(t.issues) for t in tools)

    models = {}
    for t in installed:
        if t.model:
            models[t.name] = t.model

    console.rule("[bold]Summary[/bold]")
    console.print(f"  Tools installed: {len(installed)}/{len(tools)}")

    if models:
        model_str = ", ".join(f"{name}: {model}" for name, model in models.items())
        console.print(f"  Models: {model_str}")
        unique_models = set(models.values())
        if len(unique_models) > 1:
            console.print(
                "  [yellow]![/yellow] Different models across tools — "
                "sync with: [bold]ai-helper config set --model <model>[/bold]"
            )

    if total_issues > 0:
        console.print(f"  Issues: [yellow]{total_issues}[/yellow]")
    else:
        console.print("  Issues: [green]none[/green]")

    console.print()
