from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.improvement_portfolio_fixture_support import (
    PROFILE_BINDING_ID,
    STUDENT,
    ImprovementPortfolioFixture,
    build_improvement_portfolio_fixture,
)
from vitrine.curation_state import project_curation_state
from vitrine.models import (
    PortfolioProfileBinding,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileRevision,
    PortfolioSelection,
    PortfolioSubjectDisplaySnapshot,
    PortfolioSubjectIdentityDecision,
)
from vitrine.storage import load_current_records


@pytest.fixture(scope="module")
def improvement_setup(tmp_path_factory: pytest.TempPathFactory) -> Iterator[ImprovementPortfolioFixture]:
    result = build_improvement_portfolio_fixture(
        tmp_path_factory.mktemp("improvement-portfolio-runtime")
    )
    assert isinstance(result, ImprovementPortfolioFixture)
    yield result


def test_subject_and_profile_application_services_preserve_required_history(
    improvement_setup: ImprovementPortfolioFixture,
) -> None:
    records = load_current_records(improvement_setup.workspace)
    displays = tuple(
        item for item in records if isinstance(item, PortfolioSubjectDisplaySnapshot)
    )
    decisions = tuple(
        item for item in records if isinstance(item, PortfolioSubjectIdentityDecision)
    )
    lifecycle = tuple(
        item for item in records if isinstance(item, PortfolioProfileLifecycleEvent)
    )
    bindings = tuple(
        item for item in records if isinstance(item, PortfolioProfileBinding)
    )
    profiles = tuple(
        item
        for item in records
        if isinstance(item, PortfolioProfileRevision)
        and item.reference == improvement_setup.composition.profile_revision
    )

    assert len(displays) == 2
    assert sorted(item.decision_type for item in decisions) == [
        "confirm_link",
        "confirm_link",
        "create_subject",
    ]
    assert len(lifecycle) == 1
    assert lifecycle[0].event_kind == "activated"
    assert len(bindings) == 1
    assert bindings[0].profile_binding_id == PROFILE_BINDING_ID
    assert len(profiles) == 1
    assert tuple(item.section_id for item in profiles[0].sections) == (
        "baseline",
        "later_work",
        "reflection",
    )
    reflection_section = profiles[0].sections[2]
    assert reflection_section.reflection_requirement == "required"
    assert reflection_section.minimum_placements == 0
    assert reflection_section.maximum_placements == 0


def test_exact_candidates_require_explicit_selections_and_arrangements(
    improvement_setup: ImprovementPortfolioFixture,
) -> None:
    setup = improvement_setup
    source_ids = {
        item.source_endpoint.producer_source.source_record_id for item in setup.candidates
    }
    assert source_ids == {"baseline_argument", "revised_argument", "revised_feedback"}
    assert len(setup.evaluations) == len(setup.candidates) == 3
    assert len(setup.proposals) == len(setup.decisions) == len(setup.selections) == 3
    assert setup.candidate("revised_feedback").candidate_id not in {
        setup.candidate("baseline_argument").candidate_id,
        setup.candidate("revised_argument").candidate_id,
    }
    state = project_curation_state(load_current_records(setup.workspace))
    later = state.current_arrangement(setup.composition.portfolio_id, PROFILE_BINDING_ID, "later_work")
    assert later is not None
    assert later.placement_ids == (
        setup.placement("revised_argument").placement_id,
        setup.placement("revised_feedback").placement_id,
    )


def test_reflection_and_composition_freeze_exact_student_comparison(
    improvement_setup: ImprovementPortfolioFixture,
) -> None:
    setup = improvement_setup
    assert setup.reflection.author == STUDENT
    assert tuple(item.semantic_role for item in setup.reflection.target_references) == (
        "baseline",
        "later",
    )
    assert tuple(item.target_id for item in setup.reflection.target_references) == (
        setup.selection("baseline_argument").selection_id,
        setup.selection("revised_argument").selection_id,
    )
    assert any(
        item.record_kind == "reflection"
        and item.record_id == setup.reflection.reflection_id
        and item.revision == setup.reflection.reflection_revision
        for item in setup.inventory.included_curation_revisions
    )
    assert setup.composition.selection_ids == tuple(
        item.selection_id for item in setup.selections
    )


def test_unlinked_same_looking_student_does_not_resolve_and_discovery_does_not_select(
    tmp_path: Path,
) -> None:
    result = build_improvement_portfolio_fixture(
        tmp_path,
        include_later_link=False,
        complete_curation=False,
    )
    assert not isinstance(result, ImprovementPortfolioFixture)
    workspace, evaluations, candidates = result
    assert len(evaluations) == 3
    assert tuple(
        item.source_endpoint.producer_source.source_record_id for item in candidates
    ) == ("baseline_argument",)
    assert not any(
        isinstance(item, PortfolioSelection) for item in load_current_records(workspace)
    )

