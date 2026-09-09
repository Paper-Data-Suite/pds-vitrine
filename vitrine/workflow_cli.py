"""Noninteractive Portfolio-centered CLI handlers."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from typing import TextIO

from pds_core.academic_catalog import PublicationCatalogQuery

from vitrine.audience_services import (
    create_audience_context,
    list_audience_contexts,
    show_audience_context,
)
from vitrine.candidate_inbox import (
    CandidateInboxDetail,
    CandidateInboxItem,
    CandidateInboxQuery,
    get_candidate_inbox_detail,
    list_candidate_inbox,
)
from vitrine.candidate_review_cli import (
    CANDIDATE_REVIEW_CLI_COMMANDS,
    configure_candidate_review_parsers,
    run_candidate_review_command,
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
from vitrine.current_portfolio_cli import (
    configure_current_portfolio_build_export_parsers,
    run_current_portfolio_build_export_command,
)
from vitrine.models import (
    ActorAttribution,
    CandidateSourceEndpoint,
    ClassQualifiedStudentRef,
    ProfileRevisionRef,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotSeries,
    strict_json_loads,
)
from vitrine.portfolio_services import (
    create_portfolio,
    list_portfolios,
    observe_portfolio_state_revision,
    show_portfolio,
)
from vitrine.portfolio_setup import (
    CreatePortfolioForStudentRequest,
    PortfolioSetupError,
    PortfolioSetupPlan,
    create_portfolio_for_student,
    plan_create_portfolio_for_student,
)
from vitrine.profile_services import ProfileBindingContext
from vitrine.snapshot_distribution import (
    inspect_snapshot_custody,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.snapshot_planning import (
    SnapshotPlanningError,
    SnapshotPlanningRequest,
    SnapshotPlanSpecification,
    prepare_snapshot_build,
    snapshot_plan_specification_from_dict,
)
from vitrine.snapshot_services import (
    create_snapshot_series,
    execute_snapshot_build_attempt,
    request_snapshot_build,
    seal_snapshot_build_attempt,
    start_snapshot_build_attempt,
)
from vitrine.subject_services import IdentityDecisionContext
from vitrine.workflow_context import VitrineWorkflowDependencies
from vitrine.workflow_views import (
    list_candidate_summaries,
    list_snapshot_series,
    show_arrangement,
    show_candidate_detail,
    show_composition,
    show_snapshot_plan,
    show_snapshot_series,
)
from vitrine.working_composition_cli import (
    WORKING_COMPOSITION_CLI_COMMANDS,
    configure_working_composition_parsers,
    run_working_composition_command,
)
from vitrine.workspace import show_workspace


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
    configure_current_portfolio_build_export_parsers(portfolios)

    p_setup = portfolios.add_parser(
        "create-for-student",
        help="Plan or create a Portfolio from one exact Core roster student.",
    )
    p_setup.add_argument("--class-id", required=True)
    p_setup.add_argument("--school-year", required=True)
    p_setup.add_argument("--student-id", required=True)
    p_setup.add_argument(
        "--purpose",
        required=True,
        choices=("improvement", "showcase"),
    )
    p_setup.add_argument("--profile-id", required=True)
    p_setup.add_argument("--profile-revision", required=True, type=int)
    subject_mode = p_setup.add_mutually_exclusive_group()
    subject_mode.add_argument("--new-subject", action="store_true")
    subject_mode.add_argument("--existing-subject-id")
    p_setup.add_argument(
        "--identity-basis-type",
        choices=(
            "direct_teacher_knowledge",
            "verified_sis_information",
            "authorized_institutional_crosswalk",
            "student_confirmation",
            "other_authorized_basis",
        ),
    )
    p_setup.add_argument("--identity-basis-summary")
    p_setup.add_argument(
        "--identity-authority-source",
        default="local_teacher_workflow",
    )
    p_setup.add_argument("--institution-id")
    p_setup.add_argument("--program-id")
    p_setup.add_argument("--content-area")
    p_setup.add_argument("--as-of")
    p_setup.add_argument("--title")
    p_setup.add_argument("--description")
    p_setup.add_argument("--dry-run", action="store_true")
    _actor(p_setup)

    candidates = _nested(subparsers, "candidate", "Discover and review Candidates.")
    c_list = candidates.add_parser("list")
    c_list.add_argument("portfolio_id")
    _workspace(c_list)
    c_show = candidates.add_parser("show")
    c_show.add_argument("candidate_id")
    _workspace(c_show)
    inbox = candidates.add_parser(
        "inbox",
        help="Review current Candidate and Evaluation inbox state.",
    )
    inbox_subcommands = inbox.add_subparsers(
        dest="candidate_inbox_command",
    )
    inbox.add_argument("--portfolio-id")
    inbox.add_argument("--subject-id")
    inbox.add_argument("--purpose")
    inbox.add_argument(
        "--outcome",
        action="append",
        default=[],
        metavar="OUTCOME",
    )
    inbox.add_argument(
        "--condition",
        action="append",
        default=[],
        metavar="CONDITION",
    )
    inbox.add_argument("--attention-only", action="store_true")
    inbox.add_argument("--stale-only", action="store_true")
    inbox.add_argument(
        "--selected-state",
        choices=("selected", "unselected", "historical_only"),
    )
    inbox.add_argument("--module-id")
    inbox.add_argument(
        "--evaluated-since",
        metavar="ISO_DATETIME",
    )
    inbox.add_argument("--limit", type=int, default=100)
    _workspace(inbox)

    inbox_show = inbox_subcommands.add_parser(
        "show",
        help="Show exact persisted provenance for one inbox entry.",
    )
    inbox_show.add_argument("entry_id")
    _workspace(inbox_show)
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
    configure_candidate_review_parsers(candidates)

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
        "--decision",
        required=True,
        choices=("accepted", "rejected", "changes_requested", "withdrawn", "expired"),
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
    configure_working_composition_parsers(compositions)

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
    plan_show = snapshot.add_parser("plan-show")
    plan_show.add_argument("snapshot_build_plan_id")
    _workspace(plan_show)
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


def _inbox_datetime(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError as error:
        raise ValueError(
            "evaluated_since_invalid: --evaluated-since must be an ISO datetime"
        ) from error


def _inbox_query(args: argparse.Namespace) -> CandidateInboxQuery:
    return CandidateInboxQuery(
        portfolio_id=args.portfolio_id,
        portfolio_subject_id=args.subject_id,
        profile_purpose=args.purpose,
        evaluation_outcomes=tuple(args.outcome),
        candidate_conditions=tuple(args.condition),
        attention_only=args.attention_only,
        stale_only=args.stale_only,
        selected_state=args.selected_state,
        producer_module_id=args.module_id,
        evaluated_since=_inbox_datetime(args.evaluated_since),
        limit=args.limit,
    )


def _teacher_label(value: str | None) -> str:
    if value is None:
        return "Unavailable"
    return value.replace("_", " ").strip().title()


def _selection_label(item: CandidateInboxItem) -> str:
    if item.selected_state == "selected":
        return "Selected"
    if item.selected_state == "historical_only":
        return "Historical selection only"
    return "Not selected"


def _print_candidate_inbox_item(
    item: CandidateInboxItem,
    *,
    output: TextIO,
) -> None:
    outcome = _teacher_label(item.evaluation_outcome)
    condition = (
        ""
        if item.candidate_condition is None
        else f" | {_teacher_label(item.candidate_condition)}"
    )
    freshness = _teacher_label(item.stale_state)
    attention = " | Attention needed" if item.attention_needed else ""
    print(
        (
            f"{item.entry_id}\t{outcome}{condition} | {freshness}"
            f"{attention} | {_selection_label(item)}\t"
            f"{item.source_display_label}"
        ),
        file=output,
    )


def _detail_endpoint(
    detail: CandidateInboxDetail,
) -> CandidateSourceEndpoint | None:
    if detail.evaluation is not None and detail.evaluation.source_endpoint is not None:
        return detail.evaluation.source_endpoint
    if detail.candidate is not None:
        return detail.candidate.source_endpoint
    return None


def _print_candidate_inbox_detail(
    detail: CandidateInboxDetail,
    *,
    output: TextIO,
) -> None:
    item = detail.item
    endpoint = _detail_endpoint(detail)
    print(f"Candidate Inbox Entry: {item.entry_id}", file=output)
    print(f"Source: {item.source_display_label}", file=output)
    print(
        f"Outcome: {_teacher_label(item.evaluation_outcome)}",
        file=output,
    )
    print(
        f"Condition: {_teacher_label(item.candidate_condition)}",
        file=output,
    )
    print(
        f"Currentness: {_teacher_label(item.stale_state)}",
        file=output,
    )
    print(
        (f"Stale reasons: {', '.join(item.stale_reason_codes) or '(none)'}"),
        file=output,
    )
    print(
        (f"Attention: {'yes' if item.attention_needed else 'no'}"),
        file=output,
    )
    print(
        (f"Attention reasons: {', '.join(item.attention_reason_codes) or '(none)'}"),
        file=output,
    )
    print(f"Selection: {_selection_label(item)}", file=output)
    print(f"Portfolio: {item.portfolio_id}", file=output)
    print(f"Portfolio label: {item.portfolio_label}", file=output)
    print(f"Subject: {item.portfolio_subject_id}", file=output)
    print(f"Subject label: {item.subject_label}", file=output)
    print(f"Profile Binding: {item.profile_binding_id}", file=output)
    print(
        (
            f"Profile: {item.portfolio_profile_id}"
            f"@{item.profile_revision} ({item.profile_label})"
        ),
        file=output,
    )
    print(f"Profile purpose: {item.profile_purpose}", file=output)
    print(
        (
            "Current Candidate Evaluation: "
            f"{item.current_evaluation_id or '(unresolved)'}"
        ),
        file=output,
    )
    print(
        f"Current resolution: {item.current_resolution}",
        file=output,
    )
    print(
        (f"Eligible sections: {', '.join(item.eligible_section_ids) or '(none)'}"),
        file=output,
    )
    print(
        (f"Active Selections: {', '.join(item.active_selection_ids) or '(none)'}"),
        file=output,
    )
    print(
        (
            "Historical Selections: "
            f"{', '.join(item.historical_selection_ids) or '(none)'}"
        ),
        file=output,
    )

    if endpoint is None:
        print("Core Publication: (unavailable)", file=output)
        print("Producer source: (unavailable)", file=output)
        print("Artifact: (unavailable)", file=output)
        print("Subject relationships: (unavailable)", file=output)
    else:
        publication = endpoint.core_publication
        producer = endpoint.producer_source
        artifact = endpoint.source_artifact
        print(
            f"Core Publication: {publication.publication_id}",
            file=output,
        )
        print(
            f"Producer module: {producer.producer_module_id}",
            file=output,
        )
        print(
            (
                "Producer source: "
                f"{producer.source_record_kind}:"
                f"{producer.source_record_id}"
            ),
            file=output,
        )
        print(
            (f"Producer native revision: {producer.native_revision or '(none)'}"),
            file=output,
        )
        print(
            (f"Artifact: {artifact.artifact_id if artifact else '(none)'}"),
            file=output,
        )
        print(
            (
                "Artifact kind/representation: "
                f"{artifact.artifact_kind + '/' + artifact.representation_kind if artifact else '(none)'}"
            ),
            file=output,
        )
        relationships = ", ".join(
            (
                f"{value.relationship_kind}:"
                f"{value.source_subject_kind}:"
                f"{value.source_subject_id}"
            )
            for value in endpoint.subject_relationship_assertions
        )
        print(
            f"Subject relationships: {relationships or '(none)'}",
            file=output,
        )

    if endpoint is not None:
        publication = endpoint.core_publication
        producer = endpoint.producer_source
        artifact = endpoint.source_artifact
        print(
            (
                "Core work: "
                f"{publication.work.module_id}:"
                f"{publication.work.class_id}:"
                f"{publication.work.work_id}"
            ),
            file=output,
        )
        print(f"Publication kind: {publication.publication_kind}", file=output)
        print(
            f"Record set: {publication.record_set_id}@{publication.record_set_revision}",
            file=output,
        )
        print(
            f"Manifest contract: {publication.manifest_contract_version}",
            file=output,
        )
        print(f"Published at: {publication.published_at.isoformat()}", file=output)
        print(
            "Registration revision: "
            f"{publication.academic_work_registration_revision or '(none)'}",
            file=output,
        )
        print(
            f"Observed series state: {publication.observed_series_state}", file=output
        )
        print(
            f"Observed withdrawal state: {publication.observed_withdrawal_state}",
            file=output,
        )
        print(
            f"Producer lifecycle: {producer.native_lifecycle or '(none)'}",
            file=output,
        )
        print(
            f"Producer disposition: {producer.native_disposition or '(none)'}",
            file=output,
        )
        print(
            f"Producer lineage: {producer.lineage_reference or '(none)'}",
            file=output,
        )
        print(f"Reader contract: {producer.reader_contract_version}", file=output)
        print(
            f"Projection contract: {producer.projection_contract_version}",
            file=output,
        )
        if artifact is not None:
            print(f"Artifact media type: {artifact.media_type}", file=output)
    if detail.evaluation is not None:
        print(
            "Matched Profile rules: "
            f"{', '.join(detail.evaluation.matched_profile_rule_ids) or '(none)'}",
            file=output,
        )

    if detail.evaluation is not None:
        evaluation = detail.evaluation
        print(
            (f"Evaluation reasons: {', '.join(evaluation.reason_codes) or '(none)'}"),
            file=output,
        )
        availability = ", ".join(
            f"{value.dimension}={value.outcome}"
            for value in evaluation.availability_observations
        )
        print(
            f"Availability: {availability or '(none)'}",
            file=output,
        )
        print(
            (f"Evaluator contract: {evaluation.evaluator_contract_version}"),
            file=output,
        )
    print(
        (
            "Evaluation history: "
            + ", ".join(
                value.candidate_evaluation_id for value in detail.evaluation_history
            )
        ),
        file=output,
    )
    print(
        (
            "Current-pointer history: "
            + (
                ", ".join(
                    f"{value.pointer_revision}:{value.current_candidate_evaluation_id}"
                    for value in detail.pointer_history
                )
                or "(none)"
            )
        ),
        file=output,
    )


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


def _optional_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise PortfolioSetupError(
            "profile_context_invalid",
            "--as-of must use YYYY-MM-DD.",
        ) from error


def _portfolio_setup_request(
    args: argparse.Namespace,
) -> CreatePortfolioForStudentRequest:
    actor = _actor_value(args)
    if args.new_subject:
        subject_action = "create_new"
        existing_subject_id = None
    elif args.existing_subject_id is not None:
        subject_action = "link_existing"
        existing_subject_id = args.existing_subject_id
    else:
        subject_action = None
        existing_subject_id = None

    identity_context: IdentityDecisionContext | None = None
    if subject_action is not None:
        if not args.identity_basis_type or not args.identity_basis_summary:
            raise PortfolioSetupError(
                "identity_basis_required",
                "Explicit Subject creation/linking requires --identity-basis-type "
                "and --identity-basis-summary.",
            )
        identity_context = IdentityDecisionContext(
            actor=actor,
            authority_source=args.identity_authority_source,
            basis_type=args.identity_basis_type,
            basis_summary=args.identity_basis_summary,
        )

    return CreatePortfolioForStudentRequest(
        student_reference=ClassQualifiedStudentRef(
            school_year=args.school_year,
            class_id=args.class_id,
            student_id=args.student_id,
        ),
        purpose_kind=args.purpose,
        profile_revision=ProfileRevisionRef(
            portfolio_profile_id=args.profile_id,
            profile_revision=args.profile_revision,
        ),
        profile_context=ProfileBindingContext(
            as_of=_optional_date(args.as_of),
            institution_id=args.institution_id,
            program_id=args.program_id,
            content_area=args.content_area,
        ),
        subject_action=subject_action,
        existing_subject_id=existing_subject_id,
        identity_context=identity_context,
        title_snapshot=args.title,
        description_snapshot=args.description,
    )


def _print_portfolio_setup_plan(
    plan: PortfolioSetupPlan,
    *,
    output: TextIO,
    dry_run: bool,
) -> None:
    print("Create Portfolio for Student plan", file=output)
    print(f"Contract: {plan.contract_version}", file=output)
    observed = (
        str(plan.observed_state_revision)
        if plan.observed_state_revision is not None
        else "(none)"
    )
    print(f"Observed state revision: {observed}", file=output)
    print(f"Ready: {'yes' if plan.ready else 'no'}", file=output)
    if plan.student is not None:
        print(f"Student: {plan.student.display_name}", file=output)
        print(
            "Roster reference: "
            f"{plan.student.reference.school_year}:"
            f"{plan.student.reference.class_id}:"
            f"{plan.student.reference.student_id}",
            file=output,
        )
    print(f"Subject action: {plan.subject_action or '(unresolved)'}", file=output)
    print(f"Portfolio Subject: {plan.portfolio_subject_id or '(none)'}", file=output)
    if plan.selected_profile is not None:
        reference = plan.selected_profile.reference
        print(
            f"Profile: {reference.portfolio_profile_id}:{reference.profile_revision}",
            file=output,
        )
    print(
        "Existing Portfolios: "
        + (
            ", ".join(item.portfolio_id for item in plan.existing_portfolios)
            or "(none)"
        ),
        file=output,
    )
    print(
        "Planned records: " + (", ".join(plan.planned_record_kinds) or "(none)"),
        file=output,
    )
    print(
        "Blocking codes: " + (", ".join(plan.blocking_codes) or "(none)"),
        file=output,
    )
    print(
        f"Mutation: {'dry-run only' if dry_run else 'requested'}",
        file=output,
    )


def _run_create_for_student(
    args: argparse.Namespace,
    *,
    root: Path | None,
    output: TextIO,
) -> None:
    resolved_root = show_workspace(root).root
    request = _portfolio_setup_request(args)
    plan = plan_create_portfolio_for_student(resolved_root, request)
    if (
        args.expected_state_revision is not None
        and args.expected_state_revision != plan.observed_state_revision
    ):
        raise PortfolioSetupError(
            "state_conflict",
            f"Vitrine state changed: expected {args.expected_state_revision!r}, "
            f"found {plan.observed_state_revision!r}.",
        )
    _print_portfolio_setup_plan(plan, output=output, dry_run=args.dry_run)
    if not plan.ready:
        raise PortfolioSetupError(
            plan.blocking_codes[0] if plan.blocking_codes else "setup_plan_invalid",
            "Create Portfolio for Student plan is not ready.",
        )
    if args.dry_run:
        return
    result = create_portfolio_for_student(
        resolved_root,
        plan,
        actor=_actor_value(args),
    )
    print(
        f"Created Portfolio for Student: {result.portfolio_id}\n"
        f"Portfolio Subject: {result.portfolio_subject_id}\n"
        f"Profile Binding: {result.profile_binding_id}\n"
        f"State revision: {result.state_revision}",
        file=output,
    )


def _plan_specification(path: Path) -> SnapshotPlanSpecification:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SnapshotPlanningError(
            "snapshot_plan_file_unreadable",
            "Snapshot Plan specification file could not be read.",
        ) from exc
    try:
        value = strict_json_loads(data)
    except ValueError as exc:
        raise SnapshotPlanningError(
            "snapshot_plan_file_invalid",
            "Snapshot Plan specification is not valid JSON.",
        ) from exc
    if not isinstance(value, dict):
        raise SnapshotPlanningError(
            "snapshot_plan_specification_invalid",
            "Snapshot Plan specification must contain one object.",
        )
    return snapshot_plan_specification_from_dict(value)


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
        elif subcommand == "build-export":
            return run_current_portfolio_build_export_command(
                args, dependencies=dependencies, output=output
            )
        elif subcommand == "create-for-student":
            _run_create_for_student(args, root=root, output=output)
        elif subcommand == "create":
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
        else:
            raise AssertionError(f"Unhandled Portfolio command: {subcommand}")
        return 0
    if command == "candidate":
        if subcommand in CANDIDATE_REVIEW_CLI_COMMANDS:
            return run_candidate_review_command(
                args,
                dependencies=dependencies,
                output=output,
            )
        if subcommand == "list":
            for candidate_summary in list_candidate_summaries(root, args.portfolio_id):
                print(
                    f"{candidate_summary.candidate_id}\t{candidate_summary.condition_state}\t{candidate_summary.display_snapshot}\tselected={candidate_summary.active_selection_id or 'no'}",
                    file=output,
                )
        elif subcommand == "inbox":
            inbox_command = getattr(
                args,
                "candidate_inbox_command",
                None,
            )
            if inbox_command == "show":
                detail = get_candidate_inbox_detail(
                    root,
                    args.entry_id,
                )
                _print_candidate_inbox_detail(
                    detail,
                    output=output,
                )
            else:
                result = list_candidate_inbox(
                    root,
                    _inbox_query(args),
                )
                print(
                    (
                        "Candidate Inbox: "
                        f"{result.matched_count} matching"
                        + (
                            f" (showing {len(result.items)})"
                            if result.truncated
                            else ""
                        )
                    ),
                    file=output,
                )
                for item in result.items:
                    _print_candidate_inbox_item(
                        item,
                        output=output,
                    )
        elif subcommand == "show":
            candidate = show_candidate_detail(root, args.candidate_id)
            endpoint = candidate.source_endpoint
            publication = endpoint.core_publication
            producer = endpoint.producer_source
            artifact = endpoint.source_artifact
            print(
                f"Candidate: {candidate.candidate_id}\nCandidate Evaluation: {candidate.candidate_evaluation_id}\nSummary: {candidate.display_snapshot}\nProfile Binding: {candidate.profile_binding_id}\nCore Publication: {publication.publication_id}\nProducer module: {producer.producer_module_id}\nProducer source: {producer.source_record_kind}:{producer.source_record_id}\nProducer native revision: {producer.native_revision if producer.native_revision is not None else '(none)'}\nArtifact: {artifact.artifact_id if artifact else '(none)'}\nArtifact kind/representation: {artifact.artifact_kind + '/' + artifact.representation_kind if artifact else '(none)'}\nSubject relationships: {', '.join(x.relationship_kind + ':' + x.source_subject_kind + ':' + x.source_subject_id for x in endpoint.subject_relationship_assertions)}\nCondition: {candidate.condition_state}\nEvaluation reasons: {', '.join(candidate.evaluation_reason_codes) or '(none)'}\nUnresolved condition codes: {', '.join(candidate.unresolved_condition_codes) or '(none)'}\nEligible sections: {', '.join(candidate.eligible_section_ids)}\nAvailability: {', '.join(x.dimension + '=' + x.outcome for x in candidate.availability_observations)}\nCollaborative semantics: Group Membership != Artifact Author; Artifact Subject != Artifact Author; documented contribution != whole-Artifact authorship; represented Group remains separate; Group Score target != individual Score.",
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
            for finding in discovery_result.findings:
                print(f"{finding.code}\tstage={finding.stage}", file=output)
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
        if subcommand in WORKING_COMPOSITION_CLI_COMMANDS:
            return run_working_composition_command(
                args,
                dependencies=dependencies,
                output=output,
            )
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
        if subcommand == "plan-show":
            exact_plan = show_snapshot_plan(root, args.snapshot_build_plan_id)
            kinds = tuple(item.materialization_kind for item in exact_plan.entry_plans)
            print(
                f"Build Plan: {exact_plan.snapshot_build_plan_id}\n"
                f"Build Request: {exact_plan.snapshot_build_request_id}\n"
                f"Snapshot Series: {exact_plan.snapshot_series_id}\n"
                f"Composition revision: {exact_plan.composition_revision}\n"
                f"Audience Context: {exact_plan.audience_context_id}\n"
                f"Entries: {len(exact_plan.entry_plans)}\n"
                f"Copied/generated/reference-only: "
                f"{kinds.count('copied_source')}/{kinds.count('generated_vitrine')}/"
                f"{kinds.count('reference_only')}\n"
                f"Exports: {', '.join(item.export_format for item in exact_plan.export_plans)}\n"
                f"Acknowledged obligations: "
                f"{', '.join(exact_plan.acknowledged_obligation_codes) or '(none)'}",
                file=output,
            )
            return 0
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
            for custody_finding in audit.findings:
                print(f"{custody_finding.code}\t{custody_finding.summary}", file=output)
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
            specification = _plan_specification(args.from_plan_json)
            plan_result = prepare_snapshot_build(
                root,
                SnapshotPlanningRequest(
                    snapshot_build_request_id=args.snapshot_build_request_id,
                    planned_by=_actor_value(args),
                    expected_state_revision=_required_expected(args),
                ),
                provider=dependencies.snapshot_planning_provider,
                specification=specification,
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
