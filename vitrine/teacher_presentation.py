"""Transient teacher-facing presentation projections.

This module translates exact canonical Vitrine state into low-density teacher
context without creating a second authority. Human-readable labels are display
only; the exact identifiers retained here remain the underlying authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vitrine.candidate_inbox import CandidateInboxDetail
from vitrine.models import PortfolioProfileBinding, PortfolioProfileRevision
from vitrine.portfolio_services import show_portfolio
from vitrine.profile_services import (
    get_portfolio_profile_binding,
    get_profile_revision,
)
from vitrine.subject_services import show_subject

TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION = (
    "vitrine_teacher_information_architecture_v1"
)


@dataclass(frozen=True, slots=True)
class TeacherSubjectLink:
    """One exact class-qualified Subject link plus bounded display context."""

    subject_link_id: str
    school_year: str
    class_id: str
    student_id: str
    display_name: str | None
    status: str
    current_resolution: str


@dataclass(frozen=True, slots=True)
class TeacherCandidateSection:
    'One exact eligible Profile section plus its display label.'

    section_id: str
    label: str | None


@dataclass(frozen=True, slots=True)
class TeacherCandidateDetail:
    'Teacher-first projection over one exact Candidate Inbox detail.'

    contract_version: str
    entry_id: str
    candidate_id: str | None
    current_evaluation_id: str | None
    portfolio_id: str
    portfolio_label: str
    portfolio_subject_id: str
    subject_label: str
    profile_binding_id: str
    portfolio_profile_id: str
    profile_revision: int
    profile_label: str
    profile_purpose: str
    evidence_label: str
    evaluation_outcome: str | None
    candidate_condition: str | None
    currentness: str | None
    attention_needed: bool
    selected_state: str
    eligible_sections: tuple[TeacherCandidateSection, ...]


@dataclass(frozen=True, slots=True)
class TeacherProfileSection:
    """One exact Profile section plus its human-readable presentation."""

    section_id: str
    label: str
    purpose: str
    obligation: str


@dataclass(frozen=True, slots=True)
class TeacherProfileBinding:
    """Teacher-first projection over one exact active Profile Binding."""

    contract_version: str
    portfolio_id: str
    profile_binding_id: str
    portfolio_profile_id: str
    profile_revision: int
    profile_label: str
    purpose_kind: str
    predecessor_binding_id: str | None
    binding_reason: str | None
    bound_at: str
    sections: tuple[TeacherProfileSection, ...]
    audience_rule_count: int


@dataclass(frozen=True, slots=True)
class TeacherPortfolioOverview:
    """Read-only teacher projection for one exact Portfolio."""

    contract_version: str
    portfolio_id: str
    portfolio_subject_id: str
    title: str | None
    subject_label: str | None
    profile_binding_id: str | None
    portfolio_profile_id: str | None
    profile_revision: int | None
    profile_label: str | None
    purpose_kind: str | None
    subject_links: tuple[TeacherSubjectLink, ...]
    candidate_count: int
    active_selection_count: int
    current_composition_revision: int | None
    snapshot_series_count: int
    current_edition_count: int


def teacher_term(value: str | None) -> str:
    """Render one bounded enum/token for ordinary teacher display."""

    if value is None:
        return "Unavailable"
    return value.replace("_", " ").strip().title()


def build_teacher_candidate_detail(
    detail: CandidateInboxDetail,
) -> TeacherCandidateDetail:
    'Project one exact Inbox detail without changing Candidate semantics.'

    item = detail.item
    section_labels = {
        section.section_id: section.label for section in detail.profile_revision.sections
    }
    eligible_sections = tuple(
        TeacherCandidateSection(
            section_id=section_id,
            label=section_labels.get(section_id),
        )
        for section_id in item.eligible_section_ids
    )
    return TeacherCandidateDetail(
        contract_version=TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION,
        entry_id=item.entry_id,
        candidate_id=item.candidate_id,
        current_evaluation_id=item.current_evaluation_id,
        portfolio_id=item.portfolio_id,
        portfolio_label=item.portfolio_label,
        portfolio_subject_id=item.portfolio_subject_id,
        subject_label=item.subject_label,
        profile_binding_id=item.profile_binding_id,
        portfolio_profile_id=item.portfolio_profile_id,
        profile_revision=item.profile_revision,
        profile_label=item.profile_label,
        profile_purpose=item.profile_purpose,
        evidence_label=item.source_display_label,
        evaluation_outcome=item.evaluation_outcome,
        candidate_condition=item.candidate_condition,
        currentness=item.stale_state,
        attention_needed=item.attention_needed,
        selected_state=item.selected_state,
        eligible_sections=eligible_sections,
    )


def build_teacher_profile_binding(
    binding: PortfolioProfileBinding,
    revision: PortfolioProfileRevision,
) -> TeacherProfileBinding:
    """Project one exact Binding/Revision pair without changing authority."""

    if binding.profile_revision != revision.reference:
        raise ValueError(
            "profile_binding_revision_mismatch: exact Binding and Revision differ"
        )
    return TeacherProfileBinding(
        contract_version=TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION,
        portfolio_id=binding.portfolio_id,
        profile_binding_id=binding.profile_binding_id,
        portfolio_profile_id=binding.profile_revision.portfolio_profile_id,
        profile_revision=binding.profile_revision.profile_revision,
        profile_label=revision.label,
        purpose_kind=revision.purpose_kind,
        predecessor_binding_id=binding.predecessor_binding_id,
        binding_reason=binding.binding_reason,
        bound_at=binding.bound_at.isoformat(),
        sections=tuple(
            TeacherProfileSection(
                section_id=section.section_id,
                label=section.label,
                purpose=section.purpose,
                obligation=section.obligation,
            )
            for section in revision.sections
        ),
        audience_rule_count=len(revision.audience_rules),
    )


def build_teacher_portfolio_overview(
    workspace_root: str | Path,
    portfolio_id: str,
) -> TeacherPortfolioOverview:
    """Project one exact Portfolio into teacher-first presentation context."""

    detail = show_portfolio(workspace_root, portfolio_id)
    summary = detail.summary
    subject = show_subject(workspace_root, summary.portfolio_subject_id)
    binding = get_portfolio_profile_binding(workspace_root, portfolio_id)

    profile_id: str | None = None
    profile_revision: int | None = None
    profile_label: str | None = None
    purpose_kind: str | None = None
    profile_binding_id: str | None = None
    if binding is not None:
        revision = get_profile_revision(workspace_root, binding.profile_revision)
        profile_binding_id = binding.profile_binding_id
        profile_id = binding.profile_revision.portfolio_profile_id
        profile_revision = binding.profile_revision.profile_revision
        profile_label = revision.label
        purpose_kind = revision.purpose_kind

    links = tuple(
        TeacherSubjectLink(
            subject_link_id=item.subject_link_id,
            school_year=item.reference.school_year,
            class_id=item.reference.class_id,
            student_id=item.reference.student_id,
            display_name=item.display_name,
            status=item.status,
            current_resolution=item.current_resolution,
        )
        for item in subject.current_links
    )

    return TeacherPortfolioOverview(
        contract_version=TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION,
        portfolio_id=summary.portfolio_id,
        portfolio_subject_id=summary.portfolio_subject_id,
        title=summary.title_snapshot,
        subject_label=subject.summary.display_name or summary.subject_display_label,
        profile_binding_id=profile_binding_id,
        portfolio_profile_id=profile_id,
        profile_revision=profile_revision,
        profile_label=profile_label,
        purpose_kind=purpose_kind,
        subject_links=links,
        candidate_count=summary.candidate_count,
        active_selection_count=summary.active_selection_count,
        current_composition_revision=summary.current_composition_revision,
        snapshot_series_count=summary.snapshot_series_count,
        current_edition_count=summary.current_edition_count,
    )


__all__ = [
    "TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION",
    "TeacherCandidateDetail",
    "TeacherCandidateSection",
    "TeacherPortfolioOverview",
    "TeacherProfileBinding",
    "TeacherProfileSection",
    "TeacherSubjectLink",
    "build_teacher_candidate_detail",
    "build_teacher_profile_binding",
    "build_teacher_portfolio_overview",
    "teacher_term",
]
