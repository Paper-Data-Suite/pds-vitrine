"""Guarded application services for explicit Vitrine working-Portfolio curation."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Protocol

from pds_core.publication_storage import (
    PublicationStorageError,
    list_publication_record_set,
)
from pds_core.registry_services import (
    RegistryServiceError,
    get_canonical_publication_record,
    get_canonical_publication_withdrawal,
)

from vitrine.curation_state import (
    CurationState,
    collect_curation_state_issues,
    project_curation_state,
)
from vitrine.models import (
    ActorAttribution,
    CurationAnnotation,
    CurationRationale,
    CurationReviewDecision,
    CurationRevisionRef,
    CurationTargetRef,
    PlacementLifecycleEvent,
    PlacementPresentation,
    Portfolio,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioProfileBinding,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioReflection,
    PortfolioSelection,
    PortfolioSubjectClassLink,
    ProfileSectionDefinition,
    SectionArrangementPointerRevision,
    SectionArrangementRevision,
    SelectionDecision,
    SelectionLifecycleEvent,
    SelectionProposal,
    VitrineRecord,
    WorkingPortfolioCompositionInventory,
    WorkingPortfolioCompositionPointerRevision,
    WorkingPortfolioCompositionRevision,
)
from vitrine.models.common import (
    identifier_tuple,
    lower_key_tuple,
    require_aware_datetime,
    require_bool,
    require_controlled_key,
    require_enum,
    require_identifier,
    require_optional_text,
    require_positive_int,
    require_text,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.profile_state import collect_profile_state_issues, project_profile_state
from vitrine.storage import (
    VitrineStorageConflictError,
    VitrineStorageError,
    VitrineStorageNotFoundError,
    _commit_prevalidated_curation_batch,
    load_current_records_with_state,
)

Clock = Callable[[], datetime]
IdFactory = Callable[[str], str]

CURATION_OPERATIONS: Final[frozenset[str]] = frozenset(
    {
        "propose_selection",
        "decide_selection",
        "direct_select",
        "withdraw_selection",
        "replace_selection",
        "invalidate_selection",
        "place_selection",
        "replace_placement",
        "arrange_section",
        "annotate",
        "reflect",
        "review_curation",
        "compose_portfolio",
    }
)
_AUTHORITY_OUTCOMES: Final[frozenset[str]] = frozenset(
    {"allowed", "denied", "unresolved"}
)
_RESULT_DISPOSITIONS: Final[frozenset[str]] = frozenset({"created", "existing"})

CURATION_WORKFLOW_CODES: Final[frozenset[str]] = frozenset(
    {
        "curation.invalid_request",
        "curation.context_not_found",
        "curation.profile_binding_missing",
        "curation.profile_binding_conflict",
        "curation.profile_mismatch",
        "curation.authority_denied",
        "curation.authority_unresolved",
        "curation.candidate_not_found",
        "curation.candidate_context_mismatch",
        "curation.candidate_not_selectable",
        "curation.candidate_condition_unresolved",
        "curation.candidate_source_withdrawn",
        "curation.candidate_source_historical",
        "curation.candidate_source_unresolved",
        "curation.proposal_not_found",
        "curation.proposal_already_decided",
        "curation.proposal_context_mismatch",
        "curation.decision_invalid",
        "curation.selection_not_found",
        "curation.selection_duplicate_active",
        "curation.selection_inactive",
        "curation.selection_replacement_cycle",
        "curation.placement_not_found",
        "curation.placement_duplicate_active",
        "curation.placement_inactive",
        "curation.section_not_found",
        "curation.section_prohibited",
        "curation.section_not_candidate_eligible",
        "curation.section_cardinality_exceeded",
        "curation.arrangement_incomplete",
        "curation.arrangement_conflict",
        "curation.annotation_target_invalid",
        "curation.annotation_revision_conflict",
        "curation.reflection_requirement_missing",
        "curation.reflection_target_invalid",
        "curation.reflection_revision_conflict",
        "curation.reflection_author_unresolved",
        "curation.review_requirement_missing",
        "curation.review_target_invalid",
        "curation.review_target_stale",
        "curation.review_waiver_not_permitted",
        "curation.composition_inconsistent",
        "curation.composition_revision_conflict",
        "curation.composition_pointer_conflict",
        "curation.state_conflict",
    }
)


class CurationWorkflowError(RuntimeError):
    """Expected curation workflow failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str, *, stage: str) -> None:
        if code not in CURATION_WORKFLOW_CODES:
            raise ValueError(f"unsupported curation workflow code: {code}")
        self.code = code
        self.stage = stage
        super().__init__(message)


@dataclass(frozen=True, slots=True, kw_only=True)
class CurationAuthorityRequest:
    operation: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision_id: str
    profile_revision_number: int
    actor: ActorAttribution
    candidate_id: str | None = None
    selection_id: str | None = None
    placement_id: str | None = None
    target_references: tuple[CurationTargetRef, ...] = ()
    profile_requirement_ids: tuple[str, ...] = ()
    candidate_condition_state: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "operation",
                require_enum(self.operation, "operation", CURATION_OPERATIONS),
            )
            for name in (
                "portfolio_id",
                "portfolio_subject_id",
                "profile_binding_id",
                "profile_revision_id",
            ):
                object.__setattr__(
                    self, name, require_identifier(getattr(self, name), name)
                )
            object.__setattr__(
                self,
                "profile_revision_number",
                require_positive_int(
                    self.profile_revision_number, "profile_revision_number"
                ),
            )
            if not isinstance(self.actor, ActorAttribution):
                raise VitrineModelValidationError("actor must be ActorAttribution.")
            for name in ("candidate_id", "selection_id", "placement_id"):
                value = getattr(self, name)
                if value is not None:
                    object.__setattr__(self, name, require_identifier(value, name))
            targets = tuple(self.target_references)
            if any(not isinstance(item, CurationTargetRef) for item in targets):
                raise VitrineModelValidationError(
                    "target_references must contain CurationTargetRef values."
                )
            object.__setattr__(self, "target_references", targets)
            object.__setattr__(
                self,
                "profile_requirement_ids",
                identifier_tuple(
                    self.profile_requirement_ids, "profile_requirement_ids"
                ),
            )
            if self.candidate_condition_state is not None:
                object.__setattr__(
                    self,
                    "candidate_condition_state",
                    require_controlled_key(
                        self.candidate_condition_state,
                        "candidate_condition_state",
                    ),
                )
        except VitrineModelValidationError as error:
            raise CurationWorkflowError(
                "curation.invalid_request",
                "Curation authority request is invalid.",
                stage="authority_request",
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class CurationAuthorityDecision:
    outcome: str
    authority_reference: str | None = None
    reason_codes: tuple[str, ...] = ()
    acknowledged_condition_codes: tuple[str, ...] = ()
    waiver_permitted: bool = False

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "outcome",
                require_enum(self.outcome, "outcome", _AUTHORITY_OUTCOMES),
            )
            object.__setattr__(
                self,
                "authority_reference",
                require_optional_text(
                    self.authority_reference,
                    "authority_reference",
                    maximum=500,
                ),
            )
            object.__setattr__(
                self,
                "reason_codes",
                lower_key_tuple(self.reason_codes, "reason_codes"),
            )
            object.__setattr__(
                self,
                "acknowledged_condition_codes",
                lower_key_tuple(
                    self.acknowledged_condition_codes,
                    "acknowledged_condition_codes",
                ),
            )
            object.__setattr__(
                self,
                "waiver_permitted",
                require_bool(self.waiver_permitted, "waiver_permitted"),
            )
        except VitrineModelValidationError as error:
            raise CurationWorkflowError(
                "curation.invalid_request",
                "Curation authority decision is invalid.",
                stage="authority",
            ) from error
        if self.outcome == "allowed" and self.authority_reference is None:
            raise CurationWorkflowError(
                "curation.invalid_request",
                "Allowed curation authority requires authority_reference.",
                stage="authority",
            )
        if self.outcome != "allowed" and self.waiver_permitted:
            raise CurationWorkflowError(
                "curation.invalid_request",
                "Only an allowed authority decision may permit waiver.",
                stage="authority",
            )


class CurationAuthorityGate(Protocol):
    def authorize(self, request: CurationAuthorityRequest) -> CurationAuthorityDecision: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class CurationMutationResult:
    state_revision: int
    records: tuple[VitrineRecord, ...]
    disposition: str

    def __post_init__(self) -> None:
        require_positive_int(self.state_revision, "state_revision")
        object.__setattr__(self, "records", tuple(self.records))
        if self.disposition not in _RESULT_DISPOSITIONS:
            raise ValueError("unsupported curation mutation disposition.")


@dataclass(frozen=True, slots=True)
class _Context:
    records: tuple[VitrineRecord, ...]
    state_revision: int
    portfolio: Portfolio
    binding: PortfolioProfileBinding
    profile: PortfolioProfileRevision
    requirements: tuple[PortfolioProfileRequirement, ...]
    curation: CurationState


def _clock() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _now(clock: Clock) -> datetime:
    try:
        return require_aware_datetime(clock(), "clock").astimezone(timezone.utc)
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Curation clock must return an aware datetime.",
            stage="clock",
        ) from error


