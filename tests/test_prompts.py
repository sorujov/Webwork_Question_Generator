"""Tests for the prompt builder module."""

from __future__ import annotations

import pytest

from src.prompts import (
    PROBLEM_DELIMITER,
    Prompt,
    build_multi_question_prompt,
    build_question_prompt,
)


class TestBuildQuestionPrompt:
    def test_returns_prompt_object(self):
        p = build_question_prompt("Some section text about limits.")
        assert isinstance(p, Prompt)

    def test_system_message_non_empty(self):
        p = build_question_prompt("text")
        assert len(p.system) > 0

    def test_user_message_contains_section_text(self):
        p = build_question_prompt("limits and derivatives")
        assert "limits and derivatives" in p.user

    def test_difficulty_in_user_message(self):
        p = build_question_prompt("text", difficulty="hard")
        assert "hard" in p.user

    def test_question_type_in_user_message(self):
        p = build_question_prompt("text", question_type="conceptual")
        assert "conceptual" in p.user

    def test_topic_hint_included(self):
        p = build_question_prompt("text", topic_hint="integration by parts")
        assert "integration by parts" in p.user

    def test_no_topic_hint_by_default(self):
        p = build_question_prompt("text")
        assert "focus on" not in p.user.lower() or "Specifically" not in p.user


class TestBuildMultiQuestionPrompt:
    def test_returns_prompt_object(self):
        p = build_multi_question_prompt("Chapter summary", num_questions=3)
        assert isinstance(p, Prompt)

    def test_user_message_contains_num_questions(self):
        p = build_multi_question_prompt("Chapter summary", num_questions=7)
        assert "7" in p.user

    def test_user_message_contains_delimiter(self):
        p = build_multi_question_prompt("Summary", num_questions=2)
        assert PROBLEM_DELIMITER in p.user

    def test_difficulty_in_user_message(self):
        p = build_multi_question_prompt("Summary", difficulty="easy")
        assert "easy" in p.user

    def test_chapter_summary_in_user_message(self):
        p = build_multi_question_prompt("This is about matrices", num_questions=2)
        assert "matrices" in p.user


class TestProblemDelimiter:
    def test_delimiter_is_string(self):
        assert isinstance(PROBLEM_DELIMITER, str)
        assert len(PROBLEM_DELIMITER) > 0
