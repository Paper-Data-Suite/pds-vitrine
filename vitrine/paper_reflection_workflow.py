"""Read-only Portfolio-level projection for paper-native student Reflection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vitrine.models import (
    Portfolio,
    PortfolioProfileRequirement,
    PortfolioReflection,
    ReflectionAuthorshipConfirmation,
    ReflectionPaperFinalization,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
    ReflectionReturnedPaperEvidence,
)
from vitrine.profile_state import project_profile_state
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
)

PAPER_REFLECTION_WORKFLOW_CONTRACT_VERSION: Final[str] = (
    "vitrine_paper_reflection_workflow_v1"
)
PAPER_REFLECTION_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "not_issued",
        "issued_awaiting_return",
        "returned_needs_review",
        "confirmed_needs_recording",
        "recorded",
        "attention_required",
    }
)


class PaperReflectionWorkflowError(RuntimeError):
    """Read-only projection failure for one Portfolio's Reflection workflow."""


@dataclass(frozen=True, slots=True)
class PaperReflectionRequirementStatus:
    requirement_id: str
    title: str
    statement: str
    obligation: str
    status: str
    issuance_id: str | None
    prompt_snapshot: str | None
    target_count: int
    issued_page_count: int
    returned_page_count: int
    returned_occurrence_count: int
    rescan_choice_required: bool
    authorship_confirmation_id: str | None
    reflection_id: str | None
    reflection_revision: int | None
    paper_finalization_id: str | None
    explanation: str

    def __post_init__(self) -> None:
        if self.status not in PAPER_REFLECTION_STATUSES:
            raise ValueError("unsupported paper Reflection workflow status")
        for value in (
            self.target_count,
            self.issued_page_count,
            self.returned_page_count,
            self.returned_occurrence_count,
        ):
            if value < 0:
                raise ValueError(
                    "paper Reflection workflow counts must be nonnegative"
                )


@dataclass(frozen=True, slots=True)
class PaperReflectionWorkflowView:
    contract_version: str
    observed_state_revision: int
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    requirements: tuple[PaperReflectionRequirementStatus, ...]

    def __post_init__(self) -> None:
        if self.contract_version != PAPER_REFLECTION_WORKFLOW_CONTRACT_VERSION:
            raise ValueError(
                "unexpected paper Reflection workflow contract version"
            )
        if self.observed_state_revision <= 0:
            raise ValueError("observed_state_revision must be positive")


def build_paper_reflection_workflow_view(
    workspace_root: str | Path,
    portfolio_id: str,
) -> PaperReflectionWorkflowView:
    """Project the exact paper-Reflection lifecycle without mutating state."""

    try:
        current, records = load_current_records_with_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise PaperReflectionWorkflowError(
            "Canonical Vitrine state is unavailable for Student Reflection."
        ) from error

    portfolios = tuple(
        item
        for item in records
        if isinstance(item, Portfolio) and item.portfolio_id == portfolio_id
    )
    if len(portfolios) != 1:
        raise PaperReflectionWorkflowError(
            "Exact Portfolio is missing or ambiguous for Student Reflection."
        )
    portfolio = portfolios[0]

    profile = project_profile_state(records)
    binding = profile.active_binding(portfolio_id)
    if binding is None:
        raise PaperReflectionWorkflowError(
            "Student Reflection requires one exact active Profile Binding."
        )
    requirements = tuple(
        item
        for item in profile.requirements_for(binding.profile_revision)
        if item.requirement_kind == "reflection"
    )

    projected = tuple(
        _project_requirement(
            records,
            portfolio_id=portfolio_id,
            portfolio_subject_id=portfolio.portfolio_subject_id,
            profile_binding_id=binding.profile_binding_id,
            requirement=requirement,
        )
        for requirement in requirements
    )
    return PaperReflectionWorkflowView(
        contract_version=PAPER_REFLECTION_WORKFLOW_CONTRACT_VERSION,
        observed_state_revision=current.state_revision,
        portfolio_id=portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        requirements=projected,
    )


