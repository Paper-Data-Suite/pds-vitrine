"""Read-only Vitrine teacher-attention and next-action projection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vitrine.candidate_inbox import (
    MAX_CANDIDATE_INBOX_RESULTS,
    CandidateInboxError,
    CandidateInboxItem,
    CandidateInboxQuery,
    list_candidate_inbox,
)
from vitrine.curation_services import CurationWorkflowError
from vitrine.curation_state import CurationState, project_curation_state
from vitrine.models import (
    Portfolio,
    PortfolioCandidate,
    SelectionProposal,
    SnapshotBuildAttempt,
    SnapshotBuildAttemptResult,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotExportArtifact,
    SnapshotExportPlan,
    SnapshotSeries,
    VitrineRecord,
)
from vitrine.models.common import (
    require_enum,
    require_identifier,
    require_nonnegative_int,
    require_positive_int,
    require_text,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.snapshot_distribution import (
    SnapshotCustodyFinding,
    SnapshotDistributionError,
    inspect_snapshot_custody,
    verify_snapshot_export,
)
from vitrine.snapshot_state import SnapshotState, project_snapshot_state
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
    load_current_state,
)
from vitrine.working_composition import (
    WorkingCompositionPreparation,
    prepare_working_composition,
)

VITRINE_ATTENTION_CONTRACT_VERSION: Final[str] = "vitrine_attention_next_actions_v1"
VITRINE_ATTENTION_EVALUATIONS: Final[frozenset[str]] = frozenset(
    {"evaluated", "unavailable"}
)
VITRINE_ATTENTION_CLASSES: Final[frozenset[str]] = frozenset(
    {"workflow", "recovery", "integrity", "notice"}
)
VITRINE_ATTENTION_NOTICE_CODES: Final[frozenset[str]] = frozenset(
    {"vitrine_attention_partial", "vitrine_attention_unavailable"}
)
VITRINE_ATTENTION_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "vitrine_attention.invalid_query",
        "vitrine_attention.portfolio_not_found",
    }
)

_MAX_CODE_LENGTH: Final[int] = 64
_MAX_LABEL_LENGTH: Final[int] = 160
_MAX_NOTICE_LENGTH: Final[int] = 240
_MAX_REASON_CODE_LENGTH: Final[int] = 128
_MAX_REASON_CODES: Final[int] = 16
_MAX_SUMMARIES: Final[int] = 32
_MAX_NOTICES: Final[int] = 16
_MAX_COUNT: Final[int] = 1_000_000


class VitrineAttentionError(RuntimeError):
    """Expected invalid attention request with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        if code not in VITRINE_ATTENTION_ERROR_CODES:
            raise ValueError(f"unsupported Vitrine attention error code: {code}")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class VitrineAttentionQuery:
    """Optional exact Portfolio scope for one read-only attention evaluation."""

    portfolio_id: str | None = None

    def __post_init__(self) -> None:
        if self.portfolio_id is None:
            return
        try:
            object.__setattr__(
                self,
                "portfolio_id",
                require_identifier(self.portfolio_id, "portfolio_id"),
            )
        except VitrineModelValidationError as error:
            raise VitrineAttentionError(
                "vitrine_attention.invalid_query",
                "Attention Portfolio scope is invalid.",
            ) from error


@dataclass(frozen=True, slots=True)
class VitrineNextActionRef:
    """Opaque Vitrine-owned route back to an existing owner workflow."""

    action_id: str
    portfolio_id: str | None = None

    def __post_init__(self) -> None:
        try:
            action_id = require_identifier(self.action_id, "action_id")
            if len(action_id) > _MAX_CODE_LENGTH:
                raise VitrineModelValidationError("action_id is too long.")
            object.__setattr__(self, "action_id", action_id)
            if self.portfolio_id is not None:
                object.__setattr__(
                    self,
                    "portfolio_id",
                    require_identifier(self.portfolio_id, "portfolio_id"),
                )
        except VitrineModelValidationError as error:
            raise ValueError("invalid Vitrine next-action reference") from error


@dataclass(frozen=True, slots=True)
class VitrineAttentionNotice:
    """Bounded code-owned explanatory notice for one attention evaluation."""

    code: str
    summary: str

    def __post_init__(self) -> None:
        if self.code not in VITRINE_ATTENTION_NOTICE_CODES:
            raise ValueError("unsupported Vitrine attention notice code")
        try:
            if len(require_identifier(self.code, "code")) > _MAX_CODE_LENGTH:
                raise VitrineModelValidationError("notice code is too long.")
            object.__setattr__(
                self,
                "summary",
                require_text(self.summary, "summary", maximum=_MAX_NOTICE_LENGTH),
            )
        except VitrineModelValidationError as error:
            raise ValueError("invalid Vitrine attention notice") from error


