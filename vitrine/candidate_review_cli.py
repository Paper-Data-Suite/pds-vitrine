"""Task-level noninteractive CLI for guided Candidate review and curation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Final, TextIO

from vitrine.candidate_review import (
    CandidateReviewActionPlan,
    CandidateReviewAnnotationActionPlan,
    CandidateReviewCurationReviewActionPlan,
    CandidateReviewDetail,
    CandidateReviewError,
    CandidateReviewReflectionActionPlan,
    execute_annotation_action,
    execute_candidate_decision,
    execute_curation_review,
    execute_reflection_action,
    get_candidate_review_detail,
    plan_annotation_creation,
    plan_annotation_revision,
    plan_candidate_decision,
    plan_curation_review,
    plan_reflection_creation,
    plan_reflection_revision,
)
from vitrine.models import ActorAttribution, CurationTargetRef
from vitrine.models.errors import VitrineModelValidationError
from vitrine.workflow_context import VitrineWorkflowDependencies

CANDIDATE_REVIEW_CLI_COMMANDS: Final[frozenset[str]] = frozenset(
    {"review", "decide", "annotation", "reflection", "curation-review"}
)

_ANNOTATION_PURPOSES: Final[tuple[str, ...]] = (
    "curator_context",
    "source_context",
    "comparison_note",
    "standards_context",
    "caption",
    "accessibility_description",
)
_ANNOTATION_SCOPES: Final[tuple[str, ...]] = (
    "selection",
    "placement",
    "section",
    "comparison_set",
)
_REFLECTION_SCOPES: Final[tuple[str, ...]] = (
    "selection",
    "placement",
    "comparison_set",
    "section",
    "checkpoint",
    "portfolio",
)
_REVIEW_DECISIONS: Final[tuple[str, ...]] = (
    "approved",
    "rejected",
    "changes_requested",
    "acknowledged",
    "waived",
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


def _target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--target",
        action="append",
        required=True,
        metavar="KIND:ID[:REVISION[:ROLE]]",
        help=(
            "Exact immutable curation target. Annotation/Reflection/Composition "
            "targets require an exact revision; comparison Reflection roles are explicit."
        ),
    )


def configure_candidate_review_parsers(
    candidates: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Add #66 task-level commands without changing existing Candidate commands."""

    review = candidates.add_parser(
        "review",
        help="Show persisted guided review detail for one exact Candidate inbox entry.",
    )
    review.add_argument("entry_id")
    _workspace(review)

    decide = candidates.add_parser(
        "decide",
        help="Explicitly select or decline one persisted positive Candidate entry.",
    )
    decide.add_argument("entry_id")
    decide.add_argument(
        "--decision",
        required=True,
        choices=("select", "decline"),
    )
    decide.add_argument("--section-id", action="append", required=True)
    decide.add_argument("--requirement-id", action="append", default=[])
    decide.add_argument("--reason")
    decide.add_argument(
        "--acknowledge-condition",
        action="store_true",
        help=(
            "Confirm that a non-ready Candidate condition was reviewed. This does "
            "not clear or satisfy the condition; curation authority remains required."
        ),
    )
    _actor(decide)

    annotation = candidates.add_parser(
        "annotation",
        help="Create or revise a guided Curation Annotation for one Candidate entry.",
    )
    annotation_commands = annotation.add_subparsers(
        dest="candidate_annotation_command",
        required=True,
    )
    annotation_add = annotation_commands.add_parser("add")
    annotation_add.add_argument("entry_id")
    annotation_add.add_argument("--purpose", required=True, choices=_ANNOTATION_PURPOSES)
    annotation_add.add_argument("--scope", required=True, choices=_ANNOTATION_SCOPES)
    _target_arguments(annotation_add)
    annotation_add.add_argument("--content", required=True)
    annotation_add.add_argument("--language", default="en")
    annotation_add.add_argument("--content-format", default="plain_text")
    annotation_add.add_argument("--presentation-class")
    _actor(annotation_add)

    annotation_revise = annotation_commands.add_parser("revise")
    annotation_revise.add_argument("entry_id")
    annotation_revise.add_argument("annotation_id")
    annotation_revise.add_argument("--content", required=True)
    annotation_revise.add_argument("--purpose", choices=_ANNOTATION_PURPOSES)
    annotation_revise.add_argument("--scope", choices=_ANNOTATION_SCOPES)
    annotation_revise.add_argument(
        "--target",
        action="append",
        metavar="KIND:ID[:REVISION[:ROLE]]",
    )
    annotation_revise.add_argument("--language")
    annotation_revise.add_argument("--content-format")
    annotation_revise.add_argument("--presentation-class")
    _actor(annotation_revise)

    reflection = candidates.add_parser(
        "reflection",
        help="Create or revise a guided Portfolio Reflection for one Candidate entry.",
    )
    reflection_commands = reflection.add_subparsers(
        dest="candidate_reflection_command",
        required=True,
    )
    reflection_add = reflection_commands.add_parser("add")
    reflection_add.add_argument("entry_id")
    reflection_add.add_argument("--requirement-id", required=True)
    reflection_add.add_argument("--prompt-id", required=True)
    reflection_add.add_argument("--prompt-version", required=True)
    reflection_add.add_argument("--prompt-snapshot", required=True)
    reflection_add.add_argument("--scope", required=True, choices=_REFLECTION_SCOPES)
    _target_arguments(reflection_add)
    reflection_add.add_argument("--content", required=True)
    reflection_add.add_argument(
        "--content-mode",
        default="inline_text",
        choices=("inline_text", "structured_response", "external_reference"),
    )
    reflection_add.add_argument("--language", default="en")
    reflection_add.add_argument("--content-format", default="plain_text")
    _actor(reflection_add)

    reflection_revise = reflection_commands.add_parser("revise")
    reflection_revise.add_argument("entry_id")
    reflection_revise.add_argument("reflection_id")
    reflection_revise.add_argument("--content", required=True)
    reflection_revise.add_argument("--prompt-id")
    reflection_revise.add_argument("--prompt-version")
    reflection_revise.add_argument("--prompt-snapshot")
    reflection_revise.add_argument("--scope", choices=_REFLECTION_SCOPES)
    reflection_revise.add_argument(
        "--target",
        action="append",
        metavar="KIND:ID[:REVISION[:ROLE]]",
    )
    _actor(reflection_revise)

    review_curation = candidates.add_parser(
        "curation-review",
        help="Record one explicit curation Review over exact immutable targets.",
    )
    review_curation.add_argument("entry_id")
    review_curation.add_argument("--scope", required=True)
    _target_arguments(review_curation)
    review_curation.add_argument("--decision", required=True, choices=_REVIEW_DECISIONS)
    review_curation.add_argument("--reason", required=True)
    review_curation.add_argument("--approval-requirement-id")
    review_curation.add_argument("--follow-up-code", action="append", default=[])
    review_curation.add_argument("--predecessor-review-id")
    _actor(review_curation)


