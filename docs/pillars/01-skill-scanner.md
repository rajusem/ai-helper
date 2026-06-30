# Pillar 1: Skill Scanner

## Command

```bash
ai-helper scan [path] [options]
```

### Options

| Flag | Purpose |
|------|---------|
| `--format table\|sarif` | Output format (default: table) |
| `--severity warning\|suggestion\|info` | Minimum severity to show |
| `--verbose` / `-v` | Show per-file detail |
| `--disable RULE1,RULE2` | Suppress specific rules |
| `--fail-on warning\|suggestion\|info` | Exit non-zero for CI gates |
| `--save-baseline` | Save current findings as baseline |
| `--diff` | Show only new issues since baseline |
| `--baseline-path PATH` | Custom baseline file location |
| `--report` | Show aggregate summary with top rules and worst files |

Supports local directories and GitHub HTTPS URLs (`ai-helper scan https://github.com/org/repo`).

## Problem

AI skill files (SKILL.md, agent definitions, CLAUDE.md, .cursorrules) are the primary interface between developers and AI coding tools. Poorly written skills lead to wasted tokens, hallucinations, inconsistent output, and rework cycles. No tool exists to lint or analyze these files for quality.

## Approach

Static analysis of skill files — check for detectable patterns that correlate with poor agent performance. Score each file 0-100 with actionable fix suggestions. Severity-weighted scoring with per-category caps.

## Rules (35+)

| Prefix | Category | Example Rules |
|--------|----------|---------------|
| TCOST | Token cost | TCOST001 (file too long), TCOST003 (consider trimming), TCOST007 (near-duplicates), TCOST008 (hedging language), TCOST010 (long paragraphs) |
| DESC | Description quality | DESC001 (description too long), DESC003 (second-person in description), DESC005 (no "Use when...") |
| HRISK | Hallucination risk | HRISK001 (vague instruction), HRISK002 (no output format), HRISK004 (compound instructions) |
| FRAME | Framing | FRAME001 (heavy prohibitions without positive alternatives) |
| OQUAL | Output quality | OQUAL001 (no examples), OQUAL002 (no verification steps), OQUAL003 (no role statement) |
| BPRAC | Best practice | BPRAC001 (no model in frontmatter), BPRAC002 (no error handling), BPRAC003 (no termination condition) |
| STRUCT | Structure | STRUCT002 (encoding issues), STRUCT003 (no headers), STRUCT006 (broken file references) |

## Features

- **SARIF output** for CI/CD integration
- **Baseline/diff mode** for incremental adoption — save current findings, then only show new issues
- **Config file** (`.ai-helper-scan.yaml`) for per-project rule disabling and fail-on thresholds
- **Custom rules** via `Rule` base class and `RULE_REGISTRY` (must use `CUSTOM_` prefix)
- **URL scanning** — scan public GitHub repos by HTTPS URL (shallow clone, auto cleanup)
- **Content region parsing** — distinguishes frontmatter, code fences, and content to avoid false positives in code blocks
- **False-positive mitigations** — runtime-created file detection, target-repo reference detection, word-boundary hedging matching, delegation-aware checks, linear-step vs loop distinction

## Files Discovered

The scanner automatically finds:
- `CLAUDE.md`, `AGENTS.md`, `.cursorrules` in project root
- `agents/*.md` in `.opencode/agents/`, `.claude/agents/`, `agents/`
- `SKILL.md` files in `.opencode/skills/`, `.claude/skills/`, `skills/`

## Future Checks

- Cross-tool compatibility (patterns that work in Claude Code but not Cursor)
- Model-appropriate complexity (Opus specified for a Sonnet-level task?)
- Prompt injection risk (does the skill handle untrusted input?)
