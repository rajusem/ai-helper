# Contributing to ai-helper

Thanks for your interest in contributing! ai-helper is a CLI for developers
who use multiple AI coding tools (Claude Code, OpenCode, Cursor) and want
unified insights across all of them.

## Getting Started

1. Read the [README](README.md) for project overview
2. Read [AGENTS.md](AGENTS.md) for project structure and commands

```bash
# Clone and install
git clone https://github.com/rajusem/ai-helper.git
cd ai-helper
uv sync --extra dev

# Verify setup
uv run ai-helper doctor

# Run tests
uv run pytest -v

# Lint
uv run ruff check src/ tests/
```

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
docs/                   # Design docs (public)
local-docs/             # Research & reference (gitignored)
```

## Development Workflow

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- At least one AI coding tool installed (Claude Code, OpenCode, or Cursor)

### Running Locally

```bash
# Project-local install (for development)
uv sync --extra dev

# Global install (use from any directory)
uv tool install -e . --force

# After code changes, re-run global install to update the binary
make install-global
```

### Git Hooks

Set up the pre-commit hook for secret detection:

```bash
git config core.hooksPath .githooks
```

This blocks commits containing secrets, API keys, private keys, or large
binary files.

## What to Contribute

### Tool Detection

Tool detectors are in `src/ai_helper/tools/`. Each follows the `ToolDetector`
base class pattern. To add a new tool:

1. Create a new detector file in `tools/`
2. Register it in `tools/registry.py`
3. Add tests

### Stats / Cost Estimation

Stats reads local session data (JSONL for Claude Code, SQLite for OpenCode
and Cursor). Pricing is maintained in the `PRICING` dict in `stats.py`.
When models are released, update pricing there.

## Code Standards

### Python

- Type hints on all functions
- Follow existing patterns in the codebase
- No comments unless the WHY is non-obvious
- Run `uv run ruff check src/ tests/` before committing

### Tests

- All new features need tests
- Test both the positive case (rule fires) and negative case (rule doesn't fire on valid input)
- Use `tmp_path` fixture for file-based tests
- Follow existing test class naming: `TestRuleName`, `TestFeatureName`

### Commits

```bash
# Format: descriptive message with Signed-off-by
git commit -s -m "Fix BPRAC003 false positives on linear sequential steps"
```

- Always sign off with `-s` flag
- Message should describe what changed and why
- One logical change per commit

### What NOT to Commit

- `.env` files or API keys
- `local-docs/` (gitignored research notes)
- `__pycache__/` or `*.pyc`
- Large binary files (blocked by pre-commit hook)
- Session data or user-specific paths

## Design Principles

1. **Help, don't restrict** — everything is a suggestion, not a gate
2. **Show, don't enforce** — display cost impact, let users decide
3. **Cross-tool by default** — features should work across Claude Code, OpenCode, and Cursor
4. **Honest numbers** — no inflated savings claims; measure and report real data
5. **Local-first** — all data stays on the user's machine

## Review Process

Before submitting changes:

- [ ] Tests pass (`uv run pytest -v`)
- [ ] Lint clean (`uv run ruff check src/ tests/`)
- [ ] No secrets in committed files
- [ ] Docs updated if behavior changed

For significant changes (new pillars, architecture changes, new tool support):
validate with architecture, PE, and AI expert review before merging.

## Questions?

- Project overview: See [README.md](README.md)
- Design docs: See `docs/pillars/`
- Research notes: See `local-docs/` (gitignored, available locally after clone)
