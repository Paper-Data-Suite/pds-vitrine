from __future__ import annotations

import pytest

import scripts.validate_candidate_evidence_review as validator


def test_candidate_evidence_review_validator_without_nested_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("focused pytest must not run")

    monkeypatch.setattr(validator.subprocess, "run", unexpected)
    validator.validate(run_focused_tests=False)
