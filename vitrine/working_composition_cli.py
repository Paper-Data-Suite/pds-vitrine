"""Task-level noninteractive CLI for guided Working Composition preparation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Final, TextIO

from vitrine.models import ActorAttribution
from vitrine.workflow_context import VitrineWorkflowDependencies
from vitrine.working_composition import (
    WorkingCompositionError,
    WorkingCompositionPreparation,
    freeze_prepared_working_composition,
    prepare_working_composition,
)

WORKING_COMPOSITION_CLI_COMMANDS: Final[frozenset[str]] = frozenset(
    {"prepare", "freeze"}
)


def _workspace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace-root", type=Path)


def _prepared_actor(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--actor-id", required=True)
    parser.add_argument(
        "--actor-kind",
        default="authorized_adult",
        choices=("authorized_adult", "system", "external_actor"),
    )
    parser.add_argument("--owning-system", default="local")
    parser.add_argument("--role", default="teacher")
    parser.add_argument("--expected-state-revision", required=True, type=int)
    _workspace(parser)


def configure_working_composition_parsers(
    compositions: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Add #67 task-level commands without changing existing low-level commands."""

    prepare = compositions.add_parser(
        "prepare",
        help="Prepare and explain the exact current Working Composition read-only.",
    )
    prepare.add_argument("portfolio_id")
    prepare.add_argument("--note")
    _workspace(prepare)

    freeze = compositions.add_parser(
        "freeze",
        help=(
            "Freeze only an exact previously reviewed Working Composition preparation. "
            "No stale expectation is inferred or refreshed."
        ),
    )
    freeze.add_argument("portfolio_id")
    freeze.add_argument("--preparation-fingerprint", required=True)
    freeze.add_argument(
        "--expected-composition-pointer-revision",
        required=True,
        metavar="REVISION_OR_NONE",
        help=(
            "Exact Composition pointer revision observed during preparation, "
            "or the literal 'none' for an initial Composition."
        ),
    )
    freeze.add_argument("--note")
    _prepared_actor(freeze)


def _actor_value(args: argparse.Namespace) -> ActorAttribution:
    return ActorAttribution(
        actor_kind=args.actor_kind,
        actor_id=args.actor_id,
        owning_system=args.owning_system,
        role_snapshot=args.role,
    )


def _pointer_value(raw: str) -> int | None:
    value = raw.strip()
    if value.casefold() == "none":
        return None
    try:
        revision = int(value)
    except ValueError as error:
        raise WorkingCompositionError(
            "working_composition.invalid_request",
            "--expected-composition-pointer-revision must be a positive integer or 'none'.",
        ) from error
    if revision < 1:
        raise WorkingCompositionError(
            "working_composition.invalid_request",
            "--expected-composition-pointer-revision must be a positive integer or 'none'.",
        )
    return revision


def _fingerprint_value(raw: str) -> str:
    value = raw.strip().casefold()
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise WorkingCompositionError(
            "working_composition.invalid_request",
            "--preparation-fingerprint must be one 64-character SHA-256 hex digest.",
        )
    return value


def _pointer_label(value: int | None) -> str:
    return "none" if value is None else str(value)


def _curation_revision_label(record_kind: str, record_id: str, revision: int) -> str:
    return f"{record_kind}:{record_id}@{revision}"


