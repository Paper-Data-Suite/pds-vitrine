from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import vitrine.attention as attention_module
from vitrine.attention import (
    VitrineAttentionNotice,
    VitrineAttentionReport,
    VitrineAttentionSummary,
    VitrineNextActionRef,
)

ROOT = Path(__file__).resolve().parents[1]

ACCEPTANCE_MATRIX: dict[str, dict[str, tuple[str, ...]]] = {
    "availability_and_read_only": {
        "tests/test_attention.py": (
            "test_missing_vitrine_store_is_unavailable_without_creation",
            "test_curation_fixture_projects_candidate_and_composition_attention_read_only",
            "test_isolatable_working_composition_failure_returns_partial_report",
        ),
    },
    "candidate_currentness_and_disposition": {
        "tests/test_attention.py": (
            "test_current_core_action_ids_accept_core_063_owner_action_contract",
            "test_candidate_staleness_is_reused_from_candidate_inbox",
            "test_evaluation_only_unresolved_is_attention_without_fake_candidate",
            "test_viewing_candidate_inbox_does_not_clear_review_pending_attention",
            "test_explicit_reject_resolves_one_candidate_review_pending_fact",
        ),
    },
    "selection_review_and_composition": {
        "tests/test_attention.py": (
            "test_proposal_head_moves_from_pending_decision_to_follow_up",
            "test_active_unplaced_selection_routes_to_existing_review_workflow",
            "test_review_follow_up_reuses_working_composition_review_projection",
            "test_required_review_and_human_requirement_stay_structured",
            "test_exact_current_composition_removes_refresh_but_not_obligations",
        ),
    },
    "snapshot_recovery_omission_and_export": {
        "tests/test_attention_snapshot.py": (
            "test_incomplete_attempt_is_one_recovery_build_despite_build_lock",
            "test_historical_failed_attempt_drops_after_later_attempt_seals",
            "test_current_sealed_omission_persists_but_export_pending_resolves",
            "test_corrupt_current_export_is_reported_once_not_double_counted",
            "test_unscoped_orphan_staging_is_workspace_only_integrity_attention",
        ),
    },
    "teacher_surface_and_direct_cli": {
        "tests/test_attention_cli.py": (
            "test_direct_attention_cli_is_noninteractive_and_emits_stable_codes",
            "test_unavailable_attention_cli_returns_nonzero_but_reports_contract",
        ),
        "tests/test_attention_menu.py": (
            "test_attention_menu_renders_bounded_next_action_without_mutation",
            "test_main_menu_option_six_routes_workspace_attention",
            "test_portfolio_option_seven_routes_exact_portfolio_attention",
        ),
    },
}


def _test_functions(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return frozenset(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


def test_issue69_acceptance_matrix_points_to_real_behavior_tests() -> None:
    referenced: set[tuple[str, str]] = set()
    for group, files in ACCEPTANCE_MATRIX.items():
        assert files, f"acceptance group {group} has no focused tests"
        for relative, expected_tests in files.items():
            path = ROOT / relative
            assert path.is_file(), f"missing acceptance test file: {relative}"
            available = _test_functions(path)
            for test_name in expected_tests:
                assert test_name in available, (
                    f"acceptance group {group} lost behavior test "
                    f"{relative}::{test_name}"
                )
                referenced.add((relative, test_name))

    assert len(referenced) >= 20


def test_workspace_aggregation_drops_exact_portfolio_for_shared_code() -> None:
    fact = attention_module._AttentionFact
    summaries = attention_module._aggregate_facts(
        (
            fact(
                code="vitrine_candidate_review_pending",
                portfolio_id="portfolio_a",
            ),
            fact(
                code="vitrine_candidate_review_pending",
                portfolio_id="portfolio_b",
            ),
        )
    )

    assert len(summaries) == 1
    assert summaries[0].count == 2
    assert summaries[0].portfolio_id is None
    assert summaries[0].next_action is not None
    assert summaries[0].next_action.portfolio_id is None


def test_definition_order_not_input_order_controls_summary_order() -> None:
    fact = attention_module._AttentionFact
    summaries = attention_module._aggregate_facts(
        (
            fact(
                code="vitrine_export_verification_problem",
                portfolio_id="portfolio_a",
            ),
            fact(
                code="vitrine_candidate_review_pending",
                portfolio_id="portfolio_a",
            ),
        )
    )

    assert tuple(item.code for item in summaries) == (
        "vitrine_candidate_review_pending",
        "vitrine_export_verification_problem",
    )


def test_attention_low_density_schema_excludes_private_payload_fields() -> None:
    field_names = {
        field.name
        for value in (
            VitrineNextActionRef,
            VitrineAttentionNotice,
            VitrineAttentionSummary,
            VitrineAttentionReport,
        )
        for field in fields(value)
    }
    prohibited = {
        "student_name",
        "student_id",
        "score",
        "percentage",
        "feedback",
        "rationale",
        "artifact_bytes",
        "source_path",
        "absolute_path",
        "traceback",
        "credential",
        "token",
        "recipient",
        "ready",
    }

    assert field_names.isdisjoint(prohibited)
