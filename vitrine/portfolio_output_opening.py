"""Verified local-use boundary for canonical completed Portfolio artifacts.

Issue #102 Slice 3 keeps local opening downstream of canonical discovery and
first-party verification. Callers provide canonical artifact identities, never
teacher-entered filesystem paths.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final, Literal

from pds_core.local_open import LocalOpenError, open_local_path
from pds_core.workspace import WorkspaceRootError, resolve_workspace_root

from vitrine.models import PortfolioPresentationArtifact, SnapshotExportArtifact
from vitrine.portfolio_presentation_verification import (
    PortfolioPresentationVerificationError,
    verify_portfolio_presentation,
)
from vitrine.snapshot_distribution import (
    SnapshotDistributionError,
    verify_snapshot_export,
)
from vitrine.storage import VitrineStorageError, load_current_records_with_state
from vitrine.storage.errors import VitrineStorageValidationError
from vitrine.storage.paths import safe_vitrine_descendant

_PORTFOLIO_OUTPUT_OPEN_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "portfolio_output.invalid_request",
        "portfolio_output.canonical_not_found",
        "portfolio_output.verification_failed",
        "portfolio_output.unsafe_target",
        "portfolio_output.local_open_failed",
    }
)
_TargetKind = Literal["file", "directory"]
LocalOpener = Callable[[Path], Path]


class PortfolioOutputOpenError(RuntimeError):
    """Stable fail-closed error for completed Portfolio local-use actions."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        underlying_code: str | None = None,
    ) -> None:
        if code not in _PORTFOLIO_OUTPUT_OPEN_ERROR_CODES:
            raise ValueError(f"unsupported Portfolio output open code: {code}")
        self.code = code
        self.stage = stage
        self.underlying_code = underlying_code
        super().__init__(message)


def _records(root: str | Path) -> tuple[object, ...]:
    try:
        _state, records = load_current_records_with_state(root)
    except VitrineStorageError as error:
        raise PortfolioOutputOpenError(
            "portfolio_output.canonical_not_found",
            "Canonical Vitrine state is unavailable.",
            stage="canonical",
        ) from error
    return tuple(records)


def _presentation(
    records: tuple[object, ...],
    presentation_artifact_id: str,
) -> PortfolioPresentationArtifact:
    matches = tuple(
        item
        for item in records
        if isinstance(item, PortfolioPresentationArtifact)
        and item.presentation_artifact_id == presentation_artifact_id
    )
    if len(matches) != 1:
        raise PortfolioOutputOpenError(
            "portfolio_output.canonical_not_found",
            "Portfolio Presentation Artifact does not resolve uniquely.",
            stage="canonical",
        )
    return matches[0]


def _export(
    records: tuple[object, ...],
    snapshot_export_artifact_id: str,
) -> SnapshotExportArtifact:
    matches = tuple(
        item
        for item in records
        if isinstance(item, SnapshotExportArtifact)
        and item.snapshot_export_artifact_id == snapshot_export_artifact_id
    )
    if len(matches) != 1:
        raise PortfolioOutputOpenError(
            "portfolio_output.canonical_not_found",
            "Snapshot Export Artifact does not resolve uniquely.",
            stage="canonical",
        )
    return matches[0]


def _verified_presentation(
    root: str | Path,
    presentation_artifact_id: str,
) -> PortfolioPresentationArtifact:
    artifact = _presentation(_records(root), presentation_artifact_id)
    try:
        verified = verify_portfolio_presentation(
            root,
            presentation_artifact_id=presentation_artifact_id,
        )
    except PortfolioPresentationVerificationError as error:
        raise PortfolioOutputOpenError(
            "portfolio_output.verification_failed",
            "Student Portfolio Presentation verification failed.",
            stage="presentation_verification",
            underlying_code=error.code,
        ) from error
    if verified.presentation_artifact_id != artifact.presentation_artifact_id:
        raise PortfolioOutputOpenError(
            "portfolio_output.verification_failed",
            "Presentation verification returned a different canonical identity.",
            stage="presentation_verification",
        )
    return artifact


def _verified_export(
    root: str | Path,
    snapshot_export_artifact_id: str,
) -> SnapshotExportArtifact:
    artifact = _export(_records(root), snapshot_export_artifact_id)
    try:
        verified = verify_snapshot_export(
            root,
            snapshot_export_artifact_id=snapshot_export_artifact_id,
        )
    except SnapshotDistributionError as error:
        raise PortfolioOutputOpenError(
            "portfolio_output.verification_failed",
            "Technical Snapshot Export verification failed.",
            stage="export_verification",
            underlying_code=error.code,
        ) from error
    if verified.snapshot_export_artifact_id != artifact.snapshot_export_artifact_id:
        raise PortfolioOutputOpenError(
            "portfolio_output.verification_failed",
            "Export verification returned a different canonical identity.",
            stage="export_verification",
        )
    return artifact


