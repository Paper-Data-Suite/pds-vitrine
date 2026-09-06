from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from pds_core.academic_catalog import PublicationCatalogQuery
from pds_core.registry_services import (
    PublicationManifestRequest,
    PublicationWithdrawalRequest,
    get_canonical_publication_record,
    supersede_manifest_revision,
    withdraw_publication,
)

import vitrine.producer_reader_services as producer_reader_services
from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_inbox import CandidateInboxQuery, list_candidate_inbox
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.curation_services import (
    CurationAuthorityDecision,
    CurationAuthorityRequest,
    select_candidate_directly,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import (
    PortfolioCandidate,
    PortfolioProfileBinding,
    PortfolioSubjectIdentityDecision,
)
from vitrine.storage import (
    commit_record_batch,
    load_current_records,
    load_current_state,
)


class _AllowedCurationGate:
    def authorize(
        self, _request: CurationAuthorityRequest
    ) -> CurationAuthorityDecision:
        return CurationAuthorityDecision(
            outcome="allowed", authority_reference="fixture:teacher"
        )


def _discover(setup: object, module_id: str = "vitrine_scoreform_fixture"):
    return discover_and_evaluate_candidates(
        getattr(setup, "workspace"),
        CandidateDiscoveryRequest(
            portfolio_id=getattr(setup, "portfolio_id"),
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id=module_id, state="current", limit=20
            ),
            expected_state_revision=getattr(setup, "state_revision"),
        ),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )


def _first_candidate(setup: object) -> PortfolioCandidate:
    return next(
        item
        for item in load_current_records(getattr(setup, "workspace"))
        if isinstance(item, PortfolioCandidate)
    )


def test_profile_binding_successor_marks_candidate_stale_without_rewrite(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    records = load_current_records(setup.workspace)
    candidate = _first_candidate(setup)
    binding = next(
        item
        for item in records
        if isinstance(item, PortfolioProfileBinding)
        and item.profile_binding_id == candidate.profile_binding_id
    )
    before = load_current_state(setup.workspace).state_revision
    successor = PortfolioProfileBinding(
        profile_binding_id="profile_binding_successor",
        portfolio_id=binding.portfolio_id,
        profile_revision=binding.profile_revision,
        bound_at=fixed_clock() + timedelta(seconds=5),
        bound_by=ACTOR,
        binding_reason="Synthetic rebinding for inbox test.",
        predecessor_binding_id=binding.profile_binding_id,
    )
    commit_record_batch(setup.workspace, (successor,), expected_state_revision=before)
    before_read = load_current_state(setup.workspace).state_revision
    result = list_candidate_inbox(setup.workspace, CandidateInboxQuery(stale_only=True))
    assert result.matched_count == 2
    assert all(
        "candidate_inbox.profile_binding_changed" in i.stale_reason_codes
        for i in result.items
    )
    assert all(i.attention_needed for i in result.items)
    assert load_current_state(setup.workspace).state_revision == before_read


def test_subject_link_invalidation_marks_candidate_stale_by_exact_link(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    assertion = _first_candidate(setup).source_endpoint.subject_relationship_assertions[
        0
    ]
    before = load_current_state(setup.workspace).state_revision
    decision = PortfolioSubjectIdentityDecision(
        identity_decision_id="identity_decision_invalidate_candidate_link",
        decision_type="invalidate_link",
        subject_ids=(),
        subject_link_ids=(assertion.subject_link_id,),
        decided_at=fixed_clock() + timedelta(seconds=5),
        decided_by=ACTOR,
        authority_source="fixture:teacher",
        basis_type="direct_teacher_knowledge",
        basis_summary="Synthetic exact-link invalidation for inbox test.",
    )
    commit_record_batch(setup.workspace, (decision,), expected_state_revision=before)
    result = list_candidate_inbox(setup.workspace, CandidateInboxQuery(stale_only=True))
    assert result.matched_count == 2
    assert all(
        "candidate_inbox.subject_relationship_changed" in i.stale_reason_codes
        for i in result.items
    )


def test_publication_successor_marks_old_candidates_stale_without_discovery(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    previous = get_canonical_publication_record(
        setup.workspace, setup.scoreform_publication_id
    )
    old_manifest = setup.manifest_paths["vitrine_scoreform_fixture"]
    successor_manifest = old_manifest.with_name("inbox-successor.json")
    successor_manifest.write_bytes(old_manifest.read_bytes())
    successor = supersede_manifest_revision(
        setup.workspace,
        PublicationManifestRequest(
            work=previous.work,
            source_record=previous.source_record,
            publication_kind=previous.publication_kind,
            capabilities=previous.capabilities,
            record_set_id=previous.record_set_id,
            record_set_revision=previous.record_set_revision + 1,
            manifest_contract_version=previous.manifest_contract_version,
            manifest_path=successor_manifest.relative_to(setup.workspace).as_posix(),
            academic_work_registration_revision=previous.academic_work_registration_revision,
        ),
        expected_current_publication_id=previous.publication_id,
    )
    assert successor.publication.publication_id != previous.publication_id
    result = list_candidate_inbox(setup.workspace, CandidateInboxQuery(stale_only=True))
    assert result.matched_count == 2
    assert all(
        "candidate_inbox.publication_superseded" in i.stale_reason_codes
        for i in result.items
    )


def test_publication_withdrawal_marks_candidate_stale(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    withdraw_publication(
        setup.workspace,
        PublicationWithdrawalRequest(
            publication_id=setup.scoreform_publication_id,
            reason="Synthetic withdrawal.",
        ),
    )
    result = list_candidate_inbox(setup.workspace, CandidateInboxQuery(stale_only=True))
    assert result.matched_count == 2
    assert all(
        "candidate_inbox.publication_withdrawn" in i.stale_reason_codes
        for i in result.items
    )


def test_conditional_candidate_is_attention_without_quality_inference(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_concord_fixture")
    result = list_candidate_inbox(
        setup.workspace, CandidateInboxQuery(attention_only=True)
    )
    collaborator = tuple(
        i
        for i in result.items
        if i.candidate_condition == "collaborator_review_required"
    )
    assert len(collaborator) == 1
    assert collaborator[0].stale_state == "current"
    assert collaborator[0].attention_reason_codes == (
        "candidate_inbox.collaborator_review_required",
    )


def test_selected_stale_candidate_gets_explicit_attention_without_mutation(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    candidate = _first_candidate(setup)
    select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=(candidate.eligible_section_ids[0],),
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=_AllowedCurationGate(),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    withdraw_publication(
        setup.workspace,
        PublicationWithdrawalRequest(
            publication_id=setup.scoreform_publication_id,
            reason="Synthetic withdrawal after selection.",
        ),
    )
    before = load_current_state(setup.workspace).state_revision
    result = list_candidate_inbox(
        setup.workspace,
        CandidateInboxQuery(attention_only=True, selected_state="selected"),
    )
    assert result.matched_count == 1
    assert (
        "candidate_inbox.selected_candidate_stale"
        in result.items[0].attention_reason_codes
    )
    assert load_current_state(setup.workspace).state_revision == before


def test_staleness_does_not_call_producer_source_read_services(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup)
    calls = 0

    def forbidden(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("producer source read must not run")

    monkeypatch.setattr(
        producer_reader_services, "read_authorized_producer_manifest", forbidden
    )
    monkeypatch.setattr(
        producer_reader_services, "read_verified_publication_manifest_bytes", forbidden
    )
    before = load_current_state(setup.workspace).state_revision
    result = list_candidate_inbox(setup.workspace)
    assert result.matched_count == 2 and calls == 0
    assert load_current_state(setup.workspace).state_revision == before
