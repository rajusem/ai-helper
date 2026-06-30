"""ai-helper config — unified configuration across AI coding tools."""

from __future__ import annotations

import json
import re
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ai_helper.tools import detect_tools
from ai_helper.tools.base import ToolInfo

console = Console()

MODEL_ALIASES = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
}

KNOWN_MODELS = {
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-opus-4-5",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-fable-5",
    "claude-haiku-4-5",
    "claude-haiku-4-5-20251001",
}

KNOWN_PROVIDERS = {
    "google-vertex-anthropic",
    "anthropic",
    "bedrock",
}


def _validate_model(model: str) -> str | None:
    """Validate a model ID. Returns a warning message or None if valid."""
    if model in MODEL_ALIASES:
        return None
    if model in KNOWN_MODELS:
        return None

    # Check provider-prefixed format: provider/model@version
    if "/" in model:
        parts = model.split("/", 1)
        provider = parts[0]
        rest = parts[1]
        model_part = rest.split("@")[0] if "@" in rest else rest

        if provider not in KNOWN_PROVIDERS:
            return f"Unknown provider '{provider}'"
        if model_part not in KNOWN_MODELS:
            return f"Unknown model '{model_part}'"
        if "@" in rest:
            version = rest.split("@")[1]
            if version and not re.match(
                r"^(default|latest|\d{8,10})$", version
            ):
                return f"Suspicious version '{version}'"
        return None

    return f"Unknown model '{model}'"


def _confirm_proceed() -> bool:
    try:
        answer = console.input("  Continue anyway? [y/N] ").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def resolve_model(name: str | None) -> str | None:
    if name is None:
        return None
    return MODEL_ALIASES.get(name.lower(), name)


def show_config() -> None:
    tools = detect_tools()
    installed = [t for t in tools if t.installed]

    if not installed:
        console.print("[bold red]No AI tools detected.[/bold red]")
        return

    table = Table(title="AI Tool Configuration")
    table.add_column("Setting", style="dim")
    for tool in installed:
        table.add_column(tool.name, min_width=12)

    table.add_row("Version", *[t.version or "-" for t in installed])
    table.add_row("Model", *[t.model or "[dim]default[/dim]" for t in installed])
    table.add_row(
        "Small Model",
        *[t.extras.get("small_model", "[dim]-[/dim]") for t in installed],
    )
    table.add_row(
        "MCP Servers",
        *[", ".join(t.mcp_servers) if t.mcp_servers else "[dim]none[/dim]" for t in installed],
    )
    table.add_row(
        "Config Path",
        *[str(t.config_path) if t.config_path else "[dim]-[/dim]" for t in installed],
    )

    console.print()
    console.print(table)
    console.print()


def set_config(
    model: str | None = None,
    small_model: str | None = None,
    tool_filter: str = "all",
) -> None:
    resolved_model = resolve_model(model)
    resolved_small = resolve_model(small_model)

    for label, value in [("model", resolved_model), ("small-model", resolved_small)]:
        if value:
            warning = _validate_model(value)
            if warning:
                console.print(
                    f"[yellow]Warning: {warning} for --{label}."
                    " Proceeding anyway — use an alias (opus, sonnet,"
                    " haiku) or a known model ID.[/yellow]"
                )
                if not _confirm_proceed():
                    return

    tools = detect_tools()
    installed = [t for t in tools if t.installed]

    if tool_filter != "all":
        installed = [t for t in installed if _matches_filter(t, tool_filter)]

    if not installed:
        console.print(f"[bold red]No matching tools found for '{tool_filter}'[/bold red]")
        return

    console.print()
    for tool in installed:
        _set_tool_config(tool, resolved_model, resolved_small)
    console.print()


def _matches_filter(tool: ToolInfo, filter_name: str) -> bool:
    name = filter_name.lower().replace(" ", "").replace("-", "").replace("_", "")
    tool_name = tool.name.lower().replace(" ", "")
    aliases = {
        "claude": "claudecode",
        "claudecode": "claudecode",
        "opencode": "opencode",
        "cursor": "cursor",
    }
    return aliases.get(name, name) == aliases.get(tool_name, tool_name)


def _set_tool_config(tool: ToolInfo, model: str | None, small_model: str | None) -> None:
    if tool.name == "Claude Code":
        _set_claude_code(tool, model, small_model)
    elif tool.name == "OpenCode":
        _set_opencode(tool, model, small_model)
    elif tool.name == "Cursor":
        _set_cursor(tool, model, small_model)
    else:
        console.print(f"  [yellow]![/yellow] {tool.name}: config writing not supported")


def _set_claude_code(tool: ToolInfo, model: str | None, small_model: str | None) -> None:
    config_path = tool.config_path or Path.home() / ".claude" / "settings.json"
    config = _read_json(config_path)

    changes = []
    if model:
        old = config.get("model", "default")
        config["model"] = model
        changes.append(f"model: {old} -> {model}")
    if small_model:
        old = config.get("smallModel", "default")
        config["smallModel"] = small_model
        changes.append(f"smallModel: {old} -> {small_model}")

    if changes:
        _write_json(config_path, config)
        for change in changes:
            console.print(f"  [green]v[/green] Claude Code: {change}")
    else:
        console.print("  [dim]Claude Code: no changes[/dim]")


def _set_opencode(tool: ToolInfo, model: str | None, small_model: str | None) -> None:
    config_path = tool.config_path
    if not config_path:
        config_path = Path.home() / ".config" / "opencode" / "opencode.json"

    config = _read_json(config_path)

    changes = []
    if model:
        old = config.get("model", "default")
        config["model"] = model
        changes.append(f"model: {old} -> {model}")
    if small_model:
        old = config.get("small_model", "default")
        config["small_model"] = small_model
        changes.append(f"small_model: {old} -> {small_model}")

    if changes:
        _write_json(config_path, config)
        for change in changes:
            console.print(f"  [green]v[/green] OpenCode: {change}")
    else:
        console.print("  [dim]OpenCode: no changes[/dim]")


def _set_cursor(tool: ToolInfo, model: str | None, small_model: str | None) -> None:
    console.print(
        "  [yellow]![/yellow] Cursor: model selection is managed in the Cursor app UI"
    )
    if model:
        console.print(f"       Set your model to [bold]{model}[/bold] in Cursor Settings > Models")


def _read_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _write_json(path: Path, data: dict) -> None:
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    data_str = json.dumps(data, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(
        dir=path.parent, suffix=".tmp", prefix=".config-"
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data_str)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
