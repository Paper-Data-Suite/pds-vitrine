"""Validate issue #68 Build and Export Current Portfolio contract."""

from __future__ import annotations

import argparse
import ast
import inspect
import subprocess
import sys
import tomllib
from dataclasses import fields
from pathlib import Path

from vitrine.current_portfolio_build import (
    CURRENT_PORTFOLIO_BUILD_BLOCKING_REASONS,
    CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
    CURRENT_PORTFOLIO_BUILD_ERROR_CODES,
    CURRENT_PORTFOLIO_EXPORT_FORMAT,
    CurrentPortfolioBuildPreparation,
    CurrentPortfolioDirectoryExportPreview,
    CurrentPortfolioGeneratedReflection,
    CurrentPortfolioPlannedItem,
    prepare_current_portfolio_build,
)
from vitrine.current_portfolio_execution import (
    CURRENT_PORTFOLIO_EXECUTION_ERROR_CODES,
    CurrentPortfolioBuildExportResult,
    execute_prepared_current_portfolio_build,
)
from vitrine.current_portfolio_reflection import (
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION,
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
    CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
    CurrentPortfolioReflectionRenderer,
)

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_current_portfolio_build.py",
    "tests/test_current_portfolio_build_planning.py",
    "tests/test_current_portfolio_reflection.py",
    "tests/test_current_portfolio_execution.py",
    "tests/test_current_portfolio_surface.py",
    "tests/test_current_portfolio_cli.py",
    "tests/test_current_portfolio_menu.py",
    "tests/test_current_portfolio_routing.py",
    "tests/test_current_portfolio_acceptance_matrix.py",
    "tests/test_working_composition.py",
    "tests/test_working_composition_acceptance_matrix.py",
    "tests/test_snapshot_materialization.py",
    "tests/test_snapshot_deferred_media.py",
    "tests/test_snapshot_custody.py",
    "tests/test_snapshot_services.py",
    "tests/test_quillan_artifact_source.py",
    "tests/test_concord_artifact_source.py",
)

CURRENT_PORTFOLIO_RUNTIME = (
    "vitrine/current_portfolio_build.py",
    "vitrine/current_portfolio_reflection.py",
    "vitrine/current_portfolio_execution.py",
    "vitrine/current_portfolio_surface.py",
    "vitrine/current_portfolio_cli.py",
    "vitrine/current_portfolio_menu.py",
)

REQUIRED_DOCS = (
    "docs/contracts/build-export-current-portfolio-v1.md",
    "docs/development/build-export-current-portfolio.md",
    "docs/validation/issue-68-build-export-current-portfolio-validation.md",
)

FORBIDDEN_DURABLE_TASK_MARKERS = (
    "class CurrentPortfolioBuildSession",
    "class PortfolioExportDraft",
    "class SnapshotWizard",
    "class BuildPreparationRecord",
)

FORBIDDEN_SIBLING_IMPORT_ROOTS = frozenset(
    {"scoreform", "quillan", "concord", "portia", "meridian"}
)

FORBIDDEN_PREPARATION_IMPORTS = frozenset(
    {
        "vitrine.audience_services",
        "vitrine.snapshot_distribution",
        "vitrine.snapshot_services",
    }
)

FORBIDDEN_PREPARATION_CALLS = frozenset(
    {
        "create_audience_context",
        "create_snapshot_series",
        "request_snapshot_build",
        "start_snapshot_build_attempt",
        "execute_snapshot_build_attempt",
        "seal_snapshot_build_attempt",
        "create_snapshot_directory_export",
    }
)

