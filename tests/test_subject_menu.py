from __future__ import annotations

import io
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from pds_core.menu_navigation import QuitPDS, ReturnToMainMenu

from tests.subject_helpers import make_subject_workspace
from vitrine.subject_menu import run_subject_menu
from vitrine.subject_services import SubjectWorkflowError, list_subjects


def scripted_input(values: list[str]) -> Callable[[str], str]:
    iterator: Iterator[str] = iter(values)
    return lambda _prompt: next(iterator)


class ScreenRecorder:
    def __init__(self) -> None:
        self.output = io.StringIO()
        self.offsets: list[int] = []

    def clear(self) -> None:
        self.offsets.append(self.output.tell())

    def screens(self) -> tuple[str, ...]:
        text = self.output.getvalue()
        starts = self.offsets
        if not starts:
            return (text,)
        result: list[str] = []
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else len(text)
            result.append(text[start:end])
        return tuple(result)


def test_subject_menu_help_back_main_and_quit() -> None:
    output = io.StringIO()
    run_subject_menu(
        input_fn=scripted_input(["h", "", "b"]),
        output=output,
        clear_fn=lambda: None,
    )
    assert "Portfolio Subject Help" in output.getvalue()
    assert "B. Back" in output.getvalue()
    assert "M. Main Menu" in output.getvalue()
    assert "Q. Quit" in output.getvalue()

    with pytest.raises(ReturnToMainMenu):
        run_subject_menu(
            input_fn=scripted_input(["m"]),
            output=io.StringIO(),
            clear_fn=lambda: None,
        )
    with pytest.raises(QuitPDS):
        run_subject_menu(
            input_fn=scripted_input(["q"]),
            output=io.StringIO(),
            clear_fn=lambda: None,
        )


def test_subject_menu_dispatches_all_six_workflows(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []
    names = (
        "_create_subject_workflow",
        "_link_subject_workflow",
        "_view_subject_workflow",
        "_correct_link_workflow",
        "_merge_workflow",
        "_split_workflow",
    )
    for name in names:
        monkeypatch.setattr(
            f"vitrine.subject_menu.{name}",
            lambda *args, _name=name, **kwargs: called.append(_name),
        )
    for index, name in enumerate(names, start=1):
        run_subject_menu(
            input_fn=scripted_input([str(index), "b"]),
            output=io.StringIO(),
            clear_fn=lambda: None,
        )
        assert called[-1] == name


def test_create_cancellation_at_class_selection_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = make_subject_workspace(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))
    run_subject_menu(
        input_fn=scripted_input(["1", "b", "b"]),
        output=io.StringIO(),
        clear_fn=lambda: None,
    )
    assert list_subjects(workspace) == ()


def test_create_flow_clears_roster_before_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = make_subject_workspace(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))
    recorder = ScreenRecorder()
    # Classes are sorted: csp_p1, english10_p2, math_p3.
    run_subject_menu(
        input_fn=scripted_input(
            [
                "1",  # create
                "2",  # english10_p2
                "1",  # Jane Doe / 00107
                "teacher_1",
                "1",  # direct teacher knowledge
                "I teach this student.",
                "CREATE",
                "",  # success pause
                "b",
            ]
        ),
        output=recorder.output,
        clear_fn=recorder.clear,
    )
    subjects = list_subjects(workspace)
    assert len(subjects) == 1
    assert subjects[0].display_name == "Jay Doe"

    confirmation = next(
        screen for screen in recorder.screens() if screen.startswith("Create Portfolio Subject\n")
    )
    assert "Student: Jane Doe" in confirmation
    assert "Student ID: 00107" in confirmation
    assert "Select Student" not in confirmation
    assert "Smith, Alex" not in confirmation
    assert "1. Doe, Jane" not in confirmation


def test_expected_subject_error_is_concise_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise SubjectWorkflowError("state_conflict", "Vitrine state changed.")

    monkeypatch.setattr("vitrine.subject_menu._create_subject_workflow", fail)
    output = io.StringIO()
    run_subject_menu(
        input_fn=scripted_input(["1", "", "b"]),
        output=output,
        clear_fn=lambda: None,
    )
    text = output.getvalue()
    assert "Subject problem [state_conflict]: Vitrine state changed." in text
    assert "Traceback" not in text


