"""Validate the issue #66 guided Candidate review and Selection contract."""

from __future__ import annotations

import argparse
import ast
import inspect
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

from vitrine.candidate_review import (
    CANDIDATE_REVIEW_CONTRACT_VERSION,
    CANDIDATE_REVIEW_DECISIONS,
    CandidateReviewActionPlan,
    CandidateReviewDetail,
    CandidateReviewReplacementActionPlan,
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
    plan_annotation_revision,
    plan_candidate_decision,
    plan_curation_review,
    plan_reflection_creation,
    plan_reflection_revision,
    plan_selection_placement,
    plan_selection_replacement,
    plan_selection_withdrawal,
)
from vitrine.candidate_review_cli import CANDIDATE_REVIEW_CLI_COMMANDS
from vitrine.curation_services import CURATION_OPERATIONS, reject_candidate_directly

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_candidate_review.py",
    "tests/test_candidate_review_actions.py",
    "tests/test_candidate_review_selection_management.py",
    "tests/test_candidate_review_curation_content.py",
    "tests/test_candidate_review_menu.py",
    "tests/test_candidate_review_cli.py",
    "tests/test_candidate_review_acceptance_matrix.py",
    "tests/test_portfolio_menu.py",
    "tests/test_workflow_cli.py",
    "tests/test_curation_services.py",
)

FORBIDDEN_GUIDED_IMPORT_PREFIXES = (
    "vitrine.candidate_services",
    "vitrine.producer_reader_services",
    "vitrine.scoreform_adapter",
    "vitrine.quillan_adapter",
    "vitrine.concord_adapter",
    "vitrine.quillan_artifact_source",
    "vitrine.concord_artifact_source",
    "vitrine.development_adapters",
    "vitrine.development_candidate_fixtures",
)

FORBIDDEN_GUIDED_CALLS = {
    "discover_and_evaluate_candidates",
}

FORBIDDEN_JUDGMENT_TOKENS = (
    "highest_score",
    "best_work",
    "latest_attempt",
    "mastery",
    "auto_select",
    "automatic_selection",
)

