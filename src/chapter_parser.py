"""Utilities for parsing and chunking book chapter text.

The parser extracts meaningful sections and concepts from raw chapter text so
they can be turned into WeBWorK questions by the LLM prompt layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ChapterSection:
    """A section extracted from the chapter."""

    heading: str
    body: str

    def summary(self, max_chars: int = 1500) -> str:
        """Return a trimmed excerpt suitable for use in a prompt."""
        text = self.body.strip()
        if len(text) > max_chars:
            text = text[:max_chars].rsplit(" ", 1)[0] + " …"
        return f"## {self.heading}\n\n{text}"


@dataclass
class ParsedChapter:
    """Structured representation of a book chapter."""

    title: str
    sections: List[ChapterSection] = field(default_factory=list)
    raw_text: str = ""

    def full_summary(self, max_chars_per_section: int = 1500) -> str:
        """Return a condensed chapter summary for use in prompts."""
        lines = [f"# {self.title}"]
        for sec in self.sections:
            lines.append(sec.summary(max_chars_per_section))
        return "\n\n".join(lines)


class ChapterParser:
    """Parse raw book-chapter text into structured sections.

    The parser is intentionally simple and heuristic: it splits the text on
    lines that look like headings (all-caps, numbered, or markdown-style ``#``
    headings) and treats the rest as the section body.
    """

    # Patterns that identify a heading line (markdown, numbered, or all-caps)
    _HEADING_RE = re.compile(
        r"^(?:(?P<md>#{1,4})\s+|(?P<num>\d+(?:\.\d+)*\.?)\s+|(?P<caps>[A-Z][A-Z\s]{4,}))(?P<text>.+)?$"
    )

    def parse(self, chapter_text: str, chapter_title: str = "Chapter") -> ParsedChapter:
        """Parse *chapter_text* into a :class:`ParsedChapter`.

        Parameters
        ----------
        chapter_text:
            The raw text of the chapter.
        chapter_title:
            An optional title for the chapter (used when no title heading is
            detected).

        Returns
        -------
        ParsedChapter
        """
        lines = chapter_text.splitlines()
        title = chapter_title
        sections: List[ChapterSection] = []
        current_heading: str | None = None
        current_body_lines: List[str] = []

        for line in lines:
            m = self._HEADING_RE.match(line.strip())
            if m:
                # Save the previous section
                if current_heading is not None:
                    body = "\n".join(current_body_lines).strip()
                    if body:
                        sections.append(ChapterSection(current_heading, body))
                elif current_body_lines:
                    # Text before the first heading: treat as intro
                    body = "\n".join(current_body_lines).strip()
                    if body:
                        sections.append(ChapterSection("Introduction", body))

                current_body_lines = []
                heading_text = (m.group("text") or "").strip() or line.strip()

                # Detect the chapter title from the first heading
                if not sections and current_heading is None and m.group("md") == "#":
                    title = heading_text
                    current_heading = None
                else:
                    current_heading = heading_text
            else:
                current_body_lines.append(line)

        # Flush the last section
        if current_heading is not None:
            body = "\n".join(current_body_lines).strip()
            if body:
                sections.append(ChapterSection(current_heading, body))
        elif current_body_lines:
            body = "\n".join(current_body_lines).strip()
            if body:
                sections.append(ChapterSection("Introduction", body))

        # If no sections were detected, wrap the whole text as one section
        if not sections:
            sections.append(ChapterSection(chapter_title, chapter_text.strip()))

        return ParsedChapter(title=title, sections=sections, raw_text=chapter_text)
