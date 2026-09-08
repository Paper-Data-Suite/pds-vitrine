from __future__ import annotations

from pathlib import Path

import pytest

import scripts.validate_working_composition as validator


def test_working_composition_validator_contract_checks_without_nested_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("focused pytest must not run")

    monkeypatch.setattr(validator.subprocess, "run", unexpected)
    validator.validate(run_focused_tests=False)


def test_working_composition_validator_rejects_producer_reader_import(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad_guided_source.py"
    path.write_text(
        "from vitrine.producer_reader_services import read_publication\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="protected producer/audience/Snapshot"):
        validator._validate_guided_source(path)


def test_working_composition_validator_rejects_downstream_audience_call(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad_audience_source.py"
    path.write_text(
        "def bad():\n    create_audience_context()\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="protected downstream/discovery"):
        validator._validate_guided_source(path)
