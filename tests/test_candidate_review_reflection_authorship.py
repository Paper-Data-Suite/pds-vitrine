from __future__ import annotations

from pathlib import Path

import pytest

from scripts.candidate_fixture_support import (
    CLASS_ID,
    NOW,
    SCHOOL_YEAR,
    STUDENT_ID,
)
from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
)
from vitrine.candidate_review import (
    CandidateReviewError,
    execute_typed_reflection_action,
    list_reflection_student_author_choices,
    plan_reflection_creation,
)
from vitrine.models import (
    ClassQualifiedStudentRef,
    CurationTargetRef,
    PortfolioReflection,
    PortfolioSubjectClassLink,
    ReflectionManualEntryProvenance,
)
from vitrine.storage import commit_record_batch


def _entry_id(candidate_id: str) -> str:
    return f"candidate:{candidate_id}"


def _candidate(setup):
    return next(iter(setup.candidate_records_by_source.values()))


def test_reflection_plan_carries_forward_one_exact_current_student_link(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate(setup)
    entry_id = _entry_id(candidate.candidate_id)

    choices = list_reflection_student_author_choices(
        setup.workspace,
        entry_id,
    )
    assert len(choices) == 1

    plan = plan_reflection_creation(
        setup.workspace,
        entry_id=entry_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="typed_prompt",
        prompt_version="1",
        prompt_snapshot="Describe what you notice.",
        target_scope="portfolio",
        target_references=(
            CurationTargetRef(
                target_kind="portfolio",
                target_id=setup.portfolio_id,
            ),
        ),
        content="Student text.",
    )

    assert plan.subject_link_id == choices[0].subject_link_id
    assert plan.student_reference == choices[0].student_reference
    assert plan.student_reference is not None
    assert plan.student_reference.student_id == STUDENT_ID


def test_multiple_current_links_require_explicit_teacher_choice(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate(setup)
    second = PortfolioSubjectClassLink(
        subject_link_id="subject_link_candidate_fixture_second",
        portfolio_subject_id=setup.candidate_setup.portfolio_subject_id,
        student_reference=ClassQualifiedStudentRef(
            class_id="english10_p9",
            student_id=STUDENT_ID,
            school_year=SCHOOL_YEAR,
        ),
        confirmed_at=NOW,
        confirmed_by=ACTOR,
        confirmation_basis="teacher_confirmed",
        authority_reference="fixture_second_roster",
    )
    commit_record_batch(
        setup.workspace,
        (second,),
        expected_state_revision=setup.state_revision,
    )
    entry_id = _entry_id(candidate.candidate_id)

    choices = list_reflection_student_author_choices(
        setup.workspace,
        entry_id,
    )
    assert len(choices) == 2

    with pytest.raises(CandidateReviewError, match="subject link"):
        plan_reflection_creation(
            setup.workspace,
            entry_id=entry_id,
            reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
            prompt_id="typed_prompt",
            prompt_version="1",
            prompt_snapshot="Describe what you notice.",
            target_scope="portfolio",
            target_references=(
                CurationTargetRef(
                    target_kind="portfolio",
                    target_id=setup.portfolio_id,
                ),
            ),
            content="Student text.",
        )

    plan = plan_reflection_creation(
        setup.workspace,
        entry_id=entry_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="typed_prompt",
        prompt_version="1",
        prompt_snapshot="Describe what you notice.",
        target_scope="portfolio",
        target_references=(
            CurationTargetRef(
                target_kind="portfolio",
                target_id=setup.portfolio_id,
            ),
        ),
        content="Student text.",
        subject_link_id=second.subject_link_id,
    )
    assert plan.subject_link_id == second.subject_link_id
    assert plan.student_reference == second.student_reference


def test_guided_typed_executor_uses_adult_as_recorder_not_author(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    candidate = _candidate(setup)
    plan = plan_reflection_creation(
        setup.workspace,
        entry_id=_entry_id(candidate.candidate_id),
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="typed_prompt",
        prompt_version="1",
        prompt_snapshot="Describe what you notice.",
        target_scope="portfolio",
        target_references=(
            CurationTargetRef(
                target_kind="portfolio",
                target_id=setup.portfolio_id,
            ),
        ),
        content="Student-provided typed fallback.",
    )

    result = execute_typed_reflection_action(
        setup.workspace,
        plan,
        recorded_by=ACTOR,
        authority_gate=StaticCurationAuthorityGate(),
    )

    reflection = next(
        item for item in result.records if isinstance(item, PortfolioReflection)
    )
    provenance = next(
        item
        for item in result.records
        if isinstance(item, ReflectionManualEntryProvenance)
    )
    assert reflection.author.actor_kind == "core_student"
    assert reflection.author.actor_id == STUDENT_ID
    assert provenance.recorded_by == ACTOR
    assert provenance.student_reference.class_id == CLASS_ID
