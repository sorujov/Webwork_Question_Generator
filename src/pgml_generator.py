"""PGML (PG Markup Language) generator utilities for WeBWorK questions.

Provides helpers for creating valid PGML-format WeBWorK problem files (.pg).
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from typing import List, Optional

# Regex to find DOCUMENT(); that is NOT part of ENDDOCUMENT();
_DOCUMENT_RE = re.compile(r"(?<!END)DOCUMENT\(\);")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PGMLQuestion:
    """Represents a single WeBWorK PGML question."""

    title: str
    variables: List[str] = field(default_factory=list)
    setup_code: str = ""
    problem_text: str = ""
    answer_expression: str = ""
    solution_text: str = ""
    macros: List[str] = field(
        default_factory=lambda: [
            "PGstandard.pl",
            "MathObjects.pl",
            "PGML.pl",
            "PGcourse.pl",
        ]
    )
    context: str = "Numeric"

    # Optional hints
    hints: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class PGMLGenerator:
    """Generates valid PGML WeBWorK problem source (.pg files)."""

    # Indentation used in generated Perl code
    _INDENT = "    "

    def generate(self, question: PGMLQuestion) -> str:
        """Return the complete PGML source for *question* as a string.

        Parameters
        ----------
        question:
            A :class:`PGMLQuestion` instance describing the problem.

        Returns
        -------
        str
            The full content of a ``.pg`` WeBWorK problem file.
        """
        parts: List[str] = []
        parts.append("DOCUMENT();")
        parts.append("")
        parts.append(self._render_macros(question.macros))
        parts.append("")
        parts.append("TEXT(beginproblem());")
        parts.append(f'Context("{question.context}");')
        parts.append("")

        if question.setup_code:
            parts.append(self._normalise_code(question.setup_code))
            parts.append("")

        parts.append("BEGIN_PGML")
        if question.problem_text:
            parts.append(self._normalise_text(question.problem_text))
        if question.answer_expression:
            parts.append("")
            parts.append(
                f"[__________]{{Compute(\"{question.answer_expression}\")}}"
            )
        parts.append("END_PGML")
        parts.append("")

        if question.hints:
            parts.append("BEGIN_PGML_HINT")
            for hint in question.hints:
                parts.append(self._normalise_text(hint))
            parts.append("END_PGML_HINT")
            parts.append("")

        if question.solution_text:
            parts.append("BEGIN_PGML_SOLUTION")
            parts.append(self._normalise_text(question.solution_text))
            parts.append("END_PGML_SOLUTION")
            parts.append("")

        parts.append("ENDDOCUMENT();")

        return "\n".join(parts) + "\n"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _render_macros(macros: List[str]) -> str:
        macro_lines = ",\n".join(f'    "{m}"' for m in macros)
        return f"loadMacros(\n{macro_lines}\n);"

    @staticmethod
    def _normalise_code(code: str) -> str:
        """Strip leading/trailing blank lines while keeping indentation."""
        return textwrap.dedent(code).strip()

    @staticmethod
    def _normalise_text(text: str) -> str:
        """Dedent and strip a block of PGML text."""
        return textwrap.dedent(text).strip()

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def validate_pgml(source: str) -> List[str]:
        """Return a list of validation warnings for *source*.

        Checks for common structural issues without executing Perl.
        """
        issues: List[str] = []

        if not _DOCUMENT_RE.search(source):
            issues.append("Missing DOCUMENT(); declaration")
        if "ENDDOCUMENT();" not in source:
            issues.append("Missing ENDDOCUMENT(); declaration")
        if "loadMacros(" not in source:
            issues.append("Missing loadMacros() call")
        if "BEGIN_PGML" not in source:
            issues.append("Missing BEGIN_PGML block")
        if "END_PGML" not in source:
            issues.append("Missing END_PGML marker")

        # Balanced BEGIN/END blocks
        for block in ("PGML", "PGML_SOLUTION", "PGML_HINT"):
            begins = len(re.findall(rf"^BEGIN_{block}$", source, re.MULTILINE))
            ends = len(re.findall(rf"^END_{block}$", source, re.MULTILINE))
            if begins != ends:
                issues.append(
                    f"Unbalanced BEGIN_{block}/END_{block} blocks "
                    f"({begins} vs {ends})"
                )

        return issues