@dataclass(frozen=True, slots=True)
class VitrineAttentionSummary:
    """One deterministic privacy-minimal Vitrine teacher-attention aggregate."""

    code: str
    label: str
    count: int
    count_unit: str
    attention_class: str
    portfolio_id: str | None
    reason_codes: tuple[str, ...]
    next_action: VitrineNextActionRef | None

    def __post_init__(self) -> None:
        try:
            code = require_identifier(self.code, "code")
            if len(code) > _MAX_CODE_LENGTH:
                raise VitrineModelValidationError("attention code is too long.")
            object.__setattr__(self, "code", code)
            object.__setattr__(
                self,
                "label",
                require_text(self.label, "label", maximum=_MAX_LABEL_LENGTH),
            )
            count = require_nonnegative_int(self.count, "count")
            if count > _MAX_COUNT:
                raise VitrineModelValidationError("attention count is too large.")
            object.__setattr__(self, "count", count)
            object.__setattr__(
                self,
                "count_unit",
                require_identifier(self.count_unit, "count_unit"),
            )
            object.__setattr__(
                self,
                "attention_class",
                require_enum(
                    self.attention_class,
                    "attention_class",
                    VITRINE_ATTENTION_CLASSES,
                ),
            )
            if self.portfolio_id is not None:
                object.__setattr__(
                    self,
                    "portfolio_id",
                    require_identifier(self.portfolio_id, "portfolio_id"),
                )
            reasons = tuple(
                require_text(
                    value,
                    "reason_codes",
                    maximum=_MAX_REASON_CODE_LENGTH,
                )
                for value in self.reason_codes
            )
            if len(set(reasons)) != len(reasons):
                raise VitrineModelValidationError(
                    "reason_codes must not contain duplicates."
                )
            if len(reasons) > _MAX_REASON_CODES:
                raise VitrineModelValidationError(
                    "reason_codes exceeds the bounded attention maximum."
                )
            object.__setattr__(self, "reason_codes", reasons)
        except VitrineModelValidationError as error:
            raise ValueError("invalid Vitrine attention summary") from error
        if self.next_action is not None:
            if not isinstance(self.next_action, VitrineNextActionRef):
                raise ValueError("next_action must be VitrineNextActionRef or null")
            if self.next_action.portfolio_id != self.portfolio_id:
                raise ValueError(
                    "next_action Portfolio scope must match the attention summary"
                )


@dataclass(frozen=True, slots=True)
class VitrineAttentionReport:
    """One exact read-only Vitrine attention evaluation."""

    contract_version: str
    evaluation: str
    observed_state_revision: int | None
    summaries: tuple[VitrineAttentionSummary, ...]
    notices: tuple[VitrineAttentionNotice, ...]

    def __post_init__(self) -> None:
        if self.contract_version != VITRINE_ATTENTION_CONTRACT_VERSION:
            raise ValueError("unsupported Vitrine attention contract version")
        try:
            object.__setattr__(
                self,
                "evaluation",
                require_enum(
                    self.evaluation,
                    "evaluation",
                    VITRINE_ATTENTION_EVALUATIONS,
                ),
            )
            if self.observed_state_revision is not None:
                object.__setattr__(
                    self,
                    "observed_state_revision",
                    require_positive_int(
                        self.observed_state_revision,
                        "observed_state_revision",
                    ),
                )
        except VitrineModelValidationError as error:
            raise ValueError("invalid Vitrine attention report") from error
        summaries = tuple(self.summaries)
        notices = tuple(self.notices)
        if len(summaries) > _MAX_SUMMARIES:
            raise ValueError("too many Vitrine attention summaries")
        if len(notices) > _MAX_NOTICES:
            raise ValueError("too many Vitrine attention notices")
        if any(not isinstance(item, VitrineAttentionSummary) for item in summaries):
            raise ValueError("summaries must contain VitrineAttentionSummary values")
        if any(not isinstance(item, VitrineAttentionNotice) for item in notices):
            raise ValueError("notices must contain VitrineAttentionNotice values")
        if len({item.code for item in summaries}) != len(summaries):
            raise ValueError("attention summary codes must be unique")
        if len({item.code for item in notices}) != len(notices):
            raise ValueError("attention notice codes must be unique")
        object.__setattr__(self, "summaries", summaries)
        object.__setattr__(self, "notices", notices)
        if self.evaluation == "evaluated" and self.observed_state_revision is None:
            raise ValueError("evaluated attention reports require a state revision")
        if (
            self.evaluation == "unavailable"
            and self.observed_state_revision is not None
        ):
            raise ValueError(
                "unavailable attention reports must not claim a state revision"
            )


@dataclass(frozen=True, slots=True)
class _AttentionDefinition:
    code: str
    label: str
    count_unit: str
    attention_class: str
    action_id: str

    def __post_init__(self) -> None:
        VitrineAttentionSummary(
            code=self.code,
            label=self.label,
            count=0,
            count_unit=self.count_unit,
            attention_class=self.attention_class,
            portfolio_id=None,
            reason_codes=(),
            next_action=VitrineNextActionRef(self.action_id),
        )


@dataclass(frozen=True, slots=True)
class _AttentionFact:
    code: str
    portfolio_id: str | None
    reason_codes: tuple[str, ...] = ()


