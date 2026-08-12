from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from scripts.curation_fixture_support import (
    ACTOR,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.curation_services import select_candidate_directly
from vitrine.curation_state import collect_curation_state_issues, project_curation_state
from vitrine.models import SelectionLifecycleEvent
from vitrine.storage import load_current_records


def test_curation_state_detects_selection_lifecycle_branch(tmp_path: Path) -> None:
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
    activation = next(
        item for item in result.records if isinstance(item, SelectionLifecycleEvent)
    )
    first = replace(
        activation,
        selection_lifecycle_event_id="selection_event_branch_a",
        event_kind="withdrawn",
        predecessor_event_id=activation.selection_lifecycle_event_id,
        basis_selection_decision_id=None,
        reason="First terminal branch.",
    )
    second = replace(
        activation,
        selection_lifecycle_event_id="selection_event_branch_b",
        event_kind="invalidated",
        predecessor_event_id=activation.selection_lifecycle_event_id,
        basis_selection_decision_id=None,
        reason="Second terminal branch.",
    )
    records = (*load_current_records(setup.workspace), first, second)
    codes = {
        item.code
        for item in collect_curation_state_issues(project_curation_state(records))
    }
    assert "curation.selection_lifecycle_branch" in codes
    assert "curation.selection_lifecycle_conflict" in codes
