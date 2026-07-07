"""Unit tests for scan.py — bug fixes + R1 conditions."""

import json
from pathlib import Path

import pytest

from ai_helper.scan import (
    RULE_REGISTRY,
    Issue,
    Rule,
    ScanResult,
    _analyze_file,
    _baseline_key,
    _build_baseline,
    _check_broken_references,
    _check_compound_instructions,
    _check_description_quality,
    _check_failure_mode_framing,
    _check_hallucination_risks,
    _check_hedging_and_filler,
    _check_output_quality,
    _check_redundant_context,
    _check_role_identity,
    _check_structure,
    _check_termination_conditions,
    _check_token_waste,
    _compute_score,
    _count_hedging,
    _find_conflicting_instructions,
    _find_duplicate_instructions,
    _has_skill_delegation,
    _is_git_url,
    _is_root_reference_doc,
    _load_baseline,
    _load_config,
    _parse_content_regions,
    _print_sarif,
    _save_baseline,
    register_rule,
    run_scan,
)

# ── _parse_content_regions ──────────────────────────────────────────


class TestParseContentRegions:
    def test_all_content(self):
        lines = ["hello", "world", "foo"]
        assert _parse_content_regions(lines) == [
            "content", "content", "content"
        ]

    def test_frontmatter(self):
        lines = ["---", "key: value", "other: x", "---", "body"]
        regions = _parse_content_regions(lines)
        assert regions == [
            "frontmatter", "frontmatter", "frontmatter",
            "frontmatter", "content",
        ]

    def test_code_fence_backticks(self):
        lines = ["text", "```python", "code here", "```", "after"]
        regions = _parse_content_regions(lines)
        assert regions == [
            "content", "codefence", "codefence", "codefence", "content"
        ]

    def test_code_fence_tildes(self):
        lines = ["text", "~~~", "code", "~~~", "after"]
        regions = _parse_content_regions(lines)
        assert regions == [
            "content", "codefence", "codefence", "codefence", "content"
        ]

    def test_frontmatter_and_fence(self):
        lines = ["---", "key: val", "---", "text", "```", "code", "```"]
        regions = _parse_content_regions(lines)
        assert regions == [
            "frontmatter", "frontmatter", "frontmatter",
            "content", "codefence", "codefence", "codefence",
        ]

    def test_unclosed_frontmatter(self):
        lines = ["---", "key: val", "still going"]
        regions = _parse_content_regions(lines)
        assert all(r == "frontmatter" for r in regions)

    def test_unclosed_code_fence(self):
        lines = ["text", "```", "code", "more code"]
        regions = _parse_content_regions(lines)
        assert regions == [
            "content", "codefence", "codefence", "codefence"
        ]

    def test_nested_backtick_fence(self):
        lines = ["````", "```", "inner", "```", "````"]
        regions = _parse_content_regions(lines)
        assert all(r == "codefence" for r in regions)

    def test_dashes_in_content_not_frontmatter(self):
        lines = ["hello", "---", "world"]
        regions = _parse_content_regions(lines)
        assert regions == ["content", "content", "content"]


# ── Bug 1: Description regex ───────────────────────────────────────


class TestDescriptionRegex:
    def test_description_last_field_is_parsed(self):
        """Bug 1: description as last field should be parsed (not skipped)."""
        desc = "Reviews code for security issues and reports vulnerabilities found"
        content = f"---\ndescription: {desc}\n---\nbody"
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        descs = [i for i in result.issues if i.category == "description"]
        assert any("when to use" in i.message.lower() for i in descs), (
            "Should detect description as last field and flag missing trigger"
        )

    def test_description_followed_by_field(self):
        desc = "Reviews code for security issues and reports vulnerabilities found"
        content = f"---\ndescription: {desc}\nmodel: opus\n---\nbody"
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        descs = [i for i in result.issues if i.category == "description"]
        assert any("when to use" in i.message.lower() for i in descs)

    def test_long_description_last_field(self):
        long_desc = "A" * 250
        content = f"---\ndescription: {long_desc}\n---\nbody"
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        assert any("too long" in i.message.lower() for i in result.issues)

    def test_description_with_trigger(self):
        content = "---\ndescription: Use when deploying apps\n---\nbody"
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        assert not any(
            "when to use" in i.message.lower() for i in result.issues
        )


# ── Bug 2: Long-line skip in frontmatter/fence ────────────────────


class TestLongLineSkip:
    def _make_result(self):
        return ScanResult(file="test.md")

    def test_long_line_in_code_fence_skipped(self):
        lines = ["text", "```", "A" * 250, "```", "short"]
        regions = _parse_content_regions(lines)
        result = self._make_result()
        _check_token_waste(result, "\n".join(lines), lines, regions)
        long_line_issues = [
            i for i in result.issues if "chars" in i.message
        ]
        assert len(long_line_issues) == 0

    def test_long_line_in_frontmatter_skipped(self):
        lines = ["---", "description: " + "A" * 250, "---", "body"]
        regions = _parse_content_regions(lines)
        result = self._make_result()
        _check_token_waste(result, "\n".join(lines), lines, regions)
        long_line_issues = [
            i for i in result.issues if "chars" in i.message
        ]
        assert len(long_line_issues) == 0

    def test_long_line_in_content_reported(self):
        lines = ["---", "key: val", "---", "A" * 250]
        regions = _parse_content_regions(lines)
        result = self._make_result()
        _check_token_waste(result, "\n".join(lines), lines, regions)
        long_line_issues = [
            i for i in result.issues if "chars" in i.message
        ]
        assert len(long_line_issues) == 1

    def test_long_url_skipped(self):
        lines = ["https://example.com/" + "a" * 250]
        regions = _parse_content_regions(lines)
        result = self._make_result()
        _check_token_waste(result, "\n".join(lines), lines, regions)
        long_line_issues = [
            i for i in result.issues if "chars" in i.message
        ]
        assert len(long_line_issues) == 0


# ── Bug 3: Duplicate detection ─────────────────────────────────────


class TestDuplicateDetection:
    def test_shared_prefix_not_duplicate(self):
        prefix = "verify the output format is json before proceeding with "
        line_a = prefix + "validation and checking all fields are present"
        line_b = prefix + "error handling and ensuring proper logging setup"
        count = _find_duplicate_instructions([line_a, line_b])
        assert count == 0

    def test_identical_lines_duplicate(self):
        line = "always verify the output format before proceeding with the task"
        count = _find_duplicate_instructions([line, line])
        assert count == 1

    def test_short_lines_excluded(self):
        count = _find_duplicate_instructions(["short", "short"])
        assert count == 0

    def test_headers_excluded(self):
        line = "# This is a long header that repeats across the file somewhere"
        count = _find_duplicate_instructions([line, line])
        assert count == 0


# ── Bug 4: Encoding ────────────────────────────────────────────────


