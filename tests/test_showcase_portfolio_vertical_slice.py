from __future__ import annotations

from collections.abc import Iterator

import pytest

from scripts.curation_fixture_support import StaticCurationAuthorityGate
from scripts.showcase_portfolio_fixture_support import (
    APPROVAL_REQUIREMENT_ID,
    ATTRIBUTION_TEXT,
    PROFILE_BINDING_ID,
    RATIONALE_TEXT,
    ShowcasePortfolioFixture,
    build_showcase_portfolio_fixture,
)
from vitrine.curation_services import create_working_composition, revise_annotation
from vitrine.curation_state import project_curation_state
from vitrine.models import (
    CurationAnnotation,
    PortfolioProfileRevision,
    PortfolioSelection,
    PortfolioSubjectClassLink,
    WorkingPortfolioCompositionInventory,
)
from vitrine.storage import load_current_records, load_current_state


@pytest.fixture(scope="module")
def showcase_setup(tmp_path_factory: pytest.TempPathFactory) -> Iterator[ShowcasePortfolioFixture]:
    result = build_showcase_portfolio_fixture(tmp_path_factory.mktemp("showcase-portfolio-runtime"))
    assert isinstance(result, ShowcasePortfolioFixture)
    yield result


def test_subject_and_profile_are_exact(showcase_setup: ShowcasePortfolioFixture) -> None:
    records = load_current_records(showcase_setup.workspace)
    links = tuple(item for item in records if isinstance(item, PortfolioSubjectClassLink))
    assert len(links) == 1
    assert (
        links[0].student_reference.school_year,
        links[0].student_reference.class_id,
        links[0].student_reference.student_id,
    ) == ("2025-2026", "class-ela12-syn", "student-syn-001")
    profile = next(
        item for item in records
        if isinstance(item, PortfolioProfileRevision)
        and item.portfolio_profile_id == "profile-showcase-rev-001"
    )
    sections = {item.section_id: item for item in profile.sections}
    assert sections["featured_work"].required_relationship_kinds == ("submission_subject",)
    assert sections["collaboration"].required_relationship_kinds == ("documented_contributor",)
    assert profile.audience_rules[0].audience_class == "external_reviewer"


def test_concord_projection_keeps_relationships_and_score_targets_separate(
    showcase_setup: ShowcasePortfolioFixture,
) -> None:
    artifact = next(
        item.projected_source for item in showcase_setup.projection_results
        if item.projected_source.projection_kind == "concord_fixture:artifact"
    )
    subject_relationships = {
        item.relationship_kind for item in artifact.source_relationships
        if item.source_subject_kind == "core_student"
        and item.source_subject_id == "student-syn-001"
    }
    assert {"group_member", "artifact_subject", "documented_contributor"} <= subject_relationships
    assert "artifact_author" not in subject_relationships
    group_relationships = {
        item.relationship_kind for item in artifact.source_relationships
        if item.source_subject_kind == "concord_group"
    }
    assert {"artifact_author", "artifact_subject", "represented_group"} <= group_relationships
    assert artifact.source_artifact is not None
    assert artifact.source_artifact.media_type == "text/plain"

    scores = tuple(
        item for item in showcase_setup.projection_results
        if item.projected_source.projection_kind == "concord_fixture:score_summary"
    )
    assert len(scores) == 2
    assert all(item.candidate is None and item.evaluation.outcome == "unresolved" for item in scores)
    assert all(
        dict((field.key, field.value) for field in item.projected_source.display_snapshot.fields)["target_kind"]
        == "concord_group"
        for item in scores
    )
    deferred = next(
        item for item in scores
        if dict((field.key, field.value) for field in item.projected_source.display_snapshot.fields)["disposition"]
        == "deferred"
    )
    assert not any(field.key == "native_value" for field in deferred.projected_source.display_snapshot.fields)


