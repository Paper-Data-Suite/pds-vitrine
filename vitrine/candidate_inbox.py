"""Read-only teacher Candidate inbox projection over canonical Vitrine state."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Final

from pds_core.publication_storage import (
    PublicationStorageError,
    list_publication_record_set,
)
from pds_core.registry_services import (
    RegistryServiceError,
    get_canonical_publication_record,
    get_canonical_publication_withdrawal,
)

from vitrine.candidate_services import CANDIDATE_EVALUATOR_CONTRACT_VERSION
from vitrine.candidate_state import (
    CandidateState,
    project_candidate_state,
)
from vitrine.curation_state import CurationState, project_curation_state
from vitrine.identity_state import (
    PortfolioSubjectIdentityState,
    project_identity_state,
)
from vitrine.models import (
    CandidateCurrentEvaluationPointerRevision,
    CandidateEvaluation,
    Portfolio,
    PortfolioCandidate,
    PortfolioProfileRevision,
    PortfolioSelection,
    PortfolioSubject,
    ProfileRevisionRef,
    VitrineRecord,
)
from vitrine.models.candidates import (
    CANDIDATE_CONDITION_STATES,
    EVALUATION_OUTCOMES,
    CandidateSourceEndpoint,
)
from vitrine.models.common import (
    require_aware_datetime,
    require_bool,
    require_enum,
    require_identifier,
    require_lower_identifier,
    require_positive_int,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.models.profiles import PROFILE_PURPOSE_KINDS
from vitrine.profile_state import (
    PortfolioProfileState,
    project_profile_state,
)
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
)

CANDIDATE_INBOX_CONTRACT_VERSION: Final[str] = "vitrine_candidate_inbox_v1"
CANDIDATE_INBOX_SELECTED_STATES: Final[frozenset[str]] = frozenset(
    {"selected", "unselected", "historical_only"}
)
CANDIDATE_INBOX_STALE_STATES: Final[frozenset[str]] = frozenset(
    {"current", "stale", "unresolved"}
)
CANDIDATE_INBOX_CONDITION_ATTENTION_CODES: Final[dict[str, str]] = {
    condition: f"candidate_inbox.{condition}"
    for condition in CANDIDATE_CONDITION_STATES
    if condition != "ready_for_consideration"
}
CANDIDATE_INBOX_CURRENT_RESOLUTIONS: Final[frozenset[str]] = frozenset(
    {"explicit", "legacy", "evaluation_only", "unresolved"}
)
VISIBLE_EVALUATION_OUTCOMES: Final[frozenset[str]] = EVALUATION_OUTCOMES - {
    "suppressed"
}
MAX_CANDIDATE_INBOX_RESULTS: Final[int] = 500

CANDIDATE_INBOX_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "candidate_inbox.invalid_query",
        "candidate_inbox.entry_not_found",
        "candidate_inbox.state_invalid",
    }
)


class CandidateInboxError(RuntimeError):
    """Expected read-only Candidate inbox failure with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        if code not in CANDIDATE_INBOX_ERROR_CODES:
            raise ValueError(f"unsupported Candidate inbox error code: {code}")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateInboxQuery:
    portfolio_id: str | None = None
    portfolio_subject_id: str | None = None
    profile_purpose: str | None = None
    evaluation_outcomes: tuple[str, ...] = ()
    candidate_conditions: tuple[str, ...] = ()
    attention_only: bool = False
    stale_only: bool = False
    selected_state: str | None = None
    producer_module_id: str | None = None
    evaluated_since: datetime | None = None
    limit: int = 100

    def __post_init__(self) -> None:
        try:
            for name in ("portfolio_id", "portfolio_subject_id"):
                value = getattr(self, name)
                if value is not None:
                    object.__setattr__(
                        self,
                        name,
                        require_identifier(value, name),
                    )
            if self.profile_purpose is not None:
                object.__setattr__(
                    self,
                    "profile_purpose",
                    require_enum(
                        self.profile_purpose,
                        "profile_purpose",
                        PROFILE_PURPOSE_KINDS,
                    ),
                )
            outcomes = tuple(self.evaluation_outcomes)
            if len(set(outcomes)) != len(outcomes):
                raise VitrineModelValidationError(
                    "evaluation_outcomes must not contain duplicates."
                )
            for outcome in outcomes:
                require_enum(
                    outcome,
                    "evaluation_outcomes",
                    VISIBLE_EVALUATION_OUTCOMES,
                )
            object.__setattr__(
                self,
                "evaluation_outcomes",
                outcomes,
            )
            conditions = tuple(self.candidate_conditions)
            if len(set(conditions)) != len(conditions):
                raise VitrineModelValidationError(
                    "candidate_conditions must not contain duplicates."
                )
            for condition in conditions:
                require_enum(
                    condition,
                    "candidate_conditions",
                    CANDIDATE_CONDITION_STATES,
                )
            object.__setattr__(
                self,
                "candidate_conditions",
                conditions,
            )
            object.__setattr__(
                self,
                "attention_only",
                require_bool(self.attention_only, "attention_only"),
            )
            object.__setattr__(
                self,
                "stale_only",
                require_bool(self.stale_only, "stale_only"),
            )
            if self.selected_state is not None:
                object.__setattr__(
                    self,
                    "selected_state",
                    require_enum(
                        self.selected_state,
                        "selected_state",
                        CANDIDATE_INBOX_SELECTED_STATES,
                    ),
                )
            if self.producer_module_id is not None:
                object.__setattr__(
                    self,
                    "producer_module_id",
                    require_lower_identifier(
                        self.producer_module_id,
                        "producer_module_id",
                    ),
                )
            if self.evaluated_since is not None:
                object.__setattr__(
                    self,
                    "evaluated_since",
                    require_aware_datetime(
                        self.evaluated_since,
                        "evaluated_since",
                    ),
                )
            limit = require_positive_int(self.limit, "limit")
            if limit > MAX_CANDIDATE_INBOX_RESULTS:
                raise VitrineModelValidationError(
                    "limit exceeds the Candidate inbox maximum."
                )
            object.__setattr__(self, "limit", limit)
        except VitrineModelValidationError as error:
            raise CandidateInboxError(
                "candidate_inbox.invalid_query",
                "Candidate inbox query is invalid.",
            ) from error


