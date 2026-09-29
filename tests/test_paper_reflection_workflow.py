from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.models import (
    CurationTargetRef,
    PortfolioReflection,
    ReflectionAuthorshipConfirmation,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
    ReflectionReturnedPaperEvidence,
)
from vitrine.paper_reflection_authorship import (
    confirm_returned_paper_authorship,
    finalize_confirmed_paper_reflection,
)
from vitrine.paper_reflection_services import prepare_reflection_issuance
from vitrine.paper_reflection_workflow import (
    build_paper_reflection_workflow_view,
)
from vitrine.storage import commit_record_batch

INTAKE = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)


def _issue(setup):
    result = prepare_reflection_issuance(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_compare",
        prompt_version="1",
        prompt_snapshot="Compare the selected work. What do you notice?",
        target_scope="portfolio",
        target_references=(
            CurationTargetRef(
                target_kind="portfolio",
                target_id=setup.portfolio_id,
            ),
        ),
        issued_by=ACTOR,
        page_count=1,
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    issuance = next(
        item
        for item in result.records
        if isinstance(item, ReflectionPromptIssuance)
    )
    page = next(
        item
        for item in result.records
        if isinstance(item, ReflectionResponsePage)
    )
    return result, issuance, page


def test_workflow_projects_not_issued_then_awaiting_return(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)

    initial = build_paper_reflection_workflow_view(
        setup.workspace,
        setup.portfolio_id,
    )
    assert len(initial.requirements) == 1
    assert initial.requirements[0].requirement_id == REFLECTION_REQUIREMENT_ID
    assert initial.requirements[0].status == "not_issued"

    _result, issuance, _page = _issue(setup)
    awaiting = build_paper_reflection_workflow_view(
        setup.workspace,
        setup.portfolio_id,
    )
    item = awaiting.requirements[0]
    assert item.status == "issued_awaiting_return"
    assert item.issuance_id == issuance.issuance_id
    assert item.prompt_snapshot == issuance.prompt_snapshot
    assert item.target_count == 1
    assert item.issued_page_count == 1
    assert item.returned_page_count == 0


def test_workflow_projects_return_review_confirmation_and_recording(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    issued, issuance, page = _issue(setup)
    evidence = ReflectionReturnedPaperEvidence(
        returned_paper_evidence_id="paper_evidence_projection",
        issuance_id=issuance.issuance_id,
        response_page_id=page.response_page_id,
        route_id=page.route_id,
        class_id=page.class_id,
        work_id=page.work_id,
        source_scan_id="scan_projection",
        source_filename="reflection.png",
        source_page_number=1,
        retained_source_relative_path=(
            "scans/source/2026-09-26/reflection_projection.png"
        ),
        source_sha256="0" * 64,
        intake_timestamp=INTAKE,
        intake_date=INTAKE.date(),
    )
    returned_state = commit_record_batch(
        setup.workspace,
        (evidence,),
        expected_state_revision=issued.state_revision,
    )

    returned = build_paper_reflection_workflow_view(
        setup.workspace,
        setup.portfolio_id,
    ).requirements[0]
    assert returned.status == "returned_needs_review"
    assert returned.returned_page_count == 1
    assert returned.returned_occurrence_count == 1

    confirmed_result = confirm_returned_paper_authorship(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        issuance_id=issuance.issuance_id,
        returned_paper_evidence_ids=(evidence.returned_paper_evidence_id,),
        confirmed_by=ACTOR,
        expected_state_revision=returned_state.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    confirmation = next(
        item
        for item in confirmed_result.records
        if isinstance(item, ReflectionAuthorshipConfirmation)
    )
    confirmed = build_paper_reflection_workflow_view(
        setup.workspace,
        setup.portfolio_id,
    ).requirements[0]
    assert confirmed.status == "confirmed_needs_recording"
    assert confirmed.authorship_confirmation_id == (
        confirmation.authorship_confirmation_id
    )

    finalized = finalize_confirmed_paper_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        authorship_confirmation_id=confirmation.authorship_confirmation_id,
        recorded_by=ACTOR,
        expected_state_revision=confirmed_result.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    reflection = next(
        item
        for item in finalized.records
        if isinstance(item, PortfolioReflection)
    )
    recorded = build_paper_reflection_workflow_view(
        setup.workspace,
        setup.portfolio_id,
    ).requirements[0]
    assert recorded.status == "recorded"
    assert recorded.reflection_id == reflection.reflection_id
    assert recorded.reflection_revision == reflection.reflection_revision
    assert recorded.paper_finalization_id is not None


def test_workflow_marks_rescan_choice_without_guessing(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    issued, issuance, page = _issue(setup)
    evidence = tuple(
        ReflectionReturnedPaperEvidence(
            returned_paper_evidence_id=f"paper_evidence_rescan_{index}",
            issuance_id=issuance.issuance_id,
            response_page_id=page.response_page_id,
            route_id=page.route_id,
            class_id=page.class_id,
            work_id=page.work_id,
            source_scan_id=f"scan_rescan_{index}",
            source_filename=f"reflection-{index}.png",
            source_page_number=1,
            retained_source_relative_path=(
                f"scans/source/2026-09-26/reflection-rescan-{index}.png"
            ),
            source_sha256=str(index) * 64,
            intake_timestamp=INTAKE,
            intake_date=INTAKE.date(),
        )
        for index in (1, 2)
    )
    commit_record_batch(
        setup.workspace,
        evidence,
        expected_state_revision=issued.state_revision,
    )

    item = build_paper_reflection_workflow_view(
        setup.workspace,
        setup.portfolio_id,
    ).requirements[0]
    assert item.status == "returned_needs_review"
    assert item.returned_page_count == 1
    assert item.returned_occurrence_count == 2
    assert item.rescan_choice_required is True
