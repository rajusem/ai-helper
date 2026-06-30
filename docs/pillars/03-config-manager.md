# Pillar 3: Config Manager

## Commands

```bash
ai-helper config show                                    # side-by-side view
ai-helper config set --model opus --small-model sonnet   # set across all tools
ai-helper config set --model sonnet --tool opencode      # target one tool
```

## Problem

Each AI coding tool has its own config format, location, and model naming conventions. Developers who use multiple tools must manually update each one.

## Approach

One command, three tools. Read and write config files for each target tool, translating model names and settings as needed.

### Config Locations

| Tool | Config File | Model Field | Small Model Field |
|------|------------|-------------|-------------------|
| Claude Code | `~/.claude/settings.json` | model preference | via settings |
| OpenCode | `~/.config/opencode/config.json` | `model` | `small_model` |
| Cursor | UI only (no CLI config write) | model selection | model selection |

Cursor config is read-only — `config set` shows a UI instruction instead of writing files.

### Model Aliases

| Alias | Resolves to |
|-------|-------------|
| opus | claude-opus-4-6 |
| sonnet | claude-sonnet-4-6 |
| haiku | claude-haiku-4-5 |
| fable | claude-fable-5 |

### Model Validation

- Checks provider prefix, model name, and version format
- Version must be `default`, `latest`, or a date string (8-10 digits)
- Prompts for confirmation on validation warnings
- Atomic config writes (tempfile + os.replace)

## Implemented Features

1. **`config show`** — side-by-side display of model settings from all installed tools
2. **`config set`** — set primary and small model across all installed tools (or target one tool with `--tool`)
3. **Model alias resolution** — `opus`, `sonnet`, `haiku`, `fable` resolve to full model IDs
4. **Validation** — rejects typos and invalid model formats before writing

## Future Features

- MCP server sync across tools
- Config profiles (work/personal)
- Config export/import for team sharing
- Rules sync (CLAUDE.md content to .cursorrules)
