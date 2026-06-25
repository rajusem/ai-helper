# Pillar 4: Smart Defaults & Optimization

## Command

```bash
ai-helper optimize install          # install optimization tools (RTK, Ponytail)
ai-helper optimize status           # show what's active
ai-helper optimize report           # show measured savings
ai-helper optimize discover         # find missed optimization opportunities
ai-helper optimize recommend        # suggest optimizations based on usage patterns
```

## Problem

Developers overspend on AI tool usage because:
1. Tool output (git, find, ls) is verbose — agents read thousands of tokens of noise
2. Code generation is unconstrained — agents write more code than needed
3. Model selection is manual — developers default to the most expensive model
4. No visibility into what could be optimized

## Approach

**Show, don't enforce.** Everything is opt-in. We recommend optimizations, show their impact, and let users decide. No restrictions, no mandatory constraints.

### Design Principles

- Every optimization is a **suggestion**, not a mandate
- Show the **cost impact** of choices, let the user decide
- `--strict` mode available for teams that want enforcement, but default is advisory
- Like ESLint `--fix`: auto-fix what's safe, warn about the rest
- Users can **override anytime** — nothing is locked

## Optimization Layers

### Layer 1: Input Compression (RTK)

[RTK](https://github.com/rtk-ai/rtk) (66k stars, Apache-2.0) compresses tool output before your AI reads it.

```bash
ai-helper optimize install rtk
# Runs: rtk init -g (Claude Code) / rtk init --opencode (OpenCode)
# Cursor: investigate integration path
```

**Honest assessment:** RTK claims significant savings on git/find/ls commands. The user's local tests showed 49-91% reduction on various commands. However, RTK's official benchmarks page shows "No benchmark data yet" — their README figures are self-described as estimates. We present savings as "measured on your machine" via `rtk gain`, not as guaranteed percentages.

### Layer 2: Code Generation Defaults (Ponytail)

[Ponytail](https://github.com/DietrichGebert/ponytail) (57.4k stars, MIT) provides a priority ladder for AI code generation.

```bash
ai-helper optimize install ponytail
# Installs as a global skill/rule for each tool
```

**Honest assessment:** Official agentic benchmark shows -20% cost, -22% tokens, -54% LOC (Haiku 4.5, n=4). Our earlier estimates of 25-43% were from local tests, not published benchmarks. Issue #121 shows costs can *increase by 55%* in Cursor completion-forced scenarios. We recommend Ponytail for agentic CLI workflows (Claude Code, OpenCode) and warn about IDE completion workflows (Cursor).

### Layer 3: Model Recommendations

Based on usage patterns from Pillar 2 (Stats), suggest model routing:

```
ai-helper optimize recommend

Recommendations based on your last 30 days:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. You used Opus for 12 investigation sessions.
   → Sonnet often matches Opus quality for investigation tasks.
   → Estimated savings: ~$15/month if you switch.
   → Try it: ai-helper config set --model sonnet (revert anytime)

2. You ran 45 quick file lookups on Opus.
   → Haiku handles simple lookups well at 95% less cost.
   → Estimated savings: ~$8/month.
```

## MVP Features

1. **`optimize install`** — one-command setup for RTK across installed tools
2. **`optimize status`** — show which optimizations are active
3. **`optimize report`** — show measured savings (wraps `rtk gain`)
4. **`optimize discover`** — find missed opportunities (wraps `rtk discover`)

## Future Features

- Ponytail installation as a global skill
- Model recommendation engine based on usage patterns
- Context window hygiene tips ("Your CLAUDE.md is 5K tokens — here's how to trim it")
- Session management suggestions ("/compact at 250K tokens, not 500K")
- Prompt optimization tips based on observed patterns
- Team-level optimization policies

## Competitors

No direct competitor combines optimization tooling with usage tracking and config management. RTK and Ponytail are standalone tools — ai-helper wraps them for easier setup and unified reporting.

## MCP Integration

As an MCP tool, optimization features can be accessed during AI sessions:
- "How much has RTK saved me today?"
- "Install RTK for this project"
- "What optimizations am I missing?"
