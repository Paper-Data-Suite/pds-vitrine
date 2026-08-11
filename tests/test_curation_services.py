from __future__ import annotations

from pathlib import Path

import pytest
from pds_core.registry_services import (
    PublicationWithdrawalRequest,
    withdraw_publication,
)

from scripts.curation_fixture_support import (
    ACTOR,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.curation_services import CurationWorkflowError, select_candidate_directly
from vitrine.curation_state import project_curation_state
from vitrine.storage import load_current_records


def test_withdrawn_candidate_source_blocks_new_selection_without_retargeting_history(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    first = setup.candidate("evidence_selected")
    second = setup.candidate("evidence_approved")
    selected = select_candidate_directly(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        candidate_id=first.candidate_id,
        selected_by=ACTOR,
        proposed_section_ids=("baseline",),
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    selection_id = next(
        item.selection_id
        for item in selected.records
        if getattr(item, "record_type", "") == "portfolio_selection"
    )
    publication_id = first.source_endpoint.core_publication.publication_id
    withdraw_publication(
        setup.workspace,
        PublicationWithdrawalRequest(
            publication_id=publication_id,
            reason="Synthetic source withdrawal after curation.",
        ),
    )
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
    assert exc.value.code == "curation.candidate_source_withdrawn"
    state = project_curation_state(load_current_records(setup.workspace))
    assert state.selection_status(selection_id) == "activated"
