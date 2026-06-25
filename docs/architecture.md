# Architecture

## Design Principles

1. **MCP-first** — core logic lives in an MCP server; CLI wraps it for terminal use
2. **Cross-tool** — one implementation serves Claude Code, OpenCode, and Cursor
3. **Local-first** — all data stays on the user's machine; no cloud dependency
4. **Composable** — each pillar works independently; use what you need

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                    ai-helper                         │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │   CLI    │  │MCP Server│  │  Tool Plugins    │   │
│  │ (direct  │  │ (stdio/  │  │                  │   │
│  │  usage)  │  │  SSE)    │  │ ┌──────────────┐ │   │
│  └────┬─────┘  └────┬─────┘  │ │ Claude Code  │ │   │
│       │              │        │ │ (skill/hook) │ │   │
│       │              │        │ ├──────────────┤ │   │
│       ▼              ▼        │ │  OpenCode    │ │   │
│  ┌──────────────────────┐     │ │ (TS plugin)  │ │   │
│  │      Core Engine     │     │ ├──────────────┤ │   │
│  │                      │     │ │   Cursor     │ │   │
│  │ ┌──────┐ ┌────────┐  │     │ │  (rules)    │ │   │
│  │ │ Scan │ │ Stats  │  │     │ └──────────────┘ │   │
│  │ ├──────┤ ├────────┤  │     └──────────────────┘   │
│  │ │Config│ │Optimize│  │                            │
│  │ ├──────┤ ├────────┤  │                            │
│  │ │ Init │ │ Doctor │  │                            │
│  │ └──────┘ └────────┘  │                            │
│  └──────────────────────┘                            │
└─────────────────────────────────────────────────────┘
```

## Why MCP-First

All three target tools support MCP (Model Context Protocol):

| Tool | MCP Transport | Config Location |
|------|--------------|-----------------|
| Claude Code | stdio | `.claude/settings.json` → `mcpServers` |
| OpenCode | stdio | `.opencode/config.toml` or similar |
| Cursor | stdio | `.cursor/mcp.json` |

Building as an MCP server means:
- One implementation, three tools get access
- Tools can call ai-helper capabilities during AI sessions
- No wrapper/proxy overhead — direct integration
- CLI provides the same features for standalone use

## Data Flow

### Session Data Reading

```
Claude Code  →  ~/.claude/projects/*/sessions/  →  JSONL files
OpenCode     →  ~/.opencode/sessions/            →  (format TBD)
Cursor       →  ~/.cursor/                       →  SQLite database
                          ↓
                   ai-helper stats
                          ↓
                 Unified analytics
```

### Config Management

```
ai-helper config set --model opus --small-model sonnet
                          ↓
         ┌────────────────┼────────────────┐
         ↓                ↓                ↓
  Claude Code         OpenCode          Cursor
  settings.json       config.toml     .cursor/settings
  model: opus         model: opus      model: opus
  small: sonnet       small: sonnet    small: sonnet
```

### Security Scanning

```
ai-helper scan
      ↓
  ┌───┼───┐
  ↓   ↓   ↓
Trivy Grype OSV    ← deterministic scanners (parallel)
  ↓   ↓   ↓
  └───┼───┘
      ↓
  Dedup & merge
      ↓
  LLM triage       ← AI prioritization & fix suggestions
      ↓
  Unified report
```

## Tool Integration Points

### Claude Code
- **Plugin**: skills (ai-helper commands), hooks (post-session tracking), MCP server
- **Config**: `~/.claude/settings.json` (global), `.claude/settings.json` (project)
- **Sessions**: `~/.claude/projects/*/sessions/*.jsonl`
- **Reference**: https://code.claude.com/docs/en/plugins-reference

### OpenCode
- **Plugin**: JS/TS modules hooking into events (`tool.execute.before`, etc.)
- **Config**: `.opencode/config.toml` or similar
- **Sessions**: format to be investigated
- **Reference**: https://opencode.ai/docs/plugins/

### Cursor
- **Plugin**: Rules, MCP servers, Commands
- **Config**: `.cursor/` directory, VS Code settings inheritance
- **Sessions**: SQLite database
- **Reference**: https://cursor.com/docs/reference/plugins

## Tech Stack (Proposed)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | TypeScript | Ecosystem alignment (MCP SDK, all three tools use JS/TS plugins) |
| Runtime | Node.js 20+ | Stable, cross-platform, familiar to target audience |
| MCP SDK | `@modelcontextprotocol/sdk` | Official MCP TypeScript SDK |
| CLI framework | Commander.js or oclif | Mature, well-documented |
| Security scanners | Trivy, Grype (shelled out) | Industry standard, no wrapper needed |
| Pricing data | LiteLLM pricing DB | 2200+ models, community maintained |
| Package manager | npm | Widest reach for installation |

## Directory Structure (Planned)

```
ai-helper/
├── src/
│   ├── core/               # Shared logic
│   │   ├── scanner/        # Security scanner orchestrator
│   │   ├── stats/          # Usage analytics engine
│   │   ├── config/         # Config manager
│   │   ├── optimize/       # Smart defaults & RTK/Ponytail integration
│   │   └── setup/          # Init & doctor
│   ├── mcp/                # MCP server entry point
│   ├── cli/                # CLI entry point
│   └── plugins/            # Tool-specific plugins
│       ├── claude-code/    # Claude Code plugin package
│       ├── opencode/       # OpenCode plugin package
│       └── cursor/         # Cursor rules/config
├── docs/
│   ├── architecture.md     # This file
│   └── pillars/            # Per-pillar design docs
├── tests/
├── package.json
├── tsconfig.json
└── README.md
```
