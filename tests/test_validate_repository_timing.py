from __future__ import annotations

import subprocess
from pathlib import Path

import scripts.validate_repository as validator


def test_run_records_and_prints_phase_timing(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    clock = iter((10.0, 12.5))
    monkeypatch.setattr(validator, "perf_counter", lambda: next(clock))

    def fake_run(command, **_kwargs):
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validator.subprocess, "run", fake_run)
    timings: list[validator.PhaseTiming] = []

    validator._run(
        ["python", "example.py"],
        cwd=tmp_path,
        env={},
        phase="example phase",
        timings=timings,
    )

    assert timings == [
        validator.PhaseTiming(phase="example phase", elapsed_seconds=2.5)
    ]
    assert "TIMING example phase: 2.500s" in capsys.readouterr().out


def test_run_records_timing_when_command_fails(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    clock = iter((20.0, 20.75))
    monkeypatch.setattr(validator, "perf_counter", lambda: next(clock))

    def fail_run(command, **_kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(validator.subprocess, "run", fail_run)
    timings: list[validator.PhaseTiming] = []

    try:
        validator._run(
            ["python", "broken.py"],
            cwd=tmp_path,
            env={},
            phase="broken phase",
            timings=timings,
        )
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError("expected subprocess failure")

    assert timings == [
        validator.PhaseTiming(phase="broken phase", elapsed_seconds=0.75)
    ]
    assert "TIMING broken phase: 0.750s" in capsys.readouterr().out


def test_print_timing_summary_is_stable(capsys) -> None:
    validator._print_timing_summary(
        [
            validator.PhaseTiming(phase="pytest", elapsed_seconds=3.125),
            validator.PhaseTiming(phase="mypy", elapsed_seconds=1.5),
        ],
        5.0,
    )

    assert capsys.readouterr().out == (
        "\n"
        "Validation timing summary:\n"
        "  pytest: 3.125s\n"
        "  mypy: 1.500s\n"
        "  TOTAL: 5.000s\n"
    )


def test_repository_gate_avoids_nested_focused_pytest_reexecution() -> None:
    commands = dict(validator.VALIDATOR_COMMANDS)
    assert commands["Candidate discovery"] == (
        "scripts/validate_candidate_discovery.py",
        "--skip-focused-tests",
    )
    assert commands["curation workflows"] == (
        "scripts/validate_curation_workflows.py",
        "--skip-focused-tests",
    )

