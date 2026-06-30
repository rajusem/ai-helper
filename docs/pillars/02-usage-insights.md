# Pillar 2: Usage Insights & Analytics

## Commands

```bash
ai-helper stats [--period 1d|7d|30d|all] [--tool claude|opencode|cursor|all]
ai-helper stats recommend    # what-if model savings
ai-helper stats compare      # cross-tool cost per session by model tier
ai-helper stats context      # context window usage per tool
```

## Problem

Developers use multiple AI coding tools but have no unified view of their spending, token usage, or efficiency. Each tool only shows its own data.

## Approach

Cross-tool analytics with actionable recommendations. Read local session data — no proxy, no API keys, nothing leaves the machine.

### Data Sources

| Tool | Session Location | Format | What We Read |
|------|-----------------|--------|--------------|
| Claude Code | `~/.claude/projects/*/*.jsonl` | JSONL | model, tokens (input/output/cache_read/cache_write), usage, timestamps |
| OpenCode | `~/.local/share/opencode/opencode.db` | SQLite | model (JSON field), tokens, timestamps |
| Cursor | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` | SQLite | session headers from composerHeaders; tokens unreliable (98% zero) |

All data stays local. Read-only access to existing session files.

## Implemented Features

### Summary Table (`ai-helper stats`)
- Sessions, input/output tokens, cache read, **cache hit rate**, estimated cost, total time
- Per-tool breakdown (Claude Code, OpenCode, Cursor side by side)
- Recent sessions with model, turns, output, cost, duration, project
- Model usage distribution across all tools

### What-If Savings (`stats recommend`)
- "If 20/40/60% of Opus turns used Sonnet, save $X/week"
- Based on actual usage patterns, not hypothetical
- Flat-rate plan caveat included

### Cross-Tool Comparison (`stats compare`)
- Cost per session by model tier across all tools
- Opus $X/session vs Sonnet $Y/session vs Local $0.00

### Context Usage (`stats context`)
- Average input/output tokens per session per tool
- Estimated context window usage

### Cache Hit Rate
- Calculated as `cache_read / (cache_read + cache_write + input) * 100`
- Typical healthy rate: 85-94% for Claude Code
- Shows N/A for tools without cache data (Cursor)

## Cost Estimation

Uses per-model pricing from Anthropic's published rates:

| Model | Input | Output | Cache Read | Cache Write |
|-------|-------|--------|------------|-------------|
| Opus 4.5-4.8 | $15/M | $75/M | $1.50/M | $18.75/M |
| Sonnet 4.5-4.6 | $3/M | $15/M | $0.30/M | $3.75/M |
| Fable 5 | $1/M | $5/M | $0.10/M | $1.25/M |
| Haiku 4.5 | $0.80/M | $4/M | $0.08/M | $1.00/M |

## Honest Caveats

- All cost estimates are approximations based on published pricing
- Actual billing may differ — Anthropic warns against using usage fields for financial decisions
- Cursor token data is unreliable (shows "--" for output/cost, not "0")
- Flat-rate plans (Max, Team) are not affected by per-token pricing
- We present estimates clearly labeled as estimates

## Future Features

- Waste detection: sessions with high token usage but no file changes
- Budget awareness: "Team has used $500 of $1000 this month"
- Export: CSV, JSON for custom analysis
- Trend alerts: "Your daily spend has increased 3x this week"
