"""Validate issue #34 curation workflows and locked foundational compatibility."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCKED_FIXTURES = {
    ROOT / "tests/fixtures/runtime-models/improvement-foundational-records-v1.json": (
        "608f96fa10e5b7a20cf42dd4582a2b77cb1dede99da74491c8e7faf8f7635de8"
    ),
    ROOT / "tests/fixtures/runtime-models/showcase-foundational-records-v1.json": (
        "ac72e824bb97c5e550b65f1dbdcb489abd3bd11d9b8f84cb0f83a6fc0c8b0360"
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> None:
    for path, expected in LOCKED_FIXTURES.items():
        if _sha256(path) != expected:
            raise RuntimeError(f"locked foundational fixture changed: {path.name}")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_curation_models.py",
            "tests/test_curation_state.py",
            "tests/test_curation_services.py",
            "tests/test_curation_workflows.py",
            "tests/test_curation_acceptance_matrix.py",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )


def main() -> int:
    try:
        validate()
        print("PASS curation workflow validation")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Curation workflow validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
