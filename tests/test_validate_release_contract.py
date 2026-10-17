from __future__ import annotations

from pathlib import Path

from scripts.validate_release_contract import (
    EXPECTED_CORE_REQUIREMENT,
    EXPECTED_VERSION,
    _runtime_boundary_findings,
    validate,
)


def test_v040_identity_preserves_frozen_v030_qualification_anchor() -> None:
    assert EXPECTED_VERSION == "0.4.0"
    # This is the historical v0.3.0 release requirement, not the active floor.
    assert EXPECTED_CORE_REQUIREMENT == "pds-core>=0.6.3,<0.7"


def test_release_contract_validator_passes_for_repository() -> None:
    assert validate(Path.cwd()) == ()


def test_release_runtime_boundary_is_frozen() -> None:
    assert _runtime_boundary_findings() == []
