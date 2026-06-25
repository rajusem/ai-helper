# Pillar 1: Skill Scanner

## Command

```bash
ai-helper scan [path] [--format table|json] [--severity warning|suggestion|info]
```

## Problem

AI skill files (SKILL.md, agent definitions, CLAUDE.md, .cursorrules) are the primary interface between developers and AI coding tools. Poorly written skills lead to wasted tokens, hallucinations, inconsistent output, and rework cycles. No tool exists to lint or analyze these files for quality.

## Approach

Static analysis of skill files — check for detectable patterns that correlate with poor agent performance. Score each file 0-100 with actionable fix suggestions.

## Check Categories

| Category | What It Catches |
|----------|----------------|
| **token-cost** | Oversized files, long lines, filler phrases, near-duplicates |
| **description** | Workflow summaries in descriptions, missing trigger conditions |
| **hallucination-risk** | Vague instructions, missing output format, missing constraints |
| **framing** | Heavy prohibitions with no positive alternatives, conflicting instructions |
| **output-quality** | Missing examples, missing verification gates |
| **best-practice** | No model in frontmatter, multi-step without error handling |
| **structure** | Missing headers, broken frontmatter |

## Files Discovered

The scanner automatically finds:
- `CLAUDE.md`, `AGENTS.md`, `.cursorrules` in project root
- `agents/*.md` in `.opencode/agents/`, `.claude/agents/`, `agents/`
- `SKILL.md` files in `.opencode/skills/`, `.claude/skills/`, `skills/`

## Future Checks

- Cross-reference validation (do referenced files/tools exist?)
- Cross-tool compatibility (patterns that work in Claude Code but not Cursor)
- Model-appropriate complexity (Opus specified for a Sonnet-level task?)
- Prompt injection risk (does the skill handle untrusted input?)
- Skill testing coverage

## MCP Integration

As an MCP tool, `scan` can be invoked during AI sessions:
- "Scan this project's skills for issues"
- "Check if my CLAUDE.md is too large"
- "Review my agent definitions for quality"
