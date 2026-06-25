# ai-helper

Your toolkit for working smarter with AI coding tools.

**Scan for vulnerabilities. See what you spend. Configure your tools. Optimize your workflow.**

ai-helper is an open-source CLI and MCP server that helps developers get more out of AI coding tools — without restricting how they use them. Everything is a suggestion, never a mandate.

## Target Tools

| Tool | Integration |
|------|------------|
| [Claude Code](https://claude.ai/code) | Plugin + MCP server |
| [OpenCode](https://opencode.ai) | Plugin + MCP server |
| [Cursor](https://cursor.com) | Rules + MCP server |

## Pillars

### 1. Security Scanner (`ai-helper scan`)

Orchestrate security scanning across your dependencies and codebase. Wraps existing scanners (Trivy, Grype, OSV-Scanner) and adds an AI triage layer for prioritization and fix suggestions.

- Unified results from multiple scanners, deduplicated
- AI-powered severity assessment and fix recommendations
- License compliance checking
- SBOM generation

[Design doc](docs/pillars/01-security-scanner.md)

### 2. Usage Insights (`ai-helper stats`)

Understand how you use AI tools across your workflow. Not just tracking — actionable insights and recommendations.

- Cross-tool token, cost, and time analytics
- Model usage patterns and cost comparison
- "You spent $12 on Claude Code and $8 on Cursor for similar tasks — here's which was more cost-effective"
- Session history and trends
- Team dashboards and budget awareness

[Design doc](docs/pillars/02-usage-insights.md)

### 3. Config Manager (`ai-helper config`)

One command to configure your AI tools consistently.

```bash
# Set your preferred models across all tools
ai-helper config set --model opus --small-model sonnet

# See current config across all tools
ai-helper config show

# Sync MCP server configuration
ai-helper config sync-mcp
```

- Set default models across Claude Code, OpenCode, and Cursor
- Sync MCP server registrations
- Manage rules/instructions files
- Profile support (work vs personal)

[Design doc](docs/pillars/03-config-manager.md)

### 4. Smart Defaults (`ai-helper optimize`)

Opt-in optimizations that help you spend less without changing how you work.

- **RTK integration** — compress tool output before your AI reads it. One-command install.
- **Ponytail integration** — smart code generation defaults that reduce unnecessary output.
- **Model recommendations** — suggests the right model tier based on task type.
- **Savings visibility** — see what you saved, not what you're forced to save.

Everything is advisory. Override anytime.

[Design doc](docs/pillars/04-smart-defaults.md)

### 5. Developer Setup (`ai-helper init`)

Get productive with AI tools in minutes, not hours.

```bash
# Set up AI tooling for this project
ai-helper init

# Health check across all installed tools
ai-helper doctor

# Generate project context files from codebase analysis
ai-helper init context
```

- Detect installed AI tools and their versions
- Generate CLAUDE.md, .cursorrules, OpenCode config from project analysis
- Install and configure MCP servers across tools
- Health check: auth, config, versions, common issues

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

## Status

Early development. See the [design docs](docs/) for the current plan.

## License

[Apache-2.0](LICENSE)
