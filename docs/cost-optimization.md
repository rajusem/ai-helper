# Cost Optimization Guide

Techniques ranked by real-world impact for Claude Code, OpenCode, and Cursor.

## Impact Ranking

| Rank | Technique | Savings | How |
|------|-----------|---------|-----|
| 1 | Prompt caching (don't break it) | 84-90% of input costs | Automatic in Claude Code. Avoid mid-session model switches, keep CLAUDE.md stable during sessions |
| 2 | Model routing | 60-77% | Use `opusplan` alias or `ai-helper config set --model sonnet` for routine tasks |
| 3 | Lean context files | Reduces base cost | Keep CLAUDE.md under 200 lines, move specialized instructions into on-demand skills |
| 4 | Fresh sessions per task | Prevents rework waste | New session per task, `--continue` only for closely related follow-up |
| 5 | Token compression tools | 0.5-3% of bill | RTK/Headroom — modest dollar impact, useful for token-capped plans |

## Prompt Caching

Cached tokens cost **0.1x** the base input price (90% discount). Claude Code handles caching automatically.

**What breaks the cache:**
- Switching models mid-session (`/model`) — full cache invalidation
- Editing CLAUDE.md during a session
- Adding/removing MCP tools mid-session

**What preserves it:**
- Staying on one model per session
- Editing CLAUDE.md between sessions, not during
- Using deferred tool loading (default)

## Model Routing

| Model | Best for | Input / Output per MTok |
|-------|---------|-------------------------|
| Opus | Complex architecture, hard bugs | $15 / $75 |
| Sonnet | Most coding, reviews, implementation | $3 / $15 |
| Haiku | Simple lookups, formatting | $0.80 / $4 |

The `opusplan` alias routes Opus for planning, Sonnet for execution automatically.

## Visibility

```bash
ai-helper stats                  # cache hit rate, cost per session
ai-helper stats recommend        # what-if model savings
ai-helper stats compare          # cross-tool cost comparison
ai-helper optimize status        # RTK/Ponytail/Headroom status
skill-lint . --report            # context file token costs (separate tool: pip install ai-skill-lint)
```