@dataclass(frozen=True, slots=True)
class CandidateInboxItem:
    contract_version: str
    entry_id: str
    candidate_id: str | None
    current_evaluation_id: str | None
    current_resolution: str
    portfolio_id: str
    portfolio_label: str
    portfolio_subject_id: str
    subject_label: str
    profile_binding_id: str
    portfolio_profile_id: str
    profile_revision: int
    profile_label: str
    profile_purpose: str
    source_display_label: str
    producer_module_id: str | None
    evaluation_outcome: str | None
    candidate_condition: str | None
    stale_state: str | None
    stale_reason_codes: tuple[str, ...]
    attention_needed: bool
    attention_reason_codes: tuple[str, ...]
    selected_state: str
    active_selection_ids: tuple[str, ...]
    historical_selection_ids: tuple[str, ...]
    evaluated_at: datetime | None
    eligible_section_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateInboxResult:
    contract_version: str
    observed_state_revision: int
    matched_count: int
    truncated: bool
    items: tuple[CandidateInboxItem, ...]


@dataclass(frozen=True, slots=True)
class CandidateInboxDetail:
    contract_version: str
    observed_state_revision: int
    item: CandidateInboxItem
    evaluation: CandidateEvaluation | None
    candidate: PortfolioCandidate | None
    profile_revision: PortfolioProfileRevision
    evaluation_history: tuple[CandidateEvaluation, ...]
    pointer_history: tuple[CandidateCurrentEvaluationPointerRevision, ...]
    selection_history: tuple[PortfolioSelection, ...]


