"""Prompt templates for the WeBWorK question generation skill.

Each template produces an LLM prompt (system + user) that instructs the model
to output a valid PGML WeBWorK problem.  Templates are kept as plain strings so
they are easy to read, test, and tweak without touching any other code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Prompt:
    """A structured LLM prompt (system message + user message)."""

    system: str
    user: str


# ---------------------------------------------------------------------------
# System message shared across all templates
# ---------------------------------------------------------------------------

_SYSTEM_MESSAGE = """\
You are an expert mathematics educator who specialises in writing WeBWorK \
online homework problems using PGML (PG Markup Language).

Your output must be a single, complete, syntactically valid WeBWorK .pg file.

Follow these rules strictly:
1. Start with  DOCUMENT();
2. Call loadMacros() and include at minimum "PGstandard.pl", "MathObjects.pl",
   "PGML.pl", and "PGcourse.pl".
3. Set the appropriate MathObjects Context (e.g. Context("Numeric"),
   Context("Vector"), etc.).
4. Declare Perl variables for any random parameters using random(), Real(),
   Compute(), etc.
5. Write the problem statement inside a BEGIN_PGML ... END_PGML block.
6. Provide an answer blank in PGML notation: [__________]{$answer}
7. Include a complete worked solution inside BEGIN_PGML_SOLUTION ...
   END_PGML_SOLUTION.
8. End with  ENDDOCUMENT();
9. Do not include any explanation outside the .pg file — output ONLY the file
   contents.
10. Use LaTeX math notation inside backtick-brackets: [`...`] for inline math
    and [``...``] for display math.
"""


# ---------------------------------------------------------------------------
# Template functions
# ---------------------------------------------------------------------------


def build_question_prompt(
    section_summary: str,
    question_type: str = "computational",
    difficulty: str = "medium",
    topic_hint: Optional[str] = None,
) -> Prompt:
    """Return a :class:`Prompt` asking the LLM to write a PGML question.

    Parameters
    ----------
    section_summary:
        A concise text excerpt from the book chapter section.
    question_type:
        One of ``"computational"``, ``"conceptual"``, or ``"proof-based"``.
    difficulty:
        One of ``"easy"``, ``"medium"``, or ``"hard"``.
    topic_hint:
        Optional extra guidance for the model (e.g. "focus on integration by
        parts").
    """
    user_lines = [
        f"Write a {difficulty} {question_type} WeBWorK PGML problem based on "
        f"the following section from a textbook chapter:",
        "",
        "---",
        section_summary.strip(),
        "---",
    ]

    if topic_hint:
        user_lines.append("")
        user_lines.append(f"Specifically focus on: {topic_hint}")

    user_lines += [
        "",
        "Requirements:",
        "- The problem must have at least one numerical or algebraic answer blank.",
        "- Use random parameters so the problem has different values for different students.",
        "- Include a clear worked solution.",
        "- Output ONLY the complete .pg file, with no commentary before or after.",
    ]

    return Prompt(system=_SYSTEM_MESSAGE, user="\n".join(user_lines))


def build_multi_question_prompt(
    chapter_summary: str,
    num_questions: int = 5,
    difficulty: str = "medium",
) -> Prompt:
    """Return a :class:`Prompt` asking for *num_questions* PGML problems.

    The LLM is instructed to separate each problem with a clear delimiter so
    the response can be split into individual ``.pg`` files.

    Parameters
    ----------
    chapter_summary:
        A condensed summary of the full chapter.
    num_questions:
        How many distinct problems to generate.
    difficulty:
        Difficulty level for all generated problems.
    """
    delimiter = "%%% PROBLEM BREAK %%%"

    user = (
        f"Write exactly {num_questions} distinct {difficulty} WeBWorK PGML "
        f"problems based on the following textbook chapter. Cover different "
        f"topics from the chapter so the set of problems is varied.\n\n"
        f"---\n{chapter_summary.strip()}\n---\n\n"
        f"Rules:\n"
        f"- Each problem must be a complete, valid .pg file.\n"
        f"- Separate consecutive problems with this exact delimiter on its own "
        f"line (with no surrounding text):\n\n"
        f"    {delimiter}\n\n"
        f"- Use random parameters in each problem.\n"
        f"- Include a worked solution for each problem.\n"
        f"- Output ONLY the .pg files and the delimiters — no commentary."
    )

    return Prompt(system=_SYSTEM_MESSAGE, user=user)


# ---------------------------------------------------------------------------
# Constants for callers
# ---------------------------------------------------------------------------

PROBLEM_DELIMITER = "%%% PROBLEM BREAK %%%"
