"""Teacher-facing guided Working Composition preparation and freeze menu."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from pds_core.menu_navigation import NavigationChoice, parse_navigation_choice

from vitrine.curation_services import CurationWorkflowError
from vitrine.menu_interactions import confirm_exact_phrase
from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import ActorAttribution
from vitrine.teacher_presentation import teacher_term
from vitrine.workflow_context import VitrineWorkflowDependencies
from vitrine.workflow_views import CompositionView, WorkflowViewError, show_composition
from vitrine.working_composition import (
    WorkingCompositionError,
    WorkingCompositionPreparation,
    freeze_prepared_working_composition,
    prepare_working_composition,
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


def _codes(values: tuple[str, ...]) -> str:
    return ", ".join(values) or "(none)"


def _teacher_codes(values: tuple[str, ...]) -> str:
    return ", ".join(teacher_term(value) for value in values) or "None"


def _preparation_status(disposition: str) -> str:
    if disposition == "create_initial":
        return "Ready to freeze the initial Working Composition"
    if disposition == "create_successor":
        return "Ready to freeze an updated Working Composition"
    if disposition == "reuse_exact_current":
        return "Current frozen Composition already matches this curation"
    return teacher_term(disposition)


def _selection_title(
    preparation: WorkingCompositionPreparation,
    selection_id: str,
) -> str:
    for selection in preparation.selections:
        if selection.selection_id == selection_id:
            return selection.candidate_display_snapshot
    return "Selection"


def _render_composition_view(
    output: TextIO,
    view: CompositionView,
    *,
    heading: str,
) -> None:
    _write(output, heading, "")
    composition = view.composition
    inventory = view.inventory
    if composition is None:
        _write(output, "No Working Composition was found.")
        return
    _write(
        output,
        f"Revision: {composition.composition_revision}",
        f"Frozen at: {composition.created_at.isoformat()}",
        f"Composition note: {composition.composition_note or '(none)'}",
        "",
        "Portfolio state",
        f"Selections included: {len(composition.selection_ids)}",
        f"Placements included: {len(composition.placement_ids)}",
        f"Ordered sections represented: {len(composition.arrangement_ids)}",
    )
    if inventory is None:
        _write(output, "Composition inventory is unavailable.")
        return
    _write(
        output,
        f"Coherence: {teacher_term(inventory.coherence_state)}",
        "Unresolved obligations: "
        f"{_teacher_codes(inventory.unresolved_obligation_codes)}",
        f"Applicable curation Reviews: "
        f"{len(inventory.applicable_review_decision_ids)}",
        f"Related Profile requirements: "
        f"{len(inventory.related_profile_requirement_ids)}",
    )


def _render_composition_technical_details(
    output: TextIO,
    view: CompositionView,
    *,
    heading: str,
) -> None:
    _write(output, f"{heading} — Technical Details / Provenance", "")
    composition = view.composition
    inventory = view.inventory
    if composition is None:
        _write(output, "No Working Composition was found.")
        return
    _write(
        output,
        f"Revision: {composition.composition_revision}",
        f"Profile Binding: {composition.profile_binding_id}",
        "Profile Revision: "
        f"{composition.profile_revision.portfolio_profile_id}:"
        f"{composition.profile_revision.profile_revision}",
        "Predecessor revision: "
        f"{composition.predecessor_composition_revision or '(none)'}",
        f"Created by: {composition.created_by.actor_id}",
        f"Created at: {composition.created_at.isoformat()}",
        f"Composition note: {composition.composition_note or '(none)'}",
        f"Selection IDs: {_codes(composition.selection_ids)}",
        f"Placement IDs: {_codes(composition.placement_ids)}",
        f"Arrangement IDs: {_codes(composition.arrangement_ids)}",
        f"Composition pointer revision: {view.pointer_revision or '(none)'}",
    )
    if inventory is None:
        _write(output, "Inventory: missing")
        return
    _write(
        output,
        f"Coherence: {inventory.coherence_state}",
        f"Unresolved obligations: {_codes(inventory.unresolved_obligation_codes)}",
        f"Rationale IDs: {_codes(inventory.included_rationale_ids)}",
        "Curation revisions: "
        + _codes(
            tuple(
                f"{item.record_kind}:{item.record_id}:{item.revision}"
                for item in inventory.included_curation_revisions
            )
        ),
        "Applicable Review Decision IDs: "
        f"{_codes(inventory.applicable_review_decision_ids)}",
        "Related Profile Requirement IDs: "
        f"{_codes(inventory.related_profile_requirement_ids)}",
    )


def _composition_view_menu(
    view: CompositionView,
    *,
    heading: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> None:
    while True:
        clear_fn()
        _render_composition_view(output, view, heading=heading)
        _write(
            output,
            "",
            "T. Technical details / provenance",
            "B. Back",
        )
        choice = _read(
            input_fn,
            "T for technical details or Enter/B to return: ",
        )
        if not choice or _navigation(choice) is NavigationChoice.BACK:
            return
        if choice.casefold() == "t":
            clear_fn()
            _render_composition_technical_details(
                output,
                view,
                heading=heading,
            )
            _pause(input_fn)
            continue
        if _navigation(choice) is not None:
            return
        _write(output, "That Composition view choice is not available.")
        _pause(input_fn)


def _render_sections(output: TextIO, preparation: WorkingCompositionPreparation) -> None:
    _write(output, "Sections and order", "")
    for section in preparation.sections:
        maximum = (
            "no maximum"
            if section.maximum_placements is None
            else f"limit {section.maximum_placements}"
        )
        _write(
            output,
            f"{section.order}. {section.label} — "
            f"{teacher_term(section.obligation)}",
            f"   {section.purpose}",
            f"   {section.active_placement_count} placed; "
            f"minimum {section.minimum_placements}; {maximum}",
        )
        for position, placement in enumerate(section.placements, 1):
            title = placement.display_title or placement.candidate_display_snapshot
            _write(
                output,
                f"   {position}. {title}",
                f"      Status: "
                f"{teacher_term(placement.candidate_condition_state)}",
            )
            if placement.unresolved_condition_codes:
                _write(
                    output,
                    "      Needs attention: "
                    f"{_teacher_codes(placement.unresolved_condition_codes)}",
                )
    if preparation.unplaced_selection_ids:
        _write(
            output,
            "",
            "Active evidence not currently placed in a Portfolio section:",
            *(
                f"- {_selection_title(preparation, selection_id)}"
                for selection_id in preparation.unplaced_selection_ids
            ),
        )


def _render_requirements(
    output: TextIO,
    preparation: WorkingCompositionPreparation,
) -> None:
    _write(output, "Profile requirements", "")
    for requirement in preparation.requirements:
        _write(
            output,
            f"- {requirement.title} — {teacher_term(requirement.obligation)}",
            f"  {teacher_term(requirement.requirement_kind)}; "
            f"{teacher_term(requirement.status)}",
        )
        if requirement.associated_unresolved_obligation_codes:
            _write(
                output,
                "  Needs attention: "
                f"{_teacher_codes(requirement.associated_unresolved_obligation_codes)}",
            )
    _write(
        output,
        "",
        "Requirement status uses explicit machine-readable Profile semantics.",
        "Profile prose is not parsed into hidden policy.",
    )


def _render_sources(output: TextIO, preparation: WorkingCompositionPreparation) -> None:
    _write(output, "Source currentness", "")
    if not preparation.source_observations:
        _write(output, "No active Selection source observations are included.")
        return
    for source in preparation.source_observations:
        _write(
            output,
            f"- {_selection_title(preparation, source.selection_id)}",
            f"  Current use: {teacher_term(source.current_use_state)}",
            f"  Publication series: {teacher_term(source.observed_series_state)}; "
            f"withdrawal: {teacher_term(source.observed_withdrawal_state)}",
        )
    _write(
        output,
        "",
        "Historical, withdrawn, or unresolved source state does not "
        "automatically remove curation.",
    )


def _render_reviews(output: TextIO, preparation: WorkingCompositionPreparation) -> None:
    _write(output, "Applicable curation Reviews", "")
    if not preparation.reviews:
        _write(output, "No Review Decision applies to the prepared curation state.")
        return
    for review in preparation.reviews:
        marker = " — NEEDS ATTENTION" if review.requires_attention else ""
        _write(
            output,
            f"- {teacher_term(review.decision)}{marker}",
            f"  Applies to {len(review.target_references)} curation item(s)",
            "  Profile approval requirement: "
            f"{'yes' if review.approval_requirement_id else 'no'}",
            f"  Follow-up: {_teacher_codes(review.required_follow_up_codes)}",
        )
    _write(output, "", "Curation Review is not disclosure authorization.")


def _render_audience(output: TextIO, preparation: WorkingCompositionPreparation) -> None:
    _write(output, "Profile audience constraints", "")
    if not preparation.audience_rules:
        _write(output, "The exact Profile Revision defines no audience rules.")
        return
    for rule in preparation.audience_rules:
        _write(
            output,
            f"- {teacher_term(rule.audience_class)}",
            f"  Presentation: {teacher_term(rule.presentation_class)}",
            f"  Allowed: {_teacher_codes(rule.allowed_content_classes)}",
            f"  Prohibited: {_teacher_codes(rule.prohibited_content_classes)}",
            f"  Required review: {_teacher_codes(rule.required_review_classes)}",
        )
        if rule.retention_policy_reference:
            _write(
                output,
                f"  Retention policy: {rule.retention_policy_reference}",
            )
    _write(
        output,
        "",
        "These are Profile constraints only. This workflow does not create an Audience Context",
        "and does not authorize disclosure or build a Snapshot.",
    )


def _render_preparation_technical_details(
    output: TextIO,
    preparation: WorkingCompositionPreparation,
) -> None:
    _write(
        output,
        "Working Composition Technical Details / Provenance",
        "",
        f"Portfolio ID: {preparation.portfolio_id}",
        f"Portfolio Subject ID: {preparation.portfolio_subject_id}",
        f"Profile Binding ID: {preparation.profile_binding_id}",
        "Profile Revision: "
        f"{preparation.profile_revision_id}:{preparation.profile_revision_number}",
        f"Observed Vitrine state revision: {preparation.observed_state_revision}",
        "Observed Composition pointer revision: "
        f"{preparation.observed_composition_pointer_revision or '(none)'}",
        f"Current Composition revision: "
        f"{preparation.current_composition_revision or '(none)'}",
        f"Predicted Composition revision: {preparation.predicted_composition_revision}",
        "Predicted Composition pointer revision: "
        f"{preparation.predicted_composition_pointer_revision}",
        f"Disposition: {preparation.disposition}",
        f"Preparation fingerprint: {preparation.preparation_fingerprint}",
        "",
        "Exact prepared payload",
        f"Selection IDs: {_codes(preparation.payload.selection_ids)}",
        f"Placement IDs: {_codes(preparation.payload.placement_ids)}",
        f"Arrangement IDs: {_codes(preparation.payload.arrangement_ids)}",
        f"Rationale IDs: {_codes(preparation.payload.included_rationale_ids)}",
        "Applicable Review Decision IDs: "
        f"{_codes(preparation.payload.applicable_review_decision_ids)}",
        "Related Profile Requirement IDs: "
        f"{_codes(preparation.payload.related_profile_requirement_ids)}",
        "Unresolved obligation codes: "
        f"{_codes(preparation.payload.unresolved_obligation_codes)}",
        f"Coherence state: {preparation.payload.coherence_state}",
        "",
    )
    if preparation.sections:
        _write(output, "Section / Arrangement provenance")
        for section in preparation.sections:
            _write(
                output,
                f"- {section.label} ({section.section_id})",
                "  Arrangement: "
                f"{section.current_arrangement_id or '(none)'}; revision "
                f"{section.current_arrangement_revision or '(none)'}; pointer "
                f"{section.current_arrangement_pointer_revision or '(none)'}",
            )
            for placement in section.placements:
                _write(
                    output,
                    f"  Placement {placement.placement_id}; "
                    f"Selection {placement.selection_id}; "
                    f"Candidate {placement.candidate_id}",
                    f"  Condition: {placement.candidate_condition_state}; "
                    f"unresolved {_codes(placement.unresolved_condition_codes)}",
                )
        _write(output, "")
    if preparation.requirements:
        _write(output, "Profile requirement provenance")
        for requirement in preparation.requirements:
            _write(
                output,
                f"- {requirement.title} ({requirement.requirement_id})",
                f"  kind={requirement.requirement_kind}; "
                f"obligation={requirement.obligation}; "
                f"scope={requirement.scope_kind}:"
                f"{requirement.scope_reference or '(none)'}",
                f"  satisfaction={requirement.satisfaction_class}; "
                f"status={requirement.status}",
                "  unresolved codes: "
                f"{_codes(requirement.associated_unresolved_obligation_codes)}",
            )
        _write(output, "")
    if preparation.source_observations:
        _write(output, "Source provenance")
        for source in preparation.source_observations:
            _write(
                output,
                f"- Selection {source.selection_id}; Candidate {source.candidate_id}",
                f"  Publication {source.publication_id}; "
                f"current use {source.current_use_state}",
                "  Series head: "
                f"{source.series_head_publication_id or '(unresolved)'}; "
                f"series {source.observed_series_state}; withdrawal "
                f"{source.observed_withdrawal_state}",
            )
        _write(output, "")
    if preparation.reviews:
        _write(output, "Curation Review provenance")
        for review in preparation.reviews:
            targets = ", ".join(
                f"{item.target_kind}:{item.target_id}:"
                f"{item.target_revision if item.target_revision is not None else '-'}"
                for item in review.target_references
            )
            _write(
                output,
                f"- {review.curation_review_decision_id}: {review.decision}",
                "  approval requirement: "
                f"{review.approval_requirement_id or '(none)'}",
                f"  targets: {targets or '(none)'}",
                f"  follow-up: {_codes(review.required_follow_up_codes)}",
            )
        _write(output, "")
    if preparation.audience_rules:
        _write(output, "Audience-rule provenance")
        for rule in preparation.audience_rules:
            _write(
                output,
                f"- {rule.audience_class} ({rule.audience_rule_id})",
                f"  presentation: {rule.presentation_class}",
                f"  allowed content classes: {_codes(rule.allowed_content_classes)}",
                f"  prohibited content classes: "
                f"{_codes(rule.prohibited_content_classes)}",
                f"  required review classes: "
                f"{_codes(rule.required_review_classes)}",
                f"  retention policy: "
                f"{rule.retention_policy_reference or '(none)'}",
            )


def _set_delta(before: tuple[str, ...], after: tuple[str, ...]) -> tuple[str, str]:
    before_set = set(before)
    after_set = set(after)
    return (
        _codes(tuple(sorted(after_set - before_set))),
        _codes(tuple(sorted(before_set - after_set))),
    )


def _render_preview(
    root: Path,
    output: TextIO,
    preparation: WorkingCompositionPreparation,
) -> None:
    _write(
        output,
        "Exact freeze preview",
        "",
        f"Observed Vitrine state revision: {preparation.observed_state_revision}",
        "Observed Composition pointer revision: "
        f"{preparation.observed_composition_pointer_revision or '(none)'}",
        f"Current Composition revision: {preparation.current_composition_revision or '(none)'}",
        f"Predicted Composition revision: {preparation.predicted_composition_revision}",
        "Predicted Composition pointer revision: "
        f"{preparation.predicted_composition_pointer_revision}",
        f"Disposition: {preparation.disposition}",
        f"Coherence: {preparation.payload.coherence_state}",
        "Unresolved obligations: "
        f"{_codes(preparation.payload.unresolved_obligation_codes)}",
        f"Selection IDs: {_codes(preparation.payload.selection_ids)}",
        f"Placement IDs: {_codes(preparation.payload.placement_ids)}",
        f"Arrangement IDs: {_codes(preparation.payload.arrangement_ids)}",
        f"Rationale IDs: {_codes(preparation.payload.included_rationale_ids)}",
        "Applicable Review Decision IDs: "
        f"{_codes(preparation.payload.applicable_review_decision_ids)}",
        "Related Profile Requirement IDs: "
        f"{_codes(preparation.payload.related_profile_requirement_ids)}",
        f"Requested note: {preparation.requested_composition_note or '(none)'}",
        "Note will persist: "
        f"{'yes' if preparation.composition_note_will_persist else 'no'}",
        f"Preparation fingerprint: {preparation.preparation_fingerprint}",
        "",
        "Current-versus-prepared delta",
    )
    current = show_composition(root, preparation.portfolio_id)
    if current.composition is None:
        _write(output, "- No current Composition; this would create the initial revision.")
        return
    if preparation.disposition == "reuse_exact_current":
        _write(
            output,
            "- No material curation change would create a new Composition revision.",
            "- The current Composition already freezes this exact semantic state.",
        )
        if preparation.requested_composition_note:
            _write(
                output,
                "- The requested note would not create a note-only successor revision.",
            )
        return
    before = current.composition
    inventory = current.inventory
    added, removed = _set_delta(before.selection_ids, preparation.payload.selection_ids)
    _write(output, f"- Selections added: {added}", f"- Selections removed: {removed}")
    added, removed = _set_delta(before.placement_ids, preparation.payload.placement_ids)
    _write(output, f"- Placements added: {added}", f"- Placements removed: {removed}")
    _write(
        output,
        "- Arrangement identities changed: "
        f"{'yes' if before.arrangement_ids != preparation.payload.arrangement_ids else 'no'}",
    )
    if inventory is not None:
        added, removed = _set_delta(
            inventory.applicable_review_decision_ids,
            preparation.payload.applicable_review_decision_ids,
        )
        _write(output, f"- Reviews added: {added}", f"- Reviews removed: {removed}")
        added, removed = _set_delta(
            inventory.related_profile_requirement_ids,
            preparation.payload.related_profile_requirement_ids,
        )
        _write(
            output,
            f"- Related requirements added: {added}",
            f"- Related requirements removed: {removed}",
            "- Unresolved obligation codes changed: "
            f"{'yes' if inventory.unresolved_obligation_codes != preparation.payload.unresolved_obligation_codes else 'no'}",
        )
    _write(
        output,
        "- Source currentness is a live preparation observation; historical Composition records",
        "  do not store a prior source-currentness observation to compare as historical truth.",
    )


def _review_preparation(
    *,
    root: Path,
    preparation: WorkingCompositionPreparation,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    while True:
        clear_fn()
        _write(
            output,
            "Working Composition Preparation",
            "",
            f"Status: {_preparation_status(preparation.disposition)}",
            f"Coherence: {teacher_term(preparation.payload.coherence_state)}",
            "Unresolved obligations: "
            f"{_teacher_codes(preparation.payload.unresolved_obligation_codes)}",
            "",
            "1. Sections and order",
            "2. Requirements and unresolved items",
            "3. Source currentness",
            "4. Reviews and follow-up",
            "5. Audience constraints",
            "6. Exact freeze preview / changes",
            "7. Freeze this reviewed preparation",
            "T. Technical details / provenance",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        choice = _read(input_fn, "Choice: ")
        if choice.casefold() == "h":
            clear_fn()
            _write(
                output,
                "Working Composition Help",
                "",
                "Preparation is read-only and creates no canonical record.",
                "Coherent does not mean approved or disclosure-ready.",
                "Unresolved obligations are preserved rather than silently cleared.",
                "Working Composition is not an Audience Context or Snapshot.",
            )
            _pause(input_fn)
            continue
        navigation = _navigation(choice)
        if navigation is not None:
            return
        clear_fn()
        if choice == "1":
            _render_sections(output, preparation)
        elif choice == "2":
            _render_requirements(output, preparation)
        elif choice == "3":
            _render_sources(output, preparation)
        elif choice == "4":
            _render_reviews(output, preparation)
        elif choice == "5":
            _render_audience(output, preparation)
        elif choice == "6":
            _render_preview(root, output, preparation)
        elif choice.casefold() == "t":
            _render_preparation_technical_details(output, preparation)
        elif choice == "7":
            def render_freeze_review() -> None:
                _render_preview(root, output, preparation)
                if preparation.payload.unresolved_obligation_codes:
                    _write(
                        output,
                        "",
                        "This exact Composition will retain the unresolved obligations shown above.",
                        "Freezing does not clear, waive, satisfy, or authorize them.",
                    )

            if not confirm_exact_phrase(
                expected_phrase="FREEZE COMPOSITION",
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
                render_review=render_freeze_review,
            ):
                continue
            mutation_actor = _mutation_actor(actor, input_fn)
            if mutation_actor is None:
                _write(output, "Working Composition was not frozen.")
                _pause(input_fn)
                continue
            try:
                result = freeze_prepared_working_composition(
                    root,
                    preparation,
                    created_by=mutation_actor,
                    authority_gate=dependencies.curation_authority_gate,
                )
            except (WorkingCompositionError, CurationWorkflowError) as error:
                _write(
                    output,
                    f"Working Composition freeze failed: {error.code}",
                    str(error),
                    "Prepare again before retrying if state changed.",
                )
                _pause(input_fn)
                return
            clear_fn()
            if result.disposition == "existing":
                _write(
                    output,
                    "Working Composition current state",
                    "",
                    "The current frozen Composition already matches this exact semantic state.",
                    "No duplicate Composition revision was created.",
                    f"Vitrine state revision: {result.state_revision}",
                )
            else:
                _write(
                    output,
                    "Working Composition frozen.",
                    "",
                    f"Vitrine state revision: {result.state_revision}",
                )
            return
        else:
            _write(output, "That Working Composition action is not available.")
        _pause(input_fn)


def run_working_composition_menu(
    *,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    workspace_root: Path,
    actor: ActorAttribution | None = None,
) -> None:
    """Run the Portfolio-scoped guided Working Composition workflow."""
    root = Path(workspace_root)
    while True:
        clear_fn()
        try:
            current = show_composition(root, portfolio_id)
            current_line = (
                "Current frozen Composition: not frozen"
                if current.composition is None
                else "Current frozen Composition: "
                f"revision {current.composition.composition_revision}"
            )
        except WorkflowViewError as error:
            current_line = f"Current Composition unavailable: {error.code}"
        _write(
            output,
            "Working Composition",
            "",
            current_line,
            "",
            "1. Prepare current curation",
            "2. View current frozen Composition",
            "3. View historical Composition revision",
            "H. Help",
            "B. Back",
            "M. Main Menu",
            "Q. Quit",
        )
        choice = _read(input_fn, "Choice: ")
        if choice.casefold() == "h":
            clear_fn()
            _write(
                output,
                "Working Composition Help",
                "",
                "Preparation is read-only. Freeze is a separate explicit action.",
                "Working Composition is byte-free curation state, not a Snapshot.",
                "Profile audience rules are constraints, not disclosure authorization.",
            )
            _pause(input_fn)
            continue
        navigation = _navigation(choice)
        if navigation is not None:
            return
        clear_fn()
        if choice == "1":
            note = _read(
                input_fn,
                "Composition note (optional; persists only for a new revision): ",
            ) or None
            try:
                preparation = prepare_working_composition(
                    root,
                    portfolio_id,
                    composition_note=note,
                )
            except (WorkingCompositionError, CurationWorkflowError) as error:
                _write(
                    output,
                    f"Working Composition cannot be prepared: {error.code}",
                    str(error),
                    "No canonical Composition was created.",
                )
                _pause(input_fn)
                continue
            _review_preparation(
                root=root,
                preparation=preparation,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
                dependencies=dependencies,
                actor=actor,
            )
        elif choice == "2":
            try:
                view = show_composition(root, portfolio_id)
                _composition_view_menu(
                    view,
                    heading="Current frozen Working Composition",
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
            except WorkflowViewError as error:
                _write(output, f"Composition view unavailable: {error.code}", str(error))
                _pause(input_fn)
        elif choice == "3":
            raw_revision = _read(input_fn, "Exact historical Composition revision: ")
            if not raw_revision.isdecimal() or int(raw_revision) < 1:
                _write(output, "That Composition revision is not available.")
                _pause(input_fn)
                continue
            try:
                view = show_composition(root, portfolio_id, int(raw_revision))
                _composition_view_menu(
                    view,
                    heading=f"Working Composition revision {raw_revision}",
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
            except WorkflowViewError as error:
                _write(output, f"Composition view unavailable: {error.code}", str(error))
                _pause(input_fn)
        else:
            _write(output, "That Working Composition action is not available.")
            _pause(input_fn)


__all__ = ["run_working_composition_menu"]
