"""Validate issue #70 Vitrine suite module-operations integration."""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import fields
from pathlib import Path

from pds_core.module_operations import (
    MODULE_OPERATIONS_CONTRACT_VERSION,
    MODULE_OPERATIONS_ENTRY_POINT_GROUP,
    ModuleAttentionReport,
    ModuleAttentionSummary,
    ModuleOperationsNotice,
    ModuleOperationsRequest,
    ModuleOwnerActionRef,
    ModuleReadinessReport,
    validate_module_attention_report,
    validate_module_operations_profile,
    validate_module_readiness_report,
)

from vitrine.attention import (
    VITRINE_ATTENTION_CONTRACT_VERSION,
    VitrineAttentionNotice,
    VitrineAttentionReport,
    VitrineAttentionSummary,
    VitrineNextActionRef,
)
from vitrine.constants import VITRINE_MODULE_ID
from vitrine.operations_provider import (
    VITRINE_ATTENTION_CLASS_SCOPE_UNSUPPORTED,
    VITRINE_ATTENTION_WORKSPACE_REQUIRED,
    VITRINE_READINESS_STORAGE_BLOCKED,
    VITRINE_READINESS_WORKSPACE_REQUIRED,
    evaluate_vitrine_attention_for_core,
    evaluate_vitrine_readiness,
    project_vitrine_attention_to_core,
)
from vitrine.pds_operations import get_module_operations_profile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FOCUSED_TESTS = (
    "tests/test_pds_operations.py",
    "tests/test_metadata.py",
    "tests/test_side_effects.py",
    "tests/test_operations_package_contract.py",
    "tests/test_validate_workspace_relocation.py",
    "tests/test_validate_suite_operations_integration.py",
)

REQUIRED_DOCS = (
    "docs/contracts/suite-operations-integration-v1.md",
    "docs/development/suite-operations-integration.md",
    "docs/validation/issue-70-suite-operations-integration-validation.md",
)

REQUIRED_SDIST_FILES = (
    *REQUIRED_DOCS,
    "scripts/smoke_test_operations_wheel.py",
    "scripts/validate_workspace_relocation.py",
    "scripts/validate_suite_operations_integration.py",
    "tests/test_pds_operations.py",
    "tests/test_operations_package_contract.py",
    "tests/test_validate_workspace_relocation.py",
    "tests/test_validate_suite_operations_integration.py",
)

FORBIDDEN_SIBLING_IMPORT_ROOTS = frozenset(
    {
        "scoreform",
        "quillan",
        "concord",
        "portia",
        "meridian",
        "paper_data_suite",
    }
)

FORBIDDEN_ACTION_FRAGMENTS = (
    "/",
    "\\",
    "://",
    "python ",
    "vitrine ",
    "--",
    "?",
    "#",
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
                f"{_relative(path)} is missing required #70 marker: {marker}"
            )


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _validate_project_contract() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("pyproject project table is missing")
    if project.get("dependencies") != ["pds-core>=0.6.3,<0.7"]:
        raise RuntimeError("Issue #70 must preserve the Core 0.6.3 runtime floor")
    if project.get("scripts") != {"vitrine": "vitrine.cli:main"}:
        raise RuntimeError("Issue #70 must preserve the vitrine console script")

    entry_points = project.get("entry-points")
    expected = {
        MODULE_OPERATIONS_ENTRY_POINT_GROUP: {
            "vitrine": "vitrine.pds_operations:get_module_operations_profile"
        }
    }
    if entry_points != expected:
        raise RuntimeError(
            "Issue #70 requires exactly one Vitrine operations entry point"
        )

    dependencies = tuple(project.get("dependencies", ()))
    optional = project.get("optional-dependencies", {})
    if isinstance(optional, dict):
        dependency_sets = (
            dependencies,
            *(tuple(values) for values in optional.values()),
        )
    else:
        dependency_sets = (dependencies,)
    for requirement_set in dependency_sets:
        normalized = "\n".join(str(item) for item in requirement_set).casefold()
        for sibling in FORBIDDEN_SIBLING_IMPORT_ROOTS:
            if sibling in normalized:
                raise RuntimeError(
                    f"Issue #70 added forbidden sibling dependency: {sibling}"
                )

    mypy_files = tuple(data.get("tool", {}).get("mypy", {}).get("files", ()))
    for required in (
        "scripts/smoke_test_operations_wheel.py",
        "scripts/validate_workspace_relocation.py",
        "scripts/validate_suite_operations_integration.py",
    ):
        if required not in mypy_files:
            raise RuntimeError(f"Issue #70 MyPy scope is missing {required}")


