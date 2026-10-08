"""Validate Issue #102 completed Portfolio navigation and local-use boundaries."""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
import tomllib
from pathlib import Path

from vitrine.completed_portfolio import COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_completed_portfolio_history_issue102.py",
    "tests/test_completed_portfolio_menu_issue102.py",
    "tests/test_portfolio_output_opening_issue102.py",
    "tests/test_completed_portfolio_open_actions_issue102.py",
    "tests/test_completed_portfolio_actions_issue102.py",
    "tests/test_completed_portfolio_verification_menu_issue102.py",
    "tests/test_completed_portfolio_build_updated_issue102.py",
    "tests/test_current_portfolio_menu.py",
    "tests/test_portfolio_presentation_workflow_issue101.py",
    "tests/test_portfolio_presentation_verification_issue101.py",
)

RUNTIME = (
    "vitrine/completed_portfolio.py",
    "vitrine/completed_portfolio_actions.py",
    "vitrine/completed_portfolio_menu.py",
    "vitrine/portfolio_output_opening.py",
)

REQUIRED_DOCS = (
    "docs/contracts/completed-portfolio-navigation-v1.md",
    "docs/development/completed-portfolio-navigation.md",
    "docs/validation/issue-102-completed-portfolio-navigation-validation.md",
)

FORBIDDEN_SIBLING_IMPORT_ROOTS = frozenset(
    {"scoreform", "quillan", "concord", "portia", "meridian"}
)


def _require_text(path: Path, *markers: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"missing Issue #102 file: {path.relative_to(ROOT)}")
    source = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in source:
            raise RuntimeError(
                f"{path.relative_to(ROOT)} is missing Issue #102 marker: {marker}"
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


def _validate_contract() -> None:
    if (
        COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION
        != "vitrine_completed_portfolio_history_v1"
    ):
        raise RuntimeError("completed Portfolio history contract identity changed")


def _validate_runtime_boundaries() -> None:
    for relative in RUNTIME:
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"missing Issue #102 runtime module: {relative}")
        forbidden = _import_roots(path) & FORBIDDEN_SIBLING_IMPORT_ROOTS
        if forbidden:
            raise RuntimeError(
                f"{relative} imports optional producer package(s): {sorted(forbidden)}"
            )

    _require_text(
        ROOT / "vitrine/completed_portfolio.py",
        "project_completed_portfolio_history",
        "SnapshotCurrentPointerRevision",
        "current_edition_number",
        "PortfolioPresentationArtifact",
        "SnapshotExportArtifact",
    )
    _require_text(
        ROOT / "vitrine/portfolio_output_opening.py",
        "verify_portfolio_presentation(",
        "verify_snapshot_export(",
        "safe_vitrine_descendant",
        "open_local_path",
        "opener: LocalOpener | None = None",
    )
    _require_text(
        ROOT / "vitrine/completed_portfolio_actions.py",
        "verify_snapshot_edition(",
        "verify_snapshot_export(",
        "verify_portfolio_presentation(",
        "build_student_portfolio_presentation(",
        "presentation_exists",
    )
    _require_text(
        ROOT / "vitrine/completed_portfolio_menu.py",
        "Verify Portfolio Now",
        "Create Student Portfolio Presentation",
        "Build Updated Edition",
        "BUILD_UPDATED_EDITION",
    )
    _require_text(
        ROOT / "vitrine/portfolio_menu.py",
        "completed_action == BUILD_UPDATED_EDITION",
        "run_current_portfolio_build_export_menu(",
    )
    _require_text(
        ROOT / "vitrine/current_portfolio_menu.py",
        "_run_post_build_continuation",
        "open_student_portfolio_html(",
        "open_printable_student_portfolio(",
        "open_student_portfolio_folder(",
    )


