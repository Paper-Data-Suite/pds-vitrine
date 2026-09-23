from __future__ import annotations

from dataclasses import replace

import pytest

from tests.runtime_fixture_factory import NOW, TEACHER, make_improvement_graph
from vitrine.curation_state import project_curation_state
from vitrine.models import (
    PlacementLifecycleEvent,
    PortfolioProfileRequirement,
    SectionArrangementPointerRevision,
    SelectionLifecycleEvent,
)
from vitrine.selection_placement_guidance import (
    SELECTION_PLACEMENT_GUIDANCE_CONTRACT_VERSION,
    SelectionPlacementGuidanceError,
    profile_requirement_ids_for_sections,
    project_selection_placement_guidance,
)


def _fixture_context():
    graph = make_improvement_graph()
    original = graph.profile_revisions[0]
    sections = []
    for section in original.sections:
        if section.section_id == "later_work":
            sections.append(replace(section, maximum_placements=3))
        elif section.section_id == "reflection":
            sections.append(
                replace(
                    section,
                    label="Comparison Reflection",
                    maximum_placements=0,
                )
            )
        else:
            sections.append(section)
    profile = replace(original, sections=tuple(sections))
    candidate = replace(
        graph.candidates[0],
        eligible_profile_rule_ids=(
            "baseline_cardinality",
            "later_evidence_cardinality",
        ),
        eligible_section_ids=("baseline", "later_work", "reflection"),
    )
    requirements = (
        PortfolioProfileRequirement(
            portfolio_profile_id=profile.portfolio_profile_id,
            profile_revision=profile.profile_revision,
            requirement_id="baseline_cardinality",
            requirement_kind="section",
            obligation="required",
            title="Baseline evidence",
            statement="Include one baseline item.",
            scope_kind="section",
            scope_reference="baseline",
            satisfaction_class="section_cardinality",
        ),
        PortfolioProfileRequirement(
            portfolio_profile_id=profile.portfolio_profile_id,
            profile_revision=profile.profile_revision,
            requirement_id="later_evidence_cardinality",
            requirement_kind="section",
            obligation="required",
            title="Later evidence",
            statement="Include later evidence.",
            scope_kind="section",
            scope_reference="later_work",
            satisfaction_class="section_cardinality",
        ),
        PortfolioProfileRequirement(
            portfolio_profile_id=profile.portfolio_profile_id,
            profile_revision=profile.profile_revision,
            requirement_id="comparison_reflection",
            requirement_kind="reflection",
            obligation="required",
            title="Student comparison reflection",
            statement="The student interprets the comparison.",
            scope_kind="section",
            scope_reference="reflection",
            satisfaction_class="reflection_record",
        ),
        PortfolioProfileRequirement(
            portfolio_profile_id=profile.portfolio_profile_id,
            profile_revision=profile.profile_revision,
            requirement_id="teacher_review",
            requirement_kind="approval",
            obligation="required",
            title="Teacher review",
            statement="A teacher reviews the portfolio.",
            scope_kind="portfolio",
            scope_reference=None,
            satisfaction_class="review_decision",
        ),
    )
    return graph, profile, candidate, requirements


def _activated_placement(placement_id: str) -> PlacementLifecycleEvent:
    return PlacementLifecycleEvent(
        placement_lifecycle_event_id=f"event_{placement_id}",
        placement_id=placement_id,
        event_kind="activated",
        event_at=NOW,
        actor=TEACHER,
        authority_reference="issue97_test",
        reason="Activate test Placement.",
    )


def _activated_selection(selection_id: str) -> SelectionLifecycleEvent:
    return SelectionLifecycleEvent(
        selection_lifecycle_event_id=f"event_{selection_id}",
        selection_id=selection_id,
        event_kind="activated",
        event_at=NOW,
        actor=TEACHER,
        authority_reference="issue97_test",
        reason="Activate test Selection.",
        basis_selection_decision_id=f"decision_{selection_id}",
    )


def _section(guidance, section_id: str):
    return next(item for item in guidance.sections if item.section_id == section_id)