def _validate_profile_contract() -> None:
    if MODULE_OPERATIONS_CONTRACT_VERSION != "1":
        raise RuntimeError("Core module-operations contract version changed")
    if MODULE_OPERATIONS_ENTRY_POINT_GROUP != "paper_data_suite.module_operations":
        raise RuntimeError("Core module-operations entry-point group changed")
    if VITRINE_MODULE_ID != "vitrine":
        raise RuntimeError("Vitrine module identity changed")

    profile = get_module_operations_profile()
    if validate_module_operations_profile(profile) is not profile:
        raise RuntimeError("Core did not return the validated Vitrine profile")
    if profile.module_id != "vitrine":
        raise RuntimeError("Vitrine operations profile module_id changed")
    if profile.supported_core_operations_contract_versions != frozenset({"1"}):
        raise RuntimeError("Vitrine operations profile support set changed")
    if profile.readiness_provider is None or profile.attention_provider is None:
        raise RuntimeError("Vitrine profile must expose readiness and attention")


def _validate_core_shapes() -> None:
    if {field.name for field in fields(ModuleReadinessReport)} != {
        "evaluation",
        "ready",
        "notices",
    }:
        raise RuntimeError("Core readiness report shape changed")
    if {field.name for field in fields(ModuleAttentionReport)} != {
        "evaluation",
        "summaries",
        "notices",
    }:
        raise RuntimeError("Core attention report shape changed")
    if {field.name for field in fields(ModuleAttentionSummary)} != {
        "code",
        "label",
        "count",
        "class_id",
        "work_ref",
        "action",
    }:
        raise RuntimeError("Core attention summary shape changed")
    if {field.name for field in fields(ModuleOwnerActionRef)} != {
        "module_id",
        "action_id",
    }:
        raise RuntimeError("Core owner-action shape changed")
    if {field.name for field in fields(ModuleOperationsNotice)} != {
        "code",
        "summary",
        "action",
    }:
        raise RuntimeError("Core operations notice shape changed")


def _validate_source_boundaries() -> None:
    pds_path = ROOT / "vitrine" / "pds_operations.py"
    provider_path = ROOT / "vitrine" / "operations_provider.py"
    for path in (pds_path, provider_path):
        forbidden_roots = _imported_roots(path) & FORBIDDEN_SIBLING_IMPORT_ROOTS
        if forbidden_roots:
            raise RuntimeError(
                f"{_relative(path)} imports sibling package(s): {sorted(forbidden_roots)}"
            )

    pds_source = pds_path.read_text(encoding="utf-8")
    module_tree = ast.parse(pds_source)
    module_level_calls = [
        node
        for node in module_tree.body
        if isinstance(node, (ast.Expr, ast.Assign, ast.AnnAssign))
        and any(isinstance(child, ast.Call) for child in ast.walk(node))
    ]
    if module_level_calls:
        raise RuntimeError("pds_operations must not perform module-level calls")
    for forbidden_marker in (
        "resolve_workspace_root",
        "ensure_workspace_root",
        "inspect_workspace_root",
        "load_current_state",
        "evaluate_vitrine_attention(",
    ):
        if forbidden_marker in pds_source:
            raise RuntimeError(
                "profile module must not resolve or evaluate workspace state: "
                f"{forbidden_marker}"
            )

    _require_text(
        provider_path,
        "if request.class_id is not None:",
        "VITRINE_ATTENTION_CLASS_SCOPE_UNSUPPORTED",
        "evaluate_vitrine_attention(Path(request.workspace_root))",
        "class_id=None",
        "work_ref=None",
        "action_id=action.action_id",
        "audit_canonical_storage(workspace.root)",
    )


