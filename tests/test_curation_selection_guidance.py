from __future__ import annotations

from pathlib import Path

import pytest

from scripts.curation_fixture_support import (
    ACTOR,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.curation_services import (
    CurationWorkflowError,
    place_selection,
    propose_candidate_selection,
    reject_candidate_directly,
    select_candidate_directly,
)
from vitrine.models import PortfolioSelection
from vitrine.storage import load_current_state


def _write_fresh_intent(
    operation: str,
    *,
    setup: object,
    candidate_id: str,
    section_ids: tuple[str, ...],
    requirement_ids: tuple[str, ...] = (),
) -> object:
    workspace = getattr(setup, "workspace")
    portfolio_id = getattr(setup, "portfolio_id")
    revision = load_current_state(workspace).state_revision
    gate = StaticCurationAuthorityGate()
    ids = getattr(setup, "ids")
    common = dict(
        workspace_root=workspace,
        portfolio_id=portfolio_id,
        candidate_id=candidate_id,
        proposed_section_ids=section_ids,
        intended_profile_requirement_ids=requirement_ids,
        expected_state_revision=revision,
        authority_gate=gate,
        clock=fixed_clock,
        id_factory=ids,
    )
    if operation == "proposal":
        return propose_candidate_selection(
            **common,
            proposer=ACTOR,
            proposal_origin="teacher",
        )
    if operation == "direct_selection":
        return select_candidate_directly(
            **common,
            selected_by=ACTOR,
        )
    if operation == "direct_decline":
        return reject_candidate_directly(
            **common,
            rejected_by=ACTOR,
        )
    raise AssertionError(f"unknown operation: {operation}")


@pytest.mark.parametrize(
    "operation",
    ("proposal", "direct_selection", "direct_decline"),
)
def test_fresh_write_boundaries_reject_requirement_from_other_section(
    tmp_path: Path,
    operation: str,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = next(
        item
        for item in setup.candidate_records_by_source.values()
        if {"baseline", "later_work"}.issubset(item.eligible_section_ids)
        and "later_work_section_rule" in item.eligible_profile_rule_ids
    )
    before = setup.state_revision

    with pytest.raises(CurationWorkflowError) as error:
        _write_fresh_intent(
            operation,
            setup=setup,
            candidate_id=candidate.candidate_id,
            section_ids=("baseline",),
            requirement_ids=("later_work_section_rule",),
        )

    assert error.value.code == "curation.profile_mismatch"
    assert setup.state_revision == before


@pytest.mark.parametrize(
    "operation",
    ("proposal", "direct_selection", "direct_decline"),
)
def test_fresh_write_boundaries_reject_semantically_eligible_full_section(
    tmp_path: Path,
    operation: str,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    baseline_candidates = tuple(
        item
        for item in setup.candidate_records_by_source.values()
        if "baseline" in item.eligible_section_ids
    )
    assert len(baseline_candidates) >= 2
    occupying_candidate, candidate = baseline_candidates[:2]

    selected = select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=occupying_candidate.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=("baseline",),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    selection = next(
        item for item in selected.records if isinstance(item, PortfolioSelection)
    )
    place_selection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        selection_id=selection.selection_id,
        section_id="baseline",
        placed_by=ACTOR,
        expected_state_revision=setup.state_revision,
        expected_arrangement_pointer_revision=None,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    before = setup.state_revision

    with pytest.raises(CurationWorkflowError) as error:
        _write_fresh_intent(
            operation,
            setup=setup,
            candidate_id=candidate.candidate_id,
            section_ids=("baseline",),
        )

    assert error.value.code == "curation.section_cardinality_exceeded"
    assert setup.state_revision == before


def test_fresh_write_boundary_preserves_valid_exact_section_requirement(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = next(
        item
        for item in setup.candidate_records_by_source.values()
        if "baseline" in item.eligible_section_ids
        and "baseline_section_rule" in item.eligible_profile_rule_ids
    )

    result = _write_fresh_intent(
        "proposal",
        setup=setup,
        candidate_id=candidate.candidate_id,
        section_ids=("baseline",),
        requirement_ids=("baseline_section_rule",),
    )

    assert getattr(result, "state_revision") == setup.state_revision
    assert getattr(result, "records")