_ATTENTION_DEFINITIONS: Final[tuple[_AttentionDefinition, ...]] = (
    _AttentionDefinition(
        "vitrine_candidate_review_pending",
        "Candidate review pending",
        "candidates",
        "workflow",
        "open_candidate_inbox",
    ),
    _AttentionDefinition(
        "vitrine_candidate_evaluation_stale",
        "Candidate evaluation stale",
        "candidate_entries",
        "workflow",
        "open_candidate_inbox",
    ),
    _AttentionDefinition(
        "vitrine_candidate_evaluation_unresolved",
        "Candidate evaluation unresolved",
        "candidate_entries",
        "workflow",
        "open_candidate_inbox",
    ),
    _AttentionDefinition(
        "vitrine_selection_decision_pending",
        "Selection decision pending",
        "selection_proposals",
        "workflow",
        "open_candidate_review",
    ),
    _AttentionDefinition(
        "vitrine_selection_follow_up_required",
        "Selection follow-up required",
        "selection_proposals",
        "workflow",
        "open_candidate_review",
    ),
    _AttentionDefinition(
        "vitrine_selection_condition_unresolved",
        "Selection condition unresolved",
        "selections",
        "workflow",
        "open_candidate_review",
    ),
    _AttentionDefinition(
        "vitrine_selection_unplaced",
        "Selection needs placement",
        "selections",
        "workflow",
        "open_candidate_review",
    ),
    _AttentionDefinition(
        "vitrine_curation_review_required",
        "Curation review required",
        "profile_requirements",
        "workflow",
        "open_candidate_review",
    ),
    _AttentionDefinition(
        "vitrine_curation_review_follow_up",
        "Curation review follow-up",
        "curation_reviews",
        "workflow",
        "open_candidate_review",
    ),
    _AttentionDefinition(
        "vitrine_working_composition_refresh_needed",
        "Working Composition refresh needed",
        "portfolios",
        "workflow",
        "open_working_composition",
    ),
    _AttentionDefinition(
        "vitrine_composition_requirement_unresolved",
        "Composition requirement unresolved",
        "profile_requirements",
        "workflow",
        "open_working_composition",
    ),
    _AttentionDefinition(
        "vitrine_composition_requirement_human_review",
        "Composition requirement needs human review",
        "profile_requirements",
        "workflow",
        "open_working_composition",
    ),
    _AttentionDefinition(
        "vitrine_composition_obligation_unresolved",
        "Composition obligation unresolved",
        "obligation_codes",
        "workflow",
        "open_working_composition",
    ),
    _AttentionDefinition(
        "vitrine_snapshot_recovery_required",
        "Snapshot recovery required",
        "snapshot_builds",
        "recovery",
        "inspect_snapshot_recovery",
    ),
    _AttentionDefinition(
        "vitrine_snapshot_build_failed",
        "Snapshot build failed",
        "snapshot_builds",
        "recovery",
        "inspect_snapshot_recovery",
    ),
    _AttentionDefinition(
        "vitrine_snapshot_durability_uncertain",
        "Snapshot durability is uncertain",
        "snapshot_builds",
        "integrity",
        "inspect_snapshot_recovery",
    ),
    _AttentionDefinition(
        "vitrine_snapshot_integrity_problem",
        "Snapshot integrity problem",
        "snapshot_findings",
        "integrity",
        "inspect_snapshot_custody",
    ),
    _AttentionDefinition(
        "vitrine_omission_audience_prohibited",
        "Snapshot content omitted for this audience",
        "snapshot_omissions",
        "notice",
        "inspect_snapshot_edition",
    ),
    _AttentionDefinition(
        "vitrine_omission_rights_review_unresolved",
        "Snapshot omission needs rights review",
        "snapshot_omissions",
        "workflow",
        "open_candidate_review",
    ),
    _AttentionDefinition(
        "vitrine_omission_privacy_review_unresolved",
        "Snapshot omission needs privacy review",
        "snapshot_omissions",
        "workflow",
        "open_candidate_review",
    ),
    _AttentionDefinition(
        "vitrine_omission_source_unavailable",
        "Snapshot source was unavailable",
        "snapshot_omissions",
        "workflow",
        "open_build_export_current_portfolio",
    ),
    _AttentionDefinition(
        "vitrine_omission_representation_unavailable",
        "Snapshot representation was unavailable",
        "snapshot_omissions",
        "workflow",
        "open_build_export_current_portfolio",
    ),
    _AttentionDefinition(
        "vitrine_omission_profile_excluded",
        "Snapshot content excluded by Profile",
        "snapshot_omissions",
        "notice",
        "inspect_snapshot_edition",
    ),
    _AttentionDefinition(
        "vitrine_omission_explicitly_not_included",
        "Snapshot content explicitly not included",
        "snapshot_omissions",
        "notice",
        "inspect_snapshot_edition",
    ),
    _AttentionDefinition(
        "vitrine_export_pending_after_seal",
        "Snapshot Export pending after seal",
        "snapshot_exports",
        "recovery",
        "open_build_export_current_portfolio",
    ),
    _AttentionDefinition(
        "vitrine_export_verification_problem",
        "Snapshot Export verification problem",
        "snapshot_exports",
        "integrity",
        "verify_snapshot_export",
    ),
)

