from __future__ import annotations

import io
from pathlib import Path

from tests.profile_helpers import (
    ACTOR,
    improvement_family,
    improvement_requirements,
    improvement_revision,
)
from tests.profile_helpers import DeterministicIds as ProfileIds
from tests.profile_helpers import fixed_clock as profile_clock
from tests.subject_helpers import DeterministicIds as SubjectIds
from tests.subject_helpers import make_subject_workspace, teacher_context
from vitrine.cli import main
from vitrine.models import ClassQualifiedStudentRef
from vitrine.portfolio_services import list_portfolios
from vitrine.profile_services import (
    activate_profile_revision,
    create_profile_family,
    create_profile_revision,
    get_portfolio_profile_binding,
    observe_profile_state_revision,
)
from vitrine.storage import load_current_records, load_current_state
from vitrine.subject_services import create_portfolio_subject


def _install_profile(workspace: Path) -> None:
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
        reason="Approved for CLI setup tests.",
        authority_reference="local_instructional_policy",
        expected_state_revision=observe_profile_state_revision(workspace),
        clock=profile_clock,
        id_factory=ids,
    )


def _ref(class_id: str = "english10_p2") -> ClassQualifiedStudentRef:
    return ClassQualifiedStudentRef(
        school_year="2026-2027",
        class_id=class_id,
        student_id="00107",
    )


def _base_args(workspace: Path) -> list[str]:
    return [
        "portfolio",
        "create-for-student",
        "--class-id",
        "english10_p2",
        "--school-year",
        "2026-2027",
        "--student-id",
        "00107",
        "--purpose",
        "improvement",
        "--profile-id",
        "profile_growth",
        "--profile-revision",
        "1",
        "--new-subject",
        "--identity-basis-type",
        "direct_teacher_knowledge",
        "--identity-basis-summary",
        "Teacher confirmed the exact roster student.",
        "--actor-id",
        "teacher_profile",
        "--workspace-root",
        str(workspace),
    ]


def test_create_for_student_dry_run_is_read_only(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    _install_profile(workspace)
    before_state = load_current_state(workspace).state_revision
    before_records = load_current_records(workspace)
    output = io.StringIO()
    error = io.StringIO()

    status = main(
        [*_base_args(workspace), "--title", "CLI Portfolio", "--dry-run"],
        output=output,
        error=error,
    )

    assert status == 0
    assert error.getvalue() == ""
    rendered = output.getvalue()
    assert "Create Portfolio for Student plan" in rendered
    assert "Ready: yes" in rendered
    assert "Mutation: dry-run only" in rendered
    assert "portfolio_subject" in rendered
    assert "portfolio_profile_binding" in rendered
    assert load_current_state(workspace).state_revision == before_state
    assert load_current_records(workspace) == before_records


def test_create_for_student_cli_commits_atomic_setup(tmp_path: Path) -> None:
    workspace = make_subject_workspace(tmp_path)
    _install_profile(workspace)
    before = load_current_state(workspace).state_revision
    output = io.StringIO()
    error = io.StringIO()

    status = main(
        [*_base_args(workspace), "--title", "CLI Portfolio"],
        output=output,
        error=error,
    )

    assert status == 0
    assert error.getvalue() == ""
    assert load_current_state(workspace).state_revision == before + 1
    portfolios = list_portfolios(workspace)
    assert len(portfolios) == 1
    assert portfolios[0].title_snapshot == "CLI Portfolio"
    binding = get_portfolio_profile_binding(workspace, portfolios[0].portfolio_id)
    assert binding is not None
    assert binding.profile_revision.portfolio_profile_id == "profile_growth"
    assert "Created Portfolio for Student:" in output.getvalue()


def test_repeated_student_id_requires_explicit_cross_class_subject_choice(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    create_portfolio_subject(
        workspace,
        _ref(),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=SubjectIds(),
    )
    _install_profile(workspace)
    before = load_current_state(workspace).state_revision
    output = io.StringIO()
    error = io.StringIO()

    status = main(
        [
            "portfolio",
            "create-for-student",
            "--class-id",
            "csp_p1",
            "--school-year",
            "2026-2027",
            "--student-id",
            "00107",
            "--purpose",
            "improvement",
            "--profile-id",
            "profile_growth",
            "--profile-revision",
            "1",
            "--actor-id",
            "teacher_profile",
            "--workspace-root",
            str(workspace),
        ],
        output=output,
        error=error,
    )

    assert status == 1
    assert "subject_choice_required" in error.getvalue()
    assert load_current_state(workspace).state_revision == before
    assert list_portfolios(workspace) == ()


def test_explicit_cross_class_cli_link_commits_to_chosen_subject(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    existing = create_portfolio_subject(
        workspace,
        _ref(),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=SubjectIds(),
    )
    _install_profile(workspace)
    before = load_current_state(workspace).state_revision
    output = io.StringIO()
    error = io.StringIO()

    status = main(
        [
            "portfolio",
            "create-for-student",
            "--class-id",
            "csp_p1",
            "--school-year",
            "2026-2027",
            "--student-id",
            "00107",
            "--purpose",
            "improvement",
            "--profile-id",
            "profile_growth",
            "--profile-revision",
            "1",
            "--existing-subject-id",
            existing.subject_ids[0],
            "--identity-basis-type",
            "direct_teacher_knowledge",
            "--identity-basis-summary",
            "Teacher confirmed the cross-class association.",
            "--actor-id",
            "teacher_profile",
            "--workspace-root",
            str(workspace),
        ],
        output=output,
        error=error,
    )

    assert status == 0
    assert error.getvalue() == ""
    assert load_current_state(workspace).state_revision == before + 1
    portfolios = list_portfolios(workspace)
    assert len(portfolios) == 1
    assert portfolios[0].portfolio_subject_id == existing.subject_ids[0]


def test_existing_primitive_portfolio_create_cli_remains_compatible(
    tmp_path: Path,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    subject = create_portfolio_subject(
        workspace,
        _ref(),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=SubjectIds(),
    )
    output = io.StringIO()
    error = io.StringIO()

    status = main(
        [
            "portfolio",
            "create",
            "--subject-id",
            subject.subject_ids[0],
            "--title",
            "Primitive Portfolio",
            "--actor-id",
            "teacher_profile",
            "--workspace-root",
            str(workspace),
        ],
        output=output,
        error=error,
    )

    assert status == 0
    assert error.getvalue() == ""
    portfolios = list_portfolios(workspace)
    assert len(portfolios) == 1
    assert portfolios[0].title_snapshot == "Primitive Portfolio"
    assert "Created Portfolio:" in output.getvalue()
