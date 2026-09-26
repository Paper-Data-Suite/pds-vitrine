"""Application services for paper-native Reflection prompt issuance."""

from __future__ import annotations

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
    CurationTargetRef,
    PortfolioSubjectClassLink,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
)
from vitrine.models.common import require_positive_int
from vitrine.models.errors import VitrineModelValidationError


def _page_count(value: int) -> int:
    try:
        return require_positive_int(value, "page_count")
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Reflection issuance page_count must be a positive integer.",
            stage="reflection_issuance",
        ) from error


def _subject_link(
    context: _Context,
    subject_link_id: str | None,
) -> PortfolioSubjectClassLink:
    # _load_context is the package's canonical exact Portfolio/Profile resolver.
    identity = project_identity_state(context.records)
    links = identity.current_links(context.portfolio.portfolio_subject_id)

    if subject_link_id is None:
        if not links:
            raise CurationWorkflowError(
                "curation.reflection_author_unresolved",
                "Portfolio Subject has no current class-qualified student link.",
                stage="reflection_issuance",
            )
        if len(links) != 1:
            raise CurationWorkflowError(
                "curation.reflection_author_unresolved",
                "Portfolio Subject has multiple current class-qualified student links; "
                "an exact subject_link_id is required.",
                stage="reflection_issuance",
            )
        return links[0]

    matches = tuple(item for item in links if item.subject_link_id == subject_link_id)
    if len(matches) != 1:
        raise CurationWorkflowError(
            "curation.reflection_author_unresolved",
            "Selected subject_link_id is not a current link for the exact Portfolio Subject.",
            stage="reflection_issuance",
        )
    return matches[0]


def prepare_reflection_issuance(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    reflection_requirement_id: str,
    prompt_id: str,
    prompt_version: str,
    prompt_snapshot: str,
    target_scope: str,
    target_references: tuple[CurationTargetRef, ...],
    issued_by: ActorAttribution,
    page_count: int,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    subject_link_id: str | None = None,
    clock: Clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    """Freeze one exact paper Reflection issuance and its ordered response pages.

    The authorized adult is the issuer/mutation actor only. The class-qualified
    student carried by the selected subject link is expected authorship context,
    not a canonical Reflection author claim. Authorship is confirmed only after
    returned paper is reviewed in a later workflow.
    """

    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    requirement = _reflection_requirement(context, reflection_requirement_id)
    targets = tuple(target_references)
    _validate_targets(context, targets)

    if issued_by.actor_kind != "authorized_adult":
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Paper Reflection issuance requires an authorized-adult issuer.",
            stage="reflection_issuance",
        )

    selected_link = _subject_link(context, subject_link_id)
    count = _page_count(page_count)

    _authority(
        authority_gate,
        context,
        issued_by,
        "reflect",
        targets=targets,
        requirement_ids=(requirement.requirement_id,),
    )

    now = _now(clock)
    issuance_id = id_factory("reflection_issuance")
    work_id = id_factory("reflection_work")
    response_page_ids = tuple(id_factory("reflection_page") for _ in range(count))
    route_ids = tuple(id_factory("reflection_route") for _ in range(count))

    pages = tuple(
        ReflectionResponsePage(
            response_page_id=response_page_id,
            issuance_id=issuance_id,
            class_id=selected_link.student_reference.class_id,
            work_id=work_id,
            route_id=route_id,
            logical_page_number=index,
            total_pages=count,
            created_at=now,
            created_by=issued_by,
        )
        for index, (response_page_id, route_id) in enumerate(
            zip(response_page_ids, route_ids, strict=True),
            start=1,
        )
    )
    issuance = ReflectionPromptIssuance(
        issuance_id=issuance_id,
        portfolio_id=context.portfolio.portfolio_id,
        portfolio_subject_id=context.portfolio.portfolio_subject_id,
        profile_binding_id=context.binding.profile_binding_id,
        profile_revision=context.binding.profile_revision,
        reflection_requirement_id=requirement.requirement_id,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        prompt_snapshot=prompt_snapshot,
        target_scope=target_scope,
        target_references=targets,
        subject_link_id=selected_link.subject_link_id,
        student_reference=selected_link.student_reference,
        response_page_ids=response_page_ids,
        issued_at=now,
        issued_by=issued_by,
    )
    return _validated_commit(
        workspace_root,
        context,
        (issuance, *pages),
    )


__all__ = ["prepare_reflection_issuance"]
