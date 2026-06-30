"""ai-helper optimize — smart defaults and optimization tooling."""

from __future__ import annotations

import shutil
import subprocess

from rich.console import Console
from rich.panel import Panel

from ai_helper.tools import detect_tools

console = Console()


def run_install(target: str = "rtk") -> None:
    if target == "rtk":
        _install_rtk()
    elif target == "ponytail":
        _install_ponytail()
    else:
        console.print(f"[bold red]Unknown target: {target}[/bold red]")
        console.print("Available: rtk, ponytail")


def run_status() -> None:
    console.print()
    rtk_path = shutil.which("rtk")
    if rtk_path:
        version = _run_cmd([rtk_path, "--version"])
        console.print(f"[green]RTK[/green]  installed ({version.strip()})")

        hooks = _check_rtk_hooks()
        if hooks:
            for tool_name, status in hooks.items():
                icon = "[green]v[/green]" if status else "[yellow]![/yellow]"
                label = "active" if status else "not configured"
                console.print(f"  {icon} {tool_name}: {label}")
        else:
            msg = "No hooks configured — run: ai-helper optimize install rtk"
            console.print(f"  [yellow]![/yellow] {msg}")
    else:
        console.print("[dim]RTK[/dim]  not installed")
        console.print(
            "  Install: [bold]brew install rtk-ai/tap/rtk[/bold]"
            " or [bold]curl -fsSL"
            " https://raw.githubusercontent.com/rtk-ai/rtk/"
            "refs/heads/master/install.sh | sh[/bold]"
        )

    ponytail = _check_ponytail()
    if ponytail:
        console.print(f"[green]Ponytail[/green]  found ({ponytail})")
    else:
        console.print("[dim]Ponytail[/dim]  not detected")

    headroom_path = shutil.which("headroom")
    if headroom_path:
        version = _run_cmd([headroom_path, "--version"])
        console.print(f"[green]Headroom[/green]  installed ({version.strip()})")
    else:
        console.print("[dim]Headroom[/dim]  not installed")

    console.print()
    console.print(
        "[dim]Tip: These tools compress tokens (0.5-3% bill savings)."
        " For bigger impact, use model routing"
        " (ai-helper config set --model sonnet) and keep"
        " CLAUDE.md lean.[/dim]"
    )
    console.print()


def run_report() -> None:
    rtk_path = shutil.which("rtk")
    if not rtk_path:
        console.print("[bold red]RTK not installed.[/bold red]")
        _print_rtk_install()
        return

    output = _run_cmd([rtk_path, "gain"])
    if output:
        console.print()
        console.print(Panel(output.strip(), title="RTK Token Savings", border_style="green"))
        console.print()


def run_discover() -> None:
    rtk_path = shutil.which("rtk")
    if not rtk_path:
        console.print("[bold red]RTK not installed.[/bold red]")
        _print_rtk_install()
        return

    output = _run_cmd([rtk_path, "discover"])
    if output:
        console.print()
        panel = Panel(output.strip(), title="Optimization Opportunities", border_style="yellow")
        console.print(panel)
        console.print()


def _install_rtk() -> None:
    rtk_path = shutil.which("rtk")
    if not rtk_path:
        console.print("[bold red]RTK not installed.[/bold red]")
        console.print("Install RTK first:")
        console.print("  macOS:  [bold]brew install rtk-ai/tap/rtk[/bold]")
        console.print(
            "  Linux:  [bold]curl -fsSL"
            " https://raw.githubusercontent.com/rtk-ai/rtk/"
            "refs/heads/master/install.sh | sh[/bold]"
        )
        return

    version = _run_cmd([rtk_path, "--version"]).strip()
    console.print(f"RTK {version} found at {rtk_path}")
    console.print()

    tools = detect_tools()
    installed = [t for t in tools if t.installed]

    for tool in installed:
        if tool.name == "Claude Code":
            _install_rtk_claude(rtk_path, tool)
        elif tool.name == "OpenCode":
            _install_rtk_opencode(rtk_path, tool)
        elif tool.name == "Cursor":
            _install_rtk_cursor(rtk_path, tool)

    console.print()
    console.print("Run [bold]ai-helper optimize report[/bold] to see savings after a few sessions.")