def _project_requirement(
    records: tuple[object, ...],
    *,
    portfolio_id: str,
    portfolio_subject_id: str,
    profile_binding_id: str,
    requirement: PortfolioProfileRequirement,
) -> PaperReflectionRequirementStatus:
    issuances = tuple(
        item
        for item in records
        if isinstance(item, ReflectionPromptIssuance)
        and item.portfolio_id == portfolio_id
        and item.portfolio_subject_id == portfolio_subject_id
        and item.profile_binding_id == profile_binding_id
        and item.reflection_requirement_id == requirement.requirement_id
    )
    if not issuances:
        return _status(
            requirement,
            status="not_issued",
            explanation="No paper Reflection prompt has been issued.",
        )
    if len(issuances) != 1:
        return _status(
            requirement,
            status="attention_required",
            explanation=(
                "Multiple paper Reflection issuances exist for this exact "
                "requirement; teacher review must choose the intended issuance."
            ),
        )

    issuance = issuances[0]
    pages = tuple(
        item
        for item in records
        if isinstance(item, ReflectionResponsePage)
        and item.issuance_id == issuance.issuance_id
    )
    page_by_id = {item.response_page_id: item for item in pages}
    if (
        len(page_by_id) != len(issuance.response_page_ids)
        or set(page_by_id) != set(issuance.response_page_ids)
    ):
        return _status(
            requirement,
            status="attention_required",
            issuance=issuance,
            explanation=(
                "Issued paper response-page records are incomplete or contradictory."
            ),
        )

    evidence_by_page: dict[str, list[ReflectionReturnedPaperEvidence]] = {
        page_id: [] for page_id in issuance.response_page_ids
    }
    for item in records:
        if (
            isinstance(item, ReflectionReturnedPaperEvidence)
            and item.issuance_id == issuance.issuance_id
            and item.response_page_id in evidence_by_page
        ):
            evidence_by_page[item.response_page_id].append(item)

    returned_page_count = sum(
        bool(evidence_by_page[page_id])
        for page_id in issuance.response_page_ids
    )
    occurrence_count = sum(len(values) for values in evidence_by_page.values())
    rescan_choice_required = any(
        len(values) > 1 for values in evidence_by_page.values()
    )

    confirmations = tuple(
        item
        for item in records
        if isinstance(item, ReflectionAuthorshipConfirmation)
        and item.issuance_id == issuance.issuance_id
    )
    if len(confirmations) > 1:
        return _status(
            requirement,
            status="attention_required",
            issuance=issuance,
            returned_page_count=returned_page_count,
            occurrence_count=occurrence_count,
            rescan_choice_required=rescan_choice_required,
            explanation="Conflicting authorship confirmations require review.",
        )

    if len(confirmations) == 1:
        confirmation = confirmations[0]
        finalizations = tuple(
            item
            for item in records
            if isinstance(item, ReflectionPaperFinalization)
            and item.authorship_confirmation_id
            == confirmation.authorship_confirmation_id
        )
        if len(finalizations) > 1:
            return _status(
                requirement,
                status="attention_required",
                issuance=issuance,
                returned_page_count=returned_page_count,
                occurrence_count=occurrence_count,
                rescan_choice_required=rescan_choice_required,
                confirmation=confirmation,
                explanation="Conflicting paper finalizations require review.",
            )
        if len(finalizations) == 1:
            finalization = finalizations[0]
            reflections = tuple(
                item
                for item in records
                if isinstance(item, PortfolioReflection)
                and item.reflection_id == finalization.reflection_id
                and item.reflection_revision
                == finalization.reflection_revision
            )
            if len(reflections) != 1:
                return _status(
                    requirement,
                    status="attention_required",
                    issuance=issuance,
                    returned_page_count=returned_page_count,
                    occurrence_count=occurrence_count,
                    rescan_choice_required=rescan_choice_required,
                    confirmation=confirmation,
                    finalization=finalization,
                    explanation=(
                        "Paper finalization does not resolve to one exact "
                        "canonical Portfolio Reflection."
                    ),
                )
            reflection = reflections[0]
            return _status(
                requirement,
                status="recorded",
                issuance=issuance,
                returned_page_count=returned_page_count,
                occurrence_count=occurrence_count,
                rescan_choice_required=rescan_choice_required,
                confirmation=confirmation,
                finalization=finalization,
                reflection=reflection,
                explanation=(
                    "Reflection recorded with student authorship; original paper "
                    "evidence remains preserved."
                ),
            )
        return _status(
            requirement,
            status="confirmed_needs_recording",
            issuance=issuance,
            returned_page_count=returned_page_count,
            occurrence_count=occurrence_count,
            rescan_choice_required=rescan_choice_required,
            confirmation=confirmation,
            explanation=(
                "Student authorship is confirmed; canonical Reflection "
                "recording still needs completion."
            ),
        )

    if returned_page_count < len(issuance.response_page_ids):
        return _status(
            requirement,
            status="issued_awaiting_return",
            issuance=issuance,
            returned_page_count=returned_page_count,
            occurrence_count=occurrence_count,
            rescan_choice_required=rescan_choice_required,
            explanation=(
                "Prompt issued; waiting for all required response pages to return."
            ),
        )

    return _status(
        requirement,
        status="returned_needs_review",
        issuance=issuance,
        returned_page_count=returned_page_count,
        occurrence_count=occurrence_count,
        rescan_choice_required=rescan_choice_required,
        explanation=(
            "All required response pages have returned; teacher authorship "
            "review is required before a canonical Reflection can be recorded."
        ),
    )


def _status(
    requirement: PortfolioProfileRequirement,
    *,
    status: str,
    explanation: str,
    issuance: ReflectionPromptIssuance | None = None,
    returned_page_count: int = 0,
    occurrence_count: int = 0,
    rescan_choice_required: bool = False,
    confirmation: ReflectionAuthorshipConfirmation | None = None,
    reflection: PortfolioReflection | None = None,
    finalization: ReflectionPaperFinalization | None = None,
) -> PaperReflectionRequirementStatus:
    return PaperReflectionRequirementStatus(
        requirement_id=requirement.requirement_id,
        title=requirement.title,
        statement=requirement.statement,
        obligation=requirement.obligation,
        status=status,
        issuance_id=None if issuance is None else issuance.issuance_id,
        prompt_snapshot=None if issuance is None else issuance.prompt_snapshot,
        target_count=(
            0 if issuance is None else len(issuance.target_references)
        ),
        issued_page_count=(
            0 if issuance is None else len(issuance.response_page_ids)
        ),
        returned_page_count=returned_page_count,
        returned_occurrence_count=occurrence_count,
        rescan_choice_required=rescan_choice_required,
        authorship_confirmation_id=(
            None
            if confirmation is None
            else confirmation.authorship_confirmation_id
        ),
        reflection_id=None if reflection is None else reflection.reflection_id,
        reflection_revision=(
            None if reflection is None else reflection.reflection_revision
        ),
        paper_finalization_id=(
            None
            if finalization is None
            else finalization.paper_finalization_id
        ),
        explanation=explanation,
    )


__all__ = [
    "PAPER_REFLECTION_STATUSES",
    "PAPER_REFLECTION_WORKFLOW_CONTRACT_VERSION",
    "PaperReflectionRequirementStatus",
    "PaperReflectionWorkflowError",
    "PaperReflectionWorkflowView",
    "build_paper_reflection_workflow_view",
]
