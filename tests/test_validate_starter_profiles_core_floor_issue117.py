"""Issue #117: current starter Profile Core floor, with producer isolation."""
from __future__ import annotations

from pathlib import Path

from scripts.validate_starter_profiles import _validate_package_dependencies


def _findings(tmp_path: Path, dependencies: str) -> list[str]:
    (tmp_path / "pyproject.toml").write_text(
        f"[project]\ndependencies = [{dependencies}]\n", encoding="utf-8"
    )
    issues: list[str] = []
    _validate_package_dependencies(tmp_path, issues)
    return issues


def test_current_core_066_floor_is_accepted(tmp_path: Path) -> None:
    assert _findings(tmp_path, '"pds-core>=0.6.6,<0.7"') == []


def test_old_core_065_floor_is_rejected(tmp_path: Path) -> None:
    assert "pyproject.toml is missing the expected Core dependency range." in (
        _findings(tmp_path, '"pds-core>=0.6.5,<0.7"')
    )


def test_missing_core_dependency_is_rejected(tmp_path: Path) -> None:
    assert "pyproject.toml is missing the expected Core dependency range." in (
        _findings(tmp_path, '"unrelated>=1"')
    )


def test_core_066_does_not_authorize_sibling_dependency(tmp_path: Path) -> None:
    findings = _findings(
        tmp_path,
        '"pds-core>=0.6.6,<0.7", "pds-concord>=0.3"',
    )
    assert any("hard sibling dependency" in item for item in findings)
