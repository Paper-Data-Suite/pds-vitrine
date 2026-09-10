"""Low-density Portfolio-centered teacher workflow."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Sequence, TextIO, TypeVar

from pds_core.academic_catalog import PublicationCatalogQuery
from pds_core.menu_navigation import NavigationChoice, parse_navigation_choice
from pds_core.workspace import resolve_workspace_root

from vitrine.attention_menu import run_attention_menu
from vitrine.candidate_review_menu import run_candidate_review_menu
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.curation_services import (
    decide_selection_proposal,
    invalidate_selection,
    place_selection,
    reorder_section,
    replace_selection,
    withdraw_selection,
)
from vitrine.current_portfolio_menu import (
    run_current_portfolio_build_export_menu,
)
from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import ActorAttribution
from vitrine.portfolio_services import (
    list_portfolios,
    observe_portfolio_state_revision,
    show_portfolio,
)
from vitrine.portfolio_setup_menu import run_create_portfolio_for_student_menu
from vitrine.profile_services import (
    ProfileBindingContext,
    analyze_profile_migration,
    bind_portfolio_profile,
    get_portfolio_profile_binding,
    get_profile_migration_history,
    get_profile_revision,
    list_bindable_profile_revisions,
    migrate_portfolio_profile,
    observe_profile_state_revision,
)
from vitrine.subject_menu import run_subject_menu
from vitrine.workflow_context import VitrineWorkflowDependencies
from vitrine.workflow_views import (
    CandidateDetail,
    list_active_selections,
    list_candidate_summaries,
    show_arrangement,
    show_candidate_detail,
)
from vitrine.working_composition_menu import run_working_composition_menu

_ChoiceValue = TypeVar("_ChoiceValue")


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
        value, allow_back=True, allow_main_menu=True, allow_quit=True
    )


def _numbered_choice(
    value: str, choices: Sequence[_ChoiceValue]
) -> _ChoiceValue | NavigationChoice | None:
    """Resolve one presentation number without accepting Python negative indexes."""
    navigation = _navigation(value)
    if navigation is not None:
        return navigation
    if not value.isdecimal():
        return None
    index = int(value)
    if index < 1 or index > len(choices):
        return None
    return choices[index - 1]


def _require_observed_revision(root: Path) -> int:
    revision = observe_portfolio_state_revision(root)
    if revision is None:
        raise ValueError(
            "state_revision_missing: this operation requires existing Vitrine state"
        )
    return revision


def _actor(input_fn: InputFunction) -> ActorAttribution | None:
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


def _choose_portfolio(
    *,
    root: Path,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
) -> str | None:
    values = list_portfolios(root)
    clear_fn()
    _write(output, "Open Portfolio", "")
    if not values:
        _write(output, "No Portfolios exist yet.")
        _pause(input_fn)
        return None
    for index, item in enumerate(values, 1):
        _write(
            output,
            f"{index}. {item.title_snapshot or item.subject_display_label or '(untitled)'}",
            f"   {item.portfolio_id}",
        )
    raw = _read(input_fn, "Portfolio number (B to go back): ")
    selected = _numbered_choice(raw, values)
    if isinstance(selected, NavigationChoice):
        return None
    if selected is None:
        _write(output, "That Portfolio number is not available.")
        _pause(input_fn)
        return None
    return selected.portfolio_id


def _overview(root: Path, portfolio_id: str, output: TextIO) -> None:
    x = show_portfolio(root, portfolio_id).summary
    _write(
        output,
        "Portfolio Overview",
        "",
        f"Portfolio ID: {x.portfolio_id}",
        f"Subject: {x.subject_display_label or x.portfolio_subject_id}",
        f"Profile Binding: {x.profile_binding_id or 'not bound'}",
        f"Candidates: {x.candidate_count}",
        f"Active Selections: {x.active_selection_count}",
        f"Working Composition: {x.current_composition_revision or 'not frozen'}",
        f"Snapshot Series: {x.snapshot_series_count}",
    )


def _profile_context(input_fn: InputFunction) -> ProfileBindingContext:
    as_of_text = _read(input_fn, "As-of date YYYY-MM-DD (optional): ")
    return ProfileBindingContext(
        as_of=date.fromisoformat(as_of_text) if as_of_text else None,
        school_year=_read(input_fn, "School year (optional): ") or None,
        institution_id=_read(input_fn, "Institution ID (optional): ") or None,
        program_id=_read(input_fn, "Program ID (optional): ") or None,
        content_area=_read(input_fn, "Content area (optional): ") or None,
    )


def _profile_binding_workflow(
    *,
    root: Path,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
    actor: ActorAttribution | None,
) -> None:
    _write(output, "Profile Binding", "")
    binding = get_portfolio_profile_binding(root, portfolio_id)
    if binding is not None:
        _write(
            output,
            f"Current exact Binding: {binding.profile_binding_id}",
            "Profile Revision: "
            f"{binding.profile_revision.portfolio_profile_id}:"
            f"{binding.profile_revision.profile_revision}",
            "",
            "1. Inspect current Profile Revision",
            "2. Browse bindable revisions / migrate explicitly",
            "3. View migration history",
        )
        action = _read(input_fn, "Action (Enter to leave unchanged): ")
        if action == "1":
            revision = get_profile_revision(root, binding.profile_revision)
            _write(
                output,
                f"Label: {revision.label}",
                f"Purpose: {revision.purpose_kind}",
                f"Sections: {', '.join(x.section_id for x in revision.sections)}",
            )
            return
        if action == "3":
            history = get_profile_migration_history(root, portfolio_id)
            if not history:
                _write(output, "No Profile migrations recorded.")
            for migration_item in history:
                _write(
                    output,
                    f"{migration_item.profile_migration_id}: "
                    f"{migration_item.source_profile_revision.profile_revision} -> "
                    f"{migration_item.target_profile_revision.profile_revision}",
                )
            return
        if action != "2":
            return

    observed_revision = observe_profile_state_revision(root)
    revisions = list_bindable_profile_revisions(root)
    for index, revision_item in enumerate(revisions, 1):
        marker = (
            " (current)"
            if binding is not None
            and revision_item.reference == binding.profile_revision
            else ""
        )
        _write(
            output,
            f"{index}. {revision_item.label}{marker}",
            f"   {revision_item.reference.portfolio_profile_id}:"
            f"{revision_item.reference.profile_revision}",
        )
    raw_profile = _read(input_fn, "Profile number (Enter to leave unchanged): ")
    selected = _numbered_choice(raw_profile, revisions)
    if selected is None or isinstance(selected, NavigationChoice):
        if raw_profile and selected is None:
            _write(output, "That Profile number is not available.")
        return
    context = _profile_context(input_fn)
    mutation_actor = actor or _actor(input_fn)
    if mutation_actor is None:
        return
    if binding is None:
        if _read(input_fn, "Type BIND to bind this exact Profile Revision: ") != "BIND":
            return
        bind_portfolio_profile(
            root,
            portfolio_id,
            selected.reference,
            actor=mutation_actor,
            binding_reason=_read(input_fn, "Binding reason: ") or "teacher_selected",
            context=context,
            expected_state_revision=observed_revision,
        )
        _write(output, "Profile Binding recorded.")
        return

    analysis = analyze_profile_migration(
        root, portfolio_id, selected.reference, context=context
    )
    impact = analysis.requirement_impact
    _write(
        output,
        "Migration impact",
        f"Added requirements: {', '.join(impact.added) or '(none)'}",
        f"Removed requirements: {', '.join(impact.removed) or '(none)'}",
        f"Replaced requirements: {', '.join(impact.replaced) or '(none)'}",
        f"Material changes: {', '.join(impact.materially_changed) or '(none)'}",
        f"Affected sections: {', '.join(analysis.affected_section_ids) or '(none)'}",
        f"Potentially affected Selections: {analysis.potentially_affected_selection_count}",
        f"Blocked: {'yes' if analysis.blocked else 'no'}",
    )
    if (
        analysis.blocked
        or _read(
            input_fn, "Type MIGRATE to migrate explicitly to this exact revision: "
        )
        != "MIGRATE"
    ):
        return
    migrate_portfolio_profile(
        root,
        portfolio_id,
        selected.reference,
        actor=mutation_actor,
        migration_reason=_read(input_fn, "Migration reason: ") or "teacher_selected",
        authority_reference=_read(input_fn, "Authority reference: ")
        or "teacher_workflow",
        context=context,
        expected_state_revision=observed_revision,
    )
    _write(output, "Profile migration recorded.")


def _show_candidate_facts(
    root: Path, candidate_id: str, output: TextIO
) -> CandidateDetail:
    detail = show_candidate_detail(root, candidate_id)
    endpoint = detail.source_endpoint
    publication = endpoint.core_publication
    producer = endpoint.producer_source
    artifact = endpoint.source_artifact
    relationships = ", ".join(
        f"{item.assertion_id}:{item.relationship_kind}:"
        f"{item.source_subject_kind}:{item.source_subject_id}"
        for item in endpoint.subject_relationship_assertions
    )
    availability = ", ".join(
        f"{item.dimension}={item.outcome}" for item in detail.availability_observations
    )
    _write(
        output,
        "Candidate Review",
        "",
        detail.display_snapshot,
        f"Candidate ID: {detail.candidate_id}",
        f"Candidate Evaluation ID: {detail.candidate_evaluation_id}",
        f"Profile Binding: {detail.profile_binding_id}",
        f"Core Publication ID: {publication.publication_id}",
        f"Producer module: {producer.producer_module_id}",
        f"Producer source: {producer.source_record_kind}:{producer.source_record_id}",
        f"Producer native revision: {producer.native_revision if producer.native_revision is not None else '(none)'}",
        f"Artifact ID: {artifact.artifact_id if artifact else '(none)'}",
        "Artifact kind/representation: "
        f"{artifact.artifact_kind + '/' + artifact.representation_kind if artifact else '(none)'}",
        f"Subject relationships: {relationships or '(none)'}",
        f"Condition: {detail.condition_state}",
        f"Evaluation reasons: {', '.join(detail.evaluation_reason_codes) or '(none)'}",
        "Unresolved condition codes: "
        f"{', '.join(detail.unresolved_condition_codes) or '(none)'}",
        f"Availability: {availability or '(none)'}",
        f"Eligible sections: {', '.join(detail.eligible_section_ids)}",
        "",
        "Collaborative semantics: Group Membership != Artifact Author; "
        "Artifact Subject != Artifact Author; documented contribution != "
        "whole-Artifact authorship; represented Group remains separate; "
        "Group Score target != individual Score.",
        "Reviewing a Candidate does not select it.",
    )
    return detail


def _selection_placement_state(
    root: Path, portfolio_id: str, selection_id: str, candidate_id: str
) -> tuple[dict[str, int | None], dict[str, str]]:
    pointers: dict[str, int | None] = {}
    placements: dict[str, str] = {}
    candidate = show_candidate_detail(root, candidate_id)
    for section_id in candidate.eligible_section_ids:
        arrangement = show_arrangement(root, portfolio_id, section_id)
        matching = tuple(
            item for item in arrangement.placements if item.selection_id == selection_id
        )
        if matching:
            pointers[section_id] = arrangement.pointer_revision
            placements.update({item.placement_id: section_id for item in matching})
    return pointers, placements


def _curation_workflow(
    *,
    root: Path,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    observed = _require_observed_revision(root)
    _write(
        output,
        "Curate Selections",
        "",
        "1. Decide exact Selection Proposal",
        "2. Place active Selection",
        "3. Withdraw active Selection",
        "4. Invalidate active Selection",
        "5. Replace active Selection",
        "6. Reorder section Placements",
    )
    selections = list_active_selections(root, portfolio_id)
    for index, item in enumerate(selections, 1):
        _write(output, f"{index}. {item.selection_id} — Candidate {item.candidate_id}")
    action = _read(input_fn, "Curation action (Enter to inspect only): ")
    if action == "1":
        proposal_id = _read(input_fn, "Exact Selection Proposal ID: ")
        decision = _read(
            input_fn,
            "Decision (accepted/rejected/changes_requested/withdrawn/expired): ",
        )
        if decision not in {
            "accepted",
            "rejected",
            "changes_requested",
            "withdrawn",
            "expired",
        }:
            _write(output, "That Selection Decision is not available.")
            return
        mutation_actor = actor or _actor(input_fn)
        if (
            mutation_actor is not None
            and _read(input_fn, "Type DECIDE to record this immutable Decision: ")
            == "DECIDE"
        ):
            decide_selection_proposal(
                root,
                portfolio_id=portfolio_id,
                selection_proposal_id=proposal_id,
                decision=decision,
                decided_by=mutation_actor,
                expected_state_revision=observed,
                authority_gate=dependencies.curation_authority_gate,
                rationale_text=_read(input_fn, "Decision rationale (optional): ")
                or None,
            )
            _write(output, "Selection Decision recorded.")
        return
    if action == "6":
        section_id = _read(input_fn, "Exact section ID: ")
        arrangement = show_arrangement(root, portfolio_id, section_id)
        for index, placement in enumerate(arrangement.placements, 1):
            _write(output, f"{index}. {placement.placement_id}")
        order = tuple(
            item.strip()
            for item in _read(
                input_fn, "Placement IDs in exact order (comma-separated): "
            ).split(",")
            if item.strip()
        )
        mutation_actor = actor or _actor(input_fn)
        if (
            mutation_actor is not None
            and order
            and _read(input_fn, "Type REORDER to commit this exact order: ")
            == "REORDER"
        ):
            if arrangement.pointer_revision is None:
                raise ValueError(
                    "arrangement_pointer_missing: section has no current Arrangement pointer"
                )
            reorder_section(
                root,
                portfolio_id=portfolio_id,
                section_id=section_id,
                placement_ids=order,
                arranged_by=mutation_actor,
                expected_state_revision=observed,
                expected_arrangement_pointer_revision=arrangement.pointer_revision,
                authority_gate=dependencies.curation_authority_gate,
            )
            _write(output, "Section reordered.")
        return
    if action not in {"2", "3", "4", "5"}:
        return
    selection = _numbered_choice(
        _read(input_fn, "Active Selection number: "), selections
    )
    if selection is None or isinstance(selection, NavigationChoice):
        _write(output, "That Selection number is not available.")
        return
    mutation_actor = actor or _actor(input_fn)
    if mutation_actor is None:
        return
    if action == "2":
        section_id = _read(input_fn, "Exact section ID: ")
        arrangement = show_arrangement(root, portfolio_id, section_id)
        if _read(input_fn, "Type PLACE to place this Selection: ") == "PLACE":
            place_selection(
                root,
                portfolio_id=portfolio_id,
                selection_id=selection.selection_id,
                section_id=section_id,
                placed_by=mutation_actor,
                expected_state_revision=observed,
                expected_arrangement_pointer_revision=arrangement.pointer_revision,
                authority_gate=dependencies.curation_authority_gate,
            )
            _write(output, "Selection placed.")
        return
    pointers, placements = _selection_placement_state(
        root, portfolio_id, selection.selection_id, selection.candidate_id
    )
    reason = _read(input_fn, "Reason: ") or "teacher_curated"
    if action == "3" and _read(input_fn, "Type WITHDRAW to confirm: ") == "WITHDRAW":
        withdraw_selection(
            root,
            portfolio_id=portfolio_id,
            selection_id=selection.selection_id,
            withdrawn_by=mutation_actor,
            expected_state_revision=observed,
            expected_pointer_revisions=pointers,
            authority_gate=dependencies.curation_authority_gate,
            reason=reason,
        )
        _write(output, "Selection withdrawn.")
    elif (
        action == "4"
        and _read(input_fn, "Type INVALIDATE to confirm: ") == "INVALIDATE"
    ):
        invalidate_selection(
            root,
            portfolio_id=portfolio_id,
            selection_id=selection.selection_id,
            invalidated_by=mutation_actor,
            expected_state_revision=observed,
            expected_pointer_revisions=pointers,
            authority_gate=dependencies.curation_authority_gate,
            reason=reason,
        )
        _write(output, "Selection invalidated.")
    elif action == "5":
        candidates = tuple(
            item
            for item in list_candidate_summaries(root, portfolio_id)
            if item.candidate_id != selection.candidate_id
        )
        for index, replacement_item in enumerate(candidates, 1):
            _write(
                output,
                f"{index}. {replacement_item.display_snapshot} — "
                f"{replacement_item.candidate_id}",
            )
        successor = _numbered_choice(
            _read(input_fn, "Replacement Candidate number: "), candidates
        )
        if (
            successor is not None
            and not isinstance(successor, NavigationChoice)
            and _read(
                input_fn, "Type REPLACE to preserve eligible Placement sections: "
            )
            == "REPLACE"
        ):
            replace_selection(
                root,
                portfolio_id=portfolio_id,
                selection_id=selection.selection_id,
                successor_candidate_id=successor.candidate_id,
                replaced_by=mutation_actor,
                placement_dispositions=placements,
                expected_state_revision=observed,
                expected_pointer_revisions=pointers,
                authority_gate=dependencies.curation_authority_gate,
                reason=reason,
            )
            _write(output, "Selection replaced.")


def _portfolio_context(
    *,
    root: Path,
    portfolio_id: str,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    actor: ActorAttribution | None,
) -> None:
    while True:
        detail = show_portfolio(root, portfolio_id)
        clear_fn()
        _write(
            output,
            f"Portfolio — {detail.summary.title_snapshot or detail.summary.subject_display_label or portfolio_id}",
            "",
            "1. Overview / Subject Links",
            "2. Profile Binding",
            "3. Discover Candidates",
            "4. Review Candidates / Selections",
            "5. Working Composition",
            "6. Build and Export Current Portfolio",
            "7. Attention / Next Actions",
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
                "Portfolio Help",
                "",
                "Candidate review does not create a Selection.",
                "Working Composition is not a Snapshot.",
                "Audience Context is not disclosure authorization.",
            )
            _pause(input_fn)
            continue
        if _navigation(choice) is not None:
            return
        clear_fn()
        if choice == "1":
            _overview(root, portfolio_id, output)
            _pause(input_fn)
            run_subject_menu(
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
                portfolio_subject_id=detail.summary.portfolio_subject_id,
                workspace_root=root,
            )
            continue
        elif choice == "2":
            _profile_binding_workflow(
                root=root,
                portfolio_id=portfolio_id,
                input_fn=input_fn,
                output=output,
                actor=actor,
            )
        elif choice == "3":
            _write(output, "Discover Candidates", "")
            if (
                _read(
                    input_fn,
                    "Type DISCOVER to query configured Candidate sources, or Enter to cancel: ",
                )
                == "DISCOVER"
            ):
                discovery_observed = _require_observed_revision(root)
                mutation_actor = actor or _actor(input_fn)
                if mutation_actor is not None:
                    discovery = discover_and_evaluate_candidates(
                        root,
                        CandidateDiscoveryRequest(
                            portfolio_id=portfolio_id,
                            requesting_actor=mutation_actor,
                            requested_purpose=_read(input_fn, "Purpose: ")
                            or "teacher_review",
                            catalog_query=PublicationCatalogQuery(
                                school_year=_read(
                                    input_fn, "School year filter (optional): "
                                )
                                or None,
                                class_id=_read(input_fn, "Class ID filter (optional): ")
                                or None,
                                module_id=_read(
                                    input_fn, "Module ID filter (optional): "
                                )
                                or None,
                                work_id=_read(input_fn, "Work ID filter (optional): ")
                                or None,
                                state="current",
                                limit=100,
                            ),
                            expected_state_revision=discovery_observed,
                        ),
                        producer_registry=dependencies.producer_registry,
                        adapter_registry=dependencies.adapter_registry,
                        authorization_gate=dependencies.source_read_authorization_gate,
                    )
                    for finding in discovery.findings:
                        _write(output, f"{finding.code} — stage {finding.stage}")
                    _write(
                        output,
                        "Candidate discovery completed. Review is a separate persisted-state step.",
                    )
        elif choice == "4":
            run_candidate_review_menu(
                portfolio_id=portfolio_id,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
                dependencies=dependencies,
                workspace_root=root,
                actor=actor,
            )
        elif choice == "5":
            run_working_composition_menu(
                portfolio_id=portfolio_id,
                input_fn=input_fn,
                output=output,
                clear_fn=clear_fn,
                dependencies=dependencies,
                workspace_root=root,
                actor=actor,
            )
        elif choice == "6":
            run_current_portfolio_build_export_menu(
                root=root,
                portfolio_id=portfolio_id,
                input_fn=input_fn,
                output=output,
                dependencies=dependencies,
                actor=actor,
            )
        elif choice == "7":
            run_attention_menu(
                output=output,
                clear_fn=clear_fn,
                workspace_root=root,
                portfolio_id=portfolio_id,
            )
        else:
            _write(output, "Please choose 1-7, H, B, M, or Q.")
        _pause(input_fn)


def run_portfolio_menu(
    *,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    dependencies: VitrineWorkflowDependencies,
    workspace_root: Path | None = None,
    actor: ActorAttribution | None = None,
) -> None:
    """Run Portfolio navigation; canonical facts are reloaded before every action."""
    root = resolve_workspace_root(workspace_root)
    session_actor = actor
    while True:
        clear_fn()
        _write(
            output,
            "Portfolios",
            "",
            "1. Create Portfolio for Student",
            "2. Open Portfolio",
            "3. List Portfolios",
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
                "Portfolio Help",
                "",
                "Create a Portfolio by choosing an exact Core class and roster student.",
                "Cross-class identity is explicit; names and repeated IDs never auto-link.",
                "Guided setup binds one exact activated Profile Revision.",
            )
            _pause(input_fn)
            continue
        if _navigation(choice) is not None:
            return
        try:
            if choice == "1":
                existing_portfolio_id = run_create_portfolio_for_student_menu(
                    workspace_root=root,
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                    actor=session_actor,
                )
                if existing_portfolio_id is not None:
                    _portfolio_context(
                        root=root,
                        portfolio_id=existing_portfolio_id,
                        input_fn=input_fn,
                        output=output,
                        clear_fn=clear_fn,
                        dependencies=dependencies,
                        actor=session_actor,
                    )
            elif choice == "2":
                selected = _choose_portfolio(
                    root=root,
                    input_fn=input_fn,
                    output=output,
                    clear_fn=clear_fn,
                )
                if selected:
                    _portfolio_context(
                        root=root,
                        portfolio_id=selected,
                        input_fn=input_fn,
                        output=output,
                        clear_fn=clear_fn,
                        dependencies=dependencies,
                        actor=session_actor,
                    )
            elif choice == "3":
                clear_fn()
                _write(output, "Portfolios", "")
                values = list_portfolios(root)
                if not values:
                    _write(output, "No Portfolios exist yet.")
                for x in values:
                    _write(
                        output,
                        f"{x.title_snapshot or x.subject_display_label or '(untitled)'}",
                        f"  {x.portfolio_id}",
                    )
                _pause(input_fn)
            else:
                _write(output, "Please choose 1-3, H, B, M, or Q.")
                _pause(input_fn)
        except (ValueError, RuntimeError) as exc:
            clear_fn()
            _write(
                output,
                "Portfolio workflow problem",
                "",
                f"{getattr(exc, 'code', exc.__class__.__name__)}: {exc}",
            )
            _pause(input_fn)


__all__ = ["run_portfolio_menu"]