def _resolve_vitrine_target(
    root: str | Path,
    relative_path: str,
    *,
    target_kind: _TargetKind,
) -> Path:
    text = str(relative_path)
    if not text.strip() or text != text.strip():
        raise PortfolioOutputOpenError(
            "portfolio_output.unsafe_target",
            "Canonical Portfolio output path is empty or malformed.",
            stage="target",
        )
    if text.casefold().startswith(("http://", "https://", "file://")):
        raise PortfolioOutputOpenError(
            "portfolio_output.unsafe_target",
            "Portfolio output targets must be local workspace paths.",
            stage="target",
        )
    try:
        workspace = resolve_workspace_root(root).resolve(strict=True)
    except (OSError, RuntimeError, WorkspaceRootError) as error:
        raise PortfolioOutputOpenError(
            "portfolio_output.unsafe_target",
            "The active PDS workspace is unavailable.",
            stage="workspace",
        ) from error
    if not workspace.is_dir():
        raise PortfolioOutputOpenError(
            "portfolio_output.unsafe_target",
            "The active PDS workspace is not a directory.",
            stage="workspace",
        )
    try:
        candidate = safe_vitrine_descendant(workspace, text)
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError, VitrineStorageValidationError) as error:
        raise PortfolioOutputOpenError(
            "portfolio_output.unsafe_target",
            "Canonical Portfolio output target is missing or unsafe.",
            stage="target",
        ) from error
    try:
        resolved.relative_to(workspace)
    except ValueError as error:
        raise PortfolioOutputOpenError(
            "portfolio_output.unsafe_target",
            "Canonical Portfolio output target escapes the active workspace.",
            stage="target",
        ) from error
    if target_kind == "file":
        valid_kind = resolved.is_file()
    else:
        valid_kind = resolved.is_dir()
    if not valid_kind:
        raise PortfolioOutputOpenError(
            "portfolio_output.unsafe_target",
            f"Canonical Portfolio output target is not the expected {target_kind}.",
            stage="target",
        )
    return resolved


def _open_target(
    path: Path,
    *,
    opener: LocalOpener | None = None,
) -> Path:
    selected_opener = open_local_path if opener is None else opener
    try:
        opened = selected_opener(path)
    except LocalOpenError as error:
        raise PortfolioOutputOpenError(
            "portfolio_output.local_open_failed",
            "The verified Portfolio output could not be opened locally.",
            stage="local_open",
        ) from error
    try:
        return Path(opened).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise PortfolioOutputOpenError(
            "portfolio_output.local_open_failed",
            "The local opener did not return an existing local target.",
            stage="local_open",
        ) from error


def open_student_portfolio_html(
    root: str | Path,
    *,
    presentation_artifact_id: str,
    opener: LocalOpener | None = None,
) -> Path:
    """Verify and open the exact canonical student Portfolio HTML."""

    artifact = _verified_presentation(root, presentation_artifact_id)
    target = _resolve_vitrine_target(
        root,
        artifact.html_relative_path,
        target_kind="file",
    )
    return _open_target(target, opener=opener)


def open_printable_student_portfolio(
    root: str | Path,
    *,
    presentation_artifact_id: str,
    opener: LocalOpener | None = None,
) -> Path:
    """Verify and open the exact canonical binder-ready Portfolio PDF."""

    artifact = _verified_presentation(root, presentation_artifact_id)
    target = _resolve_vitrine_target(
        root,
        artifact.printable_pdf_relative_path,
        target_kind="file",
    )
    return _open_target(target, opener=opener)


def open_student_portfolio_folder(
    root: str | Path,
    *,
    presentation_artifact_id: str,
    opener: LocalOpener | None = None,
) -> Path:
    """Verify and open the exact canonical student Presentation root."""

    artifact = _verified_presentation(root, presentation_artifact_id)
    target = _resolve_vitrine_target(
        root,
        artifact.relative_path,
        target_kind="directory",
    )
    return _open_target(target, opener=opener)


def open_technical_export_folder(
    root: str | Path,
    *,
    snapshot_export_artifact_id: str,
    opener: LocalOpener | None = None,
) -> Path:
    """Verify and open the exact canonical technical Snapshot Export root."""

    artifact = _verified_export(root, snapshot_export_artifact_id)
    target = _resolve_vitrine_target(
        root,
        artifact.relative_path,
        target_kind="directory",
    )
    return _open_target(target, opener=opener)


__all__ = [
    "PortfolioOutputOpenError",
    "open_printable_student_portfolio",
    "open_student_portfolio_folder",
    "open_student_portfolio_html",
    "open_technical_export_folder",
]
