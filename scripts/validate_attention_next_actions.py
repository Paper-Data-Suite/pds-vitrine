"""Validate issue #69 Vitrine attention and next-action contract."""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
import tomllib
from dataclasses import fields
from pathlib import Path

from pds_core.module_operations import ModuleOwnerActionRef

import vitrine.attention as attention_module
from vitrine.attention import (
    VITRINE_ATTENTION_ACTION_IDS,
    VITRINE_ATTENTION_CLASSES,
    VITRINE_ATTENTION_CODES,
    VITRINE_ATTENTION_CONTRACT_VERSION,
    VITRINE_ATTENTION_EVALUATIONS,
    VITRINE_ATTENTION_NOTICE_CODES,
    VitrineAttentionNotice,
    VitrineAttentionQuery,
    VitrineAttentionReport,
    VitrineAttentionSummary,
    VitrineNextActionRef,
    evaluate_vitrine_attention,
)
from vitrine.released_producer_contracts import (
    CONCORD_0_3_0_AUDIT,
    CORE_0_6_3_AUDIT,
    QUILLAN_0_10_0_AUDIT,
    SCOREFORM_0_11_0_AUDIT,
)

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS = (
    "tests/test_attention.py",
    "tests/test_attention_snapshot.py",
    "tests/test_attention_cli.py",
    "tests/test_attention_menu.py",
    "tests/test_attention_acceptance_matrix.py",
    "tests/test_validate_attention_next_actions.py",
    "tests/test_candidate_inbox.py",
    "tests/test_working_composition.py",
    "tests/test_snapshot_services.py",
)

REQUIRED_DOCS = (
    "docs/contracts/attention-next-actions-v1.md",
    "docs/development/attention-next-actions.md",
    "docs/validation/issue-69-attention-next-actions-validation.md",
)

EXPECTED_DEFINITIONS = {
    "vitrine_candidate_review_pending": (
        "Candidate review pending",
        "candidates",
        "workflow",
        "open_candidate_inbox",
    ),
    "vitrine_candidate_evaluation_stale": (
        "Candidate evaluation stale",
        "candidate_entries",
        "workflow",
        "open_candidate_inbox",
    ),
    "vitrine_candidate_evaluation_unresolved": (
        "Candidate evaluation unresolved",
        "candidate_entries",
        "workflow",
        "open_candidate_inbox",
    ),
    "vitrine_selection_decision_pending": (
        "Selection decision pending",
        "selection_proposals",
        "workflow",
        "open_candidate_review",
    ),
    "vitrine_selection_follow_up_required": (
        "Selection follow-up required",
        "selection_proposals",
        "workflow",
        "open_candidate_review",
    ),
    "vitrine_selection_condition_unresolved": (
        "Selection condition unresolved",
        "selections",
        "workflow",
        "open_candidate_review",
    ),
    "vitrine_selection_unplaced": (
        "Selection needs placement",
        "selections",
        "workflow",
        "open_candidate_review",
    ),
    "vitrine_curation_review_required": (
        "Curation review required",
        "profile_requirements",
        "workflow",
        "open_candidate_review",
    ),
    "vitrine_curation_review_follow_up": (
        "Curation review follow-up",
        "curation_reviews",
        "workflow",
        "open_candidate_review",
    ),
    "vitrine_working_composition_refresh_needed": (
        "Working Composition refresh needed",
        "portfolios",
        "workflow",
        "open_working_composition",
    ),
    "vitrine_composition_requirement_unresolved": (
        "Composition requirement unresolved",
        "profile_requirements",
        "workflow",
        "open_working_composition",
    ),
    "vitrine_composition_requirement_human_review": (
        "Composition requirement needs human review",
        "profile_requirements",
        "workflow",
        "open_working_composition",
    ),
    "vitrine_composition_obligation_unresolved": (
        "Composition obligation unresolved",
        "obligation_codes",
        "workflow",
        "open_working_composition",
    ),
    "vitrine_snapshot_recovery_required": (
        "Snapshot recovery required",
        "snapshot_builds",
        "recovery",
        "inspect_snapshot_recovery",
    ),
    "vitrine_snapshot_build_failed": (
        "Snapshot build failed",
        "snapshot_builds",
        "recovery",
        "inspect_snapshot_recovery",
    ),
    "vitrine_snapshot_durability_uncertain": (
        "Snapshot durability is uncertain",
        "snapshot_builds",
        "integrity",
        "inspect_snapshot_recovery",
    ),
    "vitrine_snapshot_integrity_problem": (
        "Snapshot integrity problem",
        "snapshot_findings",
        "integrity",
        "inspect_snapshot_custody",
    ),
    "vitrine_omission_audience_prohibited": (
        "Snapshot content omitted for this audience",
        "snapshot_omissions",
        "notice",
        "inspect_snapshot_edition",
    ),
    "vitrine_omission_rights_review_unresolved": (
        "Snapshot omission needs rights review",
        "snapshot_omissions",
        "workflow",
        "open_candidate_review",
    ),
    "vitrine_omission_privacy_review_unresolved": (
        "Snapshot omission needs privacy review",
        "snapshot_omissions",
        "workflow",
        "open_candidate_review",
    ),
    "vitrine_omission_source_unavailable": (
        "Snapshot source was unavailable",
        "snapshot_omissions",
        "workflow",
        "open_build_export_current_portfolio",
    ),
    "vitrine_omission_representation_unavailable": (
        "Snapshot representation was unavailable",
        "snapshot_omissions",
        "workflow",
        "open_build_export_current_portfolio",
    ),
    "vitrine_omission_profile_excluded": (
        "Snapshot content excluded by Profile",
        "snapshot_omissions",
        "notice",
        "inspect_snapshot_edition",
    ),
    "vitrine_omission_explicitly_not_included": (
        "Snapshot content explicitly not included",
        "snapshot_omissions",
        "notice",
        "inspect_snapshot_edition",
    ),
    "vitrine_export_pending_after_seal": (
        "Snapshot Export pending after seal",
        "snapshot_exports",
        "recovery",
        "open_build_export_current_portfolio",
    ),
    "vitrine_export_verification_problem": (
        "Snapshot Export verification problem",
        "snapshot_exports",
        "integrity",
        "verify_snapshot_export",
    ),
}