def _install_rtk_claude(rtk_path: str, tool) -> None:
    rtk_active = tool.extras.get("rtk_active", False)
    if rtk_active:
        console.print("  [green]v[/green] Claude Code: RTK already configured")
        return

    console.print("  Setting up RTK for Claude Code...")
    result = subprocess.run(
        [rtk_path, "init", "-g"], capture_output=True, text=True
    )
    if result.returncode == 0:
        console.print("  [green]v[/green] Claude Code: RTK hooks installed (global)")
    else:
        console.print("  [red]x[/red] Claude Code: RTK init failed")
        if result.stderr:
            console.print(f"       {result.stderr.strip()}")


def _install_rtk_opencode(rtk_path: str, tool) -> None:
    console.print("  Setting up RTK for OpenCode...")
    result = subprocess.run(
        [rtk_path, "init", "--opencode"], capture_output=True, text=True
    )
    if result.returncode == 0:
        console.print("  [green]v[/green] OpenCode: RTK plugin installed")
    else:
        console.print("  [yellow]![/yellow] OpenCode: RTK init returned non-zero")
        if result.stderr:
            console.print(f"       {result.stderr.strip()}")
        if result.stdout:
            console.print(f"       {result.stdout.strip()}")


def _install_rtk_cursor(rtk_path: str, tool) -> None:
    console.print("  Setting up RTK for Cursor...")
    result = subprocess.run(
        [rtk_path, "init", "-g", "--agent", "cursor"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        console.print("  [green]v[/green] Cursor: RTK hooks installed")
    else:
        console.print("  [red]x[/red] Cursor: RTK init failed")
        if result.stderr:
            console.print(f"       {result.stderr.strip()}")


def _install_ponytail() -> None:
    console.print("[yellow]Ponytail install varies by tool:[/yellow]")
    console.print(
        "  Claude Code: Run [bold]/plugin marketplace add"
        " DietrichGebert/ponytail[/bold] then"
        " [bold]/plugin install ponytail@ponytail[/bold]"
    )
    console.print(
        '  OpenCode:    Add [bold]'
        '{"plugin": ["@dietrichgebert/ponytail"]}[/bold]'
        " to opencode.json"
    )
    console.print(
        "  Details:     https://github.com/DietrichGebert/ponytail"
    )


def _print_rtk_install() -> None:
    console.print(
        "Install: [bold]brew install rtk-ai/tap/rtk[/bold]"
        " or [bold]curl -fsSL"
        " https://raw.githubusercontent.com/rtk-ai/rtk/"
        "refs/heads/master/install.sh | sh[/bold]"
    )


def _check_rtk_hooks() -> dict[str, bool]:
    from pathlib import Path

    tools = detect_tools()
    result = {}
    for tool in tools:
        if not tool.installed:
            continue
        if tool.name == "Claude Code":
            result[tool.name] = tool.extras.get("rtk_active", False)
        elif tool.name == "OpenCode":
            plugin_path = (
                Path.home() / ".config" / "opencode"
                / "node_modules" / "rtk-opencode"
            )
            result[tool.name] = plugin_path.exists()
        elif tool.name == "Cursor":
            hooks_json = Path.home() / ".cursor" / "hooks.json"
            result[tool.name] = (
                hooks_json.exists()
                and "rtk" in hooks_json.read_text(errors="replace").lower()
            )
    return result


def _check_ponytail() -> str | None:
    import json
    from pathlib import Path

    # Claude Code: plugin marketplace (current install method)
    plugin_dir = Path.home() / ".claude" / "plugins" / "ponytail"
    if plugin_dir.exists():
        return str(plugin_dir)

    # Claude Code: legacy skill directory
    skill_dir = Path.home() / ".claude" / "skills" / "ponytail"
    if skill_dir.exists():
        return str(skill_dir)

    # OpenCode: check opencode.json for ponytail plugin
    oc_config = Path.home() / ".config" / "opencode" / "opencode.json"
    if oc_config.exists():
        try:
            data = json.loads(oc_config.read_text())
            plugins = data.get("plugin", [])
            if any("ponytail" in str(p).lower() for p in plugins):
                return "opencode plugin"
        except (json.JSONDecodeError, OSError):
            pass

    # OpenCode: legacy skill directory
    oc_skill = Path.home() / ".config" / "opencode" / "skills" / "ponytail"
    if oc_skill.exists():
        return str(oc_skill)

    return None


def _run_cmd(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""
