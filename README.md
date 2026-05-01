# Webwork_Question_Generator

A skill for generating [WeBWorK](https://webwork.maa.org/) online homework
questions in **PGML** (PG Markup Language) format from a specified textbook
chapter.

---

## Features

- Parses raw textbook chapter text and extracts structured sections.
- Sends chapter content to an OpenAI LLM to generate valid `.pg` WeBWorK
  problem files.
- Produces multiple distinct problems per chapter with random parameters and
  worked solutions.
- Validates the generated PGML source for common structural errors.
- Exposes a clean **Python API** and a **command-line interface**.

---

## Installation

```bash
pip install -r requirements.txt
```

Or install in editable mode (includes dev/test dependencies):

```bash
pip install -e ".[dev]"
```

---

## Usage

### Python API

```python
from src.skill import generate_questions

questions = generate_questions(
    chapter_text=open("chapter03.txt").read(),
    num_questions=5,
    api_key="sk-...",          # or set OPENAI_API_KEY env var
    difficulty="medium",       # "easy" | "medium" | "hard"
    question_type="computational",  # "computational" | "conceptual" | "proof-based"
)

for q in questions:
    print(q.filename)          # e.g. "question_01.pg"
    print(q.pgml_source)       # full .pg file contents
    if q.validation_warnings:
        print(q.validation_warnings)
```

### Command-line interface

```bash
# Generate 5 questions and print to stdout
python -m src.cli chapter03.txt --num-questions 5 --api-key sk-...

# Write .pg files to a directory
python -m src.cli chapter03.txt \
    --num-questions 8 \
    --output-dir ./hw3_questions \
    --difficulty hard \
    --title "Chapter 3: Derivatives"

# Read chapter from stdin
cat chapter03.txt | python -m src.cli - --num-questions 3
```

Full option reference:

```
usage: webwork-gen [-h] [-n N] [-o DIR] [--title TITLE]
                   [--difficulty {easy,medium,hard}]
                   [--question-type {computational,conceptual,proof-based}]
                   [--strategy {chapter,section}]
                   [--model MODEL] [--api-key KEY]
                   [--base-filename PREFIX]
                   CHAPTER_FILE
```

---

## Project structure

```
src/
  __init__.py          Public API exports
  skill.py             Main generate_questions() entry point
  pgml_generator.py    PGML source builder and validator
  chapter_parser.py    Textbook chapter parser
  prompts.py           LLM prompt templates
  cli.py               Command-line interface
tests/
  test_skill.py
  test_pgml_generator.py
  test_chapter_parser.py
  test_prompts.py
  test_cli.py
requirements.txt
pyproject.toml
```

---

## Example output

A generated `.pg` file looks like:

```perl
DOCUMENT();

loadMacros(
    "PGstandard.pl",
    "MathObjects.pl",
    "PGML.pl",
    "PGcourse.pl"
);

TEXT(beginproblem());
Context("Numeric");

$a = random(2, 9, 1);
$b = random(2, 9, 1);
$answer = Compute("$a * $b");

BEGIN_PGML
Compute [` [$a] \cdot [$b] `].

[__________]{$answer}
END_PGML

BEGIN_PGML_SOLUTION
[` [$a] \times [$b] = [$answer] `]
END_PGML_SOLUTION

ENDDOCUMENT();
```

---

## Running tests

```bash
pytest
```

---

## Environment variables

| Variable         | Description                                         |
|------------------|-----------------------------------------------------|
| `OPENAI_API_KEY` | OpenAI API key (alternative to the `--api-key` flag) |
