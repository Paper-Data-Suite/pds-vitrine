"""Teacher-facing guided Candidate review and Selection menu."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TextIO, TypeVar

from pds_core.menu_navigation import NavigationChoice, parse_navigation_choice

from vitrine.candidate_inbox import (
    CandidateInboxError,
    CandidateInboxItem,
    CandidateInboxQuery,
)
from vitrine.candidate_review import (
    CandidateReviewDetail,
    CandidateReviewError,
    CandidateReviewPlacementSummary,
    CandidateReviewProfileRequirementSummary,
    CandidateReviewSectionSummary,
    CandidateReviewSelectionSummary,
    execute_annotation_action,
    execute_candidate_decision,
    execute_curation_review,
    execute_reflection_action,
    execute_selection_placement,
    execute_selection_replacement,
    execute_selection_withdrawal,
    get_candidate_review_detail,
    list_candidate_review_entries,
    plan_annotation_creation,
    plan_annotation_revision,
    plan_candidate_decision,
    plan_curation_review,
    plan_reflection_creation,
    plan_reflection_revision,
    plan_selection_placement,
    plan_selection_replacement,
    plan_selection_withdrawal,
)
from vitrine.curation_services import CurationWorkflowError
from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import ActorAttribution, CurationTargetRef
from vitrine.workflow_context import VitrineWorkflowDependencies

_ChoiceValue = TypeVar("_ChoiceValue")

_ANNOTATION_PURPOSES = (
    "curator_context",
    "source_context",
    "comparison_note",
    "standards_context",
    "caption",
    "accessibility_description",
)
_REVIEW_DECISIONS = (
    "approved",
    "rejected",
    "changes_requested",
    "acknowledged",
    "waived",
)


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


def _numbered_many(
    value: str,
    choices: Sequence[_ChoiceValue],
) -> tuple[_ChoiceValue, ...] | NavigationChoice | None:
    navigation = _navigation(value)
    if navigation is not None:
        return navigation
    values = tuple(item.strip() for item in value.split(",") if item.strip())
    if not values or any(not item.isdecimal() for item in values):
        return None
    indexes = tuple(int(item) for item in values)
    if len(set(indexes)) != len(indexes):
        return None
    if any(index < 1 or index > len(choices) for index in indexes):
        return None
    return tuple(choices[index - 1] for index in indexes)


def _mutation_actor(
    actor: ActorAttribution | None,
    input_fn: InputFunction,
) -> ActorAttribution | None:
    if actor is not None:
        return actor
    actor_id = _read(input_fn, "Teacher/actor ID (B to cancel): ")
    if _navigation(actor_id) is NavigationChoice.BACK or not actor_id:
        return None
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id=actor_id,
        owning_system="local",
        role_snapshot="teacher",
    )


def _item_line(item: CandidateInboxItem) -> str:
    outcome = item.evaluation_outcome or "unavailable"
    condition = item.candidate_condition or "no_candidate"
    currentness = item.stale_state or "unavailable"
    attention = " | ATTENTION" if item.attention_needed else ""
    return (
        f"{item.source_display_label} | {outcome} | {condition} | "
        f"{currentness} | {item.selected_state}{attention}"
    )


def _query_for_category(portfolio_id: str, category: str) -> CandidateInboxQuery:
    if category == "1":
        return CandidateInboxQuery(
            portfolio_id=portfolio_id,
            attention_only=True,
            limit=100,
        )
    if category == "2":
        return CandidateInboxQuery(
            portfolio_id=portfolio_id,
            candidate_conditions=("ready_for_consideration",),
            limit=100,
        )
    if category in {"3", "6"}:
        return CandidateInboxQuery(
            portfolio_id=portfolio_id,
            selected_state="selected",
            limit=100,
        )
    if category == "4":
        return CandidateInboxQuery(
            portfolio_id=portfolio_id,
            evaluation_outcomes=("ineligible", "unresolved"),
            limit=100,
        )
    return CandidateInboxQuery(portfolio_id=portfolio_id, limit=100)


def _history_entries(
    root: Path,
    portfolio_id: str,
) -> tuple[CandidateInboxItem, ...]:
    result = list_candidate_review_entries(
        root,
        CandidateInboxQuery(portfolio_id=portfolio_id, limit=100),
    )
    values: list[CandidateInboxItem] = []
    for item in result.items:
        if item.candidate_id is None:
            continue
        detail = get_candidate_review_detail(root, item.entry_id)
        if any(selection.lifecycle_state != "activated" for selection in detail.selections):
            values.append(item)
    return tuple(values)


def _render_detail(output: TextIO, detail: CandidateReviewDetail) -> None:
    item = detail.inbox_detail.item
    source = detail.source
    _write(
        output,
        "Candidate Review",
        "",
        f"Source: {item.source_display_label}",
        f"Entry ID: {item.entry_id}",
        f"Candidate ID: {item.candidate_id or '(evaluation only)'}",
        f"Portfolio: {item.portfolio_label or item.portfolio_id}",
        f"Subject: {item.subject_label or item.portfolio_subject_id}",
        f"Profile: {item.profile_label} — {item.profile_purpose}",
        f"Profile Binding: {item.profile_binding_id}",
        f"Profile Revision: {item.portfolio_profile_id}:{item.profile_revision}",
        f"Evaluation outcome: {item.evaluation_outcome or '(none)'}",
        f"Candidate condition: {item.candidate_condition or '(none)'}",
        f"Currentness: {item.stale_state or '(none)'}",
        f"Stale reasons: {', '.join(item.stale_reason_codes) or '(none)'}",
        f"Attention reasons: {', '.join(item.attention_reason_codes) or '(none)'}",
        f"Selection state: {item.selected_state}",
        f"Current review Evaluation: {detail.current_review_evaluation_id or '(none)'}",
        "Curation provenance Evaluation: "
        f"{detail.curation_provenance_evaluation_id or '(none)'}",
        "",
    )
    if detail.current_evaluation_differs_from_curation_provenance:
        _write(
            output,
            "Current review Evaluation differs from immutable curation provenance.",
            "New curation does not retarget the Candidate or historical Selection history.",
            "",
        )
    if source is not None:
        _write(
            output,
            f"Core Publication: {source.core_publication_id}",
            "Publication state: "
            f"{source.observed_series_state} / {source.observed_withdrawal_state}",
            f"Producer module: {source.producer_module_id}",
            f"Producer source: {source.source_record_kind}:{source.source_record_id}",
            f"Producer native revision: {source.native_revision or '(none)'}",
            f"Artifact: {source.artifact_id or '(none)'}",
            "",
        )
    if detail.sections:
        _write(output, "Eligible sections")
        for index, section in enumerate(detail.sections, 1):
            maximum = (
                "unbounded"
                if section.maximum_placements is None
                else str(section.maximum_placements)
            )
            _write(
                output,
                f"{index}. {section.label} ({section.section_id})",
                "   "
                f"{section.obligation}; active {section.active_placement_count}; "
                f"maximum {maximum}; arrangement pointer "
                f"{section.arrangement_pointer_revision}",
            )
        _write(output, "")
    if detail.proposals:
        _write(output, "Selection Proposals")
        for proposal in detail.proposals:
            status = "undecided" if proposal.undecided else ", ".join(
                decision.decision for decision in proposal.decisions
            )
            _write(
                output,
                f"- {proposal.selection_proposal_id} — {status}",
                f"  sections: {', '.join(proposal.proposed_section_ids)}",
            )
        _write(output, "")
    if detail.selections:
        _write(output, "Selection history")
        for selection in detail.selections:
            _write(
                output,
                f"- {selection.selection_id} — {selection.lifecycle_state}",
                f"  Evaluation: {selection.candidate_evaluation_id}",
                "  active Placements: "
                f"{', '.join(selection.active_placement_ids) or '(none)'}",
            )
        _write(output, "")
    if not detail.selectable:
        _write(
            output,
            "This is an Evaluation-only inbox entry. It is reviewable but not selectable.",
            "No Candidate or rejected Selection Decision will be fabricated.",
        )


def _choose_sections(
    input_fn: InputFunction,
    output: TextIO,
    sections: Sequence[CandidateReviewSectionSummary],
    *,
    prompt: str,
) -> tuple[str, ...] | None:
    if not sections:
        _write(output, "No eligible sections are available.")
        return None
    for index, section in enumerate(sections, 1):
        _write(
            output,
            f"{index}. {section.label} ({section.section_id}) — "
            f"active {section.active_placement_count}",
        )
    raw = _read(input_fn, prompt)
    chosen = _numbered_many(raw, sections)
    if isinstance(chosen, NavigationChoice):
        return None
    if chosen is None:
        _write(output, "Those section numbers are not available.")
        return None
    return tuple(section.section_id for section in chosen)


def _choose_profile_requirements(
    input_fn: InputFunction,
    output: TextIO,
    requirements: Sequence[CandidateReviewProfileRequirementSummary],
) -> tuple[str, ...] | None:
    if not requirements:
        return ()
    _write(output, "Exact Profile requirements (optional)")
    for index, requirement in enumerate(requirements, 1):
        _write(
            output,
            f"{index}. {requirement.title} ({requirement.requirement_id}) — "
            f"{requirement.requirement_kind}",
        )
    raw = _read(
        input_fn,
        "Requirement numbers, comma-separated (Enter for none): ",
    )
    if not raw:
        return ()
    chosen = _numbered_many(raw, requirements)
    if isinstance(chosen, NavigationChoice):
        return None
    if chosen is None:
        _write(output, "Those Profile requirement numbers are not available.")
        return None
    return tuple(item.requirement_id for item in chosen)


def _render_decision_plan(output: TextIO, plan: object, rationale: str | None) -> None:
    _write(
        output,
        "Final Candidate Decision Review",
        "",
        f"Portfolio: {getattr(plan, 'portfolio_id')}",
        f"Candidate: {getattr(plan, 'candidate_id')}",
        "Current review Evaluation: "
        f"{getattr(plan, 'current_review_evaluation_id') or '(none)'}",
        "Curation provenance Evaluation: "
        f"{getattr(plan, 'curation_provenance_evaluation_id')}",
        f"Condition: {getattr(plan, 'candidate_condition')}",
        f"Stale state: {getattr(plan, 'stale_state') or '(none)'}",
        "Stale reasons: "
        f"{', '.join(getattr(plan, 'stale_reason_codes')) or '(none)'}",
        f"Decision: {getattr(plan, 'decision')}",
        f"Proposal: {getattr(plan, 'selection_proposal_id') or '(fresh)'}",
        f"Intended sections: {', '.join(getattr(plan, 'proposed_section_ids'))}",
        "Profile requirements: "
        f"{', '.join(getattr(plan, 'intended_profile_requirement_ids')) or '(none)'}",
        f"Rationale: {rationale or '(none)'}",
        f"Observed Vitrine state revision: {getattr(plan, 'observed_state_revision')}",
        "Placement is a separate explicit action.",
    )


def _decision_flow(
    *,
    root: Path,
    detail: CandidateReviewDetail,
    decision: str,
    selection_proposal_id: str | None,
    input_fn: InputFunction,
    output: TextIO,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    if selection_proposal_id is None:
        sections = _choose_sections(
            input_fn,
            output,
            detail.sections,
            prompt="Intended section numbers, comma-separated: ",
        )
        if sections is None:
            return
        requirements = _choose_profile_requirements(
            input_fn,
            output,
            detail.profile_requirements,
        )
        if requirements is None:
            return
    else:
        sections = ()
        requirements = ()
    plan = plan_candidate_decision(
        root,
        entry_id=detail.inbox_detail.item.entry_id,
        decision=decision,
        proposed_section_ids=sections,
        intended_profile_requirement_ids=requirements,
        selection_proposal_id=selection_proposal_id,
    )
    if plan.condition_acknowledgement_required:
        _write(
            output,
            "This Candidate has a non-ready condition.",
            "Acknowledging review does not clear the condition or grant authorization.",
        )
        if _read(input_fn, "Type ACKNOWLEDGE to continue reviewing this action: ") != "ACKNOWLEDGE":
            return
    rationale = _read(input_fn, "Rationale (optional): ") or None
    _render_decision_plan(output, plan, rationale)
    if _read(input_fn, f"Type {plan.confirmation_phrase} to confirm: ") != plan.confirmation_phrase:
        return
    mutation_actor = _mutation_actor(actor, input_fn)
    if mutation_actor is None:
        return
    result = execute_candidate_decision(
        root,
        plan,
        actor=mutation_actor,
        authority_gate=dependencies.curation_authority_gate,
        rationale_text=rationale,
    )
    _write(
        output,
        f"Candidate decision recorded at state revision {result.state_revision}.",
        "No Placement was created implicitly.",
    )


def _choose_active_selection(
    input_fn: InputFunction,
    output: TextIO,
    detail: CandidateReviewDetail,
) -> CandidateReviewSelectionSummary | None:
    selections = tuple(
        item for item in detail.selections if item.lifecycle_state == "activated"
    )
    if not selections:
        _write(output, "No active Selection is available.")
        return None
    for index, selection in enumerate(selections, 1):
        _write(
            output,
            f"{index}. {selection.selection_id} — Evaluation "
            f"{selection.candidate_evaluation_id}",
        )
    selected = _numbered_choice(_read(input_fn, "Active Selection number: "), selections)
    if selected is None or isinstance(selected, NavigationChoice):
        _write(output, "That active Selection number is not available.")
        return None
    return selected


def _placement_flow(
    *,
    root: Path,
    detail: CandidateReviewDetail,
    input_fn: InputFunction,
    output: TextIO,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    selection = _choose_active_selection(input_fn, output, detail)
    if selection is None:
        return
    section_ids = _choose_sections(
        input_fn,
        output,
        detail.sections,
        prompt="One exact section number for this Placement: ",
    )
    if section_ids is None or len(section_ids) != 1:
        if section_ids is not None:
            _write(output, "Placement requires exactly one section.")
        return
    plan = plan_selection_placement(
        root,
        entry_id=detail.inbox_detail.item.entry_id,
        selection_id=selection.selection_id,
        section_id=section_ids[0],
    )
    _write(
        output,
        "Final Placement Review",
        f"Selection: {plan.selection_id}",
        f"Section: {plan.section_label} ({plan.section_id})",
        f"Current active count: {plan.active_placement_count}",
        f"Maximum: {plan.maximum_placements if plan.maximum_placements is not None else 'unbounded'}",
        "Observed Arrangement pointer revision: "
        f"{plan.expected_arrangement_pointer_revision}",
        f"Observed Vitrine state revision: {plan.observed_state_revision}",
    )
    if _read(input_fn, f"Type {plan.confirmation_phrase} to confirm: ") != plan.confirmation_phrase:
        return
    mutation_actor = _mutation_actor(actor, input_fn)
    if mutation_actor is None:
        return
    result = execute_selection_placement(
        root,
        plan,
        placed_by=mutation_actor,
        authority_gate=dependencies.curation_authority_gate,
    )
    _write(output, f"Selection placed at state revision {result.state_revision}.")


def _withdrawal_flow(
    *,
    root: Path,
    detail: CandidateReviewDetail,
    input_fn: InputFunction,
    output: TextIO,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    selection = _choose_active_selection(input_fn, output, detail)
    if selection is None:
        return
    reason = _read(input_fn, "Withdrawal reason: ")
    if not reason:
        _write(output, "Withdrawal requires a reason.")
        return
    plan = plan_selection_withdrawal(
        root,
        entry_id=detail.inbox_detail.item.entry_id,
        selection_id=selection.selection_id,
        reason=reason,
    )
    _write(
        output,
        "Final Withdrawal Review",
        f"Selection: {plan.selection_id}",
        f"Candidate: {plan.candidate_id}",
        f"Selection Evaluation: {plan.selection_evaluation_id}",
        f"Active Placements: {', '.join(plan.active_placement_ids) or '(none)'}",
        f"Affected sections: {', '.join(plan.affected_section_ids) or '(none)'}",
        f"Reason: {plan.reason}",
        f"Observed Vitrine state revision: {plan.observed_state_revision}",
    )
    for pointer in plan.arrangement_pointers:
        _write(
            output,
            f"- {pointer.section_id}: Arrangement pointer {pointer.pointer_revision}",
        )
    if _read(input_fn, f"Type {plan.confirmation_phrase} to confirm: ") != plan.confirmation_phrase:
        return
    mutation_actor = _mutation_actor(actor, input_fn)
    if mutation_actor is None:
        return
    result = execute_selection_withdrawal(
        root,
        plan,
        withdrawn_by=mutation_actor,
        authority_gate=dependencies.curation_authority_gate,
    )
    _write(output, f"Selection withdrawn at state revision {result.state_revision}.")


def _successor_entries(
    root: Path,
    portfolio_id: str,
    candidate_id: str,
) -> tuple[CandidateInboxItem, ...]:
    result = list_candidate_review_entries(
        root,
        CandidateInboxQuery(portfolio_id=portfolio_id, limit=100),
    )
    return tuple(
        item
        for item in result.items
        if item.candidate_id is not None
        and item.candidate_id != candidate_id
        and item.selected_state != "selected"
    )


def _replacement_dispositions(
    *,
    input_fn: InputFunction,
    output: TextIO,
    placements: Sequence[CandidateReviewPlacementSummary],
    successor_sections: Sequence[CandidateReviewSectionSummary],
) -> dict[str, str | None] | None:
    dispositions: dict[str, str | None] = {}
    for placement in placements:
        _write(
            output,
            f"Placement {placement.placement_id} in {placement.section_label} "
            f"({placement.section_id})",
            "1. Drop this Placement",
        )
        for index, section in enumerate(successor_sections, 2):
            _write(
                output,
                f"{index}. Migrate explicitly to {section.label} ({section.section_id})",
            )
        raw = _read(input_fn, "Disposition number: ")
        if raw == "1":
            dispositions[placement.placement_id] = None
            continue
        if not raw.isdecimal():
            _write(output, "That Placement disposition is not available.")
            return None
        index = int(raw) - 2
        if index < 0 or index >= len(successor_sections):
            _write(output, "That Placement disposition is not available.")
            return None
        dispositions[placement.placement_id] = successor_sections[index].section_id
    return dispositions


def _replacement_flow(
    *,
    root: Path,
    detail: CandidateReviewDetail,
    input_fn: InputFunction,
    output: TextIO,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
    clear_fn: ClearFunction,
) -> None:
    selection = _choose_active_selection(input_fn, output, detail)
    candidate_id = detail.inbox_detail.item.candidate_id
    if selection is None or candidate_id is None:
        return
    successors = _successor_entries(
        root,
        detail.inbox_detail.item.portfolio_id,
        candidate_id,
    )
    if not successors:
        _write(output, "No other unselected positive Candidate is available.")
        return
    _write(output, "Choose exact successor Candidate")
    for index, item in enumerate(successors, 1):
        _write(output, f"{index}. {_item_line(item)}")
    successor_item = _numbered_choice(
        _read(input_fn, "Successor Candidate number: "),
        successors,
    )
    if successor_item is None or isinstance(successor_item, NavigationChoice):
        _write(output, "That successor Candidate number is not available.")
        return
    successor_detail = get_candidate_review_detail(root, successor_item.entry_id)
    clear_fn()
    _render_detail(output, successor_detail)
    proposed_sections = _choose_sections(
        input_fn,
        output,
        successor_detail.sections,
        prompt="Replacement Proposal section numbers, comma-separated: ",
    )
    if proposed_sections is None:
        return
    active_placements = tuple(
        item
        for item in detail.placements
        if item.selection_id == selection.selection_id
        and item.lifecycle_state == "activated"
    )
    dispositions = _replacement_dispositions(
        input_fn=input_fn,
        output=output,
        placements=active_placements,
        successor_sections=successor_detail.sections,
    )
    if dispositions is None:
        return
    reason = _read(input_fn, "Replacement reason: ")
    if not reason:
        _write(output, "Replacement requires a reason.")
        return
    plan = plan_selection_replacement(
        root,
        entry_id=detail.inbox_detail.item.entry_id,
        selection_id=selection.selection_id,
        successor_entry_id=successor_item.entry_id,
        proposed_section_ids=proposed_sections,
        placement_dispositions=dispositions,
        reason=reason,
    )
    _write(
        output,
        "Final Replacement Review",
        f"Old Selection: {plan.selection_id}",
        f"Old Candidate: {plan.candidate_id}",
        f"Successor Candidate: {plan.successor_candidate_id}",
        "Successor current review Evaluation: "
        f"{plan.successor_current_review_evaluation_id or '(none)'}",
        "Successor curation provenance Evaluation: "
        f"{plan.successor_curation_provenance_evaluation_id}",
        f"Successor condition: {plan.successor_candidate_condition}",
        f"Successor stale state: {plan.successor_stale_state or '(none)'}",
        f"Replacement Proposal sections: {', '.join(plan.proposed_section_ids)}",
        f"Reason: {plan.reason}",
        f"Observed Vitrine state revision: {plan.observed_state_revision}",
    )
    for disposition in plan.placement_dispositions:
        _write(
            output,
            f"- {disposition.placement_id}: {disposition.source_section_id} -> "
            f"{disposition.target_section_id or 'DROP'}",
        )
    for pointer in plan.arrangement_pointers:
        _write(
            output,
            f"- {pointer.section_id}: Arrangement pointer {pointer.pointer_revision}",
        )
    if _read(input_fn, f"Type {plan.confirmation_phrase} to confirm: ") != plan.confirmation_phrase:
        return
    mutation_actor = _mutation_actor(actor, input_fn)
    if mutation_actor is None:
        return
    result = execute_selection_replacement(
        root,
        plan,
        replaced_by=mutation_actor,
        authority_gate=dependencies.curation_authority_gate,
    )
    _write(output, f"Selection replaced at state revision {result.state_revision}.")


def _portfolio_selection_targets(
    root: Path,
    portfolio_id: str,
) -> tuple[tuple[str, CurationTargetRef], ...]:
    rows = list_candidate_review_entries(
        root,
        CandidateInboxQuery(portfolio_id=portfolio_id, limit=100),
    )
    seen: set[str] = set()
    values: list[tuple[str, CurationTargetRef]] = []
    for item in rows.items:
        if item.candidate_id is None:
            continue
        detail = get_candidate_review_detail(root, item.entry_id)
        for selection in detail.selections:
            if selection.selection_id in seen:
                continue
            seen.add(selection.selection_id)
            values.append(
                (
                    f"{item.source_display_label} — {selection.selection_id} — "
                    f"{selection.lifecycle_state}",
                    CurationTargetRef(
                        target_kind="selection",
                        target_id=selection.selection_id,
                    ),
                )
            )
    return tuple(values)


def _choose_target_scope(
    *,
    root: Path,
    detail: CandidateReviewDetail,
    input_fn: InputFunction,
    output: TextIO,
    reflection: bool,
) -> tuple[str, tuple[CurationTargetRef, ...]] | None:
    scopes = ["selection", "placement", "section", "comparison_set"]
    if reflection:
        scopes.append("portfolio")
    for index, scope in enumerate(scopes, 1):
        _write(output, f"{index}. {scope.replace('_', ' ').title()}")
    selected_scope = _numbered_choice(_read(input_fn, "Target scope number: "), scopes)
    if selected_scope is None or isinstance(selected_scope, NavigationChoice):
        _write(output, "That target scope is not available.")
        return None
    if selected_scope == "selection":
        selection_values = detail.selections
        for index, selection_item in enumerate(selection_values, 1):
            _write(
                output,
                f"{index}. {selection_item.selection_id} — "
                f"{selection_item.lifecycle_state}",
            )
        chosen_selection = _numbered_choice(
            _read(input_fn, "Selection number: "),
            selection_values,
        )
        if chosen_selection is None or isinstance(chosen_selection, NavigationChoice):
            return None
        return selected_scope, (
            CurationTargetRef(
                target_kind="selection",
                target_id=chosen_selection.selection_id,
            ),
        )
    if selected_scope == "placement":
        placement_values = detail.placements
        for index, placement_item in enumerate(placement_values, 1):
            _write(
                output,
                f"{index}. {placement_item.placement_id} — "
                f"{placement_item.section_label} — "
                f"{placement_item.lifecycle_state}",
            )
        chosen_placement = _numbered_choice(
            _read(input_fn, "Placement number: "),
            placement_values,
        )
        if chosen_placement is None or isinstance(chosen_placement, NavigationChoice):
            return None
        return selected_scope, (
            CurationTargetRef(
                target_kind="placement",
                target_id=chosen_placement.placement_id,
            ),
        )
    if selected_scope == "section":
        section_values = detail.sections
        for index, section_item in enumerate(section_values, 1):
            _write(
                output,
                f"{index}. {section_item.label} ({section_item.section_id})",
            )
        chosen_section = _numbered_choice(
            _read(input_fn, "Section number: "),
            section_values,
        )
        if chosen_section is None or isinstance(chosen_section, NavigationChoice):
            return None
        return selected_scope, (
            CurationTargetRef(
                target_kind="section",
                target_id=chosen_section.section_id,
            ),
        )
    if selected_scope == "portfolio":
        return selected_scope, (
            CurationTargetRef(
                target_kind="portfolio",
                target_id=detail.inbox_detail.item.portfolio_id,
            ),
        )
    selections = _portfolio_selection_targets(
        root,
        detail.inbox_detail.item.portfolio_id,
    )
    for index, (label, _) in enumerate(selections, 1):
        _write(output, f"{index}. {label}")
    selected_many = _numbered_many(
        _read(input_fn, "Two or more Selection numbers, comma-separated: "),
        selections,
    )
    if selected_many is None or isinstance(selected_many, NavigationChoice):
        _write(output, "Those comparison Selection numbers are not available.")
        return None
    if len(selected_many) < 2:
        _write(output, "Comparison requires at least two explicit Selections.")
        return None
    targets: list[CurationTargetRef] = []
    for _, target in selected_many:
        if reflection:
            role = _read(
                input_fn,
                f"Semantic role for Selection {target.target_id}: ",
            )
            if not role:
                _write(output, "Comparison Reflection roles must be explicit.")
                return None
            targets.append(
                CurationTargetRef(
                    target_kind="selection",
                    target_id=target.target_id,
                    semantic_role=role,
                )
            )
        else:
            targets.append(target)
    return selected_scope, tuple(targets)


def _render_targets(output: TextIO, targets: Sequence[CurationTargetRef]) -> None:
    for target in targets:
        suffix = (
            ""
            if target.target_revision is None
            else f" revision {target.target_revision}"
        )
        role = "" if target.semantic_role is None else f" role={target.semantic_role}"
        _write(
            output,
            f"- {target.target_kind}:{target.target_id}{suffix}{role}",
        )


def _annotation_flow(
    *,
    root: Path,
    detail: CandidateReviewDetail,
    input_fn: InputFunction,
    output: TextIO,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    _write(output, "Annotation", "", "1. Create Annotation", "2. Revise Annotation")
    action = _read(input_fn, "Annotation action: ")
    if action == "1":
        for index, purpose_option in enumerate(_ANNOTATION_PURPOSES, 1):
            _write(output, f"{index}. {purpose_option.replace('_', ' ').title()}")
        chosen_purpose = _numbered_choice(
            _read(input_fn, "Purpose number: "),
            _ANNOTATION_PURPOSES,
        )
        if chosen_purpose is None or isinstance(chosen_purpose, NavigationChoice):
            return
        target = _choose_target_scope(
            root=root,
            detail=detail,
            input_fn=input_fn,
            output=output,
            reflection=False,
        )
        if target is None:
            return
        scope, targets = target
        content = _read(input_fn, "Annotation text: ")
        plan = plan_annotation_creation(
            root,
            entry_id=detail.inbox_detail.item.entry_id,
            purpose=chosen_purpose,
            target_scope=scope,
            target_references=targets,
            content=content,
        )
    elif action == "2":
        if not detail.annotations:
            _write(output, "No Annotation revision is connected to this Candidate.")
            return
        for index, annotation_item in enumerate(detail.annotations, 1):
            _write(
                output,
                f"{index}. {annotation_item.annotation_id} revision "
                f"{annotation_item.annotation_revision} — {annotation_item.purpose}",
            )
        chosen_annotation = _numbered_choice(
            _read(input_fn, "Annotation revision number: "),
            detail.annotations,
        )
        if chosen_annotation is None or isinstance(chosen_annotation, NavigationChoice):
            return
        plan = plan_annotation_revision(
            root,
            entry_id=detail.inbox_detail.item.entry_id,
            annotation_id=chosen_annotation.annotation_id,
            content=_read(input_fn, "Replacement Annotation text: "),
        )
    else:
        return
    _write(
        output,
        "Final Annotation Review",
        f"Action: {plan.action}",
        f"Purpose: {plan.purpose}",
        f"Scope: {plan.target_scope}",
        f"Observed Vitrine state revision: {plan.observed_state_revision}",
    )
    _render_targets(output, plan.target_references)
    if _read(input_fn, f"Type {plan.confirmation_phrase} to confirm: ") != plan.confirmation_phrase:
        return
    mutation_actor = _mutation_actor(actor, input_fn)
    if mutation_actor is None:
        return
    result = execute_annotation_action(
        root,
        plan,
        author=mutation_actor,
        authority_gate=dependencies.curation_authority_gate,
    )
    _write(output, f"Annotation recorded at state revision {result.state_revision}.")


def _reflection_requirements(
    detail: CandidateReviewDetail,
) -> tuple[CandidateReviewProfileRequirementSummary, ...]:
    return tuple(
        item
        for item in detail.profile_requirements
        if item.requirement_kind == "reflection"
    )


def _reflection_flow(
    *,
    root: Path,
    detail: CandidateReviewDetail,
    input_fn: InputFunction,
    output: TextIO,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    _write(output, "Reflection", "", "1. Create Reflection", "2. Revise Reflection")
    action = _read(input_fn, "Reflection action: ")
    if action == "1":
        requirements = _reflection_requirements(detail)
        if not requirements:
            _write(output, "The exact bound Profile has no Reflection requirement.")
            return
        for index, requirement_item in enumerate(requirements, 1):
            _write(
                output,
                f"{index}. {requirement_item.title} "
                f"({requirement_item.requirement_id})",
            )
        chosen_requirement = _numbered_choice(
            _read(input_fn, "Reflection requirement number: "),
            requirements,
        )
        if chosen_requirement is None or isinstance(chosen_requirement, NavigationChoice):
            return
        target = _choose_target_scope(
            root=root,
            detail=detail,
            input_fn=input_fn,
            output=output,
            reflection=True,
        )
        if target is None:
            return
        scope, targets = target
        plan = plan_reflection_creation(
            root,
            entry_id=detail.inbox_detail.item.entry_id,
            reflection_requirement_id=chosen_requirement.requirement_id,
            prompt_id=_read(input_fn, "Prompt ID: "),
            prompt_version=_read(input_fn, "Prompt version: "),
            prompt_snapshot=_read(input_fn, "Prompt snapshot: "),
            target_scope=scope,
            target_references=targets,
            content=_read(input_fn, "Reflection text: "),
        )
    elif action == "2":
        if not detail.reflections:
            _write(output, "No Reflection revision is connected to this Candidate.")
            return
        for index, reflection_item in enumerate(detail.reflections, 1):
            _write(
                output,
                f"{index}. {reflection_item.reflection_id} revision "
                f"{reflection_item.reflection_revision} — "
                f"{reflection_item.reflection_requirement_id}",
            )
        chosen_reflection = _numbered_choice(
            _read(input_fn, "Reflection revision number: "),
            detail.reflections,
        )
        if chosen_reflection is None or isinstance(chosen_reflection, NavigationChoice):
            return
        plan = plan_reflection_revision(
            root,
            entry_id=detail.inbox_detail.item.entry_id,
            reflection_id=chosen_reflection.reflection_id,
            content=_read(input_fn, "Replacement Reflection text: "),
        )
    else:
        return
    _write(
        output,
        "Final Reflection Review",
        f"Action: {plan.action}",
        f"Requirement: {plan.reflection_requirement_id}",
        f"Prompt: {plan.prompt_id} / {plan.prompt_version}",
        f"Scope: {plan.target_scope}",
        f"Observed Vitrine state revision: {plan.observed_state_revision}",
        "Authorship is preserved from the explicit actor below; it is not inferred.",
    )
    _render_targets(output, plan.target_references)
    if _read(input_fn, f"Type {plan.confirmation_phrase} to confirm: ") != plan.confirmation_phrase:
        return
    mutation_actor = _mutation_actor(actor, input_fn)
    if mutation_actor is None:
        return
    result = execute_reflection_action(
        root,
        plan,
        author=mutation_actor,
        authority_gate=dependencies.curation_authority_gate,
    )
    _write(output, f"Reflection recorded at state revision {result.state_revision}.")


def _review_targets(
    detail: CandidateReviewDetail,
) -> tuple[tuple[str, str, CurationTargetRef], ...]:
    values: list[tuple[str, str, CurationTargetRef]] = []
    for annotation in detail.annotations:
        values.append(
            (
                f"Annotation {annotation.annotation_id} revision "
                f"{annotation.annotation_revision}",
                "annotation",
                CurationTargetRef(
                    target_kind="annotation",
                    target_id=annotation.annotation_id,
                    target_revision=annotation.annotation_revision,
                ),
            )
        )
    for reflection in detail.reflections:
        values.append(
            (
                f"Reflection {reflection.reflection_id} revision "
                f"{reflection.reflection_revision}",
                "reflection",
                CurationTargetRef(
                    target_kind="reflection",
                    target_id=reflection.reflection_id,
                    target_revision=reflection.reflection_revision,
                ),
            )
        )
    for selection in detail.selections:
        values.append(
            (
                f"Selection {selection.selection_id} — {selection.lifecycle_state}",
                "selection",
                CurationTargetRef(
                    target_kind="selection",
                    target_id=selection.selection_id,
                ),
            )
        )
    for placement in detail.placements:
        values.append(
            (
                f"Placement {placement.placement_id} — {placement.lifecycle_state}",
                "placement",
                CurationTargetRef(
                    target_kind="placement",
                    target_id=placement.placement_id,
                ),
            )
        )
    return tuple(values)


def _approval_requirements(
    detail: CandidateReviewDetail,
) -> tuple[CandidateReviewProfileRequirementSummary, ...]:
    return tuple(
        item for item in detail.profile_requirements if item.requirement_kind == "approval"
    )


def _review_flow(
    *,
    root: Path,
    detail: CandidateReviewDetail,
    input_fn: InputFunction,
    output: TextIO,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    targets = _review_targets(detail)
    if not targets:
        _write(output, "No exact curation target is available for Review.")
        return
    _write(output, "Curation Review targets")
    for index, (label, _, _) in enumerate(targets, 1):
        _write(output, f"{index}. {label}")
    chosen = _numbered_choice(_read(input_fn, "Review target number: "), targets)
    if chosen is None or isinstance(chosen, NavigationChoice):
        return
    _, scope, target = chosen
    for index, decision_option in enumerate(_REVIEW_DECISIONS, 1):
        _write(output, f"{index}. {decision_option.replace('_', ' ').title()}")
    chosen_decision = _numbered_choice(
        _read(input_fn, "Review decision number: "),
        _REVIEW_DECISIONS,
    )
    if chosen_decision is None or isinstance(chosen_decision, NavigationChoice):
        return
    approvals = _approval_requirements(detail)
    approval_requirement_id: str | None = None
    if approvals:
        _write(output, "0. Do not claim an approval requirement")
        for index, requirement in enumerate(approvals, 1):
            _write(
                output,
                f"{index}. {requirement.title} ({requirement.requirement_id})",
            )
        raw_approval = _read(input_fn, "Approval requirement number: ")
        if raw_approval != "0":
            approval = _numbered_choice(raw_approval, approvals)
            if approval is None or isinstance(approval, NavigationChoice):
                return
            approval_requirement_id = approval.requirement_id
    predecessor_review_decision_id: str | None = None
    if detail.reviews:
        _write(output, "0. No predecessor Review")
        for index, review in enumerate(detail.reviews, 1):
            _write(
                output,
                f"{index}. {review.curation_review_decision_id} — {review.decision}",
            )
        raw_predecessor = _read(input_fn, "Predecessor Review number: ")
        if raw_predecessor != "0":
            predecessor = _numbered_choice(raw_predecessor, detail.reviews)
            if predecessor is None or isinstance(predecessor, NavigationChoice):
                return
            predecessor_review_decision_id = predecessor.curation_review_decision_id
    follow_ups = tuple(
        item.strip()
        for item in _read(input_fn, "Required follow-up codes (comma-separated, optional): ").split(",")
        if item.strip()
    )
    reason = _read(input_fn, "Review reason: ")
    plan = plan_curation_review(
        root,
        entry_id=detail.inbox_detail.item.entry_id,
        target_scope=scope,
        target_references=(target,),
        decision=chosen_decision,
        reason=reason,
        approval_requirement_id=approval_requirement_id,
        required_follow_up_codes=follow_ups,
        predecessor_review_decision_id=predecessor_review_decision_id,
    )
    _write(
        output,
        "Final Curation Review",
        f"Decision: {plan.decision}",
        f"Approval requirement: {plan.approval_requirement_id or '(none)'}",
        f"Reason: {plan.reason}",
        f"Observed Vitrine state revision: {plan.observed_state_revision}",
        "Curation approval is not disclosure authorization.",
    )
    _render_targets(output, plan.target_references)
    if _read(input_fn, f"Type {plan.confirmation_phrase} to confirm: ") != plan.confirmation_phrase:
        return
    mutation_actor = _mutation_actor(actor, input_fn)
    if mutation_actor is None:
        return
    result = execute_curation_review(
        root,
        plan,
        reviewed_by=mutation_actor,
        authority_gate=dependencies.curation_authority_gate,
    )
    _write(output, f"Curation Review recorded at state revision {result.state_revision}.")


def _render_history(output: TextIO, detail: CandidateReviewDetail) -> None:
    _write(output, "Complete Candidate Curation History", "")
    for proposal in detail.proposals:
        _write(output, f"Proposal {proposal.selection_proposal_id}")
        for decision in proposal.decisions:
            _write(
                output,
                f"  Decision {decision.selection_decision_id}: {decision.decision}",
            )
    for selection in detail.selections:
        _write(output, f"Selection {selection.selection_id}: {selection.lifecycle_state}")
    for placement in detail.placements:
        _write(output, f"Placement {placement.placement_id}: {placement.lifecycle_state}")
    for annotation in detail.annotations:
        _write(
            output,
            f"Annotation {annotation.annotation_id} revision {annotation.annotation_revision}",
        )
    for reflection in detail.reflections:
        _write(
            output,
            f"Reflection {reflection.reflection_id} revision {reflection.reflection_revision}",
        )
    for review in detail.reviews:
        _write(
            output,
            f"Review {review.curation_review_decision_id}: {review.decision}",
        )


def _review_entry(
    *,
    root: Path,
    entry_id: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    detail = get_candidate_review_detail(root, entry_id)
    clear_fn()
    _render_detail(output, detail)
    if not detail.selectable:
        _pause(input_fn)
        return
    active = tuple(
        item for item in detail.selections if item.lifecycle_state == "activated"
    )
    if active:
        _write(
            output,
            "1. Place in another eligible section",
            "2. Add / revise Annotation",
            "3. Add / revise Reflection",
            "4. Record curation Review",
            "5. Withdraw Selection",
            "6. Replace Selection",
            "7. View complete history",
            "B. Back",
        )
        action = _read(input_fn, "Action: ")
        if _navigation(action) is not None:
            return
        if action == "1":
            _placement_flow(
                root=root,
                detail=detail,
                input_fn=input_fn,
                output=output,
                dependencies=dependencies,
                actor=actor,
            )
        elif action == "2":
            _annotation_flow(
                root=root,
                detail=detail,
                input_fn=input_fn,
                output=output,
                dependencies=dependencies,
                actor=actor,
            )
        elif action == "3":
            _reflection_flow(
                root=root,
                detail=detail,
                input_fn=input_fn,
                output=output,
                dependencies=dependencies,
                actor=actor,
            )
        elif action == "4":
            _review_flow(
                root=root,
                detail=detail,
                input_fn=input_fn,
                output=output,
                dependencies=dependencies,
                actor=actor,
            )
        elif action == "5":
            _withdrawal_flow(
                root=root,
                detail=detail,
                input_fn=input_fn,
                output=output,
                dependencies=dependencies,
                actor=actor,
            )
        elif action == "6":
            _replacement_flow(
                root=root,
                detail=detail,
                input_fn=input_fn,
                output=output,
                dependencies=dependencies,
                actor=actor,
                clear_fn=clear_fn,
            )
        elif action == "7":
            _render_history(output, detail)
        return

    pending = tuple(proposal for proposal in detail.proposals if proposal.undecided)
    _write(
        output,
        "1. Select for this Portfolio",
        "2. Decline this proposed use",
        "3. Decide an existing Proposal",
        "4. View complete history",
        "B. Not now",
    )
    action = _read(input_fn, "Action: ")
    if _navigation(action) is not None:
        return
    if action == "1":
        _decision_flow(
            root=root,
            detail=detail,
            decision="select",
            selection_proposal_id=None,
            input_fn=input_fn,
            output=output,
            dependencies=dependencies,
            actor=actor,
        )
    elif action == "2":
        _decision_flow(
            root=root,
            detail=detail,
            decision="decline",
            selection_proposal_id=None,
            input_fn=input_fn,
            output=output,
            dependencies=dependencies,
            actor=actor,
        )
    elif action == "3":
        if not pending:
            _write(output, "No undecided Selection Proposal is available.")
            return
        for index, proposal_item in enumerate(pending, 1):
            _write(
                output,
                f"{index}. {proposal_item.selection_proposal_id} — "
                f"{proposal_item.proposal_origin} — sections "
                f"{', '.join(proposal_item.proposed_section_ids)}",
            )
        chosen_proposal = _numbered_choice(
            _read(input_fn, "Proposal number: "),
            pending,
        )
        if chosen_proposal is None or isinstance(chosen_proposal, NavigationChoice):
            return
        _write(output, "1. Accept", "2. Decline")
        decision_choice = _read(input_fn, "Decision: ")
        if decision_choice not in {"1", "2"}:
            return
        _decision_flow(
            root=root,
            detail=detail,
            decision="select" if decision_choice == "1" else "decline",
            selection_proposal_id=chosen_proposal.selection_proposal_id,
            input_fn=input_fn,
            output=output,
            dependencies=dependencies,
            actor=actor,
        )
    elif action == "4":
        _render_history(output, detail)


def run_candidate_review_menu(
    *,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    workspace_root: str | Path,
    actor: ActorAttribution | None = None,
) -> None:
    """Run the Portfolio-scoped guided Candidate review and Selection workflow."""

    root = Path(workspace_root)
    while True:
        clear_fn()
        _write(
            output,
            "Review Candidates / Selections",
            "",
            "1. Needs attention",
            "2. Ready to consider",
            "3. Already selected",
            "4. Negative / unresolved",
            "5. All persisted Candidate state",
            "6. Active Selections",
            "7. Selection history",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        category = _read(input_fn, "Choice: ")
        if category.casefold() == "h":
            clear_fn()
            _write(
                output,
                "Candidate Review Help",
                "",
                "Review uses persisted Candidate Inbox state and does not run discovery.",
                "Candidate eligibility is not automatic Selection.",
                "Selection is not Placement.",
                "Acknowledging a Candidate condition does not clear it.",
                "Curation approval is not disclosure authorization.",
            )
            _pause(input_fn)
            continue
        if _navigation(category) is not None:
            return
        if category not in {"1", "2", "3", "4", "5", "6", "7"}:
            _write(output, "That review category is not available.")
            _pause(input_fn)
            continue
        try:
            if category == "7":
                items = _history_entries(root, portfolio_id)
            else:
                items = list_candidate_review_entries(
                    root,
                    _query_for_category(portfolio_id, category),
                ).items
            clear_fn()
            _write(output, "Candidate Review Entries", "")
            if not items:
                _write(output, "No matching persisted Candidate review entries.")
                _pause(input_fn)
                continue
            for index, item in enumerate(items, 1):
                _write(output, f"{index}. {_item_line(item)}")
            selected = _numbered_choice(
                _read(input_fn, "Entry number (B to go back): "),
                items,
            )
            if isinstance(selected, NavigationChoice):
                continue
            if selected is None:
                _write(output, "That Candidate review entry number is not available.")
                _pause(input_fn)
                continue
            _review_entry(
                root=root,
                entry_id=selected.entry_id,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
                dependencies=dependencies,
                actor=actor,
            )
            _pause(input_fn)
        except (CandidateInboxError, CandidateReviewError, CurationWorkflowError) as error:
            code = getattr(error, "code", "candidate_review.problem")
            _write(output, f"{code}: {error}")
            _pause(input_fn)


__all__ = ["run_candidate_review_menu"]
