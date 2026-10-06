"""Run the final synthetic Issue #101 student Portfolio acceptance."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = "tests/test_portfolio_presentation_end_to_end_issue101.py"


def validate() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", TEST, "-q"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"Issue #101 synthetic end-to-end acceptance failed: {detail}"
        )


def main() -> int:
    try:
        validate()
        print(
            "PASS Issue #101 synthetic Improvement Portfolio "
            "presentation end-to-end acceptance"
        )
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