VITRINE_ATTENTION_CODES: Final[frozenset[str]] = frozenset(
    item.code for item in _ATTENTION_DEFINITIONS
)
VITRINE_ATTENTION_ACTION_IDS: Final[frozenset[str]] = frozenset(
    item.action_id for item in _ATTENTION_DEFINITIONS
)
_DEFINITION_BY_CODE: Final[dict[str, _AttentionDefinition]] = {
    item.code: item for item in _ATTENTION_DEFINITIONS
}


def _unavailable_report() -> VitrineAttentionReport:
    return VitrineAttentionReport(
        contract_version=VITRINE_ATTENTION_CONTRACT_VERSION,
        evaluation="unavailable",
        observed_state_revision=None,
        summaries=(),
        notices=(
            VitrineAttentionNotice(
                code="vitrine_attention_unavailable",
                summary="Vitrine attention could not be evaluated safely.",
            ),
        ),
    )


def _partial_notice() -> VitrineAttentionNotice:
    return VitrineAttentionNotice(
        code="vitrine_attention_partial",
        summary=(
            "Some Vitrine attention sources could not be evaluated safely; "
            "available summaries are still shown."
        ),
    )


def _candidate_by_id(
    records: tuple[VitrineRecord, ...],
) -> dict[str, PortfolioCandidate]:
    return {
        item.candidate_id: item
        for item in records
        if isinstance(item, PortfolioCandidate)
    }


def _proposal_heads(
    state: CurationState,
    *,
    portfolio_id: str,
    profile_binding_id: str,
    candidate_id: str,
) -> tuple[SelectionProposal, ...]:
    proposals = tuple(
        item
        for item in state.proposals
        if item.portfolio_id == portfolio_id
        and item.profile_binding_id == profile_binding_id
        and item.candidate_id == candidate_id
    )
    predecessor_ids = {
        item.predecessor_proposal_id
        for item in proposals
        if item.predecessor_proposal_id is not None
    }
    return tuple(
        item
        for item in proposals
        if item.selection_proposal_id not in predecessor_ids
    )


def _candidate_has_explicit_curation_disposition(
    item: CandidateInboxItem,
    state: CurationState,
    candidates: dict[str, PortfolioCandidate],
) -> bool:
    if item.candidate_id is None:
        return False
    candidate = candidates.get(item.candidate_id)
    if candidate is None:
        return False
    if any(
        selection.candidate_id == candidate.candidate_id
        and selection.candidate_evaluation_id == candidate.candidate_evaluation_id
        for selection in state.selections
    ):
        return True
    proposal_ids = {
        proposal.selection_proposal_id
        for proposal in state.proposals
        if proposal.portfolio_id == item.portfolio_id
        and proposal.profile_binding_id == item.profile_binding_id
        and proposal.candidate_id == candidate.candidate_id
        and proposal.candidate_evaluation_id == candidate.candidate_evaluation_id
    }
    return any(
        decision.selection_proposal_id in proposal_ids for decision in state.decisions
    )


def _candidate_facts(
    items: tuple[CandidateInboxItem, ...],
    state: CurationState,
    records: tuple[VitrineRecord, ...],
) -> tuple[_AttentionFact, ...]:
    candidates = _candidate_by_id(records)
    facts: list[_AttentionFact] = []
    for item in items:
        if (
            item.candidate_id is not None
            and item.evaluation_outcome in {"eligible", "conditionally_eligible"}
            and not _candidate_has_explicit_curation_disposition(
                item,
                state,
                candidates,
            )
        ):
            facts.append(
                _AttentionFact(
                    code="vitrine_candidate_review_pending",
                    portfolio_id=item.portfolio_id,
                    reason_codes=("candidate_without_explicit_curation_disposition",),
                )
            )
        if item.stale_state == "stale":
            facts.append(
                _AttentionFact(
                    code="vitrine_candidate_evaluation_stale",
                    portfolio_id=item.portfolio_id,
                    reason_codes=item.stale_reason_codes,
                )
            )
        if item.evaluation_outcome == "unresolved" or item.stale_state == "unresolved":
            reasons = tuple(
                sorted(
                    set(
                        (
                            *item.stale_reason_codes,
                            *item.attention_reason_codes,
                        )
                    )
                )
            )
            facts.append(
                _AttentionFact(
                    code="vitrine_candidate_evaluation_unresolved",
                    portfolio_id=item.portfolio_id,
                    reason_codes=reasons or ("candidate_evaluation_unresolved",),
                )
            )
    return tuple(facts)


def _proposal_facts(
    items: tuple[CandidateInboxItem, ...],
    state: CurationState,
) -> tuple[_AttentionFact, ...]:
    facts: list[_AttentionFact] = []
    for item in items:
        if item.candidate_id is None:
            continue
        for proposal in _proposal_heads(
            state,
            portfolio_id=item.portfolio_id,
            profile_binding_id=item.profile_binding_id,
            candidate_id=item.candidate_id,
        ):
            decisions = tuple(
                decision
                for decision in state.decisions
                if decision.selection_proposal_id == proposal.selection_proposal_id
            )
            if not decisions:
                facts.append(
                    _AttentionFact(
                        code="vitrine_selection_decision_pending",
                        portfolio_id=item.portfolio_id,
                        reason_codes=("selection_proposal_undecided",),
                    )
                )
                continue
            if len(decisions) == 1 and decisions[0].decision == "changes_requested":
                facts.append(
                    _AttentionFact(
                        code="vitrine_selection_follow_up_required",
                        portfolio_id=item.portfolio_id,
                        reason_codes=("selection_decision_changes_requested",),
                    )
                )
    return tuple(facts)


