from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from pds_core.classes import load_class_roster, write_class_roster
from pds_core.rosters import Roster

from tests.profile_helpers import (
    ACTOR,
    improvement_family,
    improvement_requirements,
    improvement_revision,
)
from tests.profile_helpers import (
    DeterministicIds as ProfileIds,
)
from tests.profile_helpers import (
    fixed_clock as profile_clock,
)
from tests.subject_helpers import (
    DeterministicIds as SubjectIds,
)
from tests.subject_helpers import (
    make_subject_workspace,
    teacher_context,
)
from vitrine.models import ClassQualifiedStudentRef, ProfileRevisionRef
from vitrine.portfolio_services import create_portfolio, show_portfolio
from vitrine.portfolio_setup import (
    CreatePortfolioForStudentRequest,
    PortfolioSetupError,
    create_portfolio_for_student,
    plan_create_portfolio_for_student,
)
from vitrine.profile_services import (
    activate_profile_revision,
    create_profile_family,
    create_profile_revision,
    get_portfolio_profile_binding,
    observe_profile_state_revision,
)
from vitrine.storage import load_current_records, load_current_state
from vitrine.subject_services import (
    create_portfolio_subject,
    observe_state_revision,
    show_subject,
)


def _ref(class_id: str, student_id: str = "00107") -> ClassQualifiedStudentRef:
    return ClassQualifiedStudentRef(
        school_year="2026-2027",
        class_id=class_id,
        student_id=student_id,
    )


def _install_improvement(workspace: Path) -> ProfileRevisionRef:
    ids = ProfileIds()
    create_profile_family(
        workspace,
        improvement_family(),
        expected_state_revision=observe_profile_state_revision(workspace),
    )
    revision = improvement_revision(1)
    create_profile_revision(
        workspace,
        revision,
        improvement_requirements(1),
        expected_state_revision=observe_profile_state_revision(workspace),
    )
    activate_profile_revision(
        workspace,
        revision.reference,
        actor=ACTOR,
        reason="Approved for atomic setup tests.",
        authority_reference="local_instructional_policy",
        expected_state_revision=observe_profile_state_revision(workspace),
        clock=profile_clock,
        id_factory=ids,
    )
    return revision.reference


def test_new_subject_portfolio_and_binding_commit_in_one_revision(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    profile = _install_improvement(workspace)
    before = load_current_state(workspace).state_revision
    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("english10_p2"),
            purpose_kind="improvement",
            profile_revision=profile,
            subject_action="create_new",
            identity_context=teacher_context(),
            title_snapshot="Jane Improvement",
        ),
    )
    assert plan.ready

    result = create_portfolio_for_student(
        workspace,
        plan,
        actor=ACTOR,
        clock=profile_clock,
    )

    assert result.state_revision == before + 1
    assert result.subject_action == "create_new"
    assert result.portfolio_subject_id == plan.proposed_ids.portfolio_subject_id
    subject = show_subject(workspace, result.portfolio_subject_id)
    assert [item.reference for item in subject.current_links] == [_ref("english10_p2")]
    portfolio = show_portfolio(workspace, result.portfolio_id)
    assert portfolio.portfolio.portfolio_subject_id == result.portfolio_subject_id
    binding = get_portfolio_profile_binding(workspace, result.portfolio_id)
    assert binding is not None
    assert binding.profile_binding_id == result.profile_binding_id
    assert binding.profile_revision == profile


def test_explicit_cross_class_link_portfolio_binding_commit_together(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    existing = create_portfolio_subject(
        workspace,
        _ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=SubjectIds(),
    )
    profile = _install_improvement(workspace)
    before = load_current_state(workspace).state_revision
    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("csp_p1"),
            purpose_kind="improvement",
            profile_revision=profile,
            subject_action="link_existing",
            existing_subject_id=existing.subject_ids[0],
            identity_context=teacher_context(
                "Teacher confirmed this cross-class association."
            ),
        ),
    )
    assert plan.ready

    result = create_portfolio_for_student(
        workspace,
        plan,
        actor=ACTOR,
        clock=profile_clock,
    )

    assert result.state_revision == before + 1
    assert result.subject_action == "link_existing"
    subject = show_subject(workspace, existing.subject_ids[0])
    assert {item.reference.class_id for item in subject.current_links} == {
        "english10_p2",
        "csp_p1",
    }
    assert all(item.reference.student_id == "00107" for item in subject.current_links)
    binding = get_portfolio_profile_binding(workspace, result.portfolio_id)
    assert binding is not None and binding.profile_revision == profile


