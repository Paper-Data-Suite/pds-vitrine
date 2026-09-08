"""Validate the issue #67 guided Working Composition contract."""

from __future__ import annotations

import argparse
import ast
import inspect
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

from vitrine.curation_services import (
    WorkingCompositionDerivation,
    create_working_composition,
    derive_working_composition,
)
from vitrine.working_composition import (
    REQUIREMENT_STATUSES,
    WORKING_COMPOSITION_CONTRACT_VERSION,
    WORKING_COMPOSITION_ERROR_CODES,
    WorkingCompositionPayloadPreview,
    WorkingCompositionPreparation,
    WorkingCompositionSectionSummary,
    WorkingCompositionSourceObservation,
    freeze_prepared_working_composition,
    prepare_working_composition,
)
from vitrine.working_composition_cli import WORKING_COMPOSITION_CLI_COMMANDS

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_working_composition.py",
    "tests/test_working_composition_menu.py",
    "tests/test_working_composition_cli.py",
    "tests/test_working_composition_acceptance_matrix.py",
    "tests/test_portfolio_menu.py",
    "tests/test_workflow_cli.py",
    "tests/test_curation_services.py",
    "tests/test_curation_workflows.py",
)

FORBIDDEN_GUIDED_IMPORT_PREFIXES = (
    "vitrine.audience_services",
    "vitrine.candidate_services",
    "vitrine.producer_reader_services",
    "vitrine.scoreform_adapter",
    "vitrine.quillan_adapter",
    "vitrine.concord_adapter",
    "vitrine.quillan_artifact_source",
    "vitrine.concord_artifact_source",
    "vitrine.snapshot_services",
    "vitrine.snapshot_planning",
    "vitrine.snapshot_materialization",
    "vitrine.snapshot_distribution",
    "vitrine.development_adapters",
    "vitrine.development_candidate_fixtures",
)

FORBIDDEN_GUIDED_CALLS = {
    "create_audience_context",
    "discover_and_evaluate_candidates",
    "execute_snapshot_build_attempt",
    "prepare_snapshot_build",
    "request_snapshot_build",
    "seal_snapshot_build_attempt",
    "start_snapshot_build_attempt",
}

REQUIRED_DOCS = (
    "docs/contracts/guided-working-composition-v1.md",
    "docs/development/guided-working-composition.md",
    "docs/validation/issue-67-guided-working-composition-validation.md",
)


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


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
                f"{_relative(path)} imports protected producer/audience/Snapshot path: "
                f"{forbidden}"
            )
    forbidden_calls = sorted(_called_names(tree) & FORBIDDEN_GUIDED_CALLS)
    if forbidden_calls:
        raise RuntimeError(
            f"{_relative(path)} invokes protected downstream/discovery call: "
            f"{forbidden_calls}"
        )


def _require_text(path: Path, *markers: str) -> None:
    source = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in source:
            raise RuntimeError(
                f"{_relative(path)} is missing required #67 marker: {marker}"
            )


