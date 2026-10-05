"""Validate Issue #101 student Portfolio presentation integration."""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
import tomllib
from pathlib import Path

from vitrine.portfolio_presentation import (
    STUDENT_PORTFOLIO_PRESENTATION_CLASS,
    STUDENT_PORTFOLIO_PRESENTATION_CONTRACT_VERSION,
)
from vitrine.portfolio_presentation_contract import (
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_ID,
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_VERSION,
)
from vitrine.portfolio_presentation_html import STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION
from vitrine.portfolio_presentation_package import (
    STUDENT_PORTFOLIO_FILE_INVENTORY_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_FILE_PACKAGE_CONTRACT_VERSION,
)
from vitrine.portfolio_presentation_pdf import STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_portfolio_presentation_issue101.py",
    "tests/test_portfolio_presentation_package_issue101.py",
    "tests/test_portfolio_presentation_html_issue101.py",
    "tests/test_portfolio_presentation_pdf_issue101.py",
    "tests/test_portfolio_presentation_workflow_issue101.py",
    "tests/test_portfolio_presentation_verification_issue101.py",
    "tests/test_current_portfolio_presentation_issue101.py",
    "tests/test_current_portfolio_execution.py",
    "tests/test_current_portfolio_menu.py",
    "tests/test_current_portfolio_cli.py",
    "tests/test_presentation_path_policy_issue111.py",
)

PRESENTATION_RUNTIME = (
    "vitrine/models/presentations.py",
    "vitrine/portfolio_presentation.py",
    "vitrine/portfolio_presentation_contract.py",
    "vitrine/portfolio_presentation_html.py",
    "vitrine/portfolio_presentation_package.py",
    "vitrine/portfolio_presentation_pdf.py",
    "vitrine/portfolio_presentation_services.py",
    "vitrine/portfolio_presentation_verification.py",
)

REQUIRED_DOCS = (
    "docs/contracts/student-portfolio-presentation-v1.md",
    "docs/development/student-portfolio-presentation.md",
    "docs/validation/issue-101-student-portfolio-presentation-validation.md",
)

FORBIDDEN_SIBLING_IMPORT_ROOTS = frozenset(
    {"scoreform", "quillan", "concord", "portia", "meridian"}
)


def _require_text(path: Path, *markers: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"missing Issue #101 file: {path.relative_to(ROOT)}")
    source = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in source:
            raise RuntimeError(
                f"{path.relative_to(ROOT)} is missing Issue #101 marker: {marker}"
            )


def _import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _validate_contracts() -> None:
    if (
        STUDENT_PORTFOLIO_PRESENTATION_CONTRACT_VERSION
        != "vitrine_student_portfolio_presentation_v1"
    ):
        raise RuntimeError("student Portfolio presentation contract identity changed")
    if STUDENT_PORTFOLIO_PRESENTATION_CLASS != "student_portfolio":
        raise RuntimeError("student Portfolio presentation class changed")
    if (
        STUDENT_PORTFOLIO_FILE_PACKAGE_CONTRACT_VERSION
        != "vitrine_student_portfolio_file_package_v1"
    ):
        raise RuntimeError("student Portfolio package contract identity changed")
    if (
        STUDENT_PORTFOLIO_FILE_INVENTORY_CONTRACT_VERSION
        != "vitrine_student_portfolio_file_inventory_v1"
    ):
        raise RuntimeError("student Portfolio file-inventory contract changed")
    if STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION != "vitrine_student_portfolio_html_v1":
        raise RuntimeError("student Portfolio HTML contract identity changed")
    if STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION != "vitrine_student_portfolio_pdf_v1":
        raise RuntimeError("student Portfolio PDF contract identity changed")
    if (
        STUDENT_PORTFOLIO_PRESENTATION_RENDERER_ID
        != "vitrine_student_portfolio_renderer"
        or STUDENT_PORTFOLIO_PRESENTATION_RENDERER_VERSION != "1"
        or STUDENT_PORTFOLIO_PRESENTATION_RENDERER_CONTRACT_VERSION
        != "vitrine_student_portfolio_renderer_v1"
    ):
        raise RuntimeError("student Portfolio composite renderer contract changed")


def _validate_runtime_boundaries() -> None:
    for relative in PRESENTATION_RUNTIME:
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"missing Issue #101 runtime module: {relative}")
        forbidden = _import_roots(path) & FORBIDDEN_SIBLING_IMPORT_ROOTS
        if forbidden:
            raise RuntimeError(
                f"{relative} imports optional producer package(s): {sorted(forbidden)}"
            )

    _require_text(
        ROOT / "vitrine/portfolio_presentation.py",
        '"portfolio_index"',
        '"student_portfolio"',
        "verify_snapshot_export(",
        "build_bounded_presentation_filename(",
        "build_bounded_presentation_directory_name(",
    )
    _require_text(
        ROOT / "vitrine/portfolio_presentation_package.py",
        "_presentation_staging_relative_path",
        "clear_student_portfolio_file_package_staging",
        "staging_root.rename(final_root)",
        "portfolio_presentation_package.staging_conflict",
    )
    _require_text(
        ROOT / "vitrine/portfolio_presentation_verification.py",
        "verify_snapshot_edition(",
        "verify_snapshot_export(",
        "portfolio_presentation_verification.unexpected_file",
        "portfolio_presentation_verification.source_mismatch",
        "require_unique_presentation_components",
    )
    _require_text(
        ROOT / "vitrine/portfolio_presentation_services.py",
        "build_student_portfolio_presentation",
        "resume_student_portfolio_presentation",
        'disposition="existing"',
        'disposition = "recovered" if recovered_package else "created"',
        "verify_portfolio_presentation(",
    )
    _require_text(
        ROOT / "vitrine/current_portfolio_execution.py",
        "build_student_portfolio_presentation(",
        "resume_current_portfolio_presentation",
        '"current_portfolio_build.presentation_failed"',
        '"resume_presentation_existing_edition"',
        "current_pointer_advanced=False",
    )


