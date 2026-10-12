"""Derived completion state for one exact Vitrine Portfolio.

Issue #103 Slice 1 introduces a read-only completion projection. It composes
the existing Working Composition and completed-Portfolio history contracts and
derives bounded canonical Snapshot recovery signals. It does not mutate
curation, build Snapshots, advance Current Pointers, create Presentations, or
change Attention behavior.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vitrine.completed_portfolio import (
    COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
    CompletedPortfolioEdition,
    CompletedPortfolioHistory,
    CompletedPortfolioHistoryError,
    CompletedPortfolioSeries,
    project_completed_portfolio_history,
)
from vitrine.curation_services import CurationWorkflowError
from vitrine.models.snapshot_workflow import (
    SnapshotBuildAttempt,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotSeries,
)
from vitrine.snapshot_state import SnapshotState, project_snapshot_state
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
)
from vitrine.working_composition import (
    WORKING_COMPOSITION_CONTRACT_VERSION,
    WorkingCompositionPreparation,
    prepare_working_composition,
)

PORTFOLIO_COMPLETION_CONTRACT_VERSION: Final[str] = "vitrine_portfolio_completion_v1"

PORTFOLIO_COMPLETION_STATES: Final[frozenset[str]] = frozenset(
    {
        "required_work",
        "ready_to_build",
        "complete",
        "update_ready",
        "recovery_or_integrity_blocked",
    }
)

PORTFOLIO_COMPLETION_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "portfolio_completion.invalid_request",
        "portfolio_completion.context_not_found",
        "portfolio_completion.state_changed",
        "portfolio_completion.history_inconsistent",
        "portfolio_completion.canonical_state_inconsistent",
    }
)


class PortfolioCompletionError(RuntimeError):
    """Stable failure for one unsafe completion projection."""

    def __init__(self, code: str, message: str) -> None:
        if code not in PORTFOLIO_COMPLETION_ERROR_CODES:
            raise ValueError(f"unsupported Portfolio completion error code: {code}")
        self.code = code
        super().__init__(message)


def _normalized_codes(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    items = tuple(values)
    if any(not isinstance(item, str) or not item for item in items):
        raise ValueError(f"{field_name} must contain nonempty strings.")
    return tuple(sorted(set(items)))


@dataclass(frozen=True, slots=True)
class PortfolioCompletionOperationalStatus:
    """Canonical operational blockers independent of completion/history status."""

    recovery_reason_codes: tuple[str, ...] = ()
    integrity_reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "recovery_reason_codes",
            _normalized_codes(
                self.recovery_reason_codes,
                "recovery_reason_codes",
            ),
        )
        object.__setattr__(
            self,
            "integrity_reason_codes",
            _normalized_codes(
                self.integrity_reason_codes,
                "integrity_reason_codes",
            ),
        )

    @property
    def blocked(self) -> bool:
        return bool(self.recovery_reason_codes or self.integrity_reason_codes)


@dataclass(frozen=True, slots=True)
class PortfolioCompletionEditionSummary:
    snapshot_series_id: str
    edition_number: int
    audience_context_id: str
    presentation_class: str
    is_current: bool
    export_count: int
    presentation_count: int
    student_presentation_available: bool


@dataclass(frozen=True, slots=True)
class PortfolioCompletionProjection:
    contract_version: str
    observed_state_revision: int
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision_id: str
    profile_revision_number: int
    current_composition_revision: int | None
    predicted_composition_revision: int
    working_composition_disposition: str
    state: str
    required_reason_codes: tuple[str, ...]
    recovery_reason_codes: tuple[str, ...]
    integrity_reason_codes: tuple[str, ...]
    exact_current_editions: tuple[PortfolioCompletionEditionSummary, ...]
    historical_completed_edition_count: int
    student_presentation_missing: bool

    def __post_init__(self) -> None:
        if self.contract_version != PORTFOLIO_COMPLETION_CONTRACT_VERSION:
            raise ValueError("unsupported Portfolio completion contract version")
        if self.state not in PORTFOLIO_COMPLETION_STATES:
            raise ValueError("unsupported Portfolio completion state")

    @property
    def has_required_work(self) -> bool:
        return self.state == "required_work"

    @property
    def is_complete(self) -> bool:
        return self.state == "complete"

    @property
    def can_build_current(self) -> bool:
        return self.state in {"ready_to_build", "update_ready"}


def _required_work_reason_codes(
    working: WorkingCompositionPreparation,
) -> tuple[str, ...]:
    reasons: set[str] = set()

    if working.disposition != "reuse_exact_current":
        reasons.add(f"working_composition_{working.disposition}")

    if working.unplaced_selection_ids:
        reasons.add("selection_unplaced")

    if any(item.unresolved_condition_codes for item in working.selections):
        reasons.add("selection_condition_unresolved")

    for requirement in working.requirements:
        if requirement.status in {"unresolved_missing", "conditional_unresolved"}:
            reasons.add(f"requirement_{requirement.status}")
        elif (
            requirement.status == "not_machine_evaluable"
            and requirement.obligation == "required"
        ):
            reasons.add("required_requirement_human_review")

    if any(item.requires_attention for item in working.reviews):
        reasons.add("curation_review_follow_up")

    if working.payload.unresolved_obligation_codes:
        reasons.add("composition_obligation_unresolved")

    return tuple(sorted(reasons))


def _edition_matches_exact_current(
    edition: CompletedPortfolioEdition,
    working: WorkingCompositionPreparation,
) -> bool:
    return (
        working.disposition == "reuse_exact_current"
        and working.current_composition_revision is not None
        and edition.portfolio_id == working.portfolio_id
        and edition.portfolio_subject_id == working.portfolio_subject_id
        and edition.profile_binding_id == working.profile_binding_id
        and edition.profile_revision.portfolio_profile_id
        == working.profile_revision_id
        and edition.profile_revision.profile_revision
        == working.profile_revision_number
        and edition.composition_revision == working.current_composition_revision
    )


def _edition_summary(
    series: CompletedPortfolioSeries,
    edition: CompletedPortfolioEdition,
) -> PortfolioCompletionEditionSummary:
    student_presentations = tuple(
        item
        for item in edition.presentations
        if item.presentation_class == "student_portfolio"
    )
    return PortfolioCompletionEditionSummary(
        snapshot_series_id=edition.snapshot_series_id,
        edition_number=edition.edition_number,
        audience_context_id=edition.audience_context_id,
        presentation_class=series.presentation_class,
        is_current=edition.is_current,
        export_count=len(edition.exports),
        presentation_count=len(edition.presentations),
        student_presentation_available=bool(student_presentations),
    )


def project_portfolio_completion(
    working: WorkingCompositionPreparation,
    history: CompletedPortfolioHistory,
    *,
    operational_status: PortfolioCompletionOperationalStatus | None = None,
) -> PortfolioCompletionProjection:
    """Project completion from existing authoritative read models only."""

    if not isinstance(working, WorkingCompositionPreparation):
        raise PortfolioCompletionError(
            "portfolio_completion.invalid_request",
            "working must be a WorkingCompositionPreparation.",
        )
    if not isinstance(history, CompletedPortfolioHistory):
        raise PortfolioCompletionError(
            "portfolio_completion.invalid_request",
            "history must be a CompletedPortfolioHistory.",
        )
    if working.contract_version != WORKING_COMPOSITION_CONTRACT_VERSION:
        raise PortfolioCompletionError(
            "portfolio_completion.invalid_request",
            "Working Composition contract is unsupported.",
        )
    if history.contract_version != COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION:
        raise PortfolioCompletionError(
            "portfolio_completion.invalid_request",
            "Completed Portfolio history contract is unsupported.",
        )
    if (
        history.portfolio_id != working.portfolio_id
        or history.portfolio_subject_id != working.portfolio_subject_id
    ):
        raise PortfolioCompletionError(
            "portfolio_completion.history_inconsistent",
            "Completed history does not describe the exact Working Portfolio.",
        )

    operational = operational_status or PortfolioCompletionOperationalStatus()
    required_reasons = _required_work_reason_codes(working)

    exact_current: list[PortfolioCompletionEditionSummary] = []
    historical_completed_count = 0
    missing_student_presentation = False

    for series in history.series:
        for edition in series.editions:
            technical_complete = bool(edition.exports)
            if technical_complete:
                historical_completed_count += 1
            if not _edition_matches_exact_current(edition, working):
                continue
            if not technical_complete:
                continue
            summary = _edition_summary(series, edition)
            exact_current.append(summary)
            if (
                series.presentation_class == "student_portfolio"
                and not summary.student_presentation_available
            ):
                missing_student_presentation = True

    exact_current_tuple = tuple(
        sorted(
            exact_current,
            key=lambda item: (item.snapshot_series_id, item.edition_number),
        )
    )

    if operational.blocked:
        state = "recovery_or_integrity_blocked"
    elif required_reasons:
        state = "required_work"
    elif exact_current_tuple:
        state = "complete"
    elif historical_completed_count:
        state = "update_ready"
    else:
        state = "ready_to_build"

    return PortfolioCompletionProjection(
        contract_version=PORTFOLIO_COMPLETION_CONTRACT_VERSION,
        observed_state_revision=working.observed_state_revision,
        portfolio_id=working.portfolio_id,
        portfolio_subject_id=working.portfolio_subject_id,
        profile_binding_id=working.profile_binding_id,
        profile_revision_id=working.profile_revision_id,
        profile_revision_number=working.profile_revision_number,
        current_composition_revision=working.current_composition_revision,
        predicted_composition_revision=working.predicted_composition_revision,
        working_composition_disposition=working.disposition,
        state=state,
        required_reason_codes=required_reasons,
        recovery_reason_codes=operational.recovery_reason_codes,
        integrity_reason_codes=operational.integrity_reason_codes,
        exact_current_editions=exact_current_tuple,
        historical_completed_edition_count=historical_completed_count,
        student_presentation_missing=missing_student_presentation,
    )


def _series_heads(
    state: SnapshotState,
    portfolio_id: str,
) -> tuple[SnapshotSeries, ...]:
    values = tuple(item for item in state.series if item.portfolio_id == portfolio_id)
    predecessor_ids = {
        item.predecessor_series_id
        for item in values
        if item.predecessor_series_id is not None
    }
    return tuple(
        item for item in values if item.snapshot_series_id not in predecessor_ids
    )


def _request_heads(
    state: SnapshotState,
    snapshot_series_id: str,
) -> tuple[SnapshotBuildRequest, ...]:
    values = tuple(
        item
        for item in state.requests
        if item.snapshot_series_id == snapshot_series_id
    )
    predecessor_ids = {
        item.predecessor_request_id
        for item in values
        if item.predecessor_request_id is not None
    }
    return tuple(
        item
        for item in values
        if item.snapshot_build_request_id not in predecessor_ids
    )


def _plan_heads(
    state: SnapshotState,
    request_id: str,
) -> tuple[SnapshotBuildPlan, ...]:
    values = tuple(
        item
        for item in state.plans
        if item.snapshot_build_request_id == request_id
    )
    predecessor_ids = {
        item.predecessor_plan_id
        for item in values
        if item.predecessor_plan_id is not None
    }
    return tuple(
        item
        for item in values
        if item.snapshot_build_plan_id not in predecessor_ids
    )


def _current_attempt(
    state: SnapshotState,
    plan_id: str,
) -> tuple[SnapshotBuildAttempt | None, bool]:
    attempts = tuple(
        item
        for item in state.attempts
        if item.snapshot_build_plan_id == plan_id
    )
    if not attempts:
        return None, False
    numbers = [item.attempt_number for item in attempts]
    if len(set(numbers)) != len(numbers):
        return None, True
    return max(attempts, key=lambda item: item.attempt_number), False


def _matching_export_head_count(
    state: SnapshotState,
    *,
    snapshot_series_id: str,
    edition_number: int,
    export_format: str,
    export_contract_version: str,
    configuration_digest: object,
) -> int:
    values = tuple(
        item
        for item in state.export_artifacts
        if item.snapshot_edition.snapshot_series_id == snapshot_series_id
        and item.snapshot_edition.edition_number == edition_number
        and item.export_format == export_format
        and item.export_contract_version == export_contract_version
        and item.configuration_digest == configuration_digest
    )
    predecessor_ids = {
        item.predecessor_export_artifact_id
        for item in values
        if item.predecessor_export_artifact_id is not None
    }
    return sum(
        1
        for item in values
        if item.snapshot_export_artifact_id not in predecessor_ids
    )


def project_portfolio_completion_operational_status(
    records: Iterable[object],
    *,
    portfolio_id: str,
) -> PortfolioCompletionOperationalStatus:
    """Derive bounded canonical recovery/integrity signals without filesystem I/O."""

    if not isinstance(portfolio_id, str) or not portfolio_id.strip():
        raise PortfolioCompletionError(
            "portfolio_completion.invalid_request",
            "portfolio_id must be nonempty text.",
        )

    state = project_snapshot_state(records)
    recovery: set[str] = set()
    integrity: set[str] = set()

    for series in _series_heads(state, portfolio_id):
        request_heads = _request_heads(state, series.snapshot_series_id)
        if len(request_heads) > 1:
            integrity.add("snapshot_request_history_conflict")
            continue
        if not request_heads:
            continue
        request = request_heads[0]

        plan_heads = _plan_heads(state, request.snapshot_build_request_id)
        if len(plan_heads) > 1:
            integrity.add("snapshot_plan_history_conflict")
            continue
        if not plan_heads:
            continue
        plan = plan_heads[0]

        attempt, attempt_conflict = _current_attempt(
            state,
            plan.snapshot_build_plan_id,
        )
        if attempt_conflict:
            integrity.add("snapshot_attempt_history_conflict")
            continue
        if attempt is None:
            continue

        matching_results = tuple(
            item
            for item in state.attempt_results
            if item.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id
        )
        if len(matching_results) > 1:
            integrity.add("snapshot_attempt_result_conflict")
            continue
        if not matching_results:
            recovery.add("snapshot_attempt_incomplete")
            continue
        result = matching_results[0]

        if result.terminal_outcome == "failed":
            recovery.add("snapshot_build_failed")
            continue
        if result.terminal_outcome == "durability_uncertain":
            recovery.add("snapshot_durability_uncertain")
            integrity.add("snapshot_durability_uncertain")
            continue
        if result.terminal_outcome not in {"sealed", "partial_success_after_seal"}:
            continue

        edition = result.sealed_snapshot_edition
        if edition is None:
            integrity.add("snapshot_sealed_result_missing_edition")
            continue

        for export_plan in plan.export_plans:
            head_count = _matching_export_head_count(
                state,
                snapshot_series_id=edition.snapshot_series_id,
                edition_number=edition.edition_number,
                export_format=export_plan.export_format,
                export_contract_version=export_plan.export_contract_version,
                configuration_digest=export_plan.configuration_digest,
            )
            if head_count == 0:
                recovery.add("snapshot_export_missing")
            elif head_count > 1:
                integrity.add("snapshot_export_head_conflict")

    return PortfolioCompletionOperationalStatus(
        recovery_reason_codes=tuple(recovery),
        integrity_reason_codes=tuple(integrity),
    )


def prepare_portfolio_completion(
    workspace_root: str | Path,
    portfolio_id: str,
) -> PortfolioCompletionProjection:
    """Read one exact current Portfolio and derive completion without writes."""

    if not isinstance(portfolio_id, str) or not portfolio_id.strip():
        raise PortfolioCompletionError(
            "portfolio_completion.invalid_request",
            "portfolio_id must be nonempty text.",
        )

    try:
        working = prepare_working_composition(workspace_root, portfolio_id)
    except CurationWorkflowError as error:
        raise PortfolioCompletionError(
            "portfolio_completion.context_not_found",
            "Current Portfolio composition could not be prepared safely.",
        ) from error

    try:
        current, records = load_current_records_with_state(workspace_root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise PortfolioCompletionError(
            "portfolio_completion.context_not_found",
            "Vitrine canonical state is unavailable for completion projection.",
        ) from error

    if current.state_revision != working.observed_state_revision:
        raise PortfolioCompletionError(
            "portfolio_completion.state_changed",
            "Vitrine state changed during completion projection.",
        )

    try:
        history = project_completed_portfolio_history(
            records,
            portfolio_id=portfolio_id,
        )
    except CompletedPortfolioHistoryError as error:
        raise PortfolioCompletionError(
            "portfolio_completion.history_inconsistent",
            "Completed Portfolio history could not be projected safely.",
        ) from error

    operational = project_portfolio_completion_operational_status(
        records,
        portfolio_id=portfolio_id,
    )
    return project_portfolio_completion(
        working,
        history,
        operational_status=operational,
    )


__all__ = [
    "PORTFOLIO_COMPLETION_CONTRACT_VERSION",
    "PORTFOLIO_COMPLETION_ERROR_CODES",
    "PORTFOLIO_COMPLETION_STATES",
    "PortfolioCompletionEditionSummary",
    "PortfolioCompletionError",
    "PortfolioCompletionOperationalStatus",
    "PortfolioCompletionProjection",
    "prepare_portfolio_completion",
    "project_portfolio_completion",
    "project_portfolio_completion_operational_status",
]
