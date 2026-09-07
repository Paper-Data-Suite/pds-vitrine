"""Validate the Issue #65 Create Portfolio for Student contract."""

from __future__ import annotations

import argparse
import ast
import inspect
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

from vitrine.portfolio_setup import (
    CREATE_PORTFOLIO_FOR_STUDENT_CONTRACT_VERSION,
    CreatePortfolioForStudentRequest,
    PortfolioSetupPlan,
    create_portfolio_for_student,
    plan_create_portfolio_for_student,
)

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_portfolio_setup_planner.py",
    "tests/test_portfolio_setup_atomic.py",
    "tests/test_portfolio_setup_menu.py",
    "tests/test_portfolio_setup_cli.py",
    "tests/test_portfolio_setup_acceptance.py",
    "tests/test_portfolio_menu.py",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "vitrine.producer_reader_services",
    "vitrine.scoreform_adapter",
    "vitrine.quillan_adapter",
    "vitrine.concord_adapter",
    "vitrine.candidate_services",
    "vitrine.curation_services",
    "vitrine.starter_profiles",
)

FORBIDDEN_CALLS = {
    "discover_and_evaluate_candidates",
    "install_starter_profile",
    "install_starter_profile_plan",
    "select_candidate_directly",
    "propose_candidate_selection",
    "place_selection",
    "replace_selection",
    "create_working_composition",
    "request_snapshot_build",
}

FORBIDDEN_IDENTITY_TOKENS = (
    "sequencematcher",
    "difflib",
    "fuzzy",
    "similarity",
    "levenshtein",
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
        if isinstance(node.func, ast.Name):
            values.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            values.add(node.func.attr)
    return values


def _has_argparse_command(tree: ast.AST, command: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_parser":
            continue
        if not node.args:
            continue
        value = node.args[0]
        if isinstance(value, ast.Constant) and value.value == command:
            return True
    return False


def validate(*, run_focused_tests: bool = True) -> None:
    if (
        CREATE_PORTFOLIO_FOR_STUDENT_CONTRACT_VERSION
        != "vitrine_create_portfolio_for_student_v1"
    ):
        raise RuntimeError("Create Portfolio for Student contract identity changed")

    request_fields = {field.name for field in fields(CreatePortfolioForStudentRequest)}
    if not {
        "student_reference",
        "purpose_kind",
        "profile_revision",
        "profile_context",
        "subject_action",
        "existing_subject_id",
        "identity_context",
        "title_snapshot",
        "description_snapshot",
    }.issubset(request_fields):
        raise RuntimeError(
            "Create Portfolio for Student request contract is incomplete"
        )

    plan_fields = {field.name for field in fields(PortfolioSetupPlan)}
    if not {
        "observed_state_revision",
        "subject_resolution",
        "resulting_links",
        "existing_portfolios",
        "profile_choices",
        "selected_profile",
        "effective_profile_context",
        "proposed_ids",
        "planned_record_kinds",
        "blocking_codes",
    }.issubset(plan_fields):
        raise RuntimeError("Create Portfolio for Student plan contract is incomplete")

    setup_path = ROOT / "vitrine" / "portfolio_setup.py"
    setup_source = setup_path.read_text(encoding="utf-8")
    setup_tree = ast.parse(setup_source)

    imports = _imported_modules(setup_tree)
    for forbidden in FORBIDDEN_IMPORT_PREFIXES:
        if any(
            module == forbidden or module.startswith(forbidden + ".")
            for module in imports
        ):
            raise RuntimeError(
                f"Portfolio setup imports forbidden workflow/source path: {forbidden}"
            )

    forbidden_calls = sorted(_called_names(setup_tree) & FORBIDDEN_CALLS)
    if forbidden_calls:
        raise RuntimeError(
            f"Portfolio setup calls forbidden automatic workflow: {forbidden_calls}"
        )

    lowered = setup_source.casefold()
    for token in FORBIDDEN_IDENTITY_TOKENS:
        if token in lowered:
            raise RuntimeError(
                f"Portfolio setup contains forbidden identity heuristic: {token}"
            )

    planner_source = inspect.getsource(plan_create_portfolio_for_student)
    if "commit_record_batch" in planner_source:
        raise RuntimeError("Portfolio setup planner must remain read-only")
    for required in (
        "ClassQualifiedStudentRef",
        "subject_choice_required",
        "profile_choice_required",
        "profile_purpose_mismatch",
    ):
        if required not in setup_source:
            raise RuntimeError(
                f"Portfolio setup contract marker is missing: {required}"
            )

    executor_source = inspect.getsource(create_portfolio_for_student)
    if executor_source.count("commit_record_batch(") != 1:
        raise RuntimeError(
            "Portfolio setup must perform one final canonical batch commit"
        )
    for required in (
        "_current_student_for_plan",
        "_revalidate_subject_plan",
        "_revalidate_profile_plan",
        "state_conflict",
    ):
        if required not in executor_source:
            raise RuntimeError(
                f"Portfolio setup revalidation marker is missing: {required}"
            )

    models_module = __import__("vitrine.models", fromlist=["*"])
    leaked = tuple(
        name
        for name in dir(models_module)
        if name.startswith(("PortfolioSetup", "StudentPortfolioSetup"))
    )
    if leaked:
        raise RuntimeError(f"guided setup leaked into canonical models: {leaked}")

    registry_source = (ROOT / "vitrine" / "record_registry.py").read_text(
        encoding="utf-8"
    )
    if "portfolio_setup" in registry_source.casefold():
        raise RuntimeError("guided setup must not add a canonical setup record")

    menu_source = (ROOT / "vitrine" / "portfolio_menu.py").read_text(encoding="utf-8")
    if '"1. Create Portfolio for Student"' not in menu_source:
        raise RuntimeError("teacher Portfolio menu does not expose guided setup")

    setup_menu_source = (ROOT / "vitrine" / "portfolio_setup_menu.py").read_text(
        encoding="utf-8"
    )
    if "CREATE PORTFOLIO" not in setup_menu_source:
        raise RuntimeError("guided setup final explicit confirmation is missing")
    if "_review_subject_identity_and_existing_portfolios(" not in setup_menu_source:
        raise RuntimeError("guided setup pre-Profile Subject review is missing")
    if '"Existing Portfolios"' not in setup_menu_source:
        raise RuntimeError("guided setup existing Portfolio review is missing")
    if "Known limitations:" not in setup_menu_source:
        raise RuntimeError("guided setup final Profile limitations are missing")

    cli_source = (ROOT / "vitrine" / "workflow_cli.py").read_text(encoding="utf-8")
    cli_tree = ast.parse(cli_source)
    if not _has_argparse_command(cli_tree, "create-for-student"):
        raise RuntimeError("direct create-for-student CLI is missing")
    if not _has_argparse_command(cli_tree, "create"):
        raise RuntimeError("primitive Portfolio create CLI was not preserved")
    if "--dry-run" not in cli_source:
        raise RuntimeError("create-for-student CLI dry-run is missing")

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
                f"Create Portfolio for Student focused validation failed: {detail}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-focused-tests", action="store_true")
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS Create Portfolio for Student validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(
            f"Create Portfolio for Student validation failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
