from __future__ import annotations

from pathlib import Path

import pytest

from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    STUDENT_ACTOR,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.curation_services import CurationWorkflowError
from vitrine.identity_state import project_identity_state
from vitrine.models import (
    ClassQualifiedStudentRef,
    CurationTargetRef,
    Portfolio,
    PortfolioSubjectClassLink,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
)
from vitrine.paper_reflection_services import prepare_reflection_issuance
from vitrine.storage import commit_record_batch, load_current_records


def _portfolio_target(portfolio_id: str) -> tuple[CurationTargetRef, ...]:
    return (
        CurationTargetRef(
            target_kind="portfolio",
            target_id=portfolio_id,
        ),
    )


def _current_subject_links(workspace: Path, portfolio_id: str):
    records = load_current_records(workspace)
    portfolio = next(
        item
        for item in records
        if isinstance(item, Portfolio) and item.portfolio_id == portfolio_id
    )
    return project_identity_state(records).current_links(
        portfolio.portfolio_subject_id
    )


def test_prepare_reflection_issuance_freezes_exact_context_and_pages(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    links = _current_subject_links(setup.workspace, setup.portfolio_id)
    assert len(links) == 1
    gate = StaticCurationAuthorityGate()

    result = prepare_reflection_issuance(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_compare",
        prompt_version="1",
        prompt_snapshot="Compare the two curated works. What changed?",
        target_scope="portfolio",
        target_references=_portfolio_target(setup.portfolio_id),
        issued_by=ACTOR,
        page_count=2,
        expected_state_revision=setup.state_revision,
        authority_gate=gate,
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    issuance = next(
        item for item in result.records if isinstance(item, ReflectionPromptIssuance)
    )
    pages = tuple(
        item for item in result.records if isinstance(item, ReflectionResponsePage)
    )
    assert issuance.subject_link_id == links[0].subject_link_id
    assert issuance.student_reference == links[0].student_reference
    assert issuance.reflection_requirement_id == REFLECTION_REQUIREMENT_ID
    assert issuance.prompt_snapshot == "Compare the two curated works. What changed?"
    assert issuance.target_references == _portfolio_target(setup.portfolio_id)
    assert len(pages) == 2
    assert issuance.response_page_ids == tuple(item.response_page_id for item in pages)
    assert tuple(item.logical_page_number for item in pages) == (1, 2)
    assert {item.total_pages for item in pages} == {2}
    assert len({item.work_id for item in pages}) == 1
    assert len({item.route_id for item in pages}) == 2
    assert {item.class_id for item in pages} == {
        links[0].student_reference.class_id
    }
    assert len(gate.requests) == 1
    assert gate.requests[0].actor == ACTOR
    assert gate.requests[0].profile_requirement_ids == (
        REFLECTION_REQUIREMENT_ID,
    )

    persisted = load_current_records(setup.workspace)
    assert issuance in persisted
    assert all(page in persisted for page in pages)


def test_prepare_reflection_issuance_requires_explicit_link_when_subject_has_multiple(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    original = _current_subject_links(setup.workspace, setup.portfolio_id)
    assert len(original) == 1
    extra_reference = ClassQualifiedStudentRef(
        school_year=original[0].student_reference.school_year,
        class_id="class_reflection_other",
        student_id="student_reflection_other",
    )
    extra = PortfolioSubjectClassLink(
        subject_link_id="link_reflection_other",
        portfolio_subject_id=original[0].portfolio_subject_id,
        student_reference=extra_reference,
        confirmed_at=fixed_clock(),
        confirmed_by=ACTOR,
        confirmation_basis="teacher_confirmed",
        authority_reference="fixture_curation_authority",
    )
    commit_record_batch(
        setup.workspace,
        (extra,),
        expected_state_revision=setup.state_revision,
    )
    assert len(_current_subject_links(setup.workspace, setup.portfolio_id)) == 2

    with pytest.raises(CurationWorkflowError) as exc:
        prepare_reflection_issuance(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
            prompt_id="growth_compare",
            prompt_version="1",
            prompt_snapshot="Compare the curated works.",
            target_scope="portfolio",
            target_references=_portfolio_target(setup.portfolio_id),
            issued_by=ACTOR,
            page_count=1,
            expected_state_revision=setup.state_revision,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert exc.value.code == "curation.reflection_author_unresolved"
    assert "exact subject_link_id is required" in str(exc.value)


def test_prepare_reflection_issuance_accepts_explicit_current_link_when_multiple(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    original = _current_subject_links(setup.workspace, setup.portfolio_id)
    assert len(original) == 1
    extra = PortfolioSubjectClassLink(
        subject_link_id="link_reflection_other",
        portfolio_subject_id=original[0].portfolio_subject_id,
        student_reference=ClassQualifiedStudentRef(
            school_year=original[0].student_reference.school_year,
            class_id="class_reflection_other",
            student_id="student_reflection_other",
        ),
        confirmed_at=fixed_clock(),
        confirmed_by=ACTOR,
        confirmation_basis="teacher_confirmed",
        authority_reference="fixture_curation_authority",
    )
    commit_record_batch(
        setup.workspace,
        (extra,),
        expected_state_revision=setup.state_revision,
    )

    result = prepare_reflection_issuance(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_compare",
        prompt_version="1",
        prompt_snapshot="Compare the curated works.",
        target_scope="portfolio",
        target_references=_portfolio_target(setup.portfolio_id),
        issued_by=ACTOR,
        page_count=1,
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        subject_link_id=original[0].subject_link_id,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    issuance = next(
        item for item in result.records if isinstance(item, ReflectionPromptIssuance)
    )
    assert issuance.subject_link_id == original[0].subject_link_id
    assert issuance.student_reference == original[0].student_reference


def test_prepare_reflection_issuance_rejects_noncurrent_explicit_link(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)

    with pytest.raises(CurationWorkflowError) as exc:
        prepare_reflection_issuance(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
            prompt_id="growth_compare",
            prompt_version="1",
            prompt_snapshot="Compare the curated works.",
            target_scope="portfolio",
            target_references=_portfolio_target(setup.portfolio_id),
            issued_by=ACTOR,
            page_count=1,
            expected_state_revision=setup.state_revision,
            authority_gate=StaticCurationAuthorityGate(),
            subject_link_id="link_not_current",
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert exc.value.code == "curation.reflection_author_unresolved"


def test_prepare_reflection_issuance_separates_student_from_adult_issuer(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)

    with pytest.raises(CurationWorkflowError) as exc:
        prepare_reflection_issuance(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
            prompt_id="growth_compare",
            prompt_version="1",
            prompt_snapshot="Compare the curated works.",
            target_scope="portfolio",
            target_references=_portfolio_target(setup.portfolio_id),
            issued_by=STUDENT_ACTOR,
            page_count=1,
            expected_state_revision=setup.state_revision,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert exc.value.code == "curation.invalid_request"
    assert "authorized-adult issuer" in str(exc.value)


def test_prepare_reflection_issuance_rejects_nonpositive_page_count(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)

    with pytest.raises(CurationWorkflowError) as exc:
        prepare_reflection_issuance(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
            prompt_id="growth_compare",
            prompt_version="1",
            prompt_snapshot="Compare the curated works.",
            target_scope="portfolio",
            target_references=_portfolio_target(setup.portfolio_id),
            issued_by=ACTOR,
            page_count=0,
            expected_state_revision=setup.state_revision,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )
    assert exc.value.code == "curation.invalid_request"
