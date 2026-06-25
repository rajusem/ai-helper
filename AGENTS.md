# ai-helper

An open-source CLI + MCP server helping developers work smarter with AI coding tools.

## Project Overview

- **Target tools:** Claude Code, OpenCode, Cursor
- **Architecture:** MCP server (core) + CLI wrapper
- **Language:** Python 3.11+
- **Package manager:** uv
- **License:** Apache-2.0

## Commands

```bash
uv sync --extra dev    # install deps
uv run ai-helper       # run CLI
uv run pytest -v       # run tests
uv run ruff check src/ # lint
```

## 5 Pillars

1. `ai-helper scan` — Skill scanner (analyze skills for quality, tokens, hallucination risk)
2. `ai-helper stats` — Cross-tool usage insights and recommendations
3. `ai-helper config` — Unified model/MCP config across tools
4. `ai-helper optimize` — Smart defaults (RTK, Ponytail integration, model recommendations)
5. `ai-helper init` / `ai-helper doctor` — Developer setup and health check

## Key Design Principles

- Help, don't restrict — everything is a suggestion
- Show, don't enforce — display cost impact, let users decide
- Cross-tool by default — one tool, three AI environments
- Honest numbers — no inflated savings claims
- Local-first — all data stays on user's machine

## Project Structure

```
src/ai_helper/
├── cli.py              # CLI entry point (Click)
├── doctor.py           # Health check command
├── config.py           # Config show/set commands
├── stats.py            # Usage insights & analytics
├── optimize.py         # RTK/Ponytail integration
└── tools/              # Tool detection layer
    ├── registry.py     # detect_tools(), get_tool()
    ├── base.py         # ToolDetector base class, ToolInfo dataclass
    ├── claude_code.py  # Claude Code detection
    ├── opencode.py     # OpenCode detection
    └── cursor.py       # Cursor detection
tests/                  # Tests (pytest)
docs/                   # Design docs
docs/pillars/           # Per-pillar design docs
local-docs/             # Research & reference (gitignored, not committed)
```

## Status

- `ai-helper doctor` — working (detects all 3 tools)
- `ai-helper config show` — working (side-by-side config table)
- `ai-helper config set` — working (writes Claude Code + OpenCode configs)
- `ai-helper stats` — working (Claude Code session analytics)
- `ai-helper optimize status/install/report/discover` — working (RTK integration)
- `ai-helper scan` — working (skill file analyzer, 18 checks)
- `ai-helper init` — placeholder stub
- 10 tests passing
