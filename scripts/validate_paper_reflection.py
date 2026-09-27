"""Validate Issue #99 paper-native student Reflection integration."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from vitrine.paper_reflection_review import PAPER_REFLECTION_REVIEW_CONTRACT_VERSION
from vitrine.paper_reflection_workflow import PAPER_REFLECTION_WORKFLOW_CONTRACT_VERSION

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_paper_reflection_services.py",
    "tests/test_paper_reflection_routes.py",
    "tests/test_paper_reflection_printing.py",
    "tests/test_paper_reflection_evidence.py",
    "tests/test_paper_reflection_authorship.py",
    "tests/test_paper_reflection_packet.py",
    "tests/test_paper_reflection_workflow.py",
    "tests/test_paper_reflection_review.py",
    "tests/test_paper_reflection_menu.py",
    "tests/test_paper_reflection_returned_menu.py",
    "tests/test_current_portfolio_reflection.py",
)

REQUIRED_DOCS = (
    "docs/contracts/paper-native-reflection-v1.md",
    "docs/development/paper-native-reflection.md",
    "docs/validation/issue-99-paper-native-reflection-validation.md",
)

REQUIRED_RUNTIME_MARKERS: dict[str, tuple[str, ...]] = {
    "vitrine/paper_reflection_services.py": (
        "prepare_reflection_issuance",
        "ReflectionPromptIssuance",
    ),
    "vitrine/paper_reflection_printing.py": (
        "prepare_reflection_print_plan",
        "persist_reflection_print_route_registrations",
    ),
    "vitrine/paper_reflection_evidence.py": (
        "capture_returned_paper_evidence",
        "ReflectionReturnedPaperEvidence",
    ),
    "vitrine/paper_reflection_authorship.py": (
        "confirm_returned_paper_authorship",
        "finalize_confirmed_paper_reflection",
    ),
    "vitrine/manual_reflection_services.py": (
        "create_typed_reflection",
        "revise_typed_reflection",
    ),
    "vitrine/paper_reflection_materialization.py": (
        "PaperReflectionMaterialization",
        "read_paper_reflection_materialization_bytes",
    ),
    "vitrine/paper_reflection_workflow.py": (
        "PAPER_REFLECTION_WORKFLOW_CONTRACT_VERSION",
        "returned_needs_review",
        "confirmed_needs_recording",
        "recorded",
    ),
    "vitrine/paper_reflection_pdf.py": (
        "render_persisted_reflection_pdf",
        "PAPER_REFLECTION_PDF_FILENAME",
    ),
    "vitrine/paper_reflection_packet.py": (
        "issue_paper_reflection_packet",
        "render_issued_paper_reflection_packet",
    ),
    "vitrine/paper_reflection_review.py": (
        "PAPER_REFLECTION_REVIEW_CONTRACT_VERSION",
        "acquire_paper_reflection_evidence_preview",
        "selected_occurrence_ids",
    ),
    "vitrine/paper_reflection_menu.py": (
        "Prepare / print Reflection",
        "Review returned paper / confirm student author",
        "CONFIRM STUDENT AUTHOR",
        "Complete canonical Reflection recording",
    ),
}


def _require_text(path: Path, *markers: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"missing required #99 file: {path.relative_to(ROOT)}")
    source = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in source:
            raise RuntimeError(
                f"{path.relative_to(ROOT)} is missing required #99 marker: {marker}"
            )


def _validate_contracts() -> None:
    if PAPER_REFLECTION_WORKFLOW_CONTRACT_VERSION != "vitrine_paper_reflection_workflow_v1":
        raise RuntimeError("paper Reflection workflow contract identity changed")
    if PAPER_REFLECTION_REVIEW_CONTRACT_VERSION != "vitrine_paper_reflection_review_v1":
        raise RuntimeError("paper Reflection review contract identity changed")


def validate(*, run_focused_tests: bool = True) -> None:
    _validate_contracts()
    for relative, markers in REQUIRED_RUNTIME_MARKERS.items():
        _require_text(ROOT / relative, *markers)

    _require_text(
        ROOT / "vitrine" / "pds_module.py",
        "get_module_profile",
        "ModuleProfile",
        "vitrine",
    )
    model_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "vitrine" / "models").glob("*.py"))
    )
    for marker in (
        "ReflectionPromptIssuance",
        "ReflectionResponsePage",
        "ReflectionReturnedPaperEvidence",
        "ReflectionAuthorshipConfirmation",
        "ReflectionPaperFinalization",
    ):
        if marker not in model_sources:
            raise RuntimeError(
                f"Vitrine models package is missing required #99 marker: {marker}"
            )

    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing #99 documentation: {relative}")

    _require_text(
        ROOT / "pyproject.toml",
        '[project.entry-points."paper_data_suite.modules"]',
        "qrcode[pil]",
        "reportlab",
        '"scripts/validate_paper_reflection.py"',
        '"scripts/smoke_test_paper_reflection_wheel.py"',
    )
    _require_text(
        ROOT / "scripts" / "check_package.py",
        '"vitrine/paper_reflection_review.py"',
        '"vitrine/paper_reflection_packet.py"',
        '"vitrine/models/paper_reflection.py"',
        '"docs/contracts/paper-native-reflection-v1.md"',
        '"docs/development/paper-native-reflection.md"',
        '"docs/validation/issue-99-paper-native-reflection-validation.md"',
        '"scripts/validate_paper_reflection.py"',
        '"scripts/smoke_test_paper_reflection_wheel.py"',
        "missing Vitrine routing module-profile entry point",
        "missing qrcode runtime dependency",
        "missing reportlab runtime dependency",
    )
    _require_text(
        ROOT / "scripts" / "validate_repository.py",
        "scripts/validate_paper_reflection.py",
        "scripts/smoke_test_paper_reflection_wheel.py",
    )
    _require_text(
        ROOT / "docs" / "README.md",
        "contracts/paper-native-reflection-v1.md",
        "development/paper-native-reflection.md",
        "validation/issue-99-paper-native-reflection-validation.md",
    )
    _require_text(
        ROOT / "CHANGELOG.md",
        "Issue #99",
        "paper-native",
        "CONFIRM STUDENT AUTHOR",
    )

    if run_focused_tests:
        missing = [item for item in FOCUSED_TESTS if not (ROOT / item).is_file()]
        if missing:
            raise RuntimeError("missing focused #99 test files: " + ", ".join(missing))
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", *FOCUSED_TESTS, "-q"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"paper Reflection focused validation failed: {detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-focused-tests", action="store_true")
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS paper-native Reflection validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Paper-native Reflection validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