def _actor_value(args: argparse.Namespace) -> ActorAttribution:
    return ActorAttribution(
        actor_kind=args.actor_kind,
        actor_id=args.actor_id,
        owning_system=args.owning_system,
        role_snapshot=args.role,
    )


def _require_observed_match(args: argparse.Namespace, observed: int) -> None:
    expected = getattr(args, "expected_state_revision", None)
    if expected is not None and expected != observed:
        raise CandidateReviewError(
            "candidate_review.state_changed",
            f"Vitrine state changed: expected {expected}, found {observed}; review again.",
        )


def _target_reference(raw: str) -> CurationTargetRef:
    parts = raw.split(":", 3)
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "--target must use KIND:ID[:REVISION[:ROLE]].",
        )
    revision: int | None = None
    if len(parts) >= 3 and parts[2]:
        try:
            revision = int(parts[2])
        except ValueError as error:
            raise CandidateReviewError(
                "candidate_review.invalid_request",
                "Target revision must be a positive integer when provided.",
            ) from error
        if revision < 1:
            raise CandidateReviewError(
                "candidate_review.invalid_request",
                "Target revision must be a positive integer when provided.",
            )
    role = parts[3] if len(parts) == 4 and parts[3] else None
    try:
        return CurationTargetRef(
            target_kind=parts[0],
            target_id=parts[1],
            target_revision=revision,
            semantic_role=role,
        )
    except VitrineModelValidationError as error:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "--target does not identify a valid exact curation target.",
        ) from error


