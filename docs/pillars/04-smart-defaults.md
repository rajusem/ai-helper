# Pillar 4: Smart Defaults & Optimization

## Commands

```bash
ai-helper optimize status           # show what's installed and active
ai-helper optimize install rtk      # install RTK for detected tools
ai-helper optimize install ponytail # show Ponytail install instructions
ai-helper optimize report           # show RTK token savings (wraps rtk gain)
ai-helper optimize discover         # find missed optimization opportunities (wraps rtk discover)
```

## Problem

Developers overspend on AI tool usage because:
1. Tool output (git, find, ls) is verbose — agents read thousands of tokens of noise
2. Code generation is unconstrained — agents write more code than needed
3. No visibility into what could be optimized

## Approach

Show, don't enforce. Everything is opt-in. We surface third-party optimization tools with honest assessments of their impact, and recommend built-in optimizations (model routing, prompt caching) that have the biggest real-world impact.

## Optimization Tools

### RTK — Input Token Compression

[RTK](https://github.com/rtk-ai/rtk) (67k stars, Apache-2.0) is a Rust CLI proxy that intercepts Bash tool calls and compresses output before the LLM sees it.

```bash
ai-helper optimize install rtk
# Runs: rtk init -g (Claude Code), rtk init --opencode (OpenCode), rtk init --agent cursor (Cursor)
```

**Honest assessment:** RTK compresses Bash tool output (ANSI codes, progress bars, passing test lines). Per-command savings are real (grep 30%, gh pr diff 38%, cargo test 98%). However, RTK only intercepts Bash calls — Claude Code built-in tools (Read, Grep, Glob) bypass hooks entirely. An independent evaluation (CodePointer, 500 sessions, 614M tokens) found token compression tools save **0.5-3% of the actual bill** because 78% of tool output bypasses the hook and 71% of the bill is cache-create + output tokens.

### Ponytail — Behavioral Minimalism

[Ponytail](https://github.com/DietrichGebert/ponytail) (66.5k stars, MIT) injects a minimalism ruleset into AI coding agents.

```bash
ai-helper optimize install ponytail
# Shows install instructions per tool (plugin marketplace for Claude Code, JSON config for OpenCode)
```

**Honest assessment:** Behavioral approach — constrains agents to write less code. First-party benchmark shows ~20% cost reduction, but claims of 54% LOC reduction did not survive adversarial verification (n=4, single model). A simpler YAGNI one-liner prompt achieves comparable savings per Ponytail's own benchmark.

### Headroom — Full-Stack Context Compression

[Headroom](https://github.com/chopratejas/headroom) (53.6k stars, Apache-2.0) is a Python proxy that compresses everything the agent reads via content-aware compressors.

Detected in `optimize status` if installed. Not auto-installed due to heavier footprint (Python 3.10+, proxy process).

## Real-World Cost Impact

Based on deep research (103 agents, 21 sources, adversarially verified):

| Technique | Real Savings | Source |
|-----------|-------------|--------|
| Prompt caching (built-in, don't break it) | 84-90% of input costs | Verified from real sessions |
| Model routing (opusplan, Opus→Sonnet) | 60-77% | Published pricing |
| Lean CLAUDE.md + on-demand skills | Reduces base context cost | Anthropic recommendation |
| Token compression tools (RTK/Headroom) | 0.5-3% of bill | Independent evaluation (CodePointer) |

The biggest savings come from built-in features (prompt caching, model routing), not third-party tools.

## Status Output

```
$ ai-helper optimize status

RTK  installed (rtk 0.42.4)
  v Claude Code: active
  v OpenCode: active
  v Cursor: active
Ponytail  found (~/.claude/plugins/ponytail)
Headroom  not installed

Tip: These tools compress tokens (0.5-3% bill savings). For bigger
impact, use model routing (ai-helper config set --model sonnet) and
keep CLAUDE.md lean.
```

## Future Features

- Model recommendation engine based on usage patterns from stats
- Context window hygiene tips
- Session management suggestions

## Reference

- [Cost Optimization Guide](../cost-optimization.md) — validated techniques ranked by real-world impact