def test_fresh_selection_keeps_profile_fit_but_excludes_maximum_zero_section() -> None:
    _, profile, candidate, requirements = _fixture_context()
    curation = project_curation_state((profile, candidate, *requirements))

    guidance = project_selection_placement_guidance(
        candidate=candidate,
        profile=profile,
        curation=curation,
        operation="fresh_selection",
    )

    assert guidance.contract_version == SELECTION_PLACEMENT_GUIDANCE_CONTRACT_VERSION
    assert guidance.semantic_eligible_section_ids == (
        "baseline",
        "later_work",
        "reflection",
    )
    assert guidance.actionable_section_ids == ("baseline", "later_work")
    reflection = _section(guidance, "reflection")
    assert reflection.semantic_candidate_eligible is True
    assert reflection.placement_bearing is False
    assert reflection.current_actionable is False
    assert reflection.unavailability_reason_codes == ("section_not_placement_bearing",)
    assert candidate.eligible_section_ids == ("baseline", "later_work", "reflection")


def test_fresh_selection_uses_current_capacity_without_rewriting_candidate() -> None:
    graph, profile, candidate, requirements = _fixture_context()
    placement = graph.placements[0]
    curation = project_curation_state(
        (
            profile,
            candidate,
            *requirements,
            placement,
            _activated_placement(placement.placement_id),
        )
    )

    guidance = project_selection_placement_guidance(
        candidate=candidate,
        profile=profile,
        curation=curation,
        operation="fresh_selection",
    )

    baseline = _section(guidance, "baseline")
    assert baseline.minimum_placements == 1
    assert baseline.active_placement_count == 1
    assert baseline.remaining_capacity == 0
    assert baseline.current_actionable is False
    assert "section_full" in baseline.unavailability_reason_codes
    assert guidance.actionable_section_ids == ("later_work",)
    assert candidate.eligible_section_ids == ("baseline", "later_work", "reflection")


def test_requirement_scope_is_candidate_matched_and_section_specific() -> None:
    _, profile, candidate, requirements = _fixture_context()
    candidate = replace(
        candidate,
        eligible_profile_rule_ids=(
            "baseline_cardinality",
            "later_evidence_cardinality",
            "comparison_reflection",
            "teacher_review",
        ),
    )
    curation = project_curation_state((profile, candidate, *requirements))
    guidance = project_selection_placement_guidance(
        candidate=candidate,
        profile=profile,
        curation=curation,
        operation="fresh_selection",
    )

    assert _section(guidance, "baseline").relevant_profile_requirement_ids == (
        "baseline_cardinality",
    )
    assert _section(guidance, "later_work").relevant_profile_requirement_ids == (
        "later_evidence_cardinality",
    )
    assert _section(guidance, "reflection").relevant_profile_requirement_ids == ()
    assert profile_requirement_ids_for_sections(
        guidance, ("baseline", "later_work")
    ) == ("baseline_cardinality", "later_evidence_cardinality")
    assert "comparison_reflection" not in profile_requirement_ids_for_sections(
        guidance, ("baseline",)
    )
    assert "teacher_review" not in profile_requirement_ids_for_sections(
        guidance, ("later_work",)
    )
    with pytest.raises(SelectionPlacementGuidanceError) as error:
        profile_requirement_ids_for_sections(guidance, ("reflection",))
    assert error.value.code == "selection_placement_guidance.section_not_actionable"


def test_placement_excludes_duplicate_same_selection_destination() -> None:
    graph, profile, candidate, requirements = _fixture_context()
    profile = replace(
        profile,
        sections=tuple(
            replace(section, maximum_placements=2)
            if section.section_id == "baseline"
            else section
            for section in profile.sections
        ),
    )
    selection = graph.selections[0]
    placement = graph.placements[0]
    curation = project_curation_state(
        (
            profile,
            candidate,
            *requirements,
            selection,
            _activated_selection(selection.selection_id),
            placement,
            _activated_placement(placement.placement_id),
        )
    )

    guidance = project_selection_placement_guidance(
        candidate=candidate,
        profile=profile,
        curation=curation,
        operation="placement",
        selection_id=selection.selection_id,
    )

    baseline = _section(guidance, "baseline")
    assert baseline.remaining_capacity == 1
    assert baseline.current_actionable is False
    assert baseline.unavailability_reason_codes == (
        "selection_already_placed_in_section",
    )
    assert "later_work" in guidance.actionable_section_ids


