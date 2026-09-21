from __future__ import annotations

from pathlib import Path

import pytest

import scripts.validate_teacher_information_architecture as validator


def test_teacher_information_architecture_validator_without_nested_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("focused pytest must not run")

    monkeypatch.setattr(validator.subprocess, "run", unexpected)
    validator.validate(run_focused_tests=False)


def test_teacher_presentation_validator_rejects_mutation_import(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad_presentation.py"
    path.write_text(
        "from vitrine.curation_services import place_selection\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="imports mutation/authority"):
        validator._validate_presentation_source(path)


def test_teacher_presentation_validator_rejects_mutation_call(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad_presentation.py"
    path.write_text(
        "def bad():\n    execute_prepared_current_portfolio_build()\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="invokes mutation/authority"):
        validator._validate_presentation_source(path)
