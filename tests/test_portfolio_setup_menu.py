from __future__ import annotations

import io
from pathlib import Path

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
from tests.subject_helpers import make_subject_workspace, teacher_context
from vitrine.models import ClassQualifiedStudentRef
from vitrine.portfolio_services import create_portfolio, list_portfolios
from vitrine.portfolio_setup_menu import run_create_portfolio_for_student_menu
from vitrine.profile_services import (
    activate_profile_revision,
    create_profile_family,
    create_profile_revision,
    observe_profile_state_revision,
)
from vitrine.storage import load_current_state
from vitrine.subject_services import (
    create_portfolio_subject,
    observe_state_revision,
)


def _inputs(values: list[str]) -> object:
    iterator = iter(values)
    return lambda _prompt: next(iterator)


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
        reason="Approved for teacher setup menu.",
        authority_reference="local_instructional_policy",
        expected_state_revision=observe_profile_state_revision(workspace),
        clock=profile_clock,
        id_factory=ids,
    )


def _ref() -> ClassQualifiedStudentRef:
    return ClassQualifiedStudentRef(
        school_year="2026-2027",
        class_id="english10_p2",
        student_id="00107",
    )


def test_teacher_menu_creates_student_subject_portfolio_and_binding(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    _install_profile(workspace)
    monkeypatch.setattr(
        "vitrine.portfolio_setup_menu.list_linkable_classes",
        lambda _root: (("english10_p2", "2026-2027"),),
    )
    raw = _inputs(
        [
            "1",
            "1",
            "1",
            "1",
            "Same student selected from the current roster.",
            "C",
            "1",
            "1",
            "Jane Improvement Portfolio",
            "Teacher-guided setup.",
            "CREATE PORTFOLIO",
            "",
        ]
    )
    output = io.StringIO()
    before = load_current_state(workspace).state_revision

    result = run_create_portfolio_for_student_menu(
        workspace_root=workspace,
        input_fn=lambda prompt: raw(prompt),  # type: ignore[operator]
        output=output,
        clear_fn=lambda: None,
        actor=ACTOR,
    )

    assert result is None
    assert load_current_state(workspace).state_revision == before + 1
    portfolios = list_portfolios(workspace)
    assert len(portfolios) == 1
    assert portfolios[0].title_snapshot == "Jane Improvement Portfolio"
    rendered = output.getvalue()
    assert "Review Student Identity" in rendered
    assert rendered.index("Review Student Identity") < rendered.index(
        "Choose Improvement Profile"
    )
    assert "Review Portfolio Setup" in rendered
    assert "Existing Portfolios" in rendered
    assert "portfolio_subject" in rendered
    assert "portfolio_profile_binding" in rendered
    assert "Candidate discovery/review can now be started explicitly." in rendered


def test_existing_portfolio_can_be_opened_without_creating_another(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    subject = create_portfolio_subject(
        workspace,
        _ref(),
        context=teacher_context(),
        expected_state_revision=None,
        id_factory=SubjectIds(),
    )
    _install_profile(workspace)
    existing = create_portfolio(
        workspace,
        portfolio_subject_id=subject.subject_ids[0],
        created_by=ACTOR,
        expected_state_revision=observe_state_revision(workspace),
        title_snapshot="Existing Student Portfolio",
    )
    monkeypatch.setattr(
        "vitrine.portfolio_setup_menu.list_linkable_classes",
        lambda _root: (("english10_p2", "2026-2027"),),
    )
    raw = _inputs(
        [
            "1",
            "1",
            "1",
            "1",
        ]
    )
    before = load_current_state(workspace).state_revision

    result = run_create_portfolio_for_student_menu(
        workspace_root=workspace,
        input_fn=lambda prompt: raw(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
        actor=ACTOR,
    )

    assert result == existing.portfolio.portfolio_id
    assert load_current_state(workspace).state_revision == before
    assert len(list_portfolios(workspace)) == 1


def test_no_bindable_profile_stops_without_creating_subject(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = make_subject_workspace(tmp_path)
    monkeypatch.setattr(
        "vitrine.portfolio_setup_menu.list_linkable_classes",
        lambda _root: (("english10_p2", "2026-2027"),),
    )
    raw = _inputs(
        [
            "1",
            "1",
            "1",
            "1",
            "Teacher confirmed identity.",
            "C",
            "1",
            "",
        ]
    )

    result = run_create_portfolio_for_student_menu(
        workspace_root=workspace,
        input_fn=lambda prompt: raw(prompt),  # type: ignore[operator]
        output=io.StringIO(),
        clear_fn=lambda: None,
        actor=ACTOR,
    )

    assert result is None
    assert observe_state_revision(workspace) is None