@dataclass(frozen=True, slots=True)
class _ProjectionContext:
    records: tuple[VitrineRecord, ...]
    candidate_state: CandidateState
    curation_state: CurationState
    profile_state: PortfolioProfileState
    identity_state: PortfolioSubjectIdentityState
    portfolios: dict[str, Portfolio]
    subjects: dict[str, PortfolioSubject]
    evaluations: dict[str, CandidateEvaluation]


def _context(records: tuple[VitrineRecord, ...]) -> _ProjectionContext:
    return _ProjectionContext(
        records=records,
        candidate_state=project_candidate_state(records),
        curation_state=project_curation_state(records),
        profile_state=project_profile_state(records),
        identity_state=project_identity_state(records),
        portfolios={
            item.portfolio_id: item for item in records if isinstance(item, Portfolio)
        },
        subjects={
            item.portfolio_subject_id: item
            for item in records
            if isinstance(item, PortfolioSubject)
        },
        evaluations={
            item.candidate_evaluation_id: item
            for item in records
            if isinstance(item, CandidateEvaluation)
        },
    )


def _profile_for(
    context: _ProjectionContext,
    reference: ProfileRevisionRef,
) -> PortfolioProfileRevision:
    profile = context.profile_state.revision(reference)
    if profile is None:
        raise CandidateInboxError(
            "candidate_inbox.state_invalid",
            "Exact Candidate Profile Revision is unavailable.",
        )
    return profile


def _portfolio_label(
    context: _ProjectionContext,
    portfolio_id: str,
) -> str:
    portfolio = context.portfolios.get(portfolio_id)
    if portfolio is None:
        raise CandidateInboxError(
            "candidate_inbox.state_invalid",
            "Candidate Portfolio is unavailable.",
        )
    return portfolio.title_snapshot or portfolio.portfolio_id


def _subject_label(
    context: _ProjectionContext,
    portfolio_subject_id: str,
) -> str:
    subject = context.subjects.get(portfolio_subject_id)
    if subject is None:
        raise CandidateInboxError(
            "candidate_inbox.state_invalid",
            "Candidate Portfolio Subject is unavailable.",
        )
    return subject.display_name_snapshot or subject.portfolio_subject_id


def _evaluation_source_label(
    evaluation: CandidateEvaluation,
) -> str:
    endpoint = evaluation.source_endpoint
    if endpoint is None:
        return f"Evaluation {evaluation.candidate_evaluation_id}"
    registration = endpoint.core_publication.registration_snapshot
    if registration is not None:
        return registration.title_snapshot
    artifact = endpoint.source_artifact
    producer = endpoint.producer_source
    if artifact is not None:
        return f"{producer.source_record_kind} — {artifact.artifact_kind}"
    return f"{producer.source_record_kind} — {producer.source_record_id}"


def _producer_module_id(
    evaluation: CandidateEvaluation | None,
    candidate: PortfolioCandidate | None,
) -> str | None:
    if evaluation is not None and evaluation.source_endpoint is not None:
        return evaluation.source_endpoint.producer_source.producer_module_id
    if candidate is not None:
        return candidate.source_endpoint.producer_source.producer_module_id
    return None


