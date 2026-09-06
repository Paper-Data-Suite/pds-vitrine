"""Read-only teacher Candidate inbox menu."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TextIO

from pds_core.menu_navigation import (
    NavigationChoice,
    parse_navigation_choice,
    print_navigation_options,
)
from pds_core.workspace import WorkspaceRootError, resolve_workspace_root

from vitrine.candidate_inbox import (
    CandidateInboxDetail,
    CandidateInboxError,
    CandidateInboxItem,
    CandidateInboxQuery,
    get_candidate_inbox_detail,
    list_candidate_inbox,
)
from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import CandidateSourceEndpoint


@dataclass(slots=True)
class CandidateInboxMenuFilters:
    portfolio_id: str | None = None
    evaluation_outcome: str | None = None
    attention_only: bool = False
    stale_only: bool = False
    selected_state: str | None = None

    def query(self) -> CandidateInboxQuery:
        outcomes = () if self.evaluation_outcome is None else (self.evaluation_outcome,)
        return CandidateInboxQuery(
            portfolio_id=self.portfolio_id,
            evaluation_outcomes=outcomes,
            attention_only=self.attention_only,
            stale_only=self.stale_only,
            selected_state=self.selected_state,
        )


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _read(input_fn: InputFunction, prompt: str) -> str:
    return input_fn(prompt).strip()


def _pause(input_fn: InputFunction) -> None:
    input_fn("Press Enter to continue...")


def _nav(value: str) -> NavigationChoice | None:
    return parse_navigation_choice(
        value,
        allow_back=True,
        allow_main_menu=True,
        allow_quit=True,
    )


def _label(value: str | None) -> str:
    if value is None:
        return "Unavailable"
    return value.replace("_", " ").title()


def _selection(item: CandidateInboxItem) -> str:
    if item.selected_state == "selected":
        return "Selected"
    if item.selected_state == "historical_only":
        return "Historical selection only"
    return "Not selected"


def _filter_summary(filters: CandidateInboxMenuFilters) -> str:
    values: list[str] = []
    if filters.portfolio_id:
        values.append(f"Portfolio={filters.portfolio_id}")
    if filters.evaluation_outcome:
        values.append(f"Outcome={filters.evaluation_outcome}")
    if filters.attention_only:
        values.append("Attention only")
    if filters.stale_only:
        values.append("Stale only")
    if filters.selected_state:
        values.append(f"Selection={filters.selected_state}")
    return "; ".join(values) or "none"


def _show_help(output: TextIO, input_fn: InputFunction) -> None:
    _write(
        output,
        "Candidate Inbox Help",
        "",
        "The inbox reviews persisted Candidate/Evaluation state only.",
        "Attention is a workflow signal, not an educational judgment.",
        "Stale means governing context changed; history is not rewritten.",
        "Suppressed Evaluations are not listed or counted.",
        "Use explicit Candidate discovery elsewhere to refresh source evidence.",
    )
    _pause(input_fn)


def _filter_menu(
    filters: CandidateInboxMenuFilters,
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    while True:
        clear_fn()
        _write(
            output,
            "Candidate Inbox Filters",
            "",
            f"Current: {_filter_summary(filters)}",
            "",
            "1. Portfolio ID",
            "2. Evaluation outcome",
            f"3. Attention only ({'on' if filters.attention_only else 'off'})",
            f"4. Stale only ({'on' if filters.stale_only else 'off'})",
            "5. Selection state",
            "6. Clear filters",
        )
        print_navigation_options(file=output)
        choice = _read(input_fn, "Choice: ")
        if choice.casefold() == "h":
            clear_fn()
            _show_help(output, input_fn)
            continue
        navigation = _nav(choice)
        if navigation is NavigationChoice.BACK:
            return
        if choice == "1":
            raw = _read(input_fn, "Portfolio ID (Enter to clear): ")
            if _nav(raw) is not NavigationChoice.BACK:
                filters.portfolio_id = raw or None
        elif choice == "2":
            raw = _read(
                input_fn,
                "Outcome (eligible/conditionally_eligible/ineligible/unresolved; Enter to clear): ",
            )
            if _nav(raw) is not NavigationChoice.BACK:
                filters.evaluation_outcome = raw or None
        elif choice == "3":
            filters.attention_only = not filters.attention_only
        elif choice == "4":
            filters.stale_only = not filters.stale_only
        elif choice == "5":
            raw = _read(
                input_fn,
                "Selection state (selected/unselected/historical_only; Enter to clear): ",
            )
            if _nav(raw) is not NavigationChoice.BACK:
                filters.selected_state = raw or None
        elif choice == "6":
            filters.portfolio_id = None
            filters.evaluation_outcome = None
            filters.attention_only = False
            filters.stale_only = False
            filters.selected_state = None
        else:
            _write(output, "That filter choice is not available.")
            _pause(input_fn)


def _endpoint(detail: CandidateInboxDetail) -> CandidateSourceEndpoint | None:
    if detail.evaluation is not None and detail.evaluation.source_endpoint is not None:
        return detail.evaluation.source_endpoint
    if detail.candidate is not None:
        return detail.candidate.source_endpoint
    return None


def _render_detail(output: TextIO, detail: CandidateInboxDetail) -> None:
    item = detail.item
    endpoint = _endpoint(detail)
    _write(
        output,
        "Candidate Inbox Detail",
        "",
        item.source_display_label,
        f"Entry: {item.entry_id}",
        f"Outcome: {_label(item.evaluation_outcome)}",
        f"Condition: {_label(item.candidate_condition)}",
        f"Currentness: {_label(item.stale_state)}",
        f"Stale reasons: {', '.join(item.stale_reason_codes) or '(none)'}",
        f"Attention needed: {'yes' if item.attention_needed else 'no'}",
        f"Attention reasons: {', '.join(item.attention_reason_codes) or '(none)'}",
        f"Selection: {_selection(item)}",
        f"Portfolio: {item.portfolio_label} ({item.portfolio_id})",
        f"Subject: {item.subject_label} ({item.portfolio_subject_id})",
        f"Profile Binding: {item.profile_binding_id}",
        f"Profile: {item.profile_label} ({item.portfolio_profile_id}@{item.profile_revision})",
        f"Current Candidate Evaluation: {item.current_evaluation_id or '(unresolved)'}",
        f"Current resolution: {item.current_resolution}",
    )
    if endpoint is None:
        _write(output, "Source provenance: (unavailable)")
    else:
        artifact = endpoint.source_artifact
        producer = endpoint.producer_source
        relationships = ", ".join(
            f"{x.relationship_kind}:{x.source_subject_kind}:{x.source_subject_id}"
            for x in endpoint.subject_relationship_assertions
        )
        _write(
            output,
            f"Core Publication: {endpoint.core_publication.publication_id}",
            f"Producer module: {producer.producer_module_id}",
            f"Producer source: {producer.source_record_kind}:{producer.source_record_id}",
            f"Producer native revision: {producer.native_revision or '(none)'}",
            f"Artifact: {artifact.artifact_id if artifact else '(none)'}",
            f"Subject relationships: {relationships or '(none)'}",
        )
    if endpoint is not None:
        publication = endpoint.core_publication
        producer = endpoint.producer_source
        artifact = endpoint.source_artifact
        _write(
            output,
            (
                "Core work: "
                f"{publication.work.module_id}:"
                f"{publication.work.class_id}:"
                f"{publication.work.work_id}"
            ),
            f"Publication kind: {publication.publication_kind}",
            f"Record set: {publication.record_set_id}@{publication.record_set_revision}",
            f"Manifest contract: {publication.manifest_contract_version}",
            f"Published at: {publication.published_at.isoformat()}",
            "Registration revision: "
            f"{publication.academic_work_registration_revision or '(none)'}",
            f"Observed series state: {publication.observed_series_state}",
            f"Observed withdrawal state: {publication.observed_withdrawal_state}",
            f"Producer lifecycle: {producer.native_lifecycle or '(none)'}",
            f"Producer disposition: {producer.native_disposition or '(none)'}",
            f"Producer lineage: {producer.lineage_reference or '(none)'}",
            f"Reader contract: {producer.reader_contract_version}",
            f"Projection contract: {producer.projection_contract_version}",
        )
        if artifact is not None:
            _write(output, f"Artifact media type: {artifact.media_type}")
    if detail.evaluation is not None:
        _write(
            output,
            "Matched Profile rules: "
            + (", ".join(detail.evaluation.matched_profile_rule_ids) or "(none)"),
        )

    if detail.evaluation is not None:
        evaluation = detail.evaluation
        availability = ", ".join(
            f"{x.dimension}={x.outcome}" for x in evaluation.availability_observations
        )
        _write(
            output,
            f"Evaluation reasons: {', '.join(evaluation.reason_codes) or '(none)'}",
            f"Availability: {availability or '(none)'}",
            f"Evaluator contract: {evaluation.evaluator_contract_version}",
        )
    _write(
        output,
        "Evaluation history: "
        + (
            ", ".join(x.candidate_evaluation_id for x in detail.evaluation_history)
            or "(none)"
        ),
        "Current-pointer history: "
        + (
            ", ".join(
                f"{x.pointer_revision}:{x.current_candidate_evaluation_id}"
                for x in detail.pointer_history
            )
            or "(none)"
        ),
        "",
        "Reviewing this entry does not discover, select, place, replace,",
        "approve, disclose, or otherwise mutate Portfolio state.",
    )


def run_candidate_inbox_menu(
    *,
    input_fn: InputFunction = input,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    """Browse current Candidate inbox state without mutations."""

    filters = CandidateInboxMenuFilters()
    while True:
        clear_fn()
        try:
            root = resolve_workspace_root()
            result = list_candidate_inbox(root, filters.query())
        except (WorkspaceRootError, CandidateInboxError, ValueError) as error:
            code = getattr(error, "code", error.__class__.__name__)
            _write(output, "Candidate Inbox", "", f"{code}: {error}", "")
            print_navigation_options(file=output)
            choice = _read(input_fn, "F for filters or navigation choice: ")
            if choice.casefold() == "h":
                clear_fn()
                _show_help(output, input_fn)
                continue
            if choice.casefold() == "f":
                _filter_menu(
                    filters,
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
                continue
            if _nav(choice) is NavigationChoice.BACK:
                return
            _pause(input_fn)
            continue

        _write(
            output,
            "Candidate Inbox",
            "",
            f"{result.matched_count} matching entr{'y' if result.matched_count == 1 else 'ies'}",
            f"Filters: {_filter_summary(filters)}",
            "",
        )
        for index, item in enumerate(result.items, start=1):
            markers: list[str] = []
            if item.attention_needed:
                markers.append("ATTENTION")
            if item.stale_state == "stale":
                markers.append("STALE")
            elif item.stale_state == "unresolved":
                markers.append("CURRENTNESS UNRESOLVED")
            marker = f" [{' / '.join(markers)}]" if markers else ""
            condition = (
                ""
                if item.candidate_condition is None
                else f" — {_label(item.candidate_condition)}"
            )
            _write(
                output,
                f"{index}. {item.source_display_label}{marker}",
                f"   {_label(item.evaluation_outcome)}{condition}; {_selection(item)}",
            )
        if not result.items:
            _write(output, "No visible Candidate inbox entries match.")
        _write(output, "", "F. Filters")
        print_navigation_options(file=output)
        choice = _read(input_fn, "Entry number, F, or navigation choice: ")
        if choice.casefold() == "h":
            clear_fn()
            _show_help(output, input_fn)
            continue
        if choice.casefold() == "f":
            _filter_menu(
                filters,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
            )
            continue
        if _nav(choice) is NavigationChoice.BACK:
            return
        if choice.isdecimal() and 1 <= int(choice) <= len(result.items):
            selected = result.items[int(choice) - 1]
            clear_fn()
            try:
                detail = get_candidate_inbox_detail(root, selected.entry_id)
            except CandidateInboxError as error:
                _write(output, f"{error.code}: {error}")
            else:
                _render_detail(output, detail)
            _pause(input_fn)
            continue
        _write(output, "That Candidate inbox choice is not available.")
        _pause(input_fn)


__all__ = ["CandidateInboxMenuFilters", "run_candidate_inbox_menu"]