EXPECTED_ACTION_IDS = frozenset(
    {
        "open_candidate_inbox",
        "open_candidate_review",
        "open_working_composition",
        "open_build_export_current_portfolio",
        "inspect_snapshot_recovery",
        "inspect_snapshot_custody",
        "inspect_snapshot_edition",
        "verify_snapshot_export",
    }
)

FORBIDDEN_SIBLING_IMPORT_ROOTS = frozenset(
    {"scoreform", "quillan", "concord", "portia", "meridian", "paper_data_suite"}
)

FORBIDDEN_ATTENTION_IMPORTS = (
    "vitrine.producer_reader_services",
    "vitrine.scoreform_adapter",
    "vitrine.quillan_adapter",
    "vitrine.concord_adapter",
    "vitrine.quillan_artifact_source",
    "vitrine.concord_artifact_source",
    "vitrine.snapshot_materialization",
    "vitrine.current_portfolio_execution",
)

FORBIDDEN_MUTATION_CALLS = frozenset(
    {
        "commit_record_batch",
        "create_audience_context",
        "create_snapshot_directory_export",
        "create_snapshot_series",
        "create_working_composition",
        "decide_selection_proposal",
        "discover_and_evaluate_candidates",
        "execute_snapshot_build_attempt",
        "freeze_prepared_working_composition",
        "invalidate_selection",
        "place_selection",
        "plan_snapshot_build",
        "propose_candidate_selection",
        "reject_candidate_directly",
        "replace_selection",
        "request_snapshot_build",
        "review_curation_target",
        "seal_snapshot_build_attempt",
        "select_candidate_directly",
        "start_snapshot_build_attempt",
        "withdraw_selection",
        "write_bytes",
        "write_text",
        "mkdir",
        "unlink",
    }
)

