"""Power-user CLI surface for Portfolio Subject identity workflows."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TextIO

from vitrine.models import ActorAttribution, ClassQualifiedStudentRef
from vitrine.storage import VitrineStorageError
from vitrine.subject_services import (
    IdentityDecisionContext,
    SubjectMutationResult,
    SubjectWorkflowError,
    correct_subject_link,
    create_portfolio_subject,
    invalidate_subject_link,
    link_portfolio_subject,
    list_subjects,
    merge_portfolio_subjects,
    observe_state_revision,
    show_subject,
    split_portfolio_subject,
)

_BASIS_CHOICES = (
    "direct_teacher_knowledge",
    "authorized_institutional_crosswalk",
    "verified_sis_information",
    "student_confirmation",
    "parent_or_guardian_confirmation",
    "transfer_or_enrollment_record",
    "migration_from_reviewed_source",
    "other_authorized_basis",
)


def _add_workspace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--workspace-root",
        type=Path,
        help="Explicit Paper Data Suite workspace root for this command.",
    )


def _add_reference(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--school-year", required=True)
    parser.add_argument("--class-id", required=True)
    parser.add_argument("--student-id", required=True)


def _add_decision(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--actor-id", required=True)
    parser.add_argument(
        "--actor-kind",
        default="authorized_adult",
        choices=("authorized_adult", "system", "external_actor"),
    )
    parser.add_argument("--owning-system", default="local")
    parser.add_argument("--role", default="teacher")
    parser.add_argument("--authority-source", required=True)
    parser.add_argument("--basis-type", required=True, choices=_BASIS_CHOICES)
    parser.add_argument("--basis-summary", required=True)
    parser.add_argument("--external-basis-ref")
    parser.add_argument("--expected-state-revision", type=int)


def configure_subject_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the direct Portfolio Subject command family."""
    subject = subparsers.add_parser(
        "subject",
        help="Manage Portfolio Subjects and exact Core roster links.",
    )
    commands = subject.add_subparsers(dest="subject_command", required=True)

    list_parser = commands.add_parser("list", help="List Portfolio Subjects.")
    _add_workspace(list_parser)

    show_parser = commands.add_parser("show", help="Show one Portfolio Subject.")
    show_parser.add_argument("subject_id")
    _add_workspace(show_parser)

    create_parser = commands.add_parser(
        "create", help="Create a Subject from one exact Core roster student."
    )
    _add_reference(create_parser)
    _add_decision(create_parser)
    _add_workspace(create_parser)

    link_parser = commands.add_parser(
        "link", help="Confirm another exact class/year roster link."
    )
    link_parser.add_argument("subject_id")
    _add_reference(link_parser)
    _add_decision(link_parser)
    _add_workspace(link_parser)

    correct_parser = commands.add_parser(
        "correct-link", help="Supersede a bad link with an exact replacement."
    )
    correct_parser.add_argument("subject_link_id")
    _add_reference(correct_parser)
    _add_decision(correct_parser)
    _add_workspace(correct_parser)

    invalidate_parser = commands.add_parser(
        "invalidate-link", help="Invalidate a confirmed Subject link."
    )
    invalidate_parser.add_argument("subject_link_id")
    _add_decision(invalidate_parser)
    _add_workspace(invalidate_parser)

    merge_parser = commands.add_parser(
        "merge", help="Merge current Subjects into one new successor Subject."
    )
    merge_parser.add_argument("subject_ids", nargs="+")
    _add_decision(merge_parser)
    _add_workspace(merge_parser)

    split_parser = commands.add_parser(
        "split", help="Split one Subject into explicit successor link groups."
    )
    split_parser.add_argument("subject_id")
    split_parser.add_argument(
        "--group",
        action="append",
        required=True,
        metavar="LINK_ID[,LINK_ID...]",
        help="One successor group; repeat at least twice.",
    )
    _add_decision(split_parser)
    _add_workspace(split_parser)


def _reference(args: argparse.Namespace) -> ClassQualifiedStudentRef:
    return ClassQualifiedStudentRef(
        school_year=args.school_year,
        class_id=args.class_id,
        student_id=args.student_id,
    )


def _context(args: argparse.Namespace) -> IdentityDecisionContext:
    actor = ActorAttribution(
        actor_kind=args.actor_kind,
        actor_id=args.actor_id,
        owning_system=args.owning_system,
        role_snapshot=args.role,
    )
    return IdentityDecisionContext(
        actor=actor,
        authority_source=args.authority_source,
        basis_type=args.basis_type,
        basis_summary=args.basis_summary,
        external_basis_ref=args.external_basis_ref,
    )


