"""Validate issue #95 teacher information architecture."""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

from vitrine.teacher_presentation import (
    TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION,
    TeacherCandidateDetail,
    TeacherCandidateSection,
    TeacherPortfolioOverview,
    TeacherProfileBinding,
    TeacherProfileSection,
    TeacherSubjectLink,
)

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_teacher_presentation.py",
    "tests/test_portfolio_menu.py",
    "tests/test_candidate_inbox_menu.py",
    "tests/test_candidate_inbox.py",
    "tests/test_candidate_inbox_acceptance.py",
    "tests/test_candidate_current_evaluation.py",
    "tests/test_candidate_review_menu.py",
    "tests/test_candidate_review.py",
    "tests/test_candidate_review_actions.py",
    "tests/test_working_composition_menu.py",
    "tests/test_current_portfolio_surface.py",
    "tests/test_current_portfolio_menu.py",
    "tests/test_current_portfolio_execution.py",
    "tests/test_attention_menu.py",
    "tests/test_profile_services.py",
    "tests/test_teacher_information_architecture_acceptance.py",
    "tests/test_validate_teacher_information_architecture.py",
)

REQUIRED_DOCS = (
    "docs/contracts/teacher-information-architecture-v1.md",
    "docs/development/teacher-information-architecture.md",
    "docs/validation/issue-95-teacher-information-architecture-validation.md",
)

FORBIDDEN_PRESENTATION_IMPORTS = frozenset(
    {
        "vitrine.candidate_services",
        "vitrine.curation_services",
        "vitrine.current_portfolio_execution",
        "vitrine.snapshot_services",
        "vitrine.storage",
    }
)

FORBIDDEN_PRESENTATION_CALLS = frozenset(
    {
        "bind_portfolio_profile",
        "commit_record_batch",
        "create_snapshot_series",
        "decide_selection_proposal",
        "discover_and_evaluate_candidates",
        "execute_prepared_current_portfolio_build",
        "freeze_prepared_working_composition",
        "migrate_portfolio_profile",
        "place_selection",
        "replace_selection",
        "select_candidate_directly",
        "withdraw_selection",
    }
)


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _require_text(path: Path, *markers: str) -> None:
    source = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in source:
            raise RuntimeError(
                f"{_relative(path)} is missing required #95 marker: {marker}"
            )


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


def _imported_modules(tree: ast.AST) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            values.add(node.module)
    return values


def _validate_presentation_source(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_imports = sorted(
        _imported_modules(tree) & FORBIDDEN_PRESENTATION_IMPORTS
    )
    if forbidden_imports:
        raise RuntimeError(
            "teacher presentation imports mutation/authority surface(s): "
            f"{forbidden_imports}"
        )
    forbidden_calls = sorted(_called_names(tree) & FORBIDDEN_PRESENTATION_CALLS)
    if forbidden_calls:
        raise RuntimeError(
            "teacher presentation invokes mutation/authority call(s): "
            f"{forbidden_calls}"
        )


def validate(*, run_focused_tests: bool = True) -> None:
    if (
        TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION
        != "vitrine_teacher_information_architecture_v1"
    ):
        raise RuntimeError("teacher information architecture contract identity changed")

    expected_fields = {
        TeacherSubjectLink: {
            "subject_link_id",
            "school_year",
            "class_id",
            "student_id",
            "display_name",
            "status",
            "current_resolution",
        },
        TeacherCandidateSection: {"section_id", "label"},
        TeacherProfileSection: {"section_id", "label", "purpose", "obligation"},
    }
    for model, expected in expected_fields.items():
        if {field.name for field in fields(model)} != expected:
            raise RuntimeError(f"{model.__name__} presentation shape changed")

    for model in (
        TeacherCandidateDetail,
        TeacherPortfolioOverview,
        TeacherProfileBinding,
    ):
        field_names = {field.name for field in fields(model)}
        if "contract_version" not in field_names:
            raise RuntimeError(f"{model.__name__} lost contract identity")

    presentation_path = ROOT / "vitrine/teacher_presentation.py"
    _validate_presentation_source(presentation_path)

    required_surfaces = {
        "vitrine/portfolio_menu.py": (
            "_render_teacher_portfolio_overview",
            "_render_portfolio_technical_details",
            "_render_teacher_profile_binding",
            "_render_profile_binding_technical_details",
            "_portfolio_summary_labels",
            "T. Technical details / provenance",
        ),
        "vitrine/candidate_inbox_menu.py": (
            "Candidate Evidence",
            "Candidate Technical Details / Provenance",
        ),
        "vitrine/candidate_review_menu.py": (
            "Candidate Review",
            "Candidate Review Technical Details / Provenance",
        ),
        "vitrine/working_composition_menu.py": (
            "Working Composition Technical Details / Provenance",
            "_render_preparation_technical_details",
        ),
        "vitrine/current_portfolio_surface.py": (
            "teacher_current_portfolio_preparation_lines",
            "Technical Details / Provenance",
        ),
        "vitrine/current_portfolio_menu.py": (
            "Build Result Technical Details / Provenance",
            "T. Technical details / provenance",
        ),
        "vitrine/attention_menu.py": (
            "_render_teacher_attention",
            "_render_attention_technical_details",
            "Technical Details / Provenance",
        ),
    }
    for relative, markers in required_surfaces.items():
        _require_text(ROOT / relative, *markers)

    _require_text(
        ROOT / "vitrine/current_portfolio_cli.py",
        "print_current_portfolio_preparation",
    )
    _require_text(
        ROOT / "vitrine/attention_cli.py",
        "action=",
        "Observed state revision:",
    )

    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing #95 documentation: {relative}")

    _require_text(
        ROOT / "tests/test_teacher_information_architecture_acceptance.py",
        "A_portfolio_overview_teacher_readable",
        "J_privacy_boundaries",
        "test_issue95_acceptance_matrix_points_to_real_behavior_tests",
    )

    _require_text(
        ROOT / "scripts/check_package.py",
        '"vitrine/teacher_presentation.py"',
        '"docs/contracts/teacher-information-architecture-v1.md"',
        '"docs/development/teacher-information-architecture.md"',
        '"docs/validation/issue-95-teacher-information-architecture-validation.md"',
        '"scripts/validate_teacher_information_architecture.py"',
        '"scripts/smoke_test_teacher_information_architecture_wheel.py"',
        '"tests/test_teacher_information_architecture_acceptance.py"',
        '"tests/test_validate_teacher_information_architecture.py"',
        '"tests/test_teacher_presentation.py"',
    )
    _require_text(
        ROOT / "scripts/validate_repository.py",
        "scripts/validate_teacher_information_architecture.py",
        "scripts/smoke_test_teacher_information_architecture_wheel.py",
    )
    _require_text(
        ROOT / "pyproject.toml",
        '"scripts/validate_teacher_information_architecture.py"',
        '"scripts/smoke_test_teacher_information_architecture_wheel.py"',
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
                f"teacher information architecture focused validation failed: {detail}"
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
        print("PASS teacher information architecture validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(
            f"Teacher information architecture validation failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
