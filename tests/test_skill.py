"""Tests for the main skill module (generate_questions).

The OpenAI API is mocked so these tests run without a real API key.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.skill import GeneratedQuestion, _clean_pgml, _split_problems, generate_questions


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_CHAPTER = """\
# Calculus I

## Limits

The limit of a function describes the value the function approaches as the
input approaches a particular point.

## Derivatives

The derivative measures the rate of change of a function.
"""

VALID_PG = """\
DOCUMENT();

loadMacros(
    "PGstandard.pl",
    "MathObjects.pl",
    "PGML.pl",
    "PGcourse.pl"
);

TEXT(beginproblem());
Context("Numeric");

$a = random(2, 10, 1);
$answer = Compute("$a * $a");

BEGIN_PGML
Find [`[$a]^2`].

[__________]{$answer}
END_PGML

BEGIN_PGML_SOLUTION
[`[$a]^2 = [$answer]`]
END_PGML_SOLUTION

ENDDOCUMENT();
"""


def _mock_openai_client(response_text: str):
    """Return a mock openai.OpenAI client that returns *response_text*."""
    choice = MagicMock()
    choice.message.content = response_text
    completion = MagicMock()
    completion.choices = [choice]

    client = MagicMock()
    client.chat.completions.create.return_value = completion
    return client


# ---------------------------------------------------------------------------
# Tests for generate_questions
# ---------------------------------------------------------------------------


class TestGenerateQuestions:
    def test_raises_on_zero_questions(self):
        with pytest.raises(ValueError, match="num_questions"):
            generate_questions("some text", num_questions=0, api_key="fake")

    def test_raises_on_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="API key"):
            generate_questions("some text", num_questions=1)

    def test_raises_on_invalid_strategy(self):
        with pytest.raises(ValueError, match="strategy"):
            generate_questions("text", num_questions=1, api_key="k", strategy="bad")

    def test_returns_list_of_generated_questions(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Build two problems separated by the delimiter
        from src.prompts import PROBLEM_DELIMITER
        response = f"{VALID_PG}\n{PROBLEM_DELIMITER}\n{VALID_PG}"

        mock_client = _mock_openai_client(response)
        import src.skill as skill_mod
        monkeypatch.setattr(skill_mod.openai, "OpenAI", lambda **kw: mock_client)
        result = generate_questions(
            chapter_text=SAMPLE_CHAPTER,
            num_questions=2,
            api_key="fake-key",
            strategy="chapter",
        )

        assert isinstance(result, list)
        assert len(result) == 2
        for q in result:
            assert isinstance(q, GeneratedQuestion)
            assert q.filename.endswith(".pg")
            assert "DOCUMENT();" in q.pgml_source

    def test_filenames_use_base_prefix(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from src.prompts import PROBLEM_DELIMITER
        response = f"{VALID_PG}\n{PROBLEM_DELIMITER}\n{VALID_PG}"

        mock_client = _mock_openai_client(response)
        import src.skill as skill_mod
        monkeypatch.setattr(skill_mod.openai, "OpenAI", lambda **kw: mock_client)
        result = generate_questions(
            chapter_text=SAMPLE_CHAPTER,
            num_questions=2,
            api_key="fake-key",
            base_filename="hw1",
        )

        assert result[0].filename == "hw1_01.pg"
        assert result[1].filename == "hw1_02.pg"

    def test_section_strategy(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        mock_client = _mock_openai_client(VALID_PG)
        import src.skill as skill_mod
        monkeypatch.setattr(skill_mod.openai, "OpenAI", lambda **kw: mock_client)
        result = generate_questions(
            chapter_text=SAMPLE_CHAPTER,
            num_questions=3,
            api_key="fake-key",
            strategy="section",
        )

        assert len(result) == 3

    def test_validation_warnings_attached(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Return source missing ENDDOCUMENT
        bad_pg = VALID_PG.replace("ENDDOCUMENT();", "")
        mock_client = _mock_openai_client(bad_pg)
        import src.skill as skill_mod
        monkeypatch.setattr(skill_mod.openai, "OpenAI", lambda **kw: mock_client)
        result = generate_questions(
            chapter_text=SAMPLE_CHAPTER,
            num_questions=1,
            api_key="fake-key",
            strategy="chapter",
        )

        assert result[0].validation_warnings  # should have at least one warning

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        mock_client = _mock_openai_client(VALID_PG)
        import src.skill as skill_mod
        monkeypatch.setattr(skill_mod.openai, "OpenAI", lambda **kw: mock_client)
        result = generate_questions(
            chapter_text=SAMPLE_CHAPTER,
            num_questions=1,
            strategy="chapter",
        )
        # Should not raise; key is read from env
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Tests for internal helpers
# ---------------------------------------------------------------------------


class TestSplitProblems:
    def test_splits_on_delimiter(self):
        from src.prompts import PROBLEM_DELIMITER
        text = f"problem one\n{PROBLEM_DELIMITER}\nproblem two"
        parts = _split_problems(text, expected=2)
        assert len(parts) == 2
        assert parts[0] == "problem one"
        assert parts[1] == "problem two"

    def test_single_problem_no_delimiter(self):
        parts = _split_problems("just one problem", expected=1)
        assert len(parts) == 1
        assert parts[0] == "just one problem"

    def test_empty_sections_ignored(self):
        from src.prompts import PROBLEM_DELIMITER
        text = f"   \n{PROBLEM_DELIMITER}\nproblem text"
        parts = _split_problems(text, expected=1)
        assert len(parts) == 1
        assert parts[0] == "problem text"


class TestCleanPgml:
    def test_strips_perl_fence(self):
        fenced = "```perl\nDOCUMENT();\nENDDOCUMENT();\n```"
        result = _clean_pgml(fenced)
        assert "```" not in result
        assert "DOCUMENT();" in result

    def test_strips_plain_fence(self):
        fenced = "```\nDOCUMENT();\nENDDOCUMENT();\n```"
        result = _clean_pgml(fenced)
        assert "```" not in result

    def test_no_fence_unchanged(self):
        plain = "DOCUMENT();\nENDDOCUMENT();"
        result = _clean_pgml(plain)
        assert "DOCUMENT();" in result
        assert "ENDDOCUMENT();" in result

    def test_always_ends_with_newline(self):
        result = _clean_pgml("DOCUMENT();")
        assert result.endswith("\n")
