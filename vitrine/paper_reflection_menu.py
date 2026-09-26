"""Portfolio-scoped teacher workflow for paper-native Student Reflection."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TextIO, TypeVar

from pds_core.menu_navigation import (
    NavigationChoice,
    parse_navigation_choice,
)
from pds_core.workspace import resolve_workspace_root

from vitrine.curation_services import CurationWorkflowError, _clock
from vitrine.menu_interactions import confirm_exact_phrase
from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import (
    ActorAttribution,
    CurationTargetRef,
    PortfolioReflection,
    PortfolioSelection,
    ReflectionAuthorshipConfirmation,
)
from vitrine.paper_reflection_authorship import (
    confirm_returned_paper_authorship,
    finalize_confirmed_paper_reflection,
)
from vitrine.paper_reflection_packet import (
    IssuedPaperReflectionPacket,
    issue_paper_reflection_packet,
    render_issued_paper_reflection_packet,
)
from vitrine.paper_reflection_review import (
    PaperReflectionReviewContext,
    PaperReflectionReviewError,
    PaperReflectionReviewOccurrence,
    acquire_paper_reflection_evidence_preview,
    prepare_paper_reflection_review_context,
    selected_occurrence_ids,
)
from vitrine.paper_reflection_workflow import (
    PaperReflectionRequirementStatus,
    PaperReflectionWorkflowView,
    build_paper_reflection_workflow_view,
)
from vitrine.teacher_presentation import (
    TeacherPortfolioOverview,
    TeacherSubjectLink,
    build_teacher_portfolio_overview,
)
from vitrine.workflow_context import VitrineWorkflowDependencies
from vitrine.workflow_views import (
    CandidateSummary,
    list_active_selections,
    list_candidate_summaries,
)

_ChoiceValue = TypeVar("_ChoiceValue")
PaperReflectionReviewLauncher = Callable[[Path], bool]


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _read(input_fn: InputFunction, prompt: str) -> str:
    try:
        return input_fn(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "B"


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


def _numbered_choice(
    value: str,
    choices: Sequence[_ChoiceValue],
) -> _ChoiceValue | NavigationChoice | None:
    navigation = _navigation(value)
    if navigation is not None:
        return navigation
    if not value.isdecimal():
        return None
    index = int(value)
    if index < 1 or index > len(choices):
        return None
    return choices[index - 1]


def _actor(
    actor: ActorAttribution | None,
    input_fn: InputFunction,
) -> ActorAttribution | None:
    if actor is not None:
        return actor
    actor_id = _read(input_fn, "Teacher/actor ID (B to cancel): ")
    if _navigation(actor_id) is NavigationChoice.BACK:
        return None
    if not actor_id:
        return None
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id=actor_id,
        owning_system="local",
        role_snapshot="teacher",
    )


def _default_launcher(path: Path) -> bool:
    return bool(webbrowser.open(path.resolve().as_uri(), new=2))


def _status_label(status: str) -> str:
    return {
        "not_issued": "Prompt not issued",
        "issued_awaiting_return": "Prompt issued — awaiting return",
        "returned_needs_review": "Returned paper needs review",
        "confirmed_needs_recording": "Authorship confirmed — recording incomplete",
        "recorded": "Reflection recorded — paper evidence preserved",
        "attention_required": "Needs teacher review",
    }[status]


def _render_requirement(
    output: TextIO,
    item: PaperReflectionRequirementStatus,
) -> None:
    _write(
        output,
        item.title,
        f"Requirement: {item.statement}",
        f"Status: {_status_label(item.status)}",
    )
    if item.prompt_snapshot is not None:
        _write(output, f"Prompt: {item.prompt_snapshot}")
    if item.issued_page_count:
        _write(
            output,
            f"Returned pages: {item.returned_page_count}/{item.issued_page_count}",
        )
    if item.rescan_choice_required:
        _write(
            output,
            "Returned paper includes multiple scan occurrences; "
            "an exact occurrence must be chosen during review.",
        )
    _write(output, item.explanation)


def _render_workflow(
    output: TextIO,
    view: PaperReflectionWorkflowView,
) -> None:
    _write(output, "Student Reflection", "")
    if not view.requirements:
        _write(output, "This Portfolio Profile has no Reflection requirement.")
        return
    for index, item in enumerate(view.requirements, 1):
        if index > 1:
            _write(output, "")
        _render_requirement(output, item)

    _write(
        output,
        "",
        "Paper is the primary Reflection workflow.",
        "Typed/manual Reflection remains a fallback in Candidate Review.",
    )


def _render_technical(
    output: TextIO,
    view: PaperReflectionWorkflowView,
) -> None:
    _write(
        output,
        "Student Reflection — Technical Details / Provenance",
        "",
        f"Observed Vitrine state revision: {view.observed_state_revision}",
        f"Portfolio ID: {view.portfolio_id}",
        f"Portfolio Subject ID: {view.portfolio_subject_id}",
        f"Profile Binding ID: {view.profile_binding_id}",
    )
    for item in view.requirements:
        _write(
            output,
            "",
            f"Requirement ID: {item.requirement_id}",
            f"Status: {item.status}",
            f"Issuance ID: {item.issuance_id or '(none)'}",
            f"Target count: {item.target_count}",
            f"Issued pages: {item.issued_page_count}",
            f"Returned page coverage: {item.returned_page_count}",
            f"Returned scan occurrences: {item.returned_occurrence_count}",
            "Authorship Confirmation ID: "
            f"{item.authorship_confirmation_id or '(none)'}",
            f"Reflection ID: {item.reflection_id or '(none)'}",
            "Reflection revision: "
            + (
                str(item.reflection_revision)
                if item.reflection_revision is not None
                else "(none)"
            ),
            f"Paper Finalization ID: {item.paper_finalization_id or '(none)'}",
        )


def _choose_requirement(
    values: tuple[PaperReflectionRequirementStatus, ...],
    *,
    input_fn: InputFunction,
    output: TextIO,
) -> PaperReflectionRequirementStatus | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    _write(output, "Choose the Reflection requirement:")
    for index, item in enumerate(values, 1):
        _write(output, f"{index}. {item.title} — {_status_label(item.status)}")
    selected = _numbered_choice(
        _read(input_fn, "Requirement number: "),
        values,
    )
    return (
        None
        if selected is None or isinstance(selected, NavigationChoice)
        else selected
    )


def _choose_subject_link(
    overview: TeacherPortfolioOverview,
    *,
    input_fn: InputFunction,
    output: TextIO,
) -> TeacherSubjectLink | None:
    links = overview.subject_links
    if not links:
        _write(
            output,
            "No exact current class-qualified student link is available.",
        )
        return None
    if len(links) == 1:
        link = links[0]
        _write(
            output,
            "Using the single current student/class link:",
            (
                f"{link.display_name or link.student_id} — "
                f"{link.class_id} — {link.school_year}"
            ),
        )
        return link
    _write(output, "Choose the exact student/class link for this paper:")
    for index, link in enumerate(links, 1):
        _write(
            output,
            (
                f"{index}. {link.display_name or link.student_id} — "
                f"{link.class_id} — {link.school_year}"
            ),
        )
    selected = _numbered_choice(
        _read(input_fn, "Student/class link number: "),
        links,
    )
    return (
        None
        if selected is None or isinstance(selected, NavigationChoice)
        else selected
    )


def _selection_label(
    selection: PortfolioSelection,
    candidates: dict[str, CandidateSummary],
) -> str:
    candidate = candidates.get(selection.candidate_id)
    if candidate is None:
        return f"Selected Portfolio evidence ({selection.candidate_id})"
    return candidate.display_snapshot


def _choose_targets(
    *,
    root: Path,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
) -> tuple[tuple[CurationTargetRef, ...], tuple[str, ...]] | None:
    selections = list_active_selections(root, portfolio_id)
    if not selections:
        _write(
            output,
            "No active curated Selections are available.",
            "Curate the Portfolio evidence before issuing this Reflection.",
        )
        return None
    candidates = {
        item.candidate_id: item
        for item in list_candidate_summaries(root, portfolio_id)
    }
    labels = tuple(
        _selection_label(selection, candidates)
        for selection in selections
    )
    _write(
        output,
        "Choose the exact curated evidence the student will reflect on.",
        "Enter one or more numbers separated by commas.",
    )
    for index, label in enumerate(labels, 1):
        _write(output, f"{index}. {label}")
    raw = _read(input_fn, "Target numbers: ")
    navigation = _navigation(raw)
    if navigation is not None:
        return None
    chosen_indexes: list[int] = []
    for token in raw.split(","):
        value = token.strip()
        if not value.isdecimal():
            _write(output, "Target choices must be comma-separated numbers.")
            return None
        index = int(value)
        if index < 1 or index > len(selections) or index in chosen_indexes:
            _write(output, "Target choice is unavailable or duplicated.")
            return None
        chosen_indexes.append(index)
    if not chosen_indexes:
        return None
    chosen = tuple(selections[index - 1] for index in chosen_indexes)
    chosen_labels = tuple(labels[index - 1] for index in chosen_indexes)
    targets = tuple(
        CurationTargetRef(
            target_kind="selection",
            target_id=selection.selection_id,
            semantic_role=f"comparison_item_{position}",
        )
        for position, selection in enumerate(chosen, 1)
    )
    return targets, chosen_labels


def _page_count(input_fn: InputFunction, output: TextIO) -> int | None:
    raw = _read(input_fn, "Response pages [1]: ")
    if not raw:
        return 1
    if not raw.isdecimal() or int(raw) < 1 or int(raw) > 10:
        _write(output, "Response pages must be a number from 1 through 10.")
        return None
    return int(raw)


def _render_issue_review(
    output: TextIO,
    *,
    overview: TeacherPortfolioOverview,
    requirement: PaperReflectionRequirementStatus,
    link: TeacherSubjectLink,
    target_labels: tuple[str, ...],
    prompt_id: str,
    prompt_version: str,
    prompt_snapshot: str,
    page_count: int,
) -> None:
    _write(
        output,
        "Prepare / Print Student Reflection",
        "",
        f"Student: {link.display_name or overview.subject_label or link.student_id}",
        f"Class: {link.class_id} — {link.school_year}",
        f"Requirement: {requirement.title}",
        "",
        "Exact curated targets",
    )
    for label in target_labels:
        _write(output, f"- {label}")
    _write(
        output,
        "",
        f"Prompt ID: {prompt_id}",
        f"Prompt version: {prompt_version}",
        f"Prompt: {prompt_snapshot}",
        f"Response pages: {page_count}",
        "",
        "Issuing freezes the prompt, exact targets, class-qualified student link,",
        "response-page identities, and PDS2 routing context.",
    )


def _report_packet(
    output: TextIO,
    packet: IssuedPaperReflectionPacket,
) -> None:
    _write(
        output,
        "Printable Student Reflection ready.",
        "",
        f"PDF: {packet.pdf_path}",
        f"Response pages: {len(packet.issuance.response_page_ids)}",
        f"PDS2 routes ready: {len(packet.registration_paths)}",
        "",
        "Print this PDF for the student. Returned scans route through normal PDS.",
    )


def _prepare_print_flow(
    *,
    root: Path,
    portfolio_id: str,
    view: PaperReflectionWorkflowView,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    requirement = _choose_requirement(
        tuple(item for item in view.requirements if item.status == "not_issued"),
        input_fn=input_fn,
        output=output,
    )
    if requirement is None:
        _write(output, "No unissued Reflection requirement is available.")
        _pause(input_fn)
        return

    overview = build_teacher_portfolio_overview(root, portfolio_id)
    link = _choose_subject_link(
        overview,
        input_fn=input_fn,
        output=output,
    )
    if link is None:
        _pause(input_fn)
        return

    selected = _choose_targets(
        root=root,
        portfolio_id=portfolio_id,
        input_fn=input_fn,
        output=output,
    )
    if selected is None:
        _pause(input_fn)
        return
    target_references, target_labels = selected

    prompt_id = _read(input_fn, "Prompt ID: ")
    prompt_version = _read(input_fn, "Prompt version [1]: ") or "1"
    prompt_snapshot = _read(input_fn, "Exact prompt shown to student: ")
    if not prompt_id or not prompt_snapshot:
        _write(output, "Prompt ID and prompt text are required.")
        _pause(input_fn)
        return
    page_count = _page_count(input_fn, output)
    if page_count is None:
        _pause(input_fn)
        return

    mutation_actor = _actor(actor, input_fn)
    if mutation_actor is None:
        return

    def render_review() -> None:
        _render_issue_review(
            output,
            overview=overview,
            requirement=requirement,
            link=link,
            target_labels=target_labels,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            prompt_snapshot=prompt_snapshot,
            page_count=page_count,
        )

    if not confirm_exact_phrase(
        expected_phrase="ISSUE REFLECTION",
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
        render_review=render_review,
    ):
        return

    packet = issue_paper_reflection_packet(
        root,
        portfolio_id=portfolio_id,
        reflection_requirement_id=requirement.requirement_id,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        prompt_snapshot=prompt_snapshot,
        subject_link_id=link.subject_link_id,
        issued_by=mutation_actor,
        target_scope=(
            "selection"
            if len(target_references) == 1
            else "comparison_set"
        ),
        target_references=target_references,
        page_count=page_count,
        expected_state_revision=view.observed_state_revision,
        authority_gate=dependencies.curation_authority_gate,
        student_display_name=link.display_name or overview.subject_label,
    )
    clear_fn()
    _report_packet(output, packet)
    _pause(input_fn)


def _reprint_flow(
    *,
    root: Path,
    portfolio_id: str,
    view: PaperReflectionWorkflowView,
    input_fn: InputFunction,
    output: TextIO,
) -> None:
    requirement = _choose_requirement(
        tuple(
            item
            for item in view.requirements
            if item.status == "issued_awaiting_return"
            and item.issuance_id is not None
        ),
        input_fn=input_fn,
        output=output,
    )
    if requirement is None or requirement.issuance_id is None:
        _write(output, "No issued Reflection is available to reprint.")
        _pause(input_fn)
        return
    overview = build_teacher_portfolio_overview(root, portfolio_id)
    packet = render_issued_paper_reflection_packet(
        root,
        issuance_id=requirement.issuance_id,
        expected_state_revision=view.observed_state_revision,
        student_display_name=overview.subject_label,
    )
    _report_packet(output, packet)
    _pause(input_fn)


def _occurrence_line(item: PaperReflectionReviewOccurrence) -> str:
    return (
        f"{item.source_filename} — received {item.intake_timestamp} — "
        f"scan {item.source_scan_id}"
    )


def _choose_returned_occurrences(
    context: PaperReflectionReviewContext,
    *,
    input_fn: InputFunction,
    output: TextIO,
) -> tuple[str, ...] | None:
    selected: list[str] = []
    for page in context.pages:
        _write(
            output,
            "",
            f"Returned page {page.logical_page_number} of {page.total_pages}",
        )
        if len(page.occurrences) == 1:
            occurrence = page.occurrences[0]
            _write(output, f"Using: {_occurrence_line(occurrence)}")
            selected.append(occurrence.returned_paper_evidence_id)
            continue
        _write(
            output,
            "Multiple routed scans exist for this page.",
            "Choose the exact occurrence to use; no rescan is selected automatically.",
        )
        for index, occurrence in enumerate(page.occurrences, 1):
            _write(output, f"{index}. {_occurrence_line(occurrence)}")
        choice = _numbered_choice(
            _read(input_fn, "Occurrence number: "),
            page.occurrences,
        )
        if choice is None or isinstance(choice, NavigationChoice):
            return None
        selected.append(choice.returned_paper_evidence_id)
    return selected_occurrence_ids(context, tuple(selected))


def _preview_returned_paper(
    context: PaperReflectionReviewContext,
    selected_evidence_ids: tuple[str, ...],
    *,
    input_fn: InputFunction,
    output: TextIO,
    launcher: PaperReflectionReviewLauncher,
) -> bool:
    by_id = {
        item.returned_paper_evidence_id: item
        for page in context.pages
        for item in page.occurrences
    }
    with TemporaryDirectory(prefix="pds-vitrine-reflection-review-") as temp_root:
        temp = Path(temp_root)
        for evidence_id in selected_evidence_ids:
            occurrence = by_id[evidence_id]
            preview = acquire_paper_reflection_evidence_preview(
                context,
                evidence_id,
            )
            path = temp / (
                f"reflection-page-{occurrence.logical_page_number:02d}"
                f"{preview.suffix}"
            )
            path.write_bytes(preview.content)
            try:
                opened = launcher(path)
            except Exception:
                opened = False
            if not opened:
                _write(
                    output,
                    "",
                    "The exact returned paper was verified, but the local viewer",
                    "could not be opened. Authorship confirmation was not recorded.",
                )
                return False
            _write(
                output,
                "",
                (
                    f"Opened returned page {occurrence.logical_page_number} "
                    f"of {occurrence.total_pages} in the local viewer."
                ),
                "Review the handwriting before continuing.",
            )
            _pause(input_fn)
    return True


def _render_authorship_review(
    output: TextIO,
    *,
    overview: TeacherPortfolioOverview,
    requirement: PaperReflectionRequirementStatus,
    context: PaperReflectionReviewContext,
    selected_evidence_ids: tuple[str, ...],
    mutation_actor: ActorAttribution,
) -> None:
    selected = {
        item.returned_paper_evidence_id: item
        for page in context.pages
        for item in page.occurrences
        if item.returned_paper_evidence_id in selected_evidence_ids
    }
    student = overview.subject_label or context.student_reference.student_id
    _write(
        output,
        "Confirm Returned Student Reflection",
        "",
        f"Student: {student}",
        (
            f"Class: {context.student_reference.class_id} — "
            f"{context.student_reference.school_year}"
        ),
        f"Requirement: {requirement.title}",
        f"Prompt: {context.prompt_snapshot}",
        "",
        "Exact curated targets",
    )
    for target in context.targets:
        _write(output, f"- {target.display_label}")
    _write(output, "", "Returned paper reviewed")
    for page in context.pages:
        evidence_id = selected_evidence_ids[page.logical_page_number - 1]
        occurrence = selected[evidence_id]
        _write(
            output,
            (
                f"- Page {page.logical_page_number}: "
                f"{occurrence.source_filename}"
            ),
        )
    _write(
        output,
        "",
        (
            f"This records {student} as the author of the returned Reflection."
        ),
        (
            f"{mutation_actor.actor_id} is recorded as the authorized adult "
            "who confirms/records the association, not as the author."
        ),
        "Routing identifies the issued response; it does not prove authorship.",
    )


def _one_confirmation(records: tuple[object, ...]) -> ReflectionAuthorshipConfirmation:
    values = tuple(
        item for item in records if isinstance(item, ReflectionAuthorshipConfirmation)
    )
    if len(values) != 1:
        raise RuntimeError(
            "Authorship confirmation mutation did not return one exact confirmation."
        )
    return values[0]


def _one_reflection(records: tuple[object, ...]) -> PortfolioReflection:
    values = tuple(
        item for item in records if isinstance(item, PortfolioReflection)
    )
    if len(values) != 1:
        raise RuntimeError(
            "Paper Reflection finalization did not return one exact Reflection."
        )
    return values[0]


def _review_returned_flow(
    *,
    root: Path,
    portfolio_id: str,
    view: PaperReflectionWorkflowView,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
    launcher: PaperReflectionReviewLauncher,
) -> None:
    requirement = _choose_requirement(
        tuple(
            item
            for item in view.requirements
            if item.status == "returned_needs_review"
            and item.issuance_id is not None
        ),
        input_fn=input_fn,
        output=output,
    )
    if requirement is None or requirement.issuance_id is None:
        _write(output, "No complete returned Reflection is available for review.")
        _pause(input_fn)
        return

    try:
        context = prepare_paper_reflection_review_context(
            root,
            portfolio_id=portfolio_id,
            issuance_id=requirement.issuance_id,
            expected_state_revision=view.observed_state_revision,
        )
        selected = _choose_returned_occurrences(
            context,
            input_fn=input_fn,
            output=output,
        )
        if selected is None:
            return
        if not _preview_returned_paper(
            context,
            selected,
            input_fn=input_fn,
            output=output,
            launcher=launcher,
        ):
            _pause(input_fn)
            return

        mutation_actor = _actor(actor, input_fn)
        if mutation_actor is None:
            return
        overview = build_teacher_portfolio_overview(root, portfolio_id)

        def render_review() -> None:
            _render_authorship_review(
                output,
                overview=overview,
                requirement=requirement,
                context=context,
                selected_evidence_ids=selected,
                mutation_actor=mutation_actor,
            )

        if not confirm_exact_phrase(
            expected_phrase="CONFIRM STUDENT AUTHOR",
            input_fn=input_fn,
            output=output,
            clear_fn=clear_fn,
            render_review=render_review,
        ):
            return

        confirmed = confirm_returned_paper_authorship(
            root,
            portfolio_id=portfolio_id,
            issuance_id=context.issuance_id,
            returned_paper_evidence_ids=selected,
            confirmed_by=mutation_actor,
            expected_state_revision=context.observed_state_revision,
            authority_gate=dependencies.curation_authority_gate,
            clock=_clock,
        )
        confirmation = _one_confirmation(confirmed.records)
        finalized = finalize_confirmed_paper_reflection(
            root,
            portfolio_id=portfolio_id,
            authorship_confirmation_id=confirmation.authorship_confirmation_id,
            recorded_by=mutation_actor,
            expected_state_revision=confirmed.state_revision,
            authority_gate=dependencies.curation_authority_gate,
            clock=_clock,
        )
        reflection = _one_reflection(finalized.records)
        clear_fn()
        _write(
            output,
            "Student Reflection recorded.",
            "",
            f"Student author: {overview.subject_label or reflection.author.actor_id}",
            f"Recorded by: {mutation_actor.actor_id}",
            f"Reflection revision: {reflection.reflection_revision}",
            "Original returned paper evidence remains preserved.",
        )
        _pause(input_fn)
    except (PaperReflectionReviewError, CurationWorkflowError, RuntimeError) as error:
        clear_fn()
        _write(
            output,
            "Returned Reflection review could not be completed safely.",
            str(error),
            "",
            "No automatic target, rescan, or student substitution was made.",
        )
        _pause(input_fn)


def _complete_recording_flow(
    *,
    root: Path,
    portfolio_id: str,
    view: PaperReflectionWorkflowView,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    requirement = _choose_requirement(
        tuple(
            item
            for item in view.requirements
            if item.status == "confirmed_needs_recording"
            and item.authorship_confirmation_id is not None
        ),
        input_fn=input_fn,
        output=output,
    )
    if (
        requirement is None
        or requirement.authorship_confirmation_id is None
    ):
        _write(output, "No confirmed Reflection is awaiting recording.")
        _pause(input_fn)
        return
    mutation_actor = _actor(actor, input_fn)
    if mutation_actor is None:
        return

    def render_review() -> None:
        _write(
            output,
            "Complete Student Reflection Recording",
            "",
            f"Requirement: {requirement.title}",
            f"Prompt: {requirement.prompt_snapshot or '(unavailable)'}",
            "",
            "Student authorship was already explicitly confirmed.",
            "This action creates the canonical Portfolio Reflection from that",
            "confirmed paper evidence; the teacher remains the recorder, not author.",
        )

    if not confirm_exact_phrase(
        expected_phrase="RECORD REFLECTION",
        input_fn=input_fn,
        output=output,
        clear_fn=clear_fn,
        render_review=render_review,
    ):
        return
    try:
        finalized = finalize_confirmed_paper_reflection(
            root,
            portfolio_id=portfolio_id,
            authorship_confirmation_id=requirement.authorship_confirmation_id,
            recorded_by=mutation_actor,
            expected_state_revision=view.observed_state_revision,
            authority_gate=dependencies.curation_authority_gate,
            clock=_clock,
        )
        reflection = _one_reflection(finalized.records)
        clear_fn()
        _write(
            output,
            "Student Reflection recorded.",
            "",
            f"Student author ID: {reflection.author.actor_id}",
            f"Recorded by: {mutation_actor.actor_id}",
            f"Reflection revision: {reflection.reflection_revision}",
            "Original returned paper evidence remains preserved.",
        )
        _pause(input_fn)
    except (CurationWorkflowError, RuntimeError) as error:
        clear_fn()
        _write(
            output,
            "Confirmed Reflection could not be recorded safely.",
            str(error),
        )
        _pause(input_fn)


def run_paper_reflection_menu(
    *,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    workspace_root: Path | None = None,
    actor: ActorAttribution | None = None,
    launcher: PaperReflectionReviewLauncher = _default_launcher,
) -> None:
    """Run the Portfolio-scoped paper-first Student Reflection workflow."""

    root = resolve_workspace_root(workspace_root)
    while True:
        view = build_paper_reflection_workflow_view(root, portfolio_id)
        clear_fn()
        _render_workflow(output, view)
        actions: list[str] = []
        if any(item.status == "not_issued" for item in view.requirements):
            actions.append("1. Prepare / print Reflection")
        if any(
            item.status == "issued_awaiting_return"
            for item in view.requirements
        ):
            actions.append("2. Reprint issued Reflection")
        if any(
            item.status == "returned_needs_review"
            for item in view.requirements
        ):
            actions.append("3. Review returned paper / confirm student author")
        if any(
            item.status == "confirmed_needs_recording"
            for item in view.requirements
        ):
            actions.append("4. Complete canonical Reflection recording")
        _write(
            output,
            "",
            *actions,
            "T. Technical details / provenance",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        choice = _read(input_fn, "Choice: ")
        if choice.casefold() == "t":
            clear_fn()
            _render_technical(output, view)
            _pause(input_fn)
            continue
        if choice == "1" and any(
            item.status == "not_issued" for item in view.requirements
        ):
            clear_fn()
            _prepare_print_flow(
                root=root,
                portfolio_id=portfolio_id,
                view=view,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
                dependencies=dependencies,
                actor=actor,
            )
            continue
        if choice == "2" and any(
            item.status == "issued_awaiting_return"
            for item in view.requirements
        ):
            clear_fn()
            _reprint_flow(
                root=root,
                portfolio_id=portfolio_id,
                view=view,
                input_fn=input_fn,
                output=output,
            )
            continue
        if choice == "3" and any(
            item.status == "returned_needs_review"
            for item in view.requirements
        ):
            clear_fn()
            _review_returned_flow(
                root=root,
                portfolio_id=portfolio_id,
                view=view,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
                dependencies=dependencies,
                actor=actor,
                launcher=launcher,
            )
            continue
        if choice == "4" and any(
            item.status == "confirmed_needs_recording"
            for item in view.requirements
        ):
            clear_fn()
            _complete_recording_flow(
                root=root,
                portfolio_id=portfolio_id,
                view=view,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
                dependencies=dependencies,
                actor=actor,
            )
            continue
        navigation = _navigation(choice)
        if navigation is not None:
            return
        _write(output, "That Student Reflection action is not available.")
        _pause(input_fn)


__all__ = [
    "PaperReflectionReviewLauncher",
    "run_paper_reflection_menu",
]
