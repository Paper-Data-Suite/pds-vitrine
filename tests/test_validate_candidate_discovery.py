from __future__ import annotations

import scripts.validate_candidate_discovery as validator


def test_candidate_discovery_skip_mode_does_not_launch_nested_pytest(
    monkeypatch,
) -> None:
    def fail_run(*_args, **_kwargs):
        raise AssertionError("skip mode must not launch a nested pytest process")

    monkeypatch.setattr(validator.subprocess, "run", fail_run)
    validator.validate(run_focused_tests=False)


def test_candidate_discovery_entrypoint_maps_success_without_reexecuting_workflow(
    monkeypatch, capsys
) -> None:
    calls: list[bool] = []

    def fake_validate(*, run_focused_tests: bool = True) -> None:
        calls.append(run_focused_tests)

    monkeypatch.setattr(validator, "validate", fake_validate)

    assert validator.main(["--skip-focused-tests"]) == 0
    assert calls == [False]
    assert "PASS Candidate discovery validation" in capsys.readouterr().out