def _working_composition_facts(
    preparation: WorkingCompositionPreparation,
) -> tuple[_AttentionFact, ...]:
    portfolio_id = preparation.portfolio_id
    facts: list[_AttentionFact] = []
    if preparation.disposition in {"create_initial", "create_successor"}:
        facts.append(
            _AttentionFact(
                code="vitrine_working_composition_refresh_needed",
                portfolio_id=portfolio_id,
                reason_codes=(
                    f"working_composition_{preparation.disposition}",
                ),
            )
        )
    for selection in preparation.selections:
        if selection.unresolved_condition_codes:
            facts.append(
                _AttentionFact(
                    code="vitrine_selection_condition_unresolved",
                    portfolio_id=portfolio_id,
                    reason_codes=selection.unresolved_condition_codes,
                )
            )
        if not selection.is_placed:
            facts.append(
                _AttentionFact(
                    code="vitrine_selection_unplaced",
                    portfolio_id=portfolio_id,
                    reason_codes=("selection_unplaced",),
                )
            )
    for requirement in preparation.requirements:
        if requirement.status in {"unresolved_missing", "conditional_unresolved"}:
            facts.append(
                _AttentionFact(
                    code="vitrine_composition_requirement_unresolved",
                    portfolio_id=portfolio_id,
                    reason_codes=(
                        f"requirement_{requirement.status}",
                        requirement.requirement_kind,
                    ),
                )
            )
            if requirement.requirement_kind == "approval":
                facts.append(
                    _AttentionFact(
                        code="vitrine_curation_review_required",
                        portfolio_id=portfolio_id,
                        reason_codes=(
                            f"approval_{requirement.status}",
                        ),
                    )
                )
        if (
            requirement.status == "not_machine_evaluable"
            and requirement.obligation == "required"
        ):
            facts.append(
                _AttentionFact(
                    code="vitrine_composition_requirement_human_review",
                    portfolio_id=portfolio_id,
                    reason_codes=(
                        "required_requirement_not_machine_evaluable",
                        requirement.requirement_kind,
                    ),
                )
            )
    for review in preparation.reviews:
        if review.requires_attention:
            reasons = tuple(
                sorted(
                    set(
                        (
                            f"curation_review_{review.decision}",
                            *review.required_follow_up_codes,
                        )
                    )
                )
            )
            facts.append(
                _AttentionFact(
                    code="vitrine_curation_review_follow_up",
                    portfolio_id=portfolio_id,
                    reason_codes=reasons,
                )
            )
    for obligation_code in preparation.payload.unresolved_obligation_codes:
        facts.append(
            _AttentionFact(
                code="vitrine_composition_obligation_unresolved",
                portfolio_id=portfolio_id,
                reason_codes=(obligation_code,),
            )
        )
    return tuple(facts)



_OMISSION_ATTENTION_CODE: Final[dict[str, str]] = {
    "audience_prohibited": "vitrine_omission_audience_prohibited",
    "rights_review_unresolved": "vitrine_omission_rights_review_unresolved",
    "privacy_review_unresolved": "vitrine_omission_privacy_review_unresolved",
    "source_unavailable": "vitrine_omission_source_unavailable",
    "representation_unavailable": "vitrine_omission_representation_unavailable",
    "profile_excluded": "vitrine_omission_profile_excluded",
    "explicitly_not_included": "vitrine_omission_explicitly_not_included",
}

_INTEGRITY_CUSTODY_CODES: Final[frozenset[str]] = frozenset(
    {
        "snapshot.custody.ambiguous_edition_target",
        "snapshot.custody.canonical_edition_missing_custody",
        "snapshot.custody.custody_edition_missing_canonical_state",
        "snapshot.custody.corrupted_entry",
        "snapshot.custody.corrupted_manifest",
        "snapshot.custody.orphan_export",
        "snapshot.custody.orphan_staging",
        "snapshot.custody.corrupted_export",
        "snapshot.custody.durability_uncertainty",
    }
)



def _series_heads(
    state: SnapshotState,
    portfolio_id: str,
) -> tuple[SnapshotSeries, ...]:
    values = tuple(
        item for item in state.series if item.portfolio_id == portfolio_id
    )
    predecessor_ids = {
        item.predecessor_series_id
        for item in values
        if item.predecessor_series_id is not None
    }
    return tuple(
        item
        for item in values
        if item.snapshot_series_id not in predecessor_ids
    )


