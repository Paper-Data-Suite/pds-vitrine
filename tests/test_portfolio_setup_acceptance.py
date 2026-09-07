from __future__ import annotations

import io
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from tests.profile_helpers import (
    ACTOR,
    NOW,
    improvement_family,
    improvement_requirements,
    improvement_revision,
    showcase_family,
    showcase_requirements,
    showcase_revision,
)
from tests.subject_helpers import make_subject_workspace, teacher_context
from vitrine.models import (
    ClassQualifiedStudentRef,
    PortfolioSubject,
    PortfolioSubjectClassLink,
    ProfileApplicability,
)
from vitrine.portfolio_services import list_portfolios
from vitrine.portfolio_setup import (
    CreatePortfolioForStudentRequest,
    create_portfolio_for_student,
    plan_create_portfolio_for_student,
    resolve_portfolio_setup_subject,
)
from vitrine.portfolio_setup_menu import run_create_portfolio_for_student_menu
from vitrine.profile_services import (
    ProfileBindingContext,
    activate_profile_revision,
    create_profile_family,
    create_profile_revision,
    list_profile_families,
    observe_profile_state_revision,
    transition_profile_lifecycle,
)
from vitrine.storage import (
    commit_record_batch,
    load_current_records,
    load_current_state,
)
from vitrine.subject_services import (
    create_portfolio_subject,
    merge_portfolio_subjects,
    observe_state_revision,
)


def _ref(
    class_id: str = "english10_p2",
    student_id: str = "00107",
    *,
    school_year: str = "2026-2027",
) -> ClassQualifiedStudentRef:
    return ClassQualifiedStudentRef(
        school_year=school_year,
        class_id=class_id,
        student_id=student_id,
    )


def _install_improvement(
    workspace: Path,
    *,
    applicability: ProfileApplicability | None = None,
    profile_id: str = "profile_growth",
) -> object:
    if not any(
        item.profile_family_id == "family_improvement"
        for item in list_profile_families(workspace)
    ):
        create_profile_family(
            workspace,
            improvement_family(),
            expected_state_revision=observe_profile_state_revision(workspace),
        )
    revision = improvement_revision(1, profile_id=profile_id)
    if applicability is not None:
        revision = replace(revision, applicability=applicability)
    create_profile_revision(
        workspace,
        revision,
        improvement_requirements(1, profile_id=profile_id),
        expected_state_revision=observe_profile_state_revision(workspace),
    )
    activate_profile_revision(
        workspace,
        revision.reference,
        actor=ACTOR,
        reason="Approved for Issue #65 acceptance.",
        authority_reference="local_instructional_policy",
        expected_state_revision=observe_profile_state_revision(workspace),
    )
    return revision.reference


def _install_showcase(workspace: Path) -> object:
    create_profile_family(
        workspace,
        showcase_family(),
        expected_state_revision=observe_profile_state_revision(workspace),
    )
    revision = showcase_revision()
    create_profile_revision(
        workspace,
        revision,
        showcase_requirements(),
        expected_state_revision=observe_profile_state_revision(workspace),
    )
    activate_profile_revision(
        workspace,
        revision.reference,
        actor=ACTOR,
        reason="Approved for Issue #65 acceptance.",
        authority_reference="local_instructional_policy",
        expected_state_revision=observe_profile_state_revision(workspace),
    )
    return revision.reference


def test_school_year_mismatch_blocks_before_setup_mutation(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    profile = _install_improvement(workspace)
    before = load_current_state(workspace).state_revision
    before_records = load_current_records(workspace)

    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref(school_year="2025-2026"),
            purpose_kind="improvement",
            profile_revision=profile,
            subject_action="create_new",
            identity_context=teacher_context(),
        ),
    )

    assert plan.subject_resolution.roster_status == "class_school_year_mismatch"
    assert "student_reference_unavailable" in plan.blocking_codes
    assert not plan.ready
    assert load_current_state(workspace).state_revision == before
    assert load_current_records(workspace) == before_records