def _validate_no_durable_preparation_record() -> None:
    for path in sorted((ROOT / "vitrine" / "models").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "class WorkingCompositionPreparation" in source:
            raise RuntimeError(
                "Working Composition preparation must remain transient, not a model record"
            )
        if "WORKING_COMPOSITION_PREPARATION_RECORD_TYPE" in source:
            raise RuntimeError(
                "Working Composition preparation record type must not be introduced"
            )


def validate(*, run_focused_tests: bool = True) -> None:
    if WORKING_COMPOSITION_CONTRACT_VERSION != "vitrine_guided_working_composition_v1":
        raise RuntimeError("guided Working Composition contract identity changed")

    expected_statuses = frozenset(
        {
            "satisfied_current_curation",
            "unresolved_missing",
            "optional_absent",
            "conditional_unresolved",
            "prohibited_clear",
            "audience_stage",
            "not_machine_evaluable",
        }
    )
    if REQUIREMENT_STATUSES != expected_statuses:
        raise RuntimeError("guided Working Composition Requirement vocabulary changed")

    expected_errors = {
        "working_composition.invalid_request",
        "working_composition.context_not_found",
        "working_composition.state_changed",
        "working_composition.composition_pointer_changed",
        "working_composition.source_state_changed",
        "working_composition.preparation_mismatch",
    }
    if not expected_errors.issubset(WORKING_COMPOSITION_ERROR_CODES):
        raise RuntimeError("guided Working Composition error vocabulary is incomplete")

    if WORKING_COMPOSITION_CLI_COMMANDS != frozenset({"prepare", "freeze"}):
        raise RuntimeError("guided Working Composition task-level CLI vocabulary changed")

    preparation_fields = {field.name for field in fields(WorkingCompositionPreparation)}
    if not {
        "observed_state_revision",
        "observed_composition_pointer_revision",
        "current_composition_revision",
        "predicted_composition_revision",
        "predicted_composition_pointer_revision",
        "disposition",
        "payload",
        "sections",
        "selections",
        "unplaced_selection_ids",
        "requirements",
        "source_observations",
        "reviews",
        "audience_rules",
        "requested_composition_note",
        "composition_note_will_persist",
        "preparation_fingerprint",
    }.issubset(preparation_fields):
        raise RuntimeError("guided Working Composition preparation contract is incomplete")

    payload_fields = {field.name for field in fields(WorkingCompositionPayloadPreview)}
    if payload_fields != {
        "selection_ids",
        "placement_ids",
        "arrangement_ids",
        "included_rationale_ids",
        "included_curation_revisions",
        "applicable_review_decision_ids",
        "related_profile_requirement_ids",
        "unresolved_obligation_codes",
        "coherence_state",
    }:
        raise RuntimeError("Working Composition payload preview diverged from canonical inventory")

    section_fields = {field.name for field in fields(WorkingCompositionSectionSummary)}
    if not {
        "order",
        "current_arrangement_id",
        "current_arrangement_revision",
        "current_arrangement_pointer_revision",
        "placements",
    }.issubset(section_fields):
        raise RuntimeError("section/Arrangement explanation lost exact ordering metadata")

    source_fields = {field.name for field in fields(WorkingCompositionSourceObservation)}
    if source_fields != {
        "selection_id",
        "candidate_id",
        "publication_id",
        "series_head_publication_id",
        "observed_series_state",
        "observed_withdrawal_state",
        "current_use_state",
    }:
        raise RuntimeError("bounded Core Publication observation contract changed")

    derivation_fields = {field.name for field in fields(WorkingCompositionDerivation)}
    if not {
        "state_revision",
        "observed_composition_pointer_revision",
        "current_composition_revision",
        "predicted_composition_revision",
        "predicted_composition_pointer_revision",
        "disposition",
        "selection_ids",
        "placement_ids",
        "arrangement_ids",
        "included_rationale_ids",
        "included_curation_revisions",
        "applicable_review_decision_ids",
        "related_profile_requirement_ids",
        "unresolved_obligation_codes",
        "coherence_state",
    }.issubset(derivation_fields):
        raise RuntimeError("shared canonical Working Composition derivation is incomplete")

    if any(
        not callable(value)
        for value in (
            derive_working_composition,
            prepare_working_composition,
            freeze_prepared_working_composition,
            create_working_composition,
        )
    ):
        raise RuntimeError("guided Working Composition callable surface is incomplete")

    preparation_source = inspect.getsource(prepare_working_composition)
    if "derive_working_composition(" not in preparation_source:
        raise RuntimeError("preparation no longer uses the shared canonical derivation")

    canonical_source = inspect.getsource(create_working_composition)
    for marker in (
        "_derive_working_composition(",
        "expected_derivation",
        "expected_source_observations",
        "curation.composition_preparation_mismatch",
    ):
        if marker not in canonical_source:
            raise RuntimeError(
                f"canonical Composition write lost prepared-guard marker: {marker}"
            )

    freeze_source = inspect.getsource(freeze_prepared_working_composition)
    for marker in (
        "current.state_revision",
        "composition_pointer_heads(",
        "_source_observations(",
        "_preparation_fingerprint(",
        "create_working_composition(",
    ):
        if marker not in freeze_source:
            raise RuntimeError(
                f"prepared freeze lost fail-closed revalidation marker: {marker}"
            )

    working_path = ROOT / "vitrine" / "working_composition.py"
    menu_path = ROOT / "vitrine" / "working_composition_menu.py"
    cli_path = ROOT / "vitrine" / "working_composition_cli.py"
    for path in (working_path, menu_path, cli_path):
        _validate_guided_source(path)

    working_source = working_path.read_text(encoding="utf-8")
    for forbidden in (
        "WorkingPortfolioCompositionRevision(",
        "WorkingPortfolioCompositionInventory(",
        "WorkingPortfolioCompositionPointerRevision(",
        "commit_record_batch(",
    ):
        if forbidden in working_source:
            raise RuntimeError(
                "guided preparation must not own canonical Composition persistence: "
                f"{forbidden}"
            )

    _require_text(
        working_path,
        "for section in profile.sections:",
        "arrangement.placement_ids",
        'requirement.requirement_kind == "audience"',
        "note_to_persist",
        "hashlib.sha256",
    )
    _require_text(
        menu_path,
        "prepare_working_composition(",
        "freeze_prepared_working_composition(",
        "FREEZE COMPOSITION",
        "This workflow does not create an Audience Context",
    )
    _require_text(
        cli_path,
        "WORKING_COMPOSITION_CLI_COMMANDS",
        '"prepare", "freeze"',
        "--preparation-fingerprint",
        "--expected-state-revision",
        "--expected-composition-pointer-revision",
        "freeze_prepared_working_composition(",
    )

    _validate_no_durable_preparation_record()

    portfolio_menu = ROOT / "vitrine" / "portfolio_menu.py"
    _require_text(
        portfolio_menu,
        '"5. Working Composition"',
        "run_working_composition_menu(",
    )

    workflow_cli = ROOT / "vitrine" / "workflow_cli.py"
    _require_text(
        workflow_cli,
        'comp_show = compositions.add_parser("show")',
        'comp_build = compositions.add_parser("build")',
        "configure_working_composition_parsers(compositions)",
        "if subcommand in WORKING_COMPOSITION_CLI_COMMANDS:",
        "run_working_composition_command(",
    )

    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing #67 documentation: {relative}")

    package_check = ROOT / "scripts" / "check_package.py"
    _require_text(
        package_check,
        '"vitrine/working_composition.py"',
        '"vitrine/working_composition_menu.py"',
        '"vitrine/working_composition_cli.py"',
        '"docs/contracts/guided-working-composition-v1.md"',
        '"scripts/validate_working_composition.py"',
        '"scripts/smoke_test_working_composition_wheel.py"',
        '"tests/test_working_composition_acceptance_matrix.py"',
    )

    repository_validator = ROOT / "scripts" / "validate_repository.py"
    _require_text(
        repository_validator,
        "scripts/validate_working_composition.py",
        "scripts/smoke_test_working_composition_wheel.py",
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
                f"guided Working Composition focused validation failed: {detail}"
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
        print("PASS guided Working Composition validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(
            f"Guided Working Composition validation failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
