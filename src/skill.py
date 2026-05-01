"""Main skill entry point for the WeBWorK Question Generator.

Usage example::

    from src.skill import generate_questions

    questions = generate_questions(
        chapter_text="...",
        num_questions=5,
        api_key="sk-...",
    )
    for q in questions:
        print(q.filename)
        print(q.pgml_source)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

try:
    import openai as openai  # noqa: PLC0414  (re-export for monkeypatching in tests)
except ImportError:  # pragma: no cover
    openai = None  # type: ignore[assignment]

from .chapter_parser import ChapterParser, ParsedChapter
from .pgml_generator import PGMLGenerator
from .prompts import (
    PROBLEM_DELIMITER,
    build_multi_question_prompt,
    build_question_prompt,
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class GeneratedQuestion:
    """A single generated WeBWorK PGML problem."""

    index: int
    filename: str
    pgml_source: str
    validation_warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_questions(
    chapter_text: str,
    num_questions: int = 5,
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
    difficulty: str = "medium",
    question_type: str = "computational",
    chapter_title: str = "Chapter",
    base_filename: str = "question",
    strategy: str = "chapter",
) -> List[GeneratedQuestion]:
    """Generate WeBWorK PGML questions from a book chapter.

    Parameters
    ----------
    chapter_text:
        The raw text of the book chapter.
    num_questions:
        How many questions to generate (default: 5).
    api_key:
        OpenAI API key.  Falls back to the ``OPENAI_API_KEY`` environment
        variable when not provided.
    model:
        The OpenAI chat-completion model to use (default: ``"gpt-4o"``).
    difficulty:
        One of ``"easy"``, ``"medium"``, or ``"hard"`` (default: ``"medium"``).
    question_type:
        One of ``"computational"``, ``"conceptual"``, or ``"proof-based"``
        (default: ``"computational"``).
    chapter_title:
        An optional title used when naming output files.
    base_filename:
        Prefix for the generated ``.pg`` filenames.
    strategy:
        ``"chapter"`` — ask the LLM to produce all questions in one request
        (default).  ``"section"`` — ask once per detected chapter section.

    Returns
    -------
    List[GeneratedQuestion]
        One entry per generated question.

    Raises
    ------
    ValueError
        If ``num_questions`` is less than 1 or ``strategy`` is invalid.
    ImportError
        If the ``openai`` package is not installed.
    RuntimeError
        If no API key is available.
    """
    if num_questions < 1:
        raise ValueError("num_questions must be at least 1")
    if strategy not in ("chapter", "section"):
        raise ValueError("strategy must be 'chapter' or 'section'")

    resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not resolved_key:
        raise RuntimeError(
            "No OpenAI API key provided.  Pass api_key= or set the "
            "OPENAI_API_KEY environment variable."
        )

    if openai is None:  # pragma: no cover
        raise ImportError(
            "The 'openai' package is required.  Install it with:\n"
            "    pip install openai"
        )

    client = openai.OpenAI(api_key=resolved_key)
    parser = ChapterParser()
    generator = PGMLGenerator()

    parsed: ParsedChapter = parser.parse(chapter_text, chapter_title)

    raw_pgml_blocks: List[str] = []

    if strategy == "chapter":
        summary = parsed.full_summary()
        prompt = build_multi_question_prompt(
            chapter_summary=summary,
            num_questions=num_questions,
            difficulty=difficulty,
        )
        response_text = _call_openai(client, model, prompt)
        raw_pgml_blocks = _split_problems(response_text, num_questions)

    else:  # strategy == "section"
        sections = parsed.sections or []
        # Cycle through sections, distributing questions evenly
        for i in range(num_questions):
            section = sections[i % len(sections)] if sections else None
            summary = section.summary() if section else parsed.full_summary()
            prompt = build_question_prompt(
                section_summary=summary,
                question_type=question_type,
                difficulty=difficulty,
            )
            block = _call_openai(client, model, prompt)
            raw_pgml_blocks.append(block.strip())

    questions: List[GeneratedQuestion] = []
    for idx, raw in enumerate(raw_pgml_blocks, start=1):
        cleaned = _clean_pgml(raw)
        warnings = generator.validate_pgml(cleaned)
        filename = f"{base_filename}_{idx:02d}.pg"
        questions.append(
            GeneratedQuestion(
                index=idx,
                filename=filename,
                pgml_source=cleaned,
                validation_warnings=warnings,
            )
        )

    return questions


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _call_openai(client, model: str, prompt) -> str:  # type: ignore[no-untyped-def]
    """Call the OpenAI chat-completion API and return the response text."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": prompt.user},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content or ""


def _split_problems(text: str, expected: int) -> List[str]:
    """Split the LLM response on ``PROBLEM_DELIMITER`` markers.

    If the response does not contain any delimiters (e.g. the model only
    produced one problem) the whole text is returned as a single-element list.
    """
    parts = [p.strip() for p in text.split(PROBLEM_DELIMITER) if p.strip()]
    if not parts:
        return [text.strip()]
    return parts


def _clean_pgml(text: str) -> str:
    """Remove markdown code-fence wrappers that the LLM may have added."""
    # Strip ```perl ... ``` or ``` ... ``` fences
    fence_re = re.compile(r"^```(?:perl)?\s*\n?(.*?)```\s*$", re.DOTALL)
    m = fence_re.match(text.strip())
    if m:
        return m.group(1).strip() + "\n"
    return text.strip() + "\n"