def _selection_state(
    context: _ProjectionContext,
    candidate_id: str,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    selections = tuple(
        sorted(
            (
                item
                for item in context.curation_state.selections
                if item.candidate_id == candidate_id
            ),
            key=lambda item: item.selection_id,
        )
    )
    active = tuple(
        item.selection_id
        for item in selections
        if context.curation_state.selection_status(item.selection_id) == "activated"
    )
    historical = tuple(
        item.selection_id for item in selections if item.selection_id not in active
    )
    if active:
        status = "selected"
    elif historical:
        status = "historical_only"
    else:
        status = "unselected"
    return status, active, historical


def _candidate_item(
    context: _ProjectionContext,
    candidate: PortfolioCandidate,
) -> CandidateInboxItem | None:
    resolution = context.candidate_state.resolve_current_evaluation(
        candidate.candidate_id
    )
    evaluation = resolution.evaluation
    if evaluation is not None and evaluation.outcome == "suppressed":
        return None
    profile = _profile_for(context, candidate.profile_revision)
    selection_state, active, historical = _selection_state(
        context,
        candidate.candidate_id,
    )
    return CandidateInboxItem(
        contract_version=CANDIDATE_INBOX_CONTRACT_VERSION,
        entry_id=f"candidate:{candidate.candidate_id}",
        candidate_id=candidate.candidate_id,
        current_evaluation_id=(
            None if evaluation is None else evaluation.candidate_evaluation_id
        ),
        current_resolution=resolution.mode,
        portfolio_id=candidate.portfolio_id,
        portfolio_label=_portfolio_label(
            context,
            candidate.portfolio_id,
        ),
        portfolio_subject_id=candidate.portfolio_subject_id,
        subject_label=_subject_label(
            context,
            candidate.portfolio_subject_id,
        ),
        profile_binding_id=candidate.profile_binding_id,
        portfolio_profile_id=(candidate.profile_revision.portfolio_profile_id),
        profile_revision=candidate.profile_revision.profile_revision,
        profile_label=profile.label,
        profile_purpose=profile.purpose_kind,
        source_display_label=candidate.display_snapshot,
        producer_module_id=_producer_module_id(
            evaluation,
            candidate,
        ),
        evaluation_outcome=(None if evaluation is None else evaluation.outcome),
        candidate_condition=candidate.condition_state,
        stale_state=None,
        stale_reason_codes=(),
        attention_needed=False,
        attention_reason_codes=(),
        selected_state=selection_state,
        active_selection_ids=active,
        historical_selection_ids=historical,
        evaluated_at=(None if evaluation is None else evaluation.evaluated_at),
        eligible_section_ids=(
            candidate.eligible_section_ids
            if evaluation is None
            else evaluation.eligible_section_ids
        ),
    )


def _evaluation_only_item(
    context: _ProjectionContext,
    evaluation: CandidateEvaluation,
) -> CandidateInboxItem | None:
    if evaluation.outcome not in {"ineligible", "unresolved"}:
        return None
    if evaluation.outcome == "suppressed":
        return None
    profile = _profile_for(context, evaluation.profile_revision)
    endpoint = evaluation.source_endpoint
    return CandidateInboxItem(
        contract_version=CANDIDATE_INBOX_CONTRACT_VERSION,
        entry_id=(f"evaluation:{evaluation.candidate_evaluation_id}"),
        candidate_id=None,
        current_evaluation_id=evaluation.candidate_evaluation_id,
        current_resolution="evaluation_only",
        portfolio_id=evaluation.portfolio_id,
        portfolio_label=_portfolio_label(
            context,
            evaluation.portfolio_id,
        ),
        portfolio_subject_id=evaluation.portfolio_subject_id,
        subject_label=_subject_label(
            context,
            evaluation.portfolio_subject_id,
        ),
        profile_binding_id=evaluation.profile_binding_id,
        portfolio_profile_id=(evaluation.profile_revision.portfolio_profile_id),
        profile_revision=evaluation.profile_revision.profile_revision,
        profile_label=profile.label,
        profile_purpose=profile.purpose_kind,
        source_display_label=_evaluation_source_label(evaluation),
        producer_module_id=(
            None if endpoint is None else endpoint.producer_source.producer_module_id
        ),
        evaluation_outcome=evaluation.outcome,
        candidate_condition=None,
        stale_state=None,
        stale_reason_codes=(),
        attention_needed=False,
        attention_reason_codes=(),
        selected_state="unselected",
        active_selection_ids=(),
        historical_selection_ids=(),
        evaluated_at=evaluation.evaluated_at,
        eligible_section_ids=evaluation.eligible_section_ids,
    )


def _evaluation_heads(
    evaluations: tuple[CandidateEvaluation, ...],
) -> tuple[CandidateEvaluation, ...]:
    predecessor_ids = {
        item.predecessor_evaluation_id
        for item in evaluations
        if item.predecessor_evaluation_id is not None
    }
    return tuple(
        sorted(
            (
                item
                for item in evaluations
                if item.candidate_evaluation_id not in predecessor_ids
            ),
            key=lambda item: item.candidate_evaluation_id,
        )
    )


def _visible_items(
    records: tuple[VitrineRecord, ...],
) -> tuple[CandidateInboxItem, ...]:
    context = _context(records)
    items: list[CandidateInboxItem] = []
    represented_evaluation_ids: set[str] = set()

    for candidate in sorted(
        context.candidate_state.candidates,
        key=lambda item: item.candidate_id,
    ):
        item = _candidate_item(context, candidate)
        if item is None:
            continue
        items.append(item)
        if item.current_evaluation_id is not None:
            represented_evaluation_ids.add(item.current_evaluation_id)

    for evaluation in _evaluation_heads(context.candidate_state.evaluations):
        if evaluation.candidate_evaluation_id in represented_evaluation_ids:
            continue
        item = _evaluation_only_item(context, evaluation)
        if item is not None:
            items.append(item)

    return tuple(items)


def _item_source_endpoint(
    context: _ProjectionContext,
    item: CandidateInboxItem,
) -> CandidateSourceEndpoint | None:
    evaluation = (
        None
        if item.current_evaluation_id is None
        else context.evaluations.get(item.current_evaluation_id)
    )
    if evaluation is not None and evaluation.source_endpoint is not None:
        return evaluation.source_endpoint
    if item.candidate_id is None:
        return None
    candidate = next(
        (
            value
            for value in context.candidate_state.candidates
            if value.candidate_id == item.candidate_id
        ),
        None,
    )
    return None if candidate is None else candidate.source_endpoint


def _publication_status(
    workspace_root: str | Path,
    context: _ProjectionContext,
    item: CandidateInboxItem,
) -> tuple[str | None, str | None]:
    endpoint = _item_source_endpoint(context, item)
    if endpoint is None:
        return "unresolved", "candidate_inbox.publication_unavailable"
    reference = endpoint.core_publication
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
            value.supersedes_publication_id
            for value in series
            if value.supersedes_publication_id is not None
        }
        heads = tuple(
            value for value in series if value.publication_id not in superseded
        )
        withdrawal = get_canonical_publication_withdrawal(
            workspace_root, publication.publication_id
        )
    except (RegistryServiceError, PublicationStorageError, OSError):
        return "unresolved", "candidate_inbox.publication_unavailable"
    if withdrawal is not None:
        return "stale", "candidate_inbox.publication_withdrawn"
    if len(heads) != 1:
        return "unresolved", "candidate_inbox.publication_unavailable"
    if heads[0].publication_id != publication.publication_id:
        return "stale", "candidate_inbox.publication_superseded"
    return None, None


