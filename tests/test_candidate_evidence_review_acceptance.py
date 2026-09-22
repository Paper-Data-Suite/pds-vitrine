from __future__ import annotations

import ast
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from pds_core.academic_catalog import PublicationCatalogQuery

from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_evidence_preview import (
    CandidateEvidencePreviewError,
    CandidateEvidencePreviewRequest,
    resolve_candidate_evidence_preview_authority,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import CandidateEvaluation
from vitrine.storage import (
    commit_record_batch,
    load_current_records,
    load_current_state,
)

ROOT = Path(__file__).resolve().parents[1]

ACCEPTANCE_MATRIX: dict[str, dict[str, tuple[str, ...]]] = {
    "A_candidate_names_instructional": {
        "tests/test_candidate_evidence_presentation.py": (
            "test_scoreform_presentation_uses_work_title_and_attempt_number",
            "test_quillan_presentation_uses_instructional_evidence_vocabulary",
            "test_concord_presentation_uses_collaborative_work_language",
        ),
    },
    "B_display_labels_not_authority": {
        "tests/test_candidate_discovery.py": (
            "test_label_only_rediscovery_reuses_existing_candidate_identity",
        ),
        "tests/test_candidate_evidence_preview.py": (
            "test_preview_request_has_no_display_label_authority",
        ),
    },
    "C_alternate_representations_distinguishable": {
        "tests/test_candidate_evidence_presentation.py": (
            "test_quillan_feedback_representations_share_family_without_merging_identity",
        ),
        "tests/test_candidate_evidence_artifact_preview.py": (
            "test_quillan_feedback_preview_preserves_exact_representation",
        ),
    },
    "D_discovery_explains_before_mutation": {
        "tests/test_candidate_discovery_menu.py": (
            "test_discovery_preflight_is_instructional_and_contextual",
            "test_guided_discovery_cancel_does_not_call_service",
        ),
    },
    "E_discovery_completion_summary": {
        "tests/test_candidate_discovery_menu.py": (
            "test_discovery_summary_uses_teacher_language_and_preserves_boundaries",
            "test_guided_discovery_runs_after_preflight_and_summarizes_result",
        ),
        "tests/test_candidate_discovery_presentation.py": (
            "test_scoreform_summary_counts_exact_discovery_result",
            "test_summary_counts_findings_as_discovery_problems_without_exposing_codes",
        ),
    },
    "F_ready_to_consider_is_undecided": {
        "tests/test_candidate_review_menu.py": (
            "test_ready_to_consider_category_requires_unselected_candidate",
            "test_selection_categories_remain_distinct",
        ),
        "tests/test_candidate_inbox.py": (
            "test_selection_status_is_observational_and_filterable",
        ),
    },
    "G_profile_fit_teacher_language": {
        "tests/test_candidate_evidence_presentation.py": (
            "test_scoreform_presentation_uses_work_title_and_attempt_number",
            "test_concord_presentation_uses_collaborative_work_language",
        ),
        "tests/test_candidate_inbox_menu.py": (
            "test_candidate_inbox_menu_lists_and_inspects_read_only",
        ),
    },
    "H_preview_before_selection_read_only": {
        "tests/test_candidate_evidence_preview_menu.py": (
            "test_structured_preview_is_explicit_read_only_and_teacher_facing",
            "test_guided_review_v_action_precedes_selection_decision",
        ),
        "tests/test_candidate_evidence_preview.py": (
            "test_preview_authority_resolves_exact_persisted_source_read_only",
        ),
    },
    "I_ordinary_rendering_has_no_artifact_io": {
        "tests/test_candidate_evidence_preview_menu.py": (
            "test_inbox_opening_detail_does_not_trigger_preview",
        ),
        "tests/test_candidate_inbox_menu.py": (
            "test_candidate_inbox_menu_technical_details_preserve_bounded_provenance",
        ),
    },
    "J_artifact_preview_exact_and_authorized": {
        "tests/test_candidate_evidence_artifact_preview.py": (
            "test_quillan_student_work_preview_bridges_exact_authorization_before_io",
            "test_preview_denial_happens_inside_producer_gate_before_native_io",
            "test_quillan_tampered_digest_fails_closed",
            "test_concord_preview_returns_exact_authorized_pdf",
            "test_concord_tampered_bytes_metadata_fails_closed",
        ),
        "tests/test_candidate_evidence_preview_revalidation.py": (
            "test_preview_rejects_manifest_integrity_drift_without_vitrine_mutation",
            "test_preview_fails_closed_when_reprojection_no_longer_matches_exact_source",
        ),
    },
    "K_metadata_only_preview_honest": {
        "tests/test_candidate_evidence_preview_structured.py": (
            "test_scoreform_structured_preview_uses_instructional_allowlist",
            "test_concord_structured_preview_omits_target_identity",
            "test_quillan_review_allowlist_excludes_private_and_raw_payload_fields",
        ),
        "tests/test_candidate_evidence_preview_revalidation.py": (
            "test_scoreform_exact_source_revalidates_as_structured_summary",
            "test_concord_score_summary_stays_structured_and_byte_free",
        ),
    },
    "L_preview_bytes_transient": {
        "tests/test_candidate_evidence_preview_menu.py": (
            "test_artifact_preview_file_exists_only_for_launch_lifetime",
        ),
    },
    "M_privacy_boundaries": {
        "tests/test_candidate_evidence_review_acceptance.py": (
            "test_suppressed_evaluation_cannot_be_resolved_for_preview",
        ),
        "tests/test_candidate_evidence_preview.py": (
            "test_preview_authorization_is_explicit_and_fail_closed",
            "test_default_workflow_preview_authorization_is_unresolved",
        ),
        "tests/test_candidate_evidence_preview_structured.py": (
            "test_quillan_review_allowlist_excludes_private_and_raw_payload_fields",
            "test_concord_structured_preview_omits_target_identity",
        ),
        "tests/test_candidate_inbox.py": (
            "test_suppressed_entry_cannot_be_retrieved_by_detail",
        ),
    },
    "N_exact_provenance_remains_inspectable": {
        "tests/test_candidate_inbox_menu.py": (
            "test_candidate_inbox_menu_technical_details_preserve_bounded_provenance",
        ),
        "tests/test_candidate_review_menu.py": (
            "test_guided_review_detail_is_teacher_first_with_explicit_technical_view",
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


def test_issue96_acceptance_matrix_points_to_real_behavior_tests() -> None:
    expected = {
        f"{letter}_{name}"
        for letter, name in (
            ("A", "candidate_names_instructional"),
            ("B", "display_labels_not_authority"),
            ("C", "alternate_representations_distinguishable"),
            ("D", "discovery_explains_before_mutation"),
            ("E", "discovery_completion_summary"),
            ("F", "ready_to_consider_is_undecided"),
            ("G", "profile_fit_teacher_language"),
            ("H", "preview_before_selection_read_only"),
            ("I", "ordinary_rendering_has_no_artifact_io"),
            ("J", "artifact_preview_exact_and_authorized"),
            ("K", "metadata_only_preview_honest"),
            ("L", "preview_bytes_transient"),
            ("M", "privacy_boundaries"),
            ("N", "exact_provenance_remains_inspectable"),
        )
    }
    assert set(ACCEPTANCE_MATRIX) == expected

    referenced: set[tuple[str, str]] = set()
    for group, files in ACCEPTANCE_MATRIX.items():
        assert files, f"acceptance group {group} has no behavior tests"
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
    assert len(referenced) >= 30


def _discover_scoreform(setup: object) -> None:
    result = discover_and_evaluate_candidates(
        getattr(setup, "workspace"),
        CandidateDiscoveryRequest(
            portfolio_id=getattr(setup, "portfolio_id"),
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id="vitrine_scoreform_fixture",
                state="current",
                limit=20,
            ),
            expected_state_revision=getattr(setup, "state_revision"),
        ),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert result.findings == ()


def test_suppressed_evaluation_cannot_be_resolved_for_preview(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(
        tmp_path,
        allow_assessment_summary=False,
    )
    _discover_scoreform(setup)
    first = next(
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, CandidateEvaluation)
    )
    suppressed = replace(
        first,
        candidate_evaluation_id="candidate_evaluation_suppressed_preview",
        predecessor_evaluation_id=first.candidate_evaluation_id,
        outcome="suppressed",
        reason_codes=("candidate:suppressed",),
        evaluated_at=first.evaluated_at + timedelta(seconds=1),
    )
    before = load_current_state(setup.workspace).state_revision
    committed = commit_record_batch(
        setup.workspace,
        (suppressed,),
        expected_state_revision=before,
    )
    assert committed.state_revision == before + 1

    request = CandidateEvidencePreviewRequest(
        portfolio_id=suppressed.portfolio_id,
        portfolio_subject_id=suppressed.portfolio_subject_id,
        entry_id=f"evaluation:{suppressed.candidate_evaluation_id}",
        candidate_id=None,
        candidate_evaluation_id=suppressed.candidate_evaluation_id,
        requesting_actor=ACTOR,
        requested_purpose="teacher_candidate_evidence_preview",
        observed_state_revision=committed.state_revision,
    )

    with pytest.raises(CandidateEvidencePreviewError) as caught:
        resolve_candidate_evidence_preview_authority(
            setup.workspace,
            request,
        )

    assert caught.value.code == "candidate_evidence_preview.entry_not_found"
    assert load_current_state(setup.workspace).state_revision == committed.state_revision
