"""Deterministic rendering for exact frozen Portfolio Reflection revisions."""

from __future__ import annotations

import hashlib
import json
from typing import Final

from vitrine.models import DigestReference, PortfolioReflection
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
    "supported_content_mode": (
        CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_MODE
    ),
    "supported_content_format": (
        CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_FORMAT
    ),
    "encoding": "utf-8",
    "output_media_type": CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE,
    "newline_policy": "preserve_exact",
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


def current_portfolio_reflection_supported(
    reflection: PortfolioReflection,
) -> bool:
    """Whether one exact Reflection can be rendered without reinterpretation."""

    return (
        reflection.content_mode
        == CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_MODE
        and reflection.content_format
        == CURRENT_PORTFOLIO_REFLECTION_SUPPORTED_CONTENT_FORMAT
    )


def current_portfolio_reflection_bytes(
    reflection: PortfolioReflection,
) -> bytes:
    """Return exact frozen inline Reflection content as deterministic UTF-8 bytes."""

    if not current_portfolio_reflection_supported(reflection):
        raise SnapshotMaterializationError(
            "snapshot.render_failed",
            "Frozen Portfolio Reflection content mode or format is unsupported.",
            stage="render",
        )
    return reflection.content.encode("utf-8")


def current_portfolio_reflection_output_digest(
    reflection: PortfolioReflection,
) -> DigestReference:
    """Return the deterministic digest of exact rendered Reflection bytes."""

    return _sha256_bytes(current_portfolio_reflection_bytes(reflection))


class CurrentPortfolioReflectionRenderer:
    """Renderer over an exact immutable set of frozen Portfolio Reflections."""

    descriptor = SnapshotRendererDescriptor(
        renderer_id=CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
        renderer_version=CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
        renderer_contract_version=(
            CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
        ),
    )

    def __init__(self, reflections: tuple[PortfolioReflection, ...]) -> None:
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

    def _reflection(self, request: SnapshotRenderRequest) -> PortfolioReflection:
        entry = request.entry_plan
        references = entry.input_references
        if len(references) != 1:
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Portfolio Reflection Entry requires one exact immutable input.",
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
        return matches[0]

    def render(self, request: SnapshotRenderRequest) -> SnapshotRenderResult:
        """Render exactly the immutable Reflection revision named by the Entry Plan."""

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
        if entry.media_type != CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE:
            raise SnapshotMaterializationError(
                "snapshot.render_failed",
                "Portfolio Reflection Entry media type is invalid.",
                stage="render",
            )
        reflection = self._reflection(request)
        return SnapshotRenderResult(
            renderer_id=CURRENT_PORTFOLIO_REFLECTION_RENDERER_ID,
            renderer_version=CURRENT_PORTFOLIO_REFLECTION_RENDERER_VERSION,
            renderer_contract_version=(
                CURRENT_PORTFOLIO_REFLECTION_RENDERER_CONTRACT_VERSION
            ),
            content=current_portfolio_reflection_bytes(reflection),
            media_type=CURRENT_PORTFOLIO_REFLECTION_MEDIA_TYPE,
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
    "current_portfolio_reflection_output_digest",
    "current_portfolio_reflection_supported",
]
