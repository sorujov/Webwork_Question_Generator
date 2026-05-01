"""Command-line interface for the WeBWorK Question Generator skill.

Examples
--------
Generate 5 questions from a chapter text file::

    python -m src.cli chapter.txt --num-questions 5 --output-dir ./questions

Read from stdin and print to stdout::

    cat chapter.txt | python -m src.cli - --num-questions 3
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .skill import generate_questions


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="webwork-gen",
        description="Generate WeBWorK PGML questions from a textbook chapter.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "chapter_file",
        metavar="CHAPTER_FILE",
        help="Path to the chapter text file, or '-' to read from stdin.",
    )
    parser.add_argument(
        "-n",
        "--num-questions",
        type=int,
        default=5,
        metavar="N",
        help="Number of questions to generate (default: 5).",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="DIR",
        default=None,
        help=(
            "Directory in which to write the generated .pg files.  "
            "If omitted, prints to stdout."
        ),
    )
    parser.add_argument(
        "--title",
        default="Chapter",
        metavar="TITLE",
        help="Chapter title used in filenames (default: 'Chapter').",
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        default="medium",
        help="Difficulty level for generated questions (default: medium).",
    )
    parser.add_argument(
        "--question-type",
        choices=["computational", "conceptual", "proof-based"],
        default="computational",
        dest="question_type",
        help="Type of questions to generate (default: computational).",
    )
    parser.add_argument(
        "--strategy",
        choices=["chapter", "section"],
        default="chapter",
        help=(
            "Generation strategy: 'chapter' sends the whole chapter to the "
            "LLM in one request; 'section' sends each section separately "
            "(default: chapter)."
        ),
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI model to use (default: gpt-4o).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        metavar="KEY",
        help=(
            "OpenAI API key.  Defaults to the OPENAI_API_KEY environment "
            "variable."
        ),
    )
    parser.add_argument(
        "--base-filename",
        default="question",
        metavar="PREFIX",
        help="Filename prefix for generated .pg files (default: 'question').",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI.  Returns the exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Read chapter text
    if args.chapter_file == "-":
        chapter_text = sys.stdin.read()
    else:
        chapter_path = Path(args.chapter_file)
        if not chapter_path.exists():
            print(f"Error: file not found: {chapter_path}", file=sys.stderr)
            return 1
        chapter_text = chapter_path.read_text(encoding="utf-8")

    if not chapter_text.strip():
        print("Error: chapter text is empty.", file=sys.stderr)
        return 1

    try:
        questions = generate_questions(
            chapter_text=chapter_text,
            num_questions=args.num_questions,
            api_key=args.api_key,
            model=args.model,
            difficulty=args.difficulty,
            question_type=args.question_type,
            chapter_title=args.title,
            base_filename=args.base_filename,
            strategy=args.strategy,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for q in questions:
            dest = out_dir / q.filename
            dest.write_text(q.pgml_source, encoding="utf-8")
            status = ""
            if q.validation_warnings:
                status = f" (warnings: {', '.join(q.validation_warnings)})"
            print(f"Wrote {dest}{status}")
    else:
        for q in questions:
            print(f"{'=' * 60}")
            print(f"# {q.filename}")
            if q.validation_warnings:
                for w in q.validation_warnings:
                    print(f"# WARNING: {w}")
            print(f"{'=' * 60}")
            print(q.pgml_source)

    return 0


if __name__ == "__main__":
    sys.exit(main())
