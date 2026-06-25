# Pillar 1: Security Scanner Orchestrator

## Command

```bash
ai-helper scan [path] [--format json|table|sarif] [--fix] [--severity critical,high]
```

## Problem

Developers use multiple security scanning tools, each with different output formats, coverage gaps, and false positive rates. Adding AI triage on top is a separate manual step. No single open-source tool covers vulnerability scanning + license analysis + SBOM generation + AI-powered prioritization.

## Approach

**Orchestrate, don't replace.** Wrap proven deterministic scanners and add an AI layer for triage and fix suggestions.

```
ai-helper scan
      ↓
  ┌───┼───┐
  ↓   ↓   ↓
Trivy Grype OSV-Scanner    ← run in parallel
  ↓   ↓   ↓
  └───┼───┘
      ↓
  Dedup & normalize        ← unified finding format
      ↓
  AI triage (optional)     ← prioritization + fix suggestions
      ↓
  Report
```

### Why Hybrid (Not AI-Only)

Academic research (Gnieciak & Szandala, 2025) found:
- LLMs hallucinate vulnerabilities (flagging up-to-date libraries as outdated)
- LLMs can't pinpoint line/column locations accurately
- Deterministic scanners provide high-assurance verification

Best results come from: **deterministic scan first, AI triage second.**

## MVP Features

1. **Multi-scanner execution** — run Trivy + Grype in parallel on a project
2. **Result normalization** — unified JSON format regardless of scanner
3. **Deduplication** — merge overlapping findings from multiple scanners
4. **Severity filtering** — `--severity critical,high` to focus on what matters
5. **Output formats** — table (terminal), JSON (scripting), SARIF (IDE integration)

## Future Features

- AI triage: severity assessment with context ("this CVE is in a test dependency, low risk")
- AI fix suggestions: "Update package X from v1.2 to v1.3 to resolve CVE-2026-XXXX"
- License compliance scanning
- SBOM generation (CycloneDX, SPDX)
- CI/CD integration (GitHub Actions, GitLab CI)
- Policy engine: org-defined rules ("no GPL in production deps")
- Diff-aware scanning: only scan changed dependencies in PRs

## Competitors

| Tool | Type | Limitation |
|------|------|-----------|
| Trivy | Deterministic | Single tool, no AI triage |
| Grype | Deterministic | Single tool, no AI triage |
| Snyk | Freemium SaaS | $25/dev/month, not open-source |
| OpenAnt | AI-powered | Security-only, no usage tracking or config |
| Metis | AI-powered | Security-only, code review focused |

**Differentiation:** ai-helper scan is part of a larger toolkit. Security findings integrate with usage insights ("this scan cost X tokens") and config management ("scan with Sonnet to save cost").

## Dependencies

- Trivy (must be installed): `brew install trivy` / `apt install trivy`
- Grype (must be installed): `brew install grype` / `curl -sSfL install.grype.io | sh`
- OSV-Scanner (optional): `brew install osv-scanner`

## MCP Integration

As an MCP tool, `scan` can be invoked by AI coding tools during sessions:
- "Scan this project for vulnerabilities before I merge"
- "Check if this dependency I'm adding has known CVEs"
- "Generate an SBOM for this project"