def _request_head(
    state: SnapshotState,
    series: SnapshotSeries,
) -> SnapshotBuildRequest | None:
    values = tuple(
        item
        for item in state.requests
        if item.snapshot_series_id == series.snapshot_series_id
    )
    predecessor_ids = {
        item.predecessor_request_id
        for item in values
        if item.predecessor_request_id is not None
    }
    heads = tuple(
        item
        for item in values
        if item.snapshot_build_request_id not in predecessor_ids
    )
    return heads[0] if len(heads) == 1 else None


def _plan_head(
    state: SnapshotState,
    request: SnapshotBuildRequest,
) -> SnapshotBuildPlan | None:
    values = tuple(
        item
        for item in state.plans
        if item.snapshot_build_request_id == request.snapshot_build_request_id
    )
    predecessor_ids = {
        item.predecessor_plan_id
        for item in values
        if item.predecessor_plan_id is not None
    }
    heads = tuple(
        item
        for item in values
        if item.snapshot_build_plan_id not in predecessor_ids
    )
    return heads[0] if len(heads) == 1 else None

def _current_attempt(
    state: SnapshotState,
    plan: SnapshotBuildPlan,
) -> SnapshotBuildAttempt | None:
    attempts = tuple(
        item
        for item in state.attempts
        if item.snapshot_build_plan_id == plan.snapshot_build_plan_id
    )
    if not attempts:
        return None
    by_number = {item.attempt_number: item for item in attempts}
    if len(by_number) != len(attempts):
        return None
    return by_number[max(by_number)]


def _matching_export_heads(
    state: SnapshotState,
    result: SnapshotBuildAttemptResult,
    export_plan: SnapshotExportPlan,
) -> tuple[SnapshotExportArtifact, ...]:
    edition = result.sealed_snapshot_edition
    if edition is None:
        return ()
    values = tuple(
        item
        for item in state.export_artifacts
        if item.snapshot_edition == edition
        and item.export_format == export_plan.export_format
        and item.export_contract_version == export_plan.export_contract_version
        and item.configuration_digest == export_plan.configuration_digest
    )
    predecessor_ids = {
        item.predecessor_export_artifact_id
        for item in values
        if item.predecessor_export_artifact_id is not None
    }
    return tuple(
        item
        for item in values
        if item.snapshot_export_artifact_id not in predecessor_ids
    )


def _omission_facts(
    state: SnapshotState,
    result: SnapshotBuildAttemptResult,
    portfolio_id: str,
) -> tuple[_AttentionFact, ...]:
    edition = result.sealed_snapshot_edition
    if edition is None:
        return ()
    facts: list[_AttentionFact] = []
    for omission in state.omissions:
        if omission.snapshot_edition != edition:
            continue
        code = _OMISSION_ATTENTION_CODE.get(omission.reason_code)
        if code is None:
            continue
        facts.append(
            _AttentionFact(
                code=code,
                portfolio_id=portfolio_id,
                reason_codes=(omission.reason_code,),
            )
        )
    return tuple(facts)


def _custody_finding_relevant(
    finding: SnapshotCustodyFinding,
    *,
    include_unscoped: bool,
    current_attempt_ids: frozenset[str],
    current_series_ids: frozenset[str],
    current_edition_subjects: frozenset[str],
    current_export_ids: frozenset[str],
) -> bool:
    if finding.code in {
        "snapshot.custody.orphan_staging",
        "snapshot.custody.orphan_export",
        "snapshot.custody.custody_edition_missing_canonical_state",
    }:
        return include_unscoped
    if finding.subject_kind == "snapshot_build_attempt":
        return finding.subject_id in current_attempt_ids
    if finding.subject_kind == "snapshot_series":
        return finding.subject_id in current_series_ids
    if finding.subject_kind == "snapshot_edition":
        return finding.subject_id in current_edition_subjects
    if finding.subject_kind == "snapshot_export_artifact":
        return finding.subject_id in current_export_ids
    return False


