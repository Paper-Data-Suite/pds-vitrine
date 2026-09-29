"""Teacher confirmation and canonical finalization for paper Reflections."""

from __future__ import annotations

import json
from pathlib import Path

from vitrine.curation_services import (
    Clock,
    CurationAuthorityGate,
    CurationMutationResult,
    CurationWorkflowError,
    IdFactory,
    _authority,
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
    PortfolioReflection,
    PortfolioSubjectClassLink,
    ReflectionAuthorshipConfirmation,
    ReflectionPaperFinalization,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
    ReflectionReturnedPaperEvidence,
)
from vitrine.models.common import identifier_tuple
from vitrine.models.errors import VitrineModelValidationError

_PAPER_CONTENT_FORMAT = "vitrine:returned_paper_evidence"


def confirm_returned_paper_authorship(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    issuance_id: str,
    returned_paper_evidence_ids: tuple[str, ...],
    confirmed_by: ActorAttribution,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    confirmation_basis: str = "teacher_reviewed_original_paper",
    clock: Clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    """Confirm student authorship without yet creating a PortfolioReflection."""

    context = _load_context(
        workspace_root,
        portfolio_id,
        expected_state_revision,
    )
    issuance = _issuance(context, issuance_id)
    _require_issuance_context(context, issuance)
    requirement = _reflection_requirement(
        context,
        issuance.reflection_requirement_id,
    )
    _validate_targets(context, issuance.target_references)
    link = _current_issuance_link(context, issuance)
    evidence = _selected_evidence(
        context,
        issuance,
        returned_paper_evidence_ids,
    )
    _authorized_adult(confirmed_by, "confirmed_by")

    existing = tuple(
        item
        for item in context.records
        if isinstance(item, ReflectionAuthorshipConfirmation)
        and item.issuance_id == issuance.issuance_id
    )
    expected_evidence_ids = tuple(
        item.returned_paper_evidence_id for item in evidence
    )
    if existing:
        if len(existing) != 1:
            raise CurationWorkflowError(
                "curation.invalid_request",
                "Reflection issuance has conflicting authorship confirmations.",
                stage="reflection_authorship",
            )
        confirmation = existing[0]
        if (
            confirmation.subject_link_id == link.subject_link_id
            and confirmation.student_reference == link.student_reference
            and confirmation.returned_paper_evidence_ids
            == expected_evidence_ids
            and confirmation.confirmation_basis == confirmation_basis
            and confirmation.confirmed_by == confirmed_by
        ):
            return CurationMutationResult(
                state_revision=context.state_revision,
                records=(confirmation,),
                disposition="existing",
            )
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Reflection issuance already has a different authorship confirmation.",
            stage="reflection_authorship",
        )

    authority = _authority(
        authority_gate,
        context,
        confirmed_by,
        "reflect",
        targets=issuance.target_references,
        requirement_ids=(requirement.requirement_id,),
    )
    confirmation = ReflectionAuthorshipConfirmation(
        authorship_confirmation_id=id_factory(
            "reflection_authorship_confirmation"
        ),
        issuance_id=issuance.issuance_id,
        portfolio_id=issuance.portfolio_id,
        portfolio_subject_id=issuance.portfolio_subject_id,
        subject_link_id=link.subject_link_id,
        student_reference=link.student_reference,
        returned_paper_evidence_ids=expected_evidence_ids,
        confirmation_basis=confirmation_basis,
        confirmed_at=_now(clock),
        confirmed_by=confirmed_by,
        authority_reference=authority.authority_reference or "",
    )
    return _validated_commit(
        workspace_root,
        context,
        (confirmation,),
    )


