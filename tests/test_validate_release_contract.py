from __future__ import annotations

from pathlib import Path

from scripts.validate_release_contract import _runtime_boundary_findings, validate


def test_release_contract_validator_passes_for_repository() -> None:
    assert validate(Path.cwd()) == ()


def test_release_runtime_boundary_is_frozen() -> None:
    assert _runtime_boundary_findings() == []
