"""Validate Issue #111 bounded Vitrine path/output naming integration."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

from vitrine.path_policy import (
    CUSTODY_TOKEN_MAX_LENGTH,
    PRESENTATION_DIRECTORY_MAX_LENGTH,
    PRESENTATION_FILENAME_MAX_LENGTH,
    PRESENTATION_ORDINAL_MAX,
    VITRINE_PATH_POLICY_VERSION,
)

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_path_policy_issue111.py",
    "tests/test_storage_bounded_paths_issue111.py",
    "tests/test_snapshot_bounded_custody_issue111.py",
    "tests/test_path_regressions_issue111.py",
    "tests/test_presentation_path_policy_issue111.py",
)

REQUIRED_DOCS = (
    "docs/contracts/vitrine-path-output-naming-v1.md",
    "docs/development/vitrine-path-surface-audit.md",
    "docs/validation/issue-111-path-output-naming-validation.md",
)

REQUIRED_RUNTIME_MARKERS: dict[str, tuple[str, ...]] = {
    "vitrine/path_policy.py": (
        'VITRINE_PATH_POLICY_VERSION: Final[str] = "vitrine_path_policy_v1"',
        "build_bounded_custody_token",
        "build_bounded_presentation_filename",
        "build_bounded_presentation_directory_name",
        "require_unique_presentation_components",
    ),
    "vitrine/storage/paths.py": (
        "records-bounded-v1",
        "record_custody_token",
        "bounded_record_revision_path",
    ),
    "vitrine/storage/store.py": (
        "resolve_record_revision_path",
        "both legacy and bounded custody",
    ),
    "vitrine/snapshot_custody.py": (
        "staging-bounded-v1",
        "editions-bounded-v1",
        "exports-bounded-v1",
        ".locks-bounded-v1",
        "snapshot_export_path_from_relative",
    ),
    "vitrine/snapshot_distribution.py": (
        "snapshot_export_path_from_relative",
        "bounded_snapshot_export_path",
    ),
    "vitrine/paper_reflection_materialization.py": (
        "retained_source_relative_path",
        "source.read_bytes()",
    ),
}


def _require_text(path: Path, *markers: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"missing Issue #111 file: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            raise RuntimeError(
                f"{path.relative_to(ROOT)} is missing Issue #111 marker: {marker}"
            )


def _validate_policy_constants() -> None:
    if VITRINE_PATH_POLICY_VERSION != "vitrine_path_policy_v1":
        raise RuntimeError("Vitrine path-policy identity changed")
    if CUSTODY_TOKEN_MAX_LENGTH != 28:
        raise RuntimeError("bounded custody token component changed")
    if PRESENTATION_FILENAME_MAX_LENGTH != 96:
        raise RuntimeError("presentation filename budget changed")
    if PRESENTATION_DIRECTORY_MAX_LENGTH != 80:
        raise RuntimeError("presentation directory budget changed")
    if PRESENTATION_ORDINAL_MAX != 9999:
        raise RuntimeError("presentation ordinal bound changed")


def _validate_package_boundary() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = tuple(data["project"].get("dependencies", ()))
    if dependencies != ("pds-core>=0.6.3,<0.7",):
        raise RuntimeError(
            "Issue #111 must not raise the Core dependency floor merely because "
            "final qualification targets Core 0.6.4"
        )

    mypy_files = tuple(data["tool"]["mypy"].get("files", ()))
    for required in (
        "scripts/validate_path_output_naming.py",
        "scripts/smoke_test_path_output_naming_wheel.py",
    ):
        if required not in mypy_files:
            raise RuntimeError(
                f"Issue #111 MyPy scope is missing required script: {required}"
            )

    package_check = (ROOT / "scripts/check_package.py").read_text(encoding="utf-8")
    for required in (
        '"vitrine/path_policy.py"',
        '"docs/contracts/vitrine-path-output-naming-v1.md"',
        '"docs/development/vitrine-path-surface-audit.md"',
        '"docs/validation/issue-111-path-output-naming-validation.md"',
        '"scripts/validate_path_output_naming.py"',
        '"scripts/smoke_test_path_output_naming_wheel.py"',
        '"tests/test_path_policy_issue111.py"',
        '"tests/test_storage_bounded_paths_issue111.py"',
        '"tests/test_snapshot_bounded_custody_issue111.py"',
        '"tests/test_path_regressions_issue111.py"',
        '"tests/test_presentation_path_policy_issue111.py"',
    ):
        if required not in package_check:
            raise RuntimeError(
                f"package-content guard is missing Issue #111 marker: {required}"
            )

    repository_validator = (
        ROOT / "scripts/validate_repository.py"
    ).read_text(encoding="utf-8")
    for required in (
        '"scripts/validate_path_output_naming.py"',
        '"scripts/smoke_test_path_output_naming_wheel.py"',
    ):
        if required not in repository_validator:
            raise RuntimeError(
                f"repository validator is missing Issue #111 marker: {required}"
            )


def _validate_core_qualification_anchor() -> None:
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

    for relative in (
        "scripts/smoke_test_attention_next_actions_wheel.py",
        "scripts/smoke_test_operations_wheel.py",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        if 'importlib.metadata.version("pds-core") == "0.6.3"' in text:
            raise RuntimeError(
                f"{relative} still pins the historical Core 0.6.3 "
                "installed-smoke qualification"
            )
        if 'importlib.metadata.version("pds-core") == "0.6.4"' not in text:
            raise RuntimeError(
                f"{relative} is missing the current Core 0.6.4 "
                "installed-smoke qualification"
            )

    end_to_end = (ROOT / "scripts/verify_installed_end_to_end.py").read_text(
        encoding="utf-8"
    )
    if 'core_distribution.version == "0.6.3"' in end_to_end:
        raise RuntimeError(
            "installed end-to-end provenance still pins historical Core 0.6.3"
        )
    if 'core_distribution.version == "0.6.4"' not in end_to_end:
        raise RuntimeError(
            "installed end-to-end provenance is missing current Core 0.6.4"
        )


def _validate_ci_qualification_anchor() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    marker = "\n  live_installed_acceptance:\n"
    if marker not in workflow:
        raise RuntimeError("CI workflow is missing the live installed acceptance boundary")
    active, frozen = workflow.split(marker, 1)

    if "0.6.3" in active:
        raise RuntimeError(
            "active CI compatibility/qualification jobs still reference Core 0.6.3"
        )
    for required in (
        "pds_core-0.6.4-py3-none-any.whl",
        "releases/download/v0.6.4/pds_core-0.6.4-py3-none-any.whl",
    ):
        if active.count(required) < 2:
            raise RuntimeError(
                f"active CI compatibility/qualification jobs are missing Core 0.6.4: "
                f"{required}"
            )

    if "pds_core-0.6.3-py3-none-any.whl" not in frozen:
        raise RuntimeError(
            "frozen issue #71 live installed acceptance lost its audited Core 0.6.3 wheel"
        )
    if "releases/download/v0.6.3/pds_core-0.6.3-py3-none-any.whl" not in frozen:
        raise RuntimeError(
            "frozen issue #71 live installed acceptance lost its audited Core 0.6.3 URL"
        )


def validate(*, run_focused_tests: bool = True) -> None:
    _validate_policy_constants()

    for relative, markers in REQUIRED_RUNTIME_MARKERS.items():
        _require_text(ROOT / relative, *markers)

    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing Issue #111 documentation: {relative}")

    _validate_package_boundary()
    _validate_core_qualification_anchor()
    _validate_ci_qualification_anchor()

    _require_text(
        ROOT / "docs/README.md",
        "contracts/vitrine-path-output-naming-v1.md",
        "development/vitrine-path-surface-audit.md",
        "validation/issue-111-path-output-naming-validation.md",
    )
    _require_text(
        ROOT / "CHANGELOG.md",
        "Issue #111",
        "bounded",
        "Core 0.6.4",
    )

    if run_focused_tests:
        missing = [item for item in FOCUSED_TESTS if not (ROOT / item).is_file()]
        if missing:
            raise RuntimeError(
                "missing Issue #111 focused test files: " + ", ".join(missing)
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
            raise RuntimeError(
                f"Issue #111 focused validation failed: {detail}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-focused-tests", action="store_true")
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS Issue #111 bounded path/output naming validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Issue #111 validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
