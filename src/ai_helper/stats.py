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
    "claude-opus-4-8": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
    "claude-opus-4-7": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
    "claude-opus-4-5": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
    "claude-fable-5": {"input": 1.0, "output": 5.0, "cache_read": 0.1, "cache_write": 1.25},
    "claude-haiku-4-5": {"input": 0.8, "output": 4.0, "cache_read": 0.08, "cache_write": 1.0},
}

# Fallback pricing for unrecognized models (Sonnet-tier rates).
DEFAULT_PRICING = {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75}

# Tier-level pricing for what-if comparisons (per 1M tokens).
TIER_PRICING = {
    "opus": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
    "sonnet": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
    "fable": {"input": 1.0, "output": 5.0, "cache_read": 0.1, "cache_write": 1.25},
    "haiku": {"input": 0.8, "output": 4.0, "cache_read": 0.08, "cache_write": 1.0},
}


def _normalize_model_tier(model: str) -> str:
    """Map a model identifier to its pricing tier.

    Handles ``@default`` suffixes and common model-name patterns.
    Returns one of: opus, sonnet, haiku, fable, local, other.
    """
    name = model.lower().split("@")[0].strip()
    if "opus" in name:
        return "opus"
    if "sonnet" in name:
        return "sonnet"
    if "haiku" in name:
        return "haiku"
    if "fable" in name:
        return "fable"
    if any(tok in name for tok in ("local", "ollama", "llama", "deepseek")):
        return "local"
    return "other"


def _estimate_tokens_inline(text: str) -> int:
    """Rough token estimate (4 chars per token). No external imports."""
    return len(text) // 4


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
    def total_cache_write(self) -> int:
        return sum(s.cache_write_tokens for s in self.sessions)

    @property
    def cache_hit_rate(self) -> float | None:
        denom = self.total_cache_read + self.total_cache_write + self.total_input
        if denom == 0:
            return None
        return self.total_cache_read / denom * 100

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
    console.print(
        f"[yellow]Warning: unrecognized period '{period}',"
        " using 7d. Valid: Nd, Nw, all[/yellow]"
    )
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
        elif tool.name == "Cursor":
            stats = _read_cursor_sessions(cutoff)
            if stats.sessions:
                results.append(stats)
        elif tool.name == "OpenCode":
            stats = _read_opencode_sessions(cutoff)
            if stats.sessions:
                results.append(stats)
            else:
                console.print(
                    "[dim]OpenCode: no session data found[/dim]"
                )

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


def _read_opencode_sessions(
    cutoff: datetime, db_path: Path | None = None,
) -> ToolStats:
    """Read OpenCode sessions from ~/.local/share/opencode/opencode.db."""
    import sqlite3
    from contextlib import closing

    stats = ToolStats(tool="OpenCode")
    if db_path is None:
        db_path = (
            Path.home() / ".local" / "share" / "opencode" / "opencode.db"
        )
    if not db_path.exists():
        return stats

    cutoff_ms = int(cutoff.timestamp() * 1000)

    try:
        uri = f"file:{db_path}?mode=ro"
        with closing(
            sqlite3.connect(uri, uri=True, timeout=5)
        ) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT title, model, cost,"
                " tokens_input, tokens_output,"
                " tokens_cache_read, tokens_cache_write,"
                " time_created, time_updated"
                " FROM session"
                " WHERE COALESCE(time_updated, time_created) >= ?"
                " ORDER BY COALESCE(time_updated, time_created) DESC",
                (cutoff_ms,),
            ).fetchall()

            for row in rows:
                model = _parse_opencode_model(row["model"])
                started = _parse_cursor_ts(row["time_created"])
                ended = _parse_cursor_ts(row["time_updated"])
                duration = 0.0
                tc = row["time_created"] or 0
                tu = row["time_updated"] or 0
                if tc and tu:
                    duration = (tu - tc) / 60000

                stats.sessions.append(SessionStats(
                    session_id=str(row["time_created"]),
                    tool="OpenCode",
                    model=model,
                    turns=1,
                    input_tokens=row["tokens_input"] or 0,
                    output_tokens=row["tokens_output"] or 0,
                    cache_read_tokens=row["tokens_cache_read"] or 0,
                    cache_write_tokens=row["tokens_cache_write"] or 0,
                    cost_usd=row["cost"] or 0.0,
                    started=started,
                    ended=ended,
                    duration_minutes=duration,
                    project=(row["title"] or "")[:40],
                ))
    except sqlite3.DatabaseError:
        return stats

    stats.sessions.sort(
        key=lambda s: s.started or datetime.min.replace(
            tzinfo=timezone.utc
        ),
        reverse=True,
    )
    return stats