def _validate_readiness_semantics() -> None:
    missing = evaluate_vitrine_readiness(ModuleOperationsRequest())
    if validate_module_readiness_report(
        missing, expected_module_id=VITRINE_MODULE_ID
    ) is not missing:
        raise RuntimeError("readiness report did not revalidate through Core")
    if missing.evaluation != "unavailable" or missing.ready is not None:
        raise RuntimeError("missing workspace must remain readiness unavailable")
    if tuple(item.code for item in missing.notices) != (
        VITRINE_READINESS_WORKSPACE_REQUIRED,
    ):
        raise RuntimeError("missing-workspace readiness notice changed")

    with tempfile.TemporaryDirectory(prefix="vitrine-operations-ready-") as raw:
        workspace = Path(raw)
        before = tuple(workspace.iterdir())
        ready = evaluate_vitrine_readiness(
            ModuleOperationsRequest(
                workspace_root=workspace,
                active_school_year="2026-2027",
                class_id="english-10",
            )
        )
        if ready.evaluation != "evaluated" or ready.ready is not True:
            raise RuntimeError("empty shared workspace must be Vitrine-ready")
        if ready.notices:
            raise RuntimeError(
                "healthy empty workspace must not emit readiness notices"
            )
        if tuple(workspace.iterdir()) != before or (workspace / "vitrine").exists():
            raise RuntimeError("readiness evaluation mutated an empty workspace")

        namespace = workspace / "vitrine"
        namespace.mkdir()
        blocked_before = tuple(
            sorted(path.relative_to(workspace) for path in workspace.rglob("*"))
        )
        blocked = evaluate_vitrine_readiness(
            ModuleOperationsRequest(workspace_root=workspace)
        )
        blocked_after = tuple(
            sorted(path.relative_to(workspace) for path in workspace.rglob("*"))
        )
        if blocked.evaluation != "evaluated" or blocked.ready is not False:
            raise RuntimeError("diagnosable incomplete Vitrine state must be not ready")
        if tuple(item.code for item in blocked.notices) != (
            VITRINE_READINESS_STORAGE_BLOCKED,
        ):
            raise RuntimeError("blocked readiness notice changed")
        if blocked_after != blocked_before:
            raise RuntimeError("blocked readiness evaluation mutated Vitrine state")


