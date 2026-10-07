"""Verification and historical Presentation actions for completed Portfolios.

Issue #102 Slice 4 keeps completed-history verification producer-independent and
reuses the #101 student Portfolio Presentation service for exact historical
Edition/Export handoff.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vitrine.completed_portfolio import (
    CompletedPortfolioEdition,
    CompletedPortfolioHistory,
    CompletedPortfolioHistoryError,
    CompletedPortfolioPresentation,
    CompletedPortfolioSeries,
    project_completed_portfolio_history,
)
from vitrine.models import ActorAttribution
from vitrine.portfolio_presentation_services import (
    PortfolioPresentationBuildError,
    PortfolioPresentationBuildResult,
    build_student_portfolio_presentation,
)
from vitrine.portfolio_presentation_verification import (
    PortfolioPresentationVerificationError,
    verify_portfolio_presentation,
)
from vitrine.snapshot_distribution import (
    SnapshotDistributionError,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.storage import VitrineStorageError, load_current_records_with_state

STUDENT_PORTFOLIO_PRESENTATION_CLASS: Final[str] = "student_portfolio"

_COMPLETED_PORTFOLIO_ACTION_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "completed_portfolio_action.canonical_unavailable",
        "completed_portfolio_action.edition_unavailable",
        "completed_portfolio_action.verification_failed",
        "completed_portfolio_action.presentation_unavailable",
        "completed_portfolio_action.presentation_exists",
        "completed_portfolio_action.presentation_build_failed",
    }
)


class CompletedPortfolioActionError(RuntimeError):
    """Stable fail-closed error for completed Portfolio actions."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        underlying_code: str | None = None,
    ) -> None:
        if code not in _COMPLETED_PORTFOLIO_ACTION_ERROR_CODES:
            raise ValueError(f"unsupported completed Portfolio action code: {code}")
        self.code = code
        self.stage = stage
        self.underlying_code = underlying_code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CompletedPortfolioVerificationResult:
    portfolio_id: str
    snapshot_series_id: str
    edition_number: int
    verified_export_count: int
    verified_student_presentation_count: int


def _history(root: str | Path, portfolio_id: str) -> CompletedPortfolioHistory:
    try:
        _state, records = load_current_records_with_state(root)
        return project_completed_portfolio_history(records, portfolio_id=portfolio_id)
    except (VitrineStorageError, CompletedPortfolioHistoryError) as error:
        raise CompletedPortfolioActionError(
            "completed_portfolio_action.canonical_unavailable",
            "Canonical completed Portfolio history is unavailable.",
            stage="canonical",
            underlying_code=getattr(error, "code", None),
        ) from error


def _exact(
    history: CompletedPortfolioHistory,
    *,
    snapshot_series_id: str,
    edition_number: int,
) -> tuple[CompletedPortfolioSeries, CompletedPortfolioEdition]:
    for series in history.series:
        if series.snapshot_series_id != snapshot_series_id:
            continue
        for edition in series.editions:
            if edition.edition_number == edition_number:
                return series, edition
    raise CompletedPortfolioActionError(
        "completed_portfolio_action.edition_unavailable",
        "Selected completed Portfolio Edition is unavailable.",
        stage="selection",
    )


def _student_presentations(
    edition: CompletedPortfolioEdition,
) -> tuple[CompletedPortfolioPresentation, ...]:
    return tuple(
        item
        for item in edition.presentations
        if item.presentation_class == STUDENT_PORTFOLIO_PRESENTATION_CLASS
    )


def historical_student_presentation_available(
    series: CompletedPortfolioSeries,
    edition: CompletedPortfolioEdition,
) -> bool:
    """Return whether #101 can be offered as a new historical Presentation action."""

    return (
        series.presentation_class == STUDENT_PORTFOLIO_PRESENTATION_CLASS
        and bool(edition.exports)
        and not _student_presentations(edition)
    )


