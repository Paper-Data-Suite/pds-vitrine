"""Validate canonical foundational Vitrine runtime-model fixtures."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from vitrine.models import (
    graph_from_json_bytes,
    graph_to_canonical_json_bytes,
    validate_record_graph,
)

EXPECTED_FILES = {
    "improvement-foundational-records-v1.json": {
        "portfolios": 1,
        "candidates": 2,
        "snapshot_editions": 1,
    },
    "showcase-foundational-records-v1.json": {
        "portfolios": 1,
        "candidates": 3,
        "snapshot_editions": 1,
    },
}


def validate_fixture(path: Path, expected_counts: dict[str, int]) -> str:
    content = path.read_bytes()
    graph = graph_from_json_bytes(content)
    validate_record_graph(graph)
    canonical = graph_to_canonical_json_bytes(graph)
    if canonical != content:
        raise RuntimeError(f"{path.name} is not canonical or byte-stable")
    for collection, expected in expected_counts.items():
        actual = len(getattr(graph, collection))
        if actual != expected:
            raise RuntimeError(
                f"{path.name} expected {expected} {collection}; found {actual}"
            )
    return hashlib.sha256(content).hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    fixture_dir = root / "tests" / "fixtures" / "runtime-models"
    try:
        actual_files = {path.name for path in fixture_dir.glob("*.json")}
        if actual_files != set(EXPECTED_FILES):
            raise RuntimeError(
                "runtime-model fixture set differs from the expected canonical set"
            )
        for name, expected in sorted(EXPECTED_FILES.items()):
            digest = validate_fixture(fixture_dir / name, expected)
            print(f"PASS {name} sha256={digest}")
        print("PASS foundational runtime-model fixture validation")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Runtime-model validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
