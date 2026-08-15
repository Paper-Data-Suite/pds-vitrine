from __future__ import annotations

import scripts.validate_curation_workflows as validator


def test_curation_workflow_validator_locks_foundation_hashes() -> None:
    assert {path.name for path in validator.LOCKED_FIXTURES} == {
        "improvement-foundational-records-v1.json",
        "showcase-foundational-records-v1.json",
    }
    for path, expected in validator.LOCKED_FIXTURES.items():
        assert validator._sha256(path) == expected


def test_curation_skip_mode_does_not_launch_nested_pytest(monkeypatch) -> None:
    def fail_run(*_args, **_kwargs):
        raise AssertionError("skip mode must not launch a nested pytest process")

    monkeypatch.setattr(validator.subprocess, "run", fail_run)
    validator.validate(run_focused_tests=False)


def test_curation_entrypoint_maps_success_without_reexecuting_workflow(
    monkeypatch, capsys
) -> None:
    calls: list[bool] = []

    def fake_validate(*, run_focused_tests: bool = True) -> None:
        calls.append(run_focused_tests)

    monkeypatch.setattr(validator, "validate", fake_validate)

    assert validator.main(["--skip-focused-tests"]) == 0
    assert calls == [False]
    assert "PASS curation workflow validation" in capsys.readouterr().out
