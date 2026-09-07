"""Validate the issue #64 Candidate inbox architectural contract."""

from __future__ import annotations

import argparse
import ast
import inspect
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

from vitrine.candidate_inbox import (
    CANDIDATE_INBOX_CONDITION_ATTENTION_CODES,
    CANDIDATE_INBOX_CONTRACT_VERSION,
    CandidateInboxError,
    CandidateInboxQuery,
)
from vitrine.candidate_state import CandidateState
from vitrine.models import CandidateCurrentEvaluationPointerRevision
from vitrine.models.candidates import CANDIDATE_CONDITION_STATES

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_candidate_current_evaluation.py",
    "tests/test_candidate_inbox.py",
    "tests/test_candidate_inbox_status.py",
    "tests/test_candidate_inbox_acceptance.py",
    "tests/test_candidate_inbox_cli.py",
    "tests/test_candidate_inbox_menu.py",
    "tests/test_curation_services.py",
)

FORBIDDEN_INBOX_IMPORT_PREFIXES = (
    "vitrine.producer_reader_services",
    "vitrine.scoreform_adapter",
    "vitrine.quillan_adapter",
    "vitrine.concord_adapter",
    "vitrine.quillan_artifact_source",
    "vitrine.concord_artifact_source",
)

FORBIDDEN_MUTATION_CALLS = {
    "discover_and_evaluate_candidates",
    "select_candidate_directly",
    "propose_candidate_selection",
    "decide_selection_proposal",
    "place_selection",
    "replace_selection",
    "withdraw_selection",
    "migrate_portfolio_profile",
}

FORBIDDEN_JUDGMENT_TOKENS = (
    "highest_score",
    "best_work",
    "latest_attempt",
    "proficiency",
    "mastery",
)


def _imported_modules(tree: ast.AST) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            values.add(node.module)
    return values


def _called_names(tree: ast.AST) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name):
            values.add(function.id)
        elif isinstance(function, ast.Attribute):
            values.add(function.attr)
    return values


def _has_argparse_command(tree: ast.AST, command: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if (
            not isinstance(function, ast.Attribute)
            or function.attr != "add_parser"
            or not node.args
        ):
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and first.value == command:
            return True
    return False


def _has_subparser_destination(tree: ast.AST, destination: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not isinstance(function, ast.Attribute) or function.attr != "add_subparsers":
            continue
        for keyword in node.keywords:
            if (
                keyword.arg == "dest"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value == destination
            ):
                return True
    return False


def validate(*, run_focused_tests: bool = True) -> None:
    if CANDIDATE_INBOX_CONTRACT_VERSION != "vitrine_candidate_inbox_v1":
        raise RuntimeError("Candidate inbox contract identity changed")

    pointer_fields = {
        field.name for field in fields(CandidateCurrentEvaluationPointerRevision)
    }
    required_pointer_fields = {
        "candidate_id",
        "pointer_revision",
        "current_candidate_evaluation_id",
        "predecessor_pointer_revision",
        "previous_candidate_evaluation_id",
        "updated_at",
        "updated_by",
        "reason",
    }
    if not required_pointer_fields.issubset(pointer_fields):
        raise RuntimeError(
            "Candidate current-Evaluation pointer contract is incomplete"
        )

    resolution_source = inspect.getsource(CandidateState.resolve_current_evaluation)
    if "evaluated_at" in resolution_source or "max(" in resolution_source:
        raise RuntimeError(
            "Candidate current-Evaluation resolution must not use timestamps"
        )

    expected_conditions = CANDIDATE_CONDITION_STATES - {"ready_for_consideration"}
    if set(CANDIDATE_INBOX_CONDITION_ATTENTION_CODES) != expected_conditions:
        raise RuntimeError(
            "Candidate attention taxonomy does not cover every review condition"
        )

    try:
        CandidateInboxQuery(evaluation_outcomes=("suppressed",))
    except CandidateInboxError:
        pass
    else:
        raise RuntimeError("ordinary Candidate inbox queries must reject suppressed")

    inbox_path = ROOT / "vitrine" / "candidate_inbox.py"
    inbox_source = inbox_path.read_text(encoding="utf-8")
    tree = ast.parse(inbox_source)

    imports = _imported_modules(tree)
    for forbidden in FORBIDDEN_INBOX_IMPORT_PREFIXES:
        if any(
            module == forbidden or module.startswith(forbidden + ".")
            for module in imports
        ):
            raise RuntimeError(
                f"Candidate inbox imports protected producer source path: {forbidden}"
            )

    forbidden_calls = sorted(_called_names(tree) & FORBIDDEN_MUTATION_CALLS)
    if forbidden_calls:
        raise RuntimeError(
            f"Candidate inbox calls mutating/discovery services: {forbidden_calls}"
        )

    lowered = inbox_source.casefold()
    for token in FORBIDDEN_JUDGMENT_TOKENS:
        if token in lowered:
            raise RuntimeError(
                f"Candidate inbox contains forbidden ranking/judgment token: {token}"
            )

    workflow_cli = (ROOT / "vitrine" / "workflow_cli.py").read_text(encoding="utf-8")
    workflow_cli_tree = ast.parse(workflow_cli)
    if not _has_argparse_command(workflow_cli_tree, "inbox"):
        raise RuntimeError("direct Candidate inbox CLI is missing")
    if not _has_subparser_destination(
        workflow_cli_tree,
        "candidate_inbox_command",
    ):
        raise RuntimeError("Candidate inbox detail CLI is missing")

    menu_source = (ROOT / "vitrine" / "menu.py").read_text(encoding="utf-8")
    if '"5. Candidate Inbox"' not in menu_source:
        raise RuntimeError("workspace Candidate inbox menu entry is missing")

    inbox_menu_source = (ROOT / "vitrine" / "candidate_inbox_menu.py").read_text(
        encoding="utf-8"
    )
    if "Candidate Inbox Help" not in inbox_menu_source:
        raise RuntimeError("Candidate inbox standard Help navigation is missing")

    portfolio_menu = (ROOT / "vitrine" / "portfolio_menu.py").read_text(
        encoding="utf-8"
    )
    if "run_candidate_review_menu(" not in portfolio_menu:
        raise RuntimeError(
            "Portfolio Candidate review does not route through guided review"
        )

    candidate_review_menu = (
        ROOT / "vitrine" / "candidate_review_menu.py"
    ).read_text(encoding="utf-8")
    if "list_candidate_review_entries(" not in candidate_review_menu:
        raise RuntimeError(
            "guided Candidate review menu does not reuse guided review projection"
        )
    if (
        "CandidateInboxQuery(" not in candidate_review_menu
        or "portfolio_id=portfolio_id" not in candidate_review_menu
    ):
        raise RuntimeError(
            "guided Candidate review does not apply exact Portfolio filtering"
        )

    candidate_review = (ROOT / "vitrine" / "candidate_review.py").read_text(
        encoding="utf-8"
    )
    if (
        "list_candidate_inbox(" not in candidate_review
        or "get_candidate_inbox_detail(" not in candidate_review
    ):
        raise RuntimeError(
            "guided Candidate review does not reuse authoritative Candidate inbox services"
        )

    if run_focused_tests:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", *FOCUSED_TESTS, "-q"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"Candidate inbox focused validation failed: {detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-focused-tests",
        action="store_true",
        help=(
            "Skip focused pytest when an enclosing repository gate already "
            "ran the complete suite."
        ),
    )
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS Candidate inbox validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Candidate inbox validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
