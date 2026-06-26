"""ai-helper scan — skill and prompt analyzer.

Reads AI skill files (SKILL.md, agent .md, CLAUDE.md, AGENTS.md, .cursorrules)
and suggests improvements for better performance, fewer tokens, less
hallucination, and more consistent output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

SKILL_PATTERNS = [
    "SKILL.md",
    "CLAUDE.md",
    "AGENTS.md",
    ".cursorrules",
]

AGENT_DIRS = [
    ".opencode/agents",
    ".claude/agents",
    "agents",
]

SKILL_DIRS = [
    ".opencode/skills",
    ".claude/skills",
    "skills",
]


@dataclass
class Issue:
    category: str
    severity: str  # info, suggestion, warning
    message: str
    fix: str = ""
    line: int | None = None


@dataclass
class ScanResult:
    file: str
    token_estimate: int = 0
    issues: list[Issue] = field(default_factory=list)
    score: int = 100


def run_scan(
    path: str = ".",
    fmt: str = "table",
    severity_filter: str | None = None,
) -> None:
    target = Path(path).resolve()
    if not target.exists():
        console.print(f"[bold red]Path not found: {path}[/bold red]")
        return

    files = _discover_files(target)
    if not files:
        console.print("[yellow]No skill or agent files found.[/yellow]")
        console.print(
            "Looked for: SKILL.md, CLAUDE.md, AGENTS.md, .cursorrules,"
            " agents/*.md, skills/*/SKILL.md"
        )
        return

    console.print()
    console.print(
        f"Scanning [bold]{len(files)} file{'s' if len(files) != 1 else ''}"
        f"[/bold] in {target}"
    )
    console.print()

    results = []
    for filepath in files:
        result = _analyze_file(filepath, target)
        results.append(result)

    if severity_filter:
        allowed = {s.strip().lower() for s in severity_filter.split(",")}
        for r in results:
            r.issues = [i for i in r.issues if i.severity in allowed]

    if fmt == "json":
        _print_json(results)
    else:
        _print_results(results)


def _discover_files(root: Path) -> list[Path]:
    files = []

    for pattern in SKILL_PATTERNS:
        p = root / pattern
        if p.exists() and p.is_file():
            files.append(p)

    for agent_dir in AGENT_DIRS:
        d = root / agent_dir
        if d.exists():
            files.extend(sorted(d.glob("*.md")))

    for skill_dir in SKILL_DIRS:
        d = root / skill_dir
        if d.exists():
            files.extend(sorted(d.rglob("SKILL.md")))

    return list(dict.fromkeys(files))


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _analyze_file(filepath: Path, root: Path) -> ScanResult:
    content = filepath.read_text()
    rel_path = str(filepath.relative_to(root))
    tokens = _estimate_tokens(content)
    result = ScanResult(file=rel_path, token_estimate=tokens)
    lines = content.splitlines()

    _check_size(result, content, tokens, lines)
    _check_structure(result, content, lines)
    _check_description_quality(result, content)
    _check_token_waste(result, content, lines)
    _check_hedging_and_filler(result, content)
    _check_hallucination_risks(result, content, lines)
    _check_output_quality(result, content, lines)
    _check_failure_mode_framing(result, content, lines)
    _check_nested_references(result, content, lines)
    _check_redundant_context(result, content, filepath)
    _check_best_practices(result, content, lines)

    penalty = sum(
        3 if i.severity == "warning" else 1
        for i in result.issues
    )
    result.score = max(0, 100 - penalty * 5)

    return result


def _check_size(
    result: ScanResult, content: str, tokens: int, lines: list[str]
) -> None:
    line_count = len(lines)
    if line_count > 500:
        result.issues.append(Issue(
            category="token-cost",
            severity="warning",
            message=f"File is {line_count} lines — exceeds 500-line"
            " limit recommended by Anthropic and Cursor",
            fix="Split into focused sections. Move reference material"
            " to separate files loaded on demand",
        ))
    elif tokens > 5000:
        result.issues.append(Issue(
            category="token-cost",
            severity="warning",
            message=f"File is ~{tokens} tokens — costs this on EVERY turn",
            fix="Split into focused sections or move rarely-needed"
            " content to separate files read on demand",
        ))
    elif tokens > 2000:
        result.issues.append(Issue(
            category="token-cost",
            severity="suggestion",
            message=f"File is ~{tokens} tokens — consider trimming",
            fix="Remove content not needed in 80%+ of sessions",
        ))
    elif tokens < 150 and line_count > 5:
        result.issues.append(Issue(
            category="token-cost",
            severity="info",
            message=f"File is only ~{tokens} tokens — may be too sparse",
            fix="Ensure key instructions are present."
            " Very short skills may lack necessary constraints",
        ))


def _check_structure(
    result: ScanResult, content: str, lines: list[str]
) -> None:
    has_headers = any(line.startswith("#") for line in lines)
    if len(lines) > 30 and not has_headers:
        result.issues.append(Issue(
            category="structure",
            severity="suggestion",
            message="Long file with no markdown headers",
            fix="Add ## headers to organize content — helps agents"
            " navigate and reduces misinterpretation",
        ))

    if content.startswith("---"):
        end = content.find("---", 3)
        if end == -1:
            result.issues.append(Issue(
                category="structure",
                severity="warning",
                message="Frontmatter opened but never closed",
                fix="Add closing --- after frontmatter block",
            ))


def _check_description_quality(result: ScanResult, content: str) -> None:
    """Check 1: Skill descriptions should be trigger conditions, not
    workflow summaries. When a description summarizes the workflow, the
    agent follows the description instead of reading the skill body."""
    if not content.startswith("---"):
        return
    end = content.find("---", 3)
    if end == -1:
        return
    frontmatter = content[3:end]

    desc_match = re.search(
        r"description:\s*(.+?)(?:\n\w|\n---)", frontmatter, re.DOTALL
    )
    if not desc_match:
        return
    desc = desc_match.group(1).strip().strip("\"'")

    if len(desc) > 200:
        result.issues.append(Issue(
            category="description",
            severity="warning",
            message=f"Description is {len(desc)} chars — too long,"
            " agent may follow it instead of reading the skill body",
            fix="Keep description under ~100 chars with trigger"
            " conditions only: 'Use when...' not a workflow summary",
        ))

    workflow_signals = [
        r"\bthen\b.*\bthen\b",
        r"\bstep \d\b",
        r"\bfirst\b.*\bthen\b.*\bfinally\b",
        r"\banalyze.*generate.*report\b",
    ]
    for pattern in workflow_signals:
        if re.search(pattern, desc, re.IGNORECASE):
            result.issues.append(Issue(
                category="description",
                severity="warning",
                message="Description looks like a workflow summary,"
                " not a trigger condition",
                fix="Rewrite as 'Use when...' trigger."
                " Move workflow steps into the skill body.",
            ))
            break

    if re.search(r"\b(you should|you will|you are|I will|I am)\b", desc, re.I):
        result.issues.append(Issue(
            category="description",
            severity="warning",
            message="Description uses first/second person",
            fix="Write in third person — descriptions are injected"
            " into the system prompt, and inconsistent POV causes"
            " discovery problems (Anthropic best practices)",
        ))

    if len(desc) < 10:
        result.issues.append(Issue(
            category="description",
            severity="suggestion",
            message="Description is very short — may not trigger"
            " automatic skill discovery",
            fix="Include what the skill does AND when to use it",
        ))

    if not re.search(r"\b(use when|use for|invoke when)\b", desc, re.I):
        if len(desc) > 50:
            result.issues.append(Issue(
                category="description",
                severity="suggestion",
                message="Description doesn't state when to use"
                " this skill",
                fix="Start with 'Use when...' so agents (and humans)"
                " know the trigger condition",
            ))


def _check_token_waste(
    result: ScanResult, content: str, lines: list[str]
) -> None:
    for i, line in enumerate(lines, 1):
        if len(line) > 200 and not line.startswith("http"):
            result.issues.append(Issue(
                category="token-cost",
                severity="info",
                message=f"Line {i} is {len(line)} chars — long lines waste tokens",
                fix="Break into shorter sentences for clarity",
                line=i,
            ))
            break  # only report first

    filler = [
        r"\bplease\b",
        r"\bkindly\b",
        r"\bmake sure to\b",
        r"\bensure that you\b",
        r"\bit is important that\b",
        r"\bremember to\b",
        r"\bdon'?t forget to\b",
        r"\byou should always\b",
    ]
    for pattern in filler:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if len(matches) >= 3:
            result.issues.append(Issue(
                category="token-cost",
                severity="suggestion",
                message=f"Filler phrase '{matches[0]}' appears"
                f" {len(matches)} times",
                fix="Use direct imperatives instead —"
                " 'Verify X' not 'Please make sure to verify X'",
            ))
            break

    duplicates = _find_duplicate_instructions(lines)
    if duplicates:
        result.issues.append(Issue(
            category="token-cost",
            severity="warning",
            message=f"Near-duplicate instructions found ({duplicates} pairs)",
            fix="Remove redundant instructions — agents read everything,"
            " repeating wastes tokens",
        ))


def _find_duplicate_instructions(lines: list[str]) -> int:
    stripped = [
        line.strip().lower()
        for line in lines
        if len(line.strip()) > 40 and not line.strip().startswith("#")
    ]
    seen = {}
    dupes = 0
    for line in stripped:
        key = re.sub(r"\s+", " ", line)[:80]
        if key in seen:
            dupes += 1
        else:
            seen[key] = True
    return dupes


def _check_hallucination_risks(
    result: ScanResult, content: str, lines: list[str]
) -> None:
    vague_patterns = [
        (r"\bdo (?:the |your )?best\b", "do your best"),
        (r"\btry to\b", "try to"),
        (r"\bif possible\b", "if possible"),
        (r"\bas needed\b", "as needed"),
        (r"\bwhen appropriate\b", "when appropriate"),
        (r"\buse your judgment\b", "use your judgment"),
    ]
    for pattern, label in vague_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            result.issues.append(Issue(
                category="hallucination-risk",
                severity="suggestion",
                message=f"Vague instruction: '{label}'",
                fix="Replace with specific criteria — vague instructions"
                " let agents hallucinate what 'best' or 'appropriate' means",
            ))
            break

    has_output_format = bool(re.search(
        r"(output format|respond with|return.*json|format.*response"
        r"|structured output|```)",
        content, re.IGNORECASE,
    ))
    if not has_output_format and len(lines) > 20:
        result.issues.append(Issue(
            category="hallucination-risk",
            severity="suggestion",
            message="No output format specified",
            fix="Define expected output format (JSON schema, markdown"
            " template, or example) to constrain agent responses",
        ))

    has_constraints = bool(re.search(
        r"(do not|don'?t|never|must not|avoid|only|forbidden"
        r"|prohibited|restrict)",
        content, re.IGNORECASE,
    ))
    if not has_constraints and len(lines) > 15:
        result.issues.append(Issue(
            category="hallucination-risk",
            severity="info",
            message="No negative constraints found",
            fix="Add explicit 'do NOT' rules for common failure modes"
            " — agents follow positive instructions better with"
            " guardrails",
        ))


def _check_output_quality(
    result: ScanResult, content: str, lines: list[str]
) -> None:
    has_examples = bool(re.search(
        r"(example|e\.g\.|for instance|sample|```)",
        content, re.IGNORECASE,
    ))
    if not has_examples and len(lines) > 20:
        result.issues.append(Issue(
            category="output-quality",
            severity="suggestion",
            message="No examples provided",
            fix="Add 1-2 examples of expected output — examples are the"
            " most effective way to guide agent behavior",
        ))

    has_verification = bool(re.search(
        r"(verify|validate|check|confirm|test|assert|evidence|prove)",
        content, re.IGNORECASE,
    ))
    if not has_verification and len(lines) > 30:
        result.issues.append(Issue(
            category="output-quality",
            severity="suggestion",
            message="No verification steps",
            fix="Add verification gates — 'verify X before proceeding'"
            " prevents false completion claims",
        ))


def _check_failure_mode_framing(
    result: ScanResult, content: str, lines: list[str]
) -> None:
    """Prohibitions work for rule-violations but backfire for
    output-shape issues. Check if the framing matches the failure type."""
    prohibitions = re.findall(
        r"(do not|don'?t|never|must not|avoid|forbidden)", content, re.I
    )
    positives = re.findall(
        r"(instead|prefer|use .+ rather|always .+ when|the correct)",
        content, re.I,
    )

    if len(prohibitions) > 6 and len(positives) < 2:
        result.issues.append(Issue(
            category="framing",
            severity="suggestion",
            message=f"Heavy on prohibitions ({len(prohibitions)})"
            f" with few positive alternatives ({len(positives)})",
            fix="Balance 'do NOT X' with 'instead do Y' —"
            " agents need to know what TO do, not just what to avoid."
            " Prohibitions alone can cause over-cautious behavior",
        ))

    conflicting = _find_conflicting_instructions(content)
    if conflicting:
        result.issues.append(Issue(
            category="framing",
            severity="warning",
            message=f"Potentially conflicting instructions: {conflicting}",
            fix="Resolve contradictions — conflicting instructions"
            " cause unpredictable agent behavior",
        ))


def _find_conflicting_instructions(content: str) -> str | None:
    pairs = [
        (r"\balways\b.{5,40}\b(detailed|verbose|thorough)\b",
         r"\b(concise|brief|short|minimal)\b"),
        (r"\bnever\b.{5,30}\b(skip|omit)\b",
         r"\b(only when|if needed|optional)\b"),
    ]
    for pattern_a, pattern_b in pairs:
        if (re.search(pattern_a, content, re.I)
                and re.search(pattern_b, content, re.I)):
            return "both verbose/thorough AND concise/brief guidance found"
    return None


def _check_hedging_and_filler(result: ScanResult, content: str) -> None:
    """Hedging and filler tokens waste context. Based on cclint's
    karpathy rule and AgentLinter's compressible-padding detection."""
    hedging = [
        "try to", "where appropriate", "when possible",
        "if you can", "consider", "might want to",
        "it would be good to", "ideally",
    ]
    found_hedging = [
        h for h in hedging
        if content.lower().count(h) >= 2
    ]
    if found_hedging:
        result.issues.append(Issue(
            category="token-cost",
            severity="suggestion",
            message="Hedging language repeated: "
            + ", ".join(f"'{h}'" for h in found_hedging[:3]),
            fix="Replace with direct imperatives."
            " 'Verify X' not 'Try to verify X where appropriate'",
        ))

    filler_phrases = [
        "you are a helpful assistant",
        "thank you",
        "great job",
        "i appreciate",
    ]
    for phrase in filler_phrases:
        if phrase in content.lower():
            result.issues.append(Issue(
                category="token-cost",
                severity="suggestion",
                message=f"Filler phrase: '{phrase}'",
                fix="Remove — agents don't need politeness tokens."
                " Every word in a skill file costs tokens on every turn",
            ))
            break

    long_paragraphs = 0
    current_len = 0
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            current_len += len(stripped.split())
        else:
            if current_len > 80:
                long_paragraphs += 1
            current_len = 0
    if long_paragraphs >= 2:
        result.issues.append(Issue(
            category="token-cost",
            severity="suggestion",
            message=f"{long_paragraphs} paragraphs over 80 words",
            fix="Break into shorter paragraphs or bullet points."
            " Dense prose is harder for agents to parse accurately",
        ))