def _expected(args: argparse.Namespace) -> int | None:
    explicit: object = getattr(args, "expected_state_revision", None)
    if explicit is not None:
        if isinstance(explicit, bool) or not isinstance(explicit, int):
            raise AssertionError("expected_state_revision parser value must be an integer.")
        return explicit
    return observe_state_revision(args.workspace_root)


def _print_mutation(result: SubjectMutationResult, output: TextIO) -> None:
    subject_ids = result.subject_ids
    link_ids = result.link_ids
    commit = result.commit
    affected = result.affected_portfolio_ids
    print(f"State revision: {commit.state_revision}", file=output)
    if commit.no_op:
        print("No change: existing canonical association.", file=output)
    print(f"Subject IDs: {', '.join(subject_ids)}", file=output)
    if link_ids:
        print(f"Link IDs: {', '.join(link_ids)}", file=output)
    if affected:
        print(f"Affected Portfolios: {', '.join(affected)}", file=output)


def _parse_groups(raw_groups: list[str]) -> tuple[tuple[str, ...], ...]:
    groups: list[tuple[str, ...]] = []
    for raw in raw_groups:
        values = tuple(item.strip() for item in raw.split(",") if item.strip())
        if not values:
            raise SubjectWorkflowError(
                "split_allocation_invalid", "Split groups must not be empty."
            )
        groups.append(values)
    return tuple(groups)


def run_subject_command(
    args: argparse.Namespace,
    *,
    output: TextIO,
    error: TextIO,
) -> int:
    """Execute one direct Subject command without interactive prompting."""
    try:
        if args.subject_command == "list":
            for item in list_subjects(args.workspace_root):
                label = item.display_name or "(no display label)"
                print(
                    f"{item.portfolio_subject_id}\t{item.status}\t{label}\t"
                    f"links={item.current_link_count}\t"
                    f"historical={item.historical_link_count}",
                    file=output,
                )
            return 0
        if args.subject_command == "show":
            detail = show_subject(args.workspace_root, args.subject_id)
            summary = detail.summary
            print(f"Subject: {summary.portfolio_subject_id}", file=output)
            print(f"Status: {summary.status}", file=output)
            print(f"Display: {summary.display_name or '(none)'}", file=output)
            print(f"Portfolios: {summary.portfolio_count}", file=output)
            print("Current links:", file=output)
            for link in detail.current_links:
                ref = link.reference
                print(
                    f"  {link.subject_link_id}: {ref.school_year} "
                    f"{ref.class_id} {ref.student_id} "
                    f"[{link.current_resolution}]",
                    file=output,
                )
            print(f"Historical links: {len(detail.historical_links)}", file=output)
            return 0

        context = _context(args)
        expected = _expected(args)
        if args.subject_command == "create":
            result = create_portfolio_subject(
                args.workspace_root,
                _reference(args),
                context=context,
                expected_state_revision=expected,
            )
        elif args.subject_command == "link":
            result = link_portfolio_subject(
                args.workspace_root,
                args.subject_id,
                _reference(args),
                context=context,
                expected_state_revision=expected,
            )
        elif args.subject_command == "correct-link":
            result = correct_subject_link(
                args.workspace_root,
                args.subject_link_id,
                _reference(args),
                context=context,
                expected_state_revision=expected,
            )
        elif args.subject_command == "invalidate-link":
            result = invalidate_subject_link(
                args.workspace_root,
                args.subject_link_id,
                context=context,
                expected_state_revision=expected,
            )
        elif args.subject_command == "merge":
            result = merge_portfolio_subjects(
                args.workspace_root,
                args.subject_ids,
                context=context,
                expected_state_revision=expected,
            )
        elif args.subject_command == "split":
            result = split_portfolio_subject(
                args.workspace_root,
                args.subject_id,
                _parse_groups(args.group),
                context=context,
                expected_state_revision=expected,
            )
        else:
            raise AssertionError(f"Unhandled subject command: {args.subject_command}")
        _print_mutation(result, output)
        return 0
    except (SubjectWorkflowError, VitrineStorageError, ValueError) as exc:
        code = getattr(exc, "code", "subject_workflow_error")
        print(f"Subject error [{code}]: {exc}", file=error)
        return 1


__all__ = ["configure_subject_parser", "run_subject_command"]