def _targets(values: list[str]) -> tuple[CurationTargetRef, ...]:
    return tuple(_target_reference(value) for value in values)


def _optional_targets(values: list[str] | None) -> tuple[CurationTargetRef, ...] | None:
    if values is None:
        return None
    return _targets(values)


def _target_label(target: CurationTargetRef) -> str:
    value = f"{target.target_kind}:{target.target_id}"
    if target.target_revision is not None or target.semantic_role is not None:
        value += f":{target.target_revision or ''}"
    if target.semantic_role is not None:
        value += f":{target.semantic_role}"
    return value


def _print_detail(detail: CandidateReviewDetail, *, output: TextIO) -> None:
    item = detail.inbox_detail.item
    print(f"Candidate Review Entry: {item.entry_id}", file=output)
    print(f"Observed state revision: {detail.observed_state_revision}", file=output)
    print(f"Source: {item.source_display_label}", file=output)
    print(f"Portfolio: {item.portfolio_id}", file=output)
    print(f"Subject: {item.portfolio_subject_id}", file=output)
    print(f"Profile Binding: {item.profile_binding_id}", file=output)
    print(
        f"Profile: {item.portfolio_profile_id}@{item.profile_revision} ({item.profile_purpose})",
        file=output,
    )
    print(f"Candidate: {item.candidate_id or '(evaluation-only)'}", file=output)
    print(
        f"Current review Evaluation: {detail.current_review_evaluation_id or '(unresolved)'}",
        file=output,
    )
    print(
        "Curation provenance Evaluation: "
        f"{detail.curation_provenance_evaluation_id or '(not selectable)'}",
        file=output,
    )
    print(
        "Evaluation heads differ: "
        f"{'yes' if detail.current_evaluation_differs_from_curation_provenance else 'no'}",
        file=output,
    )
    print(f"Evaluation outcome: {item.evaluation_outcome or '(none)'}", file=output)
    print(f"Candidate condition: {item.candidate_condition or '(none)'}", file=output)
    print(f"Currentness: {item.stale_state or '(none)'}", file=output)
    print(
        f"Stale reasons: {', '.join(item.stale_reason_codes) or '(none)'}",
        file=output,
    )
    print(f"Selectable: {'yes' if detail.selectable else 'no'}", file=output)
    if detail.source is not None:
        source = detail.source
        print(f"Core Publication: {source.core_publication_id}", file=output)
        print(
            f"Core state: series={source.observed_series_state}; withdrawal={source.observed_withdrawal_state}",
            file=output,
        )
        print(f"Producer module: {source.producer_module_id}", file=output)
        print(
            f"Producer source: {source.source_record_kind}:{source.source_record_id}",
            file=output,
        )
        print(
            f"Producer native revision: {source.native_revision if source.native_revision is not None else '(none)'}",
            file=output,
        )
        print(f"Artifact: {source.artifact_id or '(none)'}", file=output)
    print("Eligible sections:", file=output)
    for section in detail.sections:
        maximum = "unbounded" if section.maximum_placements is None else str(section.maximum_placements)
        pointer = (
            "conflict"
            if section.arrangement_pointer_conflict
            else str(section.arrangement_pointer_revision or "none")
        )
        print(
            f"  {section.section_id}\t{section.label}\tplacements={section.active_placement_count}/{maximum}\tpointer={pointer}",
            file=output,
        )
    print(
        "Profile requirements: "
        f"{', '.join(detail.profile_requirement_ids) or '(none)'}",
        file=output,
    )
    print("Selection history:", file=output)
    if not detail.selections:
        print("  (none)", file=output)
    for selection in detail.selections:
        print(
            f"  {selection.selection_id}\t{selection.lifecycle_state}\tEvaluation={selection.candidate_evaluation_id}\tplacements={','.join(selection.active_placement_ids) or '(none)'}",
            file=output,
        )
    pending = tuple(value for value in detail.proposals if value.undecided)
    print(
        "Undecided Proposals: "
        + (
            ", ".join(value.selection_proposal_id for value in pending)
            or "(none)"
        ),
        file=output,
    )
    print(
        f"Annotations: {len(detail.annotations)}; Reflections: {len(detail.reflections)}; Reviews: {len(detail.reviews)}",
        file=output,
    )