FORBIDDEN_DURABLE_ATTENTION_MARKERS = (
    "class AttentionRecord",
    "class NotificationRecord",
    "class CandidateSeenRecord",
    "class NextActionRecord",
    "class AttentionAcknowledgement",
    "ATTENTION_RECORD_TYPE",
    "CANDIDATE_SEEN_RECORD_TYPE",
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
                f"{_relative(path)} is missing required #69 marker: {marker}"
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
    return {value.split(".", 1)[0] for value in _imported_modules(tree)}


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


def _validate_attention_source(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    sibling_imports = _imported_roots(tree) & FORBIDDEN_SIBLING_IMPORT_ROOTS
    if sibling_imports:
        raise RuntimeError(
            f"{_relative(path)} imports sibling package(s): {sorted(sibling_imports)}"
        )
    imported = _imported_modules(tree)
    protected = sorted(
        prefix
        for prefix in FORBIDDEN_ATTENTION_IMPORTS
        if any(
            value == prefix or value.startswith(prefix + ".") for value in imported
        )
    )
    if protected:
        raise RuntimeError(
            f"{_relative(path)} imports producer/build authority path(s): {protected}"
        )
    mutation_calls = sorted(_called_names(tree) & FORBIDDEN_MUTATION_CALLS)
    if mutation_calls:
        raise RuntimeError(
            f"{_relative(path)} invokes mutation/write call(s): {mutation_calls}"
        )
    for forbidden in (".evaluated_at", ".started_at", ".completed_at"):
        if forbidden in source:
            raise RuntimeError(
                "attention currentness must not use event timestamps: " + forbidden
            )


def _validate_project_contract() -> None:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("pyproject project table is missing")
    dependencies = tuple(project.get("dependencies", ()))
    if dependencies != ("pds-core>=0.6.3,<0.7",):
        raise RuntimeError(
            "Issue #69 requires the current released Core floor pds-core>=0.6.3,<0.7"
        )
    dependency_text = "\n".join(str(item) for item in dependencies).casefold()
    for sibling in ("scoreform", "quillan", "concord", "portia", "meridian"):
        if sibling in dependency_text:
            raise RuntimeError(f"attention added sibling runtime dependency: {sibling}")
    entry_points = project.get("entry-points", {})
    expected_operations = {
        "vitrine": "vitrine.pds_operations:get_module_operations_profile"
    }
    if not isinstance(entry_points, dict) or entry_points.get(
        "paper_data_suite.module_operations"
    ) != expected_operations:
        raise RuntimeError("Issue #70 Vitrine module-operations registration drifted")
    mypy_files = tuple(payload.get("tool", {}).get("mypy", {}).get("files", ()))
    for required in (
        "scripts/validate_attention_next_actions.py",
        "scripts/smoke_test_attention_next_actions_wheel.py",
    ):
        if required not in mypy_files:
            raise RuntimeError(f"Issue #69 MyPy scope is missing {required}")


def _validate_no_durable_attention_records() -> None:
    for path in sorted((ROOT / "vitrine" / "models").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_DURABLE_ATTENTION_MARKERS:
            if marker in source:
                raise RuntimeError(
                    "attention must remain a projection, not durable state: "
                    f"{marker} in {_relative(path)}"
                )


def _definition_contract() -> dict[str, tuple[str, str, str, str]]:
    definitions = getattr(attention_module, "_ATTENTION_DEFINITIONS", ())
    return {
        item.code: (
            item.label,
            item.count_unit,
            item.attention_class,
            item.action_id,
        )
        for item in definitions
    }


def validate(*, run_focused_tests: bool = True) -> None:
    if VITRINE_ATTENTION_CONTRACT_VERSION != "vitrine_attention_next_actions_v1":
        raise RuntimeError("Vitrine attention contract identity changed")
    if VITRINE_ATTENTION_EVALUATIONS != frozenset({"evaluated", "unavailable"}):
        raise RuntimeError("Vitrine attention evaluation vocabulary changed")
    if VITRINE_ATTENTION_CLASSES != frozenset(
        {"workflow", "recovery", "integrity", "notice"}
    ):
        raise RuntimeError("Vitrine attention class vocabulary changed")
    if VITRINE_ATTENTION_NOTICE_CODES != frozenset(
        {"vitrine_attention_partial", "vitrine_attention_unavailable"}
    ):
        raise RuntimeError("Vitrine attention notice vocabulary changed")
    if VITRINE_ATTENTION_CODES != frozenset(EXPECTED_DEFINITIONS):
        raise RuntimeError("Vitrine attention code vocabulary changed")
    if VITRINE_ATTENTION_ACTION_IDS != EXPECTED_ACTION_IDS:
        raise RuntimeError("Vitrine next-action vocabulary changed")
    if _definition_contract() != EXPECTED_DEFINITIONS:
        raise RuntimeError("Vitrine attention label/count/class/action mapping changed")

    if {field.name for field in fields(VitrineAttentionQuery)} != {"portfolio_id"}:
        raise RuntimeError("Vitrine attention query shape changed")
    if {field.name for field in fields(VitrineNextActionRef)} != {
        "action_id",
        "portfolio_id",
    }:
        raise RuntimeError("Vitrine next-action shape changed")
    if {field.name for field in fields(VitrineAttentionNotice)} != {
        "code",
        "summary",
    }:
        raise RuntimeError("Vitrine attention notice shape changed")
    if {field.name for field in fields(VitrineAttentionSummary)} != {
        "code",
        "label",
        "count",
        "count_unit",
        "attention_class",
        "portfolio_id",
        "reason_codes",
        "next_action",
    }:
        raise RuntimeError("Vitrine attention summary shape changed")
    report_fields = {field.name for field in fields(VitrineAttentionReport)}
    if report_fields != {
        "contract_version",
        "evaluation",
        "observed_state_revision",
        "summaries",
        "notices",
    }:
        raise RuntimeError("Vitrine attention report shape changed")
    if "ready" in report_fields:
        raise RuntimeError("attention must remain distinct from readiness")

    for action_id in VITRINE_ATTENTION_ACTION_IDS:
        action = ModuleOwnerActionRef(module_id="vitrine", action_id=action_id)
        if action.action_id != action_id:
            raise RuntimeError("Core 0.6.3 rejected a Vitrine owner-action identifier")

    released = {
        "core": CORE_0_6_3_AUDIT.release_version,
        "scoreform": SCOREFORM_0_11_0_AUDIT.release_version,
        "quillan": QUILLAN_0_10_0_AUDIT.release_version,
        "concord": CONCORD_0_3_0_AUDIT.release_version,
    }
    if released != {
        "core": "0.6.3",
        "scoreform": "0.11.0",
        "quillan": "0.10.0",
        "concord": "0.3.0",
    }:
        raise RuntimeError(f"released PDS compatibility anchors changed: {released}")

    if not callable(evaluate_vitrine_attention):
        raise RuntimeError("Vitrine attention evaluator is missing")

    attention_path = ROOT / "vitrine/attention.py"
    cli_path = ROOT / "vitrine/attention_cli.py"
    menu_path = ROOT / "vitrine/attention_menu.py"
    for path in (attention_path, cli_path, menu_path):
        if not path.is_file():
            raise RuntimeError(f"missing #69 runtime surface: {_relative(path)}")
    _validate_attention_source(attention_path)
    _require_text(
        attention_path,
        "list_candidate_inbox(",
        "prepare_working_composition(",
        "project_snapshot_state(records)",
        "inspect_snapshot_custody(workspace_root)",
        "verify_snapshot_export(",
        'if finding.code == "snapshot.custody.failed_attempt":',
        "return by_number[max(by_number)]",
        "include_unscoped=request.portfolio_id is None",
        "load_current_state(root).state_revision != current.state_revision",
    )
    source = attention_path.read_text(encoding="utf-8")
    for forbidden in (
        "seen_at",
        "last_seen",
        "CandidateSeen",
        "urgent_score",
        "risk_score",
        "priority_score",
    ):
        if forbidden in source:
            raise RuntimeError(f"attention introduced forbidden derived state: {forbidden}")

    _require_text(
        cli_path,
        '"attention"',
        '"list"',
        'listing.add_argument("--portfolio-id")',
        "evaluate_vitrine_attention(root, query)",
        "return 0 if report.evaluation == \"evaluated\" else 1",
    )
    _require_text(
        menu_path,
        "evaluate_vitrine_attention(",
        "Action ID:",
        "open_candidate_inbox",
        "verify_snapshot_export",
    )
    for path in (cli_path, menu_path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        mutation_calls = sorted(_called_names(tree) & FORBIDDEN_MUTATION_CALLS)
        if mutation_calls:
            raise RuntimeError(
                f"{_relative(path)} executes mutating owner actions: {mutation_calls}"
            )

    _require_text(
        ROOT / "vitrine/cli.py",
        "configure_attention_parser(subparsers)",
        'if args.command == "attention":',
        "run_attention_command(args, output=stdout)",
    )
    _require_text(
        ROOT / "vitrine/menu.py",
        '"6. Attention / Next Actions"',
        "run_attention_menu(",
    )
    _require_text(
        ROOT / "vitrine/portfolio_menu.py",
        '"7. Attention / Next Actions"',
        "portfolio_id=portfolio_id",
    )

    _validate_no_durable_attention_records()
    _validate_project_contract()

    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"missing #69 documentation: {relative}")

    _require_text(
        ROOT / "scripts/check_package.py",
        '"vitrine/attention.py"',
        '"vitrine/attention_cli.py"',
        '"vitrine/attention_menu.py"',
        '"docs/contracts/attention-next-actions-v1.md"',
        '"scripts/validate_attention_next_actions.py"',
        '"scripts/smoke_test_attention_next_actions_wheel.py"',
        '"tests/test_attention_acceptance_matrix.py"',
    )
    _require_text(
        ROOT / "scripts/validate_repository.py",
        "scripts/validate_attention_next_actions.py",
        "scripts/smoke_test_attention_next_actions_wheel.py",
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
            raise RuntimeError(f"Vitrine attention focused validation failed: {detail}")


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
        print("PASS Vitrine attention and next-action validation")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Vitrine attention validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