def _parse_opencode_model(model_str: str | None) -> str:
    """Parse OpenCode model JSON: {"id":"claude-sonnet-4-6@default",...}"""
    if not model_str:
        return "unknown"
    try:
        data = json.loads(model_str)
        return data.get("id", "unknown")
    except (json.JSONDecodeError, TypeError):
        return model_str[:30] if model_str else "unknown"


def _read_cursor_sessions(
    cutoff: datetime, db_path: Path | None = None,
) -> ToolStats:
    """Read Cursor sessions from state.vscdb + ai-tracking DB."""
    import json as _json
    import platform
    import sqlite3
    from contextlib import closing

    stats = ToolStats(tool="Cursor")

    # Primary: composer sessions from state.vscdb
    if db_path is None:
        system = platform.system()
        if system == "Darwin":
            state_db = (
                Path.home() / "Library" / "Application Support"
                / "Cursor" / "User" / "globalStorage" / "state.vscdb"
            )
        elif system == "Linux":
            state_db = (
                Path.home() / ".config" / "Cursor" / "User"
                / "globalStorage" / "state.vscdb"
            )
        else:
            state_db = Path()
    else:
        state_db = db_path

    cutoff_ms = int(cutoff.timestamp() * 1000)

    if state_db.exists():
        try:
            uri = f"file:{state_db}?mode=ro"
            with closing(
                sqlite3.connect(uri, uri=True, timeout=5)
            ) as conn:
                row = conn.execute(
                    "SELECT value FROM ItemTable"
                    " WHERE key = 'composer.composerHeaders'"
                ).fetchone()
                if row:
                    data = _json.loads(row[0])
                    composers = data.get("allComposers", [])
                    for c in composers:
                        created = c.get("createdAt", 0)
                        updated = c.get("lastUpdatedAt", created)
                        if updated < cutoff_ms:
                            continue
                        ts = _parse_cursor_ts(created)
                        name = c.get("name", "") or ""
                        subtitle = c.get("subtitle", "") or ""
                        stats.sessions.append(SessionStats(
                            session_id=c.get("composerId", ""),
                            tool="Cursor",
                            model=c.get("unifiedMode", "agent"),
                            turns=1,
                            started=ts,
                            ended=_parse_cursor_ts(
                                c.get("lastUpdatedAt", created)
                            ),
                            duration_minutes=(
                                (c.get("lastUpdatedAt", created)
                                 - created) / 60000
                            ),
                            project=(name or subtitle)[:40],
                        ))
        except (sqlite3.DatabaseError, _json.JSONDecodeError):
            pass

    # Secondary: AI attribution from ai-tracking DB
    tracking_db = (
        Path.home() / ".cursor" / "ai-tracking"
        / "ai-code-tracking.db"
    )
    if db_path is not None:
        tracking_db = db_path

    if tracking_db.exists() and tracking_db != state_db:
        try:
            uri = f"file:{tracking_db}?mode=ro"
            with closing(
                sqlite3.connect(uri, uri=True, timeout=5)
            ) as conn:
                conn.row_factory = sqlite3.Row
                _cursor_attribution(conn, stats)
        except sqlite3.DatabaseError:
            pass

    stats.sessions.sort(
        key=lambda s: s.started or datetime.min.replace(
            tzinfo=timezone.utc
        ),
        reverse=True,
    )
    return stats


