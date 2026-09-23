"""Validate Issue #97 Selection/Placement domain-correct guidance."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

from vitrine.selection_placement_guidance import (
    SELECTION_PLACEMENT_GUIDANCE_CONTRACT_VERSION,
    SelectionPlacementGuidance,
    SelectionPlacementGuidanceError,
    SelectionPlacementSectionGuidance,
    profile_requirement_ids_for_sections,
    project_selection_placement_guidance,
)

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_selection_placement_guidance.py",
    "tests/test_candidate_review_selection_guidance.py",
    "tests/test_curation_selection_guidance.py",
    "tests/test_selection_proposal_revalidation.py",
    "tests/test_selection_placement_execution_guidance.py",
    "tests/test_selection_replacement_guidance.py",
    "tests/test_candidate_review_section_actionability.py",
    "tests/test_candidate_review_menu.py",
)

REQUIRED_DOCS = (
    "docs/contracts/selection-placement-guidance-v1.md",
    "docs/development/selection-placement-guidance.md",
    "docs/validation/issue-97-selection-placement-guidance-validation.md",
)


def _require_text(path: Path, *markers: str) -> None:
    source = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in source:
            raise RuntimeError(
                f"{path.relative_to(ROOT)} is missing required #97 marker: {marker}"
            )


def validate(*, run_focused_tests: bool = True) -> None:
    if (
        SELECTION_PLACEMENT_GUIDANCE_CONTRACT_VERSION
        != "vitrine_selection_placement_guidance_v1"
    ):
        raise RuntimeError("Selection/Placement guidance contract identity changed")

    guidance_fields = {field.name for field in fields(SelectionPlacementGuidance)}
    required_guidance_fields = {
        "contract_version",
        "portfolio_id",
        "profile_binding_id",
        "portfolio_profile_id",
        "profile_revision",
        "candidate_id",
        "candidate_evaluation_id",
        "operation",
        "selection_id",
        "releasing_placement_ids",
        "matched_profile_requirement_ids",
        "semantic_eligible_section_ids",
        "sections",
    }
    if not required_guidance_fields.issubset(guidance_fields):
        raise RuntimeError("Selection/Placement guidance projection is incomplete")

    section_fields = {
        field.name for field in fields(SelectionPlacementSectionGuidance)
    }
    required_section_fields = {
        "section_id",
        "label",
        "operation",
        "semantic_candidate_eligible",
        "placement_bearing",
        "obligation",
        "minimum_placements",
        "active_placement_count",
        "released_placement_count",
        "effective_placement_count",
        "maximum_placements",
        "remaining_capacity",
        "arrangement_pointer_state",
        "arrangement_pointer_revision",
        "current_actionable",
        "unavailability_reason_codes",
        "relevant_profile_requirement_ids",
    }
    if not required_section_fields.issubset(section_fields):
        raise RuntimeError("per-section actionability projection is incomplete")

    for value in (
        project_selection_placement_guidance,
        profile_requirement_ids_for_sections,
    ):
        if not callable(value):
            raise RuntimeError("shared Selection/Placement guidance callable is missing")

    if not issubclass(SelectionPlacementGuidanceError, Exception):
        raise RuntimeError("Selection/Placement guidance error contract changed")

    guidance_path = ROOT / "vitrine" / "selection_placement_guidance.py"
    _require_text(
        guidance_path,
        '"fresh_selection"',
        '"placement"',
        '"replacement"',
        '"candidate_not_semantically_eligible"',
        '"section_prohibited"',
        '"section_not_placement_bearing"',
        '"section_full"',
        '"arrangement_pointer_conflict"',
        '"selection_already_placed_in_section"',
        "released_placement_count",
        "profile_requirement_ids_for_sections",
    )

    curation_path = ROOT / "vitrine" / "curation_services.py"
    _require_text(
        curation_path,
        "_require_fresh_selection_intent(",
        "_require_current_placement_target(",
        "_require_current_replacement_targets(",
        "project_selection_placement_guidance(",
        "profile_requirement_ids_for_sections(",
    )

    review_path = ROOT / "vitrine" / "candidate_review.py"
    _require_text(
        review_path,
        "list_candidate_review_section_guidance(",
        "project_selection_placement_guidance(",
        'operation="fresh_selection"',
        'operation="placement"',
        'operation="replacement"',
    )

    menu_path = ROOT / "vitrine" / "candidate_review_menu.py"
    _require_text(
        menu_path,
        "list_candidate_review_section_guidance(",
        "current_actionable",
        "relevant_profile_requirement_ids",
    )

    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing #97 documentation: {relative}")

    package_check = ROOT / "scripts" / "check_package.py"
    _require_text(
        package_check,
        '"vitrine/selection_placement_guidance.py"',
        '"docs/contracts/selection-placement-guidance-v1.md"',
        '"docs/development/selection-placement-guidance.md"',
        '"docs/validation/issue-97-selection-placement-guidance-validation.md"',
        '"scripts/validate_selection_placement_guidance.py"',
        '"scripts/smoke_test_selection_placement_guidance_wheel.py"',
        '"tests/test_validate_selection_placement_guidance.py"',
    )

    repository_validator = ROOT / "scripts" / "validate_repository.py"
    _require_text(
        repository_validator,
        "scripts/validate_selection_placement_guidance.py",
        "scripts/smoke_test_selection_placement_guidance_wheel.py",
    )

    pyproject = ROOT / "pyproject.toml"
    _require_text(
        pyproject,
        '"scripts/validate_selection_placement_guidance.py"',
        '"scripts/smoke_test_selection_placement_guidance_wheel.py"',
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
                f"Selection/Placement guidance focused validation failed: {detail}"
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
        print("PASS Selection/Placement domain-correct guidance validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(
            f"Selection/Placement guidance validation failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
