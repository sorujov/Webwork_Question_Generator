"""Tests for the CLI module."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.cli import main
from src.skill import GeneratedQuestion


VALID_PG = textwrap.dedent("""\
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
    $answer = Compute("$a * 2");

    BEGIN_PGML
    What is [`2 \\cdot [$a]`]?

    [__________]{$answer}
    END_PGML

    BEGIN_PGML_SOLUTION
    The answer is [`[$answer]`].
    END_PGML_SOLUTION

    ENDDOCUMENT();
""")


def _fake_generate_questions(**kwargs):
    n = kwargs.get("num_questions", 1)
    return [
        GeneratedQuestion(
            index=i,
            filename=f"question_{i:02d}.pg",
            pgml_source=VALID_PG,
            validation_warnings=[],
        )
        for i in range(1, n + 1)
    ]


class TestCLI:
    def test_missing_file_returns_error(self, tmp_path, capsys):
        rc = main(["nonexistent_file.txt", "--api-key", "fake"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "error" in captured.err.lower()

    def test_reads_from_file_and_prints_to_stdout(self, tmp_path, capsys):
        chapter_file = tmp_path / "chapter.txt"
        chapter_file.write_text("# Math\n\nSome content about limits.\n")

        with patch("src.cli.generate_questions", side_effect=_fake_generate_questions):
            rc = main([str(chapter_file), "--num-questions", "2", "--api-key", "fake"])

        assert rc == 0
        captured = capsys.readouterr()
        assert "question_01.pg" in captured.out
        assert "DOCUMENT();" in captured.out

    def test_writes_files_to_output_dir(self, tmp_path, capsys):
        chapter_file = tmp_path / "chapter.txt"
        chapter_file.write_text("# Physics\n\nMotion and forces.\n")
        out_dir = tmp_path / "output"

        with patch("src.cli.generate_questions", side_effect=_fake_generate_questions):
            rc = main([
                str(chapter_file),
                "--num-questions", "2",
                "--output-dir", str(out_dir),
                "--api-key", "fake",
            ])

        assert rc == 0
        assert (out_dir / "question_01.pg").exists()
        assert (out_dir / "question_02.pg").exists()
        content = (out_dir / "question_01.pg").read_text()
        assert "DOCUMENT();" in content

    def test_empty_chapter_returns_error(self, tmp_path, capsys):
        chapter_file = tmp_path / "empty.txt"
        chapter_file.write_text("   \n  \n")

        rc = main([str(chapter_file), "--api-key", "fake"])
        assert rc == 1

    def test_generate_error_returns_error(self, tmp_path, capsys):
        chapter_file = tmp_path / "chapter.txt"
        chapter_file.write_text("# Algebra\n\nSolve equations.\n")

        def raise_error(**kwargs):
            raise RuntimeError("No API key")

        with patch("src.cli.generate_questions", side_effect=raise_error):
            rc = main([str(chapter_file), "--api-key", "fake"])

        assert rc == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_validation_warnings_shown_in_stdout(self, tmp_path, capsys):
        chapter_file = tmp_path / "chapter.txt"
        chapter_file.write_text("# Test\n\nContent.\n")

        def gen_with_warnings(**kwargs):
            return [
                GeneratedQuestion(
                    index=1,
                    filename="question_01.pg",
                    pgml_source=VALID_PG,
                    validation_warnings=["Missing ENDDOCUMENT(); declaration"],
                )
            ]

        with patch("src.cli.generate_questions", side_effect=gen_with_warnings):
            rc = main([str(chapter_file), "--api-key", "fake"])

        assert rc == 0
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
