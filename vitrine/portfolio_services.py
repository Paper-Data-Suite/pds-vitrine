"""Presentation-independent Portfolio creation and compact reads."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from vitrine.curation_state import project_curation_state
from vitrine.identity_state import collect_identity_state_issues, project_identity_state
from vitrine.models import ActorAttribution, Portfolio, VitrineRecord
from vitrine.profile_state import collect_profile_state_issues, project_profile_state
from vitrine.snapshot_state import collect_snapshot_state_issues, project_snapshot_state
from vitrine.storage import (
    VitrineStorageConflictError,
    VitrineStorageNotFoundError,
    commit_record_batch,
    load_current_records,
    load_current_state,
)

Clock = Callable[[], datetime]
IdFactory = Callable[[str], str]


class PortfolioWorkflowError(ValueError):
    """Expected Portfolio workflow failure with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class PortfolioMutationResult:
    portfolio: Portfolio
    state_revision: int
    disposition: str = "created"


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    portfolio_id: str
    title_snapshot: str | None
    portfolio_subject_id: str
    subject_display_label: str | None
    profile_binding_id: str | None
    profile_revision: int | None
    candidate_count: int
    active_selection_count: int
    current_composition_revision: int | None
    snapshot_series_count: int
    current_edition_count: int


@dataclass(frozen=True, slots=True)
class PortfolioDetail:
    summary: PortfolioSummary
    portfolio: Portfolio


def _clock() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    # Random opaque identity: no title, display name, or student identifier is encoded.
    return f"{prefix}_{uuid.uuid4().hex}"


def _records_and_revision(
    workspace_root: str | Path,
) -> tuple[tuple[VitrineRecord, ...], int | None]:
    try:
        current = load_current_state(workspace_root)
    except VitrineStorageNotFoundError:
        return (), None
    return load_current_records(workspace_root), current.state_revision


def observe_portfolio_state_revision(workspace_root: str | Path) -> int | None:
    """Observe one exact canonical Vitrine state revision."""
    return _records_and_revision(workspace_root)[1]


def create_portfolio(
    workspace_root: str | Path,
    *,
    portfolio_subject_id: str,
    created_by: ActorAttribution,
    expected_state_revision: int | None,
    title_snapshot: str | None = None,
    description_snapshot: str | None = None,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> PortfolioMutationResult:
    """Create a Portfolio for one exact, current Portfolio Subject."""
    records, actual = _records_and_revision(workspace_root)
    if actual != expected_state_revision:
        raise PortfolioWorkflowError(
            "state_conflict",
            f"Vitrine state changed: expected {expected_state_revision!r}, found {actual!r}.",
        )
    identity = project_identity_state(records)
    issues = collect_identity_state_issues(identity)
    if issues:
        raise PortfolioWorkflowError(
            "identity_state_invalid", "Portfolio Subject identity state is invalid."
        )
    subject = next(
        (
            item
            for item in identity.subjects
            if item.portfolio_subject_id == portfolio_subject_id
        ),
        None,
    )
    if subject is None:
        raise PortfolioWorkflowError(
            "subject_not_found", "Portfolio Subject not found."
        )
    status = identity.subject_status(portfolio_subject_id)
    if status != "active":
        raise PortfolioWorkflowError(
            "subject_historical", f"Portfolio Subject is historical ({status})."
        )
    portfolio = Portfolio(
        portfolio_id=id_factory("portfolio"),
        portfolio_subject_id=subject.portfolio_subject_id,
        created_at=clock(),
        created_by=created_by,
        title_snapshot=title_snapshot,
        description_snapshot=description_snapshot,
    )
    try:
        commit = commit_record_batch(
            workspace_root,
            (portfolio,),
            expected_state_revision=expected_state_revision,
        )
    except VitrineStorageConflictError as error:
        raise PortfolioWorkflowError("state_conflict", str(error)) from error
    return PortfolioMutationResult(portfolio, commit.state_revision)


def _summaries(records: tuple[VitrineRecord, ...]) -> tuple[PortfolioSummary, ...]:
    identity = project_identity_state(records)
    profile = project_profile_state(records)
    curation = project_curation_state(records)
    snapshot = project_snapshot_state(records)
    if collect_profile_state_issues(profile):
        raise PortfolioWorkflowError(
            "profile_state_invalid", "Portfolio Profile state is invalid."
        )
    if collect_snapshot_state_issues(snapshot):
        raise PortfolioWorkflowError(
            "snapshot_state_invalid", "Snapshot state is invalid."
        )
    subjects = {item.portfolio_subject_id: item for item in identity.subjects}
    result: list[PortfolioSummary] = []
    for portfolio in sorted(identity.portfolios, key=lambda item: item.portfolio_id):
        binding = profile.active_binding(portfolio.portfolio_id)
        candidates = tuple(
            x for x in curation.candidates if x.portfolio_id == portfolio.portfolio_id
        )
        active = (
            ()
            if binding is None
            else curation.active_selections(
                portfolio_id=portfolio.portfolio_id,
                profile_binding_id=binding.profile_binding_id,
            )
        )
        composition = (
            None
            if binding is None
            else curation.current_composition(
                portfolio.portfolio_id, binding.profile_binding_id
            )
        )
        series = tuple(
            x for x in snapshot.series if x.portfolio_id == portfolio.portfolio_id
        )
        current_editions = tuple(
            edition
            for item in series
            if (edition := snapshot.current_edition(item.snapshot_series_id))
            is not None
        )
        subject = subjects.get(portfolio.portfolio_subject_id)
        result.append(
            PortfolioSummary(
                portfolio.portfolio_id,
                portfolio.title_snapshot,
                portfolio.portfolio_subject_id,
                None if subject is None else subject.display_name_snapshot,
                None if binding is None else binding.profile_binding_id,
                None if binding is None else binding.profile_revision.profile_revision,
                len(candidates),
                len(active),
                None if composition is None else composition.composition_revision,
                len(series),
                len(current_editions),
            )
        )
    return tuple(result)


def list_portfolios(workspace_root: str | Path) -> tuple[PortfolioSummary, ...]:
    return _summaries(_records_and_revision(workspace_root)[0])


def show_portfolio(workspace_root: str | Path, portfolio_id: str) -> PortfolioDetail:
    records, _ = _records_and_revision(workspace_root)
    portfolio = next(
        (
            item
            for item in records
            if isinstance(item, Portfolio) and item.portfolio_id == portfolio_id
        ),
        None,
    )
    if portfolio is None:
        raise PortfolioWorkflowError("portfolio_not_found", "Portfolio not found.")
    summary = next(
        item for item in _summaries(records) if item.portfolio_id == portfolio_id
    )
    return PortfolioDetail(summary, portfolio)


__all__ = [
    "PortfolioDetail",
    "PortfolioMutationResult",
    "PortfolioSummary",
    "PortfolioWorkflowError",
    "create_portfolio",
    "list_portfolios",
    "observe_portfolio_state_revision",
    "show_portfolio",
]