FORBIDDEN_POINTER_CALLS = frozenset(
    {
        "advance_snapshot_current_pointer",
        "set_snapshot_current_pointer",
        "create_snapshot_current_pointer",
        "create_snapshot_current_pointer_revision",
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
                f"{_relative(path)} is missing required #68 marker: {marker}"
            )


def _imported_modules(tree: ast.AST) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            values.add(node.module)
    return values


def _imported_roots(tree: ast.AST) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            values.add(node.module.split(".", 1)[0])
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


def _validate_runtime_source(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    sibling_imports = _imported_roots(tree) & FORBIDDEN_SIBLING_IMPORT_ROOTS
    if sibling_imports:
        raise RuntimeError(
            f"{_relative(path)} imports optional sibling package(s): "
            f"{sorted(sibling_imports)}"
        )


def _validate_preparation_source(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = _imported_modules(tree) & FORBIDDEN_PREPARATION_IMPORTS
    if imports:
        raise RuntimeError(
            f"{_relative(path)} imports canonical mutation service(s): "
            f"{sorted(imports)}"
        )
    calls = _called_names(tree) & FORBIDDEN_PREPARATION_CALLS
    if calls:
        raise RuntimeError(
            f"{_relative(path)} invokes canonical mutation call(s): "
            f"{sorted(calls)}"
        )


def _validate_execution_source(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    pointer_calls = _called_names(tree) & FORBIDDEN_POINTER_CALLS
    if pointer_calls:
        raise RuntimeError(
            f"{_relative(path)} implicitly advances Snapshot current pointer: "
            f"{sorted(pointer_calls)}"
        )


def _validate_no_durable_task_record() -> None:
    for path in sorted((ROOT / "vitrine" / "models").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_DURABLE_TASK_MARKERS:
            if marker in source:
                raise RuntimeError(
                    "Build/Export preparation must remain transient, not a model "
                    f"record: {marker} in {_relative(path)}"
                )


def _validate_core_only_runtime_dependency() -> None:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = tuple(payload["project"].get("dependencies", ()))
    if dependencies != ("pds-core>=0.6,<0.7",):
        raise RuntimeError(
            "Issue #68 must not add a hard runtime dependency beyond released Core"
        )
    mypy_files = tuple(payload["tool"]["mypy"].get("files", ()))
    for required in (
        "scripts/validate_current_portfolio_build_export.py",
        "scripts/smoke_test_current_portfolio_build_export_wheel.py",
    ):
        if required not in mypy_files:
            raise RuntimeError(
                f"Issue #68 MyPy scope is missing required script: {required}"
            )


def validate(*, run_focused_tests: bool = True) -> None:
    if (
        CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION
        != "vitrine_build_export_current_portfolio_v1"
    ):
        raise RuntimeError("Current Portfolio Build/Export contract identity changed")
    if CURRENT_PORTFOLIO_EXPORT_FORMAT != "directory_package":
        raise RuntimeError("Current Portfolio first-party export format changed")
    if (
        CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
        != "vitrine_portfolio_reflection_renderer_v1"
    ):
        raise RuntimeError("Current Portfolio Reflection renderer contract changed")
    if CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID != "vitrine_portfolio_reflection":
        raise RuntimeError("Current Portfolio Reflection renderer identity changed")
    if CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION != "1":
        raise RuntimeError("Current Portfolio Reflection renderer version changed")

    if not {
        "current_portfolio_build.invalid_request",
        "current_portfolio_build.context_not_found",
        "current_portfolio_build.state_changed",
        "current_portfolio_build.audience_rule_not_found",
        "current_portfolio_build.audience_context_invalid_choice",
        "current_portfolio_build.snapshot_series_invalid_choice",
        "current_portfolio_build.source_context_invalid",
        "current_portfolio_build.reflection_context_invalid",
    }.issubset(CURRENT_PORTFOLIO_BUILD_ERROR_CODES):
        raise RuntimeError(
            "Current Portfolio preparation error vocabulary is incomplete"
        )
    if not {
        "working_composition_requires_freeze",
        "unplaced_selections",
        "audience_context_choice_required",
        "snapshot_series_choice_required",
        "missing_required_reviews",
        "unresolved_obligations_acknowledgement_required",
        "source_artifact_unavailable",
        "source_provider_conflict",
        "unsupported_reflection_rendering",
        "unsupported_reflection_placement",
        "reflection_audience_prohibited",
        "directory_export_empty",
    }.issubset(CURRENT_PORTFOLIO_BUILD_BLOCKING_REASONS):
        raise RuntimeError(
            "Current Portfolio preparation blocking vocabulary is incomplete"
        )
    if not {
        "current_portfolio_build.snapshot_authority_denied",
        "current_portfolio_build.snapshot_authority_unresolved",
        "current_portfolio_build.producer_artifact_authorization_denied",
        "current_portfolio_build.producer_artifact_authorization_unresolved",
        "current_portfolio_build.materialization_failed",
        "current_portfolio_build.sealing_failed",
        "current_portfolio_build.edition_verification_failed",
        "current_portfolio_build.export_failed",
        "current_portfolio_build.export_verification_failed",
    }.issubset(CURRENT_PORTFOLIO_EXECUTION_ERROR_CODES):
        raise RuntimeError(
            "Current Portfolio execution error vocabulary is incomplete"
        )

    preparation_fields = {
        field.name for field in fields(CurrentPortfolioBuildPreparation)
    }
    if not {
        "observed_state_revision",
        "current_composition_pointer_revision",
        "current_composition_revision",
        "working_composition_preparation_fingerprint",
        "working_composition_disposition",
        "composition_inventory",
        "sections",
        "selections",
        "unplaced_selection_ids",
        "selected_audience_rule",
        "audience_context",
        "snapshot_series",
        "required_reviews",
        "missing_required_review_classes",
        "unresolved_obligation_codes",
        "acknowledged_obligation_codes",
        "planned_items",
        "generated_reflections",
        "directory_export",
        "warnings",
        "blocking_reasons",
        "preparation_fingerprint",
    }.issubset(preparation_fields):
        raise RuntimeError("Current Portfolio preparation contract is incomplete")

    planned_fields = {field.name for field in fields(CurrentPortfolioPlannedItem)}
    if not {
        "section_order",
        "position_in_section",
        "placement_id",
        "selection_id",
        "candidate_id",
        "candidate_evaluation_id",
        "source_publication_id",
        "source_artifact",
        "source_current_use_state",
        "materialization_kind",
        "provider_disposition",
        "target_relative_path",
        "media_type",
        "export_file",
        "permitted_omission_reason",
    }.issubset(planned_fields):
        raise RuntimeError("Current Portfolio planned-item explanation is incomplete")

    reflection_fields = {
        field.name for field in fields(CurrentPortfolioGeneratedReflection)
    }
    if not {
        "reflection_id",
        "reflection_revision",
        "reflection_requirement_id",
        "content_mode",
        "content_format",
        "language",
        "content_sha256",
        "renderer_id",
        "renderer_version",
        "renderer_contract_version",
        "renderer_configuration_sha256",
        "output_byte_size",
        "output_sha256",
        "supported",
    }.issubset(reflection_fields):
        raise RuntimeError("Current Portfolio Reflection preview is incomplete")

    export_fields = {
        field.name for field in fields(CurrentPortfolioDirectoryExportPreview)
    }
    if export_fields != {
        "export_plan_id",
        "export_format",
        "export_contract_version",
        "included_entry_plan_ids",
        "excluded_entry_plan_ids",
        "configuration_sha256",
    }:
        raise RuntimeError("Current Portfolio directory Export preview changed")

    result_fields = {field.name for field in fields(CurrentPortfolioBuildExportResult)}
    if not {
        "snapshot_build_request_id",
        "snapshot_build_plan_id",
        "snapshot_build_attempt_id",
        "attempt_terminal_outcome",
        "edition_number",
        "snapshot_export_artifact_id",
        "export_path",
        "current_pointer_advanced",
    }.issubset(result_fields):
        raise RuntimeError("Current Portfolio result lost durable stage identity")

    if not callable(prepare_current_portfolio_build):
        raise RuntimeError("Current Portfolio preparation callable is missing")
    if not callable(execute_prepared_current_portfolio_build):
        raise RuntimeError("Current Portfolio execution callable is missing")
    if not inspect.isclass(CurrentPortfolioReflectionRenderer):
        raise RuntimeError("Current Portfolio Reflection renderer is missing")

    for relative in CURRENT_PORTFOLIO_RUNTIME:
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"missing #68 runtime module: {relative}")
        _validate_runtime_source(path)

    build_path = ROOT / "vitrine/current_portfolio_build.py"
    _validate_preparation_source(build_path)
    _require_text(
        build_path,
        'working.disposition != "reuse_exact_current"',
        'blockers.append("unplaced_selections")',
        'producer_module_id == "scoreform"',
        '"assessment_summary"',
        'materialization_kind = "reference_only"',
        'provider_disposition = "reference_only_by_producer_contract"',
        'provider_disposition = "audience_prohibited"',
        'omission_reason = "audience_prohibited"',
        'materialization_kind="generated_vitrine"',
        "for section in preparation.sections:",
        "hashlib.sha256",
    )
    if "retained_source_path" in build_path.read_text(encoding="utf-8"):
        raise RuntimeError(
            "Current Portfolio planner must not infer ScoreForm retained paths"
        )

    reflection_path = ROOT / "vitrine/current_portfolio_reflection.py"
    _require_text(
        reflection_path,
        (
            'CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_MODE: Final[str] = '
            '"inline_text"'
        ),
        (
            'CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_FORMAT: Final[str] = '
            '"plain_text"'
        ),
        'CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE: Final[str] = "text/plain"',
        "reflection.content.encode(\"utf-8\")",
    )
    reflection_source = reflection_path.read_text(encoding="utf-8")
    for forbidden in ("open(", "urlopen(", "requests.", "httpx."):
        if forbidden in reflection_source:
            raise RuntimeError(
                "Current Portfolio Reflection renderer must not dereference "
                "external content"
            )

    execution_path = ROOT / "vitrine/current_portfolio_execution.py"
    _validate_execution_source(execution_path)
    _require_text(
        execution_path,
        "request_snapshot_build(",
        "start_snapshot_build_attempt(",
        "execute_snapshot_build_attempt(",
        "seal_snapshot_build_attempt(",
        "verify_snapshot_edition(",
        "create_snapshot_directory_export(",
        "verify_snapshot_export(",
        "current_pointer_advanced=False",
        "SnapshotSourceProviderRegistry",
    )

    surface_path = ROOT / "vitrine/current_portfolio_surface.py"
    _require_text(
        surface_path,
        "This rule constrains content; it is not recipient or disclosure authority.",
        "Verification is not disclosure permission.",
        "Export creation is not delivery or sending.",
    )

    cli_path = ROOT / "vitrine/current_portfolio_cli.py"
    menu_path = ROOT / "vitrine/current_portfolio_menu.py"
    _require_text(
        cli_path,
        '"build-export"',
        '"prepare"',
        '"execute"',
        "--preparation-fingerprint",
        "--expected-state-revision",
        "prepare_current_portfolio_build(",
        "execute_prepared_current_portfolio_build(",
    )
    _require_text(
        menu_path,
        'working.disposition != "reuse_exact_current"',
        "working.unplaced_selection_ids",
        "ACKNOWLEDGE OBLIGATIONS",
        "BUILD AND EXPORT",
        "prepare_current_portfolio_build(",
        "execute_prepared_current_portfolio_build(",
    )

    portfolio_menu = ROOT / "vitrine/portfolio_menu.py"
    _require_text(
        portfolio_menu,
        '"6. Build and Export Current Portfolio"',
        "run_current_portfolio_build_export_menu(",
    )

    workflow_cli = ROOT / "vitrine/workflow_cli.py"
    _require_text(
        workflow_cli,
        "configure_current_portfolio_build_export_parsers(portfolios)",
        "run_current_portfolio_build_export_command(",
        'request = snapshot.add_parser("request")',
        'plan = snapshot.add_parser("plan")',
        'build = snapshot.add_parser("build")',
        'verify = snapshot.add_parser("verify")',
        'export = snapshot.add_parser("export")',
        'custody = snapshot.add_parser("custody")',
    )

    _validate_no_durable_task_record()
    _validate_core_only_runtime_dependency()

    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing #68 documentation: {relative}")

    package_check = ROOT / "scripts/check_package.py"
    for relative in CURRENT_PORTFOLIO_RUNTIME:
        _require_text(package_check, f'"{relative}"')
    _require_text(
        package_check,
        '"docs/contracts/build-export-current-portfolio-v1.md"',
        '"docs/development/build-export-current-portfolio.md"',
        '"docs/validation/issue-68-build-export-current-portfolio-validation.md"',
        '"scripts/validate_current_portfolio_build_export.py"',
        '"scripts/smoke_test_current_portfolio_build_export_wheel.py"',
        '"tests/test_current_portfolio_acceptance_matrix.py"',
        '"tests/test_validate_current_portfolio_build_export.py"',
    )

    repository_validator = ROOT / "scripts/validate_repository.py"
    _require_text(
        repository_validator,
        "scripts/validate_current_portfolio_build_export.py",
        "scripts/smoke_test_current_portfolio_build_export_wheel.py",
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
                f"Current Portfolio Build/Export focused validation failed: {detail}"
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
        print("PASS Build and Export Current Portfolio validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(
            f"Build and Export Current Portfolio validation failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
