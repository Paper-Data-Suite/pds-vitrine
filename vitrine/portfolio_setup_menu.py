"""Teacher-facing Create Portfolio for Student guided setup."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import TextIO, TypeVar

from pds_core.menu_navigation import NavigationChoice, parse_navigation_choice
from pds_core.rosters import StudentRecord

from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import ActorAttribution, ClassQualifiedStudentRef
from vitrine.portfolio_services import list_portfolios
from vitrine.portfolio_setup import (
    CreatePortfolioForStudentRequest,
    PortfolioSetupError,
    PortfolioSetupPlan,
    PortfolioSetupProfileChoice,
    create_portfolio_for_student,
    list_portfolio_setup_profiles,
    plan_create_portfolio_for_student,
    resolve_portfolio_setup_subject,
)
from vitrine.profile_services import (
    ProfileBindingContext,
    get_portfolio_profile_binding,
    get_profile_revision,
)
from vitrine.subject_services import (
    IdentityDecisionContext,
    SubjectLinkView,
    SubjectSummary,
    list_linkable_classes,
    list_roster_students,
    list_subjects,
    show_subject,
)

_Choice = TypeVar("_Choice")


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _read(input_fn: InputFunction, prompt: str) -> str:
    try:
        return input_fn(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "Q"


def _pause(input_fn: InputFunction) -> None:
    try:
        input_fn("Press Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        return


def _navigation(value: str) -> NavigationChoice | None:
    return parse_navigation_choice(
        value,
        allow_back=True,
        allow_main_menu=True,
        allow_quit=True,
    )


def _numbered(value: str, choices: Sequence[_Choice]) -> _Choice | None:
    if not value.isdecimal():
        return None
    index = int(value)
    if index < 1 or index > len(choices):
        return None
    return choices[index - 1]


def _show_help(
    output: TextIO,
    input_fn: InputFunction,
    clear_fn: ClearFunction,
) -> None:
    clear_fn()
    _write(
        output,
        "Create Portfolio for Student — Help",
        "",
        "Choose one exact Core class and roster student.",
        "School year + class ID + student ID is the exact roster identity.",
        "Matching names or repeated student IDs never link classes automatically.",
        "An unlinked student requires an explicit new-Subject or existing-Subject choice.",
        "Choose one exact activated Profile Revision; purpose does not install policy.",
        "Nothing is written until the final CREATE PORTFOLIO confirmation.",
        "Candidate discovery and evidence selection remain separate workflows.",
    )
    _pause(input_fn)


def _choose_class(
    root: Path,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> tuple[str, str] | None:
    while True:
        classes = list_linkable_classes(root)
        clear_fn()
        _write(output, "Create Portfolio for Student", "", "Select class")
        if not classes:
            _write(output, "", "No usable Core class rosters were found.")
            _pause(input_fn)
            return None
        for index, (class_id, school_year) in enumerate(classes, 1):
            _write(output, f"{index}. {class_id} ({school_year})")
        _write(output, "", "H. Help", "B. Back", "M. Main Menu", "Q. Quit")
        raw = _read(input_fn, "Choice: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        navigation = _navigation(raw)
        if navigation is NavigationChoice.BACK or not raw:
            return None
        selected = _numbered(raw, classes)
        if selected is not None:
            return selected
        _write(output, "That class number is not available.")
        _pause(input_fn)


def _choose_student(
    root: Path,
    class_id: str,
    school_year: str,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> StudentRecord | None:
    while True:
        students = list_roster_students(
            root,
            class_id=class_id,
            school_year=school_year,
        )
        clear_fn()
        _write(output, f"Select Student — {class_id}", "")
        if not students:
            _write(output, "No roster students are available.")
            _pause(input_fn)
            return None
        for index, student in enumerate(students, 1):
            preferred = student.extra_fields.get("preferred_name", "").strip()
            display_first = preferred or student.first_name
            _write(
                output,
                f"{index}. {student.last_name}, {display_first} "
                f"(ID {student.student_id})",
            )
        _write(output, "", "H. Help", "B. Back", "M. Main Menu", "Q. Quit")
        raw = _read(input_fn, "Choice: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        navigation = _navigation(raw)
        if navigation is NavigationChoice.BACK or not raw:
            return None
        selected = _numbered(raw, students)
        if selected is not None:
            return selected
        _write(output, "That student number is not available.")
        _pause(input_fn)


def _ensure_actor(
    actor: ActorAttribution | None,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> ActorAttribution | None:
    if actor is not None:
        return actor
    while True:
        clear_fn()
        _write(
            output,
            "Teacher Identity",
            "",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        raw = _read(input_fn, "Teacher identifier: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        navigation = _navigation(raw)
        if navigation is NavigationChoice.BACK or not raw:
            return None
        return ActorAttribution(
            actor_kind="authorized_adult",
            actor_id=raw,
            owning_system="local",
            role_snapshot="teacher",
        )


def _identity_context(
    actor: ActorAttribution,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> IdentityDecisionContext | None:
    choices = (
        ("direct_teacher_knowledge", "Direct teacher knowledge"),
        ("verified_sis_information", "Verified SIS information"),
        ("authorized_institutional_crosswalk", "Authorized institutional crosswalk"),
        ("student_confirmation", "Student confirmation"),
        ("other_authorized_basis", "Other authorized basis"),
    )
    while True:
        clear_fn()
        _write(output, "Confirm Student Identity", "")
        for index, (_, label) in enumerate(choices, 1):
            _write(output, f"{index}. {label}")
        _write(output, "", "H. Help", "B. Back", "M. Main Menu", "Q. Quit")
        raw = _read(input_fn, "Confirmation basis: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        navigation = _navigation(raw)
        if navigation is NavigationChoice.BACK or not raw:
            return None
        selected = _numbered(raw, choices)
        if selected is None:
            _write(output, "That confirmation basis is not available.")
            _pause(input_fn)
            continue
        summary = _read(input_fn, "Brief reason: ")
        if summary.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        navigation = _navigation(summary)
        if navigation is NavigationChoice.BACK or not summary:
            return None
        return IdentityDecisionContext(
            actor=actor,
            authority_source="local_teacher_workflow",
            basis_type=selected[0],
            basis_summary=summary,
        )


def _choose_existing_subject(
    root: Path,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> SubjectSummary | None:
    while True:
        subjects = tuple(
            item for item in list_subjects(root) if item.status == "active"
        )
        clear_fn()
        _write(output, "Link to Existing Portfolio Subject", "")
        if not subjects:
            _write(output, "No active Portfolio Subjects are available.")
            _pause(input_fn)
            return None
        for index, subject in enumerate(subjects, 1):
            _write(
                output,
                f"{index}. {subject.display_name or '(unnamed Subject)'}",
                f"   {subject.portfolio_subject_id}",
            )
        _write(
            output,
            "",
            "Names and repeated student IDs are display information only.",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        raw = _read(input_fn, "Subject number: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        navigation = _navigation(raw)
        if navigation is NavigationChoice.BACK or not raw:
            return None
        selected = _numbered(raw, subjects)
        if selected is not None:
            return selected
        _write(output, "That Subject number is not available.")
        _pause(input_fn)


def _choose_subject_action(
    root: Path,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> tuple[str, str | None] | None:
    while True:
        clear_fn()
        _write(
            output,
            "Student Is Not Yet Linked",
            "",
            "Vitrine will not match this student to another class automatically.",
            "",
            "1. Create a new Portfolio Subject",
            "2. Link to an existing Portfolio Subject",
            "",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        raw = _read(input_fn, "Choice: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        navigation = _navigation(raw)
        if navigation is NavigationChoice.BACK or not raw:
            return None
        if raw == "1":
            return ("create_new", None)
        if raw == "2":
            subject = _choose_existing_subject(
                root,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
            )
            if subject is None:
                continue
            return ("link_existing", subject.portfolio_subject_id)
        _write(output, "Please choose 1 or 2.")
        _pause(input_fn)


def _review_subject_identity_and_existing_portfolios(
    root: Path,
    *,
    reference: ClassQualifiedStudentRef,
    student: StudentRecord,
    subject_status: str,
    subject_ids: tuple[str, ...],
    subject_action: str | None,
    existing_subject_id: str | None,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> str | None:
    subject_id: str | None
    if subject_status == "resolved":
        subject_id = subject_ids[0]
        action_label = "reuse existing"
    elif subject_action == "link_existing":
        subject_id = existing_subject_id
        action_label = "add exact link to existing"
    else:
        subject_id = None
        action_label = "create new"

    current_links: tuple[SubjectLinkView, ...] = ()
    if subject_id is not None:
        current_links = show_subject(root, subject_id).current_links

    existing_portfolios = tuple(
        item
        for item in list_portfolios(root)
        if subject_id is not None and item.portfolio_subject_id == subject_id
    )

    while True:
        clear_fn()
        preferred = student.extra_fields.get("preferred_name", "").strip()
        display_first = preferred or student.first_name
        _write(
            output,
            "Review Student Identity",
            "",
            f"Student: {display_first} {student.last_name}",
            f"Exact roster reference: {reference.school_year} / "
            f"{reference.class_id} / {reference.student_id}",
            f"Subject action: {action_label}",
            f"Portfolio Subject: {subject_id or '(new Subject assigned at final plan)'}",
            "",
            "Resulting current/proposed class links",
        )
        already_linked = False
        for link in current_links:
            if link.reference == reference:
                already_linked = True
            _write(
                output,
                f"  current: {link.reference.school_year} / "
                f"{link.reference.class_id} / {link.reference.student_id}",
                f"    {link.display_name or '(no display snapshot)'} — "
                f"{link.current_resolution}",
            )
        if not already_linked:
            _write(
                output,
                f"  proposed: {reference.school_year} / "
                f"{reference.class_id} / {reference.student_id}",
                f"    {display_first} {student.last_name} — resolvable",
            )

        _write(output, "", "Existing Portfolios for resulting Subject")
        if existing_portfolios:
            for index, portfolio in enumerate(existing_portfolios, 1):
                binding = get_portfolio_profile_binding(root, portfolio.portfolio_id)
                if binding is None:
                    purpose = "(not bound)"
                    profile = "(not bound)"
                else:
                    revision = get_profile_revision(root, binding.profile_revision)
                    purpose = revision.purpose_kind
                    profile = (
                        f"{binding.profile_revision.portfolio_profile_id}:"
                        f"{binding.profile_revision.profile_revision}"
                    )
                _write(
                    output,
                    f"{index}. {portfolio.title_snapshot or '(untitled Portfolio)'}",
                    f"   {portfolio.portfolio_id}",
                    f"   Purpose: {purpose}",
                    f"   Profile: {profile}",
                )
            _write(
                output,
                "",
                "Choose an existing Portfolio number to open it,",
                "or C to continue creating another Portfolio.",
            )
        else:
            _write(output, "  (none)", "", "C. Continue setup")

        _write(output, "H. Help", "B. Back", "M. Main Menu", "Q. Quit")
        raw = _read(input_fn, "Choice: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        if raw.casefold() == "c":
            return ""
        navigation = _navigation(raw)
        if navigation is NavigationChoice.BACK or not raw:
            return None
        selected = _numbered(raw, existing_portfolios)
        if selected is not None:
            return selected.portfolio_id
        _write(output, "Choose an existing Portfolio number or C to continue.")
        _pause(input_fn)


def _choose_purpose(
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> str | None:
    while True:
        clear_fn()
        _write(
            output,
            "Choose Portfolio Purpose",
            "",
            "1. Improvement",
            "2. Showcase",
            "",
            "Purpose filters Profile choices; it does not install hidden policy.",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        raw = _read(input_fn, "Choice: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        navigation = _navigation(raw)
        if navigation is NavigationChoice.BACK or not raw:
            return None
        if raw == "1":
            return "improvement"
        if raw == "2":
            return "showcase"
        _write(output, "Please choose 1 or 2.")
        _pause(input_fn)


def _choose_profile(
    root: Path,
    purpose_kind: str,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> PortfolioSetupProfileChoice | None:
    while True:
        profiles = list_portfolio_setup_profiles(root, purpose_kind=purpose_kind)
        clear_fn()
        _write(output, f"Choose {purpose_kind.title()} Profile", "")
        if not profiles:
            _write(
                output,
                f"No bindable {purpose_kind.title()} Profile is currently available.",
                "Install or activate a Profile explicitly, then return to setup.",
                "A packaged starter is never installed automatically here.",
            )
            _pause(input_fn)
            return None
        for index, profile in enumerate(profiles, 1):
            sections = ", ".join(item.label for item in profile.sections)
            _write(
                output,
                f"{index}. {profile.label}",
                f"   {profile.reference.portfolio_profile_id}:"
                f"{profile.reference.profile_revision}",
                f"   Sections: {sections}",
                f"   Requirements: {profile.requirement_count}",
            )
            if profile.known_limitations:
                _write(output, f"   Limits: {'; '.join(profile.known_limitations)}")
        _write(output, "", "H. Help", "B. Back", "M. Main Menu", "Q. Quit")
        raw = _read(input_fn, "Profile number: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        navigation = _navigation(raw)
        if navigation is NavigationChoice.BACK or not raw:
            return None
        selected = _numbered(raw, profiles)
        if selected is not None:
            return selected
        _write(output, "That Profile number is not available.")
        _pause(input_fn)


def _profile_context(
    root: Path,
    profile: PortfolioSetupProfileChoice,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> ProfileBindingContext | None:
    revision = get_profile_revision(root, profile.reference)
    applicability = revision.applicability
    institution_id: str | None = None
    program_id: str | None = None
    content_area: str | None = None
    as_of: date | None = None

    if applicability.institution_id is not None:
        clear_fn()
        _write(
            output,
            "Profile Context — Institution",
            "",
            f"Required institution: {applicability.institution_id}",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        raw = _read(input_fn, "Institution ID: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            return _profile_context(
                root,
                profile,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
            )
        if _navigation(raw) is NavigationChoice.BACK or not raw:
            return None
        institution_id = raw

    if applicability.program_id is not None:
        clear_fn()
        _write(
            output,
            "Profile Context — Program",
            "",
            f"Required program: {applicability.program_id}",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        raw = _read(input_fn, "Program ID: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            return _profile_context(
                root,
                profile,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
            )
        if _navigation(raw) is NavigationChoice.BACK or not raw:
            return None
        program_id = raw

    if applicability.content_areas:
        clear_fn()
        _write(
            output,
            "Profile Context — Content Area",
            "",
            f"Allowed: {', '.join(applicability.content_areas)}",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        raw = _read(input_fn, "Content area: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            return _profile_context(
                root,
                profile,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
            )
        if _navigation(raw) is NavigationChoice.BACK or not raw:
            return None
        content_area = raw

    if (
        applicability.effective_from is not None
        or applicability.effective_through is not None
    ):
        while True:
            clear_fn()
            _write(
                output,
                "Profile Context — Date",
                "",
                f"Effective from: {applicability.effective_from or '(open)'}",
                f"Effective through: {applicability.effective_through or '(open)'}",
                "H. Help",
                "B. Back",
                "M. Main Menu",
                "Q. Quit",
            )
            raw = _read(input_fn, "As-of date YYYY-MM-DD: ")
            if raw.casefold() == "h":
                _show_help(output, input_fn, clear_fn)
                continue
            if _navigation(raw) is NavigationChoice.BACK or not raw:
                return None
            try:
                as_of = date.fromisoformat(raw)
            except ValueError:
                _write(output, "Enter a valid YYYY-MM-DD date.")
                _pause(input_fn)
                continue
            break

    return ProfileBindingContext(
        as_of=as_of,
        institution_id=institution_id,
        program_id=program_id,
        content_area=content_area,
    )


def _existing_portfolio_choice(
    plan: PortfolioSetupPlan,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> str | None:
    if not plan.existing_portfolios:
        return ""
    while True:
        clear_fn()
        _write(
            output,
            "Existing Portfolios for This Student",
            "",
            "Creating another Portfolio is allowed, but review the existing choices first.",
            "",
        )
        for index, item in enumerate(plan.existing_portfolios, 1):
            profile = (
                f"{item.profile_revision.portfolio_profile_id}:"
                f"{item.profile_revision.profile_revision}"
                if item.profile_revision is not None
                else "not bound"
            )
            _write(
                output,
                f"{index}. {item.title_snapshot or '(untitled Portfolio)'}",
                f"   {item.portfolio_id}",
                f"   Purpose: {item.purpose_kind or '(not bound)'}",
                f"   Profile: {profile}",
            )
        _write(
            output,
            "",
            "C. Continue creating another Portfolio",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        raw = _read(input_fn, "Choice: ")
        if raw.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        if raw.casefold() == "c":
            return ""
        navigation = _navigation(raw)
        if navigation is NavigationChoice.BACK or not raw:
            return None
        selected = _numbered(raw, plan.existing_portfolios)
        if selected is not None:
            return selected.portfolio_id
        _write(output, "Choose an existing Portfolio number or C to continue.")
        _pause(input_fn)


def _show_final_review(
    plan: PortfolioSetupPlan,
    *,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    clear_fn()
    student = plan.student
    profile = plan.selected_profile
    _write(output, "Review Portfolio Setup", "")
    if student is not None:
        _write(
            output,
            "Student",
            f"  {student.display_name}",
            f"  {student.reference.school_year} / {student.reference.class_id} / "
            f"{student.reference.student_id}",
            "",
        )
    _write(
        output,
        "Portfolio Subject",
        f"  Action: {plan.subject_action}",
        f"  Subject ID: {plan.portfolio_subject_id}",
    )
    for link in plan.resulting_links:
        _write(
            output,
            f"  {link.disposition}: {link.reference.school_year} / "
            f"{link.reference.class_id} / {link.reference.student_id}",
            f"    {link.display_name or '(no display snapshot)'} — "
            f"{link.source_resolution}",
        )
    _write(output, "", "Existing Portfolios")
    if plan.existing_portfolios:
        for item in plan.existing_portfolios:
            profile_reference = (
                f"{item.profile_revision.portfolio_profile_id}:"
                f"{item.profile_revision.profile_revision}"
                if item.profile_revision is not None
                else "(not bound)"
            )
            _write(
                output,
                f"  {item.title_snapshot or '(untitled Portfolio)'}",
                f"    ID: {item.portfolio_id}",
                f"    Purpose: {item.purpose_kind or '(not bound)'}",
                f"    Profile: {profile_reference}",
            )
    else:
        _write(output, "  (none)")

    _write(
        output,
        "",
        "Portfolio",
        f"  Title: {plan.request.title_snapshot or '(untitled)'}",
        f"  Description: {plan.request.description_snapshot or '(none)'}",
        "",
        "Purpose and Profile",
        f"  Purpose: {plan.request.purpose_kind}",
    )
    if profile is not None:
        _write(
            output,
            f"  Profile: {profile.label}",
            f"  Revision: {profile.reference.portfolio_profile_id}:"
            f"{profile.reference.profile_revision}",
            f"  Sections: {', '.join(item.label for item in profile.sections)}",
            f"  Requirements: {profile.requirement_count}",
        )
        if profile.known_limitations:
            _write(
                output,
                f"  Known limitations: {'; '.join(profile.known_limitations)}",
            )
    context = plan.effective_profile_context
    _write(
        output,
        f"  School year: {context.school_year or '(none)'}",
        f"  Institution: {context.institution_id or '(none)'}",
        f"  Program: {context.program_id or '(none)'}",
        f"  Content area: {context.content_area or '(none)'}",
        f"  As-of: {context.as_of or '(none)'}",
        "",
        "Planned durable records",
    )
    for record_type in plan.planned_record_kinds:
        _write(output, f"  - {record_type}")
    _write(
        output,
        "",
        "No Candidate discovery or evidence selection will run.",
        "H. Help",
        "B. Back",
        "M. Main Menu",
        "Q. Quit",
    )


def run_create_portfolio_for_student_menu(
    *,
    workspace_root: Path,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    actor: ActorAttribution | None = None,
) -> str | None:
    """Run guided setup; return an existing Portfolio ID when teacher opens one."""
    chosen_class = _choose_class(
        workspace_root,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if chosen_class is None:
        return None
    class_id, school_year = chosen_class
    student = _choose_student(
        workspace_root,
        class_id,
        school_year,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if student is None:
        return None

    reference = ClassQualifiedStudentRef(
        school_year=school_year,
        class_id=class_id,
        student_id=student.student_id,
    )
    resolution = resolve_portfolio_setup_subject(workspace_root, reference)
    if resolution.roster_status != "resolvable":
        clear_fn()
        _write(
            output,
            "Portfolio Setup Blocked",
            "",
            "The exact Core roster student is not currently resolvable.",
        )
        _pause(input_fn)
        return None
    if resolution.subject_status == "conflict":
        clear_fn()
        _write(
            output,
            "Portfolio Setup Blocked",
            "",
            "This exact roster reference has a Portfolio Subject identity conflict.",
            "Use Portfolio Subject merge/split/correction/invalidation workflows first.",
        )
        _pause(input_fn)
        return None

    subject_action: str | None = None
    existing_subject_id: str | None = None
    identity_context: IdentityDecisionContext | None = None

    mutation_actor = _ensure_actor(
        actor,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if mutation_actor is None:
        return None

    if resolution.subject_status == "unlinked":
        selected_action = _choose_subject_action(
            workspace_root,
            input_fn=input_fn,
            output=output,
            clear_fn=clear_fn,
        )
        if selected_action is None:
            return None
        subject_action, existing_subject_id = selected_action
        identity_context = _identity_context(
            mutation_actor,
            input_fn=input_fn,
            output=output,
            clear_fn=clear_fn,
        )
        if identity_context is None:
            return None

    existing_choice = _review_subject_identity_and_existing_portfolios(
        workspace_root,
        reference=reference,
        student=student,
        subject_status=resolution.subject_status,
        subject_ids=resolution.subject_ids,
        subject_action=subject_action,
        existing_subject_id=existing_subject_id,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if existing_choice is None:
        return None
    if existing_choice:
        return existing_choice

    purpose_kind = _choose_purpose(
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if purpose_kind is None:
        return None
    profile = _choose_profile(
        workspace_root,
        purpose_kind,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if profile is None:
        return None
    profile_context = _profile_context(
        workspace_root,
        profile,
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
    )
    if profile_context is None:
        return None

    clear_fn()
    _write(
        output,
        "Portfolio Details",
        "",
        "H. Help",
        "B. Back",
        "M. Main Menu",
        "Q. Quit",
    )
    title = _read(input_fn, "Title (optional): ")
    if title.casefold() == "h":
        _show_help(output, input_fn, clear_fn)
        return None
    if _navigation(title) is NavigationChoice.BACK:
        return None
    description = _read(input_fn, "Description (optional): ")
    if description.casefold() == "h":
        _show_help(output, input_fn, clear_fn)
        return None
    if _navigation(description) is NavigationChoice.BACK:
        return None

    request = CreatePortfolioForStudentRequest(
        student_reference=reference,
        purpose_kind=purpose_kind,
        profile_revision=profile.reference,
        profile_context=profile_context,
        subject_action=subject_action,
        existing_subject_id=existing_subject_id,
        identity_context=identity_context,
        title_snapshot=title or None,
        description_snapshot=description or None,
    )
    try:
        plan = plan_create_portfolio_for_student(workspace_root, request)
    except PortfolioSetupError as error:
        clear_fn()
        _write(output, "Portfolio Setup Blocked", "", f"{error.code}: {error}")
        _pause(input_fn)
        return None
    if not plan.ready:
        clear_fn()
        _write(
            output,
            "Portfolio Setup Blocked",
            "",
            *tuple(f"- {code}" for code in plan.blocking_codes),
            "",
            "No records were created.",
        )
        _pause(input_fn)
        return None

    while True:
        _show_final_review(plan, output=output, clear_fn=clear_fn)
        confirmation = _read(
            input_fn,
            "Type CREATE PORTFOLIO to create this exact setup: ",
        )
        if confirmation.casefold() == "h":
            _show_help(output, input_fn, clear_fn)
            continue
        navigation = _navigation(confirmation)
        if navigation is NavigationChoice.BACK or not confirmation:
            return None
        if confirmation != "CREATE PORTFOLIO":
            _write(output, "Setup canceled; no records were created.")
            _pause(input_fn)
            return None
        break

    try:
        result = create_portfolio_for_student(
            workspace_root,
            plan,
            actor=mutation_actor,
        )
    except PortfolioSetupError as error:
        clear_fn()
        _write(
            output,
            "Portfolio Setup Changed",
            "",
            f"{error.code}: {error}",
            "Nothing from this setup was partially created.",
            "Review the setup again.",
        )
        _pause(input_fn)
        return None

    clear_fn()
    _write(
        output,
        "Portfolio Created",
        "",
        f"Student: {plan.student.display_name if plan.student else reference.student_id}",
        f"Portfolio: {result.portfolio_id}",
        f"Purpose: {plan.request.purpose_kind}",
        f"Profile: {result.profile_revision.portfolio_profile_id}:"
        f"{result.profile_revision.profile_revision}",
        f"Profile Binding: {result.profile_binding_id}",
        "",
        "Candidate discovery/review can now be started explicitly.",
    )
    _pause(input_fn)
    return None


__all__ = ["run_create_portfolio_for_student_menu"]
