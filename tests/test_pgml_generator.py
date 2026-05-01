"""Tests for the PGML generator module."""

from __future__ import annotations

import pytest

from src.pgml_generator import PGMLGenerator, PGMLQuestion


class TestPGMLQuestion:
    def test_defaults(self):
        q = PGMLQuestion(title="Test")
        assert q.title == "Test"
        assert q.macros == [
            "PGstandard.pl",
            "MathObjects.pl",
            "PGML.pl",
            "PGcourse.pl",
        ]
        assert q.context == "Numeric"
        assert q.hints == []
        assert q.variables == []


class TestPGMLGenerator:
    def _make_simple_question(self) -> PGMLQuestion:
        return PGMLQuestion(
            title="Addition",
            setup_code="$a = random(2, 10, 1);\n$b = random(2, 10, 1);\n$ans = Compute(\"$a + $b\");",
            problem_text="Compute [`[$a] + [$b]`].",
            answer_expression="$a + $b",
            solution_text="The answer is [`[$a] + [$b] = [$ans]`].",
        )

    def test_generate_returns_string(self):
        gen = PGMLGenerator()
        q = self._make_simple_question()
        source = gen.generate(q)
        assert isinstance(source, str)
        assert len(source) > 0

    def test_contains_document_markers(self):
        gen = PGMLGenerator()
        source = gen.generate(self._make_simple_question())
        assert "DOCUMENT();" in source
        assert "ENDDOCUMENT();" in source

    def test_contains_load_macros(self):
        gen = PGMLGenerator()
        source = gen.generate(self._make_simple_question())
        assert "loadMacros(" in source
        assert '"PGstandard.pl"' in source
        assert '"MathObjects.pl"' in source
        assert '"PGML.pl"' in source

    def test_contains_pgml_block(self):
        gen = PGMLGenerator()
        source = gen.generate(self._make_simple_question())
        assert "BEGIN_PGML" in source
        assert "END_PGML" in source

    def test_contains_problem_text(self):
        gen = PGMLGenerator()
        source = gen.generate(self._make_simple_question())
        assert "Compute" in source

    def test_contains_answer_blank(self):
        gen = PGMLGenerator()
        source = gen.generate(self._make_simple_question())
        assert "[__________]" in source
        assert "Compute(" in source

    def test_contains_solution(self):
        gen = PGMLGenerator()
        source = gen.generate(self._make_simple_question())
        assert "BEGIN_PGML_SOLUTION" in source
        assert "END_PGML_SOLUTION" in source

    def test_no_solution_when_empty(self):
        gen = PGMLGenerator()
        q = PGMLQuestion(
            title="No Solution",
            problem_text="What is 1+1?",
            answer_expression="2",
        )
        source = gen.generate(q)
        assert "BEGIN_PGML_SOLUTION" not in source

    def test_hints_included_when_provided(self):
        gen = PGMLGenerator()
        q = PGMLQuestion(
            title="With Hint",
            problem_text="Solve for x.",
            answer_expression="3",
            hints=["Try substituting values."],
        )
        source = gen.generate(q)
        assert "BEGIN_PGML_HINT" in source
        assert "END_PGML_HINT" in source
        assert "Try substituting values." in source

    def test_no_hints_block_when_empty(self):
        gen = PGMLGenerator()
        q = PGMLQuestion(title="No Hint", problem_text="Simple problem.", answer_expression="1")
        source = gen.generate(q)
        assert "BEGIN_PGML_HINT" not in source

    def test_context_set(self):
        gen = PGMLGenerator()
        q = PGMLQuestion(title="Vector", problem_text="Find the vector.", context="Vector")
        source = gen.generate(q)
        assert 'Context("Vector")' in source

    def test_ends_with_newline(self):
        gen = PGMLGenerator()
        source = gen.generate(self._make_simple_question())
        assert source.endswith("\n")

    def test_custom_macros(self):
        gen = PGMLGenerator()
        q = PGMLQuestion(
            title="Custom",
            problem_text="Problem.",
            macros=["PGstandard.pl", "PGML.pl", "parserMultiAnswer.pl"],
        )
        source = gen.generate(q)
        assert '"parserMultiAnswer.pl"' in source

    def test_no_answer_blank_when_expression_empty(self):
        gen = PGMLGenerator()
        q = PGMLQuestion(title="No Answer", problem_text="Describe something.")
        source = gen.generate(q)
        assert "[__________]" not in source


class TestPGMLGeneratorValidate:
    def test_valid_source_no_issues(self):
        gen = PGMLGenerator()
        source = gen.generate(
            PGMLQuestion(
                title="Valid",
                problem_text="Compute 2+2.",
                answer_expression="4",
                solution_text="4",
            )
        )
        issues = gen.validate_pgml(source)
        assert issues == []

    def test_missing_document(self):
        issues = PGMLGenerator.validate_pgml("loadMacros(); BEGIN_PGML\nfoo\nEND_PGML\nENDDOCUMENT();")
        assert any("DOCUMENT" in i for i in issues)

    def test_missing_enddocument(self):
        issues = PGMLGenerator.validate_pgml("DOCUMENT();\nloadMacros();\nBEGIN_PGML\nfoo\nEND_PGML")
        assert any("ENDDOCUMENT" in i for i in issues)

    def test_missing_begin_pgml(self):
        issues = PGMLGenerator.validate_pgml("DOCUMENT();\nloadMacros();\nEND_PGML\nENDDOCUMENT();")
        assert any("BEGIN_PGML" in i for i in issues)

    def test_unbalanced_pgml_blocks(self):
        source = "DOCUMENT();\nloadMacros();\nBEGIN_PGML\nfoo\nEND_PGML\nBEGIN_PGML\nbar\nENDDOCUMENT();"
        issues = PGMLGenerator.validate_pgml(source)
        assert any("Unbalanced" in i for i in issues)