def finalize_confirmed_paper_reflection(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    authorship_confirmation_id: str,
    recorded_by: ActorAttribution,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    clock: Clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    """Create the canonical paper-backed Reflection after explicit confirmation."""

    context = _load_context(
        workspace_root,
        portfolio_id,
        expected_state_revision,
    )
    confirmation = _confirmation(
        context,
        authorship_confirmation_id,
    )
    issuance = _issuance(context, confirmation.issuance_id)
    _require_issuance_context(context, issuance)
    requirement = _reflection_requirement(
        context,
        issuance.reflection_requirement_id,
    )
    _validate_targets(context, issuance.target_references)
    link = _current_issuance_link(context, issuance)
    if (
        confirmation.portfolio_id != issuance.portfolio_id
        or confirmation.portfolio_subject_id
        != issuance.portfolio_subject_id
        or confirmation.subject_link_id != link.subject_link_id
        or confirmation.student_reference != link.student_reference
    ):
        raise CurationWorkflowError(
            "curation.reflection_author_unresolved",
            "Authorship confirmation no longer matches the exact current Subject link.",
            stage="paper_reflection",
        )
    evidence = _selected_evidence(
        context,
        issuance,
        confirmation.returned_paper_evidence_ids,
    )
    _authorized_adult(recorded_by, "recorded_by")

    existing_finalizations = tuple(
        item
        for item in context.records
        if isinstance(item, ReflectionPaperFinalization)
        and item.authorship_confirmation_id
        == confirmation.authorship_confirmation_id
    )
    if existing_finalizations:
        if len(existing_finalizations) != 1:
            raise CurationWorkflowError(
                "curation.composition_inconsistent",
                "Authorship confirmation has conflicting paper finalizations.",
                stage="paper_reflection",
            )
        finalization = existing_finalizations[0]
        reflection = next(
            (
                item
                for item in context.curation.reflections
                if item.reflection_id == finalization.reflection_id
                and item.reflection_revision
                == finalization.reflection_revision
            ),
            None,
        )
        if reflection is None:
            raise CurationWorkflowError(
                "curation.composition_inconsistent",
                "Paper finalization does not resolve to its canonical Reflection.",
                stage="paper_reflection",
            )
        return CurationMutationResult(
            state_revision=context.state_revision,
            records=(reflection, finalization),
            disposition="existing",
        )

    authority = _authority(
        authority_gate,
        context,
        recorded_by,
        "reflect",
        targets=issuance.target_references,
        requirement_ids=(requirement.requirement_id,),
    )
    now = _now(clock)
    student_author = ActorAttribution(
        actor_kind="core_student",
        actor_id=confirmation.student_reference.student_id,
        owning_system="core",
        role_snapshot="student",
    )
    evidence_ids = tuple(
        item.returned_paper_evidence_id for item in evidence
    )
    content = json.dumps(
        {"returned_paper_evidence_ids": list(evidence_ids)},
        separators=(",", ":"),
        sort_keys=True,
    )
    reflection = PortfolioReflection(
        reflection_id=id_factory("reflection"),
        reflection_revision=1,
        portfolio_id=issuance.portfolio_id,
        portfolio_subject_id=issuance.portfolio_subject_id,
        profile_binding_id=issuance.profile_binding_id,
        profile_revision=issuance.profile_revision,
        reflection_requirement_id=issuance.reflection_requirement_id,
        prompt_id=issuance.prompt_id,
        prompt_version=issuance.prompt_version,
        prompt_snapshot=issuance.prompt_snapshot,
        author=student_author,
        target_scope=issuance.target_scope,
        target_references=issuance.target_references,
        content_mode="external_reference",
        language="und",
        content_format=_PAPER_CONTENT_FORMAT,
        content=content,
        created_at=now,
    )
    finalization = ReflectionPaperFinalization(
        paper_finalization_id=id_factory("reflection_paper_finalization"),
        authorship_confirmation_id=confirmation.authorship_confirmation_id,
        reflection_id=reflection.reflection_id,
        reflection_revision=reflection.reflection_revision,
        returned_paper_evidence_ids=evidence_ids,
        student_author=student_author,
        recorded_at=now,
        recorded_by=recorded_by,
        authority_reference=authority.authority_reference or "",
    )
    return _validated_commit(
        workspace_root,
        context,
        (reflection, finalization),
    )


def _issuance(
    context: _Context,
    issuance_id: str,
) -> ReflectionPromptIssuance:
    matches = tuple(
        item
        for item in context.records
        if isinstance(item, ReflectionPromptIssuance)
        and item.issuance_id == issuance_id
    )
    if len(matches) != 1:
        raise CurationWorkflowError(
            "curation.context_not_found",
            "Exact Reflection prompt issuance is missing or ambiguous.",
            stage="paper_reflection",
        )
    return matches[0]


def _confirmation(
    context: _Context,
    confirmation_id: str,
) -> ReflectionAuthorshipConfirmation:
    matches = tuple(
        item
        for item in context.records
        if isinstance(item, ReflectionAuthorshipConfirmation)
        and item.authorship_confirmation_id == confirmation_id
    )
    if len(matches) != 1:
        raise CurationWorkflowError(
            "curation.context_not_found",
            "Exact Reflection authorship confirmation is missing or ambiguous.",
            stage="paper_reflection",
        )
    return matches[0]


def _require_issuance_context(
    context: _Context,
    issuance: ReflectionPromptIssuance,
) -> None:
    expected = (
        context.portfolio.portfolio_id,
        context.portfolio.portfolio_subject_id,
        context.binding.profile_binding_id,
        context.binding.profile_revision,
    )
    actual = (
        issuance.portfolio_id,
        issuance.portfolio_subject_id,
        issuance.profile_binding_id,
        issuance.profile_revision,
    )
    if actual != expected:
        raise CurationWorkflowError(
            "curation.profile_mismatch",
            "Paper Reflection issuance belongs to another Portfolio/Profile context.",
            stage="paper_reflection",
        )


def _current_issuance_link(
    context: _Context,
    issuance: ReflectionPromptIssuance,
) -> PortfolioSubjectClassLink:
    state = project_identity_state(context.records)
    links = state.current_links(issuance.portfolio_subject_id)
    matches = tuple(
        link
        for link in links
        if link.subject_link_id == issuance.subject_link_id
        and link.student_reference == issuance.student_reference
    )
    if len(matches) != 1:
        raise CurationWorkflowError(
            "curation.reflection_author_unresolved",
            "Issued class-qualified student link is no longer exact and current.",
            stage="reflection_authorship",
        )
    return matches[0]


def _selected_evidence(
    context: _Context,
    issuance: ReflectionPromptIssuance,
    evidence_ids: tuple[str, ...],
) -> tuple[ReflectionReturnedPaperEvidence, ...]:
    try:
        selected_ids = identifier_tuple(
            evidence_ids,
            "returned_paper_evidence_ids",
            nonempty=True,
        )
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Returned-paper evidence identifiers are invalid.",
            stage="paper_reflection",
        ) from error
    if len(selected_ids) != len(issuance.response_page_ids):
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Exactly one returned-paper evidence record is required for every issued page.",
            stage="paper_reflection",
        )

    pages = {
        item.response_page_id: item
        for item in context.records
        if isinstance(item, ReflectionResponsePage)
        and item.issuance_id == issuance.issuance_id
    }
    if set(pages) != set(issuance.response_page_ids):
        raise CurationWorkflowError(
            "curation.context_not_found",
            "Issuance response-page records are incomplete or contradictory.",
            stage="paper_reflection",
        )

    evidence_by_id = {
        item.returned_paper_evidence_id: item
        for item in context.records
        if isinstance(item, ReflectionReturnedPaperEvidence)
    }
    selected: list[ReflectionReturnedPaperEvidence] = []
    for response_page_id, evidence_id in zip(
        issuance.response_page_ids,
        selected_ids,
        strict=True,
    ):
        evidence = evidence_by_id.get(evidence_id)
        page = pages[response_page_id]
        if evidence is None:
            raise CurationWorkflowError(
                "curation.context_not_found",
                "Selected returned-paper evidence does not exist.",
                stage="paper_reflection",
            )
        if (
            evidence.issuance_id != issuance.issuance_id
            or evidence.response_page_id != response_page_id
            or evidence.route_id != page.route_id
            or evidence.class_id != page.class_id
            or evidence.work_id != page.work_id
        ):
            raise CurationWorkflowError(
                "curation.invalid_request",
                "Selected evidence does not match its exact issued response page.",
                stage="paper_reflection",
            )
        selected.append(evidence)
    return tuple(selected)


def _authorized_adult(actor: ActorAttribution, field_name: str) -> None:
    if not isinstance(actor, ActorAttribution):
        raise CurationWorkflowError(
            "curation.invalid_request",
            f"{field_name} must be ActorAttribution.",
            stage="paper_reflection",
        )
    if actor.actor_kind != "authorized_adult":
        raise CurationWorkflowError(
            "curation.invalid_request",
            f"{field_name} must be an authorized_adult.",
            stage="paper_reflection",
        )


__all__ = [
    "confirm_returned_paper_authorship",
    "finalize_confirmed_paper_reflection",
]