def _cursor_attribution(conn, stats):
    """Read AI attribution data from scored_commits."""
    try:
        rows = conn.execute(
            "SELECT commitHash, linesAdded, v1AiPercentage"
            " FROM scored_commits"
            " WHERE linesAdded > 0 AND v1AiPercentage != ''"
        ).fetchall()
    except Exception:
        return

    if not rows:
        return

    total_lines = 0
    weighted_pct = 0.0
    for row in rows:
        try:
            lines = int(row["linesAdded"])
            pct = float(row["v1AiPercentage"])
            total_lines += lines
            weighted_pct += pct * lines
        except (ValueError, TypeError):
            continue

    if total_lines > 0:
        avg_pct = weighted_pct / total_lines
        stats.tool = f"Cursor (AI: {avg_pct:.0f}%)"


def _parse_cursor_ts(ts_ms) -> datetime | None:
    if ts_ms is None:
        return None
    try:
        return datetime.fromtimestamp(
            int(ts_ms) / 1000, tz=timezone.utc
        )
    except (ValueError, TypeError, OSError):
        return None


LOCAL_PRICING = {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0}


def _estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read: int,
    cache_write: int,
) -> float:
    if _normalize_model_tier(model) == "local":
        prices = LOCAL_PRICING
    else:
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
        *[
            _format_tokens(ts.total_input) if ts.total_input else "[dim]N/A[/dim]"
            for ts in all_stats
        ],
    )
    table.add_row(
        "Output Tokens",
        *[
            _format_tokens(ts.total_output) if ts.total_output else "[dim]N/A[/dim]"
            for ts in all_stats
        ],
    )
    table.add_row(
        "Cache Read",
        *[
            _format_tokens(ts.total_cache_read) if ts.total_cache_read else "[dim]N/A[/dim]"
            for ts in all_stats
        ],
    )
    table.add_row(
        "Cache Hit Rate",
        *[
            f"{ts.cache_hit_rate:.0f}%" if ts.cache_hit_rate is not None else "[dim]N/A[/dim]"
            for ts in all_stats
        ],
    )
    table.add_row(
        "Est. Cost",
        *[
            f"${ts.total_cost:.2f}" if ts.total_cost else "[dim]N/A[/dim]"
            for ts in all_stats
        ],
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

        is_cursor = "Cursor" in ts.tool
        for s in recent:
            date = s.started.strftime("%m/%d %H:%M") if s.started else "-"
            dur = f"{s.duration_minutes:.0f}m" if s.duration_minutes else "-"
            output = (
                "[dim]--[/dim]" if is_cursor
                else _format_tokens(s.output_tokens)
            )
            cost = (
                "[dim]--[/dim]" if is_cursor
                else f"${s.cost_usd:.2f}"
            )
            table.add_row(
                date, s.model, str(s.turns),
                output, cost, dur, s.project,
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


# ── stats recommend ─────────────────────────────────────────────────


def show_recommend(period: str = "7d", tool_filter: str = "all") -> None:
    """Show what-if cost savings by shifting expensive model usage."""
    cutoff = _parse_period(period)
    all_stats = _collect_stats(cutoff, tool_filter)

    if not all_stats:
        console.print("[bold red]No session data found.[/bold red]")
        return

    # Aggregate per-tier token totals across all tools.
    tier_totals: dict[str, dict[str, int]] = {}
    for ts in all_stats:
        for s in ts.sessions:
            tier = _normalize_model_tier(s.model)
            if tier not in tier_totals:
                tier_totals[tier] = {
                    "input": 0, "output": 0,
                    "cache_read": 0, "cache_write": 0,
                    "sessions": 0,
                }
            tier_totals[tier]["input"] += s.input_tokens
            tier_totals[tier]["output"] += s.output_tokens
            tier_totals[tier]["cache_read"] += s.cache_read_tokens
            tier_totals[tier]["cache_write"] += s.cache_write_tokens
            tier_totals[tier]["sessions"] += 1

    opus = tier_totals.get("opus")
    if not opus or opus["sessions"] == 0:
        console.print(
            "[yellow]No Opus usage found -- nothing to optimize.[/yellow]"
        )
        return

    opus_prices = TIER_PRICING["opus"]
    sonnet_prices = TIER_PRICING["sonnet"]

    opus_cost = _tier_cost(opus, opus_prices)

    table = Table(title=f"What-If Savings ({period})")
    table.add_column("Scenario", min_width=38)
    table.add_column("Opus Cost", justify="right")
    table.add_column("Shifted Cost", justify="right")
    table.add_column("Saved", justify="right", style="green")

    for pct in (20, 40, 60):
        frac = pct / 100
        kept = _scale_tokens(opus, 1 - frac)
        shifted = _scale_tokens(opus, frac)
        new_cost = _tier_cost(kept, opus_prices) + _tier_cost(
            shifted, sonnet_prices
        )
        saved = opus_cost - new_cost
        table.add_row(
            f"If {pct}% of Opus turns used Sonnet instead",
            f"${opus_cost:.2f}",
            f"${new_cost:.2f}",
            f"${saved:.2f}",
        )

    console.print()
    console.print(table)
    console.print()
    console.print(
        "[dim]Savings apply to API/pay-per-token usage."
        " Flat-rate plans (Max, Team) are not affected.[/dim]"
    )
    console.print()


def _scale_tokens(
    totals: dict[str, int], fraction: float,
) -> dict[str, int]:
    """Scale token counts by a fraction."""
    return {
        k: int(v * fraction) if k != "sessions" else v
        for k, v in totals.items()
    }


def _tier_cost(totals: dict[str, int], prices: dict[str, float]) -> float:
    """Calculate cost from token totals and per-1M prices."""
    cost = (
        totals["input"] * prices["input"]
        + totals["output"] * prices["output"]
        + totals["cache_read"] * prices["cache_read"]
        + totals["cache_write"] * prices["cache_write"]
    ) / 1_000_000
    return round(cost, 4)


# ── stats context ──────────────────────────────────────────────────


def show_context(period: str = "7d", tool_filter: str = "all") -> None:
    """Show context-window usage per tool (session count, not turns)."""
    cutoff = _parse_period(period)
    all_stats = _collect_stats(cutoff, tool_filter)

    if not all_stats:
        console.print("[bold red]No session data found.[/bold red]")
        return

    table = Table(title=f"Context Usage ({period})")
    table.add_column("Tool")
    table.add_column("Sessions", justify="right")
    table.add_column("Avg Input Tokens", justify="right")
    table.add_column("Avg Output Tokens", justify="right")
    table.add_column("Est. Avg Context (tokens)", justify="right")

    for ts in all_stats:
        n_sessions = len(ts.sessions)
        if n_sessions == 0:
            continue
        avg_in = ts.total_input // n_sessions
        avg_out = ts.total_output // n_sessions
        avg_ctx = avg_in + avg_out
        table.add_row(
            ts.tool,
            str(n_sessions),
            _format_tokens(avg_in),
            _format_tokens(avg_out),
            _format_tokens(avg_ctx),
        )

    console.print()
    console.print(table)
    console.print()


# ── stats compare ──────────────────────────────────────────────────


def show_compare(period: str = "7d", tool_filter: str = "all") -> None:
    """Show plain cost-per-session comparison across model tiers."""
    cutoff = _parse_period(period)
    all_stats = _collect_stats(cutoff, tool_filter)

    if not all_stats:
        console.print("[bold red]No session data found.[/bold red]")
        return

    # Group sessions by tier.
    tier_sessions: dict[str, list[SessionStats]] = {}
    for ts in all_stats:
        for s in ts.sessions:
            tier = _normalize_model_tier(s.model)
            tier_sessions.setdefault(tier, []).append(s)

    table = Table(title=f"Cost per Session by Model Tier ({period})")
    table.add_column("Tier")
    table.add_column("Sessions", justify="right")
    table.add_column("Total Cost", justify="right")
    table.add_column("Cost / Session", justify="right")

    for tier in ("opus", "sonnet", "fable", "haiku", "other", "local"):
        sessions = tier_sessions.get(tier)
        if not sessions:
            continue
        total = sum(s.cost_usd for s in sessions)
        per = total / len(sessions) if sessions else 0
        table.add_row(
            tier.capitalize(),
            str(len(sessions)),
            f"${total:.2f}",
            f"${per:.4f}",
        )

    console.print()
    console.print(table)
    console.print(
        "\n[dim]Savings apply to API/pay-per-token usage."
        " Flat-rate plans (Max, Team) are not affected.[/dim]\n"
    )
    console.print()