def _snapshot_facts(
    workspace_root: Path,
    state: SnapshotState,
    portfolio_ids: tuple[str, ...],
    *,
    observed_state_revision: int,
    include_unscoped: bool,
) -> tuple[tuple[_AttentionFact, ...], bool]:
    facts: list[_AttentionFact] = []
    current_attempt_ids: set[str] = set()
    current_series_ids: set[str] = set()
    current_edition_subjects: set[str] = set()
    current_export_ids: set[str] = set()
    portfolio_by_attempt: dict[str, str] = {}
    portfolio_by_series: dict[str, str] = {}
    portfolio_by_edition: dict[str, str] = {}
    portfolio_by_export: dict[str, str] = {}
    verification_failed_ids: set[str] = set()
    recovery_series_ids: set[str] = set()
    partial = False

    for portfolio_id in portfolio_ids:
        for series in _series_heads(state, portfolio_id):
            current_series_ids.add(series.snapshot_series_id)
            portfolio_by_series[series.snapshot_series_id] = portfolio_id
            request = _request_head(state, series)
            if request is None:
                continue
            plan = _plan_head(state, request)
            if plan is None:
                continue
            attempt = _current_attempt(state, plan)
            if attempt is None:
                continue
            current_attempt_ids.add(attempt.snapshot_build_attempt_id)
            portfolio_by_attempt[attempt.snapshot_build_attempt_id] = portfolio_id
            result = state.result_for_attempt(attempt.snapshot_build_attempt_id)
            if result is None:
                recovery_series_ids.add(series.snapshot_series_id)
                facts.append(
                    _AttentionFact(
                        code="vitrine_snapshot_recovery_required",
                        portfolio_id=portfolio_id,
                        reason_codes=("snapshot_attempt_incomplete",),
                    )
                )
                continue
            if result.terminal_outcome == "failed":
                reasons = tuple(
                    sorted({item.code for item in result.findings})
                ) or ("snapshot_attempt_failed",)
                facts.append(
                    _AttentionFact(
                        code="vitrine_snapshot_build_failed",
                        portfolio_id=portfolio_id,
                        reason_codes=reasons,
                    )
                )
                continue
            if result.terminal_outcome == "durability_uncertain":
                recovery_series_ids.add(series.snapshot_series_id)
                facts.extend(
                    (
                        _AttentionFact(
                            code="vitrine_snapshot_durability_uncertain",
                            portfolio_id=portfolio_id,
                            reason_codes=("snapshot_durability_uncertain",),
                        ),
                        _AttentionFact(
                            code="vitrine_snapshot_recovery_required",
                            portfolio_id=portfolio_id,
                            reason_codes=("snapshot_durability_uncertain",),
                        ),
                    )
                )
                continue
            if result.terminal_outcome not in {"sealed", "partial_success_after_seal"}:
                continue
            edition = result.sealed_snapshot_edition
            if edition is None:
                continue
            edition_subject = f"{edition.snapshot_series_id}:{edition.edition_number}"
            current_edition_subjects.add(edition_subject)
            portfolio_by_edition[edition_subject] = portfolio_id
            facts.extend(_omission_facts(state, result, portfolio_id))

            for export_plan in plan.export_plans:
                exports = _matching_export_heads(state, result, export_plan)
                if len(exports) != 1:
                    facts.append(
                        _AttentionFact(
                            code="vitrine_export_pending_after_seal",
                            portfolio_id=portfolio_id,
                            reason_codes=(
                                "snapshot_export_missing"
                                if not exports
                                else "snapshot_export_head_conflict",
                            ),
                        )
                    )
                    continue
                artifact = exports[0]
                current_export_ids.add(artifact.snapshot_export_artifact_id)
                portfolio_by_export[artifact.snapshot_export_artifact_id] = portfolio_id
                try:
                    verify_snapshot_export(
                        workspace_root,
                        snapshot_export_artifact_id=(
                            artifact.snapshot_export_artifact_id
                        ),
                    )
                except SnapshotDistributionError as error:
                    verification_failed_ids.add(
                        artifact.snapshot_export_artifact_id
                    )
                    facts.append(
                        _AttentionFact(
                            code="vitrine_export_verification_problem",
                            portfolio_id=portfolio_id,
                            reason_codes=(error.code,),
                        )
                    )
                except Exception:
                    partial = True

    try:
        audit = inspect_snapshot_custody(workspace_root)
    except SnapshotDistributionError:
        partial = True
    except Exception:
        partial = True
    else:
        if audit.canonical_state_revision != observed_state_revision:
            return (), True
        for finding in audit.findings:
            if finding.code == "snapshot.custody.failed_attempt":
                continue
            if not _custody_finding_relevant(
                finding,
                include_unscoped=include_unscoped,
                current_attempt_ids=frozenset(current_attempt_ids),
                current_series_ids=frozenset(current_series_ids),
                current_edition_subjects=frozenset(current_edition_subjects),
                current_export_ids=frozenset(current_export_ids),
            ):
                continue
            finding_portfolio_id: str | None = None
            if finding.subject_kind == "snapshot_build_attempt":
                finding_portfolio_id = portfolio_by_attempt.get(finding.subject_id)
            elif finding.subject_kind == "snapshot_series":
                finding_portfolio_id = portfolio_by_series.get(finding.subject_id)
            elif finding.subject_kind == "snapshot_edition":
                finding_portfolio_id = portfolio_by_edition.get(finding.subject_id)
            elif finding.subject_kind == "snapshot_export_artifact":
                finding_portfolio_id = portfolio_by_export.get(finding.subject_id)
            if finding.code == "snapshot.custody.incomplete_attempt":
                continue
            if finding.code == "snapshot.custody.build_lock_present":
                if finding.subject_id in recovery_series_ids:
                    continue
                facts.append(
                    _AttentionFact(
                        code="vitrine_snapshot_recovery_required",
                        portfolio_id=finding_portfolio_id,
                        reason_codes=(finding.code,),
                    )
                )
                continue
            if (
                finding.code == "snapshot.custody.corrupted_export"
                and finding.subject_id in verification_failed_ids
            ):
                continue
            if finding.code in _INTEGRITY_CUSTODY_CODES:
                facts.append(
                    _AttentionFact(
                        code="vitrine_snapshot_integrity_problem",
                        portfolio_id=finding_portfolio_id,
                        reason_codes=(finding.code,),
                    )
                )

    return tuple(facts), partial

