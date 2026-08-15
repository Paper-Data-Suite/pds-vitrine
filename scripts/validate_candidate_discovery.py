"""Validate the fixture-backed Core-to-Vitrine Candidate discovery boundary."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_HASHES = {
    "tests/fixtures/runtime-models/improvement-foundational-records-v1.json": (
        "608f96fa10e5b7a20cf42dd4582a2b77cb1dede99da74491c8e7faf8f7635de8"
    ),
    "tests/fixtures/runtime-models/showcase-foundational-records-v1.json": (
        "ac72e824bb97c5e550b65f1dbdcb489abd3bd11d9b8f84cb0f83a6fc0c8b0360"
    ),
}


def validate(*, run_focused_tests: bool = True) -> None:
    if run_focused_tests:
        focused = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_candidate_services.py",
                "tests/test_candidate_discovery.py",
                "-q",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if focused.returncode != 0:
            detail = focused.stderr.strip() or focused.stdout.strip()
            raise RuntimeError(
                f"Candidate discovery focused validation failed: {detail}"
            )

    for relative, expected in FOUNDATION_HASHES.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"foundation fixture changed: {relative}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-focused-tests",
        action="store_true",
        help=(
            "Skip the focused pytest subset when an enclosing qualification gate "
            "has already run the complete pytest suite."
        ),
    )
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS Candidate discovery validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Candidate discovery validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
