"""Unit tests for scan.py — focused on the 5 bug fixes."""

import tempfile
from pathlib import Path

import pytest

from ai_helper.scan import (
    ScanResult,
    Issue,
    _check_description_quality,
    _check_structure,
    _check_token_waste,
    _find_duplicate_instructions,
    _parse_content_regions,
    _analyze_file,
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
        base = [f"line {i}" for i in range(35)]
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
        lines = ["## Section"] + [f"line {i}" for i in range(35)]
        content = "\n".join(lines)
        regions = _parse_content_regions(lines)
        result = ScanResult(file="test.md")
        _check_structure(result, content, lines, regions)
        assert not any(
            "no markdown headers" in i.message for i in result.issues
        )

    def test_shebang_not_header(self):
        lines = ["#!/bin/bash"] + [f"line {i}" for i in range(35)]
        content = "\n".join(lines)
        regions = _parse_content_regions(lines)
        result = ScanResult(file="test.md")
        _check_structure(result, content, lines, regions)
        assert any(
            "no markdown headers" in i.message for i in result.issues
        )