def _load_context(
    workspace_root: str | Path,
    portfolio_id: str,
    expected_state_revision: int,
) -> _Context:
    try:
        portfolio_id = require_identifier(portfolio_id, "portfolio_id")
        expected_state_revision = require_positive_int(
            expected_state_revision, "expected_state_revision"
        )
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Curation request identifiers are invalid.",
            stage="request",
        ) from error
    try:
        current, records = load_current_records_with_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise CurationWorkflowError(
            "curation.context_not_found",
            "Vitrine canonical state is unavailable.",
            stage="context",
        ) from error
    if current.state_revision != expected_state_revision:
        raise CurationWorkflowError(
            "curation.state_conflict",
            "Vitrine state changed before curation began.",
            stage="context",
        )
    profile_state = project_profile_state(records)
    if collect_profile_state_issues(profile_state):
        raise CurationWorkflowError(
            "curation.profile_mismatch",
            "Portfolio Profile state is invalid.",
            stage="context",
        )
    curation = project_curation_state(records)
    if collect_curation_state_issues(curation):
        raise CurationWorkflowError(
            "curation.context_not_found",
            "Canonical curation state is invalid.",
            stage="context",
        )
    portfolio = next(
        (item for item in profile_state.portfolios if item.portfolio_id == portfolio_id),
        None,
    )
    if portfolio is None:
        raise CurationWorkflowError(
            "curation.context_not_found",
            "Portfolio does not exist.",
            stage="context",
        )
    heads = profile_state.active_binding_heads(portfolio_id)
    if not heads:
        raise CurationWorkflowError(
            "curation.profile_binding_missing",
            "Portfolio has no active Profile Binding head.",
            stage="context",
        )
    if len(heads) != 1:
        raise CurationWorkflowError(
            "curation.profile_binding_conflict",
            "Portfolio has conflicting Profile Binding heads.",
            stage="context",
        )
    binding = heads[0]
    profile = profile_state.revision(binding.profile_revision)
    if profile is None or profile.purpose_kind not in {"improvement", "showcase"}:
        raise CurationWorkflowError(
            "curation.profile_mismatch",
            "Exact bound Profile is unavailable for this curation slice.",
            stage="context",
        )
    return _Context(
        records=records,
        state_revision=current.state_revision,
        portfolio=portfolio,
        binding=binding,
        profile=profile,
        requirements=profile_state.requirements_for(binding.profile_revision),
        curation=curation,
    )


def _authority(
    gate: CurationAuthorityGate,
    context: _Context,
    actor: ActorAttribution,
    operation: str,
    *,
    candidate_id: str | None = None,
    selection_id: str | None = None,
    placement_id: str | None = None,
    targets: tuple[CurationTargetRef, ...] = (),
    requirement_ids: tuple[str, ...] = (),
    candidate_condition_state: str | None = None,
) -> CurationAuthorityDecision:
    if not isinstance(actor, ActorAttribution):
        raise CurationWorkflowError(
            "curation.invalid_request",
            "actor must be ActorAttribution.",
            stage="authority_request",
        )
    request = CurationAuthorityRequest(
        operation=operation,
        portfolio_id=context.portfolio.portfolio_id,
        portfolio_subject_id=context.portfolio.portfolio_subject_id,
        profile_binding_id=context.binding.profile_binding_id,
        profile_revision_id=context.profile.portfolio_profile_id,
        profile_revision_number=context.profile.profile_revision,
        actor=actor,
        candidate_id=candidate_id,
        selection_id=selection_id,
        placement_id=placement_id,
        target_references=targets,
        profile_requirement_ids=requirement_ids,
        candidate_condition_state=candidate_condition_state,
    )
    decision = gate.authorize(request)
    if not isinstance(decision, CurationAuthorityDecision):
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Curation authority gate returned an invalid decision.",
            stage="authority",
        )
    if decision.outcome == "denied":
        raise CurationWorkflowError(
            "curation.authority_denied",
            "Curation authority was denied.",
            stage="authority",
        )
    if decision.outcome == "unresolved":
        raise CurationWorkflowError(
            "curation.authority_unresolved",
            "Curation authority could not be established.",
            stage="authority",
        )
    return decision


def _candidate(context: _Context, candidate_id: str) -> PortfolioCandidate:
    try:
        identifier = require_identifier(candidate_id, "candidate_id")
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.invalid_request", "candidate_id is invalid.", stage="candidate"
        ) from error
    candidate = next(
        (item for item in context.curation.candidates if item.candidate_id == identifier),
        None,
    )
    if candidate is None:
        raise CurationWorkflowError(
            "curation.candidate_not_found",
            "Candidate does not exist.",
            stage="candidate",
        )
    expected = (
        context.portfolio.portfolio_id,
        context.portfolio.portfolio_subject_id,
        context.binding.profile_binding_id,
        context.binding.profile_revision,
    )
    actual = (
        candidate.portfolio_id,
        candidate.portfolio_subject_id,
        candidate.profile_binding_id,
        candidate.profile_revision,
    )
    if actual != expected:
        raise CurationWorkflowError(
            "curation.candidate_context_mismatch",
            "Candidate belongs to another Portfolio/Profile context.",
            stage="candidate",
        )
    return candidate


def _selection(context: _Context, selection_id: str, *, active: bool = False) -> PortfolioSelection:
    try:
        identifier = require_identifier(selection_id, "selection_id")
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.invalid_request", "selection_id is invalid.", stage="selection"
        ) from error
    selection = next(
        (item for item in context.curation.selections if item.selection_id == identifier),
        None,
    )
    if selection is None:
        raise CurationWorkflowError(
            "curation.selection_not_found", "Selection does not exist.", stage="selection"
        )
    if (
        selection.portfolio_id != context.portfolio.portfolio_id
        or selection.profile_binding_id != context.binding.profile_binding_id
    ):
        raise CurationWorkflowError(
            "curation.profile_mismatch",
            "Selection belongs to another Portfolio/Profile context.",
            stage="selection",
        )
    if active and context.curation.selection_status(selection.selection_id) != "activated":
        raise CurationWorkflowError(
            "curation.selection_inactive", "Selection is not active.", stage="selection"
        )
    return selection


def _placement(context: _Context, placement_id: str, *, active: bool = False) -> PortfolioPlacement:
    try:
        identifier = require_identifier(placement_id, "placement_id")
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.invalid_request", "placement_id is invalid.", stage="placement"
        ) from error
    placement = next(
        (item for item in context.curation.placements if item.placement_id == identifier),
        None,
    )
    if placement is None:
        raise CurationWorkflowError(
            "curation.placement_not_found", "Placement does not exist.", stage="placement"
        )
    if (
        placement.portfolio_id != context.portfolio.portfolio_id
        or placement.profile_binding_id != context.binding.profile_binding_id
    ):
        raise CurationWorkflowError(
            "curation.profile_mismatch",
            "Placement belongs to another Portfolio/Profile context.",
            stage="placement",
        )
    if active and context.curation.placement_status(placement.placement_id) != "activated":
        raise CurationWorkflowError(
            "curation.placement_inactive", "Placement is not active.", stage="placement"
        )
    return placement


def _section(context: _Context, section_id: str) -> ProfileSectionDefinition:
    try:
        identifier = require_identifier(section_id, "section_id")
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.invalid_request", "section_id is invalid.", stage="section"
        ) from error
    section = next(
        (item for item in context.profile.sections if item.section_id == identifier), None
    )
    if section is None:
        raise CurationWorkflowError(
            "curation.section_not_found", "Profile section does not exist.", stage="section"
        )
    if section.obligation == "prohibited":
        raise CurationWorkflowError(
            "curation.section_prohibited", "Profile section is prohibited.", stage="section"
        )
    return section


def _current_source_state(workspace_root: str | Path, candidate: PortfolioCandidate) -> str:
    reference = candidate.source_endpoint.core_publication
    try:
        publication = get_canonical_publication_record(
            workspace_root, reference.publication_id
        )
        series = list_publication_record_set(
            workspace_root,
            publication.work,
            publication.publication_kind,
            publication.record_set_id,
        )
        superseded = {
            item.supersedes_publication_id
            for item in series
            if item.supersedes_publication_id is not None
        }
        heads = tuple(item for item in series if item.publication_id not in superseded)
        if len(heads) != 1:
            return "unresolved"
        withdrawal = get_canonical_publication_withdrawal(
            workspace_root, publication.publication_id
        )
    except (RegistryServiceError, PublicationStorageError, OSError):
        return "unresolved"
    if withdrawal is not None:
        return "withdrawn"
    if heads[0].publication_id != publication.publication_id:
        return "historical"
    return "current"


def _require_current_source(workspace_root: str | Path, candidate: PortfolioCandidate) -> None:
    state = _current_source_state(workspace_root, candidate)
    if state == "withdrawn":
        raise CurationWorkflowError(
            "curation.candidate_source_withdrawn",
            "Candidate source Publication is withdrawn for new curation.",
            stage="source_current_use",
        )
    if state == "historical":
        raise CurationWorkflowError(
            "curation.candidate_source_historical",
            "Candidate source Publication is historical for new curation.",
            stage="source_current_use",
        )
    if state != "current":
        raise CurationWorkflowError(
            "curation.candidate_source_unresolved",
            "Candidate source Publication current-use state is unresolved.",
            stage="source_current_use",
        )


def _condition_acknowledged(
    candidate: PortfolioCandidate, decision: CurationAuthorityDecision
) -> None:
    if candidate.condition_state == "ready_for_consideration":
        return
    if candidate.condition_state not in decision.acknowledged_condition_codes:
        raise CurationWorkflowError(
            "curation.candidate_condition_unresolved",
            "Conditional Candidate requires an explicit acknowledged condition.",
            stage="candidate_condition",
        )


def _active_selection_for_candidate(
    context: _Context, candidate_id: str
) -> PortfolioSelection | None:
    matches = tuple(
        item
        for item in context.curation.active_selections(
            portfolio_id=context.portfolio.portfolio_id,
            profile_binding_id=context.binding.profile_binding_id,
        )
        if item.candidate_id == candidate_id
    )
    if len(matches) > 1:
        raise CurationWorkflowError(
            "curation.selection_duplicate_active",
            "Candidate has conflicting active Selections.",
            stage="selection",
        )
    return matches[0] if matches else None


def _require_profile_requirements(context: _Context, requirement_ids: tuple[str, ...]) -> None:
    known = {item.requirement_id for item in context.requirements}
    if not set(requirement_ids).issubset(known):
        raise CurationWorkflowError(
            "curation.profile_mismatch",
            "Curation request references a missing exact Profile requirement.",
            stage="profile_requirement",
        )


def _rationale(
    *,
    context: _Context,
    target_kind: str,
    target_id: str,
    action_kind: str,
    author: ActorAttribution,
    text: str | None,
    requirement_ids: tuple[str, ...],
    now: datetime,
    id_factory: IdFactory,
) -> CurationRationale | None:
    if text is None:
        return None
    return CurationRationale(
        rationale_id=id_factory("rationale"),
        portfolio_id=context.portfolio.portfolio_id,
        profile_binding_id=context.binding.profile_binding_id,
        target_kind=target_kind,
        target_id=target_id,
        action_kind=action_kind,
        author=author,
        created_at=now,
        text=text,
        profile_requirement_ids=requirement_ids,
    )


