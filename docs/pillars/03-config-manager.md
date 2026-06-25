# Pillar 3: Config Manager

## Command

```bash
ai-helper config set --model opus --small-model sonnet
ai-helper config show
ai-helper config sync-mcp
ai-helper config profile [work|personal]
ai-helper config export
ai-helper config import <file>
```

## Problem

Each AI coding tool has its own config format, location, and model naming conventions. Developers who use multiple tools must manually update each one. There is no tool that manages model settings across Claude Code, OpenCode, and Cursor simultaneously.

## Approach

**One command, three tools.** Read and write config files for each target tool, translating model names and settings as needed.

### Config Locations

| Tool | Config File | Model Field | Small Model Field |
|------|------------|-------------|-------------------|
| Claude Code | `~/.claude/settings.json` | model preference | via settings |
| OpenCode | `.opencode/config.toml` or similar | `model` | `small_model` |
| Cursor | `.cursor/settings.json` or VS Code settings | model selection | model selection |

### Model Name Translation

Different tools may use different model identifiers:

| Friendly Name | Claude Code | OpenCode | Cursor |
|---------------|------------|----------|--------|
| opus | claude-opus-4-6 | claude-opus-4-6 | claude-opus-4-6 |
| sonnet | claude-sonnet-4-6 | claude-sonnet-4-6 | claude-sonnet-4-6 |
| haiku | claude-haiku-4-5 | claude-haiku-4-5 | claude-haiku-4-5 |

## MVP Features

1. **Model sync** — set primary and small model across all installed tools
2. **Config show** — display current settings from all tools side by side
3. **MCP sync** — register/update MCP servers across all tools from one config
4. **Detect installed tools** — find which of the three tools are installed and configured

## Future Features

- **Profiles** — switch between "work" (Opus, strict rules) and "personal" (Sonnet, relaxed) configs
- **Rules sync** — sync CLAUDE.md content to equivalent files in other tools (.cursorrules, OpenCode agent .md files)
- **MCP server management** — install, configure, and sync MCP servers across tools
- **Config export/import** — share team configs ("here's our standard AI tool setup")
- **Config diff** — show differences between tools ("Claude Code uses Opus, Cursor uses Sonnet")
- **Config validation** — check for common misconfigurations
- **Team config distribution** — org-level defaults that apply to all team members

## Prior Art to Investigate

- **Ruler** — unified config management for AI coding assistants (blog post found, need to evaluate)
- **chezmoi** — dotfile management approach for syncing MCP config across tools
- Neither is a direct competitor in the way we envision, but both address adjacent problems

## MCP Integration

As an MCP tool, `config` can be managed during AI sessions:
- "Switch all my tools to use Sonnet for the rest of today"
- "Show my current model configuration"
- "Set up the same MCP servers in Cursor that I have in Claude Code"