def _profile_status(
    context: _ProjectionContext, item: CandidateInboxItem
) -> tuple[str | None, str | None]:
    heads = context.profile_state.active_binding_heads(item.portfolio_id)
    if len(heads) != 1:
        return "unresolved", "candidate_inbox.profile_binding_conflict"
    if heads[0].profile_binding_id != item.profile_binding_id:
        return "stale", "candidate_inbox.profile_binding_changed"
    return None, None


def _subject_status(
    context: _ProjectionContext,
    item: CandidateInboxItem,
) -> tuple[str | None, str | None]:
    endpoint = _item_source_endpoint(context, item)
    if endpoint is None:
        return None, None
    assertions = endpoint.subject_relationship_assertions
    if not assertions:
        return None, None

    links_by_id = {
        value.subject_link_id: value for value in context.identity_state.links
    }
    for assertion in assertions:
        source_link = links_by_id.get(assertion.subject_link_id)
        if source_link is None:
            return "stale", "candidate_inbox.subject_relationship_changed"
        if context.identity_state.link_status(assertion.subject_link_id) != "confirmed":
            return "stale", "candidate_inbox.subject_relationship_changed"

        current_subjects = context.identity_state.current_subjects_for_reference(
            source_link.student_reference
        )
        if len(current_subjects) != 1:
            return "unresolved", "candidate_inbox.subject_relationship_conflict"
        if current_subjects[0] != item.portfolio_subject_id:
            return "stale", "candidate_inbox.subject_relationship_changed"

    return None, None


