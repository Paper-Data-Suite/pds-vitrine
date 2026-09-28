"""Smoke issue #66 guided review from isolated installed Core/Vitrine wheels."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "(no child output)"
        raise RuntimeError(
            "guided Candidate review installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-candidate-review-wheel-smoke-"
    ) as temporary:
        root = Path(temporary)
        environment = root / "venv"
        work = root / "work"
        work.mkdir()
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        _run(
            [str(python), "-m", "pip", "install", str(core_wheel.resolve())],
            cwd=work,
            env=env,
        )
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                str(vitrine_wheel.resolve()),
            ],
            cwd=work,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)

        code = r"""
import argparse
import importlib.util

from vitrine.candidate_review import (
    CANDIDATE_REVIEW_CONTRACT_VERSION,
    CANDIDATE_REVIEW_DECISIONS,
    CandidateReviewActionPlan,
    CandidateReviewDetail,
    execute_annotation_action,
    execute_candidate_decision,
    execute_curation_review,
    execute_reflection_action,
    execute_selection_placement,
    execute_selection_replacement,
    execute_selection_withdrawal,
    get_candidate_review_detail,
    list_candidate_review_entries,
    plan_annotation_creation,
    plan_candidate_decision,
    plan_curation_review,
    plan_reflection_creation,
    plan_selection_placement,
    plan_selection_replacement,
    plan_selection_withdrawal,
)
from vitrine.candidate_review_cli import (
    CANDIDATE_REVIEW_CLI_COMMANDS,
    configure_candidate_review_parsers,
)
from vitrine.candidate_review_menu import run_candidate_review_menu
from vitrine.curation_services import CURATION_OPERATIONS, reject_candidate_directly

assert CANDIDATE_REVIEW_CONTRACT_VERSION == "vitrine_guided_candidate_review_v1"
assert CANDIDATE_REVIEW_DECISIONS == frozenset({"select", "decline"})
assert CANDIDATE_REVIEW_CLI_COMMANDS == frozenset(
    {"review", "decide", "annotation", "reflection", "curation-review"}
)
assert "direct_decline" in CURATION_OPERATIONS
assert callable(reject_candidate_directly)
assert CandidateReviewDetail is not None
assert CandidateReviewActionPlan is not None
for value in (
    list_candidate_review_entries,
    get_candidate_review_detail,
    plan_candidate_decision,
    execute_candidate_decision,
    plan_selection_placement,
    execute_selection_placement,
    plan_selection_withdrawal,
    execute_selection_withdrawal,
    plan_selection_replacement,
    execute_selection_replacement,
    plan_annotation_creation,
    execute_annotation_action,
    plan_reflection_creation,
    execute_reflection_action,
    plan_curation_review,
    execute_curation_review,
    run_candidate_review_menu,
):
    assert callable(value)

parser = argparse.ArgumentParser()
root = parser.add_subparsers(dest="command", required=True)
candidate = root.add_parser("candidate")
candidates = candidate.add_subparsers(dest="candidate_command", required=True)
configure_candidate_review_parsers(candidates)
assert parser.parse_args(["candidate", "review", "entry_1"]).candidate_command == "review"
parsed = parser.parse_args(
    [
        "candidate",
        "decide",
        "entry_1",
        "--decision",
        "decline",
        "--section-id",
        "evidence",
        "--actor-id",
        "teacher_1",
    ]
)
assert parsed.decision == "decline"
assert parsed.section_id == ["evidence"]

for name in ("scoreform", "quillan", "concord", "portia", "meridian"):
    assert importlib.util.find_spec(name) is None
"""
        _run([str(python), "-c", code], cwd=work, env=env)
        if list(work.iterdir()):
            raise RuntimeError(
                "guided Candidate review wheel smoke left current-directory residue"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated guided Candidate review/Selection wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(
            f"Guided Candidate review/Selection wheel smoke test failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
