from __future__ import annotations

from pathlib import Path

import pytest

import scripts.validate_current_portfolio_build_export as validator


def test_current_portfolio_validator_contract_checks_without_nested_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("focused pytest must not run")

    monkeypatch.setattr(validator.subprocess, "run", unexpected)
    validator.validate(run_focused_tests=False)


def test_current_portfolio_validator_rejects_sibling_runtime_import(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad_current_portfolio.py"
    path.write_text("import scoreform\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="optional sibling package"):
        validator._validate_runtime_source(path)


def test_current_portfolio_validator_rejects_implicit_pointer_advance(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad_execution.py"
    path.write_text(
        "def bad():\n    set_snapshot_current_pointer()\n",
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError, match="implicitly advances Snapshot current pointer"
    ):
        validator._validate_execution_source(path)


def test_current_portfolio_validator_rejects_preparation_mutation_import(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad_preparation.py"
    path.write_text(
        "from vitrine.audience_services import create_audience_context\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="canonical mutation service"):
        validator._validate_preparation_source(path)
