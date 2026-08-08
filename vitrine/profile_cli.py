"""Power-user CLI for immutable Portfolio Profile workflows."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TextIO, TypeVar

from vitrine.models import (
    ActorAttribution,
    PortfolioProfileFamily,
    PortfolioProfileOverlayRevision,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    ProfileOverlayRevisionRef,
    ProfileRevisionRef,
    record_from_dict,
    strict_json_loads,
)
from vitrine.profile_services import (
    ProfileBindingContext,
    ProfileMigrationAnalysis,
    ProfileMutationResult,
    ProfileWorkflowError,
    activate_profile_revision,
    analyze_profile_migration,
    bind_portfolio_profile,
    compose_profile_revision,
    create_profile_family,
    create_profile_overlay,
    create_profile_revision,
    get_portfolio_profile_binding,
    get_profile_requirements,
    get_profile_revision,
    list_profile_families,
    list_profile_revisions,
    migrate_portfolio_profile,
    observe_profile_state_revision,
    transition_profile_lifecycle,
)
from vitrine.storage import VitrineStorageError


def _add_workspace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace-root", type=Path)


def _add_expected(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--expected-state-revision", type=int)


def _add_actor(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--actor-id", required=True)
    parser.add_argument(
        "--actor-kind",
        default="authorized_adult",
        choices=("authorized_adult", "system", "external_actor"),
    )
    parser.add_argument("--owning-system", default="local")
    parser.add_argument("--role", default="teacher")
    parser.add_argument("--authority-reference", required=True)
    parser.add_argument("--reason", required=True)


def _add_context(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--as-of", type=date.fromisoformat)
    parser.add_argument("--school-year")
    parser.add_argument("--institution-id")
    parser.add_argument("--program-id")
    parser.add_argument("--content-area")


def _add_ref(parser: argparse.ArgumentParser, *, prefix: str = "") -> None:
    parser.add_argument(f"--{prefix}profile-id" if prefix else "profile_id")
    parser.add_argument(
        f"--{prefix}revision" if prefix else "revision",
        type=int,
    )


def configure_profile_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    profile = subparsers.add_parser("profile", help="Manage immutable Portfolio Profiles.")
    commands = profile.add_subparsers(dest="profile_command", required=True)

    list_parser = commands.add_parser("list", help="List exact Profile Revisions.")
    list_parser.add_argument("--profile-id")
    _add_workspace(list_parser)

    show_parser = commands.add_parser("show", help="Show one exact Profile Revision.")
    show_parser.add_argument("profile_id")
    show_parser.add_argument("--revision", type=int, required=True)
    _add_workspace(show_parser)

    family = commands.add_parser("family", help="Manage Profile Families.")
    family_cmd = family.add_subparsers(dest="profile_family_command", required=True)
    family_list = family_cmd.add_parser("list")
    _add_workspace(family_list)
    family_create = family_cmd.add_parser("create")
    family_create.add_argument("profile_family_id")
    family_create.add_argument("--label", required=True)
    family_create.add_argument("--purpose-kind", required=True, choices=("improvement", "showcase"))
    family_create.add_argument("--description")
    _add_actor(family_create)
    _add_expected(family_create)
    _add_workspace(family_create)

    revision = commands.add_parser("revision", help="Manage Profile Revisions.")
    revision_cmd = revision.add_subparsers(dest="profile_revision_command", required=True)
    revision_create = revision_cmd.add_parser("create")
    revision_create.add_argument("--revision-json", type=Path, required=True)
    revision_create.add_argument("--requirements-json", type=Path, required=True)
    _add_expected(revision_create)
    _add_workspace(revision_create)

    activate = commands.add_parser("activate", help="Explicitly activate one exact Revision.")
    activate.add_argument("profile_id")
    activate.add_argument("--revision", type=int, required=True)
    _add_actor(activate)
    _add_expected(activate)
    _add_workspace(activate)

    lifecycle = commands.add_parser("lifecycle", help="Record a non-active lifecycle transition.")
    lifecycle.add_argument("profile_id")
    lifecycle.add_argument("--revision", type=int, required=True)
    lifecycle.add_argument("--event", required=True, choices=("deprecated", "superseded", "withdrawn", "retired"))
    lifecycle.add_argument("--successor-profile-id")
    lifecycle.add_argument("--successor-revision", type=int)
    _add_actor(lifecycle)
    _add_expected(lifecycle)
    _add_workspace(lifecycle)

    binding = commands.add_parser("binding", help="Show one Portfolio's current Profile Binding.")
    binding.add_argument("portfolio_id")
    _add_workspace(binding)

    bind = commands.add_parser("bind", help="Bind a Portfolio to one exact activated Revision.")
    bind.add_argument("portfolio_id")
    bind.add_argument("profile_id")
    bind.add_argument("--revision", type=int, required=True)
    _add_actor(bind)
    _add_context(bind)
    _add_expected(bind)
    _add_workspace(bind)

    migration = commands.add_parser("migration", help="Analyze or perform explicit Profile migration.")
    migration_cmd = migration.add_subparsers(dest="profile_migration_command", required=True)
    analyze = migration_cmd.add_parser("analyze")
    analyze.add_argument("portfolio_id")
    analyze.add_argument("profile_id")
    analyze.add_argument("--revision", type=int, required=True)
    _add_context(analyze)
    _add_workspace(analyze)
    migrate = migration_cmd.add_parser("migrate")
    migrate.add_argument("portfolio_id")
    migrate.add_argument("profile_id")
    migrate.add_argument("--revision", type=int, required=True)
    _add_actor(migrate)
    _add_context(migrate)
    _add_expected(migrate)
    _add_workspace(migrate)

    overlay = commands.add_parser("overlay", help="Create an immutable local Overlay Revision.")
    overlay.add_argument("--overlay-json", type=Path, required=True)
    _add_expected(overlay)
    _add_workspace(overlay)

    compose = commands.add_parser("compose", help="Flatten exact components and overlays into an effective Revision.")
    compose.add_argument("--effective-revision-json", type=Path, required=True)
    compose.add_argument("--component", action="append", required=True, metavar="PROFILE_ID@REVISION")
    compose.add_argument("--overlay", action="append", default=[], metavar="OVERLAY_ID@REVISION")
    _add_actor(compose)
    _add_expected(compose)
    _add_workspace(compose)


def _actor(args: argparse.Namespace) -> ActorAttribution:
    return ActorAttribution(
        actor_kind=args.actor_kind,
        actor_id=args.actor_id,
        owning_system=args.owning_system,
        role_snapshot=args.role,
    )


def _context(args: argparse.Namespace) -> ProfileBindingContext:
    return ProfileBindingContext(
        as_of=getattr(args, "as_of", None),
        school_year=getattr(args, "school_year", None),
        institution_id=getattr(args, "institution_id", None),
        program_id=getattr(args, "program_id", None),
        content_area=getattr(args, "content_area", None),
    )


def _expected(args: argparse.Namespace) -> int | None:
    explicit: object = getattr(args, "expected_state_revision", None)
    if explicit is not None:
        if isinstance(explicit, bool) or not isinstance(explicit, int):
            raise AssertionError("expected_state_revision parser value must be an integer.")
        return explicit
    return observe_profile_state_revision(args.workspace_root)


def _ref(profile_id: str, revision: int) -> ProfileRevisionRef:
    return ProfileRevisionRef(portfolio_profile_id=profile_id, profile_revision=revision)


def _parse_exact_ref(raw: str) -> ProfileRevisionRef:
    profile_id, separator, revision_text = raw.rpartition("@")
    if not separator or not profile_id or not revision_text.isdigit():
        raise ProfileWorkflowError("profile_revision_not_found", f"Invalid exact Profile reference: {raw}")
    return _ref(profile_id, int(revision_text))


def _parse_overlay_ref(raw: str) -> ProfileOverlayRevisionRef:
    overlay_id, separator, revision_text = raw.rpartition("@")
    if not separator or not overlay_id or not revision_text.isdigit():
        raise ProfileWorkflowError("overlay_not_found", f"Invalid exact Overlay reference: {raw}")
    return ProfileOverlayRevisionRef(overlay_id=overlay_id, overlay_revision=int(revision_text))


R = TypeVar("R")


def _load_record(path: Path, expected: type[R]) -> R:
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ProfileWorkflowError("profile_input_invalid", f"{path} must contain one JSON object.")
    record = record_from_dict(value)
    if not isinstance(record, expected):
        raise ProfileWorkflowError("profile_input_invalid", f"{path} must contain {expected.__name__}.")
    return record


def _load_requirements(path: Path) -> tuple[PortfolioProfileRequirement, ...]:
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, list):
        raise ProfileWorkflowError("profile_input_invalid", f"{path} must contain a JSON array.")
    result: list[PortfolioProfileRequirement] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ProfileWorkflowError("profile_input_invalid", f"Requirement {index} must be a JSON object.")
        record = record_from_dict(item)
        if not isinstance(record, PortfolioProfileRequirement):
            raise ProfileWorkflowError("profile_input_invalid", f"Requirement {index} must be portfolio_profile_requirement.")
        result.append(record)
    return tuple(result)


def _print_mutation(result: ProfileMutationResult, output: TextIO) -> None:
    if result.commit is None:
        print("No change: exact canonical record already satisfies the request.", file=output)
    else:
        print(f"State revision: {result.commit.state_revision}", file=output)
    print(f"Record IDs: {', '.join(result.record_ids)}", file=output)


def _print_analysis(analysis: ProfileMigrationAnalysis, output: TextIO) -> None:
    print(f"Portfolio: {analysis.portfolio_id}", file=output)
    print(
        f"Source: {analysis.source_profile_revision.portfolio_profile_id}@{analysis.source_profile_revision.profile_revision}",
        file=output,
    )
    print(
        f"Target: {analysis.target_profile_revision.portfolio_profile_id}@{analysis.target_profile_revision.profile_revision}",
        file=output,
    )
    impact = analysis.requirement_impact
    for label in ("unchanged", "added", "removed", "replaced", "materially_changed", "unresolved_mapping"):
        values = getattr(impact, label)
        print(f"{label}: {', '.join(values) if values else '-'}", file=output)
    print(f"Affected sections: {', '.join(analysis.affected_section_ids) if analysis.affected_section_ids else '-'}", file=output)
    print(f"Potentially affected selections: {analysis.potentially_affected_selection_count}", file=output)
    print(f"Reapproval requirements: {', '.join(analysis.reapproval_requirement_ids) if analysis.reapproval_requirement_ids else '-'}", file=output)
    print(f"Blocked: {'yes' if analysis.blocked else 'no'}", file=output)


def run_profile_command(args: argparse.Namespace, *, output: TextIO, error: TextIO) -> int:
    """Execute one direct Profile command without interactive prompting."""
    try:
        command = args.profile_command
        if command == "list":
            for item in list_profile_revisions(args.workspace_root, portfolio_profile_id=args.profile_id):
                print(
                    f"{item.reference.portfolio_profile_id}@{item.reference.profile_revision}\t"
                    f"{item.lifecycle_status}\t{item.purpose_kind}\t{item.label}\t"
                    f"requirements={item.requirement_count}",
                    file=output,
                )
            return 0
        if command == "show":
            reference = _ref(args.profile_id, args.revision)
            revision = get_profile_revision(args.workspace_root, reference)
            requirements = get_profile_requirements(args.workspace_root, reference)
            summary = next(item for item in list_profile_revisions(args.workspace_root, portfolio_profile_id=args.profile_id) if item.reference == reference)
            print(f"Profile: {args.profile_id}@{args.revision}", file=output)
            print(f"Label: {revision.label}", file=output)
            print(f"Purpose: {revision.purpose_kind}", file=output)
            print(f"Lifecycle: {summary.lifecycle_status}", file=output)
            print(f"Bindable: {'yes' if summary.bindable else 'no'}", file=output)
            print(f"Requirements: {len(requirements)}", file=output)
            for requirement in requirements:
                print(f"- {requirement.requirement_id}: {requirement.obligation} {requirement.requirement_kind}", file=output)
            return 0
        if command == "family":
            if args.profile_family_command == "list":
                for family in list_profile_families(args.workspace_root):
                    print(f"{family.profile_family_id}\t{family.purpose_kind}\t{family.label}", file=output)
                return 0
            now = datetime.now(timezone.utc)
            family = PortfolioProfileFamily(
                profile_family_id=args.profile_family_id,
                label=args.label,
                purpose_kind=args.purpose_kind,
                description=args.description,
                created_at=now,
                created_by=_actor(args),
            )
            _print_mutation(create_profile_family(args.workspace_root, family, expected_state_revision=_expected(args)), output)
            return 0
        if command == "revision":
            revision = _load_record(args.revision_json, PortfolioProfileRevision)
            requirements = _load_requirements(args.requirements_json)
            _print_mutation(create_profile_revision(args.workspace_root, revision, requirements, expected_state_revision=_expected(args)), output)
            return 0
        if command == "activate":
            _print_mutation(
                activate_profile_revision(
                    args.workspace_root,
                    _ref(args.profile_id, args.revision),
                    actor=_actor(args),
                    reason=args.reason,
                    authority_reference=args.authority_reference,
                    expected_state_revision=_expected(args),
                ),
                output,
            )
            return 0
        if command == "lifecycle":
            successor = None
            if args.successor_profile_id is not None or args.successor_revision is not None:
                if args.successor_profile_id is None or args.successor_revision is None:
                    raise ProfileWorkflowError("profile_lifecycle_invalid", "Both successor Profile ID and Revision are required.")
                successor = _ref(args.successor_profile_id, args.successor_revision)
            _print_mutation(
                transition_profile_lifecycle(
                    args.workspace_root,
                    _ref(args.profile_id, args.revision),
                    args.event,
                    actor=_actor(args),
                    reason=args.reason,
                    authority_reference=args.authority_reference,
                    successor_revision=successor,
                    expected_state_revision=_expected(args),
                ),
                output,
            )
            return 0
        if command == "binding":
            binding = get_portfolio_profile_binding(args.workspace_root, args.portfolio_id)
            if binding is None:
                print("No active Profile Binding.", file=output)
            else:
                print(f"Binding: {binding.profile_binding_id}", file=output)
                print(f"Profile: {binding.profile_revision.portfolio_profile_id}@{binding.profile_revision.profile_revision}", file=output)
            return 0
        if command == "bind":
            _print_mutation(
                bind_portfolio_profile(
                    args.workspace_root,
                    args.portfolio_id,
                    _ref(args.profile_id, args.revision),
                    actor=_actor(args),
                    binding_reason=args.reason,
                    context=_context(args),
                    expected_state_revision=_expected(args),
                ),
                output,
            )
            return 0
        if command == "migration":
            target = _ref(args.profile_id, args.revision)
            if args.profile_migration_command == "analyze":
                _print_analysis(analyze_profile_migration(args.workspace_root, args.portfolio_id, target, context=_context(args)), output)
                return 0
            analysis, result = migrate_portfolio_profile(
                args.workspace_root,
                args.portfolio_id,
                target,
                actor=_actor(args),
                migration_reason=args.reason,
                authority_reference=args.authority_reference,
                context=_context(args),
                expected_state_revision=_expected(args),
            )
            _print_analysis(analysis, output)
            _print_mutation(result, output)
            return 0
        if command == "overlay":
            overlay = _load_record(args.overlay_json, PortfolioProfileOverlayRevision)
            _print_mutation(create_profile_overlay(args.workspace_root, overlay, expected_state_revision=_expected(args)), output)
            return 0
        if command == "compose":
            effective = _load_record(args.effective_revision_json, PortfolioProfileRevision)
            components = tuple(_parse_exact_ref(item) for item in args.component)
            overlays = tuple(_parse_overlay_ref(item) for item in args.overlay)
            composition_result = compose_profile_revision(
                args.workspace_root,
                effective,
                components,
                overlays,
                actor=_actor(args),
                authority_reference=args.authority_reference,
                expected_state_revision=_expected(args),
            )
            print(f"State revision: {composition_result.commit.state_revision}", file=output)
            print(f"Effective Profile: {composition_result.effective_revision.portfolio_profile_id}@{composition_result.effective_revision.profile_revision}", file=output)
            print(f"Composition: {composition_result.composition_id}", file=output)
            return 0
    except (OSError, ValueError, VitrineStorageError, ProfileWorkflowError) as exc:
        code = exc.code if isinstance(exc, ProfileWorkflowError) else "profile_command_failed"
        print(f"Error [{code}]: {exc}", file=error)
        return 1
    raise AssertionError(f"Unhandled Profile command: {args.profile_command}")


__all__ = ["configure_profile_parser", "run_profile_command"]