def _evaluator_status(
    context: _ProjectionContext, item: CandidateInboxItem
) -> tuple[str | None, str | None]:
    if item.current_evaluation_id is None:
        return None, None
    evaluation = context.evaluations.get(item.current_evaluation_id)
    if evaluation is None:
        return "unresolved", "candidate_inbox.current_evaluation_unresolved"
    if evaluation.evaluator_contract_version != CANDIDATE_EVALUATOR_CONTRACT_VERSION:
        return "stale", "candidate_inbox.evaluator_contract_changed"
    return None, None


def _condition_attention_code(condition: str | None) -> str | None:
    if condition is None:
        return None
    return CANDIDATE_INBOX_CONDITION_ATTENTION_CODES.get(condition)


def _enrich_status(
    workspace_root: str | Path,
    context: _ProjectionContext,
    item: CandidateInboxItem,
) -> CandidateInboxItem:
    stale_reasons: list[str] = []
    unresolved_reasons: list[str] = []
    if item.current_resolution == "unresolved":
        unresolved_reasons.append("candidate_inbox.current_evaluation_unresolved")
    for state, reason in (
        _profile_status(context, item),
        _subject_status(context, item),
        _publication_status(workspace_root, context, item),
        _evaluator_status(context, item),
    ):
        if state is None or reason is None:
            continue
        if state == "unresolved":
            unresolved_reasons.append(reason)
        else:
            stale_reasons.append(reason)
    stale_state = (
        "unresolved"
        if unresolved_reasons
        else ("stale" if stale_reasons else "current")
    )
    all_stale_reasons = tuple(sorted(set((*stale_reasons, *unresolved_reasons))))
    attention_reasons: list[str] = []
    if item.evaluation_outcome == "unresolved":
        attention_reasons.append("candidate_inbox.evaluation_unresolved")
    condition_code = _condition_attention_code(item.candidate_condition)
    if condition_code is not None:
        attention_reasons.append(condition_code)
    attention_reasons.extend(all_stale_reasons)
    if item.selected_state == "selected" and stale_state != "current":
        attention_reasons.append("candidate_inbox.selected_candidate_stale")
    bounded = tuple(sorted(set(attention_reasons)))
    return replace(
        item,
        stale_state=stale_state,
        stale_reason_codes=all_stale_reasons,
        attention_needed=bool(bounded),
        attention_reason_codes=bounded,
    )


def _matches_query(
    item: CandidateInboxItem,
    query: CandidateInboxQuery,
) -> bool:
    if query.portfolio_id is not None and item.portfolio_id != query.portfolio_id:
        return False
    if (
        query.portfolio_subject_id is not None
        and item.portfolio_subject_id != query.portfolio_subject_id
    ):
        return False
    if (
        query.profile_purpose is not None
        and item.profile_purpose != query.profile_purpose
    ):
        return False
    if (
        query.evaluation_outcomes
        and item.evaluation_outcome not in query.evaluation_outcomes
    ):
        return False
    if (
        query.candidate_conditions
        and item.candidate_condition not in query.candidate_conditions
    ):
        return False
    if query.attention_only and not item.attention_needed:
        return False
    if query.stale_only and item.stale_state != "stale":
        return False
    if query.selected_state is not None and item.selected_state != query.selected_state:
        return False
    if (
        query.producer_module_id is not None
        and item.producer_module_id != query.producer_module_id
    ):
        return False
    if query.evaluated_since is not None:
        if item.evaluated_at is None or item.evaluated_at < query.evaluated_since:
            return False
    return True


