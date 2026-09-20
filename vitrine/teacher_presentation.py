"""Transient teacher-facing presentation projections.

This module translates exact canonical Vitrine state into low-density teacher
context without creating a second authority. Human-readable labels are display
only; the exact identifiers retained here remain the underlying authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
    "TeacherPortfolioOverview",
    "TeacherSubjectLink",
    "build_teacher_portfolio_overview",
    "teacher_term",
]
