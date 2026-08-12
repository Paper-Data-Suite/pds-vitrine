from __future__ import annotations

from pathlib import Path

import pytest
from pds_core.academic_catalog import rebuild_academic_catalog
from pds_core.registry_services import (
    PublicationManifestRequest,
    get_canonical_publication_record,
    supersede_manifest_revision,
)

from scripts.curation_fixture_support import (
    ACTOR,
    APPROVAL_REQUIREMENT_ID,
    STUDENT_ACTOR,
    CurationFixtureWorkspace,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.curation_services import (
    CurationWorkflowError,
    create_annotation,
    create_working_composition,
    decide_selection_proposal,
    invalidate_selection,
    place_selection,
    propose_candidate_selection,
    replace_selection,
    review_curation_target,
    revise_annotation,
    select_candidate_directly,
)
from vitrine.curation_state import project_curation_state
from vitrine.models import (
    CurationAnnotation,
    CurationReviewDecision,
    CurationTargetRef,
    PlacementLifecycleEvent,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioSelection,
    SelectionDecision,
    SelectionLifecycleEvent,
    SelectionProposal,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionPointerRevision,
)
from vitrine.storage import load_current_records, load_current_state


def _records(setup: CurationFixtureWorkspace):
    return load_current_records(setup.workspace)


def _state(setup: CurationFixtureWorkspace):
    return project_curation_state(_records(setup))


def _direct_select(
    setup: CurationFixtureWorkspace,
    candidate: PortfolioCandidate,
    section_id: str,
) -> PortfolioSelection:
    result = select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=(section_id,),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return next(item for item in result.records if isinstance(item, PortfolioSelection))


def _place(
    setup: CurationFixtureWorkspace,
    selection: PortfolioSelection,
    section_id: str,
) -> PortfolioPlacement:
    heads = _state(setup).arrangement_pointer_heads(
        setup.portfolio_id,
        setup.profile_binding_id,
        section_id,
    )
    expected_pointer = heads[0].pointer_revision if len(heads) == 1 else None
    result = place_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_id=selection.selection_id,
        section_id=section_id,
        placed_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_arrangement_pointer_revision=expected_pointer,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    return next(item for item in result.records if isinstance(item, PortfolioPlacement))


def _candidate_by_module(
    setup: CurationFixtureWorkspace,
    module_id: str,
) -> tuple[PortfolioCandidate, ...]:
    return tuple(
        item
        for item in _records(setup)
        if isinstance(item, PortfolioCandidate)
        and item.source_endpoint.producer_source.producer_module_id == module_id
    )


def test_changes_requested_supports_explicit_successor_proposal(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = setup.candidate("evidence_selected")
    first_result = propose_candidate_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        proposer=STUDENT_ACTOR,
        proposal_origin="student",
        proposed_section_ids=("baseline",),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    first = next(
        item for item in first_result.records if isinstance(item, SelectionProposal)
    )
    decision_result = decide_selection_proposal(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_proposal_id=first.selection_proposal_id,
        decision="changes_requested",
        decided_by=ACTOR,
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    decision = next(
        item for item in decision_result.records if isinstance(item, SelectionDecision)
    )
    assert decision.decision == "changes_requested"
    assert decision.resulting_selection_id is None

    successor_result = propose_candidate_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        proposer=STUDENT_ACTOR,
        proposal_origin="student",
        proposed_section_ids=("gallery",),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        predecessor_proposal_id=first.selection_proposal_id,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    successor = next(
        item for item in successor_result.records if isinstance(item, SelectionProposal)
    )
    assert successor.predecessor_proposal_id == first.selection_proposal_id
    assert not any(isinstance(item, PortfolioSelection) for item in _records(setup))


def test_direct_selection_provenance_and_duplicate_active_guard(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = setup.candidate("evidence_selected")
    result = select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=("baseline",),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    proposal = next(item for item in result.records if isinstance(item, SelectionProposal))
    decision = next(item for item in result.records if isinstance(item, SelectionDecision))
    selection = next(item for item in result.records if isinstance(item, PortfolioSelection))
    event = next(
        item for item in result.records if isinstance(item, SelectionLifecycleEvent)
    )
    assert proposal.proposal_origin == "direct_selection"
    assert decision.decision == "accepted"
    assert decision.selection_proposal_id == proposal.selection_proposal_id
    assert decision.resulting_selection_id == selection.selection_id
    assert event.event_kind == "activated"
    assert event.basis_selection_decision_id == decision.selection_decision_id

    with pytest.raises(CurationWorkflowError) as exc:
        select_candidate_directly(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            candidate_id=candidate.candidate_id,
            selected_by=ACTOR,
            proposed_section_ids=("gallery",),
            expected_state_revision=setup.state_revision,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert exc.value.code == "curation.selection_duplicate_active"


def test_student_annotation_revision_and_waiver_authority_boundary(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    selection = _direct_select(setup, setup.candidate("evidence_selected"), "baseline")
    created = create_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        purpose="curator_context",
        target_scope="selection",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id=selection.selection_id,
            ),
        ),
        author=STUDENT_ACTOR,
        content="Student-authored annotation for this exact Selection.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    first = next(
        item for item in created.records if isinstance(item, CurationAnnotation)
    )
    revised = revise_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        annotation_id=first.annotation_id,
        expected_annotation_revision=1,
        author=STUDENT_ACTOR,
        content="Corrected student-authored annotation.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
    )
    second = next(
        item for item in revised.records if isinstance(item, CurationAnnotation)
    )
    assert second.annotation_id == first.annotation_id
    assert second.annotation_revision == 2
    assert second.predecessor_annotation_revision == 1

    before_revision = setup.state_revision
    before_audience_count = sum(
        getattr(item, "record_type", "") == "audience_context"
        for item in _records(setup)
    )
    target = (
        CurationTargetRef(
            target_kind="selection",
            target_id=selection.selection_id,
        ),
    )
    with pytest.raises(CurationWorkflowError) as exc:
        review_curation_target(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            target_scope="selection",
            target_references=target,
            decision="waived",
            reviewed_by=ACTOR,
            reason="Attempt waiver without explicit waiver authority.",
            expected_state_revision=before_revision,
            authority_gate=StaticCurationAuthorityGate(waiver_permitted=False),
            approval_requirement_id=APPROVAL_REQUIREMENT_ID,
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert exc.value.code == "curation.review_waiver_not_permitted"
    assert load_current_state(setup.workspace).state_revision == before_revision

    allowed = review_curation_target(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        target_scope="selection",
        target_references=target,
        decision="waived",
        reviewed_by=ACTOR,
        reason="Synthetic explicit waiver authority.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(waiver_permitted=True),
        approval_requirement_id=APPROVAL_REQUIREMENT_ID,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    assert any(isinstance(item, CurationReviewDecision) for item in allowed.records)
    records = _records(setup)
    assert sum(
        getattr(item, "record_type", "") == "audience_context" for item in records
    ) == before_audience_count
    assert not any(
        getattr(item, "record_type", "").startswith("snapshot_") for item in records
    )


def test_selection_replacement_migrates_explicitly_and_invalidation_preserves_history(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    old_selection = _direct_select(
        setup,
        setup.candidate("evidence_selected"),
        "baseline",
    )
    old_placement = _place(setup, old_selection, "baseline")
    baseline_pointer = _state(setup).arrangement_pointer_heads(
        setup.portfolio_id,
        setup.profile_binding_id,
        "baseline",
    )[0]
    replaced = replace_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_id=old_selection.selection_id,
        successor_candidate_id=setup.candidate("evidence_approved").candidate_id,
        replaced_by=ACTOR,
        placement_dispositions={old_placement.placement_id: "later_work"},
        expected_state_revision=setup.state_revision,
        expected_pointer_revisions={
            "baseline": baseline_pointer.pointer_revision,
            "later_work": None,
        },
        authority_gate=StaticCurationAuthorityGate(),
        reason="Use the later exact Candidate and migrate the Placement explicitly.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    new_selection = next(
        item for item in replaced.records if isinstance(item, PortfolioSelection)
    )
    new_placement = next(
        item for item in replaced.records if isinstance(item, PortfolioPlacement)
    )
    placement_events = tuple(
        item for item in replaced.records if isinstance(item, PlacementLifecycleEvent)
    )
    assert new_selection.predecessor_selection_id == old_selection.selection_id
    assert new_selection.candidate_id == setup.candidate("evidence_approved").candidate_id
    assert new_placement.selection_id == new_selection.selection_id
    assert new_placement.section_id == "later_work"
    assert any(
        item.placement_id == old_placement.placement_id
        and item.event_kind == "replaced"
        and item.successor_placement_id == new_placement.placement_id
        for item in placement_events
    )
    state = _state(setup)
    assert state.selection_status(old_selection.selection_id) == "replaced"
    assert state.selection_status(new_selection.selection_id) == "activated"
    baseline = state.current_arrangement(
        setup.portfolio_id,
        setup.profile_binding_id,
        "baseline",
    )
    later = state.current_arrangement(
        setup.portfolio_id,
        setup.profile_binding_id,
        "later_work",
    )
    assert baseline is not None and baseline.placement_ids == ()
    assert later is not None and later.placement_ids == (new_placement.placement_id,)

    later_pointer = state.arrangement_pointer_heads(
        setup.portfolio_id,
        setup.profile_binding_id,
        "later_work",
    )[0]
    invalidate_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_id=new_selection.selection_id,
        invalidated_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_pointer_revisions={"later_work": later_pointer.pointer_revision},
        authority_gate=StaticCurationAuthorityGate(),
        reason="Synthetic invalidation preserving immutable history.",
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    state = _state(setup)
    assert state.selection_status(old_selection.selection_id) == "replaced"
    assert state.selection_status(new_selection.selection_id) == "invalidated"
    persisted_selection_ids = {
        item.selection_id for item in _records(setup) if isinstance(item, PortfolioSelection)
    }
    assert {old_selection.selection_id, new_selection.selection_id} <= persisted_selection_ids


def test_composition_preserves_unresolved_obligations_and_rejects_stale_pointer(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    first = create_working_composition(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        created_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_composition_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    inventory = next(
        item
        for item in first.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    pointer = next(
        item
        for item in first.records
        if isinstance(item, WorkingPortfolioCompositionPointerRevision)
    )
    assert inventory.coherence_state == "coherent_with_unresolved_obligations"
    assert "section_minimum_missing" in inventory.unresolved_obligation_codes
    assert "reflection_required" in inventory.unresolved_obligation_codes

    create_annotation(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        purpose="curator_context",
        target_scope="section",
        target_references=(
            CurationTargetRef(target_kind="section", target_id="baseline"),
        ),
        author=ACTOR,
        content="Change current curation after the first Composition pointer.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    with pytest.raises(CurationWorkflowError) as exc:
        create_working_composition(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            created_by=ACTOR,
            expected_state_revision=setup.state_revision,
            expected_composition_pointer_revision=None,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert pointer.pointer_revision == 1
    assert exc.value.code == "curation.composition_pointer_conflict"


def test_quillan_and_concord_semantic_boundaries_survive_curation(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    work = setup.candidate("evidence_selected")
    feedback = setup.candidate("feedback_student")
    assert work.candidate_id != feedback.candidate_id
    assert work.source_endpoint.producer_source.source_record_id == "evidence_selected"
    assert feedback.source_endpoint.producer_source.source_record_id == "feedback_student"
    assert work.source_endpoint.source_artifact is not None
    assert feedback.source_endpoint.source_artifact is not None
    assert work.source_endpoint.source_artifact.artifact_kind == "original_student_work"
    assert feedback.source_endpoint.source_artifact.artifact_kind == "rendered_feedback"

    work_selection = _direct_select(setup, work, "baseline")
    feedback_selection = _direct_select(setup, feedback, "feedback")
    _place(setup, work_selection, "baseline")
    _place(setup, feedback_selection, "feedback")

    concord_candidates = _candidate_by_module(setup, "vitrine_concord_fixture")
    assert len(concord_candidates) == 1
    concord = concord_candidates[0]
    relationship_kinds = {
        item.relationship_kind
        for item in concord.source_endpoint.subject_relationship_assertions
    }
    assert {"group_member", "artifact_subject", "documented_contributor"} <= relationship_kinds
    assert "artifact_author" not in relationship_kinds
    assert concord.source_endpoint.source_artifact is not None
    assert concord.source_endpoint.source_artifact.artifact_kind == "collaborative_artifact"

    concord_selection = _direct_select(setup, concord, "collaborative")
    _place(setup, concord_selection, "collaborative")
    selections = tuple(
        item for item in _records(setup) if isinstance(item, PortfolioSelection)
    )
    concord_selection_ids = {
        item.selection_id
        for item in selections
        if item.candidate_id == concord.candidate_id
    }
    assert concord_selection_ids == {concord_selection.selection_id}
    assert {work_selection.candidate_id, feedback_selection.candidate_id} == {
        work.candidate_id,
        feedback.candidate_id,
    }


def test_source_supersession_does_not_retarget_historical_selection(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    first = setup.candidate("evidence_selected")
    second = setup.candidate("evidence_approved")
    selected = _direct_select(setup, first, "baseline")
    previous = get_canonical_publication_record(
        setup.workspace,
        first.source_endpoint.core_publication.publication_id,
    )
    old_manifest = setup.candidate_setup.manifest_paths["vitrine_quillan_fixture"]
    next_manifest = old_manifest.with_name("2.json")
    next_manifest.write_bytes(old_manifest.read_bytes())
    supersede_manifest_revision(
        setup.workspace,
        PublicationManifestRequest(
            work=previous.work,
            source_record=previous.source_record,
            publication_kind=previous.publication_kind,
            capabilities=previous.capabilities,
            record_set_id=previous.record_set_id,
            record_set_revision=previous.record_set_revision + 1,
            manifest_contract_version=previous.manifest_contract_version,
            manifest_path=next_manifest.relative_to(setup.workspace).as_posix(),
            academic_work_registration_revision=(
                previous.academic_work_registration_revision
            ),
        ),
        expected_current_publication_id=previous.publication_id,
    )
    rebuild_academic_catalog(setup.workspace)

    with pytest.raises(CurationWorkflowError) as exc:
        select_candidate_directly(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            candidate_id=second.candidate_id,
            selected_by=ACTOR,
            proposed_section_ids=("later_work",),
            expected_state_revision=setup.state_revision,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert exc.value.code == "curation.candidate_source_historical"
    state = _state(setup)
    assert state.selection_status(selected.selection_id) == "activated"
    persisted = next(
        item
        for item in _records(setup)
        if isinstance(item, PortfolioSelection)
        and item.selection_id == selected.selection_id
    )
    assert persisted.candidate_id == first.candidate_id
