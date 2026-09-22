"""Validate issue #96 Candidate evidence discovery/review acceptance."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from vitrine.candidate_discovery_presentation import (
    CANDIDATE_DISCOVERY_PRESENTATION_CONTRACT_VERSION,
)
from vitrine.candidate_evidence_artifact_preview import (
    CANDIDATE_EVIDENCE_ARTIFACT_PREVIEW_CONTRACT_VERSION,
)
from vitrine.candidate_evidence_presentation import (
    CANDIDATE_EVIDENCE_PRESENTATION_CONTRACT_VERSION,
)
from vitrine.candidate_evidence_preview import (
    CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION,
)

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_candidate_discovery.py",
    "tests/test_candidate_discovery_presentation.py",
    "tests/test_candidate_discovery_menu.py",
    "tests/test_candidate_evidence_presentation.py",
    "tests/test_candidate_evidence_preview.py",
    "tests/test_candidate_evidence_preview_revalidation.py",
    "tests/test_candidate_evidence_preview_structured.py",
    "tests/test_candidate_evidence_artifact_preview.py",
    "tests/test_candidate_evidence_preview_menu.py",
    "tests/test_candidate_inbox.py",
    "tests/test_candidate_inbox_menu.py",
    "tests/test_candidate_review.py",
    "tests/test_candidate_review_menu.py",
    "tests/test_candidate_evidence_review_acceptance.py",
    "tests/test_validate_candidate_evidence_review.py",
)

REQUIRED_DOCS = (
    "docs/contracts/candidate-evidence-review-v1.md",
    "docs/development/candidate-evidence-review.md",
    "docs/validation/issue-96-candidate-evidence-review-validation.md",
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
                f"{_relative(path)} is missing required #96 marker: {marker}"
            )


def validate(*, run_focused_tests: bool = True) -> None:
    contracts = {
        "Candidate evidence presentation": (
            CANDIDATE_EVIDENCE_PRESENTATION_CONTRACT_VERSION,
            "vitrine_candidate_evidence_presentation_v1",
        ),
        "Candidate discovery presentation": (
            CANDIDATE_DISCOVERY_PRESENTATION_CONTRACT_VERSION,
            "vitrine_candidate_discovery_presentation_v1",
        ),
        "Candidate evidence preview": (
            CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION,
            "vitrine_candidate_evidence_preview_v1",
        ),
        "Candidate Artifact preview": (
            CANDIDATE_EVIDENCE_ARTIFACT_PREVIEW_CONTRACT_VERSION,
            "vitrine_candidate_evidence_artifact_preview_v1",
        ),
    }
    for label, (actual, expected) in contracts.items():
        if actual != expected:
            raise RuntimeError(f"{label} contract identity changed")

    _require_text(
        ROOT / "vitrine/candidate_inbox_menu.py",
        "V. View evidence",
        "Candidate Technical Details / Provenance",
    )
    _require_text(
        ROOT / "vitrine/candidate_review_menu.py",
        "V. View evidence",
        "1. Select for this Portfolio",
        "2. Decline this proposed use",
        "Candidate Review Technical Details / Provenance",
    )
    _require_text(
        ROOT / "vitrine/portfolio_menu.py",
        "Discover Portfolio Evidence",
        "Discovery may create or update Candidate/Evaluation state.",
        "No work was selected or placed in a Portfolio section.",
        "Next: Review Candidates",
    )
    _require_text(
        ROOT / "vitrine/candidate_evidence_preview_menu.py",
        "TemporaryDirectory",
        "_MEDIA_SUFFIXES",
        "teacher_candidate_evidence_preview",
        "Nothing was selected or placed in the Portfolio.",
    )
    artifact_source = (
        ROOT / "vitrine/candidate_evidence_artifact_preview.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "quillan.academic_result_artifacts",
        "concord.academic_result_artifacts",
        "candidate_evidence_preview.artifact_source_integrity_failed",
    ):
        if marker not in artifact_source:
            raise RuntimeError(f"Artifact preview bridge lost public-contract marker: {marker}")
    for forbidden in (
        "snapshot_plan_id",
        "snapshot_attempt_id",
        "review.json",
    ):
        if forbidden in artifact_source:
            raise RuntimeError(
                f"Artifact preview bridge contains forbidden #96 coupling: {forbidden}"
            )

    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing #96 documentation: {relative}")

    _require_text(
        ROOT / "tests/test_candidate_evidence_review_acceptance.py",
        "A_candidate_names_instructional",
        "N_exact_provenance_remains_inspectable",
        "test_suppressed_evaluation_cannot_be_resolved_for_preview",
        "test_issue96_acceptance_matrix_points_to_real_behavior_tests",
    )
    _require_text(
        ROOT / "scripts/check_package.py",
        '"docs/contracts/candidate-evidence-review-v1.md"',
        '"docs/development/candidate-evidence-review.md"',
        '"docs/validation/issue-96-candidate-evidence-review-validation.md"',
        '"scripts/validate_candidate_evidence_review.py"',
        '"tests/test_candidate_evidence_review_acceptance.py"',
        '"tests/test_validate_candidate_evidence_review.py"',
    )
    _require_text(
        ROOT / "scripts/validate_repository.py",
        "scripts/validate_candidate_evidence_review.py",
    )
    _require_text(
        ROOT / "pyproject.toml",
        '"scripts/validate_candidate_evidence_review.py"',
    )
    _require_text(
        ROOT / "docs/contracts/teacher-information-architecture-v1.md",
        "Issue #96 extension — Candidate evidence presentation and preview",
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
                f"Candidate evidence review focused validation failed: {detail}"
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
        print("PASS Candidate evidence review validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Candidate evidence review validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
