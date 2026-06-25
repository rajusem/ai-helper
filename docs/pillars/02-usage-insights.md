# Pillar 2: Usage Insights & Analytics

## Command

```bash
ai-helper stats [--period 7d|30d|all] [--tool claude|opencode|cursor|all] [--format table|json]
ai-helper stats compare    # cross-tool comparison
ai-helper stats recommend  # model/tool recommendations
```

## Problem

Developers use multiple AI coding tools but have no unified view of their spending, token usage, or efficiency. Existing trackers (CodeBurn, Tokscale, TokenTracker) count tokens but don't provide actionable recommendations or cross-tool comparisons.

## Approach

**Insights, not just tracking.** Don't compete with CodeBurn on dashboard prettiness. Differentiate with:
1. Cross-tool comparison (Claude Code vs OpenCode vs Cursor for the same type of work)
2. Actionable recommendations ("Switch to Sonnet for investigations to save ~$X/week")
3. Team awareness (who's spending what, where)

### Data Sources

| Tool | Session Location | Format |
|------|-----------------|--------|
| Claude Code | `~/.claude/projects/*/sessions/` | JSONL |
| OpenCode | TBD — investigate session storage | TBD |
| Cursor | `~/.cursor/` | SQLite |

All data stays local. Read-only access to existing session files — no proxy, no wrapper.

## MVP Features

1. **Cross-tool summary** — total tokens, cost estimate, time across all three tools
2. **Per-session breakdown** — model used, tokens in/out, estimated cost, duration
3. **Period comparison** — "This week vs last week" trends
4. **Model usage distribution** — how much Opus vs Sonnet vs Haiku
5. **Cost estimation** — using LiteLLM pricing data (with honest caveat that estimates may drift)

## Future Features

- **Cross-tool comparison**: "You spent $12 on Claude Code and $8 on Cursor for similar tasks"
- **Model recommendations**: "Based on your patterns, switching routine tasks to Sonnet saves ~40%"
- **Waste detection**: sessions with high token usage but no file changes
- **Team dashboards**: aggregate usage across team members
- **Budget awareness**: "Team has used $500 of $1000 this month"
- **Cost allocation**: group spending by project, team, or task type
- **Export**: CSV, JSON for custom analysis
- **Trend alerts**: "Your daily spend has increased 3x this week"

## Competitors

| Tool | Stars | Strength | Gap |
|------|-------|----------|-----|
| CodeBurn | 8.3k | 31 tools, waste optimization, yield tracking | No recommendations, no cross-tool comparison |
| Tokscale | 3.9k | 37 tools, Rust core, fast | Tracking only, no insights |
| TokenTracker | 767 | Native desktop apps, rate limits | No recommendations |
| Tokdash | 22 | Lightweight | Limited tools |

**Differentiation:** ai-helper stats provides *recommendations*, not just numbers. And it's part of a larger toolkit — insights feed into config decisions ("you should use Sonnet more") and optimization suggestions ("install RTK to save on tool output").

## Honest Caveats

- All cost estimates are approximations based on LiteLLM pricing data
- Actual billing may differ from estimates
- Anthropic warns: "Do not bill end users or trigger financial decisions from these fields"
- We present estimates clearly labeled as estimates

## MCP Integration

As an MCP tool, `stats` can be queried during AI sessions:
- "How much have I spent today?"
- "What model am I using most?"
- "Compare my Claude Code vs Cursor usage this week"
