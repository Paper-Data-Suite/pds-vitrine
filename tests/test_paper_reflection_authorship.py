from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.route_registrations import resolve_route_registration
from pds_core.scan_retention import retain_source_scan

from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    STUDENT_ACTOR,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.curation_services import CurationWorkflowError
from vitrine.models import (
    CurationTargetRef,
    PortfolioReflection,
    ReflectionAuthorshipConfirmation,
    ReflectionPaperFinalization,
    ReflectionPromptIssuance,
)
from vitrine.paper_reflection_authorship import (
    confirm_returned_paper_authorship,
    finalize_confirmed_paper_reflection,
)
from vitrine.paper_reflection_printing import (
    persist_reflection_print_route_registrations,
    prepare_reflection_print_plan,
)
from vitrine.paper_reflection_route_handler import (
    handle_vitrine_reflection_response_page_route,
)
from vitrine.paper_reflection_services import prepare_reflection_issuance
from vitrine.storage import load_current_records, load_current_state

INTAKE = datetime(2026, 9, 25, 18, 0, tzinfo=timezone.utc)


def _returned_paper(tmp_path: Path, *, pages: int = 1):
    setup = build_curation_fixture_workspace(tmp_path)
    issued = prepare_reflection_issuance(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_compare",
        prompt_version="1",
        prompt_snapshot="Compare the curated works without assuming improvement.",
        target_scope="portfolio",
        target_references=(
            CurationTargetRef(
                target_kind="portfolio",
                target_id=setup.portfolio_id,
            ),
        ),
        issued_by=ACTOR,
        page_count=pages,
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    issuance = next(
        item
        for item in issued.records
        if isinstance(item, ReflectionPromptIssuance)
    )
    plan = prepare_reflection_print_plan(
        setup.workspace,
        issuance_id=issuance.issuance_id,
        expected_state_revision=issued.state_revision,
    )
    persist_reflection_print_route_registrations(plan)

    evidences = []
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    for index, route in enumerate(plan.routes, start=1):
        source = incoming / f"student-reflection-{index}.png"
        source.write_bytes(f"handwritten page {index}".encode())
        retained = retain_source_scan(
            setup.workspace,
            source,
            intake_timestamp=INTAKE,
        )
        resolution = resolve_route_registration(
            setup.workspace,
            route.locator,
        )
        evidences.append(
            handle_vitrine_reflection_response_page_route(
                resolution,
                retained,
                1,
            )
        )
    return setup, issuance, tuple(evidences)


def test_confirmation_freezes_exact_student_link_and_selected_evidence(
    tmp_path: Path,
) -> None:
    setup, issuance, evidences = _returned_paper(tmp_path, pages=2)
    revision = load_current_state(setup.workspace).state_revision
    gate = StaticCurationAuthorityGate()

    result = confirm_returned_paper_authorship(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        issuance_id=issuance.issuance_id,
        returned_paper_evidence_ids=tuple(
            item.returned_paper_evidence_id for item in evidences
        ),
        confirmed_by=ACTOR,
        expected_state_revision=revision,
        authority_gate=gate,
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    confirmation = result.records[0]
    assert isinstance(confirmation, ReflectionAuthorshipConfirmation)
    assert confirmation.issuance_id == issuance.issuance_id
    assert confirmation.subject_link_id == issuance.subject_link_id
    assert confirmation.student_reference == issuance.student_reference
    assert confirmation.returned_paper_evidence_ids == tuple(
        item.returned_paper_evidence_id for item in evidences
    )
    assert confirmation.confirmation_basis == "teacher_reviewed_original_paper"
    assert confirmation.confirmed_by == ACTOR
    assert confirmation.authority_reference == "fixture_curation_authority"
    assert gate.requests[-1].actor == ACTOR
    assert not any(
        isinstance(item, PortfolioReflection)
        for item in load_current_records(setup.workspace)
    )


def test_confirmation_requires_authorized_adult_not_student(
    tmp_path: Path,
) -> None:
    setup, issuance, evidences = _returned_paper(tmp_path)
    revision = load_current_state(setup.workspace).state_revision

    with pytest.raises(CurationWorkflowError, match="authorized_adult"):
        confirm_returned_paper_authorship(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            issuance_id=issuance.issuance_id,
            returned_paper_evidence_ids=(
                evidences[0].returned_paper_evidence_id,
            ),
            confirmed_by=STUDENT_ACTOR,
            expected_state_revision=revision,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )


def test_confirmation_requires_explicit_evidence_for_every_issued_page(
    tmp_path: Path,
) -> None:
    setup, issuance, evidences = _returned_paper(tmp_path, pages=2)
    revision = load_current_state(setup.workspace).state_revision

    with pytest.raises(CurationWorkflowError, match="every issued page"):
        confirm_returned_paper_authorship(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            issuance_id=issuance.issuance_id,
            returned_paper_evidence_ids=(
                evidences[0].returned_paper_evidence_id,
            ),
            confirmed_by=ACTOR,
            expected_state_revision=revision,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )


def test_finalization_creates_student_authored_external_reference_and_provenance(
    tmp_path: Path,
) -> None:
    setup, issuance, evidences = _returned_paper(tmp_path, pages=2)
    confirmed = confirm_returned_paper_authorship(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        issuance_id=issuance.issuance_id,
        returned_paper_evidence_ids=tuple(
            item.returned_paper_evidence_id for item in evidences
        ),
        confirmed_by=ACTOR,
        expected_state_revision=load_current_state(
            setup.workspace
        ).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    confirmation = confirmed.records[0]
    assert isinstance(confirmation, ReflectionAuthorshipConfirmation)

    finalized = finalize_confirmed_paper_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        authorship_confirmation_id=confirmation.authorship_confirmation_id,
        recorded_by=ACTOR,
        expected_state_revision=confirmed.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    reflection = next(
        item for item in finalized.records if isinstance(item, PortfolioReflection)
    )
    provenance = next(
        item
        for item in finalized.records
        if isinstance(item, ReflectionPaperFinalization)
    )

    assert reflection.author.actor_kind == "core_student"
    assert reflection.author.actor_id == issuance.student_reference.student_id
    assert reflection.author.owning_system == "core"
    assert reflection.prompt_id == issuance.prompt_id
    assert reflection.prompt_version == issuance.prompt_version
    assert reflection.prompt_snapshot == issuance.prompt_snapshot
    assert reflection.target_scope == issuance.target_scope
    assert reflection.target_references == issuance.target_references
    assert reflection.profile_binding_id == issuance.profile_binding_id
    assert reflection.profile_revision == issuance.profile_revision
    assert reflection.reflection_requirement_id == (
        issuance.reflection_requirement_id
    )
    assert reflection.content_mode == "external_reference"
    assert reflection.language == "und"
    assert reflection.content_format == "vitrine:returned_paper_evidence"
    assert json.loads(reflection.content) == {
        "returned_paper_evidence_ids": [
            item.returned_paper_evidence_id for item in evidences
        ]
    }

    assert provenance.authorship_confirmation_id == (
        confirmation.authorship_confirmation_id
    )
    assert provenance.reflection_id == reflection.reflection_id
    assert provenance.reflection_revision == reflection.reflection_revision
    assert provenance.returned_paper_evidence_ids == (
        confirmation.returned_paper_evidence_ids
    )
    assert provenance.student_author == reflection.author
    assert provenance.recorded_by == ACTOR
    assert provenance.authority_reference == "fixture_curation_authority"


def test_finalization_requires_existing_authorship_confirmation(
    tmp_path: Path,
) -> None:
    setup, _issuance, _evidences = _returned_paper(tmp_path)

    with pytest.raises(CurationWorkflowError, match="confirmation"):
        finalize_confirmed_paper_reflection(
            setup.workspace,
            portfolio_id=setup.portfolio_id,
            authorship_confirmation_id="missing_confirmation",
            recorded_by=ACTOR,
            expected_state_revision=load_current_state(
                setup.workspace
            ).state_revision,
            authority_gate=StaticCurationAuthorityGate(),
            clock=fixed_clock,
            id_factory=setup.ids,
        )


def test_finalization_exact_replay_returns_existing_without_state_mutation(
    tmp_path: Path,
) -> None:
    setup, issuance, evidences = _returned_paper(tmp_path)
    confirmed = confirm_returned_paper_authorship(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        issuance_id=issuance.issuance_id,
        returned_paper_evidence_ids=(
            evidences[0].returned_paper_evidence_id,
        ),
        confirmed_by=ACTOR,
        expected_state_revision=load_current_state(
            setup.workspace
        ).state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    confirmation = confirmed.records[0]
    assert isinstance(confirmation, ReflectionAuthorshipConfirmation)

    first = finalize_confirmed_paper_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        authorship_confirmation_id=confirmation.authorship_confirmation_id,
        recorded_by=ACTOR,
        expected_state_revision=confirmed.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    revision = first.state_revision
    second = finalize_confirmed_paper_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        authorship_confirmation_id=confirmation.authorship_confirmation_id,
        recorded_by=ACTOR,
        expected_state_revision=revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    assert second.disposition == "existing"
    assert second.state_revision == revision
    assert second.records == first.records
    assert load_current_state(setup.workspace).state_revision == revision