def test_link_flow_requires_explicit_selected_class_and_student(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.subject_helpers import DeterministicIds, fixed_clock, teacher_context
    from vitrine.models import ClassQualifiedStudentRef
    from vitrine.subject_services import create_portfolio_subject, show_subject

    workspace = make_subject_workspace(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))
    seeded = create_portfolio_subject(
        workspace,
        ClassQualifiedStudentRef(class_id="english10_p2", student_id="00107", school_year="2026-2027"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    recorder = ScreenRecorder()
    run_subject_menu(
        input_fn=scripted_input(
            [
                "2",  # link another class
                "1",  # only active subject
                "1",  # csp_p1
                "1",  # exact 00107 row
                "teacher_1",
                "1",
                "I know these class records are the same student.",
                "LINK",
                "",
                "b",
            ]
        ),
        output=recorder.output,
        clear_fn=recorder.clear,
    )
    detail = show_subject(workspace, seeded.subject_ids[0])
    assert {item.reference.class_id for item in detail.current_links} == {
        "english10_p2",
        "csp_p1",
    }
    confirmation = next(
        screen
        for screen in recorder.screens()
        if screen.startswith("Confirm Cross-Class Link\n")
    )
    assert "Student ID: 00107" in confirmation
    assert "Names or matching IDs did not create this association." in confirmation
    assert "00999" not in confirmation
    assert "Select Student" not in confirmation


def test_invalidate_link_menu_preserves_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.subject_helpers import DeterministicIds, fixed_clock, teacher_context
    from vitrine.models import ClassQualifiedStudentRef
    from vitrine.subject_services import create_portfolio_subject, show_subject

    workspace = make_subject_workspace(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))
    seeded = create_portfolio_subject(
        workspace,
        ClassQualifiedStudentRef(class_id="english10_p2", student_id="00107", school_year="2026-2027"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    run_subject_menu(
        input_fn=scripted_input(
            [
                "4",  # correct/invalidate
                "1",  # subject
                "1",  # only link
                "2",  # invalidate
                "teacher_1",
                "1",
                "The original confirmation was wrong.",
                "INVALIDATE",
                "",
                "b",
            ]
        ),
        output=io.StringIO(),
        clear_fn=lambda: None,
    )
    detail = show_subject(workspace, seeded.subject_ids[0])
    assert detail.current_links == ()
    assert len(detail.historical_links) == 1
    assert detail.historical_links[0].status == "invalidated"


def test_merge_menu_creates_successor_without_rewriting_predecessors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.subject_helpers import DeterministicIds, fixed_clock, teacher_context
    from vitrine.models import ClassQualifiedStudentRef
    from vitrine.subject_services import create_portfolio_subject

    workspace = make_subject_workspace(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))
    ids = DeterministicIds()
    first = create_portfolio_subject(
        workspace,
        ClassQualifiedStudentRef(class_id="english10_p2", student_id="00107", school_year="2026-2027"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    create_portfolio_subject(
        workspace,
        ClassQualifiedStudentRef(class_id="math_p3", student_id="00107", school_year="2026-2027"),
        context=teacher_context(),
        expected_state_revision=first.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    recorder = ScreenRecorder()
    run_subject_menu(
        input_fn=scripted_input(
            [
                "5",
                "1,2",
                "teacher_1",
                "1",
                "I confirm these Subjects represent one person.",
                "MERGE",
                "",
                "b",
            ]
        ),
        output=recorder.output,
        clear_fn=recorder.clear,
    )
    summaries = list_subjects(workspace)
    assert sum(item.status == "merged" for item in summaries) == 2
    assert sum(item.status == "active" for item in summaries) == 1
    confirmation = next(
        screen
        for screen in recorder.screens()
        if screen.startswith("Merge Portfolio Subjects\n")
        and "Affected existing Portfolios" in screen
    )
    assert "Select two or more numbers" not in confirmation


def test_split_menu_requires_explicit_link_allocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.subject_helpers import DeterministicIds, fixed_clock, teacher_context
    from vitrine.models import ClassQualifiedStudentRef
    from vitrine.subject_services import (
        create_portfolio_subject,
        link_portfolio_subject,
    )

    workspace = make_subject_workspace(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(workspace))
    ids = DeterministicIds()
    first = create_portfolio_subject(
        workspace,
        ClassQualifiedStudentRef(class_id="english10_p2", student_id="00107", school_year="2026-2027"),
        context=teacher_context(),
        expected_state_revision=None,
        clock=fixed_clock,
        id_factory=ids,
    )
    link_portfolio_subject(
        workspace,
        first.subject_ids[0],
        ClassQualifiedStudentRef(class_id="csp_p1", student_id="00107", school_year="2026-2027"),
        context=teacher_context(),
        expected_state_revision=first.commit.state_revision,
        clock=fixed_clock,
        id_factory=ids,
    )
    run_subject_menu(
        input_fn=scripted_input(
            [
                "6",
                "1",  # subject
                "2",  # two successors
                "1",  # first exact link -> successor 1
                "2",  # second exact link -> successor 2
                "teacher_1",
                "1",
                "These class links belong to different people.",
                "SPLIT",
                "",
                "b",
            ]
        ),
        output=io.StringIO(),
        clear_fn=lambda: None,
    )
    summaries = list_subjects(workspace)
    assert sum(item.status == "split" for item in summaries) == 1
    assert sum(item.status == "active" for item in summaries) == 2
