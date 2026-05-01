"""Allow running the CLI with  python -m src.cli  or  python -m src ."""

from .cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
