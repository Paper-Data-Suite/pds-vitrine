"""Low-density Portfolio-centered teacher workflow."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TextIO

from pds_core.academic_catalog import PublicationCatalogQuery
from pds_core.menu_navigation import NavigationChoice, parse_navigation_choice
from pds_core.workspace import resolve_workspace_root

from vitrine.audience_services import create_audience_context, list_audience_contexts
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.curation_services import (
    create_working_composition,
    place_selection,
    reorder_section,
    select_candidate_directly,
)
from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import (
    ActorAttribution,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotSeries,
)
from vitrine.portfolio_services import (
    create_portfolio,
    list_portfolios,
    observe_portfolio_state_revision,
    show_portfolio,
)
from vitrine.profile_services import (
    ProfileBindingContext,
    bind_portfolio_profile,
    get_portfolio_profile_binding,
    get_profile_revision,
    list_bindable_profile_revisions,
    observe_profile_state_revision,
)
from vitrine.snapshot_distribution import (
    inspect_snapshot_custody,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.snapshot_planning import SnapshotPlanningRequest, prepare_snapshot_build
from vitrine.snapshot_services import (
    create_snapshot_series,
    execute_snapshot_build_attempt,
    request_snapshot_build,
    seal_snapshot_build_attempt,
    start_snapshot_build_attempt,
)
from vitrine.subject_services import list_subjects, show_subject
from vitrine.workflow_context import VitrineWorkflowDependencies
from vitrine.workflow_views import (
    list_active_selections,
    list_candidate_summaries,
    list_snapshot_series,
    show_arrangement,
    show_candidate_detail,
    show_composition,
    show_snapshot_series,
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
    input_fn("Press Enter to continue...")


def _navigation(value: str) -> NavigationChoice | None:
    return parse_navigation_choice(
        value, allow_back=True, allow_main_menu=True, allow_quit=True
    )


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
    if _navigation(raw) is NavigationChoice.BACK:
        return None
    try:
        return values[int(raw) - 1].portfolio_id
    except (ValueError, IndexError):
        _write(output, "That Portfolio number is not available.")
        _pause(input_fn)
        return None


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
            "3. Discover / Review Candidates",
            "4. Curate Selections / Arrange Sections",
            "5. Working Composition",
            "6. Snapshot",
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
            subject = show_subject(root, detail.summary.portfolio_subject_id)
            for link in subject.current_links:
                _write(
                    output,
                    f"Subject link: {link.subject_link_id} — "
                    f"{link.reference.class_id}/{link.reference.student_id}",
                )
        elif choice == "2":
            _write(output, "Profile Binding", "")
            binding = get_portfolio_profile_binding(root, portfolio_id)
            if binding is not None:
                _write(
                    output,
                    f"Exact Binding: {binding.profile_binding_id}",
                    "Profile Revision: "
                    f"{binding.profile_revision.portfolio_profile_id}:"
                    f"{binding.profile_revision.profile_revision}",
                )
            else:
                observed_revision = observe_profile_state_revision(root)
                revisions = list_bindable_profile_revisions(root)
                for index, item in enumerate(revisions, 1):
                    _write(
                        output,
                        f"{index}. {item.label}",
                        f"   {item.reference.portfolio_profile_id}:"
                        f"{item.reference.profile_revision}",
                    )
                raw = _read(input_fn, "Profile number (Enter to leave unbound): ")
                if raw:
                    selected = revisions[int(raw) - 1]
                    mutation_actor = actor or _actor(input_fn)
                    as_of_text = _read(
                        input_fn, "As-of date YYYY-MM-DD (optional): "
                    )
                    context = ProfileBindingContext(
                        as_of=date.fromisoformat(as_of_text) if as_of_text else None,
                        school_year=_read(input_fn, "School year (optional): ") or None,
                        institution_id=_read(
                            input_fn, "Institution ID (optional): "
                        )
                        or None,
                        program_id=_read(input_fn, "Program ID (optional): ") or None,
                        content_area=_read(input_fn, "Content area (optional): ")
                        or None,
                    )
                    binding_reason = (
                        _read(input_fn, "Binding reason: ") or "teacher_selected"
                    )
                    if (
                        mutation_actor is not None
                        and _read(
                            input_fn,
                            "Type BIND to bind this exact Profile Revision and context: ",
                        )
                        == "BIND"
                    ):
                        bind_portfolio_profile(
                            root,
                            portfolio_id,
                            selected.reference,
                            actor=mutation_actor,
                            binding_reason=binding_reason,
                            context=context,
                            expected_state_revision=observed_revision,
                        )
                        _write(output, "Profile Binding recorded.")
        elif choice == "3":
            _write(output, "Review Candidates", "")
            if (
                _read(
                    input_fn,
                    "Type DISCOVER to query configured Candidate sources, or Enter to review: ",
                )
                == "DISCOVER"
            ):
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
                            expected_state_revision=observe_portfolio_state_revision(
                                root
                            )
                            or 0,
                        ),
                        producer_registry=dependencies.producer_registry,
                        adapter_registry=dependencies.adapter_registry,
                        authorization_gate=dependencies.source_read_authorization_gate,
                    )
                    for finding in discovery.findings:
                        _write(output, f"{finding.code} — stage {finding.stage}")
            observed_revision = observe_portfolio_state_revision(root)
            candidates = list_candidate_summaries(root, portfolio_id)
            if not candidates:
                _write(
                    output,
                    "No Candidates. Discovery requires configured source-read integration and authority.",
                )
            for index, candidate_item in enumerate(candidates, 1):
                _write(
                    output,
                    f"{index}. {candidate_item.display_snapshot}",
                    f"   {candidate_item.candidate_id} — {candidate_item.condition_state}",
                )
            if candidates:
                raw = _read(
                    input_fn,
                    "Candidate number to review (Enter to leave unchanged): ",
                )
                if raw:
                    try:
                        candidate_item = candidates[int(raw) - 1]
                    except (ValueError, IndexError):
                        _write(output, "That Candidate number is not available.")
                    else:
                        clear_fn()
                        candidate_detail = show_candidate_detail(
                            root, candidate_item.candidate_id
                        )
                        _write(
                            output,
                            "Candidate Review",
                            "",
                            candidate_item.display_snapshot,
                            f"Candidate ID: {candidate_item.candidate_id}",
                            f"Candidate Evaluation ID: {candidate_detail.candidate_evaluation_id}",
                            "Core Publication ID: "
                            f"{candidate_detail.source_endpoint.core_publication.publication_id}",
                            "Producer source: "
                            f"{candidate_detail.source_endpoint.producer_source.producer_module_id}:"
                            f"{candidate_detail.source_endpoint.producer_source.source_record_id}",
                            f"Condition: {candidate_item.condition_state}",
                            "Unresolved codes: "
                            f"{', '.join(candidate_detail.unresolved_condition_codes) or '(none)'}",
                            f"Eligible sections: {', '.join(candidate_item.eligible_section_ids)}",
                            "",
                            "Reviewing a Candidate does not select it.",
                        )
                        acknowledged = True
                        if candidate_detail.unresolved_condition_codes:
                            _write(
                                output,
                                "Acknowledgement does not satisfy a separate Profile review requirement.",
                            )
                            acknowledged = (
                                _read(
                                    input_fn,
                                    "Type ACKNOWLEDGE to confirm you reviewed these conditions: ",
                                )
                                == "ACKNOWLEDGE"
                            )
                        if acknowledged and (
                            _read(
                                input_fn,
                                "Type SELECT to select this Candidate, or Enter to leave unchanged: ",
                            )
                            == "SELECT"
                        ):
                            mutation_actor = actor or _actor(input_fn)
                            if (
                                mutation_actor is not None
                                and observed_revision is not None
                            ):
                                sections = tuple(
                                    item.strip()
                                    for item in _read(
                                        input_fn,
                                        "Section IDs (comma-separated): ",
                                    ).split(",")
                                    if item.strip()
                                )
                                result = select_candidate_directly(
                                    root,
                                    portfolio_id=portfolio_id,
                                    candidate_id=candidate_item.candidate_id,
                                    selected_by=mutation_actor,
                                    proposed_section_ids=sections,
                                    expected_state_revision=observed_revision,
                                    authority_gate=dependencies.curation_authority_gate,
                                )
                                _write(
                                    output,
                                    "",
                                    f"Selection recorded at state revision {result.state_revision}.",
                                )
        elif choice == "4":
            _write(output, "Curate Selections", "")
            selections = list_active_selections(root, portfolio_id)
            if not selections:
                _write(
                    output,
                    "No active Selections. Selecting a Candidate always requires explicit confirmation and curation authority.",
                )
            for selection_item in selections:
                _write(
                    output,
                    f"{selection_item.selection_id} — Candidate {selection_item.candidate_id}",
                )
            if selections:
                raw = _read(
                    input_fn, "Selection number to place (Enter to inspect only): "
                )
                if raw:
                    selection_item = selections[int(raw) - 1]
                    section_id = _read(input_fn, "Exact section ID: ")
                    arrangement = show_arrangement(root, portfolio_id, section_id)
                    observed = observe_portfolio_state_revision(root)
                    mutation_actor = actor or _actor(input_fn)
                    if (
                        mutation_actor is not None
                        and _read(input_fn, "Type PLACE to place this Selection: ")
                        == "PLACE"
                    ):
                        place_selection(
                            root,
                            portfolio_id=portfolio_id,
                            selection_id=selection_item.selection_id,
                            section_id=section_id,
                            placed_by=mutation_actor,
                            expected_state_revision=observed or 0,
                            expected_arrangement_pointer_revision=arrangement.pointer_revision,
                            authority_gate=dependencies.curation_authority_gate,
                        )
                        _write(output, "Selection placed.")
                section_id = _read(
                    input_fn, "Section ID to reorder (Enter to finish): "
                )
                if section_id:
                    arrangement = show_arrangement(root, portfolio_id, section_id)
                    observed = observe_portfolio_state_revision(root)
                    for index, placement in enumerate(arrangement.placements, 1):
                        _write(output, f"{index}. {placement.placement_id}")
                    order = tuple(
                        item.strip()
                        for item in _read(
                            input_fn,
                            "Placement IDs in exact order (comma-separated): ",
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
                        reorder_section(
                            root,
                            portfolio_id=portfolio_id,
                            section_id=section_id,
                            placement_ids=order,
                            arranged_by=mutation_actor,
                            expected_state_revision=observed or 0,
                            expected_arrangement_pointer_revision=arrangement.pointer_revision
                            or 0,
                            authority_gate=dependencies.curation_authority_gate,
                        )
                        _write(output, "Section reordered.")
        elif choice == "5":
            _write(output, "Working Composition", "")
            composition_view = show_composition(root, portfolio_id)
            if composition_view.composition is None:
                _write(output, "No Working Composition has been frozen.")
            else:
                _write(
                    output,
                    f"Revision: {composition_view.composition.composition_revision}",
                    f"Placements: {len(composition_view.composition.placement_ids)}",
                    f"Unresolved: {', '.join(composition_view.inventory.unresolved_obligation_codes) if composition_view.inventory else 'inventory missing'}",
                )
            observed = observe_portfolio_state_revision(root)
            if (
                _read(
                    input_fn,
                    "Type FREEZE to create an exact Working Composition, or Enter: ",
                )
                == "FREEZE"
            ):
                mutation_actor = actor or _actor(input_fn)
                if mutation_actor is not None:
                    result = create_working_composition(
                        root,
                        portfolio_id=portfolio_id,
                        created_by=mutation_actor,
                        expected_state_revision=observed or 0,
                        expected_composition_pointer_revision=composition_view.pointer_revision,
                        authority_gate=dependencies.curation_authority_gate,
                    )
                    _write(
                        output,
                        f"Working Composition frozen at state revision {result.state_revision}.",
                    )
        elif choice == "6":
            _write(output, "Snapshot", "")
            _write(
                output,
                "1. Snapshot Overview",
                "2. Create Audience Context",
                "3. Create Snapshot Series",
                "4. Prepare Snapshot",
                "5. Build Prepared Snapshot",
                "6. View / Verify Edition",
                "7. Verify Export",
                "8. Snapshot Diagnostics",
            )
            series_values = list_snapshot_series(root, portfolio_id)
            if not series_values:
                _write(
                    output,
                    "No Snapshot Series. A Snapshot requires an exact Audience Context and frozen Composition.",
                )
            for series_item in series_values:
                series_view = show_snapshot_series(root, series_item.snapshot_series_id)
                _write(
                    output,
                    f"{series_item.snapshot_series_id} — {series_item.snapshot_purpose}",
                    f"  Editions: {len(series_view.editions)}; current pointer: {series_view.current_edition.edition_number if series_view.current_edition else 'none'}",
                )
            snapshot_choice = _read(input_fn, "Snapshot action (Enter for overview): ")
            mutation_actor = actor or (
                _actor(input_fn) if snapshot_choice in {"2", "3", "4", "5"} else None
            )
            if snapshot_choice == "2" and mutation_actor is not None:
                binding = get_portfolio_profile_binding(root, portfolio_id)
                if binding is None:
                    raise ValueError(
                        "profile_binding_missing: bind an exact Profile first"
                    )
                revision = get_profile_revision(root, binding.profile_revision)
                for index, rule in enumerate(revision.audience_rules, 1):
                    _write(
                        output,
                        f"{index}. {rule.audience_class} — {rule.purpose}",
                        f"   {rule.audience_rule_id}",
                    )
                rule = revision.audience_rules[
                    int(_read(input_fn, "Audience rule number: ")) - 1
                ]
                observed = observe_portfolio_state_revision(root)
                if (
                    _read(
                        input_fn,
                        "Type CREATE to freeze this Audience Context (not disclosure authorization): ",
                    )
                    == "CREATE"
                ):
                    audience_result = create_audience_context(
                        root,
                        portfolio_id=portfolio_id,
                        audience_rule_id=rule.audience_rule_id,
                        created_by=mutation_actor,
                        expected_state_revision=observed or 0,
                    )
                    _write(
                        output,
                        f"Audience Context: {audience_result.context.audience_context_id}",
                    )
            elif snapshot_choice == "3" and mutation_actor is not None:
                audiences = list_audience_contexts(root, portfolio_id=portfolio_id)
                for index, audience_item in enumerate(audiences, 1):
                    _write(
                        output,
                        f"{index}. {audience_item.audience_class} — "
                        f"{audience_item.audience_context_id}",
                    )
                audience_context = audiences[
                    int(_read(input_fn, "Audience Context number: ")) - 1
                ]
                observed = observe_portfolio_state_revision(root)
                series_result = create_snapshot_series(
                    root,
                    portfolio_id=portfolio_id,
                    audience_context_id=audience_context.audience_context_id,
                    snapshot_purpose=_read(input_fn, "Snapshot purpose: "),
                    created_by=mutation_actor,
                    expected_state_revision=observed or 0,
                )
                record = series_result.records[0]
                if isinstance(record, SnapshotSeries):
                    _write(output, f"Snapshot Series: {record.snapshot_series_id}")
            elif snapshot_choice == "4" and mutation_actor is not None:
                series_id = _read(input_fn, "Exact Snapshot Series ID: ")
                composition_revision = int(
                    _read(input_fn, "Exact Composition revision: ")
                )
                observed = observe_portfolio_state_revision(root)
                request_result = request_snapshot_build(
                    root,
                    snapshot_series_id=series_id,
                    composition_revision=composition_revision,
                    requested_by=mutation_actor,
                    expected_state_revision=observed or 0,
                )
                request_record = request_result.records[0]
                if not isinstance(request_record, SnapshotBuildRequest):
                    raise RuntimeError(
                        "Snapshot Request service returned an invalid record."
                    )
                plan_result = prepare_snapshot_build(
                    root,
                    SnapshotPlanningRequest(
                        request_record.snapshot_build_request_id,
                        mutation_actor,
                        request_result.state_revision,
                    ),
                    provider=dependencies.snapshot_planning_provider,
                )
                plan_record = plan_result.records[0]
                if not isinstance(plan_record, SnapshotBuildPlan):
                    raise RuntimeError("Snapshot planning returned an invalid record.")
                clear_fn()
                _write(
                    output,
                    "Snapshot Prepared",
                    f"Build Request ID: {request_record.snapshot_build_request_id}",
                    f"Build Plan ID: {plan_record.snapshot_build_plan_id}",
                    f"Entry plans: {len(plan_record.entry_plans)}",
                    f"Export plans: {len(plan_record.export_plans)}",
                    "Request != Plan; preparation has not built an Edition.",
                )
            elif snapshot_choice == "5" and mutation_actor is not None:
                plan_id = _read(input_fn, "Exact immutable Build Plan ID: ")
                observed = observe_portfolio_state_revision(root)
                if (
                    _read(input_fn, "Type BUILD to execute this exact Plan: ")
                    == "BUILD"
                ):
                    started = start_snapshot_build_attempt(
                        root,
                        snapshot_build_plan_id=plan_id,
                        started_by=mutation_actor,
                        expected_state_revision=observed or 0,
                    )
                    execution = execute_snapshot_build_attempt(
                        root,
                        snapshot_build_attempt_id=started.attempt.snapshot_build_attempt_id,
                        expected_state_revision=started.state_revision,
                        authority_gate=dependencies.snapshot_build_authority_gate,
                        source_providers=dependencies.snapshot_source_providers,
                        renderers=dependencies.snapshot_renderers,
                    )
                    sealed = seal_snapshot_build_attempt(
                        root,
                        execution=execution,
                        expected_state_revision=execution.state_revision,
                        sealed_by=mutation_actor,
                    )
                    _write(
                        output,
                        f"Sealed Edition: {sealed.edition.snapshot_series_id}:{sealed.edition.edition_number}",
                    )
            elif snapshot_choice == "6":
                series_id = _read(input_fn, "Exact Snapshot Series ID: ")
                edition_number = int(_read(input_fn, "Exact Edition number: "))
                verified = verify_snapshot_edition(
                    root, snapshot_series_id=series_id, edition_number=edition_number
                )
                _write(
                    output,
                    "Edition verification: verified",
                    f"Entries: {len(verified.verified_entry_ids)}",
                )
            elif snapshot_choice == "7":
                export_id = _read(input_fn, "Exact Export Artifact ID: ")
                export_verified = verify_snapshot_export(
                    root, snapshot_export_artifact_id=export_id
                )
                _write(
                    output,
                    "Export verification: verified",
                    f"Files: {len(export_verified.verified_file_paths)}",
                )
            elif snapshot_choice == "8":
                audit = inspect_snapshot_custody(root)
                for custody_finding in audit.findings:
                    _write(
                        output, f"{custody_finding.code} — {custody_finding.summary}"
                    )
        else:
            _write(output, "Please choose 1-6, H, B, M, or Q.")
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
            "1. Create Portfolio",
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
                "Create a Portfolio for one exact current Portfolio Subject.",
                "Choosing a Profile remains a separate action.",
            )
            _pause(input_fn)
            continue
        if _navigation(choice) is not None:
            return
        try:
            if choice == "1":
                clear_fn()
                _write(output, "Create Portfolio", "")
                observed_revision = observe_portfolio_state_revision(root)
                subjects = tuple(
                    item for item in list_subjects(root) if item.status == "current"
                )
                for index, item in enumerate(subjects, 1):
                    _write(
                        output,
                        f"{index}. {item.display_name or '(unnamed Subject)'}",
                        f"   {item.portfolio_subject_id}",
                    )
                raw_subject = _read(input_fn, "Subject number (B to cancel): ")
                if _navigation(raw_subject) is not None:
                    continue
                try:
                    selected_subject = subjects[int(raw_subject) - 1]
                except (ValueError, IndexError):
                    _write(output, "That Subject number is not available.")
                    _pause(input_fn)
                    continue
                subject_id = selected_subject.portfolio_subject_id
                _write(
                    output,
                    f"Selected Subject: {selected_subject.display_name or '(unnamed Subject)'}",
                    f"Exact Subject ID: {subject_id}",
                )
                title = _read(input_fn, "Title (optional): ") or None
                description = _read(input_fn, "Description (optional): ") or None
                if session_actor is None:
                    session_actor = _actor(input_fn)
                if session_actor is None:
                    continue
                confirmation = _read(input_fn, "Type CREATE to create this Portfolio: ")
                if confirmation != "CREATE":
                    continue
                result = create_portfolio(
                    root,
                    portfolio_subject_id=subject_id,
                    created_by=session_actor,
                    expected_state_revision=observed_revision,
                    title_snapshot=title,
                    description_snapshot=description,
                )
                clear_fn()
                _write(output, "Portfolio Created", "", result.portfolio.portfolio_id)
                _pause(input_fn)
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
