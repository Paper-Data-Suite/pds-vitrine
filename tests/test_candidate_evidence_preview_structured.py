from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from pds_core.academic_catalog import PublicationCatalogQuery

from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_evidence_preview import (
    CandidateEvidencePreviewRequest,
    CandidateEvidenceStructuredPreview,
    build_candidate_evidence_structured_preview,
    prepare_candidate_evidence_preview,
)
from vitrine.candidate_inbox import (
    CandidateInboxQuery,
    get_candidate_inbox_detail,
    list_candidate_inbox,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import SourceArtifactReference
from vitrine.producer_adapters import ProjectionDisplaySnapshot, ProjectionField


def _discover(setup: object, module_id: str) -> None:
    result = discover_and_evaluate_candidates(
        getattr(setup, "workspace"),
        CandidateDiscoveryRequest(
            portfolio_id=getattr(setup, "portfolio_id"),
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id=module_id,
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


def _details(setup: object, module_id: str):
    inbox = list_candidate_inbox(
        getattr(setup, "workspace"),
        CandidateInboxQuery(
            portfolio_id=getattr(setup, "portfolio_id"),
            producer_module_id=module_id,
            limit=100,
        ),
    )
    return tuple(
        get_candidate_inbox_detail(
            getattr(setup, "workspace"),
            item.entry_id,
        )
        for item in inbox.items
    )


def _endpoint(detail):
    if detail.evaluation is not None and detail.evaluation.source_endpoint is not None:
        return detail.evaluation.source_endpoint
    assert detail.candidate is not None
    return detail.candidate.source_endpoint


def _request(detail) -> CandidateEvidencePreviewRequest:
    item = detail.item
    return CandidateEvidencePreviewRequest(
        portfolio_id=item.portfolio_id,
        portfolio_subject_id=item.portfolio_subject_id,
        entry_id=item.entry_id,
        candidate_id=item.candidate_id,
        candidate_evaluation_id=item.current_evaluation_id,
        requesting_actor=ACTOR,
        requested_purpose="teacher_preview",
        observed_state_revision=detail.observed_state_revision,
    )


def test_scoreform_structured_preview_uses_instructional_allowlist(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    detail = _details(setup, "vitrine_scoreform_fixture")[0]

    result = prepare_candidate_evidence_preview(
        setup.workspace,
        _request(detail),
        adapter_registry=build_development_fixture_adapter_registry(),
        source_read_authorization_gate=StaticAuthorizationGate("allowed"),
    )

    preview = result.structured_preview
    assert isinstance(preview, CandidateEvidenceStructuredPreview)
    assert preview.title == "Synthetic argument_assessment"
    assert preview.evidence_kind == "Assessment Attempt"
    labels = {item.label for item in preview.fields}
    assert {
        "Attempt",
        "Recorded",
        "Points earned",
        "Points possible",
        "Response summary",
        "Standards / alignment",
    }.issubset(labels)
    keys = {item.source_key for item in preview.fields}
    assert "assignment_id" not in keys
    assert "class_id" not in keys
    assert "provenance_kind" not in keys
    assert "provenance_source_revision" not in keys


def test_concord_structured_preview_omits_target_identity(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_concord_fixture")
    detail = next(
        item
        for item in _details(setup, "vitrine_concord_fixture")
        if _endpoint(item).source_artifact is not None
        and _endpoint(item).source_artifact.artifact_kind == "assessment_summary"
    )

    result = prepare_candidate_evidence_preview(
        setup.workspace,
        _request(detail),
        adapter_registry=build_development_fixture_adapter_registry(),
        source_read_authorization_gate=StaticAuthorizationGate("allowed"),
    )

    preview = result.structured_preview
    assert isinstance(preview, CandidateEvidenceStructuredPreview)
    assert preview.title == "Synthetic water_quality_activity"
    assert preview.evidence_kind == "Assessment Evidence"
    labels = {item.label for item in preview.fields}
    assert {"Status", "Scale", "Target type"}.issubset(labels)
    keys = {item.source_key for item in preview.fields}
    assert "target_id" not in keys
    assert "activity_id" not in keys
    assert "group_id" not in keys


def test_artifact_preview_never_carries_structured_payload(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_quillan_fixture")
    detail = next(
        item
        for item in _details(setup, "vitrine_quillan_fixture")
        if _endpoint(item).source_artifact is not None
        and _endpoint(item).source_artifact.artifact_kind == "original_student_work"
    )

    result = prepare_candidate_evidence_preview(
        setup.workspace,
        _request(detail),
        adapter_registry=build_development_fixture_adapter_registry(),
        source_read_authorization_gate=StaticAuthorizationGate("allowed"),
    )

    assert result.preview_kind == "artifact_preview"
    assert result.structured_preview is None


def test_quillan_review_allowlist_excludes_private_and_raw_payload_fields(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    detail = _details(setup, "vitrine_scoreform_fixture")[0]
    prepared = prepare_candidate_evidence_preview(
        setup.workspace,
        _request(detail),
        adapter_registry=build_development_fixture_adapter_registry(),
        source_read_authorization_gate=StaticAuthorizationGate("allowed"),
    )

    source = replace(
        prepared.verified_source,
        producer_source=replace(
            prepared.verified_source.producer_source,
            producer_module_id="quillan",
            source_record_kind="academic_result_review",
        ),
        source_artifact=SourceArtifactReference(
            artifact_id="quillan_review_summary",
            artifact_kind="assessment_summary",
            representation_kind="quillan:review_summary",
            media_type="application/vnd.pds.vitrine.quillan-review-summary+json",
            source_locator=None,
            native_revision=1,
            source_digest=None,
            byte_size=None,
            language=None,
            accessibility_relationship=None,
        ),
        display_snapshot=ProjectionDisplaySnapshot(
            title="Quillan review — assignment_alpha",
            summary="Review summary.",
            fields=(
                ProjectionField(key="writing_type", value="short_analysis"),
                ProjectionField(key="review_state", value="complete"),
                ProjectionField(
                    key="minimum_requirement_status",
                    value="met",
                ),
                ProjectionField(
                    key="overall_rating_standard_ids",
                    value=("RL.CR.9-10.1",),
                ),
                ProjectionField(
                    key="overall_rating_values",
                    value=("proficient",),
                ),
                ProjectionField(
                    key="minimum_requirement_teacher_note_disposition",
                    value="private",
                ),
                ProjectionField(
                    key="review_payload_json_base64_chunks",
                    value=("SECRET_PAYLOAD",),
                ),
                ProjectionField(
                    key="review_source_relative_path",
                    value="private/review.json",
                ),
                ProjectionField(
                    key="review_source_sha256",
                    value="f" * 64,
                ),
            ),
        ),
    )

    preview = build_candidate_evidence_structured_preview(
        prepared.authority,
        source,
    )

    assert preview.evidence_kind == "Review"
    keys = {item.source_key for item in preview.fields}
    assert "writing_type" in keys
    assert "review_state" in keys
    assert "minimum_requirement_status" in keys
    assert "overall_rating_standard_ids" in keys
    assert "overall_rating_values" in keys
    assert "minimum_requirement_teacher_note_disposition" not in keys
    assert "review_payload_json_base64_chunks" not in keys
    assert "review_source_relative_path" not in keys
    assert "review_source_sha256" not in keys
    rendered = " ".join(item.value for item in preview.fields)
    assert "SECRET_PAYLOAD" not in rendered
    assert "private/review.json" not in rendered
    assert "f" * 64 not in rendered


def test_structured_preview_bounds_large_tuple_values(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    detail = _details(setup, "vitrine_scoreform_fixture")[0]
    prepared = prepare_candidate_evidence_preview(
        setup.workspace,
        _request(detail),
        adapter_registry=build_development_fixture_adapter_registry(),
        source_read_authorization_gate=StaticAuthorizationGate("allowed"),
    )
    source = replace(
        prepared.verified_source,
        display_snapshot=replace(
            prepared.verified_source.display_snapshot,
            fields=(
                ProjectionField(key="attempt_number", value=1),
                ProjectionField(
                    key="response_states",
                    value=tuple(f"{index}:answered" for index in range(1, 80)),
                ),
            ),
        ),
    )

    preview = build_candidate_evidence_structured_preview(
        prepared.authority,
        source,
    )
    response = next(
        item for item in preview.fields if item.source_key == "response_states"
    )

    assert "+55 more" in response.value
    assert len(response.value) <= 1200