def _print_preparation(
    preparation: WorkingCompositionPreparation,
    *,
    output: TextIO,
) -> None:
    payload = preparation.payload
    print("Working Composition preparation", file=output)
    print(f"Contract: {preparation.contract_version}", file=output)
    print(f"Portfolio: {preparation.portfolio_id}", file=output)
    print(f"Portfolio Subject: {preparation.portfolio_subject_id}", file=output)
    print(f"Profile Binding: {preparation.profile_binding_id}", file=output)
    print(
        "Profile Revision: "
        f"{preparation.profile_revision_id}@{preparation.profile_revision_number}",
        file=output,
    )
    print(
        f"Observed state revision: {preparation.observed_state_revision}",
        file=output,
    )
    print(
        "Observed Composition pointer revision: "
        f"{_pointer_label(preparation.observed_composition_pointer_revision)}",
        file=output,
    )
    print(
        "Current Composition revision: "
        f"{preparation.current_composition_revision or '(none)'}",
        file=output,
    )
    print(
        f"Predicted Composition revision: {preparation.predicted_composition_revision}",
        file=output,
    )
    print(
        "Predicted Composition pointer revision: "
        f"{preparation.predicted_composition_pointer_revision}",
        file=output,
    )
    print(f"Disposition: {preparation.disposition}", file=output)
    print(f"Coherence: {payload.coherence_state}", file=output)
    print(
        "Unresolved obligations: "
        f"{', '.join(payload.unresolved_obligation_codes) or '(none)'}",
        file=output,
    )
    print(f"Preparation fingerprint: {preparation.preparation_fingerprint}", file=output)
    print(
        f"Selection IDs: {', '.join(payload.selection_ids) or '(none)'}",
        file=output,
    )
    print(
        f"Placement IDs: {', '.join(payload.placement_ids) or '(none)'}",
        file=output,
    )
    print(
        f"Arrangement IDs: {', '.join(payload.arrangement_ids) or '(none)'}",
        file=output,
    )
    print(
        "Included rationale IDs: "
        f"{', '.join(payload.included_rationale_ids) or '(none)'}",
        file=output,
    )
    print(
        "Included curation revisions: "
        + (
            ", ".join(
                _curation_revision_label(
                    item.record_kind,
                    item.record_id,
                    item.revision,
                )
                for item in payload.included_curation_revisions
            )
            or "(none)"
        ),
        file=output,
    )
    print(
        "Applicable Review Decision IDs: "
        f"{', '.join(payload.applicable_review_decision_ids) or '(none)'}",
        file=output,
    )
    print(
        "Related Profile Requirement IDs: "
        f"{', '.join(payload.related_profile_requirement_ids) or '(none)'}",
        file=output,
    )
    print("Sections:", file=output)
    for section in preparation.sections:
        maximum = (
            "unbounded"
            if section.maximum_placements is None
            else str(section.maximum_placements)
        )
        print(
            f"  {section.order}. {section.label} ({section.section_id}) "
            f"placements={section.active_placement_count}; "
            f"minimum={section.minimum_placements}; maximum={maximum}; "
            f"arrangement={section.current_arrangement_id or 'none'}; "
            f"pointer={_pointer_label(section.current_arrangement_pointer_revision)}",
            file=output,
        )
        for placement in section.placements:
            print(
                f"     {placement.placement_id} -> {placement.selection_id} "
                f"Candidate={placement.candidate_id}",
                file=output,
            )
    print(
        "Unplaced active Selections: "
        f"{', '.join(preparation.unplaced_selection_ids) or '(none)'}",
        file=output,
    )
    print("Source currentness:", file=output)
    if not preparation.source_observations:
        print("  (none)", file=output)
    for source in preparation.source_observations:
        print(
            f"  {source.selection_id} Candidate={source.candidate_id} "
            f"Publication={source.publication_id} "
            f"head={source.series_head_publication_id or 'none'} "
            f"state={source.current_use_state}",
            file=output,
        )
    print("Audience constraints:", file=output)
    if not preparation.audience_rules:
        print("  (none)", file=output)
    for audience in preparation.audience_rules:
        print(
            f"  {audience.audience_rule_id} class={audience.audience_class}; "
            f"allowed={','.join(audience.allowed_content_classes) or '(none)'}; "
            f"prohibited={','.join(audience.prohibited_content_classes) or '(none)'}; "
            f"reviews={','.join(audience.required_review_classes) or '(none)'}",
            file=output,
        )
    print(
        "Composition note will persist: "
        f"{'yes' if preparation.composition_note_will_persist else 'no'}",
        file=output,
    )
    print(
        "Working Composition != Audience Context != Snapshot; "
        "this preparation is read-only.",
        file=output,
    )


def _validated_preparation_for_freeze(
    args: argparse.Namespace,
) -> WorkingCompositionPreparation:
    preparation = prepare_working_composition(
        args.workspace_root,
        args.portfolio_id,
        composition_note=args.note,
    )
    if args.expected_state_revision != preparation.observed_state_revision:
        raise WorkingCompositionError(
            "working_composition.state_changed",
            "Vitrine state differs from the reviewed Working Composition preparation.",
        )
    expected_pointer = _pointer_value(args.expected_composition_pointer_revision)
    if expected_pointer != preparation.observed_composition_pointer_revision:
        raise WorkingCompositionError(
            "working_composition.composition_pointer_changed",
            "Composition pointer differs from the reviewed Working Composition preparation.",
        )
    expected_fingerprint = _fingerprint_value(args.preparation_fingerprint)
    if expected_fingerprint != preparation.preparation_fingerprint:
        raise WorkingCompositionError(
            "working_composition.preparation_mismatch",
            "Preparation fingerprint does not match the exact current prepared state.",
        )
    return preparation


def run_working_composition_command(
    args: argparse.Namespace,
    *,
    dependencies: VitrineWorkflowDependencies,
    output: TextIO,
) -> int:
    """Execute one #67 task-level Working Composition command."""

    if args.composition_command == "prepare":
        preparation = prepare_working_composition(
            args.workspace_root,
            args.portfolio_id,
            composition_note=args.note,
        )
        _print_preparation(preparation, output=output)
        return 0

    if args.composition_command != "freeze":
        raise AssertionError(
            f"Unhandled guided Working Composition command: {args.composition_command}"
        )

    preparation = _validated_preparation_for_freeze(args)
    result = freeze_prepared_working_composition(
        args.workspace_root,
        preparation,
        created_by=_actor_value(args),
        authority_gate=dependencies.curation_authority_gate,
    )
    print("Working Composition prepared freeze complete.", file=output)
    print(f"Disposition: {result.disposition}", file=output)
    print(f"State revision: {result.state_revision}", file=output)
    print(
        f"Preparation fingerprint: {preparation.preparation_fingerprint}",
        file=output,
    )
    print(
        "Unresolved obligations remain recorded; freezing does not clear or waive them.",
        file=output,
    )
    return 0


__all__ = [
    "WORKING_COMPOSITION_CLI_COMMANDS",
    "configure_working_composition_parsers",
    "run_working_composition_command",
]
