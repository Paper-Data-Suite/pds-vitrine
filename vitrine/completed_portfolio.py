"""Pure canonical projection for completed Portfolio history.

Issue #102 requires completed Snapshot Editions, technical Exports, and derived
Presentations to remain discoverable from canonical Vitrine records after the
build session ends.  This module is intentionally record-only: it does not scan
custody directories, resolve filesystem paths, verify bytes, open local output,
or mutate current-pointer state.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Final, TypeVar

from vitrine.models import (
    AudienceContext,
    Portfolio,
    PortfolioPresentationArtifact,
    ProfileRevisionRef,
    SnapshotCurrentPointerRevision,
    SnapshotEdition,
    SnapshotExportArtifact,
    SnapshotManifest,
    SnapshotSeal,
    SnapshotSeries,
)

T = TypeVar("T")

COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION: Final[str] = (
    "vitrine_completed_portfolio_history_v1"
)

_COMPLETED_PORTFOLIO_HISTORY_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "completed_portfolio.invalid_request",
        "completed_portfolio.portfolio_not_found",
        "completed_portfolio.canonical_history_inconsistent",
        "completed_portfolio.current_pointer_inconsistent",
    }
)


class CompletedPortfolioHistoryError(ValueError):
    """Stable failure for an unsafe or inconsistent completed-history projection."""

    def __init__(self, code: str, message: str) -> None:
        if code not in _COMPLETED_PORTFOLIO_HISTORY_ERROR_CODES:
            raise ValueError(f"unsupported completed Portfolio history code: {code}")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CompletedPortfolioExport:
    snapshot_export_artifact_id: str
    export_format: str
    export_contract_version: str
    relative_path: str
    generated_at: datetime
    predecessor_export_artifact_id: str | None


@dataclass(frozen=True, slots=True)
class CompletedPortfolioPresentation:
    presentation_artifact_id: str
    snapshot_export_artifact_id: str
    presentation_class: str
    presentation_contract_version: str
    renderer_id: str
    renderer_version: str
    renderer_contract_version: str
    relative_path: str
    html_relative_path: str
    printable_pdf_relative_path: str
    generated_at: datetime
    predecessor_presentation_artifact_id: str | None


@dataclass(frozen=True, slots=True)
class CompletedPortfolioEdition:
    snapshot_series_id: str
    edition_number: int
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    composition_revision: int
    audience_context_id: str
    created_at: datetime
    predecessor_edition: int | None
    is_current: bool
    exports: tuple[CompletedPortfolioExport, ...]
    presentations: tuple[CompletedPortfolioPresentation, ...]


@dataclass(frozen=True, slots=True)
class CompletedPortfolioSeries:
    snapshot_series_id: str
    portfolio_id: str
    portfolio_subject_id: str
    snapshot_purpose: str
    audience_context_id: str
    audience_class: str
    audience_purpose: str
    presentation_class: str
    created_at: datetime
    predecessor_series_id: str | None
    current_edition_number: int | None
    editions: tuple[CompletedPortfolioEdition, ...]


@dataclass(frozen=True, slots=True)
class CompletedPortfolioHistory:
    contract_version: str
    portfolio_id: str
    portfolio_subject_id: str
    series: tuple[CompletedPortfolioSeries, ...]

    @property
    def completed_edition_count(self) -> int:
        return sum(len(item.editions) for item in self.series)


def _fail(message: str) -> CompletedPortfolioHistoryError:
    return CompletedPortfolioHistoryError(
        "completed_portfolio.canonical_history_inconsistent",
        message,
    )


def _unique_by_id(
    values: Iterable[T],
    *,
    id_of: Callable[[T], str],
    label: str,
) -> dict[str, T]:
    result: dict[str, T] = {}
    for value in values:
        key = id_of(value)
        if key in result:
            raise _fail(f"Canonical {label} identity is duplicated.")
        result[key] = value
    return result


def _pointer_head(
    pointers: tuple[SnapshotCurrentPointerRevision, ...],
    *,
    snapshot_series_id: str,
) -> SnapshotCurrentPointerRevision | None:
    relevant = tuple(
        item for item in pointers if item.snapshot_series_id == snapshot_series_id
    )
    if not relevant:
        return None

    ids = {item.snapshot_current_pointer_id for item in relevant}
    if len(ids) != 1:
        raise CompletedPortfolioHistoryError(
            "completed_portfolio.current_pointer_inconsistent",
            "Snapshot Series has more than one Current Pointer identity.",
        )

    by_revision: dict[int, SnapshotCurrentPointerRevision] = {}
    for item in relevant:
        if item.pointer_revision in by_revision:
            raise CompletedPortfolioHistoryError(
                "completed_portfolio.current_pointer_inconsistent",
                "Snapshot Current Pointer revision is duplicated.",
            )
        by_revision[item.pointer_revision] = item

    successor_count = {revision: 0 for revision in by_revision}
    for item in relevant:
        predecessor = item.predecessor_pointer_revision
        if predecessor is None:
            continue
        if predecessor not in by_revision:
            raise CompletedPortfolioHistoryError(
                "completed_portfolio.current_pointer_inconsistent",
                "Snapshot Current Pointer predecessor is missing.",
            )
        successor_count[predecessor] += 1
        if successor_count[predecessor] > 1:
            raise CompletedPortfolioHistoryError(
                "completed_portfolio.current_pointer_inconsistent",
                "Snapshot Current Pointer history branches.",
            )

    heads = tuple(
        item for item in relevant if successor_count[item.pointer_revision] == 0
    )
    if len(heads) != 1:
        raise CompletedPortfolioHistoryError(
            "completed_portfolio.current_pointer_inconsistent",
            "Snapshot Series does not have one exact Current Pointer head.",
        )

    # The immutable model requires predecessor revisions to be lower.  Walking
    # backward additionally proves the selected head belongs to one connected
    # chain rather than an unrelated revision island.
    visited: set[int] = set()
    current = heads[0]
    while True:
        if current.pointer_revision in visited:
            raise CompletedPortfolioHistoryError(
                "completed_portfolio.current_pointer_inconsistent",
                "Snapshot Current Pointer history contains a cycle.",
            )
        visited.add(current.pointer_revision)
        predecessor = current.predecessor_pointer_revision
        if predecessor is None:
            break
        current = by_revision[predecessor]
    if len(visited) != len(relevant):
        raise CompletedPortfolioHistoryError(
            "completed_portfolio.current_pointer_inconsistent",
            "Snapshot Current Pointer history is disconnected.",
        )
    return heads[0]


def _presentation_projection(
    artifact: PortfolioPresentationArtifact,
) -> CompletedPortfolioPresentation:
    return CompletedPortfolioPresentation(
        presentation_artifact_id=artifact.presentation_artifact_id,
        snapshot_export_artifact_id=artifact.snapshot_export_artifact_id,
        presentation_class=artifact.presentation_class,
        presentation_contract_version=artifact.presentation_contract_version,
        renderer_id=artifact.renderer_id,
        renderer_version=artifact.renderer_version,
        renderer_contract_version=artifact.renderer_contract_version,
        relative_path=artifact.relative_path,
        html_relative_path=artifact.html_relative_path,
        printable_pdf_relative_path=artifact.printable_pdf_relative_path,
        generated_at=artifact.generated_at,
        predecessor_presentation_artifact_id=(
            artifact.predecessor_presentation_artifact_id
        ),
    )


def project_completed_portfolio_history(
    records: Iterable[object],
    *,
    portfolio_id: str,
) -> CompletedPortfolioHistory:
    """Project one Portfolio's completed history from canonical records only.

    Edition numbers are compared only inside their exact Snapshot Series.
    Current status comes only from one valid Current Pointer head.  Export and
    Presentation ordering is deterministic and does not imply currentness.
    """

    if not isinstance(portfolio_id, str) or not portfolio_id.strip():
        raise CompletedPortfolioHistoryError(
            "completed_portfolio.invalid_request",
            "portfolio_id must be nonempty text.",
        )

    values = tuple(records)
    portfolios = tuple(
        item
        for item in values
        if isinstance(item, Portfolio) and item.portfolio_id == portfolio_id
    )
    if not portfolios:
        raise CompletedPortfolioHistoryError(
            "completed_portfolio.portfolio_not_found",
            "Portfolio not found in canonical Vitrine state.",
        )
    if len(portfolios) != 1:
        raise _fail("Canonical Portfolio identity is duplicated.")
    portfolio = portfolios[0]

    all_series = tuple(item for item in values if isinstance(item, SnapshotSeries))
    series_by_id = _unique_by_id(
        all_series,
        id_of=lambda item: item.snapshot_series_id,
        label="Snapshot Series",
    )
    portfolio_series = tuple(
        item for item in all_series if item.portfolio_id == portfolio_id
    )
    portfolio_series_ids = {item.snapshot_series_id for item in portfolio_series}
    editions = tuple(
        item
        for item in values
        if isinstance(item, SnapshotEdition)
        and (
            item.snapshot_series_id in portfolio_series_ids
            or item.portfolio_id == portfolio_id
        )
    )
    manifests = _unique_by_id(
        (item for item in values if isinstance(item, SnapshotManifest)),
        id_of=lambda item: item.manifest_id,
        label="Snapshot Manifest",
    )
    seals = _unique_by_id(
        (item for item in values if isinstance(item, SnapshotSeal)),
        id_of=lambda item: item.seal_id,
        label="Snapshot Seal",
    )
    exports = tuple(
        item
        for item in values
        if isinstance(item, SnapshotExportArtifact)
        and item.snapshot_edition.snapshot_series_id in portfolio_series_ids
    )
    exports_by_id = _unique_by_id(
        exports,
        id_of=lambda item: item.snapshot_export_artifact_id,
        label="Snapshot Export Artifact",
    )
    presentations = tuple(
        item
        for item in values
        if isinstance(item, PortfolioPresentationArtifact)
        and (
            item.portfolio_id == portfolio_id
            or item.snapshot_edition.snapshot_series_id in portfolio_series_ids
        )
    )
    presentations_by_id = _unique_by_id(
        presentations,
        id_of=lambda item: item.presentation_artifact_id,
        label="Portfolio Presentation Artifact",
    )
    audiences_by_id = _unique_by_id(
        (item for item in values if isinstance(item, AudienceContext)),
        id_of=lambda item: item.audience_context_id,
        label="Audience Context",
    )
    pointers = tuple(
        item for item in values if isinstance(item, SnapshotCurrentPointerRevision)
    )

    editions_by_key: dict[tuple[str, int], SnapshotEdition] = {}
    for edition in editions:
        key = (edition.snapshot_series_id, edition.edition_number)
        if key in editions_by_key:
            raise _fail("Canonical Snapshot Edition identity is duplicated.")
        editions_by_key[key] = edition

    for export in exports:
        if (
            export.predecessor_export_artifact_id is not None
            and export.predecessor_export_artifact_id not in exports_by_id
        ):
            raise _fail("Snapshot Export predecessor Artifact is missing.")
        if (export.snapshot_edition.snapshot_series_id, export.snapshot_edition.edition_number) not in editions_by_key:
            raise _fail("Snapshot Export references a missing Snapshot Edition.")

    for presentation in presentations:
        edition_key = (
            presentation.snapshot_edition.snapshot_series_id,
            presentation.snapshot_edition.edition_number,
        )
        edition = editions_by_key.get(edition_key)
        if edition is None:
            raise _fail("Portfolio Presentation references a missing Snapshot Edition.")
        export = exports_by_id.get(presentation.snapshot_export_artifact_id)
        if not isinstance(export, SnapshotExportArtifact):
            raise _fail("Portfolio Presentation references a missing Snapshot Export.")
        if export.snapshot_edition != presentation.snapshot_edition:
            raise _fail("Portfolio Presentation and Snapshot Export bind different Editions.")
        if (
            presentation.portfolio_id != edition.portfolio_id
            or presentation.portfolio_subject_id != edition.portfolio_subject_id
            or presentation.profile_binding_id != edition.profile_binding_id
            or presentation.profile_revision != edition.profile_revision
            or presentation.audience_context_id != edition.audience_context_id
        ):
            raise _fail("Portfolio Presentation context disagrees with its Snapshot Edition.")
        predecessor_id = presentation.predecessor_presentation_artifact_id
        if predecessor_id is not None:
            predecessor = presentations_by_id.get(predecessor_id)
            if not isinstance(predecessor, PortfolioPresentationArtifact):
                raise _fail("Portfolio Presentation predecessor Artifact is missing.")
            if predecessor.snapshot_edition != presentation.snapshot_edition:
                raise _fail(
                    "Portfolio Presentation predecessor belongs to a different Edition."
                )

    projected_series: list[CompletedPortfolioSeries] = []
    for series in portfolio_series:
        if series.portfolio_subject_id != portfolio.portfolio_subject_id:
            raise _fail("Snapshot Series subject disagrees with its Portfolio.")
        if series.predecessor_series_id is not None:
            predecessor_series = series_by_id.get(series.predecessor_series_id)
            if predecessor_series is None:
                raise _fail("Snapshot Series predecessor is missing.")
            if (
                predecessor_series.portfolio_id != series.portfolio_id
                or predecessor_series.portfolio_subject_id
                != series.portfolio_subject_id
            ):
                raise _fail(
                    "Snapshot Series predecessor belongs to a different Portfolio context."
                )

        audience = audiences_by_id.get(series.audience_context_id)
        if not isinstance(audience, AudienceContext):
            raise _fail("Snapshot Series references a missing Audience Context.")
        if (
            audience.portfolio_id != portfolio_id
            or audience.portfolio_subject_id != portfolio.portfolio_subject_id
        ):
            raise _fail("Snapshot Series Audience Context disagrees with its Portfolio.")

        series_editions = tuple(
            item for item in editions if item.snapshot_series_id == series.snapshot_series_id
        )
        head = _pointer_head(pointers, snapshot_series_id=series.snapshot_series_id)
        current_edition_number = None if head is None else head.edition_number
        if (
            current_edition_number is not None
            and (series.snapshot_series_id, current_edition_number) not in editions_by_key
        ):
            raise CompletedPortfolioHistoryError(
                "completed_portfolio.current_pointer_inconsistent",
                "Snapshot Current Pointer references a missing Edition.",
            )

        projected_editions: list[CompletedPortfolioEdition] = []
        for edition in series_editions:
            if (
                edition.portfolio_id != portfolio_id
                or edition.portfolio_subject_id != portfolio.portfolio_subject_id
                or edition.audience_context_id != series.audience_context_id
            ):
                raise _fail("Snapshot Edition context disagrees with its Snapshot Series.")

            manifest = manifests.get(edition.manifest_id)
            seal = seals.get(edition.seal_id)
            if not isinstance(manifest, SnapshotManifest) or not isinstance(
                seal, SnapshotSeal
            ):
                raise _fail("Snapshot Edition is missing its canonical Manifest or Seal.")
            if (
                manifest.snapshot_edition != edition.reference
                or seal.snapshot_edition != edition.reference
                or seal.manifest_id != manifest.manifest_id
            ):
                raise _fail("Snapshot Edition Manifest/Seal identity is inconsistent.")
            if (
                manifest.portfolio_id != edition.portfolio_id
                or manifest.portfolio_subject_id != edition.portfolio_subject_id
                or manifest.profile_binding_id != edition.profile_binding_id
                or manifest.profile_revision != edition.profile_revision
                or manifest.composition_revision != edition.composition_revision
                or manifest.audience_context_id != edition.audience_context_id
            ):
                raise _fail("Snapshot Manifest context disagrees with its Edition.")
            if (
                edition.profile_binding_id != audience.profile_binding_id
                or edition.profile_revision != audience.profile_revision
            ):
                raise _fail("Snapshot Edition profile context disagrees with its Audience Context.")

            edition_exports = tuple(
                CompletedPortfolioExport(
                    snapshot_export_artifact_id=item.snapshot_export_artifact_id,
                    export_format=item.export_format,
                    export_contract_version=item.export_contract_version,
                    relative_path=item.relative_path,
                    generated_at=item.generated_at,
                    predecessor_export_artifact_id=item.predecessor_export_artifact_id,
                )
                for item in sorted(
                    (
                        export
                        for export in exports
                        if export.snapshot_edition == edition.reference
                    ),
                    key=lambda item: (item.generated_at, item.snapshot_export_artifact_id),
                    reverse=True,
                )
            )
            exact_presentations = tuple(
                presentation
                for presentation in presentations
                if presentation.snapshot_edition == edition.reference
            )
            if any(
                item.presentation_class != audience.presentation_class
                for item in exact_presentations
            ):
                raise _fail(
                    "Portfolio Presentation class disagrees with its Audience Context."
                )
            edition_presentations = tuple(
                _presentation_projection(item)
                for item in sorted(
                    exact_presentations,
                    key=lambda item: (item.generated_at, item.presentation_artifact_id),
                    reverse=True,
                )
            )
            projected_editions.append(
                CompletedPortfolioEdition(
                    snapshot_series_id=edition.snapshot_series_id,
                    edition_number=edition.edition_number,
                    portfolio_id=edition.portfolio_id,
                    portfolio_subject_id=edition.portfolio_subject_id,
                    profile_binding_id=edition.profile_binding_id,
                    profile_revision=edition.profile_revision,
                    composition_revision=edition.composition_revision,
                    audience_context_id=edition.audience_context_id,
                    created_at=edition.created_at,
                    predecessor_edition=edition.predecessor_edition,
                    is_current=edition.edition_number == current_edition_number,
                    exports=edition_exports,
                    presentations=edition_presentations,
                )
            )

        projected_series.append(
            CompletedPortfolioSeries(
                snapshot_series_id=series.snapshot_series_id,
                portfolio_id=series.portfolio_id,
                portfolio_subject_id=series.portfolio_subject_id,
                snapshot_purpose=series.snapshot_purpose,
                audience_context_id=series.audience_context_id,
                audience_class=audience.audience_class,
                audience_purpose=audience.purpose,
                presentation_class=audience.presentation_class,
                created_at=series.created_at,
                predecessor_series_id=series.predecessor_series_id,
                current_edition_number=current_edition_number,
                editions=tuple(
                    sorted(
                        projected_editions,
                        key=lambda item: item.edition_number,
                        reverse=True,
                    )
                ),
            )
        )

    return CompletedPortfolioHistory(
        contract_version=COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        series=tuple(
            sorted(
                projected_series,
                key=lambda item: (item.created_at, item.snapshot_series_id),
                reverse=True,
            )
        ),
    )


__all__ = [
    "COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION",
    "CompletedPortfolioEdition",
    "CompletedPortfolioExport",
    "CompletedPortfolioHistory",
    "CompletedPortfolioHistoryError",
    "CompletedPortfolioPresentation",
    "CompletedPortfolioSeries",
    "project_completed_portfolio_history",
]