def test_missing_roster_student_blocks_before_setup_mutation(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    profile = _install_improvement(workspace)
    before = load_current_state(workspace).state_revision

    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref(student_id="missing_student"),
            purpose_kind="improvement",
            profile_revision=profile,
            subject_action="create_new",
            identity_context=teacher_context(),
        ),
    )

    assert plan.subject_resolution.roster_status == "student_not_found"
    assert "student_reference_unavailable" in plan.blocking_codes
    assert not plan.ready
    assert load_current_state(workspace).state_revision == before


def test_exact_reference_conflict_blocks_guided_setup(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    first = create_portfolio_subject(
        workspace,
        _ref(),
        context=teacher_context(),
        expected_state_revision=None,
    )
    duplicate_subject = PortfolioSubject(
        portfolio_subject_id="subject_conflict_manual",
        created_at=NOW,
        created_by=ACTOR,
        display_name_snapshot="Conflicting Subject",
    )
    duplicate_link = PortfolioSubjectClassLink(
        subject_link_id="link_conflict_manual",
        portfolio_subject_id=duplicate_subject.portfolio_subject_id,
        student_reference=_ref(),
        confirmed_at=NOW,
        confirmed_by=ACTOR,
        confirmation_basis="teacher_confirmed",
        authority_reference="acceptance_fixture",
    )
    commit_record_batch(
        workspace,
        (duplicate_subject, duplicate_link),
        expected_state_revision=observe_state_revision(workspace),
    )
    before = load_current_state(workspace).state_revision

    resolution = resolve_portfolio_setup_subject(workspace, _ref())

    assert resolution.subject_status == "conflict"
    assert set(resolution.subject_ids) == {
        first.subject_ids[0],
        duplicate_subject.portfolio_subject_id,
    }
    assert load_current_state(workspace).state_revision == before


def test_historical_subject_cannot_receive_new_setup_link(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    first = create_portfolio_subject(
        workspace,
        _ref("english10_p2", "00421"),
        context=teacher_context(),
        expected_state_revision=None,
    )
    second = create_portfolio_subject(
        workspace,
        _ref("csp_p1", "00999"),
        context=teacher_context(),
        expected_state_revision=observe_state_revision(workspace),
    )
    merge_portfolio_subjects(
        workspace,
        (first.subject_ids[0], second.subject_ids[0]),
        context=teacher_context("Teacher reconciled two historical identities."),
        expected_state_revision=observe_state_revision(workspace),
    )
    profile = _install_improvement(workspace)
    before = load_current_state(workspace).state_revision

    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("math_p3"),
            purpose_kind="improvement",
            profile_revision=profile,
            subject_action="link_existing",
            existing_subject_id=first.subject_ids[0],
            identity_context=teacher_context(),
        ),
    )

    assert "subject_historical" in plan.blocking_codes
    assert not plan.ready
    assert load_current_state(workspace).state_revision == before


def test_profile_purpose_mismatch_never_silently_selects_policy(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    improvement = _install_improvement(workspace)
    _install_showcase(workspace)

    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref(),
            purpose_kind="showcase",
            profile_revision=improvement,
            subject_action="create_new",
            identity_context=teacher_context(),
        ),
    )

    assert "profile_purpose_mismatch" in plan.blocking_codes
    assert not plan.ready


def test_multiple_bindable_profiles_require_explicit_exact_choice(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    first = _install_improvement(workspace, profile_id="profile_growth_a")
    second = _install_improvement(workspace, profile_id="profile_growth_b")

    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref(),
            purpose_kind="improvement",
            subject_action="create_new",
            identity_context=teacher_context(),
        ),
    )

    assert {item.reference for item in plan.profile_choices} == {first, second}
    assert plan.selected_profile is None
    assert "profile_choice_required" in plan.blocking_codes
    assert not plan.ready


