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
from vitrine.manual_reflection_services import (
    create_typed_reflection,
    revise_typed_reflection,
)
from vitrine.models import (
    CurationTargetRef,
    PortfolioReflection,
    ReflectionManualEntryProvenance,
)
from vitrine.storage import load_current_records


def _subject_link_id() -> str:
    return "subject_link_candidate_fixture"


def test_typed_fallback_separates_student_author_from_adult_recorder(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    gate = StaticCurationAuthorityGate()
    target = CurationTargetRef(
        target_kind="portfolio",
        target_id=setup.portfolio_id,
    )

    result = create_typed_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="typed_fallback_prompt",
        prompt_version="1",
        prompt_snapshot="Describe what you notice in the selected work.",
        subject_link_id=_subject_link_id(),
        recorded_by=ACTOR,
        target_scope="portfolio",
        target_references=(target,),
        content="Student-provided reflection text entered by the teacher.",
        expected_state_revision=setup.state_revision,
        authority_gate=gate,
        clock=fixed_clock,
        id_factory=setup.ids,
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
    assert reflection.author.actor_id == provenance.student_reference.student_id
    assert reflection.author != ACTOR
    assert reflection.content_mode == "inline_text"
    assert provenance.subject_link_id == _subject_link_id()
    assert provenance.recorded_by == ACTOR
    assert provenance.entry_mode == "typed_by_authorized_adult"
    assert provenance.authority_reference == "fixture_curation_authority"
    assert gate.requests[-1].actor == ACTOR


def test_typed_fallback_rejects_student_as_recorder(tmp_path: Path) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    target = CurationTargetRef(
        target_kind="portfolio",
        target_id=setup.portfolio_id,
    )

    with pytest.raises(CurationWorkflowError, match="authorized_adult"):
        create_typed_reflection(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
            prompt_id="typed_fallback_prompt",
            prompt_version="1",
            prompt_snapshot="Describe what you notice.",
            subject_link_id=_subject_link_id(),
            recorded_by=STUDENT_ACTOR,
            target_scope="portfolio",
            target_references=(target,),
            content="Student text.",
            expected_state_revision=setup.state_revision,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )


def test_typed_revision_preserves_student_author_prompt_and_targets(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    target = CurationTargetRef(
        target_kind="portfolio",
        target_id=setup.portfolio_id,
    )
    created = create_typed_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="typed_fallback_prompt",
        prompt_version="1",
        prompt_snapshot="Describe what you notice.",
        subject_link_id=_subject_link_id(),
        recorded_by=ACTOR,
        target_scope="portfolio",
        target_references=(target,),
        content="First version.",
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    first = next(
        item for item in created.records if isinstance(item, PortfolioReflection)
    )

    revised = revise_typed_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_id=first.reflection_id,
        expected_reflection_revision=1,
        subject_link_id=_subject_link_id(),
        recorded_by=ACTOR,
        content="Revised student-provided text.",
        expected_state_revision=created.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    second = next(
        item for item in revised.records if isinstance(item, PortfolioReflection)
    )
    provenance = next(
        item
        for item in revised.records
        if isinstance(item, ReflectionManualEntryProvenance)
    )

    assert second.reflection_revision == 2
    assert second.predecessor_reflection_revision == 1
    assert second.author == first.author
    assert second.prompt_id == first.prompt_id
    assert second.prompt_version == first.prompt_version
    assert second.prompt_snapshot == first.prompt_snapshot
    assert second.target_scope == first.target_scope
    assert second.target_references == first.target_references
    assert provenance.reflection_revision == 2
    assert provenance.recorded_by == ACTOR

    provenance_records = tuple(
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, ReflectionManualEntryProvenance)
    )
    assert len(provenance_records) == 2