def _check_nested_references(
    result: ScanResult, content: str, lines: list[str]
) -> None:
    """File references should be one level deep. Nested references
    cause agents to partially read files with head -100."""
    ref_pattern = re.compile(
        r"(?:read|see|refer to|check|load|reference)\s+"
        r"[`'\"]?([a-zA-Z0-9_./-]+\.\w+)[`'\"]?",
        re.IGNORECASE,
    )
    refs = ref_pattern.findall(content)
    if len(refs) > 10:
        result.issues.append(Issue(
            category="structure",
            severity="suggestion",
            message=f"File references {len(refs)} other files",
            fix="Keep references one level deep from SKILL.md."
            " Deeply nested refs cause agents to partially read"
            " files (head -100), losing information",
        ))


def _check_redundant_context(
    result: ScanResult, content: str, filepath: Path
) -> None:
    """Detect content the agent can infer from the project."""
    project_root = filepath.parent
    while project_root.parent != project_root:
        if (project_root / "package.json").exists():
            break
        if (project_root / "pyproject.toml").exists():
            break
        if (project_root / ".git").exists():
            break
        project_root = project_root.parent

    tech_mentions = re.findall(
        r"\b(?:we use|built with|using|our stack includes)\s+"
        r"([A-Za-z][A-Za-z0-9.]+)",
        content, re.IGNORECASE,
    )
    if not tech_mentions:
        return

    pkg_json = project_root / "package.json"
    pyproject = project_root / "pyproject.toml"
    inferable = set()

    if pkg_json.exists():
        try:
            import json
            data = json.loads(pkg_json.read_text())
            deps = set(data.get("dependencies", {}).keys())
            deps |= set(data.get("devDependencies", {}).keys())
            inferable = {d.lower() for d in deps}
        except Exception:
            pass
    elif pyproject.exists():
        try:
            text = pyproject.read_text()
            inferable = {
                m.lower()
                for m in re.findall(r'"([a-zA-Z][a-zA-Z0-9_-]+)"', text)
            }
        except Exception:
            pass

    redundant = [
        t for t in tech_mentions if t.lower() in inferable
    ]
    if redundant:
        result.issues.append(Issue(
            category="token-cost",
            severity="suggestion",
            message="Redundant tech mentions: "
            + ", ".join(f"'{t}'" for t in redundant[:3]),
            fix="Remove — agent can infer these from"
            " package.json/pyproject.toml. Stating 'we use X'"
            " when X is in dependencies wastes tokens",
        ))