def _validated_commit(
    workspace_root: str | Path,
    context: _Context,
    records: tuple[VitrineRecord, ...],
) -> CurationMutationResult:
    projected = project_curation_state((*context.records, *records))
    issues = collect_curation_state_issues(projected)
    if issues:
        raise CurationWorkflowError(
            "curation.composition_inconsistent",
            f"Proposed curation transition is invalid ({issues[0].code}).",
            stage="validation",
        )
    try:
        result = _commit_prevalidated_curation_batch(
            workspace_root,
            records,
            expected_state_revision=context.state_revision,
        )
    except VitrineStorageConflictError as error:
        raise CurationWorkflowError(
            "curation.state_conflict",
            "Vitrine state changed before curation commit.",
            stage="commit",
        ) from error
    except VitrineStorageError as error:
        raise CurationWorkflowError(
            "curation.composition_inconsistent",
            "Curation records could not be persisted safely.",
            stage="commit",
        ) from error
    return CurationMutationResult(
        state_revision=result.state_revision,
        records=records,
        disposition="created",
    )


def propose_candidate_selection(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    candidate_id: str,
    proposer: ActorAttribution,
    proposal_origin: str,
    proposed_section_ids: tuple[str, ...],
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    intended_profile_requirement_ids: tuple[str, ...] = (),
    rationale_text: str | None = None,
    predecessor_proposal_id: str | None = None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    candidate = _candidate(context, candidate_id)
    try:
        sections = identifier_tuple(
            proposed_section_ids, "proposed_section_ids", nonempty=True
        )
        requirement_ids = identifier_tuple(
            intended_profile_requirement_ids,
            "intended_profile_requirement_ids",
        )
        origin = require_enum(
            proposal_origin,
            "proposal_origin",
            frozenset(
                {
                    "student",
                    "teacher",
                    "authorized_reviewer",
                    "direct_selection",
                    "imported_prior_curation",
                    "system_suggestion",
                }
            ),
        )
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Selection Proposal fields are invalid.",
            stage="proposal",
        ) from error
    for section_id in sections:
        _section(context, section_id)
        if section_id not in candidate.eligible_section_ids:
            raise CurationWorkflowError(
                "curation.section_not_candidate_eligible",
                "Candidate is not eligible for a proposed section.",
                stage="proposal",
            )
    _require_profile_requirements(context, requirement_ids)
    _authority(
        authority_gate,
        context,
        proposer,
        "propose_selection",
        candidate_id=candidate.candidate_id,
        requirement_ids=requirement_ids,
        candidate_condition_state=candidate.condition_state,
    )
    now = _now(clock)
    proposal_id = id_factory("selection_proposal")
    rationale = _rationale(
        context=context,
        target_kind="selection_proposal",
        target_id=proposal_id,
        action_kind="propose_selection",
        author=proposer,
        text=rationale_text,
        requirement_ids=requirement_ids,
        now=now,
        id_factory=id_factory,
    )
    proposal = SelectionProposal(
        selection_proposal_id=proposal_id,
        portfolio_id=context.portfolio.portfolio_id,
        portfolio_subject_id=context.portfolio.portfolio_subject_id,
        profile_binding_id=context.binding.profile_binding_id,
        profile_revision=context.binding.profile_revision,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=candidate.candidate_evaluation_id,
        proposer=proposer,
        proposal_origin=origin,
        proposed_section_ids=sections,
        intended_profile_requirement_ids=requirement_ids,
        candidate_condition_state_snapshot=candidate.condition_state,
        proposed_at=now,
        rationale_id=None if rationale is None else rationale.rationale_id,
        predecessor_proposal_id=predecessor_proposal_id,
    )
    records: tuple[VitrineRecord, ...] = (
        (proposal,) if rationale is None else (rationale, proposal)
    )
    return _validated_commit(workspace_root, context, records)


def _accepted_selection_records(
    workspace_root: str | Path,
    context: _Context,
    proposal: SelectionProposal,
    actor: ActorAttribution,
    authority: CurationAuthorityDecision,
    *,
    rationale_text: str | None,
    now: datetime,
    id_factory: IdFactory,
    operation: str,
    existing_rationale_id: str | None = None,
) -> tuple[VitrineRecord, ...]:
    candidate = _candidate(context, proposal.candidate_id)
    if candidate.candidate_evaluation_id != proposal.candidate_evaluation_id:
        raise CurationWorkflowError(
            "curation.proposal_context_mismatch",
            "Proposal Candidate Evaluation no longer matches the exact Candidate.",
            stage="decision",
        )
    _require_current_source(workspace_root, candidate)
    _condition_acknowledged(candidate, authority)
    if _active_selection_for_candidate(context, candidate.candidate_id) is not None:
        raise CurationWorkflowError(
            "curation.selection_duplicate_active",
            "Candidate already has an active Selection in this Binding.",
            stage="selection",
        )
    selection_id = id_factory("selection")
    decision_id = id_factory("selection_decision")
    rationale = (
        None
        if existing_rationale_id is not None
        else _rationale(
            context=context,
            target_kind="selection_proposal",
            target_id=proposal.selection_proposal_id,
            action_kind=operation,
            author=actor,
            text=rationale_text,
            requirement_ids=proposal.intended_profile_requirement_ids,
            now=now,
            id_factory=id_factory,
        )
    )
    decision_rationale_id = (
        existing_rationale_id
        if existing_rationale_id is not None
        else (None if rationale is None else rationale.rationale_id)
    )
    selection = PortfolioSelection(
        selection_id=selection_id,
        portfolio_id=proposal.portfolio_id,
        portfolio_subject_id=proposal.portfolio_subject_id,
        profile_binding_id=proposal.profile_binding_id,
        profile_revision=proposal.profile_revision,
        candidate_id=proposal.candidate_id,
        candidate_evaluation_id=proposal.candidate_evaluation_id,
        selected_at=now,
        selected_by=actor,
        selection_reason=rationale_text,
    )
    decision = SelectionDecision(
        selection_decision_id=decision_id,
        selection_proposal_id=proposal.selection_proposal_id,
        decision="accepted",
        decided_at=now,
        decided_by=actor,
        authority_reference=authority.authority_reference or "",
        matched_profile_requirement_ids=proposal.intended_profile_requirement_ids,
        condition_codes=authority.acknowledged_condition_codes,
        rationale_id=decision_rationale_id,
        resulting_selection_id=selection_id,
    )
    event = SelectionLifecycleEvent(
        selection_lifecycle_event_id=id_factory("selection_event"),
        selection_id=selection_id,
        event_kind="activated",
        event_at=now,
        actor=actor,
        authority_reference=authority.authority_reference or "",
        reason="Activate accepted Portfolio Selection.",
        basis_selection_decision_id=decision_id,
        unresolved_condition_codes=(
            ()
            if candidate.condition_state == "ready_for_consideration"
            else (candidate.condition_state,)
        ),
    )
    return (
        *((rationale,) if rationale is not None else ()),
        decision,
        selection,
        event,
    )


def decide_selection_proposal(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    selection_proposal_id: str,
    decision: str,
    decided_by: ActorAttribution,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    rationale_text: str | None = None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    proposal = next(
        (
            item
            for item in context.curation.proposals
            if item.selection_proposal_id == selection_proposal_id
        ),
        None,
    )
    if proposal is None:
        raise CurationWorkflowError(
            "curation.proposal_not_found", "Selection Proposal does not exist.", stage="decision"
        )
    if any(
        item.selection_proposal_id == proposal.selection_proposal_id
        for item in context.curation.decisions
    ):
        raise CurationWorkflowError(
            "curation.proposal_already_decided",
            "Selection Proposal already has an immutable Decision.",
            stage="decision",
        )
    try:
        decision_kind = require_enum(
            decision,
            "decision",
            frozenset(
                {"accepted", "rejected", "changes_requested", "withdrawn", "expired"}
            ),
        )
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.decision_invalid", "Selection decision is invalid.", stage="decision"
        ) from error
    candidate = _candidate(context, proposal.candidate_id)
    authority = _authority(
        authority_gate,
        context,
        decided_by,
        "decide_selection",
        candidate_id=candidate.candidate_id,
        targets=(
            CurationTargetRef(
                target_kind="selection_proposal",
                target_id=proposal.selection_proposal_id,
            ),
        ),
        requirement_ids=proposal.intended_profile_requirement_ids,
        candidate_condition_state=candidate.condition_state,
    )
    now = _now(clock)
    if decision_kind == "accepted":
        records = _accepted_selection_records(
            workspace_root,
            context,
            proposal,
            decided_by,
            authority,
            rationale_text=rationale_text,
            now=now,
            id_factory=id_factory,
            operation="decide_selection",
        )
        return _validated_commit(workspace_root, context, records)
    rationale = _rationale(
        context=context,
        target_kind="selection_proposal",
        target_id=proposal.selection_proposal_id,
        action_kind="decide_selection",
        author=decided_by,
        text=rationale_text,
        requirement_ids=proposal.intended_profile_requirement_ids,
        now=now,
        id_factory=id_factory,
    )
    record = SelectionDecision(
        selection_decision_id=id_factory("selection_decision"),
        selection_proposal_id=proposal.selection_proposal_id,
        decision=decision_kind,
        decided_at=now,
        decided_by=decided_by,
        authority_reference=authority.authority_reference or "",
        matched_profile_requirement_ids=proposal.intended_profile_requirement_ids,
        condition_codes=authority.acknowledged_condition_codes,
        rationale_id=None if rationale is None else rationale.rationale_id,
    )
    records = ((record,) if rationale is None else (rationale, record))
    return _validated_commit(workspace_root, context, records)