def test_resolved_subject_creates_only_portfolio_and_binding(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    existing = create_portfolio_subject(
        workspace,
        _ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=SubjectIds(),
    )
    profile = _install_improvement(workspace)
    before_links = show_subject(workspace, existing.subject_ids[0]).current_links
    before = load_current_state(workspace).state_revision
    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("english10_p2"),
            purpose_kind="improvement",
            profile_revision=profile,
        ),
    )
    assert plan.ready
    assert plan.planned_record_kinds == (
        "portfolio",
        "portfolio_profile_binding",
    )

    result = create_portfolio_for_student(
        workspace,
        plan,
        actor=ACTOR,
        clock=profile_clock,
    )

    assert result.state_revision == before + 1
    assert result.subject_action == "reuse_existing"
    assert (
        show_subject(workspace, existing.subject_ids[0]).current_links == before_links
    )
    assert len(result.created_record_ids) == 2


def test_state_drift_rejects_reviewed_plan_without_partial_setup(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    existing = create_portfolio_subject(
        workspace,
        _ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=SubjectIds(),
    )
    profile = _install_improvement(workspace)
    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("english10_p2"),
            purpose_kind="improvement",
            profile_revision=profile,
        ),
    )
    assert plan.ready

    create_portfolio(
        workspace,
        portfolio_subject_id=existing.subject_ids[0],
        created_by=ACTOR,
        expected_state_revision=observe_state_revision(workspace),
        title_snapshot="Intervening Portfolio",
    )
    after_drift = load_current_state(workspace).state_revision

    with pytest.raises(PortfolioSetupError) as raised:
        create_portfolio_for_student(
            workspace,
            plan,
            actor=ACTOR,
            clock=profile_clock,
        )

    assert raised.value.code == "state_conflict"
    assert load_current_state(workspace).state_revision == after_drift
    assert not any(
        getattr(item, "portfolio_id", None) == plan.proposed_ids.portfolio_id
        for item in load_current_records(workspace)
    )


def test_core_roster_drift_requires_review_and_writes_nothing(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    profile = _install_improvement(workspace)
    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("english10_p2"),
            purpose_kind="improvement",
            profile_revision=profile,
            subject_action="create_new",
            identity_context=teacher_context(),
        ),
    )
    assert plan.ready
    before_revision = load_current_state(workspace).state_revision
    before_records = load_current_records(workspace)

    roster = load_class_roster(workspace, "english10_p2")
    students = tuple(
        replace(student, first_name="Janet")
        if student.student_id == "00107"
        else student
        for student in roster.students
    )
    write_class_roster(
        workspace,
        Roster(
            class_id=roster.class_id,
            students=students,
            columns=roster.columns,
        ),
        overwrite=True,
    )

    with pytest.raises(PortfolioSetupError) as raised:
        create_portfolio_for_student(
            workspace,
            plan,
            actor=ACTOR,
            clock=profile_clock,
        )

    assert raised.value.code == "roster_source_changed"
    assert load_current_state(workspace).state_revision == before_revision
    assert load_current_records(workspace) == before_records


def test_atomic_setup_does_not_create_candidate_or_curation_state(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    profile = _install_improvement(workspace)
    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("english10_p2"),
            purpose_kind="improvement",
            profile_revision=profile,
            subject_action="create_new",
            identity_context=teacher_context(),
        ),
    )

    create_portfolio_for_student(
        workspace,
        plan,
        actor=ACTOR,
        clock=profile_clock,
    )

    record_types = {item.record_type for item in load_current_records(workspace)}
    assert not any("candidate" in item for item in record_types)
    assert not any("selection" in item for item in record_types)
    assert not any("placement" in item for item in record_types)