REQUIRED_DOCS = (
    "docs/contracts/guided-candidate-review-selection-v1.md",
    "docs/development/guided-candidate-review-selection.md",
    "docs/validation/issue-66-guided-candidate-review-selection-validation.md",
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


def _validate_guided_source(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = _imported_modules(tree)
    for forbidden in FORBIDDEN_GUIDED_IMPORT_PREFIXES:
        if any(
            module == forbidden or module.startswith(forbidden + ".")
            for module in imports
        ):
            raise RuntimeError(
                f"{path.relative_to(ROOT)} imports protected producer/discovery path: "
                f"{forbidden}"
            )
    forbidden_calls = sorted(_called_names(tree) & FORBIDDEN_GUIDED_CALLS)
    if forbidden_calls:
        raise RuntimeError(
            f"{path.relative_to(ROOT)} invokes Candidate discovery: {forbidden_calls}"
        )
    lowered = source.casefold()
    for token in FORBIDDEN_JUDGMENT_TOKENS:
        if token in lowered:
            raise RuntimeError(
                f"{path.relative_to(ROOT)} contains forbidden ranking/inference token: "
                f"{token}"
            )


def _require_text(path: Path, *markers: str) -> None:
    source = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in source:
            raise RuntimeError(
                f"{path.relative_to(ROOT)} is missing required #66 marker: {marker}"
            )


def validate(*, run_focused_tests: bool = True) -> None:
    if CANDIDATE_REVIEW_CONTRACT_VERSION != "vitrine_guided_candidate_review_v1":
        raise RuntimeError("guided Candidate review contract identity changed")
    if CANDIDATE_REVIEW_DECISIONS != frozenset({"select", "decline"}):
        raise RuntimeError("guided Candidate decision vocabulary changed")
    if CANDIDATE_REVIEW_CLI_COMMANDS != frozenset(
        {"review", "decide", "annotation", "reflection", "curation-review"}
    ):
        raise RuntimeError("guided Candidate task-level CLI vocabulary changed")

    detail_fields = {field.name for field in fields(CandidateReviewDetail)}
    required_detail_fields = {
        "observed_state_revision",
        "inbox_detail",
        "selectable",
        "current_review_evaluation_id",
        "curation_provenance_evaluation_id",
        "current_evaluation_differs_from_curation_provenance",
        "profile_requirements",
        "sections",
        "proposals",
        "selections",
        "placements",
        "annotations",
        "reflections",
        "reviews",
    }
    if not required_detail_fields.issubset(detail_fields):
        raise RuntimeError("guided Candidate review detail contract is incomplete")

    action_fields = {field.name for field in fields(CandidateReviewActionPlan)}
    required_action_fields = {
        "observed_state_revision",
        "entry_id",
        "candidate_id",
        "current_review_evaluation_id",
        "curation_provenance_evaluation_id",
        "decision",
        "selection_proposal_id",
        "proposed_section_ids",
        "intended_profile_requirement_ids",
        "confirmation_phrase",
        "condition_acknowledgement_required",
    }
    if not required_action_fields.issubset(action_fields):
        raise RuntimeError("guided Candidate decision action plan is incomplete")

    replacement_fields = {
        field.name for field in fields(CandidateReviewReplacementActionPlan)
    }
    if not {
        "proposed_section_ids",
        "placement_dispositions",
        "arrangement_pointers",
        "observed_state_revision",
    }.issubset(replacement_fields):
        raise RuntimeError("guided replacement plan lost explicit intent/concurrency")

    required_callables = (
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
        plan_annotation_revision,
        execute_annotation_action,
        plan_reflection_creation,
        plan_reflection_revision,
        execute_reflection_action,
        plan_curation_review,
        execute_curation_review,
    )
    if any(not callable(value) for value in required_callables):
        raise RuntimeError("guided Candidate orchestration callable surface is incomplete")

    if "direct_decline" not in CURATION_OPERATIONS:
        raise RuntimeError("fresh direct decline is not an explicit curation operation")
    decline_source = inspect.getsource(reject_candidate_directly)
    for marker in (
        "SelectionProposal(",
        "SelectionDecision(",
        'decision="rejected"',
        "_validated_commit(",
    ):
        if marker not in decline_source:
            raise RuntimeError(f"fresh direct decline lost atomic history marker: {marker}")
    for forbidden in ("PortfolioSelection(", "PortfolioPlacement("):
        if forbidden in decline_source:
            raise RuntimeError(
                "fresh direct decline must not create positive Selection/Placement state"
            )

    candidate_review_path = ROOT / "vitrine" / "candidate_review.py"
    candidate_review_menu_path = ROOT / "vitrine" / "candidate_review_menu.py"
    candidate_review_cli_path = ROOT / "vitrine" / "candidate_review_cli.py"
    for path in (
        candidate_review_path,
        candidate_review_menu_path,
        candidate_review_cli_path,
    ):
        _validate_guided_source(path)

    _require_text(
        candidate_review_path,
        "list_candidate_inbox(",
        "get_candidate_inbox_detail(",
        "reject_candidate_directly(",
        "select_candidate_directly(",
        "place_selection(",
        "withdraw_selection(",
        "replace_selection(",
    )
    _require_text(
        candidate_review_menu_path,
        "run_candidate_review_menu",
        "plan_candidate_decision(",
        "execute_candidate_decision(",
        "plan_selection_replacement(",
    )
    _require_text(
        candidate_review_cli_path,
        '"review"',
        '"decide"',
        '"annotation"',
        '"reflection"',
        '"curation-review"',
    )

    portfolio_menu = ROOT / "vitrine" / "portfolio_menu.py"
    _require_text(
        portfolio_menu,
        '"3. Discover Candidates"',
        '"4. Review Candidates / Selections"',
        "run_candidate_review_menu(",
    )

    workflow_cli = ROOT / "vitrine" / "workflow_cli.py"
    _require_text(
        workflow_cli,
        "configure_candidate_review_parsers(candidates)",
        "if subcommand in CANDIDATE_REVIEW_CLI_COMMANDS:",
        "run_candidate_review_command(",
    )

    curation_source = (ROOT / "vitrine" / "curation_services.py").read_text(
        encoding="utf-8"
    )
    if "proposed_section_ids: tuple[str, ...] | None = None" not in curation_source:
        raise RuntimeError(
            "replace_selection does not expose compatibility-safe explicit Proposal section intent"
        )

    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing #66 documentation: {relative}")

    package_check = ROOT / "scripts" / "check_package.py"
    _require_text(
        package_check,
        '"vitrine/candidate_review.py"',
        '"vitrine/candidate_review_menu.py"',
        '"vitrine/candidate_review_cli.py"',
        '"docs/contracts/guided-candidate-review-selection-v1.md"',
        '"scripts/validate_candidate_review_selection.py"',
        '"scripts/smoke_test_candidate_review_selection_wheel.py"',
    )

    repository_validator = ROOT / "scripts" / "validate_repository.py"
    _require_text(
        repository_validator,
        "scripts/validate_candidate_review_selection.py",
        "scripts/smoke_test_candidate_review_selection_wheel.py",
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
            raise RuntimeError(
                f"guided Candidate review/Selection focused validation failed: {detail}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-focused-tests",
        action="store_true",
        help=(
            "Skip focused pytest when an enclosing repository gate already ran "
            "the complete suite."
        ),
    )
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS guided Candidate review and Selection validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(
            f"Guided Candidate review/Selection validation failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