def verify_completed_portfolio_edition(
    root: str | Path,
    *,
    portfolio_id: str,
    snapshot_series_id: str,
    edition_number: int,
) -> CompletedPortfolioVerificationResult:
    """Verify the exact Edition and every recorded Export/student Presentation."""

    history = _history(root, portfolio_id)
    _series, edition = _exact(
        history,
        snapshot_series_id=snapshot_series_id,
        edition_number=edition_number,
    )
    try:
        verify_snapshot_edition(
            root,
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
        )
        for export in edition.exports:
            verify_snapshot_export(
                root,
                snapshot_export_artifact_id=export.snapshot_export_artifact_id,
            )
        presentations = _student_presentations(edition)
        for presentation in presentations:
            verify_portfolio_presentation(
                root,
                presentation_artifact_id=presentation.presentation_artifact_id,
            )
    except (
        SnapshotDistributionError,
        PortfolioPresentationVerificationError,
    ) as error:
        raise CompletedPortfolioActionError(
            "completed_portfolio_action.verification_failed",
            "Completed Portfolio verification failed.",
            stage="verification",
            underlying_code=getattr(error, "code", None),
        ) from error

    return CompletedPortfolioVerificationResult(
        portfolio_id=portfolio_id,
        snapshot_series_id=snapshot_series_id,
        edition_number=edition_number,
        verified_export_count=len(edition.exports),
        verified_student_presentation_count=len(presentations),
    )


def create_historical_student_portfolio_presentation(
    root: str | Path,
    *,
    portfolio_id: str,
    snapshot_series_id: str,
    edition_number: int,
    snapshot_export_artifact_id: str,
    generated_by: ActorAttribution,
) -> PortfolioPresentationBuildResult:
    """Create one student Presentation from exact historical Vitrine custody."""

    history = _history(root, portfolio_id)
    series, edition = _exact(
        history,
        snapshot_series_id=snapshot_series_id,
        edition_number=edition_number,
    )
    if series.presentation_class != STUDENT_PORTFOLIO_PRESENTATION_CLASS:
        raise CompletedPortfolioActionError(
            "completed_portfolio_action.presentation_unavailable",
            "The exact historical Audience Context does not permit the student renderer.",
            stage="availability",
        )
    if _student_presentations(edition):
        raise CompletedPortfolioActionError(
            "completed_portfolio_action.presentation_exists",
            "A canonical student Portfolio Presentation already exists.",
            stage="availability",
        )

    exports = tuple(
        item
        for item in edition.exports
        if item.snapshot_export_artifact_id == snapshot_export_artifact_id
    )
    if len(exports) != 1:
        raise CompletedPortfolioActionError(
            "completed_portfolio_action.presentation_unavailable",
            "The selected technical Export does not belong to the exact Edition.",
            stage="availability",
        )

    try:
        verify_snapshot_edition(
            root,
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
        )
        verify_snapshot_export(
            root,
            snapshot_export_artifact_id=snapshot_export_artifact_id,
        )
    except SnapshotDistributionError as error:
        raise CompletedPortfolioActionError(
            "completed_portfolio_action.verification_failed",
            "Historical Edition/Export verification failed before Presentation creation.",
            stage="verification",
            underlying_code=error.code,
        ) from error

    try:
        return build_student_portfolio_presentation(
            root,
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
            snapshot_export_artifact_id=snapshot_export_artifact_id,
            generated_by=generated_by,
        )
    except PortfolioPresentationBuildError as error:
        raise CompletedPortfolioActionError(
            "completed_portfolio_action.presentation_build_failed",
            "Student Portfolio Presentation creation did not complete.",
            stage="presentation_build",
            underlying_code=error.code,
        ) from error


__all__ = [
    "CompletedPortfolioActionError",
    "CompletedPortfolioVerificationResult",
    "STUDENT_PORTFOLIO_PRESENTATION_CLASS",
    "create_historical_student_portfolio_presentation",
    "historical_student_presentation_available",
    "verify_completed_portfolio_edition",
]