def _validate_release_anchors() -> None:
    released = (ROOT / "vitrine/released_producer_contracts.py").read_text(
        encoding="utf-8"
    )
    markers = (
        'release_version="0.6.4"',
        'wheel_filename="pds_core-0.6.4-py3-none-any.whl"',
        "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b",
        'release_version="0.12.0"',
        'wheel_filename="scoreform-0.12.0-py3-none-any.whl"',
        "84ad10ada72a99bebd5455d8c18a0725f9406f8279e57156f3e424efa5678d20",
        'release_version="0.10.5"',
        'wheel_filename="quillan-0.10.5-py3-none-any.whl"',
        "031e5a5455c222da6b9a7d8f72e7823dd4c61acde7d90ddce94b49d9bcbe123f",
        'release_version="0.3.0"',
        'wheel_filename="pds_concord-0.3.0-py3-none-any.whl"',
        "dd827f7059c91c79bd69b6190b3c673d6b3bbc02bc25fa666286bbf5883c5e12",
    )
    for marker in markers:
        if marker not in released:
            raise RuntimeError(f"current release qualification marker is missing: {marker}")


def _validate_package_boundary() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = tuple(data["project"].get("dependencies", ()))
    if dependencies != ("pds-core>=0.6.3,<0.7",):
        raise RuntimeError("#102 must preserve the Core-only base dependency boundary")

    mypy_files = tuple(data["tool"]["mypy"].get("files", ()))
    for required in (
        "scripts/validate_completed_portfolio_navigation.py",
        "scripts/smoke_test_completed_portfolio_navigation_wheel.py",
    ):
        if required not in mypy_files:
            raise RuntimeError(f"MyPy scope is missing Issue #102 script: {required}")

    package_check = (ROOT / "scripts/check_package.py").read_text(encoding="utf-8")
    required_package_markers = (
        *RUNTIME,
        *REQUIRED_DOCS,
        "scripts/validate_completed_portfolio_navigation.py",
        "scripts/smoke_test_completed_portfolio_navigation_wheel.py",
        "tests/test_validate_completed_portfolio_navigation_issue102.py",
        "tests/test_completed_portfolio_build_updated_issue102.py",
    )
    for required in required_package_markers:
        if f'"{required}"' not in package_check:
            raise RuntimeError(
                f"package-content guard is missing Issue #102 marker: {required}"
            )

    repository = (ROOT / "scripts/validate_repository.py").read_text(encoding="utf-8")
    for required in (
        "scripts/validate_completed_portfolio_navigation.py",
        "scripts/smoke_test_completed_portfolio_navigation_wheel.py",
    ):
        if f'"{required}"' not in repository:
            raise RuntimeError(
                f"repository validator is missing Issue #102 marker: {required}"
            )


def _validate_documentation() -> None:
    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing Issue #102 documentation: {relative}")
    _require_text(
        ROOT / REQUIRED_DOCS[0],
        "completed Edition != current Edition",
        "newest Edition != current Edition",
        "canonical record discovery != filesystem discovery",
        "local print/open != delivery",
        "Build Updated Edition != mutate historical Edition",
    )
    _require_text(
        ROOT / REQUIRED_DOCS[1],
        "LocalOpener",
        "Producer independence",
        "Build Updated Edition",
        "Current Working Composition",
    )
    _require_text(
        ROOT / REQUIRED_DOCS[2],
        "Core 0.6.4",
        "ScoreForm 0.12.0",
        "Quillan 0.10.5",
        "Concord 0.3.0",
        "installed-wheel",
    )
    _require_text(
        ROOT / "CHANGELOG.md",
        "Issue #102 Slice 6",
        "completed Portfolio",
        "Core 0.6.4",
    )


def validate(*, run_focused_tests: bool = True) -> None:
    _validate_contract()
    _validate_runtime_boundaries()
    _validate_release_anchors()
    _validate_package_boundary()
    _validate_documentation()

    if run_focused_tests:
        missing = [item for item in FOCUSED_TESTS if not (ROOT / item).is_file()]
        if missing:
            raise RuntimeError(
                "missing Issue #102 focused tests: " + ", ".join(missing)
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
            raise RuntimeError(f"Issue #102 focused validation failed: {detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-focused-tests", action="store_true")
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS Issue #102 completed Portfolio navigation validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Issue #102 validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