def _print_decision_plan(plan: CandidateReviewActionPlan, *, output: TextIO) -> None:
    print("Candidate decision plan", file=output)
    print(f"Entry: {plan.entry_id}", file=output)
    print(f"Portfolio: {plan.portfolio_id}", file=output)
    print(f"Candidate: {plan.candidate_id}", file=output)
    print(
        f"Current review Evaluation: {plan.current_review_evaluation_id or '(unresolved)'}",
        file=output,
    )
    print(
        f"Curation provenance Evaluation: {plan.curation_provenance_evaluation_id}",
        file=output,
    )
    print(f"Decision: {plan.decision}", file=output)
    print(f"Operation: {plan.operation}", file=output)
    print(f"Sections: {', '.join(plan.proposed_section_ids)}", file=output)
    print(
        f"Profile requirements: {', '.join(plan.intended_profile_requirement_ids) or '(none)'}",
        file=output,
    )
    print(f"Candidate condition: {plan.candidate_condition}", file=output)
    print(
        f"Stale reasons: {', '.join(plan.stale_reason_codes) or '(none)'}",
        file=output,
    )
    print(f"Expected state revision: {plan.observed_state_revision}", file=output)
    print(f"Confirmation phrase: {plan.confirmation_phrase}", file=output)


def _print_content_plan(
    label: str,
    plan: CandidateReviewAnnotationActionPlan
    | CandidateReviewReflectionActionPlan
    | CandidateReviewCurationReviewActionPlan,
    *,
    output: TextIO,
) -> None:
    print(label, file=output)
    print(f"Entry: {plan.entry_id}", file=output)
    print(f"Portfolio: {plan.portfolio_id}", file=output)
    print(f"Targets: {', '.join(_target_label(x) for x in plan.target_references)}", file=output)
    print(f"Expected state revision: {plan.observed_state_revision}", file=output)
    print(f"Confirmation phrase: {plan.confirmation_phrase}", file=output)


def _run_decide(
    args: argparse.Namespace,
    *,
    dependencies: VitrineWorkflowDependencies,
    output: TextIO,
) -> int:
    plan = plan_candidate_decision(
        args.workspace_root,
        entry_id=args.entry_id,
        decision=args.decision,
        proposed_section_ids=tuple(args.section_id),
        intended_profile_requirement_ids=tuple(args.requirement_id),
    )
    _require_observed_match(args, plan.observed_state_revision)
    if plan.condition_acknowledgement_required and not args.acknowledge_condition:
        raise CandidateReviewError(
            "candidate_review.invalid_request",
            "Positive Selection requires --acknowledge-condition after reviewing the exact Candidate condition. This acknowledgement does not clear the condition.",
        )
    _print_decision_plan(plan, output=output)
    if plan.condition_acknowledgement_required:
        print(
            "Condition acknowledgement recorded only as CLI intent; it does not satisfy or clear the condition.",
            file=output,
        )
    result = execute_candidate_decision(
        args.workspace_root,
        plan,
        actor=_actor_value(args),
        authority_gate=dependencies.curation_authority_gate,
        rationale_text=args.reason,
    )
    print(f"Candidate decision recorded.\nState revision: {result.state_revision}", file=output)
    return 0


