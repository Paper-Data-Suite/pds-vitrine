from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from tests.profile_helpers import (
    ACTOR,
    improvement_family,
    improvement_requirements,
    improvement_revision,
    showcase_family,
    showcase_requirements,
    showcase_revision,
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
from vitrine.models import (
    ClassQualifiedStudentRef,
    ProfileApplicability,
    ProfileRevisionRef,
)
from vitrine.portfolio_services import create_portfolio
from vitrine.portfolio_setup import (
    CREATE_PORTFOLIO_FOR_STUDENT_CONTRACT_VERSION,
    CreatePortfolioForStudentRequest,
    list_portfolio_setup_profiles,
    plan_create_portfolio_for_student,
    resolve_portfolio_setup_subject,
)
from vitrine.profile_services import (
    ProfileBindingContext,
    activate_profile_revision,
    create_profile_family,
    create_profile_revision,
    observe_profile_state_revision,
)
from vitrine.storage import load_current_records, load_current_state
from vitrine.subject_services import create_portfolio_subject, observe_state_revision


def _ref(class_id: str, student_id: str = "00107") -> ClassQualifiedStudentRef:
    return ClassQualifiedStudentRef(
        school_year="2026-2027",
        class_id=class_id,
        student_id=student_id,
    )


def _install_improvement(
    workspace: Path,
    *,
    applicability: ProfileApplicability | None = None,
    ids: ProfileIds | None = None,
) -> ProfileRevisionRef:
    ids = ids or ProfileIds()
    create_profile_family(
        workspace,
        improvement_family(),
        expected_state_revision=observe_profile_state_revision(workspace),
    )
    revision = improvement_revision(1)
    if applicability is not None:
        revision = replace(revision, applicability=applicability)
    create_profile_revision(
        workspace,
        revision,
        improvement_requirements(1),
        expected_state_revision=observe_profile_state_revision(workspace),
    )
    reference = revision.reference
    activate_profile_revision(
        workspace,
        reference,
        actor=ACTOR,
        reason="Approved for setup planning.",
        authority_reference="local_instructional_policy",
        expected_state_revision=observe_profile_state_revision(workspace),
        clock=profile_clock,
        id_factory=ids,
    )
    return reference


def _install_showcase(
    workspace: Path,
    *,
    ids: ProfileIds | None = None,
) -> ProfileRevisionRef:
    ids = ids or ProfileIds()
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
        reason="Approved for setup planning.",
        authority_reference="local_instructional_policy",
        expected_state_revision=observe_profile_state_revision(workspace),
        clock=profile_clock,
        id_factory=ids,
    )
    return revision.reference


def test_repeated_student_id_across_classes_is_not_auto_linked(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    first = create_portfolio_subject(
        workspace,
        _ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=SubjectIds(),
    )

    resolution = resolve_portfolio_setup_subject(workspace, _ref("csp_p1"))

    assert resolution.roster_status == "resolvable"
    assert resolution.subject_status == "unlinked"
    assert resolution.subject_ids == ()
    assert first.subject_ids[0] not in resolution.subject_ids


def test_same_display_name_is_not_identity_authority(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    create_portfolio_subject(
        workspace,
        _ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=SubjectIds(),
    )

    resolution = resolve_portfolio_setup_subject(workspace, _ref("csp_p1", "00999"))

    assert resolution.student is not None
    assert resolution.student.display_name == "Jane Doe"
    assert resolution.subject_status == "unlinked"


def test_planner_is_read_only_and_requires_explicit_cross_class_choice(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    created = create_portfolio_subject(
        workspace,
        _ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=SubjectIds(),
    )
    _install_improvement(workspace)
    before_revision = load_current_state(workspace).state_revision
    before_records = load_current_records(workspace)

    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("csp_p1"),
            purpose_kind="improvement",
        ),
        id_factory=SubjectIds(),
    )

    assert plan.contract_version == CREATE_PORTFOLIO_FOR_STUDENT_CONTRACT_VERSION
    assert "subject_choice_required" in plan.blocking_codes
    assert plan.subject_resolution.subject_status == "unlinked"
    assert plan.portfolio_subject_id is None
    assert created.subject_ids[0] not in plan.subject_resolution.subject_ids
    assert load_current_state(workspace).state_revision == before_revision
    assert load_current_records(workspace) == before_records


def test_link_existing_preview_shows_existing_and_proposed_exact_links(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    created = create_portfolio_subject(
        workspace,
        _ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=SubjectIds(),
    )
    profile = _install_improvement(workspace)
    before_revision = observe_state_revision(workspace)

    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("csp_p1"),
            purpose_kind="improvement",
            profile_revision=profile,
            subject_action="link_existing",
            existing_subject_id=created.subject_ids[0],
            identity_context=teacher_context(
                "Teacher confirmed the cross-class association."
            ),
        ),
        id_factory=SubjectIds(),
    )

    assert plan.ready
    assert plan.subject_action == "link_existing"
    assert plan.portfolio_subject_id == created.subject_ids[0]
    assert [item.disposition for item in plan.resulting_links] == [
        "existing",
        "proposed",
    ]
    assert {item.reference.class_id for item in plan.resulting_links} == {
        "english10_p2",
        "csp_p1",
    }
    assert plan.planned_record_kinds == (
        "portfolio_subject_class_link",
        "portfolio_subject_display_snapshot",
        "portfolio_subject_identity_decision",
        "portfolio",
        "portfolio_profile_binding",
    )
    assert observe_state_revision(workspace) == before_revision


