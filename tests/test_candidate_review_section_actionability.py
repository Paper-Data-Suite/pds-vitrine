from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from scripts.curation_fixture_support import (
    ACTOR,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine import candidate_review_menu
from vitrine.candidate_review import (
    get_candidate_review_detail,
    list_candidate_review_section_guidance,
)
from vitrine.curation_services import place_selection, select_candidate_directly
from vitrine.models import PortfolioCandidate, PortfolioPlacement, PortfolioSelection
from vitrine.storage import load_current_state

MAX_ONE_SECTIONS = (
    "baseline",
    "later_work",
    "feedback",
    "assessment",
    "collaborative",
)


def _shared_max_one_candidates(
    setup: object,
) -> tuple[str, PortfolioCandidate, PortfolioCandidate]:
    candidates = tuple(getattr(setup, "candidate_records_by_source").values())
    for section_id in MAX_ONE_SECTIONS:
        matches = tuple(
            candidate
            for candidate in candidates
            if section_id in candidate.eligible_section_ids
        )
        if len(matches) >= 2:
            return section_id, matches[0], matches[1]
    raise AssertionError("Fixture needs two Candidates sharing one max-one section.")


def _select(
    setup: object,
    candidate: PortfolioCandidate,
    section_id: str,
) -> PortfolioSelection:
    result = select_candidate_directly(
        getattr(setup, "workspace"),
        portfolio_id=getattr(setup, "portfolio_id"),
        candidate_id=candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=(section_id,),
        expected_state_revision=load_current_state(
            getattr(setup, "workspace")
        ).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=getattr(setup, "ids"),
    )
    return next(item for item in result.records if isinstance(item, PortfolioSelection))


def _place(
    setup: object,
    selection: PortfolioSelection,
    section_id: str,
) -> PortfolioPlacement:
    result = place_selection(
        getattr(setup, "workspace"),
        portfolio_id=getattr(setup, "portfolio_id"),
        selection_id=selection.selection_id,
        section_id=section_id,
        placed_by=ACTOR,
        expected_state_revision=load_current_state(
            getattr(setup, "workspace")
        ).state_revision,
        expected_arrangement_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=getattr(setup, "ids"),
    )
    return next(item for item in result.records if isinstance(item, PortfolioPlacement))


def test_detail_keeps_semantic_fit_but_marks_full_section_unavailable(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    section_id, blocker, candidate = _shared_max_one_candidates(setup)
    blocker_selection = _select(setup, blocker, section_id)
    _place(setup, blocker_selection, section_id)

    detail = get_candidate_review_detail(
        setup.workspace,
        f"candidate:{candidate.candidate_id}",
    )
    section = next(item for item in detail.sections if item.section_id == section_id)

    assert section.semantic_candidate_eligible is True
    assert section.placement_bearing is True
    assert section.actionability_operation == "fresh_selection"
    assert section.active_placement_count == 1
    assert section.maximum_placements == 1
    assert section.remaining_capacity == 0
    assert section.current_actionable is False
    assert section.unavailability_reason_codes == ("section_full",)
    assert section_id in detail.inbox_detail.item.eligible_section_ids


def test_replacement_projection_releases_predecessor_capacity_for_menu_choice(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    section_id, predecessor, successor = _shared_max_one_candidates(setup)
    predecessor_selection = _select(setup, predecessor, section_id)
    predecessor_placement = _place(setup, predecessor_selection, section_id)

    fresh_detail = get_candidate_review_detail(
        setup.workspace,
        f"candidate:{successor.candidate_id}",
    )
    fresh_section = next(
        item for item in fresh_detail.sections if item.section_id == section_id
    )
    assert fresh_section.current_actionable is False
    assert fresh_section.unavailability_reason_codes == ("section_full",)

    replacement = list_candidate_review_section_guidance(
        setup.workspace,
        f"candidate:{successor.candidate_id}",
        operation="replacement",
        selection_id=predecessor_selection.selection_id,
        releasing_placement_ids=(predecessor_placement.placement_id,),
    )
    replacement_section = next(
        item for item in replacement if item.section_id == section_id
    )

    assert replacement_section.actionability_operation == "replacement"
    assert replacement_section.current_actionable is True
    assert replacement_section.remaining_capacity == 1
    assert replacement_section.unavailability_reason_codes == ()


def _menu_section(
    section_id: str,
    label: str,
    *,
    actionable: bool,
    requirement_ids: tuple[str, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        section_id=section_id,
        label=label,
        obligation="optional",
        minimum_placements=0,
        maximum_placements=None if actionable else 0,
        active_placement_count=0,
        remaining_capacity=None if actionable else 0,
        semantic_candidate_eligible=True,
        placement_bearing=actionable,
        actionability_operation="fresh_selection",
        current_actionable=actionable,
        unavailability_reason_codes=(
            () if actionable else ("section_not_placement_bearing",)
        ),
        arrangement_pointer_state="absent",
        arrangement_pointer_revision=None,
        arrangement_pointer_conflict=False,
        relevant_profile_requirement_ids=requirement_ids,
    )


def test_fresh_menu_omits_max_zero_match_and_unrelated_requirements(
    tmp_path: Path,
    monkeypatch,
) -> None:
    baseline = _menu_section(
        "baseline",
        "Baseline",
        actionable=True,
        requirement_ids=("baseline_rule",),
    )
    reflection = _menu_section(
        "reflection",
        "Comparison Reflection",
        actionable=False,
        requirement_ids=(),
    )
    detail = SimpleNamespace(
        inbox_detail=SimpleNamespace(
            item=SimpleNamespace(
                entry_id="candidate:candidate_exact",
                portfolio_id="portfolio_exact",
            )
        ),
        sections=(baseline, reflection),
        profile_requirements=(
            SimpleNamespace(
                requirement_id="baseline_rule",
                requirement_kind="section",
                title="Baseline evidence",
            ),
            SimpleNamespace(
                requirement_id="reflection_rule",
                requirement_kind="reflection",
                title="Comparison reflection",
            ),
            SimpleNamespace(
                requirement_id="approval_rule",
                requirement_kind="approval",
                title="Teacher approval",
            ),
        ),
    )
    planned: list[dict[str, object]] = []

    def plan(_root: Path, **kwargs: object) -> object:
        planned.append(kwargs)
        return SimpleNamespace(
            portfolio_id="portfolio_exact",
            candidate_id="candidate_exact",
            current_review_evaluation_id="evaluation_current",
            curation_provenance_evaluation_id="evaluation_origin",
            candidate_condition="ready_for_consideration",
            stale_state="current",
            stale_reason_codes=(),
            decision="select",
            selection_proposal_id=None,
            proposed_section_ids=kwargs["proposed_section_ids"],
            intended_profile_requirement_ids=kwargs[
                "intended_profile_requirement_ids"
            ],
            condition_acknowledgement_required=False,
            confirmation_phrase="SELECT CANDIDATE",
            observed_state_revision=11,
        )

    monkeypatch.setattr(candidate_review_menu, "plan_candidate_decision", plan)
    monkeypatch.setattr(
        candidate_review_menu,
        "execute_candidate_decision",
        lambda *_args, **_kwargs: SimpleNamespace(state_revision=12),
    )
    values = iter(("1", "1", "", "SELECT CANDIDATE"))
    output = io.StringIO()

    candidate_review_menu._decision_flow(
        root=tmp_path,
        detail=detail,
        decision="select",
        selection_proposal_id=None,
        input_fn=lambda _prompt: next(values),
        output=output,
        clear_fn=lambda: None,
        dependencies=SimpleNamespace(
            curation_authority_gate=StaticCurationAuthorityGate()
        ),
        actor=ACTOR,
    )

    assert planned[0]["proposed_section_ids"] == ("baseline",)
    assert planned[0]["intended_profile_requirement_ids"] == ("baseline_rule",)
    rendered = output.getvalue()
    assert "Baseline" in rendered
    assert "Comparison Reflection" not in rendered
    assert "Teacher approval" not in rendered
