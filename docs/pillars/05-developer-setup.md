# Pillar 5: Developer Setup & Health Check

## Commands

```bash
ai-helper doctor                   # health check across all tools
ai-helper init                     # planned — project setup wizard
```

## Problem

Developers use multiple AI coding tools but have no unified view of what's installed, configured, and healthy. Checking each tool separately is tedious and error-prone.

## Approach

One command to see all your AI tools in one place. Detect installations, show versions, model config, MCP servers, and flag mismatches.

## Implemented: `ai-helper doctor`

Detects Claude Code, OpenCode, and Cursor. Shows:

- **Installation status** — installed or not, path
- **Version** — current version
- **Model** — configured model (and small_model for OpenCode)
- **MCP servers** — count of configured MCP servers
- **RTK status** — whether RTK hooks are active
- **Context files** — CLAUDE.md, AGENTS.md presence
- **Issues** — model mismatches across tools, missing config

### Tool Detection

| Tool | Detection Method |
|------|-----------------|
| Claude Code | `which claude`, checks `~/.claude/settings.json` |
| OpenCode | `which opencode` + known paths (`~/.opencode/bin/opencode`), checks `~/.config/opencode/config.json` |
| Cursor | macOS app detection (`/Applications/Cursor.app`), checks MCP config and state.vscdb |

### Example Output

```
$ ai-helper doctor

Claude Code
  Version:    v1.0.52
  Model:      claude-opus-4-6
  MCP:        2 servers
  RTK:        active
  Context:    AGENTS.md (symlink from CLAUDE.md)

OpenCode
  Version:    v1.17.11
  Model:      claude-sonnet-4-6
  Small:      claude-haiku-4-5

Cursor
  Installed:  /Applications/Cursor.app
  MCP:        1 server

Issues:
  ! Claude Code uses opus, OpenCode uses sonnet — intentional?
```

## Planned: `ai-helper init`

Project setup wizard (not yet implemented):
- Detect project type (language, framework, build/test commands)
- Generate context files (CLAUDE.md, .cursorrules) from project analysis
- Register MCP servers across tools
- Suggest optimizations

## Future Features

- `doctor --fix` — auto-fix common issues
- Context file generation from project analysis
- Template library for common project types
- Version monitoring for tool updates
