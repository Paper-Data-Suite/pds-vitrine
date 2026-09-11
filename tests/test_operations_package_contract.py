from __future__ import annotations

import tomllib
from pathlib import Path


def test_operations_distribution_contract_is_declared_for_package_audit() -> None:
    from scripts.check_package import ALLOWED_RUNTIME_FILES, REQUIRED_SDIST_FILES

    assert "vitrine/pds_operations.py" in ALLOWED_RUNTIME_FILES
    assert "vitrine/operations_provider.py" in ALLOWED_RUNTIME_FILES
    required = {
        "docs/contracts/suite-operations-integration-v1.md",
        "docs/development/suite-operations-integration.md",
        "docs/validation/issue-70-suite-operations-integration-validation.md",
        "scripts/smoke_test_operations_wheel.py",
        "scripts/validate_workspace_relocation.py",
        "scripts/validate_suite_operations_integration.py",
        "tests/test_pds_operations.py",
        "tests/test_operations_package_contract.py",
        "tests/test_validate_workspace_relocation.py",
        "tests/test_validate_suite_operations_integration.py",
    }
    assert required <= REQUIRED_SDIST_FILES


def test_operations_validation_scripts_are_static_analysis_targets() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    mypy_files = tuple(data["tool"]["mypy"]["files"])
    assert "scripts/smoke_test_operations_wheel.py" in mypy_files
    assert "scripts/validate_workspace_relocation.py" in mypy_files
    assert "scripts/validate_suite_operations_integration.py" in mypy_files
