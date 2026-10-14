"""Issue #117 Slice 2: current release identity and frozen-release separation."""

from __future__ import annotations

from pathlib import Path

from scripts import check_package, validate_release_contract
from scripts import validate_issue117_release_baseline as baseline
from scripts.live_installed_acceptance_contract import VITRINE_RELEASE_WHEEL
from vitrine import __version__


def test_active_source_release_is_v040() -> None:
    assert __version__ == "0.4.0"
    assert validate_release_contract.EXPECTED_VERSION == "0.4.0"
    assert validate_release_contract.validate(Path.cwd()) == ()


def test_active_package_checker_rejects_historical_v030_identity() -> None:
    raw = (
        b"Name: pds-vitrine\n"
        b"Version: 0.3.0\n"
        b"Requires-Python: >=3.11\n"
        b"Requires-Dist: pds-core<0.7,>=0.6.5\n"
    )
    assert "unexpected version: 0.3.0" in check_package._metadata_findings(raw)
    candidate = raw.replace(b"Version: 0.3.0", b"Version: 0.4.0")
    assert not any(
        finding.startswith("unexpected version:")
        for finding in check_package._metadata_findings(candidate)
    )


def test_published_v030_wheel_audit_is_not_current_version_authority() -> None:
    assert VITRINE_RELEASE_WHEEL.version == "0.3.0"
    assert VITRINE_RELEASE_WHEEL.filename == "pds_vitrine-0.3.0-py3-none-any.whl"
    assert validate_release_contract.EXPECTED_CORE_REQUIREMENT == (
        "pds-core>=0.6.3,<0.7"
    )
    assert baseline.validate() == ()


def test_current_dependency_floor_is_core065_and_no_producers() -> None:
    assert validate_release_contract.CURRENT_DEVELOPMENT_CORE_REQUIREMENT == (
        "pds-core>=0.6.5,<0.7"
    )
    assert baseline.validate() == ()
