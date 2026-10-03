"""Immutable records for derived student-facing Portfolio presentation artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from .common import (
    SCHEMA_VERSION,
    require_aware_datetime,
    require_controlled_key,
    require_identifier,
    require_record_envelope,
    require_relative_path,
)
from .errors import VitrineModelValidationError
from .identity import (
    ActorAttribution,
    DigestReference,
    ProfileRevisionRef,
    SnapshotEditionRef,
)

PORTFOLIO_PRESENTATION_ARTIFACT_RECORD_TYPE: Final[str] = (
    "portfolio_presentation_artifact"
)


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioPresentationArtifact:
    """One immutable derived presentation of one exact verified Snapshot Edition."""

    presentation_artifact_id: str
    snapshot_edition: SnapshotEditionRef
    snapshot_export_artifact_id: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    audience_context_id: str
    presentation_class: str
    presentation_contract_version: str
    renderer_id: str
    renderer_version: str
    renderer_contract_version: str
    renderer_configuration_digest: DigestReference
    relative_path: str
    presentation_manifest_relative_path: str
    presentation_manifest_digest: DigestReference
    html_relative_path: str
    html_digest: DigestReference
    printable_pdf_relative_path: str
    printable_pdf_digest: DigestReference
    package_inventory_digest: DigestReference
    generated_at: datetime
    generated_by: ActorAttribution
    predecessor_presentation_artifact_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=PORTFOLIO_PRESENTATION_ARTIFACT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            PORTFOLIO_PRESENTATION_ARTIFACT_RECORD_TYPE,
        )
        for name in (
            "presentation_artifact_id",
            "snapshot_export_artifact_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
            "audience_context_id",
            "presentation_contract_version",
            "renderer_id",
            "renderer_version",
            "renderer_contract_version",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        if not isinstance(self.snapshot_edition, SnapshotEditionRef):
            raise VitrineModelValidationError(
                "snapshot_edition must be SnapshotEditionRef."
            )
        if not isinstance(self.profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError(
                "profile_revision must be ProfileRevisionRef."
            )
        object.__setattr__(
            self,
            "presentation_class",
            require_controlled_key(self.presentation_class, "presentation_class"),
        )
        if not isinstance(self.renderer_configuration_digest, DigestReference):
            raise VitrineModelValidationError(
                "renderer_configuration_digest must be DigestReference."
            )
        root = require_relative_path(self.relative_path, "relative_path")
        object.__setattr__(self, "relative_path", root)
        prefix = root + "/"
        for name in (
            "presentation_manifest_relative_path",
            "html_relative_path",
            "printable_pdf_relative_path",
        ):
            path = require_relative_path(getattr(self, name), name)
            if not path.startswith(prefix):
                raise VitrineModelValidationError(
                    f"{name} must be contained by relative_path."
                )
            object.__setattr__(self, name, path)
        for name in (
            "presentation_manifest_digest",
            "html_digest",
            "printable_pdf_digest",
            "package_inventory_digest",
        ):
            if not isinstance(getattr(self, name), DigestReference):
                raise VitrineModelValidationError(f"{name} must be DigestReference.")
        object.__setattr__(
            self, "generated_at", require_aware_datetime(self.generated_at, "generated_at")
        )
        if not isinstance(self.generated_by, ActorAttribution):
            raise VitrineModelValidationError("generated_by must be ActorAttribution.")
        if self.predecessor_presentation_artifact_id is not None:
            predecessor = require_identifier(
                self.predecessor_presentation_artifact_id,
                "predecessor_presentation_artifact_id",
            )
            if predecessor == self.presentation_artifact_id:
                raise VitrineModelValidationError(
                    "predecessor_presentation_artifact_id must differ from artifact identity."
                )
            object.__setattr__(self, "predecessor_presentation_artifact_id", predecessor)


__all__ = [
    "PORTFOLIO_PRESENTATION_ARTIFACT_RECORD_TYPE",
    "PortfolioPresentationArtifact",
]