def select_candidate_directly(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    candidate_id: str,
    selected_by: ActorAttribution,
    proposed_section_ids: tuple[str, ...],
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    intended_profile_requirement_ids: tuple[str, ...] = (),
    rationale_text: str | None = None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    candidate = _candidate(context, candidate_id)
    try:
        sections = identifier_tuple(
            proposed_section_ids, "proposed_section_ids", nonempty=True
        )
        requirement_ids = identifier_tuple(
            intended_profile_requirement_ids,
            "intended_profile_requirement_ids",
        )
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Direct Selection fields are invalid.",
            stage="direct_selection",
        ) from error
    for section_id in sections:
        _section(context, section_id)
        if section_id not in candidate.eligible_section_ids:
            raise CurationWorkflowError(
                "curation.section_not_candidate_eligible",
                "Candidate is not eligible for a proposed section.",
                stage="direct_selection",
            )
    _require_profile_requirements(context, requirement_ids)
    authority = _authority(
        authority_gate,
        context,
        selected_by,
        "direct_select",
        candidate_id=candidate.candidate_id,
        requirement_ids=requirement_ids,
        candidate_condition_state=candidate.condition_state,
    )
    _require_current_source(workspace_root, candidate)
    _condition_acknowledged(candidate, authority)
    if _active_selection_for_candidate(context, candidate.candidate_id) is not None:
        raise CurationWorkflowError(
            "curation.selection_duplicate_active",
            "Candidate already has an active Selection.",
            stage="direct_selection",
        )
    now = _now(clock)
    proposal_id = id_factory("selection_proposal")
    proposal_rationale = _rationale(
        context=context,
        target_kind="selection_proposal",
        target_id=proposal_id,
        action_kind="direct_select",
        author=selected_by,
        text=rationale_text,
        requirement_ids=requirement_ids,
        now=now,
        id_factory=id_factory,
    )
    proposal = SelectionProposal(
        selection_proposal_id=proposal_id,
        portfolio_id=context.portfolio.portfolio_id,
        portfolio_subject_id=context.portfolio.portfolio_subject_id,
        profile_binding_id=context.binding.profile_binding_id,
        profile_revision=context.binding.profile_revision,
        candidate_id=candidate.candidate_id,
        candidate_evaluation_id=candidate.candidate_evaluation_id,
        proposer=selected_by,
        proposal_origin="direct_selection",
        proposed_section_ids=sections,
        intended_profile_requirement_ids=requirement_ids,
        candidate_condition_state_snapshot=candidate.condition_state,
        proposed_at=now,
        rationale_id=None if proposal_rationale is None else proposal_rationale.rationale_id,
    )
    accepted = _accepted_selection_records(
        workspace_root,
        context,
        proposal,
        selected_by,
        authority,
        rationale_text=rationale_text,
        now=now,
        id_factory=id_factory,
        operation="direct_select",
        existing_rationale_id=(
            None if proposal_rationale is None else proposal_rationale.rationale_id
        ),
    )
    records: tuple[VitrineRecord, ...] = (
        *((proposal_rationale,) if proposal_rationale is not None else ()),
        proposal,
        *accepted,
    )
    return _validated_commit(workspace_root, context, records)


def _current_selection_event(context: _Context, selection_id: str) -> SelectionLifecycleEvent:
    heads = context.curation.selection_heads(selection_id)
    if len(heads) != 1 or heads[0].event_kind != "activated":
        raise CurationWorkflowError(
            "curation.selection_inactive",
            "Selection does not have one active lifecycle head.",
            stage="selection_lifecycle",
        )
    return heads[0]


def _current_placement_event(context: _Context, placement_id: str) -> PlacementLifecycleEvent:
    heads = context.curation.placement_heads(placement_id)
    if len(heads) != 1 or heads[0].event_kind != "activated":
        raise CurationWorkflowError(
            "curation.placement_inactive",
            "Placement does not have one active lifecycle head.",
            stage="placement_lifecycle",
        )
    return heads[0]


def _pointer_for_section(
    context: _Context, section_id: str
) -> SectionArrangementPointerRevision | None:
    heads = context.curation.arrangement_pointer_heads(
        context.portfolio.portfolio_id,
        context.binding.profile_binding_id,
        section_id,
    )
    if len(heads) > 1:
        raise CurationWorkflowError(
            "curation.arrangement_conflict",
            "Section Arrangement pointer is conflicted.",
            stage="arrangement",
        )
    return heads[0] if heads else None


def _arrangement_transition(
    context: _Context,
    *,
    section_id: str,
    desired_placement_ids: tuple[str, ...],
    expected_pointer_revision: int | None,
    actor: ActorAttribution,
    authority_reference: str,
    now: datetime,
    id_factory: IdFactory,
) -> tuple[SectionArrangementRevision, SectionArrangementPointerRevision]:
    _section(context, section_id)
    pointer = _pointer_for_section(context, section_id)
    if pointer is None:
        if expected_pointer_revision is not None:
            raise CurationWorkflowError(
                "curation.arrangement_conflict",
                "Expected Arrangement pointer does not exist.",
                stage="arrangement",
            )
        current_arrangement = None
        pointer_id = id_factory("arrangement_pointer")
        pointer_revision = 1
        predecessor_pointer = None
        arrangement_revision = 1
        predecessor_arrangement_id = None
    else:
        if expected_pointer_revision != pointer.pointer_revision:
            raise CurationWorkflowError(
                "curation.arrangement_conflict",
                "Arrangement pointer changed since caller observation.",
                stage="arrangement",
            )
        current_arrangement = context.curation.current_arrangement(
            context.portfolio.portfolio_id,
            context.binding.profile_binding_id,
            section_id,
        )
        if current_arrangement is None:
            raise CurationWorkflowError(
                "curation.arrangement_conflict",
                "Current Arrangement pointer target is invalid.",
                stage="arrangement",
            )
        pointer_id = pointer.arrangement_pointer_id
        pointer_revision = pointer.pointer_revision + 1
        predecessor_pointer = pointer.pointer_revision
        arrangement_revision = current_arrangement.arrangement_revision + 1
        predecessor_arrangement_id = current_arrangement.arrangement_id
    arrangement = SectionArrangementRevision(
        arrangement_id=id_factory("arrangement"),
        portfolio_id=context.portfolio.portfolio_id,
        profile_binding_id=context.binding.profile_binding_id,
        section_id=section_id,
        arrangement_revision=arrangement_revision,
        placement_ids=desired_placement_ids,
        created_at=now,
        created_by=actor,
        predecessor_arrangement_id=predecessor_arrangement_id,
    )
    next_pointer = SectionArrangementPointerRevision(
        arrangement_pointer_id=pointer_id,
        pointer_revision=pointer_revision,
        portfolio_id=context.portfolio.portfolio_id,
        profile_binding_id=context.binding.profile_binding_id,
        section_id=section_id,
        arrangement_id=arrangement.arrangement_id,
        pointed_at=now,
        pointed_by=actor,
        authority_reference=authority_reference,
        predecessor_pointer_revision=predecessor_pointer,
    )
    return arrangement, next_pointer


def _check_section_capacity(
    context: _Context,
    section_id: str,
    *,
    additional: int,
    excluding_placement_ids: tuple[str, ...] = (),
) -> None:
    section = _section(context, section_id)
    active = tuple(
        item
        for item in context.curation.active_placements(
            portfolio_id=context.portfolio.portfolio_id,
            profile_binding_id=context.binding.profile_binding_id,
            section_id=section_id,
        )
        if item.placement_id not in excluding_placement_ids
    )
    if section.maximum_placements is not None and len(active) + additional > section.maximum_placements:
        raise CurationWorkflowError(
            "curation.section_cardinality_exceeded",
            "Profile section maximum Placement count would be exceeded.",
            stage="placement",
        )


