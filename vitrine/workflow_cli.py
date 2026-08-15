"""Noninteractive Portfolio-centered CLI handlers."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TextIO

from pds_core.academic_catalog import PublicationCatalogQuery

from vitrine.audience_services import (
    create_audience_context,
    list_audience_contexts,
    show_audience_context,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.curation_services import (
    create_working_composition,
    decide_selection_proposal,
    invalidate_selection,
    place_selection,
    propose_candidate_selection,
    reorder_section,
    replace_selection,
    select_candidate_directly,
    withdraw_selection,
)
from vitrine.models import (
    ActorAttribution,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotSeries,
    record_from_dict,
    strict_json_loads,
)
from vitrine.portfolio_services import (
    create_portfolio,
    list_portfolios,
    observe_portfolio_state_revision,
    show_portfolio,
)
from vitrine.snapshot_distribution import (
    inspect_snapshot_custody,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.snapshot_services import (
    create_snapshot_series,
    execute_snapshot_build_attempt,
    plan_snapshot_build,
    request_snapshot_build,
    seal_snapshot_build_attempt,
    start_snapshot_build_attempt,
)
from vitrine.workflow_context import VitrineWorkflowDependencies
from vitrine.workflow_views import (
    list_candidate_summaries,
    list_snapshot_series,
    show_arrangement,
    show_candidate,
    show_composition,
    show_snapshot_series,
)


def _workspace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace-root", type=Path)


def _actor(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--actor-id", required=True)
    parser.add_argument(
        "--actor-kind",
        default="authorized_adult",
        choices=("authorized_adult", "system", "external_actor"),
    )
    parser.add_argument("--owning-system", default="local")
    parser.add_argument("--role", default="teacher")
    parser.add_argument("--expected-state-revision", type=int)
    _workspace(parser)


def _nested(
    root: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    help_text: str,
) -> argparse._SubParsersAction[argparse.ArgumentParser]:
    parser = root.add_parser(name, help=help_text)
    return parser.add_subparsers(dest=f"{name}_command", required=True)


def configure_workflow_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    portfolios = _nested(subparsers, "portfolio", "Create and inspect Portfolios.")
    p_list = portfolios.add_parser("list")
    _workspace(p_list)
    p_show = portfolios.add_parser("show")
    p_show.add_argument("portfolio_id")
    _workspace(p_show)
    p_create = portfolios.add_parser("create")
    p_create.add_argument("--subject-id", required=True)
    p_create.add_argument("--title")
    p_create.add_argument("--description")
    _actor(p_create)

    candidates = _nested(subparsers, "candidate", "Discover and review Candidates.")
    c_list = candidates.add_parser("list")
    c_list.add_argument("portfolio_id")
    _workspace(c_list)
    c_show = candidates.add_parser("show")
    c_show.add_argument("candidate_id")
    _workspace(c_show)
    discover = candidates.add_parser("discover")
    discover.add_argument("portfolio_id")
    discover.add_argument("--purpose", required=True)
    discover.add_argument("--school-year")
    discover.add_argument("--class-id")
    discover.add_argument("--module-id")
    discover.add_argument("--work-id")
    discover.add_argument(
        "--publication-state",
        default="current",
        choices=("current", "series_heads", "historical", "withdrawn", "all"),
    )
    discover.add_argument("--limit", type=int, default=100)
    _actor(discover)

    selections = _nested(subparsers, "selection", "Curate explicit Selections.")
    add = selections.add_parser("add")
    add.add_argument("portfolio_id")
    add.add_argument("candidate_id")
    add.add_argument("--section-id", action="append", required=True)
    add.add_argument("--reason")
    _actor(add)
    propose = selections.add_parser("propose")
    propose.add_argument("portfolio_id")
    propose.add_argument("candidate_id")
    propose.add_argument("--section-id", action="append", required=True)
    propose.add_argument("--origin", default="teacher")
    propose.add_argument("--reason")
    _actor(propose)
    decide = selections.add_parser("decide")
    decide.add_argument("portfolio_id")
    decide.add_argument("proposal_id")
    decide.add_argument(
        "--decision", required=True, choices=("accepted", "declined", "deferred")
    )
    decide.add_argument("--reason")
    _actor(decide)
    for lifecycle in ("withdraw", "invalidate"):
        action = selections.add_parser(lifecycle)
        action.add_argument("portfolio_id")
        action.add_argument("selection_id")
        action.add_argument("--reason", required=True)
        action.add_argument(
            "--pointer",
            action="append",
            default=[],
            metavar="SECTION_ID=REVISION_OR_NONE",
        )
        _actor(action)
    replace = selections.add_parser("replace")
    replace.add_argument("portfolio_id")
    replace.add_argument("selection_id")
    replace.add_argument("--candidate-id", required=True)
    replace.add_argument("--reason", required=True)
    replace.add_argument(
        "--pointer", action="append", default=[], metavar="SECTION_ID=REVISION_OR_NONE"
    )
    replace.add_argument(
        "--placement-disposition",
        action="append",
        default=[],
        metavar="PLACEMENT_ID=SECTION_ID_OR_NONE",
    )
    _actor(replace)

    arrangements = _nested(
        subparsers, "arrangement", "Place and explicitly order Selections."
    )
    a_show = arrangements.add_parser("show")
    a_show.add_argument("portfolio_id")
    a_show.add_argument("--section-id", required=True)
    _workspace(a_show)
    place = arrangements.add_parser("place")
    place.add_argument("portfolio_id")
    place.add_argument("selection_id")
    place.add_argument("--section-id", required=True)
    place.add_argument("--expected-arrangement-pointer-revision", type=int)
    _actor(place)
    reorder = arrangements.add_parser("reorder")
    reorder.add_argument("portfolio_id")
    reorder.add_argument("--section-id", required=True)
    reorder.add_argument("placement_ids", nargs="+")
    reorder.add_argument("--expected-arrangement-pointer-revision", type=int)
    _actor(reorder)

    compositions = _nested(
        subparsers, "composition", "Inspect or freeze Working Composition state."
    )
    comp_show = compositions.add_parser("show")
    comp_show.add_argument("portfolio_id")
    comp_show.add_argument("--revision", type=int)
    _workspace(comp_show)
    comp_build = compositions.add_parser("build")
    comp_build.add_argument("portfolio_id")
    comp_build.add_argument("--expected-composition-pointer-revision", type=int)
    comp_build.add_argument("--note")
    _actor(comp_build)

    audiences = _nested(subparsers, "audience", "Freeze exact Profile audience rules.")
    au_list = audiences.add_parser("list")
    au_list.add_argument("portfolio_id")
    _workspace(au_list)
    au_show = audiences.add_parser("show")
    au_show.add_argument("audience_context_id")
    _workspace(au_show)
    au_create = audiences.add_parser("create")
    au_create.add_argument("portfolio_id")
    au_create.add_argument("--audience-rule-id", required=True)
    _actor(au_create)

    snapshot = _nested(
        subparsers, "snapshot", "Prepare, build, and verify immutable Snapshots."
    )
    series = snapshot.add_parser("series")
    series_cmd = series.add_subparsers(dest="snapshot_series_command", required=True)
    s_list = series_cmd.add_parser("list")
    s_list.add_argument("portfolio_id")
    _workspace(s_list)
    s_show = series_cmd.add_parser("show")
    s_show.add_argument("snapshot_series_id")
    _workspace(s_show)
    s_create = series_cmd.add_parser("create")
    s_create.add_argument("portfolio_id")
    s_create.add_argument("--audience-context-id", required=True)
    s_create.add_argument("--purpose", required=True)
    _actor(s_create)
    request = snapshot.add_parser("request")
    request.add_argument("snapshot_series_id")
    request.add_argument("--composition-revision", type=int, required=True)
    request.add_argument("--idempotency-key")
    _actor(request)
    plan = snapshot.add_parser("plan")
    plan.add_argument("snapshot_build_request_id")
    plan.add_argument("--from-plan-json", type=Path, required=True)
    _actor(plan)
    build = snapshot.add_parser("build")
    build.add_argument("snapshot_build_plan_id")
    _actor(build)
    verify = snapshot.add_parser("verify")
    verify.add_argument("snapshot_series_id")
    verify.add_argument("--edition", type=int, required=True)
    _workspace(verify)
    edition = snapshot.add_parser("edition")
    edition_cmd = edition.add_subparsers(dest="snapshot_edition_command", required=True)
    edition_list = edition_cmd.add_parser("list")
    edition_list.add_argument("snapshot_series_id")
    _workspace(edition_list)
    edition_show = edition_cmd.add_parser("show")
    edition_show.add_argument("snapshot_series_id")
    edition_show.add_argument("--edition", type=int, required=True)
    _workspace(edition_show)
    export = snapshot.add_parser("export")
    export_cmd = export.add_subparsers(dest="snapshot_export_command", required=True)
    export_verify = export_cmd.add_parser("verify")
    export_verify.add_argument("export_artifact_id")
    _workspace(export_verify)
    custody = snapshot.add_parser("custody")
    _workspace(custody)


def _actor_value(args: argparse.Namespace) -> ActorAttribution:
    return ActorAttribution(
        actor_kind=args.actor_kind,
        actor_id=args.actor_id,
        owning_system=args.owning_system,
        role_snapshot=args.role,
    )


def _expected(args: argparse.Namespace) -> int | None:
    return (
        args.expected_state_revision
        if args.expected_state_revision is not None
        else observe_portfolio_state_revision(args.workspace_root)
    )


def _required_expected(args: argparse.Namespace) -> int:
    value = _expected(args)
    if value is None:
        raise ValueError(
            "state_not_initialized: this operation requires existing Vitrine state"
        )
    return value


def _mapping(values: list[str], *, integer_values: bool) -> dict[str, int | str | None]:
    result: dict[str, int | str | None] = {}
    for raw in values:
        key, separator, value = raw.partition("=")
        if not separator or not key or not value:
            raise ValueError("mapping arguments must use KEY=VALUE")
        if value.casefold() == "none":
            result[key] = None
        elif integer_values:
            result[key] = int(value)
        else:
            result[key] = value
    return result


def _plan_template(path: Path) -> SnapshotBuildPlan:
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("Snapshot Plan JSON must contain one object.")
    record = record_from_dict(value)
    if not isinstance(record, SnapshotBuildPlan):
        raise ValueError(
            "Snapshot Plan JSON must contain a snapshot_build_plan record."
        )
    return record


def run_workflow_command(
    args: argparse.Namespace,
    *,
    dependencies: VitrineWorkflowDependencies,
    output: TextIO,
) -> int:
    root = args.workspace_root
    command = args.command
    subcommand = getattr(args, f"{command}_command")
    if command == "portfolio":
        if subcommand == "list":
            for portfolio_summary in list_portfolios(root):
                print(
                    f"{portfolio_summary.portfolio_id}\t{portfolio_summary.title_snapshot or portfolio_summary.subject_display_label or '(untitled)'}\tsubject={portfolio_summary.portfolio_subject_id}",
                    file=output,
                )
        elif subcommand == "show":
            portfolio_summary = show_portfolio(root, args.portfolio_id).summary
            print(
                f"Portfolio: {portfolio_summary.portfolio_id}\nTitle: {portfolio_summary.title_snapshot or '(none)'}\nSubject: {portfolio_summary.portfolio_subject_id}\nProfile Binding: {portfolio_summary.profile_binding_id or '(none)'}\nCandidates: {portfolio_summary.candidate_count}\nActive Selections: {portfolio_summary.active_selection_count}\nCurrent Composition: {portfolio_summary.current_composition_revision or '(none)'}\nSnapshot Series: {portfolio_summary.snapshot_series_count}",
                file=output,
            )
        else:
            portfolio_result = create_portfolio(
                root,
                portfolio_subject_id=args.subject_id,
                created_by=_actor_value(args),
                expected_state_revision=_expected(args),
                title_snapshot=args.title,
                description_snapshot=args.description,
            )
            print(
                f"Created Portfolio: {portfolio_result.portfolio.portfolio_id}\nState revision: {portfolio_result.state_revision}",
                file=output,
            )
        return 0
    if command == "candidate":
        if subcommand == "list":
            for candidate_summary in list_candidate_summaries(root, args.portfolio_id):
                print(
                    f"{candidate_summary.candidate_id}\t{candidate_summary.condition_state}\t{candidate_summary.display_snapshot}\tselected={candidate_summary.active_selection_id or 'no'}",
                    file=output,
                )
        elif subcommand == "show":
            candidate = show_candidate(root, args.candidate_id)
            print(
                f"Candidate: {candidate.candidate_id}\nSummary: {candidate.display_snapshot}\nCondition: {candidate.condition_state}\nEligible sections: {', '.join(candidate.eligible_section_ids)}",
                file=output,
            )
        else:
            request = CandidateDiscoveryRequest(
                portfolio_id=args.portfolio_id,
                requesting_actor=_actor_value(args),
                requested_purpose=args.purpose,
                catalog_query=PublicationCatalogQuery(
                    school_year=args.school_year,
                    class_id=args.class_id,
                    module_id=args.module_id,
                    work_id=args.work_id,
                    state=args.publication_state,
                    limit=args.limit,
                ),
                expected_state_revision=_required_expected(args),
            )
            discovery_result = discover_and_evaluate_candidates(
                root,
                request,
                producer_registry=dependencies.producer_registry,
                adapter_registry=dependencies.adapter_registry,
                authorization_gate=dependencies.source_read_authorization_gate,
            )
            print(
                f"Proposed publications: {len(discovery_result.proposed_publication_ids)}\nEvaluated: {len(discovery_result.evaluation_results)}\nFindings: {len(discovery_result.findings)}",
                file=output,
            )
        return 0
    if command == "selection":
        expected_state = _required_expected(args)
        actor = _actor_value(args)
        if subcommand == "add":
            selection_result = select_candidate_directly(
                root,
                portfolio_id=args.portfolio_id,
                candidate_id=args.candidate_id,
                selected_by=actor,
                proposed_section_ids=tuple(args.section_id),
                expected_state_revision=expected_state,
                authority_gate=dependencies.curation_authority_gate,
                rationale_text=args.reason,
            )
        elif subcommand == "propose":
            selection_result = propose_candidate_selection(
                root,
                portfolio_id=args.portfolio_id,
                candidate_id=args.candidate_id,
                proposer=actor,
                proposal_origin=args.origin,
                proposed_section_ids=tuple(args.section_id),
                expected_state_revision=expected_state,
                authority_gate=dependencies.curation_authority_gate,
                rationale_text=args.reason,
            )
        elif subcommand == "decide":
            selection_result = decide_selection_proposal(
                root,
                portfolio_id=args.portfolio_id,
                selection_proposal_id=args.proposal_id,
                decision=args.decision,
                decided_by=actor,
                expected_state_revision=expected_state,
                authority_gate=dependencies.curation_authority_gate,
                rationale_text=args.reason,
            )
        else:
            pointers = _mapping(args.pointer, integer_values=True)
            expected_pointers = {
                key: value if isinstance(value, int) else None
                for key, value in pointers.items()
            }
            common = dict(
                workspace_root=root,
                portfolio_id=args.portfolio_id,
                selection_id=args.selection_id,
                expected_state_revision=expected_state,
                expected_pointer_revisions=expected_pointers,
                authority_gate=dependencies.curation_authority_gate,
                reason=args.reason,
            )
            if subcommand == "withdraw":
                selection_result = withdraw_selection(withdrawn_by=actor, **common)
            elif subcommand == "invalidate":
                selection_result = invalidate_selection(invalidated_by=actor, **common)
            else:
                dispositions = _mapping(
                    args.placement_disposition, integer_values=False
                )
                selection_result = replace_selection(
                    replaced_by=actor,
                    successor_candidate_id=args.candidate_id,
                    placement_dispositions={
                        key: value if isinstance(value, str) else None
                        for key, value in dispositions.items()
                    },
                    **common,
                )
        print(
            f"Selection recorded.\nState revision: {selection_result.state_revision}",
            file=output,
        )
        return 0
    if command == "arrangement":
        if subcommand == "show":
            arrangement_view = show_arrangement(
                root, args.portfolio_id, args.section_id
            )
            print(
                f"Section: {arrangement_view.section_id}\nPointer revision: {arrangement_view.pointer_revision or '(none)'}\nPlacement order: {', '.join(p.placement_id for p in arrangement_view.placements) or '(empty)'}",
                file=output,
            )
            return 0
        expected_state = _required_expected(args)
        pointer = args.expected_arrangement_pointer_revision
        if pointer is None:
            pointer = show_arrangement(
                root, args.portfolio_id, args.section_id
            ).pointer_revision
        if subcommand == "place":
            arrangement_result = place_selection(
                root,
                portfolio_id=args.portfolio_id,
                selection_id=args.selection_id,
                section_id=args.section_id,
                placed_by=_actor_value(args),
                expected_state_revision=expected_state,
                expected_arrangement_pointer_revision=pointer,
                authority_gate=dependencies.curation_authority_gate,
            )
        else:
            if pointer is None:
                raise ValueError(
                    "arrangement_pointer_missing: reorder requires an existing exact pointer"
                )
            arrangement_result = reorder_section(
                root,
                portfolio_id=args.portfolio_id,
                section_id=args.section_id,
                placement_ids=tuple(args.placement_ids),
                arranged_by=_actor_value(args),
                expected_state_revision=expected_state,
                expected_arrangement_pointer_revision=pointer,
                authority_gate=dependencies.curation_authority_gate,
            )
        print(
            f"Arrangement updated.\nState revision: {arrangement_result.state_revision}",
            file=output,
        )
        return 0
    if command == "composition":
        if subcommand == "show":
            composition_view = show_composition(root, args.portfolio_id, args.revision)
            composition = composition_view.composition
            print(
                "No Working Composition."
                if composition is None
                else f"Composition revision: {composition.composition_revision}\nSelections: {len(composition.selection_ids)}\nPlacements: {len(composition.placement_ids)}\nUnresolved: {', '.join(composition_view.inventory.unresolved_obligation_codes) if composition_view.inventory else '(inventory missing)'}",
                file=output,
            )
            return 0
        expected_state = _required_expected(args)
        pointer = args.expected_composition_pointer_revision
        if pointer is None:
            pointer = show_composition(root, args.portfolio_id).pointer_revision
        composition_result = create_working_composition(
            root,
            portfolio_id=args.portfolio_id,
            created_by=_actor_value(args),
            expected_state_revision=expected_state,
            expected_composition_pointer_revision=pointer,
            authority_gate=dependencies.curation_authority_gate,
            composition_note=args.note,
        )
        print(
            f"Working Composition frozen.\nState revision: {composition_result.state_revision}",
            file=output,
        )
        return 0
    if command == "audience":
        if subcommand == "list":
            for audience_context in list_audience_contexts(
                root, portfolio_id=args.portfolio_id
            ):
                print(
                    f"{audience_context.audience_context_id}\t{audience_context.audience_class}\t{audience_context.audience_rule_id}",
                    file=output,
                )
        elif subcommand == "show":
            audience_context = show_audience_context(root, args.audience_context_id)
            print(
                f"Audience Context: {audience_context.audience_context_id}\nClass: {audience_context.audience_class}\nRule: {audience_context.audience_rule_id}\nPurpose: {audience_context.purpose}\nDisclosure authorization: not represented",
                file=output,
            )
        else:
            audience_result = create_audience_context(
                root,
                portfolio_id=args.portfolio_id,
                audience_rule_id=args.audience_rule_id,
                created_by=_actor_value(args),
                expected_state_revision=_required_expected(args),
            )
            print(
                f"Created Audience Context: {audience_result.context.audience_context_id}\nState revision: {audience_result.state_revision}",
                file=output,
            )
        return 0
    if command == "snapshot":
        if subcommand == "edition":
            series_view = show_snapshot_series(root, args.snapshot_series_id)
            if args.snapshot_edition_command == "list":
                for edition_item in series_view.editions:
                    current = (
                        series_view.current_edition is not None
                        and series_view.current_edition.edition_number
                        == edition_item.edition_number
                    )
                    print(
                        f"{edition_item.edition_number}\tcomposition={edition_item.composition_revision}\tcurrent={'yes' if current else 'no'}",
                        file=output,
                    )
            else:
                exact_edition = next(
                    (
                        item
                        for item in series_view.editions
                        if item.edition_number == args.edition
                    ),
                    None,
                )
                if exact_edition is None:
                    raise ValueError("snapshot_edition_not_found: Edition not found")
                print(
                    f"Edition: {exact_edition.snapshot_series_id}:{exact_edition.edition_number}\nComposition: {exact_edition.composition_revision}\nManifest: {exact_edition.manifest_id}\nSeal: {exact_edition.seal_id}",
                    file=output,
                )
            return 0
        if subcommand == "export":
            export_verification = verify_snapshot_export(
                root, snapshot_export_artifact_id=args.export_artifact_id
            )
            print(
                f"Export verification: verified\nFiles: {len(export_verification.verified_file_paths)}",
                file=output,
            )
            return 0
        if subcommand == "custody":
            audit = inspect_snapshot_custody(root)
            print(f"Custody findings: {len(audit.findings)}", file=output)
            for finding in audit.findings:
                print(f"{finding.code}\t{finding.summary}", file=output)
            return 0
        if subcommand == "series":
            if args.snapshot_series_command == "list":
                for series_item in list_snapshot_series(root, args.portfolio_id):
                    print(
                        f"{series_item.snapshot_series_id}\t{series_item.snapshot_purpose}\taudience={series_item.audience_context_id}",
                        file=output,
                    )
            elif args.snapshot_series_command == "show":
                series_view = show_snapshot_series(root, args.snapshot_series_id)
                print(
                    f"Snapshot Series: {series_view.series.snapshot_series_id}\nRequests: {len(series_view.requests)}\nPlans: {len(series_view.plans)}\nAttempts: {len(series_view.attempts)}\nEditions: {len(series_view.editions)}\nCurrent pointer: {series_view.current_edition.edition_number if series_view.current_edition else '(none)'}",
                    file=output,
                )
            else:
                series_result = create_snapshot_series(
                    root,
                    portfolio_id=args.portfolio_id,
                    audience_context_id=args.audience_context_id,
                    snapshot_purpose=args.purpose,
                    created_by=_actor_value(args),
                    expected_state_revision=_required_expected(args),
                )
                series_record = series_result.records[0]
                if not isinstance(series_record, SnapshotSeries):
                    raise AssertionError(
                        "Snapshot Series service returned an invalid record."
                    )
                print(
                    f"Created Snapshot Series: {series_record.snapshot_series_id}\nState revision: {series_result.state_revision}",
                    file=output,
                )
        elif subcommand == "request":
            request_result = request_snapshot_build(
                root,
                snapshot_series_id=args.snapshot_series_id,
                composition_revision=args.composition_revision,
                requested_by=_actor_value(args),
                expected_state_revision=_required_expected(args),
                idempotency_key=args.idempotency_key,
            )
            request_record = request_result.records[0]
            if not isinstance(request_record, SnapshotBuildRequest):
                raise AssertionError(
                    "Snapshot Request service returned an invalid record."
                )
            print(
                f"Created Build Request: {request_record.snapshot_build_request_id}\nState revision: {request_result.state_revision}",
                file=output,
            )
        elif subcommand == "plan":
            template = _plan_template(args.from_plan_json)
            plan_result = plan_snapshot_build(
                root,
                snapshot_build_request_id=args.snapshot_build_request_id,
                entry_plans=template.entry_plans,
                export_plans=template.export_plans,
                planned_by=_actor_value(args),
                expected_state_revision=_required_expected(args),
                acknowledged_obligation_codes=template.acknowledged_obligation_codes,
                predecessor_plan_id=template.predecessor_plan_id,
                builder_contract_id=template.builder_contract_id,
                builder_contract_version=template.builder_contract_version,
                path_policy_id=template.path_policy_id,
                digest_policy_id=template.digest_policy_id,
            )
            plan_record = plan_result.records[0]
            if not isinstance(plan_record, SnapshotBuildPlan):
                raise AssertionError(
                    "Snapshot Plan service returned an invalid record."
                )
            print(
                f"Created Build Plan: {plan_record.snapshot_build_plan_id}\nState revision: {plan_result.state_revision}",
                file=output,
            )
        elif subcommand == "build":
            start = start_snapshot_build_attempt(
                root,
                snapshot_build_plan_id=args.snapshot_build_plan_id,
                started_by=_actor_value(args),
                expected_state_revision=_required_expected(args),
            )
            execution = execute_snapshot_build_attempt(
                root,
                snapshot_build_attempt_id=start.attempt.snapshot_build_attempt_id,
                expected_state_revision=start.state_revision,
                authority_gate=dependencies.snapshot_build_authority_gate,
                source_providers=dependencies.snapshot_source_providers,
                renderers=dependencies.snapshot_renderers,
            )
            sealed = seal_snapshot_build_attempt(
                root,
                execution=execution,
                expected_state_revision=execution.state_revision,
                sealed_by=_actor_value(args),
            )
            print(
                f"Sealed Edition: {sealed.edition.snapshot_series_id}:{sealed.edition.edition_number}\nState revision: {sealed.state_revision}",
                file=output,
            )
        else:
            verification = verify_snapshot_edition(
                root,
                snapshot_series_id=args.snapshot_series_id,
                edition_number=args.edition,
            )
            print(
                f"Edition verification: verified\nEntries: {len(verification.verified_entry_ids)}",
                file=output,
            )
            return 0
        return 0
    raise AssertionError(f"Unhandled workflow command: {command}")


__all__ = ["configure_workflow_parsers", "run_workflow_command"]