def _ordering_key(
    item: CandidateInboxItem,
) -> tuple[object, ...]:
    evaluated_timestamp = (
        None if item.evaluated_at is None else item.evaluated_at.timestamp()
    )
    return (
        0 if item.attention_needed else 1,
        0
        if item.stale_state == "stale"
        else (1 if item.stale_state == "unresolved" else 2),
        1 if evaluated_timestamp is None else 0,
        0.0 if evaluated_timestamp is None else -evaluated_timestamp,
        item.source_display_label.casefold(),
        item.entry_id,
    )


def project_candidate_inbox(
    records: tuple[VitrineRecord, ...],
    query: CandidateInboxQuery | None = None,
) -> tuple[CandidateInboxItem, ...]:
    """Project matching visible inbox rows without filesystem access."""

    request = CandidateInboxQuery() if query is None else query
    if not isinstance(request, CandidateInboxQuery):
        raise CandidateInboxError(
            "candidate_inbox.invalid_query",
            "query must be CandidateInboxQuery.",
        )
    visible = _visible_items(records)
    return tuple(
        sorted(
            (item for item in visible if _matches_query(item, request)),
            key=_ordering_key,
        )
    )


def _load(
    workspace_root: str | Path,
) -> tuple[int, tuple[VitrineRecord, ...]]:
    try:
        current, records = load_current_records_with_state(workspace_root)
    except (
        VitrineStorageNotFoundError,
        VitrineStorageError,
        OSError,
    ) as error:
        raise CandidateInboxError(
            "candidate_inbox.state_invalid",
            "Canonical Vitrine state is unavailable.",
        ) from error
    return current.state_revision, records


def list_candidate_inbox(
    workspace_root: str | Path,
    query: CandidateInboxQuery | None = None,
) -> CandidateInboxResult:
    """List current visible Candidate/Evaluation rows read-only."""

    request = CandidateInboxQuery() if query is None else query
    if not isinstance(request, CandidateInboxQuery):
        raise CandidateInboxError(
            "candidate_inbox.invalid_query",
            "query must be CandidateInboxQuery.",
        )
    state_revision, records = _load(workspace_root)
    context = _context(records)
    enriched = tuple(
        _enrich_status(workspace_root, context, item)
        for item in _visible_items(records)
    )
    matched = tuple(
        sorted(
            (item for item in enriched if _matches_query(item, request)),
            key=_ordering_key,
        )
    )
    return CandidateInboxResult(
        contract_version=CANDIDATE_INBOX_CONTRACT_VERSION,
        observed_state_revision=state_revision,
        matched_count=len(matched),
        truncated=len(matched) > request.limit,
        items=matched[: request.limit],
    )


def _history_to_evaluation(
    evaluation: CandidateEvaluation,
    evaluations: dict[str, CandidateEvaluation],
) -> tuple[CandidateEvaluation, ...]:
    values: list[CandidateEvaluation] = []
    current: CandidateEvaluation | None = evaluation
    seen: set[str] = set()
    while current is not None:
        if current.candidate_evaluation_id in seen:
            break
        seen.add(current.candidate_evaluation_id)
        values.append(current)
        predecessor_id = current.predecessor_evaluation_id
        current = None if predecessor_id is None else evaluations.get(predecessor_id)
    values.reverse()
    return tuple(values)


