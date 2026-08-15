from __future__ import annotations

from pathlib import Path

import pytest
from subject_helpers import (
    DeterministicIds,
    fixed_clock,
    make_subject_workspace,
    teacher_context,
)

from vitrine.models import ClassQualifiedStudentRef
from vitrine.portfolio_services import (
    PortfolioWorkflowError,
    create_portfolio,
    list_portfolios,
    observe_portfolio_state_revision,
    show_portfolio,
)
from vitrine.subject_services import create_portfolio_subject, observe_state_revision


def _subject(workspace: Path) -> str:
    result = create_portfolio_subject(
        workspace,
        ClassQualifiedStudentRef(
            class_id="english10_p2", student_id="00107", school_year="2026-2027"
        ),
        context=teacher_context(),
        expected_state_revision=observe_state_revision(workspace),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    return result.subject_ids[0]


def test_create_list_and_show_portfolio_have_no_automatic_side_effects(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    subject_id = _subject(workspace)
    result = create_portfolio(
        workspace,
        portfolio_subject_id=subject_id,
        created_by=teacher_context().actor,
        expected_state_revision=observe_portfolio_state_revision(workspace),
        title_snapshot="Synthetic Showcase",
        clock=fixed_clock,
        id_factory=lambda prefix: f"{prefix}_opaque_001",
    )
    assert result.portfolio.portfolio_id == "portfolio_opaque_001"
    summary = list_portfolios(workspace)[0]
    assert show_portfolio(workspace, result.portfolio.portfolio_id).summary == summary
    assert summary.profile_binding_id is None
    assert summary.candidate_count == 0
    assert summary.active_selection_count == 0
    assert summary.snapshot_series_count == 0


def test_create_portfolio_rejects_unknown_subject_and_stale_state(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    subject_id = _subject(workspace)
    current = observe_portfolio_state_revision(workspace)
    with pytest.raises(PortfolioWorkflowError, match="not found") as unknown:
        create_portfolio(
            workspace,
            portfolio_subject_id="subject_unknown",
            created_by=teacher_context().actor,
            expected_state_revision=current,
        )
    assert unknown.value.code == "subject_not_found"

    create_portfolio(
        workspace,
        portfolio_subject_id=subject_id,
        created_by=teacher_context().actor,
        expected_state_revision=current,
    )
    with pytest.raises(PortfolioWorkflowError) as stale:
        create_portfolio(
            workspace,
            portfolio_subject_id=subject_id,
            created_by=teacher_context().actor,
            expected_state_revision=current,
        )
    assert stale.value.code == "state_conflict"