def test_arrangement_pointer_conflict_removes_consequential_target() -> None:
    _, profile, candidate, requirements = _fixture_context()
    pointers = (
        SectionArrangementPointerRevision(
            arrangement_pointer_id="pointer_later_a",
            pointer_revision=1,
            portfolio_id=candidate.portfolio_id,
            profile_binding_id=candidate.profile_binding_id,
            section_id="later_work",
            arrangement_id="arrangement_later_a",
            pointed_at=NOW,
            pointed_by=TEACHER,
            authority_reference="issue97_test",
        ),
        SectionArrangementPointerRevision(
            arrangement_pointer_id="pointer_later_b",
            pointer_revision=1,
            portfolio_id=candidate.portfolio_id,
            profile_binding_id=candidate.profile_binding_id,
            section_id="later_work",
            arrangement_id="arrangement_later_b",
            pointed_at=NOW,
            pointed_by=TEACHER,
            authority_reference="issue97_test",
        ),
    )
    curation = project_curation_state((profile, candidate, *requirements, *pointers))

    guidance = project_selection_placement_guidance(
        candidate=candidate,
        profile=profile,
        curation=curation,
        operation="fresh_selection",
    )

    later = _section(guidance, "later_work")
    assert later.arrangement_pointer_state == "conflict"
    assert later.arrangement_pointer_revision is None
    assert later.current_actionable is False
    assert "arrangement_pointer_conflict" in later.unavailability_reason_codes


def test_replacement_capacity_releases_predecessor_placement_before_projection(
) -> None:
    graph, profile, candidate, requirements = _fixture_context()
    predecessor_candidate = candidate
    successor = replace(
        graph.candidates[1],
        eligible_profile_rule_ids=("baseline_cardinality",),
        eligible_section_ids=("baseline",),
    )
    selection = graph.selections[0]
    placement = graph.placements[0]
    curation = project_curation_state(
        (
            profile,
            predecessor_candidate,
            successor,
            *requirements,
            selection,
            _activated_selection(selection.selection_id),
            placement,
            _activated_placement(placement.placement_id),
        )
    )

    guidance = project_selection_placement_guidance(
        candidate=successor,
        profile=profile,
        curation=curation,
        operation="replacement",
        selection_id=selection.selection_id,
        releasing_placement_ids=(placement.placement_id,),
    )

    baseline = _section(guidance, "baseline")
    assert baseline.minimum_placements == 1
    assert baseline.active_placement_count == 1
    assert baseline.released_placement_count == 1
    assert baseline.effective_placement_count == 0
    assert baseline.remaining_capacity == 1
    assert baseline.current_actionable is True
    assert guidance.actionable_section_ids == ("baseline",)


def test_replacement_does_not_free_capacity_owned_by_another_selection() -> None:
    graph, profile, candidate, requirements = _fixture_context()
    predecessor_selection = graph.selections[1]
    predecessor_placement = graph.placements[1]
    occupying_placement = graph.placements[0]
    successor = replace(
        candidate,
        candidate_id="candidate_successor",
        candidate_evaluation_id="evaluation_successor",
        eligible_profile_rule_ids=("baseline_cardinality",),
        eligible_section_ids=("baseline",),
    )
    curation = project_curation_state(
        (
            profile,
            graph.candidates[1],
            successor,
            *requirements,
            predecessor_selection,
            _activated_selection(predecessor_selection.selection_id),
            predecessor_placement,
            _activated_placement(predecessor_placement.placement_id),
            occupying_placement,
            _activated_placement(occupying_placement.placement_id),
        )
    )

    guidance = project_selection_placement_guidance(
        candidate=successor,
        profile=profile,
        curation=curation,
        operation="replacement",
        selection_id=predecessor_selection.selection_id,
        releasing_placement_ids=(predecessor_placement.placement_id,),
    )

    baseline = _section(guidance, "baseline")
    assert baseline.minimum_placements == 1
    assert baseline.active_placement_count == 1
    assert baseline.released_placement_count == 0
    assert baseline.remaining_capacity == 0
    assert baseline.current_actionable is False
    assert "section_full" in baseline.unavailability_reason_codes
