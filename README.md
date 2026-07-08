# ai-helper

Your toolkit for working smarter with AI coding tools.

A CLI for developers who use multiple AI coding tools and want a unified view of usage, configuration, and skill quality.

## What ai-helper adds

A few things that aren't available built-in:

- **Cross-tool view** — see Claude Code, OpenCode, and Cursor stats side by side (each tool only shows its own)
- **Cost in dollars** — built-in stats show tokens; ai-helper estimates cost per session and model tier
- **Skill file scanner** — no built-in linter for SKILL.md, CLAUDE.md, .cursorrules files
- **Cross-tool config sync** — set models across all tools with one command instead of editing 3 config files

## Quick Start

```bash
# Install
git clone https://github.com/rajusem/ai-helper.git
cd ai-helper
uv sync --extra dev
uv tool install -e . --force   # global install

# Health check — see what's installed and configured
ai-helper doctor

# Compare config across your tools
ai-helper config show

# Set models across all tools at once
ai-helper config set --model sonnet --small-model haiku
```

## Target Tools

| Tool | Integration | Status |
|------|------------|--------|
| [Claude Code](https://claude.ai/code) | Plugin + MCP server | Detecting, config read/write |
| [OpenCode](https://opencode.ai) | Plugin + MCP server | Detecting, config read/write |
| [Cursor](https://cursor.com) | Rules + MCP server | Detecting, config read-only |

## Pillars

### 1. Skill Scanner (`ai-helper scan`)

Analyze AI skill files (SKILL.md, CLAUDE.md, agent.md, .cursorrules) for common issues.

```bash
ai-helper scan                          # Scan current project
ai-helper scan /path/to/project         # Scan a local directory
ai-helper scan https://github.com/org/repo  # Scan a GitHub repo by URL
ai-helper scan . -v                     # Verbose — show all issues per file
ai-helper scan --format sarif           # SARIF output for CI
ai-helper scan --fail-on warning        # Exit 1 on warnings (CI gate)
ai-helper scan --save-baseline          # Save current findings
ai-helper scan --diff                   # Show only new issues since baseline
```

35+ rules across 8 categories: token cost, description quality, hallucination risk, framing, output quality, structure, best practices. Each file scored 0-100.

[Design doc](docs/pillars/01-skill-scanner.md)

### 2. Usage Insights (`ai-helper stats`)

Cross-tool usage stats.

```bash
# Last 7 days summary
ai-helper stats

# Last 24 hours
ai-helper stats --period 1d

# Last 30 days
ai-helper stats --period 30d

# All time
ai-helper stats --period all
```

- **Cross-tool stats** — Claude Code (JSONL), OpenCode (SQLite), Cursor (SQLite) side by side
- Per-session breakdown: model, turns, tokens, estimated cost, duration, project
- Model usage distribution across all tools (21+ models including local Ollama)
- Cost estimation using published model pricing (with honest caveat)

```bash
# What-if model savings
ai-helper stats recommend
# → "If 40% of Opus turns used Sonnet, save $1,006/week"

# Cross-tool cost comparison by model tier
ai-helper stats compare
# → Opus $3.39/session vs Sonnet $0.44 vs Local $0.00

# Context file cost impact
ai-helper stats context
```

[Design doc](docs/pillars/02-usage-insights.md)

### 3. Config Manager (`ai-helper config`)

Set models across Claude Code, OpenCode, and Cursor from one command.

```bash
ai-helper config show                                    # Side-by-side view
ai-helper config set --model opus --small-model sonnet   # Set across all tools
ai-helper config set --model sonnet --tool opencode      # Target one tool
```

Model aliases (`opus`, `sonnet`, `haiku`) resolve to full IDs. Validates model names before writing.

[Design doc](docs/pillars/03-config-manager.md)

### 4. Smart Defaults (`ai-helper optimize`)

Convenience wrappers for RTK setup and reporting across tools.

```bash
ai-helper optimize status          # RTK/Ponytail status per tool
ai-helper optimize install rtk     # Install RTK for Claude Code + OpenCode
ai-helper optimize report          # Token savings (wraps rtk gain)
ai-helper optimize discover        # Missed opportunities (wraps rtk discover)
```

[Design doc](docs/pillars/04-smart-defaults.md)

### 5. Developer Setup (`ai-helper doctor`)

See all your AI tools in one place.

```bash
ai-helper doctor
```

Detects Claude Code, OpenCode, and Cursor. Shows version, model, MCP servers, RTK status. Flags mismatches.

[Design doc](docs/pillars/05-developer-setup.md)

## Philosophy

1. **Help, don't restrict** — every feature is a suggestion, not a gate
2. **Show, don't enforce** — display cost impact and let users decide
3. **Opt-in everything** — nothing changes without explicit user action
4. **Cross-tool by default** — one tool, three AI coding environments
5. **Honest numbers** — no inflated savings claims; measure and report real data

## Architecture

Python CLI (Click + Rich). Reads local session files and config — no proxy, no API keys, nothing leaves your machine.

[Architecture doc](docs/architecture.md)

## Development

```bash
# Clone and install
git clone https://github.com/rajusem/ai-helper.git
cd ai-helper
uv sync --extra dev

# Run
uv run ai-helper --help
uv run ai-helper doctor
uv run ai-helper config show

# Test
uv run pytest -v

# Lint
uv run ruff check src/
```

## Status

| Pillar | Status |
|--------|--------|
| 1. Skill Scanner | 35+ rules, SARIF, baseline/diff, config file, custom rules, CI exit codes |
| 2. Usage Insights | Cross-tool stats (Claude Code + OpenCode + Cursor), cost estimation, model recommendations, what-if savings, cross-tool comparison |
| 3. Config Manager | Cross-tool model config with aliases and validation |
| 4. Smart Defaults | RTK integration, model recommendations, context calculator |
| 5. Developer Setup | `doctor` working, `init` planned |

283 tests passing. Works with Claude Code, OpenCode, and Cursor.

## License

[Apache-2.0](LICENSE)