def test_candidates_do_not_auto_select_and_condition_acknowledgement_is_distinct(
    tmp_path, showcase_setup: ShowcasePortfolioFixture
) -> None:
    partial = build_showcase_portfolio_fixture(tmp_path, complete_curation=False)
    assert not isinstance(partial, ShowcasePortfolioFixture)
    workspace, results = partial
    assert not any(isinstance(item, PortfolioSelection) for item in load_current_records(workspace))
    assert sum(item.candidate is not None for item in results) == 2

    group = showcase_setup.candidate("concord-artifact-syn-001")
    assert group.condition_state == "collaborator_review_required"
    group_decision = next(
        item for item in showcase_setup.decisions
        if item.selection_proposal_id == showcase_setup.proposals[1].selection_proposal_id
    )
    assert group_decision.condition_codes == ("collaborator_review_required",)
    assert showcase_setup.review.approval_requirement_id == APPROVAL_REQUIREMENT_ID
    assert showcase_setup.review.curation_review_decision_id not in group_decision.condition_codes


def test_curation_and_composition_freeze_exact_reviewed_revisions(
    showcase_setup: ShowcasePortfolioFixture,
) -> None:
    setup = showcase_setup
    assert setup.attribution.content == ATTRIBUTION_TEXT
    assert setup.rationale.content == RATIONALE_TEXT
    assert setup.rationale.author.actor_kind == "core_student"
    assert tuple(item.target_id for item in setup.rationale.target_references) == tuple(
        item.selection_id for item in setup.selections
    )
    assert tuple(item.target_id for item in setup.review.target_references) == (
        setup.selections[1].selection_id,
        setup.attribution.annotation_id,
    )
    frozen = {
        (item.record_kind, item.record_id, item.revision)
        for item in setup.inventory.included_curation_revisions
    }
    assert ("annotation", setup.attribution.annotation_id, 1) in frozen
    assert ("annotation", setup.rationale.annotation_id, 1) in frozen
    assert setup.inventory.applicable_review_decision_ids == (
        setup.review.curation_review_decision_id,
    )
    state = project_curation_state(load_current_records(setup.workspace))
    featured = state.current_arrangement(setup.composition.portfolio_id, PROFILE_BINDING_ID, "featured_work")
    collaboration = state.current_arrangement(setup.composition.portfolio_id, PROFILE_BINDING_ID, "collaboration")
    assert featured is not None and collaboration is not None
    assert featured.placement_ids == (setup.placements[0].placement_id,)
    assert collaboration.placement_ids == (setup.placements[1].placement_id,)


def test_revised_attribution_does_not_inherit_stale_review(
    showcase_setup: ShowcasePortfolioFixture,
) -> None:
    setup = showcase_setup
    revised = revise_annotation(
        setup.workspace,
        portfolio_id=setup.composition.portfolio_id,
        annotation_id=setup.attribution.annotation_id,
        expected_annotation_revision=1,
        author=setup.attribution.author,
        content=ATTRIBUTION_TEXT + " Reviewed successor.",
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=lambda: setup.attribution.created_at,
    )
    successor = next(item for item in revised.records if isinstance(item, CurationAnnotation))
    assert successor.annotation_revision == 2
    state = project_curation_state(load_current_records(setup.workspace))
    pointer = state.composition_pointer_heads(
        setup.composition.portfolio_id, PROFILE_BINDING_ID
    )[0]
    composed = create_working_composition(
        setup.workspace,
        portfolio_id=setup.composition.portfolio_id,
        created_by=setup.rationale.author,
        expected_state_revision=load_current_state(setup.workspace).state_revision,
        expected_composition_pointer_revision=pointer.pointer_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=lambda: setup.attribution.created_at,
        id_factory=setup.ids,
    )
    inventory = next(
        item for item in composed.records
        if isinstance(item, WorkingPortfolioCompositionInventory)
    )
    assert setup.review.curation_review_decision_id not in inventory.applicable_review_decision_ids
    assert "approval_required" in inventory.unresolved_obligation_codes
