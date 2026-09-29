"""Exact-byte materialization for confirmed paper-backed Portfolio Reflections."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final, Iterable

from pds_core.workspace import resolve_workspace_root

from vitrine.models import (
    PortfolioReflection,
    ReflectionPaperFinalization,
    ReflectionReturnedPaperEvidence,
)

PAPER_REFLECTION_CONTENT_FORMAT: Final[str] = "vitrine:returned_paper_evidence"

_MEDIA_TYPE_BY_SUFFIX: Final[dict[str, str]] = {
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


class PaperReflectionMaterializationError(RuntimeError):
    """Exact paper evidence cannot be safely materialized as one Snapshot entry."""


@dataclass(frozen=True, slots=True)
class PaperReflectionMaterialization:
    reflection_id: str
    reflection_revision: int
    paper_finalization_id: str
    returned_paper_evidence_id: str
    source_scan_id: str
    source_page_number: int
    retained_source_relative_path: str
    source_sha256: str
    media_type: str


def is_paper_reflection(reflection: PortfolioReflection) -> bool:
    return (
        reflection.content_mode == "external_reference"
        and reflection.content_format == PAPER_REFLECTION_CONTENT_FORMAT
    )


def resolve_paper_reflection_materialization(
    records: Iterable[object],
    reflection: PortfolioReflection,
) -> PaperReflectionMaterialization | None:
    """Resolve typed paper provenance without parsing ``PortfolioReflection.content``."""

    if not is_paper_reflection(reflection):
        return None

    values = tuple(records)
    finalizations = tuple(
        item
        for item in values
        if isinstance(item, ReflectionPaperFinalization)
        and item.reflection_id == reflection.reflection_id
        and item.reflection_revision == reflection.reflection_revision
    )
    if len(finalizations) != 1:
        raise PaperReflectionMaterializationError(
            "Paper Reflection requires one exact finalization provenance record."
        )
    finalization = finalizations[0]
    if finalization.student_author != reflection.author:
        raise PaperReflectionMaterializationError(
            "Paper finalization student author differs from the canonical Reflection."
        )

    # Current Portfolio represents one Reflection as one Snapshot Entry. Preserve exact
    # retained bytes only when that entry maps to one exact retained source occurrence.
    # Multi-source packets remain canonical and reviewable but fail closed here rather
    # than being merged, rasterized, OCR'd, or otherwise reinterpreted.
    if len(finalization.returned_paper_evidence_ids) != 1:
        raise PaperReflectionMaterializationError(
            "Exact-byte Current Portfolio materialization currently requires one "
            "returned-paper evidence source."
        )
    evidence_id = finalization.returned_paper_evidence_ids[0]
    evidence_matches = tuple(
        item
        for item in values
        if isinstance(item, ReflectionReturnedPaperEvidence)
        and item.returned_paper_evidence_id == evidence_id
    )
    if len(evidence_matches) != 1:
        raise PaperReflectionMaterializationError(
            "Paper finalization evidence is missing or ambiguous."
        )
    evidence = evidence_matches[0]
    if evidence.source_page_number != 1:
        raise PaperReflectionMaterializationError(
            "Exact retained-source materialization requires source page 1; "
            "page extraction would create a derived artifact."
        )

    relative = PurePosixPath(evidence.retained_source_relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise PaperReflectionMaterializationError(
            "Retained paper source path is not safely workspace-relative."
        )
    if relative.parts[:2] != ("scans", "source") or len(relative.parts) != 4:
        raise PaperReflectionMaterializationError(
            "Retained paper source path is outside the Core retained-source shape."
        )
    media_type = _MEDIA_TYPE_BY_SUFFIX.get(relative.suffix.lower())
    if media_type is None:
        raise PaperReflectionMaterializationError(
            "Retained paper source media type is unsupported for exact materialization."
        )

    return PaperReflectionMaterialization(
        reflection_id=reflection.reflection_id,
        reflection_revision=reflection.reflection_revision,
        paper_finalization_id=finalization.paper_finalization_id,
        returned_paper_evidence_id=evidence.returned_paper_evidence_id,
        source_scan_id=evidence.source_scan_id,
        source_page_number=evidence.source_page_number,
        retained_source_relative_path=evidence.retained_source_relative_path,
        source_sha256=evidence.source_sha256,
        media_type=media_type,
    )


def read_paper_reflection_materialization_bytes(
    workspace_root: str | Path,
    materialization: PaperReflectionMaterialization,
) -> bytes:
    """Read and verify the exact Core-retained source bytes at Snapshot execution."""

    root = resolve_workspace_root(workspace_root)
    relative = PurePosixPath(materialization.retained_source_relative_path)
    source = root.joinpath(*relative.parts)
    try:
        absolute = Path(os.path.abspath(source))
        if source != absolute:
            raise ValueError("retained source path must be canonical")
        resolved = source.resolve(strict=True)
        if resolved != source:
            raise ValueError("retained source must not traverse a symlink or junction")
        if not source.is_file():
            raise ValueError("retained source is not an ordinary file")
        payload = source.read_bytes()
    except (OSError, ValueError) as error:
        raise PaperReflectionMaterializationError(
            f"Retained paper source cannot be read safely: {error}"
        ) from error

    digest = hashlib.sha256(payload).hexdigest()
    if digest != materialization.source_sha256:
        raise PaperReflectionMaterializationError(
            "Retained paper source bytes no longer match canonical evidence SHA-256."
        )
    return payload


__all__ = [
    "PAPER_REFLECTION_CONTENT_FORMAT",
    "PaperReflectionMaterialization",
    "PaperReflectionMaterializationError",
    "is_paper_reflection",
    "read_paper_reflection_materialization_bytes",
    "resolve_paper_reflection_materialization",
]
