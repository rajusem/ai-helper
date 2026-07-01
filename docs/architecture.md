# Architecture

## Design Principles

1. **Cross-tool** — one implementation serves Claude Code, OpenCode, and Cursor
2. **Local-first** — all data stays on the user's machine; no cloud dependency
3. **Composable** — each pillar works independently; use what you need
4. **Help, don't restrict** — everything is a suggestion, not a gate

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Rich ecosystem, fast development, cross-platform |
| CLI framework | Click | Mature, composable commands and groups |
| Terminal output | Rich | Tables, panels, colors, progress indicators |
| Config parsing | PyYAML | YAML config file support |
| Package manager | uv | Fast, modern Python tooling |
| License | Apache-2.0 | Permissive, enterprise-friendly |

## Data Flow

### Session Data Reading (read-only, no network)

```
Claude Code  →  ~/.claude/projects/*/*.jsonl        →  JSONL (model, tokens, cache, timestamps)
OpenCode     →  ~/.local/share/opencode/opencode.db →  SQLite (model as JSON, tokens, timestamps)
Cursor       →  state.vscdb + ai-code-tracking.db   →  SQLite (session headers, AI attribution)
                          ↓
                   ai-helper stats
                          ↓
                 Unified analytics (cross-tool summary, cache hit rate, cost estimates)
```

### Config Management

```
ai-helper config set --model sonnet --small-model haiku
                          ↓
         ┌────────────────┼────────────────┐
         ↓                ↓                ↓
  Claude Code         OpenCode          Cursor
  ~/.claude/          ~/.config/        (UI only —
  settings.json       opencode/         shows instruction)
                      opencode.json
```

### Skill File Scanning

```
ai-helper scan [path|URL]
      ↓
  Discover files (CLAUDE.md, AGENTS.md, .cursorrules, agents/*.md, skills/*/SKILL.md)
      ↓
  Analyze each file (33 rules across 7 categories)
      ↓
  Score 0-100 with actionable fix suggestions
      ↓
  Output: table (human), JSON (programmatic), SARIF (CI/CD)
```

## Tool Integration Points

### Claude Code
- **Config**: `~/.claude/settings.json` (global)
- **Sessions**: `~/.claude/projects/*/*.jsonl`
- **Context files**: CLAUDE.md, AGENTS.md at project root; `.claude/skills/`, `.claude/agents/`
- **RTK hooks**: PreToolUse in settings.json

### OpenCode
- **Config**: `~/.config/opencode/opencode.json`
- **Sessions**: `~/.local/share/opencode/opencode.db` (SQLite, XDG data dir)
- **Binary**: `~/.opencode/bin/opencode` (not in PATH by default)
- **Context files**: `.opencode/agents/*.md`, `.opencode/skills/*/SKILL.md`

### Cursor
- **Config**: `~/Library/Application Support/Cursor/User/settings.json` (macOS)
- **Sessions**: `state.vscdb` (composerHeaders in ItemTable)
- **AI tracking**: `~/.cursor/ai-tracking/ai-code-tracking.db`
- **Context files**: `.cursorrules`
- **Limitation**: No local token/cost data (tokens show N/A)

## Directory Structure

```
ai-helper/
├── src/ai_helper/
│   ├── cli.py              # CLI entry point (Click commands and groups)
│   ├── scan.py             # Skill file scanner (33 rules, SARIF, baseline/diff)
│   ├── stats.py            # Usage analytics (JSONL + SQLite readers, cost estimation)
│   ├── config.py           # Config manager (read/write across tools, validation)
│   ├── optimize.py         # RTK/Ponytail/Headroom integration
│   ├── doctor.py           # Health check (tool detection, issue reporting)
│   └── tools/              # Tool detection layer
│       ├── base.py         # ToolDetector base class, ToolInfo dataclass
│       ├── registry.py     # detect_tools(), get_tool()
│       ├── claude_code.py  # Claude Code detection
│       ├── opencode.py     # OpenCode detection
│       └── cursor.py       # Cursor detection
├── tests/                  # 232 tests (pytest)
├── docs/                   # Design docs (public)
├── local-docs/             # Research & reference (gitignored)
├── .githooks/              # Pre-commit secret detection
├── CONTRIBUTING.md         # Contributor guide
├── AGENTS.md               # Project context (CLAUDE.md symlinks here)
├── pyproject.toml          # Python 3.11+, deps: click, pyyaml, rich
└── Makefile                # install, test, lint, scan, doctor, stats targets
```