def _validate_package_boundary() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = tuple(data["project"].get("dependencies", ()))
    if dependencies != ("pds-core>=0.6.3,<0.7",):
        raise RuntimeError(
            "Issue #101 must retain Core-only base runtime dependency semantics"
        )
    paper = tuple(data["project"]["optional-dependencies"].get("paper", ()))
    for required in ("pypdfium2>=5.13,<6", "qrcode[pil]", "reportlab"):
        if required not in paper:
            raise RuntimeError(
                f"Issue #101 paper extra is missing renderer dependency: {required}"
            )

    mypy_files = tuple(data["tool"]["mypy"].get("files", ()))
    for required in (
        "scripts/validate_portfolio_presentation.py",
        "scripts/validate_student_portfolio_presentation_end_to_end.py",
        "scripts/smoke_test_portfolio_presentation_wheel.py",
    ):
        if required not in mypy_files:
            raise RuntimeError(
                f"Issue #101 MyPy scope is missing required script: {required}"
            )

    package_check = (ROOT / "scripts/check_package.py").read_text(encoding="utf-8")
    if "missing pypdfium2 paper-extra dependency" not in package_check:
        raise RuntimeError("package metadata guard does not enforce PDFium paper extra")
    required_package_markers = (
        *PRESENTATION_RUNTIME,
        *REQUIRED_DOCS,
        "scripts/validate_portfolio_presentation.py",
        "scripts/validate_student_portfolio_presentation_end_to_end.py",
        "scripts/smoke_test_portfolio_presentation_wheel.py",
        "tests/test_portfolio_presentation_end_to_end_issue101.py",
        "tests/test_validate_portfolio_presentation_issue101.py",
    )
    for required in required_package_markers:
        if f'"{required}"' not in package_check:
            raise RuntimeError(
                f"package-content guard is missing Issue #101 marker: {required}"
            )

    repository = (ROOT / "scripts/validate_repository.py").read_text(encoding="utf-8")
    for required in (
        "scripts/validate_portfolio_presentation.py",
        "scripts/validate_student_portfolio_presentation_end_to_end.py",
        "scripts/smoke_test_portfolio_presentation_wheel.py",
    ):
        if f'"{required}"' not in repository:
            raise RuntimeError(
                f"repository validator is missing Issue #101 marker: {required}"
            )


def _validate_core_qualification() -> None:
    verifier = (ROOT / "scripts/verify_core_wheel.py").read_text(encoding="utf-8")
    for marker in (
        'EXPECTED_CORE_VERSION = "0.6.4"',
        'EXPECTED_CORE_WHEEL_FILENAME = "pds_core-0.6.4-py3-none-any.whl"',
        "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b",
    ):
        if marker not in verifier:
            raise RuntimeError(
                f"Core 0.6.4 exact qualification anchor is missing: {marker}"
            )

    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    active = workflow.split("\n  live_installed_acceptance:\n", 1)[0]
    for marker in (
        "pds_core-0.6.4-py3-none-any.whl",
        "releases/download/v0.6.4/pds_core-0.6.4-py3-none-any.whl",
        'python scripts/validate_repository.py --core-wheel "$env:PDS_CORE_WHEEL"',
    ):
        if marker not in active:
            raise RuntimeError(
                f"active qualification is missing Core 0.6.4 marker: {marker}"
            )


def _validate_documentation() -> None:
    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing Issue #101 documentation: {relative}")
    _require_text(
        ROOT / "docs/contracts/student-portfolio-presentation-v1.md",
        "Slice 6",
        "Core 0.6.4",
        "installed-wheel",
        "Issue #101",
    )
    _require_text(
        ROOT / "docs/development/student-portfolio-presentation.md",
        "verify_portfolio_presentation",
        "resume_current_portfolio_presentation",
        "paper",
        "Core 0.6.4",
    )
    _require_text(
        ROOT / "docs/validation/issue-101-student-portfolio-presentation-validation.md",
        "20 focused acceptance claims",
        "Core 0.6.4",
        "installed-wheel",
        "synthetic Improvement Portfolio",
    )
    _require_text(
        ROOT / "CHANGELOG.md",
        "Issue #101 Slice 6",
        "Core 0.6.4",
        "installed-wheel",
    )


def validate(*, run_focused_tests: bool = True) -> None:
    _validate_contracts()
    _validate_runtime_boundaries()
    _validate_package_boundary()
    _validate_core_qualification()
    _validate_documentation()

    if run_focused_tests:
        missing = [item for item in FOCUSED_TESTS if not (ROOT / item).is_file()]
        if missing:
            raise RuntimeError(
                "missing Issue #101 focused tests: " + ", ".join(missing)
            )
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", *FOCUSED_TESTS, "-q"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"Issue #101 focused validation failed: {detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-focused-tests", action="store_true")
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS Issue #101 student Portfolio presentation validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Issue #101 validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
