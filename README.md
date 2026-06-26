# ai-helper

Your toolkit for working smarter with AI coding tools.

**Scan for vulnerabilities. See what you spend. Configure your tools. Optimize your workflow.**

ai-helper is an open-source CLI and MCP server that helps developers get more out of AI coding tools — without restricting how they use them. Everything is a suggestion, never a mandate.

## Quick Start

```bash
# Install
pip install ai-helper   # or: uv pip install ai-helper

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

### 1. Skill Scanner (`ai-helper scan`) — Implemented

Analyze your AI skill files for quality, token efficiency, and hallucination risks.

```bash
# Scan current project
ai-helper scan

# Scan another project
ai-helper scan /path/to/project

# JSON output
ai-helper scan --format json

# Filter by severity
ai-helper scan --severity warning
```

- **Token cost analysis** — flags oversized skills that waste tokens on every turn
- **Description quality** — catches workflow summaries in description fields (agents follow descriptions instead of reading skill bodies)
- **Hallucination risk** — detects vague instructions, missing output formats, missing constraints
- **Framing analysis** — flags heavy-prohibition skills with no positive alternatives
- **Duplicate detection** — finds near-duplicate instructions that waste tokens
- **Best practices** — missing model specs, missing error handling, missing verification gates
- Scores each file 0-100 with actionable fix suggestions

[Design doc](docs/pillars/01-skill-scanner.md)

### 2. Usage Insights (`ai-helper stats`) — Implemented

Understand how you use AI tools across your workflow.

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

- Cross-tool usage summary (sessions, tokens, estimated cost, time)
- Recent sessions table with model, turns, output, cost, duration, project
- Model usage distribution (turns and share %)
- Cost estimation using published model pricing (with honest caveat)
- Currently reads Claude Code session data; OpenCode and Cursor planned

[Design doc](docs/pillars/02-usage-insights.md)

### 3. Config Manager (`ai-helper config`) — Implemented

One command to configure your AI tools consistently.

```bash
# See current config across all tools side by side
ai-helper config show

# Set your preferred models across all tools
ai-helper config set --model opus --small-model sonnet

# Target a specific tool
ai-helper config set --model sonnet --tool opencode

# Model aliases work: opus, sonnet, haiku
# Full model IDs also accepted: google-vertex-anthropic/claude-sonnet-4-6@default
```

- Set default models across Claude Code and OpenCode (Cursor shows UI instruction)
- Side-by-side config comparison table
- Model aliases (`opus`, `sonnet`, `haiku`) resolve to full IDs
- Per-tool targeting with `--tool`

[Design doc](docs/pillars/03-config-manager.md)

### 4. Smart Defaults (`ai-helper optimize`) — Implemented

Opt-in optimizations that help you spend less without changing how you work.

```bash
# Check what's active
ai-helper optimize status

# Install RTK across your tools (one command)
ai-helper optimize install rtk

# See measured token savings
ai-helper optimize report

# Find missed optimization opportunities
ai-helper optimize discover
```

- **RTK integration** — install across Claude Code and OpenCode with one command
- **Savings visibility** — wraps `rtk gain` and `rtk discover` for easy reporting
- **Ponytail integration** — planned
- **Model recommendations** — planned

Everything is advisory. Override anytime.

[Design doc](docs/pillars/04-smart-defaults.md)

### 5. Developer Setup (`ai-helper init` / `ai-helper doctor`) — Doctor Implemented

Get productive with AI tools in minutes, not hours.

```bash
# Health check across all installed tools
ai-helper doctor
# Shows: version, binary path, config, model, MCP servers,
#        RTK status, context files, and issues for each tool

# Set up AI tooling for this project (planned)
ai-helper init
```

- Detect installed AI tools, versions, and config locations
- Show model configuration, MCP servers, and RTK status
- Flag issues and suggest fixes
- Generate CLAUDE.md, .cursorrules, OpenCode config from project analysis (planned)

[Design doc](docs/pillars/05-developer-setup.md)

## Philosophy

1. **Help, don't restrict** — every feature is a suggestion, not a gate
2. **Show, don't enforce** — display cost impact and let users decide
3. **Opt-in everything** — nothing changes without explicit user action
4. **Cross-tool by default** — one tool, three AI coding environments
5. **Honest numbers** — no inflated savings claims; measure and report real data

## Architecture

ai-helper is built as an **MCP server** with a **CLI wrapper**. Since Claude Code, OpenCode, and Cursor all support MCP, the server provides capabilities to all three tools through a single implementation. The CLI provides the same features for direct terminal use.

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
| 2. Usage Insights | Claude Code session analytics with cost estimation |
| 3. Config Manager | Cross-tool model config with aliases |
| 4. Smart Defaults | RTK integration (install, status, report, discover) |
| 5. Developer Setup | `doctor` working, `init` planned |

## License

[Apache-2.0](LICENSE)
