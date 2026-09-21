from __future__ import annotations

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
    CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION,
    CANDIDATE_EVIDENCE_PREVIEW_OPERATION,
    CandidateEvidencePreviewAuthorizationDecision,
    CandidateEvidencePreviewError,
    CandidateEvidencePreviewRequest,
    authorize_candidate_evidence_preview,
    build_candidate_evidence_preview_authorization_request,
    resolve_candidate_evidence_preview_authority,
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
from vitrine.storage import load_current_state
from vitrine.workflow_context import default_workflow_dependencies


def _discover_scoreform(setup: object) -> None:
    discover_and_evaluate_candidates(
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


def _detail(setup: object):
    item = list_candidate_inbox(
        getattr(setup, "workspace"),
        CandidateInboxQuery(
            portfolio_id=getattr(setup, "portfolio_id"),
            limit=20,
        ),
    ).items[0]
    return get_candidate_inbox_detail(
        getattr(setup, "workspace"),
        item.entry_id,
    )


def _request(detail) -> CandidateEvidencePreviewRequest:
    item = detail.item
    return CandidateEvidencePreviewRequest(
        portfolio_id=item.portfolio_id,
        portfolio_subject_id=item.portfolio_subject_id,
        entry_id=item.entry_id,
        candidate_id=item.candidate_id,
        candidate_evaluation_id=item.current_evaluation_id,
        requesting_actor=ACTOR,
        requested_purpose="teacher_review",
        observed_state_revision=detail.observed_state_revision,
    )


def test_preview_authority_resolves_exact_persisted_source_read_only(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    detail = _detail(setup)
    before = load_current_state(setup.workspace).state_revision

    authority = resolve_candidate_evidence_preview_authority(
        setup.workspace,
        _request(detail),
    )

    endpoint = detail.evaluation.source_endpoint
    assert endpoint is not None
    assert (
        authority.contract_version
        == CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION
    )
    assert authority.operation == CANDIDATE_EVIDENCE_PREVIEW_OPERATION
    assert authority.observed_state_revision == before
    assert authority.portfolio_id == detail.item.portfolio_id
    assert authority.portfolio_subject_id == detail.item.portfolio_subject_id
    assert authority.entry_id == detail.item.entry_id
    assert authority.candidate_id == detail.item.candidate_id
    assert (
        authority.candidate_evaluation_id
        == detail.item.current_evaluation_id
    )
    assert (
        authority.source_publication_id
        == endpoint.core_publication.publication_id
    )
    assert (
        authority.producer_module_id
        == endpoint.producer_source.producer_module_id
    )
    assert (
        authority.source_record_id
        == endpoint.producer_source.source_record_id
    )
    assert authority.source_endpoint == endpoint
    assert load_current_state(setup.workspace).state_revision == before


def test_preview_request_has_no_display_label_authority(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    detail = _detail(setup)
    request = _request(detail)

    assert not hasattr(request, "display_label")
    assert not hasattr(request, "title")
    assert not hasattr(request, "source_display_label")


def test_preview_request_preserves_exact_composite_inbox_entry_id(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    detail = _detail(setup)

    request = _request(detail)

    assert request.entry_id == detail.item.entry_id
    assert ":" in request.entry_id


def test_preview_rejects_observed_state_conflict(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    detail = _detail(setup)
    request = _request(detail)
    conflicting = CandidateEvidencePreviewRequest(
        portfolio_id=request.portfolio_id,
        portfolio_subject_id=request.portfolio_subject_id,
        entry_id=request.entry_id,
        candidate_id=request.candidate_id,
        candidate_evaluation_id=request.candidate_evaluation_id,
        requesting_actor=request.requesting_actor,
        requested_purpose=request.requested_purpose,
        observed_state_revision=request.observed_state_revision + 1,
    )

    with pytest.raises(CandidateEvidencePreviewError) as raised:
        resolve_candidate_evidence_preview_authority(
            setup.workspace,
            conflicting,
        )

    assert raised.value.code == "candidate_evidence_preview.state_conflict"


@pytest.mark.parametrize(
    "field,value",
    (
        ("portfolio_id", "portfolio_other"),
        ("portfolio_subject_id", "subject_other"),
        ("candidate_id", "candidate_other"),
        ("candidate_evaluation_id", "evaluation_other"),
    ),
)
def test_preview_rejects_mismatched_persisted_authority(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    detail = _detail(setup)
    values = {
        "portfolio_id": detail.item.portfolio_id,
        "portfolio_subject_id": detail.item.portfolio_subject_id,
        "entry_id": detail.item.entry_id,
        "candidate_id": detail.item.candidate_id,
        "candidate_evaluation_id": detail.item.current_evaluation_id,
        "requesting_actor": ACTOR,
        "requested_purpose": "teacher_review",
        "observed_state_revision": detail.observed_state_revision,
    }
    values[field] = value
    request = CandidateEvidencePreviewRequest(**values)

    with pytest.raises(CandidateEvidencePreviewError) as raised:
        resolve_candidate_evidence_preview_authority(
            setup.workspace,
            request,
        )

    assert raised.value.code == "candidate_evidence_preview.context_mismatch"


def test_evaluation_only_entry_can_resolve_without_fake_candidate(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(
        tmp_path,
        allow_assessment_summary=False,
    )
    _discover_scoreform(setup)
    item = list_candidate_inbox(
        setup.workspace,
        CandidateInboxQuery(
            portfolio_id=setup.portfolio_id,
            evaluation_outcomes=("ineligible",),
            limit=20,
        ),
    ).items[0]
    detail = get_candidate_inbox_detail(setup.workspace, item.entry_id)
    assert item.candidate_id is None

    authority = resolve_candidate_evidence_preview_authority(
        setup.workspace,
        _request(detail),
    )

    assert authority.candidate_id is None
    assert authority.candidate_evaluation_id == item.current_evaluation_id
    assert authority.source_endpoint == detail.evaluation.source_endpoint


class _AllowedGate:
    def authorize(self, _request):
        return CandidateEvidencePreviewAuthorizationDecision(
            outcome="allowed",
            authority_reference="fixture:teacher",
        )


class _DeniedGate:
    def authorize(self, _request):
        return CandidateEvidencePreviewAuthorizationDecision(
            outcome="denied",
            reason_codes=("policy_denied",),
        )


class _UnresolvedGate:
    def authorize(self, _request):
        return CandidateEvidencePreviewAuthorizationDecision(
            outcome="unresolved",
            reason_codes=("policy_unresolved",),
        )


class _BrokenGate:
    def authorize(self, _request):
        raise RuntimeError("provider unavailable")


class _InvalidGate:
    def authorize(self, _request):
        return object()


def test_preview_authorization_request_uses_exact_resolved_source(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    detail = _detail(setup)
    authority = resolve_candidate_evidence_preview_authority(
        setup.workspace,
        _request(detail),
    )

    request = build_candidate_evidence_preview_authorization_request(authority)

    assert request.operation == CANDIDATE_EVIDENCE_PREVIEW_OPERATION
    assert request.portfolio_id == authority.portfolio_id
    assert request.portfolio_subject_id == authority.portfolio_subject_id
    assert request.candidate_id == authority.candidate_id
    assert (
        request.candidate_evaluation_id
        == authority.candidate_evaluation_id
    )
    assert request.source_publication_id == authority.source_publication_id
    assert request.producer_module_id == authority.producer_module_id
    assert request.source_artifact_id == authority.source_artifact_id
    assert request.artifact_kind == authority.artifact_kind
    assert request.representation_kind == authority.representation_kind
    assert request.requesting_actor == ACTOR
    assert request.purpose == "teacher_review"


def test_preview_authorization_is_explicit_and_fail_closed(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    detail = _detail(setup)
    authority = resolve_candidate_evidence_preview_authority(
        setup.workspace,
        _request(detail),
    )
    request = build_candidate_evidence_preview_authorization_request(authority)

    allowed = authorize_candidate_evidence_preview(_AllowedGate(), request)
    assert allowed.outcome == "allowed"
    assert allowed.authority_reference == "fixture:teacher"

    for gate, code in (
        (_DeniedGate(), "candidate_evidence_preview.authorization_denied"),
        (
            _UnresolvedGate(),
            "candidate_evidence_preview.authorization_unresolved",
        ),
        (_BrokenGate(), "candidate_evidence_preview.authorization_unresolved"),
        (_InvalidGate(), "candidate_evidence_preview.authorization_unresolved"),
    ):
        with pytest.raises(CandidateEvidencePreviewError) as raised:
            authorize_candidate_evidence_preview(gate, request)
        assert raised.value.code == code


def test_default_workflow_preview_authorization_is_unresolved(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover_scoreform(setup)
    detail = _detail(setup)
    authority = resolve_candidate_evidence_preview_authority(
        setup.workspace,
        _request(detail),
    )
    request = build_candidate_evidence_preview_authorization_request(authority)
    dependencies = default_workflow_dependencies()

    with pytest.raises(CandidateEvidencePreviewError) as raised:
        authorize_candidate_evidence_preview(
            dependencies.candidate_evidence_preview_authorization_gate,
            request,
        )

    assert raised.value.code == "candidate_evidence_preview.authorization_unresolved"