def _check_best_practices(
    result: ScanResult, content: str, lines: list[str]
) -> None:
    lower = content.lower()

    if "model" not in lower and "---" in content[:10]:
        frontmatter_end = content.find("---", 3)
        if frontmatter_end > 0:
            fm = content[:frontmatter_end]
            if "model" not in fm.lower():
                result.issues.append(Issue(
                    category="best-practice",
                    severity="info",
                    message="No model specified in frontmatter",
                    fix="Add 'model: sonnet' or 'model: opus' to match"
                    " task complexity — saves cost on simple tasks",
                ))

    if re.search(r"(step \d|phase \d|stage \d)", lower):
        has_error_handling = bool(re.search(
            r"(if.*fail|error|fallback|abort|stop|retry|escalat)",
            lower,
        ))
        if not has_error_handling:
            result.issues.append(Issue(
                category="best-practice",
                severity="suggestion",
                message="Multi-step process without error handling",
                fix="Add failure protocol — what should the agent do"
                " when a step fails? Without this, agents retry"
                " endlessly and waste tokens",
            ))


def _print_results(results: list[ScanResult]) -> None:
    total_issues = sum(len(r.issues) for r in results)
    total_tokens = sum(r.token_estimate for r in results)

    for result in results:
        color = "green" if result.score >= 80 else (
            "yellow" if result.score >= 50 else "red"
        )
        header = (
            f"[{color}]{result.score}/100[/{color}]"
            f"  {result.file}"
            f"  [dim](~{result.token_estimate} tokens)[/dim]"
        )

        if not result.issues:
            console.print(f"  {header}  [green]no issues[/green]")
            continue

        lines = []
        for issue in result.issues:
            sev_style = {
                "warning": "yellow",
                "suggestion": "cyan",
                "info": "dim",
            }.get(issue.severity, "dim")

            lines.append(
                f"[{sev_style}]{issue.severity.upper():10}[/{sev_style}]"
                f" [{issue.category}] {issue.message}"
            )
            if issue.fix:
                lines.append(f"           [dim]Fix: {issue.fix}[/dim]")

        console.print(Panel(
            "\n".join(lines),
            title=header,
            border_style=color,
        ))

    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Files scanned", str(len(results)))
    table.add_row("Total tokens", f"~{total_tokens:,}")
    table.add_row("Issues found", str(total_issues))
    avg_score = (
        sum(r.score for r in results) // len(results) if results else 0
    )
    table.add_row("Avg score", f"{avg_score}/100")
    console.print(table)
    console.print()


def _print_json(results: list[ScanResult]) -> None:
    import json
    output = [
        {
            "file": r.file,
            "token_estimate": r.token_estimate,
            "score": r.score,
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity,
                    "message": i.message,
                    "fix": i.fix,
                }
                for i in r.issues
            ],
        }
        for r in results
    ]
    console.print_json(json.dumps(output, indent=2))
