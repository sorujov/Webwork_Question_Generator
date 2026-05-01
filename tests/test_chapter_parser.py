"""Tests for the chapter parser module."""

from __future__ import annotations

import pytest

from src.chapter_parser import ChapterParser, ChapterSection, ParsedChapter


SIMPLE_CHAPTER = """\
# Derivatives

## Definition of the Derivative

The derivative of a function f at a point x is defined as the limit of the
difference quotient as h approaches 0.

## Rules of Differentiation

The power rule states that if f(x) = x^n, then f'(x) = n*x^(n-1).
The product rule and chain rule extend this.

## Applications

Derivatives can be used to find the slope of a tangent line and to optimise
functions.
"""

NUMBERED_CHAPTER = """\
2. Linear Algebra

2.1 Vectors

A vector is a quantity with both magnitude and direction.

2.2 Matrices

A matrix is a rectangular array of numbers.
"""

PLAIN_CHAPTER = """\
This is a chapter about calculus. It covers limits, derivatives,
and integrals. Many examples are included throughout.
"""


class TestChapterParser:
    def test_parses_markdown_headings(self):
        parser = ChapterParser()
        result = parser.parse(SIMPLE_CHAPTER)
        assert isinstance(result, ParsedChapter)
        assert len(result.sections) >= 3

    def test_extracts_title(self):
        parser = ChapterParser()
        result = parser.parse(SIMPLE_CHAPTER)
        assert result.title == "Derivatives"

    def test_section_headings(self):
        parser = ChapterParser()
        result = parser.parse(SIMPLE_CHAPTER)
        headings = [s.heading for s in result.sections]
        assert "Definition of the Derivative" in headings
        assert "Rules of Differentiation" in headings
        assert "Applications" in headings

    def test_section_body_non_empty(self):
        parser = ChapterParser()
        result = parser.parse(SIMPLE_CHAPTER)
        for sec in result.sections:
            assert sec.body.strip(), f"Section '{sec.heading}' has empty body"

    def test_parses_numbered_headings(self):
        parser = ChapterParser()
        result = parser.parse(NUMBERED_CHAPTER, chapter_title="Linear Algebra")
        headings = [s.heading for s in result.sections]
        # At least one numbered section should be detected
        assert len(result.sections) >= 1

    def test_plain_text_becomes_single_section(self):
        parser = ChapterParser()
        result = parser.parse(PLAIN_CHAPTER, chapter_title="Calculus")
        assert len(result.sections) == 1
        assert "calculus" in result.sections[0].body.lower()

    def test_fallback_title(self):
        parser = ChapterParser()
        result = parser.parse(PLAIN_CHAPTER, chapter_title="My Chapter")
        assert result.title == "My Chapter"

    def test_raw_text_preserved(self):
        parser = ChapterParser()
        result = parser.parse(SIMPLE_CHAPTER)
        assert result.raw_text == SIMPLE_CHAPTER

    def test_empty_chapter_still_parses(self):
        parser = ChapterParser()
        result = parser.parse("", chapter_title="Empty")
        assert isinstance(result, ParsedChapter)


class TestChapterSection:
    def test_summary_truncation(self):
        long_body = "word " * 500
        sec = ChapterSection(heading="Long Section", body=long_body)
        summary = sec.summary(max_chars=100)
        assert len(summary) <= 120  # heading + newlines + truncated body
        assert "…" in summary

    def test_summary_no_truncation_for_short_text(self):
        sec = ChapterSection(heading="Short", body="Small text.")
        summary = sec.summary(max_chars=500)
        assert "Small text." in summary

    def test_summary_includes_heading(self):
        sec = ChapterSection(heading="My Heading", body="Body text.")
        summary = sec.summary()
        assert "## My Heading" in summary


class TestParsedChapter:
    def test_full_summary_contains_title(self):
        parser = ChapterParser()
        result = parser.parse(SIMPLE_CHAPTER)
        summary = result.full_summary()
        assert "# Derivatives" in summary

    def test_full_summary_contains_section_headings(self):
        parser = ChapterParser()
        result = parser.parse(SIMPLE_CHAPTER)
        summary = result.full_summary()
        assert "Definition of the Derivative" in summary