def _run_annotation(
    args: argparse.Namespace,
    *,
    dependencies: VitrineWorkflowDependencies,
    output: TextIO,
) -> int:
    if args.candidate_annotation_command == "add":
        plan = plan_annotation_creation(
            args.workspace_root,
            entry_id=args.entry_id,
            purpose=args.purpose,
            target_scope=args.scope,
            target_references=_targets(args.target),
            content=args.content,
            language=args.language,
            content_format=args.content_format,
            intended_presentation_class=args.presentation_class,
        )
    else:
        plan = plan_annotation_revision(
            args.workspace_root,
            entry_id=args.entry_id,
            annotation_id=args.annotation_id,
            content=args.content,
            purpose=args.purpose,
            target_scope=args.scope,
            target_references=_optional_targets(args.target),
            language=args.language,
            content_format=args.content_format,
            intended_presentation_class=args.presentation_class,
        )
    _require_observed_match(args, plan.observed_state_revision)
    _print_content_plan("Annotation plan", plan, output=output)
    result = execute_annotation_action(
        args.workspace_root,
        plan,
        author=_actor_value(args),
        authority_gate=dependencies.curation_authority_gate,
    )
    print(f"Annotation recorded.\nState revision: {result.state_revision}", file=output)
    return 0


def _run_reflection(
    args: argparse.Namespace,
    *,
    dependencies: VitrineWorkflowDependencies,
    output: TextIO,
) -> int:
    if args.candidate_reflection_command == "add":
        plan = plan_reflection_creation(
            args.workspace_root,
            entry_id=args.entry_id,
            reflection_requirement_id=args.requirement_id,
            prompt_id=args.prompt_id,
            prompt_version=args.prompt_version,
            prompt_snapshot=args.prompt_snapshot,
            target_scope=args.scope,
            target_references=_targets(args.target),
            content=args.content,
            content_mode=args.content_mode,
            language=args.language,
            content_format=args.content_format,
        )
    else:
        plan = plan_reflection_revision(
            args.workspace_root,
            entry_id=args.entry_id,
            reflection_id=args.reflection_id,
            content=args.content,
            prompt_id=args.prompt_id,
            prompt_version=args.prompt_version,
            prompt_snapshot=args.prompt_snapshot,
            target_scope=args.scope,
            target_references=_optional_targets(args.target),
        )
    _require_observed_match(args, plan.observed_state_revision)
    _print_content_plan("Reflection plan", plan, output=output)
    result = execute_reflection_action(
        args.workspace_root,
        plan,
        author=_actor_value(args),
        authority_gate=dependencies.curation_authority_gate,
    )
    print(f"Reflection recorded.\nState revision: {result.state_revision}", file=output)
    return 0


def _run_curation_review(
    args: argparse.Namespace,
    *,
    dependencies: VitrineWorkflowDependencies,
    output: TextIO,
) -> int:
    plan = plan_curation_review(
        args.workspace_root,
        entry_id=args.entry_id,
        target_scope=args.scope,
        target_references=_targets(args.target),
        decision=args.decision,
        reason=args.reason,
        approval_requirement_id=args.approval_requirement_id,
        required_follow_up_codes=tuple(args.follow_up_code),
        predecessor_review_decision_id=args.predecessor_review_id,
    )
    _require_observed_match(args, plan.observed_state_revision)
    _print_content_plan("Curation Review plan", plan, output=output)
    result = execute_curation_review(
        args.workspace_root,
        plan,
        reviewed_by=_actor_value(args),
        authority_gate=dependencies.curation_authority_gate,
    )
    print(f"Curation Review recorded.\nState revision: {result.state_revision}", file=output)
    return 0


def run_candidate_review_command(
    args: argparse.Namespace,
    *,
    dependencies: VitrineWorkflowDependencies,
    output: TextIO,
) -> int:
    """Run one task-level Candidate review command without prompting."""

    command = args.candidate_command
    if command == "review":
        _print_detail(
            get_candidate_review_detail(args.workspace_root, args.entry_id),
            output=output,
        )
        return 0
    if command == "decide":
        return _run_decide(args, dependencies=dependencies, output=output)
    if command == "annotation":
        return _run_annotation(args, dependencies=dependencies, output=output)
    if command == "reflection":
        return _run_reflection(args, dependencies=dependencies, output=output)
    if command == "curation-review":
        return _run_curation_review(args, dependencies=dependencies, output=output)
    raise AssertionError(f"Unhandled Candidate review command: {command}")


__all__ = [
    "CANDIDATE_REVIEW_CLI_COMMANDS",
    "configure_candidate_review_parsers",
    "run_candidate_review_command",
]
