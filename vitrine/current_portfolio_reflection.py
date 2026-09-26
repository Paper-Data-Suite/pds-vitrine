"""Deterministic rendering for exact frozen Portfolio Reflection revisions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Final, Iterable

from vitrine.models import (
    DigestReference,
    PortfolioReflection,
    SnapshotInputReference,
)
from vitrine.paper_reflection_materialization import (
    PaperReflectionMaterialization,
    PaperReflectionMaterializationError,
    read_paper_reflection_materialization_bytes,
    resolve_paper_reflection_materialization,
)
from vitrine.snapshot_materialization import (
    SnapshotMaterializationError,
    SnapshotRendererDescriptor,
    SnapshotRenderRequest,
    SnapshotRenderResult,
)

CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID: Final[str] = (
    "vitrine_portfolio_reflection"
)
CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION: Final[str] = "1"
CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION: Final[str] = (
    "vitrine_portfolio_reflection_renderer_v1"
)
CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE: Final[str] = "text/plain"
CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_MODE: Final[str] = "inline_text"
CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_FORMAT: Final[str] = "plain_text"

_REFLECTION_RENDERER_CONFIGURATION: Final[dict[str, object]] = {
    "renderer_id": CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
    "renderer_version": CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
    "renderer_contract_version": (
        CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
    ),
    "inline_text": {
        "content_mode": CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_MODE,
        "content_format": CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_FORMAT,
        "encoding": "utf-8",
        "output_media_type": CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE,
        "newline_policy": "preserve_exact",
    },
    "paper_evidence": {
        "content_mode": "external_reference",
        "content_format": "vitrine:returned_paper_evidence",
        "materialization": "exact_core_retained_source_bytes",
        "no_ocr": True,
        "no_page_extraction": True,
        "single_retained_source_entry": True,
    },
    "template": None,
}


def _sha256_bytes(payload: bytes) -> DigestReference:
    return DigestReference(value=hashlib.sha256(payload).hexdigest())


def current_portfolio_reflection_configuration_digest() -> DigestReference:
    """Return the frozen configuration digest for the first-party renderer."""

    payload = json.dumps(
        _REFLECTION_RENDERER_CONFIGURATION,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(payload)


def _paper(
    reflection: PortfolioReflection,
    records: Iterable[object],
) -> PaperReflectionMaterialization | None:
    try:
        return resolve_paper_reflection_materialization(records, reflection)
    except PaperReflectionMaterializationError:
        return None


def current_portfolio_reflection_supported(
    reflection: PortfolioReflection,
    *,
    records: Iterable[object] = (),
) -> bool:
    """Whether one exact Reflection can be rendered without reinterpretation."""

    if (
        reflection.content_mode
        == CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_MODE
        and reflection.content_format
        == CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_FORMAT
    ):
        return True
    return _paper(reflection, records) is not None


def current_portfolio_reflection_media_type(
    reflection: PortfolioReflection,
    *,
    records: Iterable[object] = (),
) -> str:
    if (
        reflection.content_mode
        == CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_MODE
        and reflection.content_format
        == CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_FORMAT
    ):
        return CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE
    paper = _paper(reflection, records)
    if paper is None:
        raise SnapshotMaterializationError(
            "snapshot.render_failed",
            "Frozen Portfolio Reflection content cannot be materialized exactly.",
            stage="render",
        )
    return paper.media_type


def current_portfolio_reflection_input_references(
    reflection: PortfolioReflection,
    *,
    records: Iterable[object] = (),
) -> tuple[SnapshotInputReference, ...]:
    base = SnapshotInputReference(
        record_type="portfolio_reflection",
        record_id=reflection.reflection_id,
        record_revision=reflection.reflection_revision,
    )
    paper = _paper(reflection, records)
    if paper is None:
        return (base,)
    return (
        base,
        SnapshotInputReference(
            record_type="reflection_paper_finalization",
            record_id=paper.paper_finalization_id,
        ),
        SnapshotInputReference(
            record_type="reflection_returned_paper_evidence",
            record_id=paper.returned_paper_evidence_id,
        ),
    )


def current_portfolio_reflection_bytes(
    reflection: PortfolioReflection,
    *,
    workspace_root: str | Path | None = None,
    records: Iterable[object] = (),
) -> bytes:
    """Return exact inline bytes or exact retained paper bytes without OCR."""

    if (
        reflection.content_mode
        == CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_MODE
        and reflection.content_format
        == CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_FORMAT
    ):
        return reflection.content.encode("utf-8")

    try:
        paper = resolve_paper_reflection_materialization(records, reflection)
    except PaperReflectionMaterializationError as error:
        raise SnapshotMaterializationError(
            "snapshot.render_failed",
            "Frozen paper Reflection evidence cannot be resolved exactly.",
            stage="render",
        ) from error
    if paper is None or workspace_root is None:
        raise SnapshotMaterializationError(
            "snapshot.render_failed",
            "Frozen Portfolio Reflection content mode or format is unsupported.",
            stage="render",
        )
    try:
        return read_paper_reflection_materialization_bytes(workspace_root, paper)
    except PaperReflectionMaterializationError as error:
        raise SnapshotMaterializationError(
            "snapshot.render_failed",
            "Frozen paper Reflection source bytes failed exact verification.",
            stage="render",
        ) from error


def current_portfolio_reflection_output_digest(
    reflection: PortfolioReflection,
    *,
    records: Iterable[object] = (),
) -> DigestReference:
    """Return the deterministic digest of the exact Reflection output bytes."""

    if (
        reflection.content_mode
        == CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_MODE
        and reflection.content_format
        == CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_FORMAT
    ):
        return _sha256_bytes(reflection.content.encode("utf-8"))
    paper = _paper(reflection, records)
    if paper is None:
        raise SnapshotMaterializationError(
            "snapshot.render_failed",
            "Frozen Portfolio Reflection content cannot be materialized exactly.",
            stage="render",
        )
    return DigestReference(value=paper.source_sha256)


class CurrentPortfolioReflectionRenderer:
    """Renderer over exact immutable inline or paper-backed Reflections."""

    descriptor = SnapshotRendererDescriptor(
        renderer_id=CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
        renderer_version=CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
        renderer_contract_version=(
            CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
        ),
    )

    def __init__(
        self,
        reflections: tuple[PortfolioReflection, ...],
        *,
        workspace_root: str | Path | None = None,
        records: Iterable[object] = (),
    ) -> None:
        values = tuple(reflections)
        keys = tuple(
            (item.reflection_id, item.reflection_revision) for item in values
        )
        if len(set(keys)) != len(keys):
            raise SnapshotMaterializationError(
                "snapshot.renderer_conflict",
                "Frozen Portfolio Reflection renderer inputs are not unique.",
                stage="renderer_registry",
            )
        self._reflections = values
        self._workspace_root = workspace_root
        self._records = tuple(records)

    def _reflection(self, request: SnapshotRenderRequest) -> PortfolioReflection:
        references = request.entry_plan.input_references
        if not references:
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Portfolio Reflection Entry requires exact immutable inputs.",
                stage="render",
            )
        reference = references[0]
        if (
            reference.record_type != "portfolio_reflection"
            or reference.record_revision is None
        ):
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Portfolio Reflection Entry input reference is invalid.",
                stage="render",
            )
        matches = tuple(
            item
            for item in self._reflections
            if item.reflection_id == reference.record_id
            and item.reflection_revision == reference.record_revision
        )
        if len(matches) != 1:
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Exact frozen Portfolio Reflection revision is unavailable.",
                stage="render",
            )
        reflection = matches[0]
        expected_references = current_portfolio_reflection_input_references(
            reflection,
            records=self._records,
        )
        if references != expected_references:
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Portfolio Reflection Entry provenance inputs differ from canonical state.",
                stage="render",
            )
        return reflection

    def render(self, request: SnapshotRenderRequest) -> SnapshotRenderResult:
        """Render the exact immutable Reflection revision named by the Entry Plan."""

        entry = request.entry_plan
        if (
            entry.renderer_id != CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID
            or entry.renderer_version
            != CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION
            or entry.renderer_contract_version
            != CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
        ):
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Portfolio Reflection Entry renderer identity is invalid.",
                stage="render",
            )
        configuration = current_portfolio_reflection_configuration_digest()
        if entry.renderer_configuration_digest != configuration:
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Portfolio Reflection Entry renderer configuration is invalid.",
                stage="render",
            )
        if entry.renderer_template_digest is not None:
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Portfolio Reflection renderer does not use a template.",
                stage="render",
            )
        reflection = self._reflection(request)
        media_type = current_portfolio_reflection_media_type(
            reflection,
            records=self._records,
        )
        if entry.media_type != media_type:
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Portfolio Reflection Entry media type is invalid.",
                stage="render",
            )
        return SnapshotRenderResult(
            renderer_id=CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
            renderer_version=CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
            renderer_contract_version=(
                CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
            ),
            content=current_portfolio_reflection_bytes(
                reflection,
                workspace_root=self._workspace_root,
                records=self._records,
            ),
            media_type=media_type,
            configuration_digest=configuration,
            template_digest=None,
            language=reflection.language,
        )


__all__ = [
    "CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE",
    "CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION",
    "CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID",
    "CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION",
    "CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_FORMAT",
    "CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_MODE",
    "CurrentPortfolioReflectionRenderer",
    "current_portfolio_reflection_bytes",
    "current_portfolio_reflection_configuration_digest",
    "current_portfolio_reflection_input_references",
    "current_portfolio_reflection_media_type",
    "current_portfolio_reflection_output_digest",
    "current_portfolio_reflection_supported",
]
