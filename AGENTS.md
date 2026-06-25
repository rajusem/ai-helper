# ai-helper

An open-source CLI + MCP server helping developers work smarter with AI coding tools.

## Project Overview

- **Target tools:** Claude Code, OpenCode, Cursor
- **Architecture:** MCP server (core) + CLI wrapper
- **Language:** TypeScript (planned)
- **License:** Apache-2.0

## 5 Pillars

1. `ai-helper scan` — Security scanner orchestrator (Trivy/Grype + AI triage)
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
docs/                 # Design docs
docs/architecture.md  # Architecture overview
docs/pillars/         # Per-pillar design docs
local-docs/           # Research & reference (gitignored, not committed)
```

## Status

Early design phase. No code yet — docs and architecture only.
