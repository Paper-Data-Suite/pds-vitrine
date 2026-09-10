from __future__ import annotations

from pathlib import Path

import pytest

import scripts.validate_attention_next_actions as validator


def test_attention_validator_contract_checks_without_nested_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("focused pytest must not run")

    monkeypatch.setattr(validator.subprocess, "run", unexpected)
    validator.validate(run_focused_tests=False)


def test_attention_validator_rejects_sibling_runtime_import(tmp_path: Path) -> None:
    path = tmp_path / "bad_attention.py"
    path.write_text("import scoreform\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="imports sibling package"):
        validator._validate_attention_source(path)


def test_attention_validator_rejects_mutation_call(tmp_path: Path) -> None:
    path = tmp_path / "bad_attention.py"
    path.write_text(
        "def bad():\n    create_working_composition()\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="mutation/write call"):
        validator._validate_attention_source(path)


def test_attention_validator_rejects_timestamp_currentness(tmp_path: Path) -> None:
    path = tmp_path / "bad_attention.py"
    path.write_text("value = item.started_at\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="must not use event timestamps"):
        validator._validate_attention_source(path)