def test_existing_portfolio_is_reported_as_warning_not_reused(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = SubjectIds()
    created = create_portfolio_subject(
        workspace,
        _ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=ids,
    )
    profile = _install_improvement(workspace)
    portfolio = create_portfolio(
        workspace,
        portfolio_subject_id=created.subject_ids[0],
        created_by=ACTOR,
        expected_state_revision=observe_state_revision(workspace),
        title_snapshot="Existing Portfolio",
        id_factory=ids,
    )

    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("english10_p2"),
            purpose_kind="improvement",
            profile_revision=profile,
        ),
        id_factory=ids,
    )

    assert plan.ready
    assert plan.subject_action == "reuse_existing"
    assert plan.proposed_ids.portfolio_id != portfolio.portfolio.portfolio_id
    assert [item.portfolio_id for item in plan.existing_portfolios] == [
        portfolio.portfolio.portfolio_id
    ]


def test_profile_choices_are_exact_bindable_and_purpose_filtered(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    ids = ProfileIds()
    improvement = _install_improvement(workspace, ids=ids)
    showcase = _install_showcase(workspace, ids=ids)

    improvement_choices = list_portfolio_setup_profiles(
        workspace,
        purpose_kind="improvement",
    )
    showcase_choices = list_portfolio_setup_profiles(
        workspace,
        purpose_kind="showcase",
    )

    assert [item.reference for item in improvement_choices] == [improvement]
    assert [item.reference for item in showcase_choices] == [showcase]


def test_planner_uses_exact_roster_school_year_for_profile_applicability(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    profile = _install_improvement(
        workspace,
        applicability=ProfileApplicability(school_years=("2026-2027",)),
    )
    created = create_portfolio_subject(
        workspace,
        _ref("english10_p2"),
        context=teacher_context(),
        expected_state_revision=observe_state_revision(workspace),
        id_factory=SubjectIds(),
    )

    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("english10_p2"),
            purpose_kind="improvement",
            profile_revision=profile,
            profile_context=ProfileBindingContext(),
        ),
        id_factory=SubjectIds(),
    )

    assert plan.ready
    assert plan.portfolio_subject_id == created.subject_ids[0]
    assert plan.effective_profile_context.school_year == "2026-2027"


def test_missing_profile_is_explained_without_starter_auto_install(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    before = observe_state_revision(workspace)

    plan = plan_create_portfolio_for_student(
        workspace,
        CreatePortfolioForStudentRequest(
            student_reference=_ref("english10_p2"),
            purpose_kind="showcase",
            subject_action="create_new",
            identity_context=teacher_context(),
        ),
        id_factory=SubjectIds(),
    )

    assert "profile_unavailable" in plan.blocking_codes
    assert plan.profile_choices == ()
    assert observe_state_revision(workspace) == before