def _aggregate_facts(
    facts: tuple[_AttentionFact, ...],
) -> tuple[VitrineAttentionSummary, ...]:
    summaries: list[VitrineAttentionSummary] = []
    for definition in _ATTENTION_DEFINITIONS:
        matching = tuple(item for item in facts if item.code == definition.code)
        if not matching:
            continue
        portfolios = {item.portfolio_id for item in matching}
        portfolio_id = (
            next(iter(portfolios))
            if len(portfolios) == 1 and None not in portfolios
            else None
        )
        all_reasons = tuple(
            sorted(
                {
                    reason
                    for item in matching
                    for reason in item.reason_codes
                }
            )
        )
        reasons = all_reasons[:_MAX_REASON_CODES]
        summaries.append(
            VitrineAttentionSummary(
                code=definition.code,
                label=definition.label,
                count=len(matching),
                count_unit=definition.count_unit,
                attention_class=definition.attention_class,
                portfolio_id=portfolio_id,
                reason_codes=reasons,
                next_action=VitrineNextActionRef(
                    action_id=definition.action_id,
                    portfolio_id=portfolio_id,
                ),
            )
        )
    return tuple(summaries)


def _portfolio_ids(
    records: tuple[VitrineRecord, ...],
    query: VitrineAttentionQuery,
) -> tuple[str, ...]:
    available = tuple(
        sorted(
            item.portfolio_id
            for item in records
            if isinstance(item, Portfolio)
        )
    )
    if query.portfolio_id is None:
        return available
    if query.portfolio_id not in available:
        raise VitrineAttentionError(
            "vitrine_attention.portfolio_not_found",
            "The exact Portfolio does not exist in current Vitrine state.",
        )
    return (query.portfolio_id,)


def evaluate_vitrine_attention(
    workspace_root: str | Path,
    query: VitrineAttentionQuery | None = None,
) -> VitrineAttentionReport:
    """Evaluate current Vitrine-owned attention without writing or producer reads."""

    request = VitrineAttentionQuery() if query is None else query
    if not isinstance(request, VitrineAttentionQuery):
        raise VitrineAttentionError(
            "vitrine_attention.invalid_query",
            "query must be VitrineAttentionQuery.",
        )
    root = Path(workspace_root)
    try:
        current, records = load_current_records_with_state(root)
    except (VitrineStorageNotFoundError, VitrineStorageError, OSError):
        return _unavailable_report()

    portfolio_ids = _portfolio_ids(records, request)
    state = project_curation_state(records)
    facts: list[_AttentionFact] = []
    notices: list[VitrineAttentionNotice] = []

    for portfolio_id in portfolio_ids:
        try:
            inbox = list_candidate_inbox(
                root,
                CandidateInboxQuery(
                    portfolio_id=portfolio_id,
                    limit=MAX_CANDIDATE_INBOX_RESULTS,
                ),
            )
        except CandidateInboxError:
            if not notices:
                notices.append(_partial_notice())
        else:
            if inbox.observed_state_revision != current.state_revision:
                return _unavailable_report()
            if inbox.truncated and not notices:
                notices.append(_partial_notice())
            facts.extend(_candidate_facts(inbox.items, state, records))
            facts.extend(_proposal_facts(inbox.items, state))

    for portfolio_id in portfolio_ids:
        try:
            preparation = prepare_working_composition(root, portfolio_id)
        except CurationWorkflowError:
            if not notices:
                notices.append(_partial_notice())
            continue
        if preparation.observed_state_revision != current.state_revision:
            return _unavailable_report()
        facts.extend(_working_composition_facts(preparation))

    snapshot_facts, snapshot_partial = _snapshot_facts(
        root,
        project_snapshot_state(records),
        portfolio_ids,
        observed_state_revision=current.state_revision,
        include_unscoped=request.portfolio_id is None,
    )
    facts.extend(snapshot_facts)
    if snapshot_partial and not notices:
        notices.append(_partial_notice())

    try:
        if load_current_state(root).state_revision != current.state_revision:
            return _unavailable_report()
    except (VitrineStorageNotFoundError, VitrineStorageError, OSError):
        return _unavailable_report()

    return VitrineAttentionReport(
        contract_version=VITRINE_ATTENTION_CONTRACT_VERSION,
        evaluation="evaluated",
        observed_state_revision=current.state_revision,
        summaries=_aggregate_facts(tuple(facts)),
        notices=tuple(notices),
    )


__all__ = [
    "VITRINE_ATTENTION_ACTION_IDS",
    "VITRINE_ATTENTION_CLASSES",
    "VITRINE_ATTENTION_CODES",
    "VITRINE_ATTENTION_CONTRACT_VERSION",
    "VITRINE_ATTENTION_EVALUATIONS",
    "VITRINE_ATTENTION_NOTICE_CODES",
    "VitrineAttentionError",
    "VitrineAttentionNotice",
    "VitrineAttentionQuery",
    "VitrineAttentionReport",
    "VitrineAttentionSummary",
    "VitrineNextActionRef",
    "evaluate_vitrine_attention",
]