def test_deprecated_profile_cannot_be_bound_implicitly(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    profile = _install_improvement(workspace)
    transition_profile_lifecycle(
        workspace,
        profile,
        "deprecated",
        actor=ACTOR,
        reason="Profile is no longer approved for new setup.",
        authority_reference="local_instructional_policy",
        expected_state_revision=observe_profile_state_revision(workspace),
    )

    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref(),
            purpose_kind="improvement",
            profile_revision=profile,
            subject_action="create_new",
            identity_context=teacher_context(),
        ),
    )

    assert "profile_not_bindable" in plan.blocking_codes
    assert not plan.ready
    assert plan.profile_choices == ()


def test_required_profile_context_must_be_complete_and_exact(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    profile = _install_improvement(
        workspace,
        applicability=ProfileApplicability(
            institution_id="hillside_hs",
            program_id="english_program",
            school_years=("2026-2027",),
            content_areas=("english",),
            effective_from=date(2026, 9, 1),
            effective_through=date(2027, 6, 30),
        ),
    )

    incomplete = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref(),
            purpose_kind="improvement",
            profile_revision=profile,
            subject_action="create_new",
            identity_context=teacher_context(),
        ),
    )
    assert "profile_not_applicable" in incomplete.blocking_codes
    assert not incomplete.ready

    complete = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref(),
            purpose_kind="improvement",
            profile_revision=profile,
            profile_context=ProfileBindingContext(
                institution_id="hillside_hs",
                program_id="english_program",
                content_area="english",
                as_of=date(2026, 9, 6),
            ),
            subject_action="create_new",
            identity_context=teacher_context(),
        ),
    )

    assert complete.ready
    assert complete.effective_profile_context.school_year == "2026-2027"


def test_reviewed_proposed_ids_are_the_ids_atomically_committed(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    profile = _install_improvement(workspace)
    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref(),
            purpose_kind="improvement",
            profile_revision=profile,
            subject_action="create_new",
            identity_context=teacher_context(),
            title_snapshot="Reviewed exact setup",
        ),
    )
    assert plan.ready

    result = create_portfolio_for_student(
        workspace,
        plan,
        actor=ACTOR,
    )

    expected_ids = (
        plan.proposed_ids.portfolio_subject_id,
        plan.proposed_ids.subject_link_id,
        plan.proposed_ids.display_snapshot_id,
        *plan.proposed_ids.identity_decision_ids,
        plan.proposed_ids.portfolio_id,
        plan.proposed_ids.profile_binding_id,
    )
    assert result.created_record_ids == expected_ids
    persisted_ids: set[str] = set()
    for item in load_current_records(workspace):
        for attribute in (
            "portfolio_subject_id",
            "subject_link_id",
            "display_snapshot_id",
            "identity_decision_id",
            "portfolio_id",
            "profile_binding_id",
        ):
            value = getattr(item, attribute, None)
            if isinstance(value, str):
                persisted_ids.add(value)
    assert set(expected_ids) <= persisted_ids


def test_final_menu_cancel_leaves_canonical_state_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    _install_improvement(workspace)
    monkeypatch.setattr(
        "vitrine.portfolio_setup_menu.list_linkable_classes",
        lambda _root: (("english10_p2", "2026-2027"),),
    )
    values = iter(
        [
            "1",
            "1",
            "1",
            "1",
            "Teacher confirmed identity.",
            "C",
            "1",
            "1",
            "Canceled Portfolio",
            "",
            "CANCEL",
            "",
        ]
    )
    before = load_current_state(workspace).state_revision
    before_records = load_current_records(workspace)

    result = run_create_portfolio_for_student_menu(
        workspace_root=workspace,
        input_fn=lambda _prompt: next(values),
        output=io.StringIO(),
        clear_fn=lambda: None,
        actor=ACTOR,
    )

    assert result is None
    assert load_current_state(workspace).state_revision == before
    assert load_current_records(workspace) == before_records
    assert list_portfolios(workspace) == ()