def _legacy_candidate_history(
    context: _ProjectionContext,
    candidate: PortfolioCandidate,
) -> tuple[CandidateEvaluation, ...]:
    creation = context.evaluations.get(candidate.candidate_evaluation_id)
    if creation is None:
        return ()
    values = [creation]
    current = creation
    seen = {creation.candidate_evaluation_id}
    while True:
        successors = context.candidate_state.evaluation_successors(
            current.candidate_evaluation_id
        )
        if len(successors) != 1:
            break
        successor = successors[0]
        if successor.candidate_evaluation_id in seen:
            break
        seen.add(successor.candidate_evaluation_id)
        values.append(successor)
        current = successor
    return tuple(values)


def get_candidate_inbox_detail(
    workspace_root: str | Path,
    entry_id: str,
) -> CandidateInboxDetail:
    """Return bounded persisted detail for one visible inbox entry."""

    if not isinstance(entry_id, str) or not entry_id.strip():
        raise CandidateInboxError(
            "candidate_inbox.invalid_query",
            "entry_id must be nonempty text.",
        )
    state_revision, records = _load(workspace_root)
    context = _context(records)
    items = tuple(
        _enrich_status(workspace_root, context, value)
        for value in _visible_items(records)
    )
    item = next(
        (value for value in items if value.entry_id == entry_id),
        None,
    )
    if item is None:
        raise CandidateInboxError(
            "candidate_inbox.entry_not_found",
            "Candidate inbox entry was not found.",
        )

    context = _context(records)
    candidate = (
        None
        if item.candidate_id is None
        else next(
            (
                value
                for value in context.candidate_state.candidates
                if value.candidate_id == item.candidate_id
            ),
            None,
        )
    )
    evaluation = (
        None
        if item.current_evaluation_id is None
        else context.evaluations.get(item.current_evaluation_id)
    )
    profile = _profile_for(
        context,
        ProfileRevisionRef(
            portfolio_profile_id=item.portfolio_profile_id,
            profile_revision=item.profile_revision,
        ),
    )

    if evaluation is not None:
        evaluation_history = _history_to_evaluation(
            evaluation,
            context.evaluations,
        )
    elif candidate is not None:
        evaluation_history = _legacy_candidate_history(
            context,
            candidate,
        )
    else:
        evaluation_history = ()

    pointer_history = (
        ()
        if candidate is None
        else tuple(
            sorted(
                (
                    value
                    for value in context.candidate_state.current_evaluation_pointers
                    if value.candidate_id == candidate.candidate_id
                ),
                key=lambda value: value.pointer_revision,
            )
        )
    )
    selection_history = (
        ()
        if candidate is None
        else tuple(
            sorted(
                (
                    value
                    for value in context.curation_state.selections
                    if value.candidate_id == candidate.candidate_id
                ),
                key=lambda value: (
                    value.selected_at,
                    value.selection_id,
                ),
            )
        )
    )
    return CandidateInboxDetail(
        contract_version=CANDIDATE_INBOX_CONTRACT_VERSION,
        observed_state_revision=state_revision,
        item=item,
        evaluation=evaluation,
        candidate=candidate,
        profile_revision=profile,
        evaluation_history=evaluation_history,
        pointer_history=pointer_history,
        selection_history=selection_history,
    )


__all__ = [
    "CANDIDATE_INBOX_CONDITION_ATTENTION_CODES",
    "CANDIDATE_INBOX_CONTRACT_VERSION",
    "CANDIDATE_INBOX_CURRENT_RESOLUTIONS",
    "CANDIDATE_INBOX_ERROR_CODES",
    "CANDIDATE_INBOX_SELECTED_STATES",
    "CANDIDATE_INBOX_STALE_STATES",
    "MAX_CANDIDATE_INBOX_RESULTS",
    "VISIBLE_EVALUATION_OUTCOMES",
    "CandidateInboxDetail",
    "CandidateInboxError",
    "CandidateInboxItem",
    "CandidateInboxQuery",
    "CandidateInboxResult",
    "get_candidate_inbox_detail",
    "list_candidate_inbox",
    "project_candidate_inbox",
]
