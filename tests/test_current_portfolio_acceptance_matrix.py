from __future__ import annotations

import ast
from pathlib import Path

import pytest

import vitrine.current_portfolio_build as build_module
from vitrine.current_portfolio_build import prepare_current_portfolio_build
from vitrine.working_composition import (
    WorkingCompositionAudienceSummary,
    WorkingCompositionPayloadPreview,
    WorkingCompositionPreparation,
)

ROOT = Path(__file__).resolve().parents[1]

ACCEPTANCE_MATRIX: dict[str, dict[str, tuple[str, ...]]] = {
    "current_composition_handoff": {
        "tests/test_current_portfolio_build.py": (
            "test_stale_working_composition_and_unplaced_selection_block",
            "test_state_change_after_working_composition_preparation_fails_closed",
        ),
        "tests/test_current_portfolio_execution.py": (
            "test_blocked_preparation_stops_before_any_canonical_write",
            "test_state_change_after_preview_fails_before_first_task_write",
        ),
    },
    "audience_reviews_and_obligations": {
        "tests/test_current_portfolio_build.py": (
            "test_exact_current_context_and_series_are_reused_without_writes",
            "test_duplicate_exact_audience_contexts_require_explicit_choice",
            "test_explicit_context_and_series_choices_resolve_ambiguity",
            "test_duplicate_exact_series_require_explicit_choice",
            "test_missing_exact_required_review_class_blocks",
            "test_unresolved_obligations_require_exact_separate_acknowledgement",
            "test_acknowledgement_cannot_claim_noncurrent_obligation",
        ),
    },
    "deterministic_materialization": {
        "tests/test_current_portfolio_build_planning.py": (
            "test_first_party_plan_uses_profile_then_frozen_arrangement_order",
            "test_exact_provider_plans_copied_source_without_source_byte_resolution",
            "test_missing_exact_provider_is_reference_only_with_no_export_file",
            "test_live_scoreform_assessment_policy_is_reference_only_without_import",
            "test_deferred_media_path_is_suffix_neutral",
            "test_audience_prohibited_content_is_explicit_planned_omission",
            "test_conflicting_exact_providers_block_instead_of_downgrading_silently",
            "test_display_text_does_not_enter_deterministic_ids_paths_or_fingerprint",
            "test_provider_identity_is_bound_into_plan_identity_and_fingerprint",
        ),
    },
    "reflection_generation_boundary": {
        "tests/test_current_portfolio_reflection.py": (
            "test_renderer_preserves_exact_frozen_content_bytes",
            "test_renderer_follows_exact_revision_not_later_successor",
            "test_external_reference_reflection_is_not_dereferenced",
            "test_preparation_adds_exact_generated_reflection_and_export_file",
            "test_unsupported_reflection_blocks_without_reinterpretation",
            (
                "test_audience_prohibited_reflection_blocks_instead_of_"
                "fabricating_omission"
            ),
            "test_frozen_reflection_change_changes_plan_and_preparation_fingerprints",
            "test_non_section_scoped_reflection_requirement_fails_closed",
            "test_annotation_inventory_reference_does_not_become_generated_document",
        ),
    },
    "canonical_execution_and_recovery": {
        "tests/test_current_portfolio_execution.py": (
            "test_changed_rederived_fingerprint_is_not_silently_substituted",
            "test_curation_revalidation_failure_is_translated_before_first_write",
            "test_create_sequence_threads_exact_returned_state_revisions",
            "test_reuse_path_does_not_create_context_or_series",
            "test_request_and_plan_freeze_exact_reviewed_export_and_acknowledgement",
            "test_request_key_is_stable_across_create_to_reuse_preparation_transition",
            "test_mid_sequence_state_conflict_preserves_completed_stage_metadata",
            "test_old_preparation_is_not_silently_replayed_after_state_advances",
            "test_revalidation_uses_exact_prepared_choices_and_provider_registry",
            "test_full_prepared_executor_shares_one_provider_registry",
            "test_completion_threads_attempt_seal_verify_and_export_boundaries",
            "test_completion_context_uses_exact_frozen_reflection_revision",
            "test_attempt_start_failure_reports_exact_durable_attempt",
            "test_completion_authority_denial_preserves_attempt_identity",
            "test_producer_artifact_authorization_failure_is_distinguished",
            "test_export_failure_reports_sealed_edition_resume_path",
            "test_export_verification_failure_preserves_artifact_identity",
            "test_resume_export_reuses_exact_existing_artifact",
            "test_exact_committed_provider_passes_preflight",
            "test_provider_identity_change_fails_before_attempt_start",
            "test_completion_state_drift_stops_before_attempt_start",
            "test_post_seal_conflict_reports_only_exact_recoverable_edition",
        ),
    },
    "teacher_surface_and_direct_cli": {
        "tests/test_current_portfolio_surface.py": (
            "test_shared_preparation_view_exposes_exact_policy_and_distinctions",
        ),
        "tests/test_current_portfolio_cli.py": (
            "test_parser_exposes_prepare_and_execute_with_exact_disambiguation",
            "test_prepare_is_read_only_and_uses_exact_provider_registry",
            "test_execute_rejects_changed_fingerprint_before_shared_executor",
            "test_execute_uses_exact_reviewed_preparation_and_shared_dependencies",
        ),
        "tests/test_current_portfolio_menu.py": (
            "test_stale_working_composition_stops_before_build_preparation",
            "test_menu_requires_exact_context_series_and_obligation_acknowledgement",
            "test_menu_declined_final_confirmation_performs_no_write",
        ),
        "tests/test_current_portfolio_routing.py": (
            "test_workflow_cli_registers_portfolio_build_export_task",
            "test_workflow_cli_routes_build_export_to_shared_task_handler",
            "test_portfolio_option_six_routes_to_current_portfolio_task",
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


def test_issue68_acceptance_matrix_points_to_real_focused_behavior_tests() -> None:
    referenced: set[tuple[str, str]] = set()
    for group, files in ACCEPTANCE_MATRIX.items():
        assert files, f"acceptance group {group} has no focused tests"
        for relative, expected_tests in files.items():
            path = ROOT / relative
            assert path.is_file(), f"missing acceptance test file: {relative}"
            available = _test_functions(path)
            for test_name in expected_tests:
                assert test_name in available, (
                    f"acceptance group {group} lost focused behavior test "
                    f"{relative}::{test_name}"
                )
                referenced.add((relative, test_name))

    assert len(referenced) >= 55


def test_no_current_working_composition_blocks_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rule = WorkingCompositionAudienceSummary(
        audience_rule_id="student_review",
        audience_class="student",
        purpose="Synthetic current-portfolio acceptance",
        allowed_content_classes=("reflection",),
        prohibited_content_classes=("private_teacher_note",),
        required_review_classes=(),
        presentation_class="student_portfolio",
        retention_policy_reference=None,
    )
    payload = WorkingCompositionPayloadPreview(
        selection_ids=(),
        placement_ids=(),
        arrangement_ids=(),
        included_rationale_ids=(),
        included_curation_revisions=(),
        applicable_review_decision_ids=(),
        related_profile_requirement_ids=(),
        unresolved_obligation_codes=(),
        coherence_state="coherent",
    )
    working = WorkingCompositionPreparation(
        contract_version="vitrine_guided_working_composition_v1",
        observed_state_revision=7,
        portfolio_id="portfolio_acceptance",
        portfolio_subject_id="subject_acceptance",
        profile_binding_id="binding_acceptance",
        profile_revision_id="profile_acceptance",
        profile_revision_number=1,
        observed_composition_pointer_revision=None,
        current_composition_revision=None,
        predicted_composition_revision=1,
        predecessor_composition_revision=None,
        predicted_composition_pointer_revision=1,
        disposition="create_initial",
        payload=payload,
        sections=(),
        selections=(),
        unplaced_selection_ids=(),
        requirements=(),
        source_observations=(),
        reviews=(),
        audience_rules=(rule,),
        requested_composition_note=None,
        composition_note_will_persist=False,
        preparation_fingerprint="a" * 64,
    )
    current = type("Current", (), {"state_revision": 7})()
    monkeypatch.setattr(
        build_module,
        "prepare_working_composition",
        lambda *_args, **_kwargs: working,
    )
    monkeypatch.setattr(
        build_module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (current, ()),
    )

    prepared = prepare_current_portfolio_build(
        ".",
        working.portfolio_id,
        audience_rule_id=rule.audience_rule_id,
    )

    assert prepared.working_composition_disposition == "create_initial"
    assert prepared.current_composition_revision is None
    assert "working_composition_requires_freeze" in prepared.blocking_reasons
    assert prepared.ready_for_plan_execution is False


def test_advanced_snapshot_cli_surface_remains_available() -> None:
    source = (ROOT / "vitrine/workflow_cli.py").read_text(encoding="utf-8")
    for marker in (
        'request = snapshot.add_parser("request")',
        'plan = snapshot.add_parser("plan")',
        'build = snapshot.add_parser("build")',
        'verify = snapshot.add_parser("verify")',
        'export = snapshot.add_parser("export")',
        'custody = snapshot.add_parser("custody")',
    ):
        assert marker in source
