"""Validate Issue #103 completion-aware attention and stable reader compatibility."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from vitrine.attention import VITRINE_ATTENTION_V2_CONTRACT_VERSION
from vitrine.portfolio_completion import PORTFOLIO_COMPLETION_CONTRACT_VERSION
from vitrine.producer_reader_compatibility import (
    VITRINE_LEGACY_EXACT_PRODUCER_RELEASES,
    VITRINE_SUPPORTED_PRODUCER_READER_CONTRACTS,
)
from vitrine.released_producer_contracts import (
    CORE_0_6_5_AUDIT,
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
)

ROOT = Path(__file__).resolve().parents[1]

FOCUSED_TESTS: tuple[str, ...] = (
    "tests/test_portfolio_completion_issue103.py",
    "tests/test_attention_completion_issue103.py",
    "tests/test_attention_menu.py",
    "tests/test_issue103_reader_contract_compatibility.py",
    "tests/test_issue103_release_baseline.py",
    "tests/test_released_producer_contracts.py",
    "tests/test_producer_reader_services.py",
    "tests/test_scoreform_adapter.py",
)

EXPECTED_CURRENT_RELEASES = {
    "scoreform": "0.13.0",
    "quillan": "0.10.6",
    "concord": "0.3.2",
}

EXPECTED_READER_CONTRACTS = {
    "scoreform": frozenset({"scoreform_academic_result_reader_v1"}),
    "quillan": frozenset({"quillan_academic_result_reader_v1"}),
    "concord": frozenset({"concord_academic_result_reader_v1"}),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _require_text(path: Path, *markers: str) -> None:
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        _require(marker in text, f"{path.relative_to(ROOT)} is missing {marker!r}")


def _validate_contracts() -> None:
    _require(
        PORTFOLIO_COMPLETION_CONTRACT_VERSION == "vitrine_portfolio_completion_v1",
        "Issue #103 Portfolio completion contract changed",
    )
    _require(
        VITRINE_ATTENTION_V2_CONTRACT_VERSION == "vitrine_attention_next_actions_v2",
        "Issue #103 Attention v2 contract changed",
    )
    _require(
        CORE_0_6_5_AUDIT.release_version == "0.6.5",
        "Issue #103 Core qualification anchor changed",
    )
    _require(
        VITRINE_SUPPORTED_PRODUCER_READER_CONTRACTS
        == EXPECTED_READER_CONTRACTS,
        "Issue #103 accepted reader-contract vocabulary changed",
    )
    current = {
        module_id: audit.release_version
        for module_id, audit in RELEASED_PRODUCER_CONTRACT_BY_MODULE.items()
    }
    _require(
        current == EXPECTED_CURRENT_RELEASES,
        "Issue #103 current producer release anchors changed",
    )
    for module_id, version in current.items():
        _require(
            version not in VITRINE_LEGACY_EXACT_PRODUCER_RELEASES[module_id],
            f"{module_id} current metadata-bearing release entered legacy fallback",
        )


def _validate_completion_and_attention_sources() -> None:
    _require_text(
        ROOT / "vitrine" / "portfolio_completion.py",
        "prepare_working_composition",
        "project_completed_portfolio_history",
        "project_portfolio_completion_operational_status",
        "student_presentation_missing",
        "recovery_or_integrity_blocked",
        "update_ready",
    )
    _require_text(
        ROOT / "vitrine" / "attention.py",
        "vitrine_attention_next_actions_v2",
        "vitrine_candidate_optional_evidence",
        "vitrine_student_presentation_missing",
        'code=f"vitrine_portfolio_{completion.state}"',
        '"complete": (',
        '"update_ready": (',
        '"recovery_or_integrity_blocked": (',
    )
    _require_text(
        ROOT / "vitrine" / "attention_menu.py",
        "Portfolio status",
        "Needs attention",
        "Optional opportunities",
        "_select_workspace_portfolio_for_action",
        "_run_owner_action",
        "evaluate_vitrine_attention_v2",
    )


def _validate_reader_sources() -> None:
    _require_text(
        ROOT / "vitrine" / "producer_reader_compatibility.py",
        "lookup_publication_reader_support",
        "legacy_exact_release",
        "declared_reader_contract",
        "normalize_persisted_reader_contract_version",
    )
    _require_text(
        ROOT / "vitrine" / "candidate_services.py",
        "normalize_persisted_reader_contract_version",
        "_producer_source_semantic_key",
    )
    _require_text(
        ROOT / "scripts" / "qualify_installed_producer_readers.py",
        "CORE_0_6_5_AUDIT",
        "PublicationReaderSupport",
        "lookup_publication_reader_support",
        "scoreform_academic_result_reader_v1",
        "quillan_academic_result_reader_v1",
        "concord_academic_result_reader_v1",
        "PASS exact-wheel Issue #103 reader-contract metadata qualification",
    )
    _require_text(
        ROOT / "scripts" / "qualify_concord_artifact_source.py",
        "CORE_0_6_5_AUDIT",
        "metadata.version(concord_audit.distribution_name)",
        "== concord_audit.release_version",
    )
    _require_text(
        ROOT / "scripts" / "qualify_quillan_artifact_source.py",
        "CORE_0_6_5_AUDIT",
        "metadata.version(quillan_audit.distribution_name)",
        "== quillan_audit.release_version",
    )
    concord_artifact_text = (
        ROOT / "scripts" / "qualify_concord_artifact_source.py"
    ).read_text(encoding="utf-8")
    quillan_artifact_text = (
        ROOT / "scripts" / "qualify_quillan_artifact_source.py"
    ).read_text(encoding="utf-8")
    _require(
        "CORE_0_6_3_AUDIT" not in concord_artifact_text,
        "Concord artifact qualifier retained historical Core 0.6.3 binding",
    )
    _require(
        "CORE_0_6_3_AUDIT" not in quillan_artifact_text
        and '== "0.10.0"' not in quillan_artifact_text,
        "Quillan artifact qualifier retained historical exact-wheel bindings",
    )


def _validate_installed_wheel_smoke() -> None:
    path = ROOT / "scripts" / "smoke_test_attention_next_actions_wheel.py"
    _require_text(
        path,
        'importlib.metadata.version("pds-core") == "0.6.6"',
        "Next step: Snapshot Export verification",
        "Action ID: verify_snapshot_export",
        "vitrine_attention_next_actions_v1",
    )
    text = path.read_text(encoding="utf-8")
    _require(
        'importlib.metadata.version("pds-core") == "0.6.4"' not in text,
        "Attention wheel smoke retained old Core 0.6.4 assertion",
    )


def _validate_repository_and_package_wiring() -> None:
    _require_text(
        ROOT / "scripts" / "validate_repository.py",
        "issue #103 completion / reader compatibility",
        "scripts/validate_issue103_acceptance.py",
        "--skip-focused-tests",
    )
    _require_text(
        ROOT / "scripts" / "check_package.py",
        '"vitrine/portfolio_completion.py"',
        '"vitrine/producer_reader_compatibility.py"',
        '"scripts/validate_issue103_acceptance.py"',
        '"tests/test_validate_issue103_acceptance.py"',
    )
    _require_text(
        ROOT / "pyproject.toml",
        '"scripts/validate_issue103_acceptance.py"',
        '"pds-core>=0.6.6,<0.7"',
    )
    _require_text(
        ROOT / "scripts" / "validate_release_contract.py",
        'CURRENT_DEVELOPMENT_CORE_REQUIREMENT = "pds-core>=0.6.6,<0.7"',
    )
    _require_text(
        ROOT / "scripts" / "verify_core_wheel.py",
        'EXPECTED_CORE_VERSION = "0.6.6"',
        'EXPECTED_CORE_WHEEL_FILENAME = "pds_core-0.6.6-py3-none-any.whl"',
        "d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301",
        "PASS Core v0.6.6 verification",
    )
    for relative in (
        "scripts/smoke_test_completed_portfolio_navigation_wheel.py",
        "scripts/smoke_test_operations_wheel.py",
        "scripts/smoke_test_path_output_naming_wheel.py",
        "scripts/smoke_test_portfolio_presentation_wheel.py",
        "scripts/verify_installed_end_to_end.py",
    ):
        current_text = (ROOT / relative).read_text(encoding="utf-8")
        _require(
            "0.6.6" in current_text,
            f"{relative} is missing the current Core 0.6.6 qualification marker",
        )
    _require_text(
        ROOT / "scripts" / "validate_scoreform_adapter.py",
        "scoreform_academic_result_reader_v1",
    )
    _require_text(
        ROOT / "scripts" / "validate_quillan_adapter.py",
        "quillan_academic_result_reader_v1",
    )
    _require_text(
        ROOT / "scripts" / "validate_concord_adapter.py",
        "concord_academic_result_reader_v1",
    )
    _require_text(
        ROOT / "scripts" / "validate_v030_release_audit.py",
        'project.get("dependencies") != ["pds-core>=0.6.6,<0.7"]',
    )


def _validate_focused_inventory() -> None:
    for relative in FOCUSED_TESTS:
        _require((ROOT / relative).is_file(), f"missing #103 focused test: {relative}")

    _require_text(
        ROOT / "tests" / "test_portfolio_completion_issue103.py",
        "test_ready_to_build_without_completed_history",
        "test_exact_completed_edition_does_not_require_current_pointer",
        "test_historical_completion_with_newer_frozen_composition_is_update_ready",
        "test_operational_blocker_precedes_otherwise_complete_state",
        "test_missing_student_presentation_is_separate_from_technical_completion",
    )
    _require_text(
        ROOT / "tests" / "test_attention_completion_issue103.py",
        "test_unused_eligible_candidate_is_optional_when_requirements_are_satisfied",
        "test_candidate_is_required_when_it_can_fill_missing_section",
        "test_selected_stale_candidate_remains_required",
        "test_v2_evaluator_reports_complete_and_optional_extra_evidence",
    )
    _require_text(
        ROOT / "tests" / "test_attention_menu.py",
        "test_attention_action_routes_to_owner_workflow_and_recomputes",
        "test_workspace_action_chooses_only_matching_human_readable_portfolio",
    )
    _require_text(
        ROOT / "tests" / "test_issue103_reader_contract_compatibility.py",
        "test_future_package_same_reader_contract_is_accepted",
        "test_same_manifest_unsupported_reader_contract_is_rejected",
        "test_old_exact_historical_scoreform_release_remains_supported",
        "test_current_metadata_bearing_releases_are_not_legacy_fallbacks",
    )
    _require_text(
        ROOT / "tests" / "test_scoreform_adapter.py",
        "test_assignment_question_and_standard_alignment_metadata_is_preserved_without_ratings",
    )


def validate(*, run_focused_tests: bool) -> None:
    _validate_contracts()
    _validate_completion_and_attention_sources()
    _validate_reader_sources()
    _validate_installed_wheel_smoke()
    _validate_repository_and_package_wiring()
    _validate_focused_inventory()
    if run_focused_tests:
        subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *FOCUSED_TESTS],
            cwd=ROOT,
            check=True,
        )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-focused-tests", action="store_true")
    args = parser.parse_args(argv)
    try:
        validate(run_focused_tests=not args.skip_focused_tests)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Issue #103 validation failed: {error}", file=sys.stderr)
        return 1
    print("PASS Issue #103 completion-aware reader compatibility validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