def place_selection(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    selection_id: str,
    section_id: str,
    placed_by: ActorAttribution,
    expected_state_revision: int,
    expected_arrangement_pointer_revision: int | None,
    authority_gate: CurationAuthorityGate,
    presentation: PlacementPresentation | None = None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    selection = _selection(context, selection_id, active=True)
    candidate = _candidate(context, selection.candidate_id)
    section = _section(context, section_id)
    if section.section_id not in candidate.eligible_section_ids:
        raise CurationWorkflowError(
            "curation.section_not_candidate_eligible",
            "Selection Candidate is not eligible for this section.",
            stage="placement",
        )
    if any(
        item.selection_id == selection.selection_id and item.section_id == section.section_id
        for item in context.curation.active_placements(
            portfolio_id=context.portfolio.portfolio_id,
            profile_binding_id=context.binding.profile_binding_id,
        )
    ):
        raise CurationWorkflowError(
            "curation.placement_duplicate_active",
            "Selection already has an active Placement in this section.",
            stage="placement",
        )
    _check_section_capacity(context, section.section_id, additional=1)
    authority = _authority(
        authority_gate,
        context,
        placed_by,
        "place_selection",
        selection_id=selection.selection_id,
        targets=(CurationTargetRef(target_kind="section", target_id=section.section_id),),
    )
    now = _now(clock)
    placement = PortfolioPlacement(
        placement_id=id_factory("placement"),
        portfolio_id=context.portfolio.portfolio_id,
        profile_binding_id=context.binding.profile_binding_id,
        selection_id=selection.selection_id,
        section_id=section.section_id,
        presentation=presentation,
        placed_at=now,
        placed_by=placed_by,
    )
    event = PlacementLifecycleEvent(
        placement_lifecycle_event_id=id_factory("placement_event"),
        placement_id=placement.placement_id,
        event_kind="activated",
        event_at=now,
        actor=placed_by,
        authority_reference=authority.authority_reference or "",
        reason="Activate section Placement.",
    )
    current_ids = tuple(
        item.placement_id
        for item in context.curation.active_placements(
            portfolio_id=context.portfolio.portfolio_id,
            profile_binding_id=context.binding.profile_binding_id,
            section_id=section.section_id,
        )
    )
    arrangement, pointer = _arrangement_transition(
        context,
        section_id=section.section_id,
        desired_placement_ids=(*current_ids, placement.placement_id),
        expected_pointer_revision=expected_arrangement_pointer_revision,
        actor=placed_by,
        authority_reference=authority.authority_reference or "",
        now=now,
        id_factory=id_factory,
    )
    return _validated_commit(
        workspace_root,
        context,
        (placement, event, arrangement, pointer),
    )


def reorder_section(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    section_id: str,
    placement_ids: tuple[str, ...],
    arranged_by: ActorAttribution,
    expected_state_revision: int,
    expected_arrangement_pointer_revision: int,
    authority_gate: CurationAuthorityGate,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    _section(context, section_id)
    try:
        desired = identifier_tuple(placement_ids, "placement_ids")
    except VitrineModelValidationError as error:
        raise CurationWorkflowError(
            "curation.invalid_request", "Placement order is invalid.", stage="arrangement"
        ) from error
    active = context.curation.active_placements(
        portfolio_id=context.portfolio.portfolio_id,
        profile_binding_id=context.binding.profile_binding_id,
        section_id=section_id,
    )
    if set(desired) != {item.placement_id for item in active} or len(desired) != len(active):
        raise CurationWorkflowError(
            "curation.arrangement_incomplete",
            "Requested Arrangement must contain exactly all active section Placements.",
            stage="arrangement",
        )
    authority = _authority(
        authority_gate,
        context,
        arranged_by,
        "arrange_section",
        targets=(CurationTargetRef(target_kind="section", target_id=section_id),),
    )
    now = _now(clock)
    arrangement, pointer = _arrangement_transition(
        context,
        section_id=section_id,
        desired_placement_ids=desired,
        expected_pointer_revision=expected_arrangement_pointer_revision,
        actor=arranged_by,
        authority_reference=authority.authority_reference or "",
        now=now,
        id_factory=id_factory,
    )
    return _validated_commit(workspace_root, context, (arrangement, pointer))


def replace_placement(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    placement_id: str,
    replaced_by: ActorAttribution,
    expected_state_revision: int,
    expected_pointer_revisions: Mapping[str, int | None],
    authority_gate: CurationAuthorityGate,
    section_id: str | None = None,
    presentation: PlacementPresentation | None = None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    old = _placement(context, placement_id, active=True)
    selection = _selection(context, old.selection_id, active=True)
    candidate = _candidate(context, selection.candidate_id)
    target_section = old.section_id if section_id is None else section_id
    section = _section(context, target_section)
    if section.section_id not in candidate.eligible_section_ids:
        raise CurationWorkflowError(
            "curation.section_not_candidate_eligible",
            "Replacement Placement section is not Candidate-eligible.",
            stage="placement",
        )
    _check_section_capacity(
        context,
        section.section_id,
        additional=1,
        excluding_placement_ids=(old.placement_id,),
    )
    authority = _authority(
        authority_gate,
        context,
        replaced_by,
        "replace_placement",
        selection_id=selection.selection_id,
        placement_id=old.placement_id,
        targets=(CurationTargetRef(target_kind="section", target_id=section.section_id),),
    )
    now = _now(clock)
    new_placement = PortfolioPlacement(
        placement_id=id_factory("placement"),
        portfolio_id=old.portfolio_id,
        profile_binding_id=old.profile_binding_id,
        selection_id=old.selection_id,
        section_id=section.section_id,
        presentation=old.presentation if presentation is None else presentation,
        placed_at=now,
        placed_by=replaced_by,
    )
    old_event = _current_placement_event(context, old.placement_id)
    retire = PlacementLifecycleEvent(
        placement_lifecycle_event_id=id_factory("placement_event"),
        placement_id=old.placement_id,
        event_kind="replaced",
        event_at=now,
        actor=replaced_by,
        authority_reference=authority.authority_reference or "",
        reason="Replace immutable Placement.",
        predecessor_event_id=old_event.placement_lifecycle_event_id,
        successor_placement_id=new_placement.placement_id,
    )
    activate = PlacementLifecycleEvent(
        placement_lifecycle_event_id=id_factory("placement_event"),
        placement_id=new_placement.placement_id,
        event_kind="activated",
        event_at=now,
        actor=replaced_by,
        authority_reference=authority.authority_reference or "",
        reason="Activate replacement Placement.",
    )
    affected_sections = tuple(sorted({old.section_id, new_placement.section_id}))
    records: list[VitrineRecord] = [new_placement, retire, activate]
    future = [
        item
        for item in context.curation.active_placements(
            portfolio_id=context.portfolio.portfolio_id,
            profile_binding_id=context.binding.profile_binding_id,
        )
        if item.placement_id != old.placement_id
    ]
    future.append(new_placement)
    for affected in affected_sections:
        desired = tuple(
            item.placement_id for item in future if item.section_id == affected
        )
        arrangement, pointer = _arrangement_transition(
            context,
            section_id=affected,
            desired_placement_ids=desired,
            expected_pointer_revision=expected_pointer_revisions.get(affected),
            actor=replaced_by,
            authority_reference=authority.authority_reference or "",
            now=now,
            id_factory=id_factory,
        )
        records.extend((arrangement, pointer))
    return _validated_commit(workspace_root, context, tuple(records))


def _retire_selection(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    selection_id: str,
    actor: ActorAttribution,
    expected_state_revision: int,
    expected_pointer_revisions: Mapping[str, int | None],
    authority_gate: CurationAuthorityGate,
    event_kind: str,
    reason: str,
    clock: Clock,
    id_factory: IdFactory,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    selection = _selection(context, selection_id, active=True)
    operation = "withdraw_selection" if event_kind == "withdrawn" else "invalidate_selection"
    authority = _authority(
        authority_gate,
        context,
        actor,
        operation,
        selection_id=selection.selection_id,
    )
    now = _now(clock)
    old_head = _current_selection_event(context, selection.selection_id)
    active_placements = tuple(
        item
        for item in context.curation.active_placements(
            portfolio_id=context.portfolio.portfolio_id,
            profile_binding_id=context.binding.profile_binding_id,
        )
        if item.selection_id == selection.selection_id
    )
    selection_event = SelectionLifecycleEvent(
        selection_lifecycle_event_id=id_factory("selection_event"),
        selection_id=selection.selection_id,
        event_kind=event_kind,
        event_at=now,
        actor=actor,
        authority_reference=authority.authority_reference or "",
        reason=reason,
        predecessor_event_id=old_head.selection_lifecycle_event_id,
        affected_placement_ids=tuple(item.placement_id for item in active_placements),
    )
    records: list[VitrineRecord] = [selection_event]
    for placement in active_placements:
        placement_head = _current_placement_event(context, placement.placement_id)
        records.append(
            PlacementLifecycleEvent(
                placement_lifecycle_event_id=id_factory("placement_event"),
                placement_id=placement.placement_id,
                event_kind="withdrawn" if event_kind == "withdrawn" else "invalidated",
                event_at=now,
                actor=actor,
                authority_reference=authority.authority_reference or "",
                reason=reason,
                predecessor_event_id=placement_head.placement_lifecycle_event_id,
            )
        )
    remaining = tuple(
        item
        for item in context.curation.active_placements(
            portfolio_id=context.portfolio.portfolio_id,
            profile_binding_id=context.binding.profile_binding_id,
        )
        if item.selection_id != selection.selection_id
    )
    for section_id in sorted({item.section_id for item in active_placements}):
        desired = tuple(item.placement_id for item in remaining if item.section_id == section_id)
        arrangement, pointer = _arrangement_transition(
            context,
            section_id=section_id,
            desired_placement_ids=desired,
            expected_pointer_revision=expected_pointer_revisions.get(section_id),
            actor=actor,
            authority_reference=authority.authority_reference or "",
            now=now,
            id_factory=id_factory,
        )
        records.extend((arrangement, pointer))
    return _validated_commit(workspace_root, context, tuple(records))


def withdraw_selection(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    selection_id: str,
    withdrawn_by: ActorAttribution,
    expected_state_revision: int,
    expected_pointer_revisions: Mapping[str, int | None],
    authority_gate: CurationAuthorityGate,
    reason: str,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    return _retire_selection(
        workspace_root,
        portfolio_id=portfolio_id,
        selection_id=selection_id,
        actor=withdrawn_by,
        expected_state_revision=expected_state_revision,
        expected_pointer_revisions=expected_pointer_revisions,
        authority_gate=authority_gate,
        event_kind="withdrawn",
        reason=reason,
        clock=clock,
        id_factory=id_factory,
    )


def invalidate_selection(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    selection_id: str,
    invalidated_by: ActorAttribution,
    expected_state_revision: int,
    expected_pointer_revisions: Mapping[str, int | None],
    authority_gate: CurationAuthorityGate,
    reason: str,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    return _retire_selection(
        workspace_root,
        portfolio_id=portfolio_id,
        selection_id=selection_id,
        actor=invalidated_by,
        expected_state_revision=expected_state_revision,
        expected_pointer_revisions=expected_pointer_revisions,
        authority_gate=authority_gate,
        event_kind="invalidated",
        reason=reason,
        clock=clock,
        id_factory=id_factory,
    )


def replace_selection(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    selection_id: str,
    successor_candidate_id: str,
    replaced_by: ActorAttribution,
    placement_dispositions: Mapping[str, str | None],
    expected_state_revision: int,
    expected_pointer_revisions: Mapping[str, int | None],
    authority_gate: CurationAuthorityGate,
    reason: str,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    old = _selection(context, selection_id, active=True)
    successor = _candidate(context, successor_candidate_id)
    if successor.candidate_id == old.candidate_id:
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Replacement Candidate must differ from the selected Candidate.",
            stage="replacement",
        )
    if _active_selection_for_candidate(context, successor.candidate_id) is not None:
        raise CurationWorkflowError(
            "curation.selection_duplicate_active",
            "Replacement Candidate already has an active Selection.",
            stage="replacement",
        )
    authority = _authority(
        authority_gate,
        context,
        replaced_by,
        "replace_selection",
        candidate_id=successor.candidate_id,
        selection_id=old.selection_id,
        candidate_condition_state=successor.condition_state,
    )
    _require_current_source(workspace_root, successor)
    _condition_acknowledged(successor, authority)
    active_old_placements = tuple(
        item
        for item in context.curation.active_placements(
            portfolio_id=context.portfolio.portfolio_id,
            profile_binding_id=context.binding.profile_binding_id,
        )
        if item.selection_id == old.selection_id
    )
    if set(placement_dispositions) != {item.placement_id for item in active_old_placements}:
        raise CurationWorkflowError(
            "curation.invalid_request",
            "Replacement requires an explicit disposition for every active Placement.",
            stage="replacement",
        )
    now = _now(clock)
    proposal_id = id_factory("selection_proposal")
    selection_id_new = id_factory("selection")
    decision_id = id_factory("selection_decision")
    rationale = CurationRationale(
        rationale_id=id_factory("rationale"),
        portfolio_id=context.portfolio.portfolio_id,
        profile_binding_id=context.binding.profile_binding_id,
        target_kind="selection",
        target_id=old.selection_id,
        action_kind="replace_selection",
        author=replaced_by,
        created_at=now,
        text=require_text(reason, "reason", maximum=4000),
    )
    proposed_sections = tuple(
        sorted(
            {
                target
                for target in placement_dispositions.values()
                if target is not None
            }
            or set(successor.eligible_section_ids[:1])
        )
    )
    proposal = SelectionProposal(
        selection_proposal_id=proposal_id,
        portfolio_id=context.portfolio.portfolio_id,
        portfolio_subject_id=context.portfolio.portfolio_subject_id,
        profile_binding_id=context.binding.profile_binding_id,
        profile_revision=context.binding.profile_revision,
        candidate_id=successor.candidate_id,
        candidate_evaluation_id=successor.candidate_evaluation_id,
        proposer=replaced_by,
        proposal_origin="direct_selection",
        proposed_section_ids=proposed_sections,
        intended_profile_requirement_ids=(),
        candidate_condition_state_snapshot=successor.condition_state,
        proposed_at=now,
        rationale_id=rationale.rationale_id,
    )
    decision = SelectionDecision(
        selection_decision_id=decision_id,
        selection_proposal_id=proposal_id,
        decision="accepted",
        decided_at=now,
        decided_by=replaced_by,
        authority_reference=authority.authority_reference or "",
        condition_codes=authority.acknowledged_condition_codes,
        rationale_id=rationale.rationale_id,
        resulting_selection_id=selection_id_new,
    )
    new_selection = PortfolioSelection(
        selection_id=selection_id_new,
        portfolio_id=context.portfolio.portfolio_id,
        portfolio_subject_id=context.portfolio.portfolio_subject_id,
        profile_binding_id=context.binding.profile_binding_id,
        profile_revision=context.binding.profile_revision,
        candidate_id=successor.candidate_id,
        candidate_evaluation_id=successor.candidate_evaluation_id,
        selected_at=now,
        selected_by=replaced_by,
        selection_reason=reason,
        predecessor_selection_id=old.selection_id,
    )
    old_head = _current_selection_event(context, old.selection_id)
    old_event = SelectionLifecycleEvent(
        selection_lifecycle_event_id=id_factory("selection_event"),
        selection_id=old.selection_id,
        event_kind="replaced",
        event_at=now,
        actor=replaced_by,
        authority_reference=authority.authority_reference or "",
        reason=reason,
        predecessor_event_id=old_head.selection_lifecycle_event_id,
        successor_selection_ids=(new_selection.selection_id,),
        affected_placement_ids=tuple(item.placement_id for item in active_old_placements),
    )
    new_event = SelectionLifecycleEvent(
        selection_lifecycle_event_id=id_factory("selection_event"),
        selection_id=new_selection.selection_id,
        event_kind="activated",
        event_at=now,
        actor=replaced_by,
        authority_reference=authority.authority_reference or "",
        reason="Activate replacement Selection.",
        basis_selection_decision_id=decision_id,
        unresolved_condition_codes=(
            ()
            if successor.condition_state == "ready_for_consideration"
            else (successor.condition_state,)
        ),
    )
    records: list[VitrineRecord] = [
        rationale,
        proposal,
        decision,
        new_selection,
        old_event,
        new_event,
    ]
    future = [
        item
        for item in context.curation.active_placements(
            portfolio_id=context.portfolio.portfolio_id,
            profile_binding_id=context.binding.profile_binding_id,
        )
        if item.selection_id != old.selection_id
    ]
    affected_sections: set[str] = {item.section_id for item in active_old_placements}
    migrated_target_sections: set[str] = set()
    for old_placement in active_old_placements:
        target_section = placement_dispositions[old_placement.placement_id]
        old_placement_head = _current_placement_event(context, old_placement.placement_id)
        if target_section is None:
            records.append(
                PlacementLifecycleEvent(
                    placement_lifecycle_event_id=id_factory("placement_event"),
                    placement_id=old_placement.placement_id,
                    event_kind="withdrawn",
                    event_at=now,
                    actor=replaced_by,
                    authority_reference=authority.authority_reference or "",
                    reason=reason,
                    predecessor_event_id=old_placement_head.placement_lifecycle_event_id,
                )
            )
            continue
        section = _section(context, target_section)
        affected_sections.add(section.section_id)
        if section.section_id not in successor.eligible_section_ids:
            raise CurationWorkflowError(
                "curation.section_not_candidate_eligible",
                "Replacement Candidate is not eligible for a migrated Placement section.",
                stage="replacement",
            )
        if section.section_id in migrated_target_sections:
            raise CurationWorkflowError(
                "curation.placement_duplicate_active",
                "Replacement would create duplicate active Placements in one section.",
                stage="replacement",
            )
        existing_target_count = sum(
            1 for item in future if item.section_id == section.section_id
        )
        if (
            section.maximum_placements is not None
            and existing_target_count + 1 > section.maximum_placements
        ):
            raise CurationWorkflowError(
                "curation.section_cardinality_exceeded",
                "Replacement Placement would exceed the Profile section maximum.",
                stage="replacement",
            )
        migrated_target_sections.add(section.section_id)
        new_placement = PortfolioPlacement(
            placement_id=id_factory("placement"),
            portfolio_id=context.portfolio.portfolio_id,
            profile_binding_id=context.binding.profile_binding_id,
            selection_id=new_selection.selection_id,
            section_id=section.section_id,
            presentation=old_placement.presentation,
            placed_at=now,
            placed_by=replaced_by,
        )
        records.extend(
            (
                new_placement,
                PlacementLifecycleEvent(
                    placement_lifecycle_event_id=id_factory("placement_event"),
                    placement_id=old_placement.placement_id,
                    event_kind="replaced",
                    event_at=now,
                    actor=replaced_by,
                    authority_reference=authority.authority_reference or "",
                    reason=reason,
                    predecessor_event_id=old_placement_head.placement_lifecycle_event_id,
                    successor_placement_id=new_placement.placement_id,
                ),
                PlacementLifecycleEvent(
                    placement_lifecycle_event_id=id_factory("placement_event"),
                    placement_id=new_placement.placement_id,
                    event_kind="activated",
                    event_at=now,
                    actor=replaced_by,
                    authority_reference=authority.authority_reference or "",
                    reason="Activate migrated replacement Placement.",
                ),
            )
        )
        future.append(new_placement)
    for section_id in sorted(affected_sections):
        desired = tuple(item.placement_id for item in future if item.section_id == section_id)
        arrangement, pointer = _arrangement_transition(
            context,
            section_id=section_id,
            desired_placement_ids=desired,
            expected_pointer_revision=expected_pointer_revisions.get(section_id),
            actor=replaced_by,
            authority_reference=authority.authority_reference or "",
            now=now,
            id_factory=id_factory,
        )
        records.extend((arrangement, pointer))
    return _validated_commit(workspace_root, context, tuple(records))


def _validate_targets(context: _Context, targets: tuple[CurationTargetRef, ...]) -> None:
    for target in targets:
        if target.target_kind == "selection":
            _selection(context, target.target_id)
        elif target.target_kind == "placement":
            _placement(context, target.target_id)
        elif target.target_kind == "section":
            _section(context, target.target_id)
        elif target.target_kind == "composition":
            if target.target_revision is None or not any(
                item.portfolio_id == target.target_id
                and item.composition_revision == target.target_revision
                and item.profile_binding_id == context.binding.profile_binding_id
                for item in context.curation.compositions
            ):
                raise CurationWorkflowError(
                    "curation.annotation_target_invalid",
                    "Composition target does not exist in the exact context.",
                    stage="target",
                )
        elif target.target_kind == "portfolio":
            if target.target_id != context.portfolio.portfolio_id:
                raise CurationWorkflowError(
                    "curation.reflection_target_invalid",
                    "Portfolio target differs from the exact context.",
                    stage="target",
                )
        elif target.target_kind == "selection_proposal":
            if not any(
                item.selection_proposal_id == target.target_id
                for item in context.curation.proposals
            ):
                raise CurationWorkflowError(
                    "curation.review_target_invalid",
                    "Proposal target does not exist.",
                    stage="target",
                )
        elif target.target_kind == "arrangement":
            if not any(item.arrangement_id == target.target_id for item in context.curation.arrangements):
                raise CurationWorkflowError(
                    "curation.review_target_invalid",
                    "Arrangement target does not exist.",
                    stage="target",
                )
        elif target.target_kind == "annotation":
            if target.target_revision is None or not any(
                item.annotation_id == target.target_id
                and item.annotation_revision == target.target_revision
                for item in context.curation.annotations
            ):
                raise CurationWorkflowError(
                    "curation.review_target_invalid",
                    "Annotation target revision does not exist.",
                    stage="target",
                )
        elif target.target_kind == "reflection":
            if target.target_revision is None or not any(
                item.reflection_id == target.target_id
                and item.reflection_revision == target.target_revision
                for item in context.curation.reflections
            ):
                raise CurationWorkflowError(
                    "curation.review_target_invalid",
                    "Reflection target revision does not exist.",
                    stage="target",
                )


def create_annotation(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    purpose: str,
    target_scope: str,
    target_references: tuple[CurationTargetRef, ...],
    author: ActorAttribution,
    content: str,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    language: str = "en",
    content_format: str = "plain_text",
    intended_presentation_class: str | None = None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    targets = tuple(target_references)
    _validate_targets(context, targets)
    _authority(authority_gate, context, author, "annotate", targets=targets)
    annotation = CurationAnnotation(
        annotation_id=id_factory("annotation"),
        annotation_revision=1,
        portfolio_id=context.portfolio.portfolio_id,
        portfolio_subject_id=context.portfolio.portfolio_subject_id,
        profile_binding_id=context.binding.profile_binding_id,
        profile_revision=context.binding.profile_revision,
        purpose=purpose,
        target_scope=target_scope,
        target_references=targets,
        author=author,
        created_at=_now(clock),
        language=language,
        content_format=content_format,
        content=content,
        intended_presentation_class=intended_presentation_class,
    )
    return _validated_commit(workspace_root, context, (annotation,))


def revise_annotation(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    annotation_id: str,
    expected_annotation_revision: int,
    author: ActorAttribution,
    content: str,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    purpose: str | None = None,
    target_scope: str | None = None,
    target_references: tuple[CurationTargetRef, ...] | None = None,
    language: str | None = None,
    content_format: str | None = None,
    intended_presentation_class: str | None = None,
    clock: Clock = _clock,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    heads = context.curation.annotation_heads(annotation_id)
    if len(heads) != 1 or heads[0].annotation_revision != expected_annotation_revision:
        raise CurationWorkflowError(
            "curation.annotation_revision_conflict",
            "Annotation revision head changed since caller observation.",
            stage="annotation",
        )
    prior = heads[0]
    targets = prior.target_references if target_references is None else tuple(target_references)
    _validate_targets(context, targets)
    _authority(authority_gate, context, author, "annotate", targets=targets)
    revised = CurationAnnotation(
        annotation_id=prior.annotation_id,
        annotation_revision=prior.annotation_revision + 1,
        portfolio_id=prior.portfolio_id,
        portfolio_subject_id=prior.portfolio_subject_id,
        profile_binding_id=prior.profile_binding_id,
        profile_revision=prior.profile_revision,
        purpose=prior.purpose if purpose is None else purpose,
        target_scope=prior.target_scope if target_scope is None else target_scope,
        target_references=targets,
        author=author,
        created_at=_now(clock),
        language=prior.language if language is None else language,
        content_format=prior.content_format if content_format is None else content_format,
        content=content,
        intended_presentation_class=(
            prior.intended_presentation_class
            if intended_presentation_class is None
            else intended_presentation_class
        ),
        predecessor_annotation_revision=prior.annotation_revision,
    )
    return _validated_commit(workspace_root, context, (revised,))


def _require_student_subject_author(
    context: _Context, author: ActorAttribution
) -> None:
    if author.actor_kind != "core_student":
        return
    links = tuple(
        item
        for item in context.records
        if isinstance(item, PortfolioSubjectClassLink)
        and item.portfolio_subject_id == context.portfolio.portfolio_subject_id
        and item.student_reference.student_id == author.actor_id
    )
    if not links:
        raise CurationWorkflowError(
            "curation.reflection_author_unresolved",
            "Student Reflection author is not exactly linked to the Portfolio Subject.",
            stage="reflection",
        )


def _reflection_requirement(
    context: _Context, requirement_id: str
) -> PortfolioProfileRequirement:
    requirement = next(
        (item for item in context.requirements if item.requirement_id == requirement_id),
        None,
    )
    if requirement is None or requirement.requirement_kind != "reflection":
        raise CurationWorkflowError(
            "curation.reflection_requirement_missing",
            "Exact Profile Reflection requirement does not exist.",
            stage="reflection",
        )
    return requirement


def create_reflection(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    reflection_requirement_id: str,
    prompt_id: str,
    prompt_version: str,
    prompt_snapshot: str,
    author: ActorAttribution,
    target_scope: str,
    target_references: tuple[CurationTargetRef, ...],
    content: str,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    content_mode: str = "inline_text",
    language: str = "en",
    content_format: str = "plain_text",
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    requirement = _reflection_requirement(context, reflection_requirement_id)
    targets = tuple(target_references)
    _validate_targets(context, targets)
    _require_student_subject_author(context, author)
    _authority(
        authority_gate,
        context,
        author,
        "reflect",
        targets=targets,
        requirement_ids=(requirement.requirement_id,),
    )
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
        author=author,
        target_scope=target_scope,
        target_references=targets,
        content_mode=content_mode,
        language=language,
        content_format=content_format,
        content=content,
        created_at=_now(clock),
    )
    return _validated_commit(workspace_root, context, (reflection,))


def revise_reflection(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    reflection_id: str,
    expected_reflection_revision: int,
    author: ActorAttribution,
    content: str,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    prompt_id: str | None = None,
    prompt_version: str | None = None,
    prompt_snapshot: str | None = None,
    target_scope: str | None = None,
    target_references: tuple[CurationTargetRef, ...] | None = None,
    clock: Clock = _clock,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    heads = context.curation.reflection_heads(reflection_id)
    if len(heads) != 1 or heads[0].reflection_revision != expected_reflection_revision:
        raise CurationWorkflowError(
            "curation.reflection_revision_conflict",
            "Reflection revision head changed since caller observation.",
            stage="reflection",
        )
    prior = heads[0]
    _reflection_requirement(context, prior.reflection_requirement_id)
    targets = prior.target_references if target_references is None else tuple(target_references)
    _validate_targets(context, targets)
    _require_student_subject_author(context, author)
    _authority(
        authority_gate,
        context,
        author,
        "reflect",
        targets=targets,
        requirement_ids=(prior.reflection_requirement_id,),
    )
    revised = PortfolioReflection(
        reflection_id=prior.reflection_id,
        reflection_revision=prior.reflection_revision + 1,
        portfolio_id=prior.portfolio_id,
        portfolio_subject_id=prior.portfolio_subject_id,
        profile_binding_id=prior.profile_binding_id,
        profile_revision=prior.profile_revision,
        reflection_requirement_id=prior.reflection_requirement_id,
        prompt_id=prior.prompt_id if prompt_id is None else prompt_id,
        prompt_version=prior.prompt_version if prompt_version is None else prompt_version,
        prompt_snapshot=prior.prompt_snapshot if prompt_snapshot is None else prompt_snapshot,
        author=author,
        target_scope=prior.target_scope if target_scope is None else target_scope,
        target_references=targets,
        content_mode=prior.content_mode,
        language=prior.language,
        content_format=prior.content_format,
        content=content,
        created_at=_now(clock),
        predecessor_reflection_revision=prior.reflection_revision,
    )
    return _validated_commit(workspace_root, context, (revised,))


def review_curation_target(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    target_scope: str,
    target_references: tuple[CurationTargetRef, ...],
    decision: str,
    reviewed_by: ActorAttribution,
    reason: str,
    expected_state_revision: int,
    authority_gate: CurationAuthorityGate,
    approval_requirement_id: str | None = None,
    required_follow_up_codes: tuple[str, ...] = (),
    predecessor_review_decision_id: str | None = None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    targets = tuple(target_references)
    _validate_targets(context, targets)
    requirement_ids: tuple[str, ...] = ()
    if approval_requirement_id is not None:
        requirement = next(
            (
                item
                for item in context.requirements
                if item.requirement_id == approval_requirement_id
            ),
            None,
        )
        if requirement is None or requirement.requirement_kind != "approval":
            raise CurationWorkflowError(
                "curation.review_requirement_missing",
                "Exact Profile approval requirement does not exist.",
                stage="review",
            )
        requirement_ids = (requirement.requirement_id,)
    authority = _authority(
        authority_gate,
        context,
        reviewed_by,
        "review_curation",
        targets=targets,
        requirement_ids=requirement_ids,
    )
    if decision == "waived" and not authority.waiver_permitted:
        raise CurationWorkflowError(
            "curation.review_waiver_not_permitted",
            "Curation waiver authority was not explicitly established.",
            stage="review",
        )
    review = CurationReviewDecision(
        curation_review_decision_id=id_factory("curation_review"),
        portfolio_id=context.portfolio.portfolio_id,
        portfolio_subject_id=context.portfolio.portfolio_subject_id,
        profile_binding_id=context.binding.profile_binding_id,
        profile_revision=context.binding.profile_revision,
        target_scope=target_scope,
        target_references=targets,
        decision=decision,
        reviewed_at=_now(clock),
        reviewed_by=reviewed_by,
        authority_reference=authority.authority_reference or "",
        reason=reason,
        approval_requirement_id=approval_requirement_id,
        required_follow_up_codes=required_follow_up_codes,
        predecessor_review_decision_id=predecessor_review_decision_id,
    )
    return _validated_commit(workspace_root, context, (review,))


def _current_curation_revision_refs(context: _Context) -> tuple[CurationRevisionRef, ...]:
    refs: list[CurationRevisionRef] = []
    for annotation_id in sorted(
        {item.annotation_id for item in context.curation.annotations}
    ):
        annotation_heads = context.curation.annotation_heads(annotation_id)
        if len(annotation_heads) == 1:
            annotation = annotation_heads[0]
            if (
                annotation.portfolio_id == context.portfolio.portfolio_id
                and annotation.profile_binding_id == context.binding.profile_binding_id
            ):
                refs.append(
                    CurationRevisionRef(
                        record_kind="annotation",
                        record_id=annotation.annotation_id,
                        revision=annotation.annotation_revision,
                    )
                )
    for reflection_id in sorted(
        {item.reflection_id for item in context.curation.reflections}
    ):
        reflection_heads = context.curation.reflection_heads(reflection_id)
        if len(reflection_heads) == 1:
            reflection = reflection_heads[0]
            if (
                reflection.portfolio_id == context.portfolio.portfolio_id
                and reflection.profile_binding_id == context.binding.profile_binding_id
            ):
                refs.append(
                    CurationRevisionRef(
                        record_kind="reflection",
                        record_id=reflection.reflection_id,
                        revision=reflection.reflection_revision,
                    )
                )
    return tuple(refs)


def _composition_pointer(context: _Context) -> WorkingPortfolioCompositionPointerRevision | None:
    heads = context.curation.composition_pointer_heads(
        context.portfolio.portfolio_id,
        context.binding.profile_binding_id,
    )
    if len(heads) > 1:
        raise CurationWorkflowError(
            "curation.composition_pointer_conflict",
            "Working Portfolio Composition pointer is conflicted.",
            stage="composition",
        )
    return heads[0] if heads else None


def create_working_composition(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    created_by: ActorAttribution,
    expected_state_revision: int,
    expected_composition_pointer_revision: int | None,
    authority_gate: CurationAuthorityGate,
    composition_note: str | None = None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CurationMutationResult:
    context = _load_context(workspace_root, portfolio_id, expected_state_revision)
    authority = _authority(
        authority_gate,
        context,
        created_by,
        "compose_portfolio",
    )
    active_selections = context.curation.active_selections(
        portfolio_id=context.portfolio.portfolio_id,
        profile_binding_id=context.binding.profile_binding_id,
    )
    active_placements = context.curation.active_placements(
        portfolio_id=context.portfolio.portfolio_id,
        profile_binding_id=context.binding.profile_binding_id,
    )
    section_order = {item.section_id: item.order for item in context.profile.sections}
    arrangements: list[SectionArrangementRevision] = []
    for section in context.profile.sections:
        section_placements = tuple(
            item for item in active_placements if item.section_id == section.section_id
        )
        if section.obligation == "prohibited" and section_placements:
            raise CurationWorkflowError(
                "curation.composition_inconsistent",
                "Prohibited section contains active Placements.",
                stage="composition",
            )
        if section.maximum_placements is not None and len(section_placements) > section.maximum_placements:
            raise CurationWorkflowError(
                "curation.section_cardinality_exceeded",
                "Section maximum Placement count is exceeded.",
                stage="composition",
            )
        if not section_placements:
            continue
        arrangement = context.curation.current_arrangement(
            context.portfolio.portfolio_id,
            context.binding.profile_binding_id,
            section.section_id,
        )
        if arrangement is None or set(arrangement.placement_ids) != {
            item.placement_id for item in section_placements
        }:
            raise CurationWorkflowError(
                "curation.arrangement_incomplete",
                "Every active Placement must be covered by the exact current Arrangement.",
                stage="composition",
            )
        arrangements.append(arrangement)
    arrangements.sort(key=lambda item: section_order[item.section_id])
    ordered_placement_ids = tuple(
        placement_id
        for arrangement in arrangements
        for placement_id in arrangement.placement_ids
    )
    selection_ids: list[str] = []
    placement_by_id = {item.placement_id: item for item in active_placements}
    for placement_id in ordered_placement_ids:
        selection_id = placement_by_id[placement_id].selection_id
        if selection_id not in selection_ids:
            selection_ids.append(selection_id)
    for selection in sorted(active_selections, key=lambda item: item.selection_id):
        if selection.selection_id not in selection_ids:
            selection_ids.append(selection.selection_id)

    unresolved: set[str] = set()
    related_requirements: set[str] = set()
    current_reflections = {
        head.reflection_requirement_id
        for reflection_id in {item.reflection_id for item in context.curation.reflections}
        for head in context.curation.reflection_heads(reflection_id)
        if len(context.curation.reflection_heads(reflection_id)) == 1
        and head.portfolio_id == context.portfolio.portfolio_id
        and head.profile_binding_id == context.binding.profile_binding_id
    }
    for section in context.profile.sections:
        count = sum(1 for item in active_placements if item.section_id == section.section_id)
        if count < section.minimum_placements:
            unresolved.add("section_minimum_missing")
        if section.reflection_requirement == "required":
            scoped = tuple(
                item
                for item in context.requirements
                if item.requirement_kind == "reflection"
                and item.scope_kind == "section"
                and item.scope_reference == section.section_id
            )
            if not scoped or not any(
                item.requirement_id in current_reflections for item in scoped
            ):
                unresolved.add("reflection_required")
            related_requirements.update(item.requirement_id for item in scoped)
    for requirement in context.requirements:
        if requirement.obligation not in {"required", "conditional"}:
            continue
        if requirement.requirement_kind == "reflection":
            related_requirements.add(requirement.requirement_id)
            if requirement.obligation == "required" and requirement.requirement_id not in current_reflections:
                unresolved.add("reflection_required")
        elif requirement.requirement_kind == "approval":
            related_requirements.add(requirement.requirement_id)
        elif requirement.obligation == "conditional":
            related_requirements.add(requirement.requirement_id)
            unresolved.add("conditional_requirement_unresolved")
    for selection in active_selections:
        heads = context.curation.selection_heads(selection.selection_id)
        if len(heads) == 1:
            unresolved.update(heads[0].unresolved_condition_codes)
        candidate = _candidate(context, selection.candidate_id)
        if _current_source_state(workspace_root, candidate) != "current":
            unresolved.add("source_current_use_unresolved")

    curation_refs = _current_curation_revision_refs(context)
    rationale_ids = tuple(
        sorted(
            item.rationale_id
            for item in context.curation.rationales
            if item.portfolio_id == context.portfolio.portfolio_id
            and item.profile_binding_id == context.binding.profile_binding_id
        )
    )
    current_target_keys: set[tuple[str, str, int | None]] = {
        ("selection", item.selection_id, None) for item in active_selections
    } | {("placement", item.placement_id, None) for item in active_placements} | {
        ("arrangement", item.arrangement_id, None) for item in arrangements
    }
    current_target_keys.update(
        (ref.record_kind, ref.record_id, ref.revision) for ref in curation_refs
    )
    applicable_reviews = tuple(
        item
        for item in context.curation.reviews
        if item.portfolio_id == context.portfolio.portfolio_id
        and item.profile_binding_id == context.binding.profile_binding_id
        and all(
            (target.target_kind, target.target_id, target.target_revision)
            in current_target_keys
            for target in item.target_references
        )
    )
    review_ids = tuple(
        sorted(item.curation_review_decision_id for item in applicable_reviews)
    )
    approved_requirement_ids = {
        item.approval_requirement_id
        for item in applicable_reviews
        if item.approval_requirement_id is not None
        and item.decision in {"approved", "acknowledged", "waived"}
    }
    # Re-evaluate required approval obligations against only reviews of exact
    # curation state included by this Composition.
    if any(
        item.obligation == "required"
        and item.requirement_kind == "approval"
        and item.requirement_id not in approved_requirement_ids
        for item in context.requirements
    ):
        unresolved.add("approval_required")

    pointer = _composition_pointer(context)
    if pointer is None:
        if expected_composition_pointer_revision is not None:
            raise CurationWorkflowError(
                "curation.composition_pointer_conflict",
                "Expected Composition pointer does not exist.",
                stage="composition",
            )
        composition_revision = 1
        predecessor_revision = None
        pointer_id = id_factory("composition_pointer")
        pointer_revision = 1
        predecessor_pointer = None
    else:
        if expected_composition_pointer_revision != pointer.pointer_revision:
            raise CurationWorkflowError(
                "curation.composition_pointer_conflict",
                "Composition pointer changed since caller observation.",
                stage="composition",
            )
        current_composition = context.curation.current_composition(
            context.portfolio.portfolio_id,
            context.binding.profile_binding_id,
        )
        if current_composition is None:
            raise CurationWorkflowError(
                "curation.composition_pointer_conflict",
                "Current Composition pointer target is invalid.",
                stage="composition",
            )
        current_inventory = next(
            (
                item
                for item in context.curation.composition_inventories
                if item.portfolio_id == current_composition.portfolio_id
                and item.composition_revision == current_composition.composition_revision
            ),
            None,
        )
        expected_payload = (
            tuple(selection_ids),
            ordered_placement_ids,
            tuple(item.arrangement_id for item in arrangements),
            rationale_ids,
            curation_refs,
            review_ids,
            tuple(sorted(related_requirements)),
            tuple(sorted(unresolved)),
        )
        if current_inventory is not None:
            current_payload = (
                current_composition.selection_ids,
                current_composition.placement_ids,
                current_composition.arrangement_ids,
                current_inventory.included_rationale_ids,
                current_inventory.included_curation_revisions,
                current_inventory.applicable_review_decision_ids,
                current_inventory.related_profile_requirement_ids,
                current_inventory.unresolved_obligation_codes,
            )
            if current_payload == expected_payload:
                return CurationMutationResult(
                    state_revision=context.state_revision,
                    records=(current_composition, current_inventory, pointer),
                    disposition="existing",
                )
        composition_revision = current_composition.composition_revision + 1
        predecessor_revision = current_composition.composition_revision
        pointer_id = pointer.composition_pointer_id
        pointer_revision = pointer.pointer_revision + 1
        predecessor_pointer = pointer.pointer_revision

    now = _now(clock)
    composition = WorkingPortfolioCompositionRevision(
        portfolio_id=context.portfolio.portfolio_id,
        portfolio_subject_id=context.portfolio.portfolio_subject_id,
        profile_binding_id=context.binding.profile_binding_id,
        profile_revision=context.binding.profile_revision,
        composition_revision=composition_revision,
        selection_ids=tuple(selection_ids),
        placement_ids=ordered_placement_ids,
        arrangement_ids=tuple(item.arrangement_id for item in arrangements),
        created_at=now,
        created_by=created_by,
        predecessor_composition_revision=predecessor_revision,
        composition_note=composition_note,
    )
    inventory = WorkingPortfolioCompositionInventory(
        portfolio_id=context.portfolio.portfolio_id,
        composition_revision=composition_revision,
        profile_binding_id=context.binding.profile_binding_id,
        profile_revision=context.binding.profile_revision,
        included_rationale_ids=rationale_ids,
        included_curation_revisions=curation_refs,
        applicable_review_decision_ids=review_ids,
        related_profile_requirement_ids=tuple(sorted(related_requirements)),
        unresolved_obligation_codes=tuple(sorted(unresolved)),
        coherence_state=(
            "coherent_with_unresolved_obligations" if unresolved else "coherent"
        ),
        created_at=now,
        created_by=created_by,
    )
    next_pointer = WorkingPortfolioCompositionPointerRevision(
        composition_pointer_id=pointer_id,
        pointer_revision=pointer_revision,
        portfolio_id=context.portfolio.portfolio_id,
        profile_binding_id=context.binding.profile_binding_id,
        composition_revision=composition_revision,
        pointed_at=now,
        pointed_by=created_by,
        authority_reference=authority.authority_reference or "",
        predecessor_pointer_revision=predecessor_pointer,
    )
    return _validated_commit(
        workspace_root,
        context,
        (composition, inventory, next_pointer),
    )


__all__ = [
    "CURATION_OPERATIONS",
    "CURATION_WORKFLOW_CODES",
    "CurationAuthorityDecision",
    "CurationAuthorityGate",
    "CurationAuthorityRequest",
    "CurationMutationResult",
    "CurationWorkflowError",
    "create_annotation",
    "create_reflection",
    "create_working_composition",
    "decide_selection_proposal",
    "invalidate_selection",
    "place_selection",
    "propose_candidate_selection",
    "reorder_section",
    "replace_placement",
    "replace_selection",
    "review_curation_target",
    "revise_annotation",
    "revise_reflection",
    "select_candidate_directly",
    "withdraw_selection",
]
