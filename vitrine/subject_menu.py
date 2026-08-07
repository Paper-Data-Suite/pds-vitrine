"""Low-density teacher-facing Portfolio Subject workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from pds_core.menu_navigation import (
    NavigationChoice,
    navigation_hint,
    parse_navigation_choice,
    print_navigation_options,
)
from pds_core.rosters import StudentRecord
from pds_core.workspace import resolve_workspace_root

from vitrine.models import ActorAttribution, ClassQualifiedStudentRef
from vitrine.storage import VitrineStorageError
from vitrine.subject_services import (
    IdentityDecisionContext,
    SubjectDetail,
    SubjectSummary,
    SubjectWorkflowError,
    correct_subject_link,
    create_portfolio_subject,
    invalidate_subject_link,
    link_portfolio_subject,
    list_linkable_classes,
    list_roster_students,
    list_subjects,
    merge_portfolio_subjects,
    observe_state_revision,
    show_subject,
    split_portfolio_subject,
)

from .menu_types import ClearFunction, InputFunction


@dataclass(slots=True)
class SubjectMenuSession:
    actor: ActorAttribution | None = None


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _read(input_fn: InputFunction, prompt: str) -> str:
    return input_fn(prompt).strip()


def _pause(input_fn: InputFunction) -> None:
    input_fn("Press Enter to continue...")


def _nav(output: TextIO) -> None:
    print_navigation_options(file=output)


def _navigation(value: str) -> NavigationChoice | None:
    return parse_navigation_choice(value)


def _show_help(output: TextIO, input_fn: InputFunction) -> None:
    _write(
        output,
        "Portfolio Subject Help",
        "",
        "A Portfolio Subject is Vitrine's local identity for one person.",
        "Each class link uses an exact school year, class ID, and student ID.",
        "Names and repeated student IDs never confirm cross-class identity.",
        "Merge and split preserve the previous Subjects and links.",
    )
    _pause(input_fn)


def _ensure_actor(
    session: SubjectMenuSession,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> ActorAttribution | None:
    if session.actor is not None:
        return session.actor
    clear_fn()
    _write(output, "Teacher Identity", "")
    _nav(output)
    _write(output, "")
    actor_id = _read(input_fn, "Teacher identifier: ")
    navigation = _navigation(actor_id)
    if not actor_id or navigation is NavigationChoice.BACK:
        return None
    try:
        session.actor = ActorAttribution(
            actor_kind="authorized_adult",
            actor_id=actor_id,
            owning_system="local",
            role_snapshot="teacher",
        )
    except ValueError as error:
        _write(output, "", f"Identity problem: {error}")
        _pause(input_fn)
        return None
    return session.actor


def _decision_context(
    session: SubjectMenuSession,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> IdentityDecisionContext | None:
    actor = _ensure_actor(
        session,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if actor is None:
        return None
    while True:
        clear_fn()
        _write(
            output,
            "Confirmation Basis",
            "",
            "1. Direct teacher knowledge",
            "2. Verified SIS information",
            "3. Authorized institutional crosswalk",
            "4. Student confirmation",
            "5. Other authorized basis",
        )
        _nav(output)
        _write(output, "")
        choice = _read(input_fn, "Choice: ")
        navigation = _navigation(choice)
        if navigation is NavigationChoice.BACK or not choice:
            return None
        basis = {
            "1": "direct_teacher_knowledge",
            "2": "verified_sis_information",
            "3": "authorized_institutional_crosswalk",
            "4": "student_confirmation",
            "5": "other_authorized_basis",
        }.get(choice)
        if basis is None:
            _write(output, navigation_hint())
            _pause(input_fn)
            continue
        clear_fn()
        _write(output, "Confirmation Basis", "")
        _nav(output)
        _write(output, "")
        summary = _read(input_fn, "Brief reason for this decision: ")
        navigation = _navigation(summary)
        if navigation is NavigationChoice.BACK or not summary:
            return None
        return IdentityDecisionContext(
            actor=actor,
            authority_source="local_teacher_workflow",
            basis_type=basis,
            basis_summary=summary,
        )


def _choose_class(
    workspace_root: Path,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> tuple[str, str] | None:
    classes = list_linkable_classes(workspace_root)
    clear_fn()
    _write(output, "Select Class", "")
    if not classes:
        _write(output, "No usable Core class rosters were found.")
        _pause(input_fn)
        return None
    for index, (class_id, school_year) in enumerate(classes, start=1):
        _write(output, f"{index}. {class_id} ({school_year})")
    _nav(output)
    _write(output, "")
    choice = _read(input_fn, "Choice: ")
    navigation = _navigation(choice)
    if not choice or navigation is NavigationChoice.BACK:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(classes):
        return classes[int(choice) - 1]
    _write(output, navigation_hint())
    _pause(input_fn)
    return None


def _choose_student(
    workspace_root: Path,
    class_id: str,
    school_year: str,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> StudentRecord | None:
    students = list_roster_students(
        workspace_root,
        class_id=class_id,
        school_year=school_year,
    )
    clear_fn()
    _write(output, f"Select Student — {class_id}", "")
    for index, student in enumerate(students, start=1):
        _write(
            output,
            f"{index}. {student.last_name}, {student.first_name} "
            f"(ID {student.student_id})",
        )
    _nav(output)
    _write(output, "")
    choice = _read(input_fn, "Choice: ")
    navigation = _navigation(choice)
    if not choice or navigation is NavigationChoice.BACK:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(students):
        return students[int(choice) - 1]
    _write(output, navigation_hint())
    _pause(input_fn)
    return None


def _choose_subject(
    workspace_root: Path,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    active_only: bool = False,
) -> SubjectSummary | None:
    subjects = tuple(
        item
        for item in list_subjects(workspace_root)
        if not active_only or item.status == "active"
    )
    clear_fn()
    _write(output, "Select Portfolio Subject", "")
    if not subjects:
        _write(output, "No matching Portfolio Subjects were found.")
        _pause(input_fn)
        return None
    for index, subject in enumerate(subjects, start=1):
        label = subject.display_name or "No display label"
        _write(output, f"{index}. {label} — {subject.portfolio_subject_id}")
    _nav(output)
    _write(output, "")
    choice = _read(input_fn, "Choice: ")
    navigation = _navigation(choice)
    if not choice or navigation is NavigationChoice.BACK:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(subjects):
        return subjects[int(choice) - 1]
    _write(output, navigation_hint())
    _pause(input_fn)
    return None


def _choose_subjects_for_merge(
    workspace_root: Path,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> tuple[SubjectSummary, ...] | None:
    subjects = tuple(item for item in list_subjects(workspace_root) if item.status == "active")
    clear_fn()
    _write(output, "Merge Portfolio Subjects", "")
    if len(subjects) < 2:
        _write(output, "At least two current Portfolio Subjects are required.")
        _pause(input_fn)
        return None
    for index, subject in enumerate(subjects, start=1):
        _write(
            output,
            f"{index}. {subject.display_name or 'No display label'} — "
            f"{subject.portfolio_subject_id}",
        )
    _nav(output)
    _write(output, "")
    raw = _read(input_fn, "Select two or more numbers, separated by commas: ")
    navigation = _navigation(raw)
    if not raw or navigation is NavigationChoice.BACK:
        return None
    try:
        indexes = tuple(dict.fromkeys(int(item.strip()) for item in raw.split(",")))
    except ValueError:
        indexes = ()
    if len(indexes) < 2 or any(index < 1 or index > len(subjects) for index in indexes):
        _write(output, "Select at least two valid Subject numbers.")
        _pause(input_fn)
        return None
    return tuple(subjects[index - 1] for index in indexes)


def _choose_current_link(
    detail: SubjectDetail,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> str | None:
    clear_fn()
    _write(output, "Select Current Link", "")
    if not detail.current_links:
        _write(output, "This Subject has no current class links.")
        _pause(input_fn)
        return None
    for index, link in enumerate(detail.current_links, start=1):
        ref = link.reference
        _write(
            output,
            f"{index}. {ref.school_year} — {ref.class_id} — ID {ref.student_id}",
        )
    _nav(output)
    _write(output, "")
    choice = _read(input_fn, "Choice: ")
    navigation = _navigation(choice)
    if not choice or navigation is NavigationChoice.BACK:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(detail.current_links):
        return detail.current_links[int(choice) - 1].subject_link_id
    _write(output, navigation_hint())
    _pause(input_fn)
    return None


def _confirm_word(
    word: str,
    *,
    input_fn: InputFunction,
) -> bool:
    response = _read(
        input_fn,
        f"Type {word} to continue, or press Enter to cancel: ",
    )
    if not response:
        return False
    navigation = _navigation(response)
    if navigation is NavigationChoice.BACK:
        return False
    return response.casefold() == word.casefold()


def _reference(class_id: str, school_year: str, student: StudentRecord) -> ClassQualifiedStudentRef:
    return ClassQualifiedStudentRef(
        school_year=school_year,
        class_id=class_id,
        student_id=student.student_id,
    )


def _show_success(
    output: TextIO,
    input_fn: InputFunction,
    clear_fn: ClearFunction,
    message: str,
) -> None:
    clear_fn()
    _write(output, message)
    _pause(input_fn)


def _create_subject_workflow(
    workspace_root: Path,
    session: SubjectMenuSession,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    expected = observe_state_revision(workspace_root)
    selected_class = _choose_class(
        workspace_root,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if selected_class is None:
        return
    class_id, school_year = selected_class
    student = _choose_student(
        workspace_root,
        class_id,
        school_year,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if student is None:
        return
    context = _decision_context(
        session,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if context is None:
        return
    clear_fn()
    _write(
        output,
        "Create Portfolio Subject",
        "",
        f"Student: {student.first_name} {student.last_name}",
        f"School year: {school_year}",
        f"Class: {class_id}",
        f"Student ID: {student.student_id}",
        "",
        "This confirms only local Vitrine identity; it grants no source access.",
        "",
    )
    if not _confirm_word("CREATE", input_fn=input_fn):
        return
    result = create_portfolio_subject(
        workspace_root,
        _reference(class_id, school_year, student),
        context=context,
        expected_state_revision=expected,
    )
    _show_success(
        output,
        input_fn,
        clear_fn,
        f"Created Portfolio Subject {result.subject_ids[0]}.",
    )


def _link_subject_workflow(
    workspace_root: Path,
    session: SubjectMenuSession,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    expected = observe_state_revision(workspace_root)
    subject = _choose_subject(
        workspace_root,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
        active_only=True,
    )
    if subject is None:
        return
    selected_class = _choose_class(
        workspace_root,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if selected_class is None:
        return
    class_id, school_year = selected_class
    student = _choose_student(
        workspace_root,
        class_id,
        school_year,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if student is None:
        return
    context = _decision_context(
        session,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if context is None:
        return
    clear_fn()
    _write(
        output,
        "Confirm Cross-Class Link",
        "",
        f"Portfolio Subject: {subject.display_name or subject.portfolio_subject_id}",
        f"School year: {school_year}",
        f"Class: {class_id}",
        f"Student: {student.first_name} {student.last_name}",
        f"Student ID: {student.student_id}",
        "",
        "Names or matching IDs did not create this association.",
        "This confirmation grants no source or disclosure access.",
        "",
    )
    if not _confirm_word("LINK", input_fn=input_fn):
        return
    result = link_portfolio_subject(
        workspace_root,
        subject.portfolio_subject_id,
        _reference(class_id, school_year, student),
        context=context,
        expected_state_revision=expected,
    )
    message = (
        "That exact class link already exists."
        if result.commit.no_op
        else "Cross-class link confirmed."
    )
    _show_success(output, input_fn, clear_fn, message)


def _view_subject_workflow(
    workspace_root: Path,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    subject = _choose_subject(
        workspace_root,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if subject is None:
        return
    detail = show_subject(workspace_root, subject.portfolio_subject_id)
    while True:
        clear_fn()
        _write(
            output,
            detail.summary.display_name or "Portfolio Subject",
            "",
            f"Subject ID: {detail.summary.portfolio_subject_id}",
            f"Status: {detail.summary.status}",
            f"Portfolios: {detail.summary.portfolio_count}",
            "",
            "Current class links:",
        )
        if detail.current_links:
            for link in detail.current_links:
                ref = link.reference
                _write(
                    output,
                    f"- {ref.school_year} / {ref.class_id} / ID {ref.student_id}",
                )
        else:
            _write(output, "- none")
        _write(
            output,
            "",
            f"Historical links: {len(detail.historical_links)}",
            "1. View historical links",
        )
        _nav(output)
        _write(output, "")
        choice = _read(input_fn, "Choice: ")
        navigation = _navigation(choice)
        if not choice or navigation is NavigationChoice.BACK:
            return
        if choice == "1":
            clear_fn()
            _write(output, "Historical Links", "")
            if not detail.historical_links:
                _write(output, "No historical links.")
            for link in detail.historical_links:
                ref = link.reference
                _write(
                    output,
                    f"- {ref.school_year} / {ref.class_id} / ID {ref.student_id} "
                    f"({link.status}; {link.current_resolution})",
                )
            _pause(input_fn)
            continue
        _write(output, navigation_hint())
        _pause(input_fn)


def _correct_link_workflow(
    workspace_root: Path,
    session: SubjectMenuSession,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    expected = observe_state_revision(workspace_root)
    subject = _choose_subject(
        workspace_root,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
        active_only=True,
    )
    if subject is None:
        return
    detail = show_subject(workspace_root, subject.portfolio_subject_id)
    link_id = _choose_current_link(
        detail,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if link_id is None:
        return
    clear_fn()
    _write(
        output,
        "Correct or Invalidate Link",
        "",
        "1. Replace with another exact roster reference",
        "2. Invalidate without replacement",
    )
    _nav(output)
    _write(output, "")
    choice = _read(input_fn, "Choice: ")
    navigation = _navigation(choice)
    if not choice or navigation is NavigationChoice.BACK:
        return
    if choice not in {"1", "2"}:
        _write(output, navigation_hint())
        _pause(input_fn)
        return
    context = _decision_context(
        session,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if context is None:
        return
    if choice == "2":
        clear_fn()
        _write(
            output,
            "Invalidate Link",
            "",
            f"Link ID: {link_id}",
            "The historical link will be preserved.",
            "",
        )
        if not _confirm_word("INVALIDATE", input_fn=input_fn):
            return
        invalidate_subject_link(
            workspace_root,
            link_id,
            context=context,
            expected_state_revision=expected,
        )
        _show_success(output, input_fn, clear_fn, "Link invalidated and preserved.")
        return
    selected_class = _choose_class(
        workspace_root,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if selected_class is None:
        return
    class_id, school_year = selected_class
    student = _choose_student(
        workspace_root,
        class_id,
        school_year,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if student is None:
        return
    clear_fn()
    _write(
        output,
        "Replace Subject Link",
        "",
        f"New class: {class_id} ({school_year})",
        f"New student: {student.first_name} {student.last_name}",
        f"New student ID: {student.student_id}",
        "Old link will remain in history.",
        "",
    )
    if not _confirm_word("REPLACE", input_fn=input_fn):
        return
    correct_subject_link(
        workspace_root,
        link_id,
        _reference(class_id, school_year, student),
        context=context,
        expected_state_revision=expected,
    )
    _show_success(output, input_fn, clear_fn, "Link replaced; history preserved.")


def _merge_workflow(
    workspace_root: Path,
    session: SubjectMenuSession,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    expected = observe_state_revision(workspace_root)
    selected = _choose_subjects_for_merge(
        workspace_root,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if selected is None:
        return
    details = tuple(
        show_subject(workspace_root, item.portfolio_subject_id)
        for item in selected
    )
    context = _decision_context(
        session,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if context is None:
        return
    clear_fn()
    _write(output, "Merge Portfolio Subjects", "")
    for detail in details:
        _write(
            output,
            detail.summary.display_name or detail.summary.portfolio_subject_id,
        )
        for link in detail.current_links:
            ref = link.reference
            _write(output, f"  {ref.school_year} / {ref.class_id} / ID {ref.student_id}")
    affected = sum(detail.summary.portfolio_count for detail in details)
    _write(
        output,
        "",
        f"Affected existing Portfolios: {affected}",
        "A new successor Subject will be created; predecessors stay historical.",
        "",
    )
    if not _confirm_word("MERGE", input_fn=input_fn):
        return
    result = merge_portfolio_subjects(
        workspace_root,
        tuple(item.portfolio_subject_id for item in selected),
        context=context,
        expected_state_revision=expected,
    )
    _show_success(
        output,
        input_fn,
        clear_fn,
        f"Created merged successor Subject {result.subject_ids[0]}.",
    )


def _split_workflow(
    workspace_root: Path,
    session: SubjectMenuSession,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    expected = observe_state_revision(workspace_root)
    subject = _choose_subject(
        workspace_root,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
        active_only=True,
    )
    if subject is None:
        return
    detail = show_subject(workspace_root, subject.portfolio_subject_id)
    if len(detail.current_links) < 2:
        clear_fn()
        _write(output, "Split Portfolio Subject", "", "At least two current links are required.")
        _pause(input_fn)
        return
    clear_fn()
    _write(output, "Split Portfolio Subject", "")
    count_raw = _read(input_fn, "Number of successor Subjects: ")
    navigation = _navigation(count_raw)
    if not count_raw or navigation is NavigationChoice.BACK:
        return
    if not count_raw.isdigit() or not 2 <= int(count_raw) <= len(detail.current_links):
        _write(output, "Choose a number from 2 through the current link count.")
        _pause(input_fn)
        return
    count = int(count_raw)
    groups: list[list[str]] = [[] for _ in range(count)]
    for link in detail.current_links:
        clear_fn()
        ref = link.reference
        _write(
            output,
            "Allocate Link",
            "",
            f"{ref.school_year} / {ref.class_id} / ID {ref.student_id}",
            "",
        )
        for index in range(1, count + 1):
            _write(output, f"{index}. Successor {index}")
        _nav(output)
        _write(output, "")
        choice = _read(input_fn, "Choice: ")
        navigation = _navigation(choice)
        if not choice or navigation is NavigationChoice.BACK:
            return
        if not choice.isdigit() or not 1 <= int(choice) <= count:
            _write(output, navigation_hint())
            _pause(input_fn)
            return
        groups[int(choice) - 1].append(link.subject_link_id)
    if any(not group for group in groups):
        clear_fn()
        _write(output, "Split Portfolio Subject", "", "Every successor must receive at least one link.")
        _pause(input_fn)
        return
    context = _decision_context(
        session,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if context is None:
        return
    link_by_id = {item.subject_link_id: item for item in detail.current_links}
    clear_fn()
    _write(output, "Confirm Split", "")
    for index, group in enumerate(groups, start=1):
        _write(output, f"Successor {index}:")
        for link_id in group:
            ref = link_by_id[link_id].reference
            _write(output, f"  {ref.school_year} / {ref.class_id} / ID {ref.student_id}")
    _write(
        output,
        "",
        f"Affected existing Portfolios: {detail.summary.portfolio_count}",
        "The predecessor Subject will remain historical.",
        "",
    )
    if not _confirm_word("SPLIT", input_fn=input_fn):
        return
    result = split_portfolio_subject(
        workspace_root,
        subject.portfolio_subject_id,
        groups,
        context=context,
        expected_state_revision=expected,
    )
    _show_success(
        output,
        input_fn,
        clear_fn,
        f"Created {len(result.subject_ids)} successor Portfolio Subjects.",
    )


def run_subject_menu(
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    """Run Portfolio Subject workflows with low-density screen transitions."""
    workspace_root = resolve_workspace_root()
    session = SubjectMenuSession()
    while True:
        clear_fn()
        _write(
            output,
            "Portfolio Subjects",
            "",
            "1. Create Portfolio Subject",
            "2. Link Another Class",
            "3. View Portfolio Subject",
            "4. Correct or Invalidate Link",
            "5. Merge Portfolio Subjects",
            "6. Split Portfolio Subject",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        choice = _read(input_fn, "Choice: ")
        if choice.casefold() == "h":
            clear_fn()
            _show_help(output, input_fn)
            continue
        navigation = _navigation(choice)
        if navigation is NavigationChoice.BACK:
            return
        try:
            if choice == "1":
                _create_subject_workflow(
                    workspace_root,
                    session,
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
            elif choice == "2":
                _link_subject_workflow(
                    workspace_root,
                    session,
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
            elif choice == "3":
                _view_subject_workflow(
                    workspace_root,
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
            elif choice == "4":
                _correct_link_workflow(
                    workspace_root,
                    session,
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
            elif choice == "5":
                _merge_workflow(
                    workspace_root,
                    session,
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
            elif choice == "6":
                _split_workflow(
                    workspace_root,
                    session,
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
            else:
                _write(output, "Please choose 1-6, H, B, M, or Q.")
                _pause(input_fn)
        except (SubjectWorkflowError, VitrineStorageError, ValueError, OSError) as error:
            clear_fn()
            code = getattr(error, "code", "subject_workflow_error")
            _write(output, f"Subject problem [{code}]: {error}")
            _pause(input_fn)


__all__ = ["SubjectMenuSession", "run_subject_menu"]
