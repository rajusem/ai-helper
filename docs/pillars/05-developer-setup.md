# Pillar 5: Developer Setup & Onboarding

## Command

```bash
ai-helper init                     # set up AI tooling for this project
ai-helper init context             # generate project context files
ai-helper doctor                   # health check across all tools
ai-helper doctor --fix             # auto-fix common issues
```

## Problem

Setting up AI coding tools for a project involves:
1. Figuring out which tools are installed and their versions
2. Creating context files (CLAUDE.md, .cursorrules, OpenCode config) manually
3. Configuring MCP servers in each tool separately
4. Installing optimizations (RTK, plugins) per tool
5. Debugging auth, config, and version issues

Each repo in the ecosystem has its own setup instructions. New developers spend 30-60 minutes getting productive.

## Approach

**One command to get productive.** Detect installed tools, generate context files, configure MCP servers, and validate everything works.

### `ai-helper init`

```
$ ai-helper init

Detected AI tools:
  Claude Code  v1.0.52  ~/.claude/settings.json
  OpenCode     v0.8.1   ~/.config/opencode/config.toml
  Cursor       v0.48    ~/.cursor/settings.json

Detected project type:
  Language:    TypeScript (package.json)
  Framework:   Express.js
  Test runner: Jest
  Build:       tsc

Actions:
  [x] Generate CLAUDE.md (build: npm run build, test: npm test, lint: npm run lint)
  [x] Generate .cursorrules (same content, Cursor format)
  [x] Generate .opencode/config (same content, OpenCode format)
  [x] Register ai-helper MCP server in all tools
  [ ] Install RTK (optional, run: ai-helper optimize install rtk)

Done. Your AI tools are ready for this project.
```

### `ai-helper doctor`

```
$ ai-helper doctor

Claude Code
  Version:    v1.0.52 (latest)
  Auth:       authenticated (Anthropic)
  Config:     ~/.claude/settings.json (valid)
  Model:      claude-opus-4-6
  MCP:        2 servers registered
  RTK:        installed (v0.42.4), active

OpenCode
  Version:    v0.8.1 (latest)
  Auth:       authenticated (Anthropic via env)
  Config:     ~/.config/opencode/config.toml (valid)
  Model:      claude-sonnet-4-6
  RTK:        installed, active (--opencode plugin)

Cursor
  Version:    v0.48 (latest)
  Auth:       authenticated
  Config:     ~/.cursor/settings.json (valid)
  Model:      claude-sonnet-4-6
  RTK:        not installed (run: ai-helper optimize install rtk)

Issues found:
  ⚠ Claude Code uses Opus, OpenCode/Cursor use Sonnet — intentional?
     Fix: ai-helper config set --model opus (sync all tools)
  ⚠ RTK not installed for Cursor
     Fix: ai-helper optimize install rtk --tool cursor
```

## MVP Features

1. **Tool detection** — find Claude Code, OpenCode, Cursor installations and versions
2. **Project detection** — identify language, framework, build/test commands
3. **Context file generation** — create CLAUDE.md from project analysis
4. **Health check** — validate auth, config, versions, common issues
5. **Issue reporting** — clear, actionable fix suggestions

## Future Features

- **Context sync** — keep CLAUDE.md, .cursorrules, and OpenCode config in sync
- **Template library** — starter configs for common project types (Go, Python, TypeScript, Rust)
- **Plugin discovery** — suggest relevant plugins/skills based on project type
- **Team onboarding** — "Here's how we use AI tools on this team" guide generation
- **Version monitoring** — notify when tool updates are available
- **Migration assistant** — help move config from one tool to another

## Ecosystem Integration

From scanning the sibling repos, every team has custom setup:
- agentic-sdlc: Makefile install targets per tool
- ai-helpers: marketplace install via skillsaw
- issue-fix-agent: .opencode/agents/ and skills/ with manual config
- harness: .mcp.json with session-insights server

`ai-helper init` can detect these patterns and suggest appropriate setup.

## MCP Integration

As an MCP tool, setup features can be accessed during AI sessions:
- "Run a health check on my AI tools"
- "Set up this project for AI-assisted development"
- "What version of Claude Code am I running?"
