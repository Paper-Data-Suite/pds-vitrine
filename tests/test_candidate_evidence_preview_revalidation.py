from __future__ import annotations

from dataclasses import replace
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
    CANDIDATE_EVIDENCE_PREVIEW_MANIFEST_OPERATION,
    CandidateEvidencePreviewError,
    CandidateEvidencePreviewRequest,
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
from vitrine.producer_adapters import ProducerProjectionAdapterRegistry
from vitrine.storage import load_current_state


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


def test_scoreform_exact_source_revalidates_as_structured_summary(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    detail = _details(setup, "vitrine_scoreform_fixture")[0]
    endpoint = _endpoint(detail)
    before = load_current_state(setup.workspace).state_revision
    gate = StaticAuthorizationGate("allowed")

    result = prepare_candidate_evidence_preview(
        setup.workspace,
        _request(detail),
        adapter_registry=build_development_fixture_adapter_registry(),
        source_read_authorization_gate=gate,
    )

    assert result.preview_kind == "structured_summary"
    assert result.artifact_authorization_required is False
    assert result.unavailable_reason is None
    assert result.authority.source_endpoint == endpoint
    assert result.verified_source.producer_source == endpoint.producer_source
    assert result.verified_source.source_artifact == endpoint.source_artifact
    assert result.verified_source.source_privacy == endpoint.source_privacy
    assert len(gate.requests) == 1
    assert gate.requests[0].operation == CANDIDATE_EVIDENCE_PREVIEW_MANIFEST_OPERATION
    assert gate.requests[0].publication_id == endpoint.core_publication.publication_id
    assert load_current_state(setup.workspace).state_revision == before


def test_quillan_byte_capable_source_is_only_prepared_for_artifact_preview(
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
    before = load_current_state(setup.workspace).state_revision

    result = prepare_candidate_evidence_preview(
        setup.workspace,
        _request(detail),
        adapter_registry=build_development_fixture_adapter_registry(),
        source_read_authorization_gate=StaticAuthorizationGate("allowed"),
    )

    assert result.preview_kind == "artifact_preview"
    assert result.artifact_authorization_required is True
    assert result.unavailable_reason is None
    assert result.verified_source.source_artifact.artifact_kind == "original_student_work"
    assert load_current_state(setup.workspace).state_revision == before


def test_concord_score_summary_stays_structured_and_byte_free(
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

    assert result.preview_kind == "structured_summary"
    assert result.artifact_authorization_required is False


@pytest.mark.parametrize(
    ("outcome", "expected_code"),
    (
        ("denied", "candidate_evidence_preview.source_read_denied"),
        ("unresolved", "candidate_evidence_preview.source_read_unresolved"),
    ),
)
def test_preview_manifest_read_is_explicitly_authorized_and_fail_closed(
    tmp_path: Path,
    outcome: str,
    expected_code: str,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    detail = _details(setup, "vitrine_scoreform_fixture")[0]

    with pytest.raises(CandidateEvidencePreviewError) as raised:
        prepare_candidate_evidence_preview(
            setup.workspace,
            _request(detail),
            adapter_registry=build_development_fixture_adapter_registry(),
            source_read_authorization_gate=StaticAuthorizationGate(outcome),
        )

    assert raised.value.code == expected_code


def test_preview_rejects_manifest_integrity_drift_without_vitrine_mutation(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    detail = _details(setup, "vitrine_scoreform_fixture")[0]
    before = load_current_state(setup.workspace).state_revision
    setup.manifest_paths["vitrine_scoreform_fixture"].write_bytes(b"{}\\n")

    with pytest.raises(CandidateEvidencePreviewError) as raised:
        prepare_candidate_evidence_preview(
            setup.workspace,
            _request(detail),
            adapter_registry=build_development_fixture_adapter_registry(),
            source_read_authorization_gate=StaticAuthorizationGate("allowed"),
        )

    assert raised.value.code == "candidate_evidence_preview.source_integrity_failed"
    assert load_current_state(setup.workspace).state_revision == before


class _DriftAdapter:
    def __init__(self, base):
        self._base = base

    @property
    def declaration(self):
        return self._base.declaration

    @property
    def reader(self):
        return self._base.reader

    def project(self, public_model):
        batch = self._base.project(public_model)
        changed = tuple(
            replace(
                source,
                source_artifact=replace(
                    source.source_artifact,
                    artifact_id=f"{source.source_artifact.artifact_id}_drift",
                ),
            )
            for source in batch.projected_sources
        )
        return replace(batch, projected_sources=changed)


def _drift_registry() -> ProducerProjectionAdapterRegistry:
    base = build_development_fixture_adapter_registry()
    return ProducerProjectionAdapterRegistry(
        adapters=tuple(_DriftAdapter(adapter) for adapter in base.adapters)
    )


def test_preview_fails_closed_when_reprojection_no_longer_matches_exact_source(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    detail = _details(setup, "vitrine_scoreform_fixture")[0]

    with pytest.raises(CandidateEvidencePreviewError) as raised:
        prepare_candidate_evidence_preview(
            setup.workspace,
            _request(detail),
            adapter_registry=_drift_registry(),
            source_read_authorization_gate=StaticAuthorizationGate("allowed"),
        )

    assert raised.value.code == "candidate_evidence_preview.source_drift"
