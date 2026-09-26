"""Portfolio-level paper Reflection issuance and printable packet orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vitrine.curation_services import (
    Clock,
    CurationAuthorityGate,
    IdFactory,
    _clock,
    _id,
)
from vitrine.models import ActorAttribution, CurationTargetRef, ReflectionPromptIssuance
from vitrine.paper_reflection_pdf import render_persisted_reflection_pdf
from vitrine.paper_reflection_printing import (
    PersistedReflectionPrintRoutes,
    persist_reflection_print_route_registrations,
    prepare_reflection_print_plan,
)
from vitrine.paper_reflection_services import prepare_reflection_issuance


@dataclass(frozen=True, slots=True)
class IssuedPaperReflectionPacket:
    issuance: ReflectionPromptIssuance
    state_revision: int
    pdf_path: Path
    registration_paths: tuple[Path, ...]
    created_registration_paths: tuple[Path, ...]
    reused_registration_paths: tuple[Path, ...]


def issue_paper_reflection_packet(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    reflection_requirement_id: str,
    prompt_id: str,
    prompt_version: str,
    prompt_snapshot: str,
    subject_link_id: str,
    issued_by: ActorAttribution,
    target_scope: str,
    target_references: tuple[CurationTargetRef, ...],
    page_count: int,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    student_display_name: str | None = None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> IssuedPaperReflectionPacket:
    """Issue immutable prompt/page state, persist Core routes, and render PDF."""

    issued = prepare_reflection_issuance(
        workspace_root,
        portfolio_id=portfolio_id,
        reflection_requirement_id=reflection_requirement_id,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        prompt_snapshot=prompt_snapshot,
        subject_link_id=subject_link_id,
        issued_by=issued_by,
        target_scope=target_scope,
        target_references=target_references,
        page_count=page_count,
        expected_state_revision=expected_state_revision,
        authority_gate=authority_gate,
        clock=clock,
        id_factory=id_factory,
    )
    issuance = _one_issuance(issued.records)
    return render_issued_paper_reflection_packet(
        workspace_root,
        issuance_id=issuance.issuance_id,
        expected_state_revision=issued.state_revision,
        student_display_name=student_display_name,
    )


def render_issued_paper_reflection_packet(
    workspace_root: str | Path,
    *,
    issuance_id: str,
    expected_state_revision: int,
    student_display_name: str | None = None,
) -> IssuedPaperReflectionPacket:
    """Persist/reuse exact Core routes and render one existing issuance."""

    plan = prepare_reflection_print_plan(
        workspace_root=workspace_root,
        issuance_id=issuance_id,
        expected_state_revision=expected_state_revision,
    )
    persisted = persist_reflection_print_route_registrations(plan)
    pdf_path = render_persisted_reflection_pdf(
        persisted,
        student_display_name=student_display_name,
    )
    return _packet_result(
        persisted,
        state_revision=plan.state_revision,
        pdf_path=pdf_path,
    )


def _one_issuance(records: tuple[object, ...]) -> ReflectionPromptIssuance:
    matches = tuple(
        item for item in records if isinstance(item, ReflectionPromptIssuance)
    )
    if len(matches) != 1:
        raise RuntimeError(
            "Paper Reflection issuance mutation did not return one exact issuance."
        )
    return matches[0]


def _packet_result(
    persisted: PersistedReflectionPrintRoutes,
    *,
    state_revision: int,
    pdf_path: Path,
) -> IssuedPaperReflectionPacket:
    return IssuedPaperReflectionPacket(
        issuance=persisted.plan.issuance,
        state_revision=state_revision,
        pdf_path=pdf_path,
        registration_paths=persisted.registration_paths,
        created_registration_paths=persisted.created_paths,
        reused_registration_paths=persisted.reused_paths,
    )


__all__ = [
    "IssuedPaperReflectionPacket",
    "issue_paper_reflection_packet",
    "render_issued_paper_reflection_packet",
]