def _validate_attention_adapter_semantics() -> None:
    no_workspace = evaluate_vitrine_attention_for_core(ModuleOperationsRequest())
    if no_workspace.evaluation != "unavailable" or no_workspace.summaries:
        raise RuntimeError("missing workspace must remain attention unavailable")
    if tuple(item.code for item in no_workspace.notices) != (
        VITRINE_ATTENTION_WORKSPACE_REQUIRED,
    ):
        raise RuntimeError("missing-workspace attention notice changed")

    class_scope = evaluate_vitrine_attention_for_core(
        ModuleOperationsRequest(
            workspace_root=ROOT / "does-not-need-to-exist",
            active_school_year="2026-2027",
            class_id="english-10",
        )
    )
    if class_scope.evaluation != "unavailable" or class_scope.summaries:
        raise RuntimeError("class-scoped Vitrine attention must be unavailable")
    if tuple(item.code for item in class_scope.notices) != (
        VITRINE_ATTENTION_CLASS_SCOPE_UNSUPPORTED,
    ):
        raise RuntimeError("class-scope attention notice changed")

    native = VitrineAttentionReport(
        contract_version=VITRINE_ATTENTION_CONTRACT_VERSION,
        evaluation="evaluated",
        observed_state_revision=7,
        summaries=(
            VitrineAttentionSummary(
                code="vitrine_selection_decision_pending",
                label="Selection decision pending",
                count=2,
                count_unit="selection_proposals",
                attention_class="workflow",
                portfolio_id="portfolio-cross-class",
                reason_codes=("proposal_undecided",),
                next_action=VitrineNextActionRef(
                    action_id="open_candidate_review",
                    portfolio_id="portfolio-cross-class",
                ),
            ),
        ),
        notices=(
            VitrineAttentionNotice(
                code="vitrine_attention_partial",
                summary="Some Vitrine attention sources remain unavailable.",
            ),
        ),
    )
    projected = project_vitrine_attention_to_core(native)
    if validate_module_attention_report(
        projected, expected_module_id=VITRINE_MODULE_ID
    ) is not projected:
        raise RuntimeError("attention report did not revalidate through Core")
    if projected.evaluation != "evaluated" or len(projected.summaries) != 1:
        raise RuntimeError("native evaluated attention did not map to Core")
    summary = projected.summaries[0]
    if (summary.code, summary.label, summary.count) != (
        "vitrine_selection_decision_pending",
        "Selection decision pending",
        2,
    ):
        raise RuntimeError("Core attention code/label/count mapping changed")
    if summary.class_id is not None or summary.work_ref is not None:
        raise RuntimeError("Core attention adapter invented class/work attribution")
    action = summary.action
    if action is None:
        raise RuntimeError("Core attention adapter dropped the owner action")
    if action != ModuleOwnerActionRef(
        module_id="vitrine", action_id="open_candidate_review"
    ):
        raise RuntimeError("Core owner action did not preserve Vitrine action identity")
    if "portfolio-cross-class" in action.action_id:
        raise RuntimeError("Core owner action encoded Portfolio identity")
    if any(
        fragment in action.action_id for fragment in FORBIDDEN_ACTION_FRAGMENTS
    ):
        raise RuntimeError("Core owner action contains executable/routing syntax")


def _validate_package_and_repository_wiring() -> None:
    from scripts.check_package import ALLOWED_RUNTIME_FILES
    from scripts.check_package import REQUIRED_SDIST_FILES as PACKAGE_SDIST_FILES

    for required in ("vitrine/pds_operations.py", "vitrine/operations_provider.py"):
        if required not in ALLOWED_RUNTIME_FILES:
            raise RuntimeError(f"package runtime allowlist is missing {required}")
    for required in REQUIRED_SDIST_FILES:
        if required not in PACKAGE_SDIST_FILES:
            raise RuntimeError(f"package sdist contract is missing {required}")

    repository_validator = ROOT / "scripts" / "validate_repository.py"
    _require_text(
        repository_validator,
        "scripts/validate_suite_operations_integration.py",
        "scripts/validate_workspace_relocation.py",
        "scripts/smoke_test_operations_wheel.py",
    )


def _validate_documentation() -> None:
    for relative in REQUIRED_DOCS:
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"Issue #70 documentation is missing {relative}")
    contract = ROOT / REQUIRED_DOCS[0]
    _require_text(
        contract,
        "request.class_id is not None",
        "evaluation = unavailable",
        "Portfolio attention may span classes",
        "backup copy != Vitrine export",
        "suite restore != Vitrine repair",
        "suite orchestrates",
        "Core defines neutral interoperability",
        "Vitrine owns Vitrine meaning and state",
    )


def validate(*, run_focused_tests: bool = True) -> None:
    _validate_project_contract()
    _validate_profile_contract()
    _validate_core_shapes()
    _validate_source_boundaries()
    _validate_readiness_semantics()
    _validate_attention_adapter_semantics()
    _validate_package_and_repository_wiring()
    _validate_documentation()

    if run_focused_tests:
        subprocess.run(
            [sys.executable, "-m", "pytest", *FOCUSED_TESTS],
            cwd=ROOT,
            check=True,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-focused-tests", action="store_true")
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
        print("PASS Vitrine suite operations integration validation")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Vitrine suite operations validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