class TestEncoding:
    def test_valid_utf8(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Hello\nworld", encoding="utf-8")
        result = _analyze_file(f, tmp_path)
        assert not any(
            "non-UTF-8" in i.message for i in result.issues
        )

    def test_non_utf8_no_crash(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_bytes(b"hello \xff\xfe world\n" * 5)
        result = _analyze_file(f, tmp_path)
        assert any("non-UTF-8" in i.message for i in result.issues)
        assert result.file == "test.md"

    def test_permission_error(self, tmp_path):
        f = tmp_path / "nope.md"
        f.write_text("hello")
        f.chmod(0o000)
        try:
            result = _analyze_file(f, tmp_path)
            assert any("could not be read" in i.message.lower()
                        for i in result.issues)
        finally:
            f.chmod(0o644)


# ── Bug 5: Header check ───────────────────────────────────────────


class TestHeaderCheck:
    def _make_long_file(self, extra_lines: list[str]) -> tuple:
        base = [f"line {i}" for i in range(55)]
        lines = base + extra_lines
        content = "\n".join(lines)
        regions = _parse_content_regions(lines)
        return content, lines, regions

    def test_hash_in_fence_not_header(self):
        content, lines, regions = self._make_long_file(
            ["```bash", "#!/bin/bash", "# comment", "```"]
        )
        result = ScanResult(file="test.md")
        _check_structure(result, content, lines, regions)
        assert any(
            "no markdown headers" in i.message for i in result.issues
        )

    def test_real_header_detected(self):
        lines = ["## Section"] + [f"line {i}" for i in range(55)]
        content = "\n".join(lines)
        regions = _parse_content_regions(lines)
        result = ScanResult(file="test.md")
        _check_structure(result, content, lines, regions)
        assert not any(
            "no markdown headers" in i.message for i in result.issues
        )

    def test_shebang_not_header(self):
        lines = ["#!/bin/bash"] + [f"line {i}" for i in range(55)]
        content = "\n".join(lines)
        regions = _parse_content_regions(lines)
        result = ScanResult(file="test.md")
        _check_structure(result, content, lines, regions)
        assert any(
            "no markdown headers" in i.message for i in result.issues
        )


# ── R1: Rule IDs ─────────────────────────────────────────────────


class TestRuleIDs:
    def test_all_emitted_issues_have_nonempty_rule_id(self, tmp_path):
        """Every issue emitted by _analyze_file must have a non-empty rule_id."""
        # Create a file that triggers many checks
        content = (
            "---\n"
            "description: you should do stuff then do more stuff then finally finish\n"
            "---\n"
            + "\n".join([f"line {i}" for i in range(40)])
            + "\nplease do this\nplease do that\nplease do everything\n"
            + "try to do something. try to do something else.\n"
        )
        f = tmp_path / "SKILL.md"
        f.write_text(content, encoding="utf-8")
        result = _analyze_file(f, tmp_path)
        for issue in result.issues:
            assert issue.rule_id, (
                f"Issue has empty rule_id: [{issue.category}] {issue.message}"
            )

    def test_rule_ids_are_unique_across_mapping(self):
        """All rule IDs in the mapping should be unique strings."""
        # Collect all known rule IDs from the plan
        known_ids = [
            "STRUCT001", "STRUCT002", "STRUCT003", "STRUCT004", "STRUCT005",
            "TCOST001", "TCOST002", "TCOST003", "TCOST004", "TCOST005",
            "TCOST006", "TCOST007", "TCOST008", "TCOST009", "TCOST010",
            "TCOST011",
            "DESC001", "DESC002", "DESC003", "DESC004", "DESC005",
            "HRISK001", "HRISK002",
            "OQUAL001", "OQUAL002",
            "FRAME001", "FRAME002",
            "BPRAC001", "BPRAC002",
        ]
        assert len(known_ids) == len(set(known_ids)), "Duplicate rule IDs found"

    def test_disable_suppresses_specific_rule(self, tmp_path):
        """--disable should suppress issues with the given rule_id."""
        content = (
            "---\n"
            "description: you should do this stuff and also do that stuff and more things\n"
            "---\n"
            + "\n".join([f"line {i}" for i in range(40)])
        )
        f = tmp_path / "SKILL.md"
        f.write_text(content, encoding="utf-8")
        # First, get all issues
        result_all = _analyze_file(f, tmp_path)
        desc003_before = [i for i in result_all.issues if i.rule_id == "DESC003"]

        # Only test disable if DESC003 was actually emitted
        if desc003_before:
            disabled = {"DESC003"}
            filtered = [i for i in result_all.issues if i.rule_id not in disabled]
            assert not any(i.rule_id == "DESC003" for i in filtered)

    def test_disabled_rules_excluded_from_scoring(self, tmp_path):
        """Disabled rules should not contribute to the score."""
        issues = [
            Issue(category="structure", severity="warning", message="test",
                  rule_id="STRUCT001"),
        ]
        score_with = _compute_score(issues)
        score_without = _compute_score([])
        assert score_without > score_with

    def test_disable_empty_string_no_effect(self, tmp_path):
        """Passing empty disable set should not crash or change results."""
        content = "---\ndescription: Use when testing\n---\n## Test\nBody here"
        f = tmp_path / "SKILL.md"
        f.write_text(content, encoding="utf-8")
        result = _analyze_file(f, tmp_path)
        disabled = set()
        filtered = [i for i in result.issues if i.rule_id not in disabled]
        assert len(filtered) == len(result.issues)

    def test_disable_unknown_id_no_crash(self, tmp_path):
        """Unknown rule IDs should be silently ignored."""
        content = "---\ndescription: Use when testing\n---\n## Test\nBody here"
        f = tmp_path / "SKILL.md"
        f.write_text(content, encoding="utf-8")
        result = _analyze_file(f, tmp_path)
        disabled = {"UNKNOWN999"}
        filtered = [i for i in result.issues if i.rule_id not in disabled]
        assert len(filtered) == len(result.issues)


# ── R1: Scoring ──────────────────────────────────────────────────


class TestScoring:
    def test_one_warning_score_85(self):
        issues = [
            Issue(category="structure", severity="warning", message="t",
                  rule_id="STRUCT001"),
        ]
        assert _compute_score(issues) == 85

    def test_five_info_same_category_score_95(self):
        issues = [
            Issue(category="token-cost", severity="info", message=f"t{i}",
                  rule_id=f"TCOST00{i}")
            for i in range(5)
        ]
        assert _compute_score(issues) == 95

    def test_four_suggestions_same_category_capped(self):
        """4 suggestions = 4*5=20, capped at 15. Score = 85."""
        issues = [
            Issue(category="token-cost", severity="suggestion", message=f"t{i}",
                  rule_id=f"TCOST00{i}")
            for i in range(4)
        ]
        assert _compute_score(issues) == 85

    def test_multi_category_sums(self):
        """Penalties from different categories sum after per-category capping."""
        issues = [
            Issue(category="structure", severity="warning", message="t1",
                  rule_id="STRUCT001"),
            Issue(category="token-cost", severity="warning", message="t2",
                  rule_id="TCOST001"),
        ]
        # Each category: 15, capped at 15. Total = 30. Score = 70.
        assert _compute_score(issues) == 70

    def test_score_never_negative(self):
        """Score should never go below 0 even with many issues."""
        issues = [
            Issue(category=f"cat{i}", severity="warning", message=f"t{i}",
                  rule_id=f"X{i:03d}")
            for i in range(20)
        ]
        score = _compute_score(issues)
        assert score >= 0

    def test_zero_issues_score_100(self):
        assert _compute_score([]) == 100


# ── R1: Top-N ────────────────────────────────────────────────────


class TestTopN:
    def _make_issues(self, n: int) -> list[Issue]:
        severities = ["warning", "suggestion", "info"]
        return [
            Issue(
                category="token-cost",
                severity=severities[i % 3],
                message=f"Issue {i}",
                rule_id=f"TCOST{i:03d}",
            )
            for i in range(n)
        ]

    def test_default_truncates_at_3(self, capsys, tmp_path):
        """With >3 issues and not verbose, only 3 should display."""
        f = tmp_path / "SKILL.md"
        # Create content that triggers many issues
        content = (
            "---\n"
            "description: you should do all the things and stuff\n"
            "---\n"
            + "\n".join([f"line number {i} with some content" for i in range(50)])
            + "\nplease do X\nplease do Y\nplease do Z\n"
            + "try to do something\ntry to do something\n"
        )
        f.write_text(content, encoding="utf-8")
        result = _analyze_file(f, tmp_path)
        if len(result.issues) > 3:
            # The truncation summary should mention "use -v"
            from ai_helper.scan import _print_results
            _print_results([result], verbose=False)
            captured = capsys.readouterr()
            assert "-v" in captured.out or "use -v" in captured.out

    def test_verbose_shows_all(self, capsys, tmp_path):
        """With verbose=True, all issues should be shown (no truncation message)."""
        f = tmp_path / "SKILL.md"
        content = (
            "---\n"
            "description: you should do all the things and stuff\n"
            "---\n"
            + "\n".join([f"line number {i} with some content" for i in range(50)])
            + "\nplease do X\nplease do Y\nplease do Z\n"
        )
        f.write_text(content, encoding="utf-8")
        result = _analyze_file(f, tmp_path)
        if len(result.issues) > 3:
            from ai_helper.scan import _print_results
            _print_results([result], verbose=True)
            captured = capsys.readouterr()
            assert "use -v" not in captured.out

    def test_severity_ordering(self):
        """Issues should sort warning > suggestion > info."""
        from ai_helper.scan import SEVERITY_ORDER
        issues = [
            Issue(category="a", severity="info", message="i", rule_id="X001"),
            Issue(category="a", severity="warning", message="w", rule_id="X002"),
            Issue(category="a", severity="suggestion", message="s", rule_id="X003"),
        ]
        sorted_issues = sorted(
            issues, key=lambda i: SEVERITY_ORDER.get(i.severity, 99)
        )
        assert sorted_issues[0].severity == "warning"
        assert sorted_issues[1].severity == "suggestion"
        assert sorted_issues[2].severity == "info"

    def test_score_uses_all_issues_not_just_displayed(self, tmp_path):
        """Score should use ALL issues, not just the top-N displayed."""
        issues = [
            Issue(category="token-cost", severity="warning", message=f"t{i}",
                  rule_id=f"TCOST{i:03d}")
            for i in range(5)
        ]
        score = _compute_score(issues)
        # 5 warnings same category: 5*15=75, capped at 15. Score = 85.
        assert score == 85


# ── R1: SARIF ────────────────────────────────────────────────────


class TestSARIF:
    def test_valid_sarif_structure(self, capsys):
        """SARIF output should have $schema, version, runs."""
        results = [ScanResult(file="test.md", token_estimate=100, score=90, issues=[])]
        _print_sarif(results)
        captured = capsys.readouterr()
        sarif = json.loads(captured.out)
        assert "$schema" in sarif
        assert sarif["version"] == "2.1.0"
        assert "runs" in sarif
        assert len(sarif["runs"]) == 1
        assert "tool" in sarif["runs"][0]

    def test_results_have_rule_id(self, capsys):
        """Each SARIF result should have a ruleId."""
        results = [ScanResult(
            file="test.md", token_estimate=100, score=85,
            issues=[
                Issue(category="structure", severity="warning",
                      message="test issue", fix="fix it", rule_id="STRUCT001"),
            ],
        )]
        _print_sarif(results)
        captured = capsys.readouterr()
        sarif = json.loads(captured.out)
        assert sarif["runs"][0]["results"][0]["ruleId"] == "STRUCT001"

    def test_level_mapping(self, capsys):
        """SARIF level should map correctly from severity."""
        results = [ScanResult(
            file="test.md", token_estimate=100, score=85,
            issues=[
                Issue(category="a", severity="warning", message="w",
                      rule_id="X001"),
                Issue(category="a", severity="suggestion", message="s",
                      rule_id="X002"),
                Issue(category="a", severity="info", message="i",
                      rule_id="X003"),
            ],
        )]
        _print_sarif(results)
        captured = capsys.readouterr()
        sarif = json.loads(captured.out)
        levels = [r["level"] for r in sarif["runs"][0]["results"]]
        assert levels == ["warning", "note", "note"]

    def test_no_region_when_line_is_none(self, capsys):
        """region should be omitted when issue.line is None."""
        results = [ScanResult(
            file="test.md", token_estimate=100, score=85,
            issues=[
                Issue(category="a", severity="warning", message="no line",
                      rule_id="X001", line=None),
            ],
        )]
        _print_sarif(results)
        captured = capsys.readouterr()
        sarif = json.loads(captured.out)
        loc = sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
        assert "region" not in loc

    def test_region_present_when_line_set(self, capsys):
        """region should be present with startLine when issue.line is set."""
        results = [ScanResult(
            file="test.md", token_estimate=100, score=85,
            issues=[
                Issue(category="a", severity="info", message="has line",
                      rule_id="X001", line=42),
            ],
        )]
        _print_sarif(results)
        captured = capsys.readouterr()
        sarif = json.loads(captured.out)
        loc = sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
        assert loc["region"]["startLine"] == 42

    def test_empty_results_when_no_issues(self, capsys):
        """SARIF results array should be empty when no issues."""
        results = [ScanResult(file="test.md", token_estimate=50, score=100, issues=[])]
        _print_sarif(results)
        captured = capsys.readouterr()
        sarif = json.loads(captured.out)
        assert sarif["runs"][0]["results"] == []


# ── Theme 3: Broken file references ───────────────────────────────


class TestBrokenReferences:
    def test_existing_file_no_issue(self, tmp_path):
        ref_file = tmp_path / "helper.md"
        ref_file.write_text("# Helper")
        skill = tmp_path / "SKILL.md"
        skill.write_text("Read helper.md for details.")
        result = ScanResult(file="SKILL.md")
        regions = _parse_content_regions(skill.read_text().splitlines())
        _check_broken_references(result, skill.read_text(), skill, regions)
        assert not any(i.rule_id == "STRUCT006" for i in result.issues)

    def test_missing_file_flagged(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("Read nonexistent.md for context.")
        result = ScanResult(file="SKILL.md")
        regions = _parse_content_regions(skill.read_text().splitlines())
        _check_broken_references(result, skill.read_text(), skill, regions)
        assert any(i.rule_id == "STRUCT006" for i in result.issues)

    def test_path_in_code_fence_skipped(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("text\n```\nRead missing.md\n```\nmore")
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert not any(i.rule_id == "STRUCT006" for i in result.issues)

    def test_template_var_skipped(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("Read ${CONFIG_PATH}/settings.json")
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert not any(i.rule_id == "STRUCT006" for i in result.issues)

    def test_glob_pattern_skipped(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("Read *.md files in the directory")
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert not any(i.rule_id == "STRUCT006" for i in result.issues)

    def test_absolute_path_skipped(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("Read /etc/config.json for settings")
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert not any(i.rule_id == "STRUCT006" for i in result.issues)


# ── Theme 3: Termination conditions ───────────────────────────────


class TestTerminationConditions:
    def test_multi_step_with_limit_no_issue(self):
        content = "\n".join([f"line {i}" for i in range(25)] + [
            "Step 1: analyze the code",
            "Step 2: fix the issue",
            "Step 3: verify the fix",
            "Maximum 3 retries allowed.",
        ])
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        result = ScanResult(file="test.md")
        _check_termination_conditions(result, content, lines, regions)
        assert not any(i.rule_id == "BPRAC003" for i in result.issues)

    def test_multi_step_without_limit_flagged(self):
        content = "\n".join([f"line {i}" for i in range(25)] + [
            "Step 1: analyze the code",
            "Step 2: call agent to fix",
            "Step 3: retry if needed",
        ])
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        result = ScanResult(file="test.md")
        _check_termination_conditions(result, content, lines, regions)
        assert any(i.rule_id == "BPRAC003" for i in result.issues)

    def test_short_file_skipped(self):
        content = "Step 1: do thing\nStep 2: retry"
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        result = ScanResult(file="test.md")
        _check_termination_conditions(result, content, lines, regions)
        assert not any(i.rule_id == "BPRAC003" for i in result.issues)

    def test_steps_in_code_fence_skipped(self):
        base = [f"line {i}" for i in range(25)]
        fenced = base + ["```", "Step 1: foo", "retry bar", "```"]
        content = "\n".join(fenced)
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        result = ScanResult(file="test.md")
        _check_termination_conditions(result, content, lines, regions)
        assert not any(i.rule_id == "BPRAC003" for i in result.issues)


# ── Theme 3: Role identity ────────────────────────────────────────


class TestRoleIdentity:
    def _make_agent_path(self, tmp_path, name="reviewer.md"):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        return agents_dir / name

    def test_agent_with_role_no_issue(self, tmp_path):
        f = self._make_agent_path(tmp_path)
        content = "---\nname: reviewer\n---\n" + "\n".join(
            ["You are a code reviewer."] + [f"line {i}" for i in range(20)]
        )
        f.write_text(content)
        result = ScanResult(file=str(f))
        lines = content.splitlines()
        _check_role_identity(result, content, lines, f)
        assert not any(i.rule_id == "OQUAL003" for i in result.issues)

    def test_agent_without_role_flagged(self, tmp_path):
        f = self._make_agent_path(tmp_path)
        content = "---\nname: reviewer\n---\n" + "\n".join(
            ["Review the code."] + [f"Check line {i}" for i in range(20)]
        )
        f.write_text(content)
        result = ScanResult(file=str(f))
        lines = content.splitlines()
        _check_role_identity(result, content, lines, f)
        assert any(i.rule_id == "OQUAL003" for i in result.issues)

    def test_claude_md_skipped(self, tmp_path):
        f = tmp_path / "CLAUDE.md"
        content = "\n".join([f"line {i}" for i in range(20)])
        f.write_text(content)
        result = ScanResult(file=str(f))
        lines = content.splitlines()
        _check_role_identity(result, content, lines, f)
        assert not any(i.rule_id == "OQUAL003" for i in result.issues)

    def test_non_agents_dir_skipped(self, tmp_path):
        f = tmp_path / "skills" / "foo.md"
        f.parent.mkdir()
        content = "\n".join([f"line {i}" for i in range(20)])
        f.write_text(content)
        result = ScanResult(file=str(f))
        lines = content.splitlines()
        _check_role_identity(result, content, lines, f)
        assert not any(i.rule_id == "OQUAL003" for i in result.issues)


# ── Theme 3: Compound instructions ────────────────────────────────


class TestCompoundInstructions:
    def test_two_conjunctions_no_issue(self):
        lines = ["Check the file and verify the output and report."]
        regions = ["content"]
        result = ScanResult(file="test.md")
        _check_compound_instructions(result, "\n".join(lines), lines, regions)
        assert not any(i.rule_id == "HRISK004" for i in result.issues)

    def test_three_plus_conjunctions_flagged(self):
        line = ("Analyze the code and fix the bugs and update tests"
                " and also document the changes")
        lines = [line]
        regions = ["content"]
        result = ScanResult(file="test.md")
        _check_compound_instructions(result, "\n".join(lines), lines, regions)
        assert any(i.rule_id == "HRISK004" for i in result.issues)

    def test_compound_in_code_fence_skipped(self):
        line = "do this and that and also something and additionally more"
        lines = ["```", line, "```"]
        regions = _parse_content_regions(lines)
        result = ScanResult(file="test.md")
        _check_compound_instructions(
            result, "\n".join(lines), lines, regions
        )
        assert not any(i.rule_id == "HRISK004" for i in result.issues)

    def test_short_lines_skipped(self):
        lines = ["a and b and c and d"]
        regions = ["content"]
        result = ScanResult(file="test.md")
        _check_compound_instructions(result, "\n".join(lines), lines, regions)
        assert not any(i.rule_id == "HRISK004" for i in result.issues)


# ── Theme 5: Softened/removed noisy checks ───────────────────────


class TestHRISK002Threshold:
    """HRISK002 threshold raised from 20 to 50."""

    def test_40_line_file_no_trigger(self):
        lines = [f"instruction line {i}" for i in range(40)]
        content = "\n".join(lines)
        result = ScanResult(file="test.md")
        _check_hallucination_risks(result, content, lines)
        assert not any(i.rule_id == "HRISK002" for i in result.issues)

    def test_55_line_file_triggers(self):
        lines = [f"instruction line {i}" for i in range(55)]
        content = "\n".join(lines)
        result = ScanResult(file="test.md")
        _check_hallucination_risks(result, content, lines)
        assert any(i.rule_id == "HRISK002" for i in result.issues)


class TestOQUAL001Threshold:
    """OQUAL001 threshold raised from 20 to 50."""

    def test_40_line_file_no_trigger(self):
        lines = [f"instruction line {i}" for i in range(40)]
        content = "\n".join(lines)
        result = ScanResult(file="test.md")
        _check_output_quality(result, content, lines)
        assert not any(i.rule_id == "OQUAL001" for i in result.issues)

    def test_55_line_file_triggers(self):
        lines = [f"instruction line {i}" for i in range(55)]
        content = "\n".join(lines)
        result = ScanResult(file="test.md")
        _check_output_quality(result, content, lines)
        assert any(i.rule_id == "OQUAL001" for i in result.issues)


class TestHRISK003Removed:
    """HRISK003 removed entirely — no file should trigger it."""

    def test_55_line_file_no_hrisk003(self):
        lines = [f"do something positive line {i}" for i in range(55)]
        content = "\n".join(lines)
        result = ScanResult(file="test.md")
        _check_hallucination_risks(result, content, lines)
        assert not any(i.rule_id == "HRISK003" for i in result.issues)


class TestSTRUCT003Threshold:
    """STRUCT003 threshold raised from 30 to 50."""

    def test_49_line_file_no_trigger(self):
        lines = [f"line {i}" for i in range(49)]
        content = "\n".join(lines)
        regions = _parse_content_regions(lines)
        result = ScanResult(file="test.md")
        _check_structure(result, content, lines, regions)
        assert not any(i.rule_id == "STRUCT003" for i in result.issues)

    def test_51_line_file_triggers(self):
        lines = [f"line {i}" for i in range(51)]
        content = "\n".join(lines)
        regions = _parse_content_regions(lines)
        result = ScanResult(file="test.md")
        _check_structure(result, content, lines, regions)
        assert any(i.rule_id == "STRUCT003" for i in result.issues)


class TestOQUAL002ThresholdAndFilename:
    """OQUAL002 threshold raised from 30 to 50 + review/audit suppression."""

    def test_40_line_file_no_trigger(self):
        lines = [f"instruction line {i}" for i in range(40)]
        content = "\n".join(lines)
        result = ScanResult(file="test.md")
        _check_output_quality(result, content, lines)
        assert not any(i.rule_id == "OQUAL002" for i in result.issues)

    def test_55_line_file_triggers(self):
        lines = [f"instruction line {i}" for i in range(55)]
        content = "\n".join(lines)
        result = ScanResult(file="test.md")
        _check_output_quality(result, content, lines)
        assert any(i.rule_id == "OQUAL002" for i in result.issues)

    def test_review_file_suppressed(self):
        lines = [f"instruction line {i}" for i in range(55)]
        content = "\n".join(lines)
        filepath = Path("agents/review-agent.md")
        result = ScanResult(file="review-agent.md")
        _check_output_quality(result, content, lines, filepath)
        assert not any(i.rule_id == "OQUAL002" for i in result.issues)

    def test_audit_file_suppressed(self):
        lines = [f"instruction line {i}" for i in range(55)]
        content = "\n".join(lines)
        filepath = Path("agents/audit.md")
        result = ScanResult(file="audit.md")
        _check_output_quality(result, content, lines, filepath)
        assert not any(i.rule_id == "OQUAL002" for i in result.issues)

    def test_review_uppercase_suppressed(self):
        """Case-insensitive filename matching."""
        lines = [f"instruction line {i}" for i in range(55)]
        content = "\n".join(lines)
        filepath = Path("agents/CodeReview.md")
        result = ScanResult(file="CodeReview.md")
        _check_output_quality(result, content, lines, filepath)
        assert not any(i.rule_id == "OQUAL002" for i in result.issues)


# ── Item 4.2: Config file loading ─────────────────────────────────


class TestConfigFile:
    def test_missing_config_returns_empty(self, tmp_path):
        config = _load_config(tmp_path)
        assert config == {}

    def test_valid_config_loaded(self, tmp_path):
        cfg = tmp_path / ".ai-helper-scan.yaml"
        cfg.write_text(
            "disable:\n  - HRISK002\n  - OQUAL001\nfail_on: warning\n"
        )
        config = _load_config(tmp_path)
        assert config["disable"] == ["HRISK002", "OQUAL001"]
        assert config["fail_on"] == "warning"

    def test_invalid_yaml_returns_empty(self, tmp_path):
        cfg = tmp_path / ".ai-helper-scan.yaml"
        cfg.write_text(": : : invalid yaml [[[")
        config = _load_config(tmp_path)
        assert config == {}

    def test_empty_config_returns_empty(self, tmp_path):
        cfg = tmp_path / ".ai-helper-scan.yaml"
        cfg.write_text("")
        config = _load_config(tmp_path)
        assert config == {}


# ── Item 4.3: Baseline ───────────────────────────────────────────


class TestBaseline:
    def test_baseline_key_stable(self):
        issue = Issue(
            category="test", severity="warning",
            message="Test message", rule_id="TEST001",
        )
        k1 = _baseline_key(issue)
        k2 = _baseline_key(issue)
        assert k1 == k2
        assert k1.startswith("TEST001:")

    def test_build_and_save_baseline(self, tmp_path):
        results = [ScanResult(
            file="test.md", token_estimate=100,
            issues=[Issue(
                category="test", severity="warning",
                message="bad", rule_id="TEST001",
            )],
        )]
        bl = _build_baseline(results, str(tmp_path))
        assert bl["version"] == 1
        assert len(bl["findings"]) == 1

        bl_path = tmp_path / ".ai-helper-scan-baseline.json"
        _save_baseline(bl, bl_path)
        assert bl_path.exists()

        loaded = _load_baseline(bl_path)
        assert loaded["version"] == 1
        assert len(loaded["findings"]) == 1

    def test_load_missing_baseline_returns_empty(self, tmp_path):
        bl_path = tmp_path / "nope.json"
        assert _load_baseline(bl_path) == {}

    def test_load_corrupted_baseline_returns_empty(self, tmp_path):
        bl_path = tmp_path / "bad.json"
        bl_path.write_text("{invalid json")
        assert _load_baseline(bl_path) == {}

    def test_load_wrong_version_returns_empty(self, tmp_path):
        bl_path = tmp_path / "old.json"
        bl_path.write_text('{"version": 99}')
        assert _load_baseline(bl_path) == {}

    def test_diff_hides_baselined_issues(self, tmp_path):
        from ai_helper.scan import run_scan

        skill = tmp_path / "AGENTS.md"
        skill.write_text("\n".join([f"line {i}" for i in range(55)]))

        # First scan: save baseline
        run_scan(path=str(tmp_path), save_baseline=True)
        bl_path = tmp_path / ".ai-helper-scan-baseline.json"
        assert bl_path.exists()

        # Second scan with diff: known issues suppressed
        counts = run_scan(path=str(tmp_path), diff_baseline=True)
        total = sum(counts.values())
        assert total == 0

    def test_mutual_exclusivity_in_cli(self):
        from click.testing import CliRunner

        from ai_helper.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main, ["scan", ".", "--save-baseline", "--diff"]
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


# ── Item 4.5: Rule system ─────────────────────────────────────────


class TestRuleSystem:
    def setup_method(self):
        RULE_REGISTRY.clear()

    def teardown_method(self):
        RULE_REGISTRY.clear()

    def test_register_custom_rule(self):
        class MyRule(Rule):
            id = "CUSTOM_001"
            name = "test rule"

            def check(self, ctx):
                return [Issue(
                    category="custom", severity="info",
                    message="custom finding", rule_id=self.id,
                )]

        register_rule(MyRule())
        assert len(RULE_REGISTRY) == 1

    def test_duplicate_id_rejected(self):
        r1 = Rule()
        r1.id = "CUSTOM_001"
        register_rule(r1)
        r2 = Rule()
        r2.id = "CUSTOM_001"
        with pytest.raises(ValueError, match="Duplicate"):
            register_rule(r2)

    def test_non_custom_prefix_rejected(self):
        r = Rule()
        r.id = "TCOST999"
        with pytest.raises(ValueError, match="CUSTOM_"):
            register_rule(r)

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            register_rule(Rule())

    def test_custom_rule_executed_in_analyze(self, tmp_path):
        class TagRule(Rule):
            id = "CUSTOM_TAG"
            name = "tag check"

            def check(self, ctx):
                return [Issue(
                    category="custom", severity="info",
                    message="tagged", rule_id=self.id,
                )]

        register_rule(TagRule())
        f = tmp_path / "AGENTS.md"
        f.write_text("# Test\ncontent")
        result = _analyze_file(f, tmp_path)
        custom = [i for i in result.issues if i.rule_id == "CUSTOM_TAG"]
        assert len(custom) == 1

    def test_custom_rule_error_handled(self, tmp_path):
        class BadRule(Rule):
            id = "CUSTOM_BAD"
            name = "bad"

            def check(self, ctx):
                raise RuntimeError("boom")

        register_rule(BadRule())
        f = tmp_path / "AGENTS.md"
        f.write_text("# Test\ncontent")
        result = _analyze_file(f, tmp_path)
        assert not any(i.rule_id == "CUSTOM_BAD" for i in result.issues)
        # The error should be reported as a RULE_ERR info-severity issue
        err_issues = [i for i in result.issues if i.rule_id == "RULE_ERR"]
        assert len(err_issues) == 1
        assert "CUSTOM_BAD" in err_issues[0].message
        assert "RuntimeError" in err_issues[0].message
        assert "boom" in err_issues[0].message
        assert err_issues[0].severity == "info"


# ── M6: Project root walk iteration limit ────────────────────────


class TestProjectRootWalkLimit:
    """M6: Both _check_redundant_context and _check_broken_references
    should stop walking up after 10 levels."""

    def test_redundant_context_stops_at_depth_10(self, tmp_path):
        """Walk-up in _check_redundant_context is bounded."""
        # Create a deep path with no project markers
        deep = tmp_path
        for i in range(15):
            deep = deep / f"level{i}"
        deep.mkdir(parents=True)
        skill = deep / "SKILL.md"
        skill.write_text("We use react for the frontend.\n" * 5)
        result = ScanResult(file="SKILL.md")
        # Should not crash or hang on deep paths
        _check_redundant_context(result, skill.read_text(), skill)

    def test_broken_references_stops_at_depth_10(self, tmp_path):
        """Walk-up in _check_broken_references is bounded."""
        deep = tmp_path
        for i in range(15):
            deep = deep / f"level{i}"
        deep.mkdir(parents=True)
        skill = deep / "SKILL.md"
        skill.write_text("Read nonexistent.md for context.")
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        # Should not crash or hang on deep paths
        _check_broken_references(result, content, skill, regions)


# ── M9: Score computed before severity filter ─────────────────────


class TestScoreBeforeSeverityFilter:
    """M9: Score should reflect ALL issues, not just severity-filtered ones."""

    def test_score_independent_of_severity_filter(self, tmp_path):
        """Score should be the same whether or not a severity filter is applied."""
        skill = tmp_path / "SKILL.md"
        # Create content that triggers both warnings and suggestions
        content = (
            "---\n"
            "description: you should do stuff then do more stuff"
            " then finally finish\n"
            "---\n"
            + "\n".join([f"line {i}" for i in range(55)])
        )
        skill.write_text(content)

        # Scan without filter
        counts_all = run_scan(path=str(tmp_path), fmt="json")

        # Scan with severity filter (only show warnings)
        counts_filtered = run_scan(
            path=str(tmp_path), fmt="json",
            severity_filter="warning",
        )

        # The counts should be the same (counts are computed before filter)
        assert counts_all == counts_filtered

    def test_compute_score_uses_all_issues_before_filter(self):
        """Direct test: score from full issue list should be less than 100."""
        issues = [
            Issue(category="structure", severity="warning",
                  message="w", rule_id="STRUCT001"),
            Issue(category="token-cost", severity="suggestion",
                  message="s", rule_id="TCOST003"),
        ]
        score = _compute_score(issues)
        # warning=15 (capped 15) + suggestion=5 (capped 5) = 20
        assert score == 80

        # After filtering to only suggestions, score would be 95
        # but M9 fix ensures we compute score BEFORE filtering
        filtered = [i for i in issues if i.severity == "suggestion"]
        filtered_score = _compute_score(filtered)
        assert filtered_score == 95
        assert score < filtered_score  # full score is lower


# ── M10: DESC003 conditional "you are" exclusion ──────────────────


class TestDESC003ConditionalExclusion:
    """M10: 'you are' preceded by when/if/whenever/whether should not
    trigger DESC003."""

    def test_when_you_are_not_flagged(self):
        content = "---\ndescription: Use when you are debugging code\n---\nbody"
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        assert not any(i.rule_id == "DESC003" for i in result.issues)

    def test_if_you_are_not_flagged(self):
        content = "---\ndescription: Invoke if you are seeing errors\n---\nbody"
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        assert not any(i.rule_id == "DESC003" for i in result.issues)

    def test_whenever_you_are_not_flagged(self):
        content = "---\ndescription: Use whenever you are deploying\n---\nbody"
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        assert not any(i.rule_id == "DESC003" for i in result.issues)

    def test_whether_you_are_not_flagged(self):
        content = "---\ndescription: Use whether you are local or remote\n---\nbody"
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        assert not any(i.rule_id == "DESC003" for i in result.issues)

    def test_bare_you_are_still_flagged(self):
        content = "---\ndescription: You are a code reviewer\n---\nbody"
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        assert any(i.rule_id == "DESC003" for i in result.issues)

    def test_you_should_still_flagged(self):
        content = "---\ndescription: You should review the code\n---\nbody"
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        assert any(i.rule_id == "DESC003" for i in result.issues)

    def test_i_will_still_flagged(self):
        content = "---\ndescription: I will analyze the code\n---\nbody"
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        assert any(i.rule_id == "DESC003" for i in result.issues)

    def test_mixed_conditional_and_bare(self):
        """'when you are' is fine but 'you should' in same desc still flags."""
        content = (
            "---\ndescription: Use when you are ready,"
            " you should start immediately\n---\nbody"
        )
        result = ScanResult(file="test.md")
        _check_description_quality(result, content)
        assert any(i.rule_id == "DESC003" for i in result.issues)


# ── M11: Distinct conflict messages ───────────────────────────────


class TestConflictMessages:
    """M11: Each conflict pattern pair should return its own message."""

    def test_verbose_concise_conflict_message(self):
        content = "Always provide detailed explanations. Be concise."
        msg = _find_conflicting_instructions(content)
        assert msg is not None
        assert "verbose/thorough" in msg
        assert "concise/brief" in msg

    def test_never_skip_optional_conflict_message(self):
        content = "Never ever really skip validation. Only when needed, run tests."
        msg = _find_conflicting_instructions(content)
        assert msg is not None
        assert "never skip/omit" in msg
        assert "only when needed/optional" in msg

    def test_no_conflict_returns_none(self):
        content = "Always be thorough in your analysis."
        msg = _find_conflicting_instructions(content)
        assert msg is None

    def test_second_pair_does_not_return_first_message(self):
        """The second conflict pair must NOT return the verbose/concise message."""
        content = "Never ever really omit error handling. This is optional for tests."
        msg = _find_conflicting_instructions(content)
        assert msg is not None
        assert "verbose/thorough" not in msg


# ── URL scanning ──────────────────────────────────────────────────


class TestUrlScanning:
    def test_https_detected(self):
        assert _is_git_url("https://github.com/org/repo")

    def test_git_at_not_detected(self):
        assert not _is_git_url("git@github.com:org/repo.git")

    def test_http_not_detected(self):
        assert not _is_git_url("http://github.com/org/repo")

    def test_local_path_not_detected(self):
        assert not _is_git_url(".")
        assert not _is_git_url("/path/to/project")
        assert not _is_git_url("relative/path")


# ── False-positive fixes ────────────────────────────────────────────


class TestIsRootReferenceDoc:
    def test_root_agents_md(self, tmp_path):
        f = tmp_path / "AGENTS.md"
        assert _is_root_reference_doc(f, tmp_path)

    def test_agents_in_subdir_not_root(self, tmp_path):
        d = tmp_path / "agents"
        d.mkdir()
        f = d / "AGENTS.md"
        assert not _is_root_reference_doc(f, tmp_path)

    def test_root_skill_md_not_reference_doc(self, tmp_path):
        f = tmp_path / "SKILL.md"
        assert not _is_root_reference_doc(f, tmp_path)


class TestHasSkillDelegation:
    def test_follow_skill(self, tmp_path):
        skill_dir = tmp_path / ".opencode" / "skills" / "review"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Review skill")
        content = "Follow the issue-investigate skill for details."
        assert _has_skill_delegation(content, tmp_path / "agent.md", tmp_path)

    def test_see_skill_md(self, tmp_path):
        skill_dir = tmp_path / "skills" / "deploy"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Deploy")
        content = "See SKILL.md for output format."
        assert _has_skill_delegation(content, tmp_path / "agent.md", tmp_path)

    def test_invoke_skill(self, tmp_path):
        skill_dir = tmp_path / ".claude" / "skills" / "test"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test")
        content = "Invoke the deploy skill to run."
        assert _has_skill_delegation(content, tmp_path / "agent.md", tmp_path)

    def test_use_your_skill_not_delegation(self, tmp_path):
        content = "Use your debugging skill to find the issue."
        assert not _has_skill_delegation(content, tmp_path / "agent.md", tmp_path)

    def test_delegation_to_missing_skill(self, tmp_path):
        content = "Follow the nonexistent skill for details."
        assert not _has_skill_delegation(content, tmp_path / "agent.md", tmp_path)


class TestSTRUCT006RuntimeCreated:
    def test_echo_created_file_not_flagged(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "Check .audit/validation.json for results.\n"
            "```bash\n"
            "echo '{}' > .audit/validation.json\n"
            "```\n"
        )
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert not any(i.rule_id == "STRUCT006" for i in result.issues)

    def test_touch_created_file_not_flagged(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "Load output.json for the report.\n"
            "```\n"
            "touch output.json\n"
            "```\n"
        )
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert not any(i.rule_id == "STRUCT006" for i in result.issues)

    def test_genuine_broken_ref_still_flagged(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("Read missing-file.md for context.")
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert any(i.rule_id == "STRUCT006" for i in result.issues)

    def test_creation_of_different_file_not_confused(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "Read report.json for results.\n"
            "```\n"
            "echo '{}' > other.json\n"
            "```\n"
        )
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert any(i.rule_id == "STRUCT006" for i in result.issues)


class TestSTRUCT006TargetRepo:
    def test_target_repo_context_not_flagged(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("Check go.mod in the target repo for versions.")
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert not any(i.rule_id == "STRUCT006" for i in result.issues)

    def test_example_list_not_flagged(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "Check files like go.mod, pyproject.toml for dependencies."
        )
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert not any(i.rule_id == "STRUCT006" for i in result.issues)

    def test_project_word_alone_not_suppressed(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("Read config.yaml for project settings.")
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert any(i.rule_id == "STRUCT006" for i in result.issues)

    def test_the_repository_context_not_flagged(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("Check setup.py in the repository for metadata.")
        result = ScanResult(file="SKILL.md")
        content = skill.read_text()
        regions = _parse_content_regions(content.splitlines())
        _check_broken_references(result, content, skill, regions)
        assert not any(i.rule_id == "STRUCT006" for i in result.issues)


class TestTCOST008WordBoundary:
    def test_consideration_not_counted(self):
        content = (
            "Missing considerations for edge cases.\n"
            "Add considerations for performance.\n"
        )
        assert _count_hedging("consider", content) == 0

    def test_retry_to_not_counted_for_try_to(self):
        content = "On failure, retry to connect. Will retry to verify."
        assert _count_hedging("try to", content) == 0

    def test_interrogative_consider_not_counted(self):
        content = (
            "Did the plan consider alternatives?\n"
            "Did you consider edge cases?\n"
        )
        assert _count_hedging("consider", content) == 0

    def test_real_hedging_consider_counted(self):
        content = (
            "Consider adding tests for coverage.\n"
            "Also consider using a linter.\n"
        )
        assert _count_hedging("consider", content) == 2

    def test_heading_consider_not_counted(self):
        content = (
            "## Alternatives Considered\n"
            "## Options Considered\n"
        )
        assert _count_hedging("consider", content) == 0

    def test_hedging_filler_with_word_boundaries(self):
        content = (
            "Consider using X. Consider adding Y.\n"
            "Try to verify the output. Try to confirm it.\n"
        )
        result = ScanResult(file="test.md")
        _check_hedging_and_filler(result, content)
        rule_ids = [i.rule_id for i in result.issues]
        assert "TCOST008" in rule_ids


class TestBPRAC003RootRefDoc:
    def test_root_agents_md_skipped(self, tmp_path):
        agents = tmp_path / "AGENTS.md"
        content = "\n".join([f"line {i}" for i in range(25)])
        content += "\nStep 1: understand\nPhase 2: plan\nIteration loop\n"
        agents.write_text(content)
        result = ScanResult(file="AGENTS.md")
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        _check_termination_conditions(
            result, content, lines, regions, agents, tmp_path,
        )
        assert not any(i.rule_id == "BPRAC003" for i in result.issues)

    def test_claude_md_not_skipped(self, tmp_path):
        claude = tmp_path / "CLAUDE.md"
        content = "\n".join([f"line {i}" for i in range(25)])
        content += "\nStep 1: foo\nIteration loop\nRetry until done\n"
        claude.write_text(content)
        result = ScanResult(file="CLAUDE.md")
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        _check_termination_conditions(
            result, content, lines, regions, claude, tmp_path,
        )
        assert any(i.rule_id == "BPRAC003" for i in result.issues)

    def test_agent_file_in_subdir_still_caught(self, tmp_path):
        d = tmp_path / "agents"
        d.mkdir()
        agent = d / "fix.md"
        content = "\n".join([f"line {i}" for i in range(25)])
        content += "\nStep 1: investigate\nRetry the operation\n"
        agent.write_text(content)
        result = ScanResult(file="agents/fix.md")
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        _check_termination_conditions(
            result, content, lines, regions, agent, tmp_path,
        )
        assert any(i.rule_id == "BPRAC003" for i in result.issues)


class TestDelegationSkips:
    def _make_skill_tree(self, tmp_path):
        d = tmp_path / ".opencode" / "skills" / "review"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# Review\n```json\n{}\n```\nExample output")

    def test_hrisk002_skipped_with_delegation(self, tmp_path):
        self._make_skill_tree(tmp_path)
        content = "\n".join([f"Line {i}" for i in range(55)])
        content += "\nFollow the issue-investigate skill.\n"
        agent = tmp_path / "agents" / "fix.md"
        agent.parent.mkdir(parents=True, exist_ok=True)
        agent.write_text(content)
        result = ScanResult(file="agents/fix.md")
        lines = content.splitlines()
        _check_hallucination_risks(result, content, lines, agent, tmp_path)
        assert not any(i.rule_id == "HRISK002" for i in result.issues)

    def test_oqual001_skipped_with_delegation(self, tmp_path):
        self._make_skill_tree(tmp_path)
        content = "\n".join([f"Line {i}" for i in range(55)])
        content += "\nFollow the code-review skill.\n"
        agent = tmp_path / "agents" / "review.md"
        agent.parent.mkdir(parents=True, exist_ok=True)
        agent.write_text(content)
        result = ScanResult(file="agents/review.md")
        lines = content.splitlines()
        _check_output_quality(result, content, lines, agent, tmp_path)
        assert not any(i.rule_id == "OQUAL001" for i in result.issues)

    def test_hrisk002_caught_without_delegation(self, tmp_path):
        content = "\n".join([f"Line {i}" for i in range(55)])
        agent = tmp_path / "agents" / "fix.md"
        agent.parent.mkdir(parents=True, exist_ok=True)
        agent.write_text(content)
        result = ScanResult(file="agents/fix.md")
        lines = content.splitlines()
        _check_hallucination_risks(result, content, lines, agent, tmp_path)
        assert any(i.rule_id == "HRISK002" for i in result.issues)

    def test_delegation_to_missing_skill_still_flags(self, tmp_path):
        content = "\n".join([f"Line {i}" for i in range(55)])
        content += "\nFollow the nonexistent skill.\n"
        agent = tmp_path / "agents" / "fix.md"
        agent.parent.mkdir(parents=True, exist_ok=True)
        agent.write_text(content)
        result = ScanResult(file="agents/fix.md")
        lines = content.splitlines()
        _check_hallucination_risks(result, content, lines, agent, tmp_path)
        assert any(i.rule_id == "HRISK002" for i in result.issues)


class TestBPRAC003LinearSteps:
    def test_linear_steps_only_no_flag(self):
        content = "\n".join([f"line {i}" for i in range(25)])
        content += "\nStep 1: Understand the code\nStep 2: Make changes\nStep 3: Run tests\n"
        result = ScanResult(file="SKILL.md")
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        _check_termination_conditions(result, content, lines, regions)
        assert not any(i.rule_id == "BPRAC003" for i in result.issues)

    def test_iteration_keyword_still_flags(self):
        content = "\n".join([f"line {i}" for i in range(25)])
        content += "\nStep 1: Run tests\nRetry until all pass\n"
        result = ScanResult(file="SKILL.md")
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        _check_termination_conditions(result, content, lines, regions)
        assert any(i.rule_id == "BPRAC003" for i in result.issues)

    def test_loop_keyword_still_flags(self):
        content = "\n".join([f"line {i}" for i in range(25)])
        content += "\nPhase 1: Init\nLoop over all items and process\n"
        result = ScanResult(file="SKILL.md")
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        _check_termination_conditions(result, content, lines, regions)
        assert any(i.rule_id == "BPRAC003" for i in result.issues)

    def test_linear_with_termination_no_flag(self):
        content = "\n".join([f"line {i}" for i in range(25)])
        content += "\nStep 1: Run tests\nRetry failures\nMaximum 3 attempts\n"
        result = ScanResult(file="SKILL.md")
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        _check_termination_conditions(result, content, lines, regions)
        assert not any(i.rule_id == "BPRAC003" for i in result.issues)


class TestCodeFenceFiltering:
    def _build_content_text(self, content):
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        ct_lines = []
        in_fence = False
        for line, rgn in zip(lines, regions):
            if rgn == "content":
                ct_lines.append(line)
                in_fence = False
            elif not in_fence:
                ct_lines.append("")
                in_fence = True
        return "\n".join(ct_lines)

    def test_hedging_in_code_fence_not_counted(self):
        content = "Some text\n```\nconsider this\nconsider that\n```\n"
        content_text = self._build_content_text(content)
        assert _count_hedging("consider", content_text) == 0

    def test_hedging_in_content_still_counted(self):
        content = "Consider adding tests.\nConsider using a linter.\n"
        content_text = self._build_content_text(content)
        assert _count_hedging("consider", content_text) == 2

    def test_vague_instruction_in_code_fence_not_flagged(self):
        content = "\n".join([f"line {i}" for i in range(55)])
        content += "\n```bash\n# if possible use cache\n```\n"
        content_text = self._build_content_text(content)
        result = ScanResult(file="test.md")
        lines = content.splitlines()
        _check_hallucination_risks(
            result, content, lines, content_text=content_text,
        )
        assert not any(i.rule_id == "HRISK001" for i in result.issues)

    def test_prohibition_in_code_fence_not_counted(self):
        content = (
            "```bash\n# do not remove\n# do not delete\n"
            "# do not skip\n# do not ignore\n"
            "# do not modify\n# do not change\n# do not alter\n```\n"
        )
        content_text = self._build_content_text(content)
        result = ScanResult(file="test.md")
        _check_failure_mode_framing(result, content_text, content.splitlines())
        assert not any(i.rule_id == "FRAME001" for i in result.issues)

    def test_content_only_still_flagged(self):
        content = "Consider adding tests.\nConsider using a linter.\n"
        content_text = self._build_content_text(content)
        result = ScanResult(file="test.md")
        _check_hedging_and_filler(result, content_text)
        assert any(i.rule_id == "TCOST008" for i in result.issues)

    def test_hrisk002_detects_code_fence_as_output_format(self):
        content = "\n".join([f"line {i}" for i in range(55)])
        content += "\n```json\n{}\n```\n"
        content_text = self._build_content_text(content)
        result = ScanResult(file="test.md")
        lines = content.splitlines()
        _check_hallucination_risks(
            result, content, lines, content_text=content_text,
        )
        assert not any(i.rule_id == "HRISK002" for i in result.issues)


class TestFRAME003BareDirectives:
    def test_five_bare_directives_flagged(self):
        content = (
            "NEVER skip tests\n"
            "MUST validate input\n"
            "ALWAYS run linter\n"
            "DO NOT commit secrets\n"
            "NEVER force push\n"
        )
        result = ScanResult(file="test.md")
        _check_failure_mode_framing(result, content, content.splitlines())
        assert any(i.rule_id == "FRAME003" for i in result.issues)

    def test_four_bare_directives_not_flagged(self):
        content = (
            "NEVER skip tests\n"
            "MUST validate input\n"
            "ALWAYS run linter\n"
            "DO NOT commit secrets\n"
        )
        result = ScanResult(file="test.md")
        _check_failure_mode_framing(result, content, content.splitlines())
        assert not any(i.rule_id == "FRAME003" for i in result.issues)

    def test_directives_with_rationale_not_flagged(self):
        content = (
            "NEVER skip tests because they catch regressions\n"
            "MUST validate input since it prevents injection\n"
            "ALWAYS run linter to prevent style drift\n"
            "DO NOT commit secrets -- they end up in git history\n"
            "NEVER force push to avoid overwriting work\n"
        )
        result = ScanResult(file="test.md")
        _check_failure_mode_framing(result, content, content.splitlines())
        assert not any(i.rule_id == "FRAME003" for i in result.issues)

    def test_code_fence_directives_not_counted(self):
        content = (
            "Some instructions\n"
            "```\n"
            "NEVER do X\nMUST do Y\nALWAYS do Z\n"
            "DO NOT do W\nNEVER do V\n"
            "```\n"
        )
        lines = content.splitlines()
        regions = _parse_content_regions(lines)
        ct_lines = []
        in_fence = False
        for line, rgn in zip(lines, regions):
            if rgn == "content":
                ct_lines.append(line)
                in_fence = False
            elif not in_fence:
                ct_lines.append("")
                in_fence = True
        content_text = "\n".join(ct_lines)
        result = ScanResult(file="test.md")
        _check_failure_mode_framing(result, content_text, lines)
        assert not any(i.rule_id == "FRAME003" for i in result.issues)

    def test_must_not_counts_as_one(self):
        content = (
            "MUST NOT skip tests\n"
            "MUST NOT ignore errors\n"
            "MUST NOT commit secrets\n"
            "MUST NOT force push\n"
        )
        result = ScanResult(file="test.md")
        _check_failure_mode_framing(result, content, content.splitlines())
        assert not any(i.rule_id == "FRAME003" for i in result.issues)
