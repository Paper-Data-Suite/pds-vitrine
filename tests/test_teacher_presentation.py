from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from vitrine import portfolio_menu, teacher_presentation
from vitrine.candidate_inbox import CandidateInboxDetail
from vitrine.teacher_presentation import (
    TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION,
    TeacherCandidateDetail,
    TeacherPortfolioOverview,
    TeacherSubjectLink,
)


def _overview() -> TeacherPortfolioOverview:
    return TeacherPortfolioOverview(
        contract_version=TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION,
        portfolio_id="portfolio_exact",
        portfolio_subject_id="subject_exact",
        title="Improvement Portfolio",
        subject_label="Jordan Rivera",
        profile_binding_id="binding_exact",
        portfolio_profile_id="vitrine_starter_improvement",
        profile_revision=1,
        profile_label="Starter Improvement Portfolio",
        purpose_kind="improvement",
        subject_links=(
            TeacherSubjectLink(
                subject_link_id="link_baseline",
                school_year="2025-2026",
                class_id="english11",
                student_id="student_exact",
                display_name="Jordan Rivera",
                status="confirmed",
                current_resolution="resolvable",
            ),
            TeacherSubjectLink(
                subject_link_id="link_later",
                school_year="2026-2027",
                class_id="english12",
                student_id="student_exact",
                display_name="Jordan Rivera",
                status="confirmed",
                current_resolution="resolvable",
            ),
        ),
        candidate_count=8,
        active_selection_count=2,
        current_composition_revision=1,
        snapshot_series_count=1,
        current_edition_count=1,
    )


def test_teacher_portfolio_projection_preserves_exact_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = SimpleNamespace(
        portfolio_id="portfolio_exact",
        title_snapshot="Improvement Portfolio",
        portfolio_subject_id="subject_exact",
        subject_display_label="Jordan Rivera",
        candidate_count=8,
        active_selection_count=2,
        current_composition_revision=1,
        snapshot_series_count=1,
        current_edition_count=1,
    )
    monkeypatch.setattr(
        teacher_presentation,
        "show_portfolio",
        lambda *_: SimpleNamespace(summary=summary),
    )
    monkeypatch.setattr(
        teacher_presentation,
        "show_subject",
        lambda *_: SimpleNamespace(
            summary=SimpleNamespace(display_name="Jordan Rivera"),
            current_links=(
                SimpleNamespace(
                    subject_link_id="link_exact",
                    reference=SimpleNamespace(
                        school_year="2025-2026",
                        class_id="english11",
                        student_id="student_exact",
                    ),
                    display_name="Jordan Rivera",
                    status="confirmed",
                    current_resolution="resolvable",
                ),
            ),
        ),
    )
    reference = SimpleNamespace(
        portfolio_profile_id="vitrine_starter_improvement",
        profile_revision=1,
    )
    monkeypatch.setattr(
        teacher_presentation,
        "get_portfolio_profile_binding",
        lambda *_: SimpleNamespace(
            profile_binding_id="binding_exact",
            profile_revision=reference,
        ),
    )
    monkeypatch.setattr(
        teacher_presentation,
        "get_profile_revision",
        lambda *_: SimpleNamespace(
            label="Starter Improvement Portfolio",
            purpose_kind="improvement",
        ),
    )

    view = teacher_presentation.build_teacher_portfolio_overview(
        tmp_path,
        "portfolio_exact",
    )

    assert view.contract_version == TEACHER_INFORMATION_ARCHITECTURE_CONTRACT_VERSION
    assert view.subject_label == "Jordan Rivera"
    assert view.profile_label == "Starter Improvement Portfolio"
    assert view.portfolio_id == "portfolio_exact"
    assert view.profile_binding_id == "binding_exact"
    assert view.portfolio_profile_id == "vitrine_starter_improvement"
    assert view.subject_links[0].student_id == "student_exact"


def test_default_portfolio_overview_prioritizes_teacher_context() -> None:
    output = io.StringIO()

    portfolio_menu._render_teacher_portfolio_overview(output, _overview())

    rendered = output.getvalue()
    assert "Jordan Rivera" in rendered
    assert "Improvement Portfolio" in rendered
    assert "Starter Improvement Portfolio" in rendered
    assert "Profile revision: 1" in rendered
    assert "2025-2026 / english11 / ID student_exact" in rendered
    assert "2026-2027 / english12 / ID student_exact" in rendered
    assert "Working Composition: revision 1" in rendered
    assert "Current Portfolio Editions: 1" in rendered
    assert "portfolio_exact" not in rendered
    assert "binding_exact" not in rendered
    assert "vitrine_starter_improvement" not in rendered
    assert "link_baseline" not in rendered


def test_portfolio_technical_details_preserve_exact_provenance() -> None:
    output = io.StringIO()

    portfolio_menu._render_portfolio_technical_details(output, _overview())

    rendered = output.getvalue()
    assert "Technical Details / Provenance" in rendered
    assert "Portfolio ID: portfolio_exact" in rendered
    assert "Portfolio Subject ID: subject_exact" in rendered
    assert "Profile Binding ID: binding_exact" in rendered
    assert "Profile ID: vitrine_starter_improvement" in rendered
    assert "Subject Link ID: link_baseline" in rendered
    assert "Resolution: resolvable" in rendered
    assert "Snapshot Series: 1" in rendered


def test_teacher_candidate_projection_uses_profile_section_labels_without_replacing_ids() -> None:
    item = SimpleNamespace(
        entry_id="candidate:candidate_exact",
        candidate_id="candidate_exact",
        current_evaluation_id="evaluation_exact",
        portfolio_id="portfolio_exact",
        portfolio_label="Improvement Portfolio",
        portfolio_subject_id="subject_exact",
        subject_label="Jordan Rivera",
        profile_binding_id="binding_exact",
        portfolio_profile_id="profile_exact",
        profile_revision=1,
        profile_label="Starter Improvement Portfolio",
        profile_purpose="improvement",
        source_display_label="Argument Paragraph — First Draft",
        evaluation_outcome="eligible",
        candidate_condition="ready_for_consideration",
        stale_state="current",
        attention_needed=False,
        selected_state="unselected",
        eligible_section_ids=("baseline", "supporting_feedback"),
    )
    profile_revision = SimpleNamespace(
        sections=(
            SimpleNamespace(section_id="baseline", label="Baseline Evidence"),
            SimpleNamespace(
                section_id="supporting_feedback",
                label="Supporting Feedback",
            ),
        )
    )
    detail = cast(
        CandidateInboxDetail,
        SimpleNamespace(item=item, profile_revision=profile_revision),
    )

    view = teacher_presentation.build_teacher_candidate_detail(detail)

    assert isinstance(view, TeacherCandidateDetail)
    assert view.evidence_label == "Argument Paragraph — First Draft"
    assert tuple(x.label for x in view.eligible_sections) == (
        "Baseline Evidence",
        "Supporting Feedback",
    )
    assert tuple(x.section_id for x in view.eligible_sections) == (
        "baseline",
        "supporting_feedback",
    )
    assert view.candidate_id == "candidate_exact"
    assert view.current_evaluation_id == "evaluation_exact"
    assert view.profile_binding_id == "binding_exact"


def test_teacher_term_is_display_only_humanization() -> None:
    value = teacher_presentation.teacher_term(
        "coherent_with_unresolved_obligations"
    )
    assert value == "Coherent With Unresolved Obligations"
    assert teacher_presentation.teacher_term(None) == "Unavailable"
