"""ai-helper stats — cross-tool usage insights and analytics."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ai_helper.tools import detect_tools

console = Console()

PRICING = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
    "claude-opus-4-5": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
    "claude-haiku-4-5": {"input": 0.8, "output": 4.0, "cache_read": 0.08, "cache_write": 1.0},
}

DEFAULT_PRICING = {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75}


@dataclass
class SessionStats:
    session_id: str
    tool: str
    model: str = "unknown"
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    started: datetime | None = None
    ended: datetime | None = None
    duration_minutes: float = 0.0
    project: str = ""


@dataclass
class ToolStats:
    tool: str
    sessions: list[SessionStats] = field(default_factory=list)

    @property
    def total_input(self) -> int:
        return sum(s.input_tokens for s in self.sessions)

    @property
    def total_output(self) -> int:
        return sum(s.output_tokens for s in self.sessions)

    @property
    def total_cache_read(self) -> int:
        return sum(s.cache_read_tokens for s in self.sessions)

    @property
    def total_cost(self) -> float:
        return sum(s.cost_usd for s in self.sessions)

    @property
    def total_minutes(self) -> float:
        return sum(s.duration_minutes for s in self.sessions)

    @property
    def models_used(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.sessions:
            counts[s.model] = counts.get(s.model, 0) + s.turns
        return counts


def show_stats(period: str = "7d", tool_filter: str = "all") -> None:
    cutoff = _parse_period(period)
    all_stats = _collect_stats(cutoff, tool_filter)

    if not all_stats:
        console.print("[bold red]No session data found.[/bold red]")
        return

    _print_summary(all_stats, period)
    _print_sessions(all_stats)
    _print_models(all_stats)
    _print_cost_caveat()


def _parse_period(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    period = period.lower().strip()
    if period == "all":
        return datetime(2020, 1, 1, tzinfo=timezone.utc)
    if period.endswith("d"):
        try:
            days = int(period[:-1])
        except ValueError:
            console.print(
                f"[yellow]Warning: invalid period '{period}',"
                " using 7d[/yellow]"
            )
            return now - timedelta(days=7)
        return now - timedelta(days=days)
    if period.endswith("w"):
        try:
            weeks = int(period[:-1])
        except ValueError:
            console.print(
                f"[yellow]Warning: invalid period '{period}',"
                " using 7d[/yellow]"
            )
            return now - timedelta(days=7)
        return now - timedelta(weeks=weeks)
    return now - timedelta(days=7)


def _collect_stats(
    cutoff: datetime, tool_filter: str
) -> list[ToolStats]:
    tools = detect_tools()
    results = []

    for tool in tools:
        if not tool.installed:
            continue
        if tool_filter != "all" and tool_filter.lower() not in tool.name.lower():
            continue

        if tool.name == "Claude Code":
            stats = _read_claude_sessions(cutoff)
            if stats.sessions:
                results.append(stats)

    return results


def _read_claude_sessions(cutoff: datetime) -> ToolStats:
    stats = ToolStats(tool="Claude Code")
    projects_dir = Path.home() / ".claude" / "projects"

    if not projects_dir.exists():
        return stats

    home_slug = str(Path.home()).replace(os.sep, "-").lstrip("-")

    for jsonl_path in projects_dir.rglob("*.jsonl"):
        mtime = datetime.fromtimestamp(
            os.path.getmtime(jsonl_path), tz=timezone.utc
        )
        if mtime < cutoff:
            continue

        session = _parse_claude_session(jsonl_path)
        if session and session.started and session.started >= cutoff:
            project_dir = jsonl_path.parent.name
            session.project = project_dir.replace(f"-{home_slug}-", "~/")
            stats.sessions.append(session)

    stats.sessions.sort(
        key=lambda s: s.started or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return stats


def _parse_claude_session(path: Path) -> SessionStats | None:
    try:
        session_id = path.stem
        session = SessionStats(session_id=session_id, tool="Claude Code")
        models: dict[str, int] = {}
        first_ts = None
        last_ts = None

        with open(path) as f:
            for line in f:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if d.get("type") == "assistant":
                    msg = d.get("message", {})
                    model = msg.get("model", "unknown")
                    if model == "<synthetic>":
                        continue

                    session.turns += 1
                    models[model] = models.get(model, 0) + 1

                    usage = msg.get("usage", {})
                    session.input_tokens += usage.get("input_tokens", 0)
                    session.output_tokens += usage.get("output_tokens", 0)
                    session.cache_read_tokens += usage.get(
                        "cache_read_input_tokens", 0
                    )
                    session.cache_write_tokens += usage.get(
                        "cache_creation_input_tokens", 0
                    )

                    ts_str = d.get("timestamp")
                    if ts_str:
                        ts = _parse_ts(ts_str)
                        if ts:
                            if first_ts is None:
                                first_ts = ts
                            last_ts = ts

        if not session.turns:
            return None

        session.model = max(models, key=models.get) if models else "unknown"
        session.started = first_ts
        session.ended = last_ts

        if first_ts and last_ts:
            session.duration_minutes = (
                last_ts - first_ts
            ).total_seconds() / 60

        session.cost_usd = _estimate_cost(
            session.model,
            session.input_tokens,
            session.output_tokens,
            session.cache_read_tokens,
            session.cache_write_tokens,
        )

        return session
    except OSError:
        return None


def _estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read: int,
    cache_write: int,
) -> float:
    prices = PRICING.get(model, DEFAULT_PRICING)
    cost = (
        input_tokens * prices["input"]
        + output_tokens * prices["output"]
        + cache_read * prices["cache_read"]
        + cache_write * prices["cache_write"]
    ) / 1_000_000
    return round(cost, 4)


def _parse_ts(ts_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _print_summary(all_stats: list[ToolStats], period: str) -> None:
    table = Table(title=f"Usage Summary ({period})")
    table.add_column("Metric", style="dim")
    for ts in all_stats:
        table.add_column(ts.tool, min_width=14)

    table.add_row("Sessions", *[str(len(ts.sessions)) for ts in all_stats])
    table.add_row(
        "Input Tokens",
        *[_format_tokens(ts.total_input) for ts in all_stats],
    )
    table.add_row(
        "Output Tokens",
        *[_format_tokens(ts.total_output) for ts in all_stats],
    )
    table.add_row(
        "Cache Read",
        *[_format_tokens(ts.total_cache_read) for ts in all_stats],
    )
    table.add_row(
        "Est. Cost",
        *[f"${ts.total_cost:.2f}" for ts in all_stats],
    )
    table.add_row(
        "Total Time",
        *[f"{ts.total_minutes:.0f} min" for ts in all_stats],
    )

    console.print()
    console.print(table)


def _print_sessions(all_stats: list[ToolStats]) -> None:
    for ts in all_stats:
        if not ts.sessions:
            continue

        recent = ts.sessions[:10]
        table = Table(title=f"Recent Sessions — {ts.tool}")
        table.add_column("Date", style="dim")
        table.add_column("Model")
        table.add_column("Turns", justify="right")
        table.add_column("Output", justify="right")
        table.add_column("Cost", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Project", max_width=30)

        for s in recent:
            date = s.started.strftime("%m/%d %H:%M") if s.started else "-"
            dur = f"{s.duration_minutes:.0f}m" if s.duration_minutes else "-"
            table.add_row(
                date,
                s.model,
                str(s.turns),
                _format_tokens(s.output_tokens),
                f"${s.cost_usd:.2f}",
                dur,
                s.project,
            )

        console.print()
        console.print(table)


def _print_models(all_stats: list[ToolStats]) -> None:
    all_models: dict[str, int] = {}
    for ts in all_stats:
        for model, turns in ts.models_used.items():
            all_models[model] = all_models.get(model, 0) + turns

    if not all_models:
        return

    table = Table(title="Model Usage (by turns)")
    table.add_column("Model")
    table.add_column("Turns", justify="right")
    table.add_column("Share", justify="right")

    total = sum(all_models.values())
    for model, turns in sorted(
        all_models.items(), key=lambda x: x[1], reverse=True
    ):
        pct = turns / total * 100 if total else 0
        table.add_row(model, str(turns), f"{pct:.0f}%")

    console.print()
    console.print(table)


def _print_cost_caveat() -> None:
    console.print()
    console.print(
        "[dim]Note: Cost estimates are approximate, based on published"
        " pricing. Actual billing may differ.[/dim]"
    )
    console.print()
