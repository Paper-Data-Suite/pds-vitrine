"""Typed/manual Reflection fallback with separated author and recorder."""

from __future__ import annotations

from pathlib import Path

from vitrine.curation_services import (
    Clock,
    CurationAuthorityGate,
    CurationMutationResult,
    CurationWorkflowError,
    IdFactory,
    _authority,
    _clock,
    _Context,
    _id,
    _load_context,
    _now,
    _reflection_requirement,
    _validate_targets,
    _validated_commit,
)
from vitrine.identity_state import project_identity_state
from vitrine.models import (
    ActorAttribution,
    CurationTargetRef,
    PortfolioReflection,
    PortfolioSubjectClassLink,
    ReflectionManualEntryProvenance,
)

_TYPED_ENTRY_MODE = "typed_by_authorized_adult"


def create_typed_reflection(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    reflection_requirement_id: str,
    prompt_id: str,
    prompt_version: str,
    prompt_snapshot: str,
    subject_link_id: str,
    recorded_by: ActorAttribution,
    target_scope: str,
    target_references: tuple[CurationTargetRef, ...],
    content: str,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    language: str = "en",
    content_format: str = "plain_text",
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    """Create a typed fallback Reflection authored by the exact linked student."""

    context = _load_context(
        workspace_root,
        portfolio_id,
        expected_state_revision,
    )
    requirement = _reflection_requirement(
        context,
        reflection_requirement_id,
    )
    targets = tuple(target_references)
    _validate_targets(context, targets)
    link = _exact_current_link(context, subject_link_id)
    _authorized_adult(recorded_by, "recorded_by")
    authority = _authority(
        authority_gate,
        context,
        recorded_by,
        "reflect",
        targets=targets,
        requirement_ids=(requirement.requirement_id,),
    )
    now = _now(clock)
    student_author = _student_author(link)
    reflection = PortfolioReflection(
        reflection_id=id_factory("reflection"),
        reflection_revision=1,
        portfolio_id=context.portfolio.portfolio_id,
        portfolio_subject_id=context.portfolio.portfolio_subject_id,
        profile_binding_id=context.binding.profile_binding_id,
        profile_revision=context.binding.profile_revision,
        reflection_requirement_id=requirement.requirement_id,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        prompt_snapshot=prompt_snapshot,
        author=student_author,
        target_scope=target_scope,
        target_references=targets,
        content_mode="inline_text",
        language=language,
        content_format=content_format,
        content=content,
        created_at=now,
    )
    provenance = ReflectionManualEntryProvenance(
        manual_entry_provenance_id=id_factory(
            "reflection_manual_entry"
        ),
        reflection_id=reflection.reflection_id,
        reflection_revision=reflection.reflection_revision,
        portfolio_id=reflection.portfolio_id,
        portfolio_subject_id=reflection.portfolio_subject_id,
        subject_link_id=link.subject_link_id,
        student_reference=link.student_reference,
        entry_mode=_TYPED_ENTRY_MODE,
        recorded_at=now,
        recorded_by=recorded_by,
        authority_reference=authority.authority_reference or "",
    )
    return _validated_commit(
        workspace_root,
        context,
        (reflection, provenance),
    )


def revise_typed_reflection(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    reflection_id: str,
    expected_reflection_revision: int,
    subject_link_id: str,
    recorded_by: ActorAttribution,
    content: str,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    """Revise typed content while preserving prompt, targets, and student author."""

    context = _load_context(
        workspace_root,
        portfolio_id,
        expected_state_revision,
    )
    heads = context.curation.reflection_heads(reflection_id)
    if (
        len(heads) != 1
        or heads[0].reflection_revision != expected_reflection_revision
    ):
        raise CurationWorkflowError(
            "curation.reflection_revision_conflict",
            "Reflection revision head changed since caller observation.",
            stage="typed_reflection",
        )
    prior = heads[0]
    if prior.content_mode != "inline_text":
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Typed fallback can revise only inline-text Reflections.",
            stage="typed_reflection",
        )
    if prior.author.actor_kind != "core_student":
        raise CurationWorkflowError(
            "curation.reflection_author_unresolved",
            "Typed Reflection revision requires an existing student author.",
            stage="typed_reflection",
        )
    _reflection_requirement(context, prior.reflection_requirement_id)
    _validate_targets(context, prior.target_references)
    link = _exact_current_link(context, subject_link_id)
    if link.student_reference.student_id != prior.author.actor_id:
        raise CurationWorkflowError(
            "curation.reflection_author_unresolved",
            "Selected Subject link does not match the existing student author.",
            stage="typed_reflection",
        )
    _authorized_adult(recorded_by, "recorded_by")
    authority = _authority(
        authority_gate,
        context,
        recorded_by,
        "reflect",
        targets=prior.target_references,
        requirement_ids=(prior.reflection_requirement_id,),
    )
    now = _now(clock)
    revised = PortfolioReflection(
        reflection_id=prior.reflection_id,
        reflection_revision=prior.reflection_revision + 1,
        portfolio_id=prior.portfolio_id,
        portfolio_subject_id=prior.portfolio_subject_id,
        profile_binding_id=prior.profile_binding_id,
        profile_revision=prior.profile_revision,
        reflection_requirement_id=prior.reflection_requirement_id,
        prompt_id=prior.prompt_id,
        prompt_version=prior.prompt_version,
        prompt_snapshot=prior.prompt_snapshot,
        author=prior.author,
        target_scope=prior.target_scope,
        target_references=prior.target_references,
        content_mode=prior.content_mode,
        language=prior.language,
        content_format=prior.content_format,
        content=content,
        created_at=now,
        predecessor_reflection_revision=prior.reflection_revision,
    )
    provenance = ReflectionManualEntryProvenance(
        manual_entry_provenance_id=id_factory(
            "reflection_manual_entry"
        ),
        reflection_id=revised.reflection_id,
        reflection_revision=revised.reflection_revision,
        portfolio_id=revised.portfolio_id,
        portfolio_subject_id=revised.portfolio_subject_id,
        subject_link_id=link.subject_link_id,
        student_reference=link.student_reference,
        entry_mode=_TYPED_ENTRY_MODE,
        recorded_at=now,
        recorded_by=recorded_by,
        authority_reference=authority.authority_reference or "",
    )
    return _validated_commit(
        workspace_root,
        context,
        (revised, provenance),
    )


def _exact_current_link(
    context: _Context,
    subject_link_id: str,
) -> PortfolioSubjectClassLink:
    links = project_identity_state(context.records).current_links(
        context.portfolio.portfolio_subject_id
    )
    matches = tuple(
        item
        for item in links
        if item.subject_link_id == subject_link_id
    )
    if len(matches) != 1:
        raise CurationWorkflowError(
            "curation.reflection_author_unresolved",
            "Exact current Portfolio Subject class/student link is unavailable.",
            stage="typed_reflection",
        )
    return matches[0]


def _student_author(
    link: PortfolioSubjectClassLink,
) -> ActorAttribution:
    return ActorAttribution(
        actor_kind="core_student",
        actor_id=link.student_reference.student_id,
        owning_system="core",
        role_snapshot="student",
    )


def _authorized_adult(
    actor: ActorAttribution,
    field_name: str,
) -> None:
    if not isinstance(actor, ActorAttribution):
        raise CurationWorkflowError(
            "curation.invalid_request",
            f"{field_name} must be ActorAttribution.",
            stage="typed_reflection",
        )
    if actor.actor_kind != "authorized_adult":
        raise CurationWorkflowError(
            "curation.invalid_request",
            f"{field_name} must be an authorized_adult.",
            stage="typed_reflection",
        )


__all__ = [
    "create_typed_reflection",
    "revise_typed_reflection",
]
