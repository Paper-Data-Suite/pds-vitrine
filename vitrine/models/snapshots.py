"""Foundational immutable Snapshot metadata models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from .common import (
    SCHEMA_VERSION,
    identifier_tuple,
    require_aware_datetime,
    require_enum,
    require_identifier,
    require_nonnegative_int,
    require_optional_text,
    require_positive_int,
    require_record_envelope,
    require_relative_path,
    require_text,
)
from .errors import VitrineModelValidationError
from .identity import (
    ActorAttribution,
    DigestReference,
    ProfileRevisionRef,
    SnapshotEditionRef,
)
from .sources import SourceArtifactReference

MATERIALIZATION_KINDS: Final[frozenset[str]] = frozenset(
    {"copied_source", "generated_vitrine", "reference_only"}
)
OMISSION_REASONS: Final[frozenset[str]] = frozenset(
    {
        "audience_prohibited",
        "rights_review_unresolved",
        "privacy_review_unresolved",
        "source_unavailable",
        "representation_unavailable",
        "profile_excluded",
        "explicitly_not_included",
    }
)

MATERIALIZATION_RECORD_TYPE: Final[str] = "snapshot_materialization"
SNAPSHOT_ENTRY_RECORD_TYPE: Final[str] = "snapshot_entry"
SNAPSHOT_OMISSION_RECORD_TYPE: Final[str] = "snapshot_omission"
SNAPSHOT_MANIFEST_RECORD_TYPE: Final[str] = "snapshot_manifest"
SNAPSHOT_SEAL_RECORD_TYPE: Final[str] = "snapshot_seal"
SNAPSHOT_EDITION_RECORD_TYPE: Final[str] = "snapshot_edition"


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotMaterializationRecord:
    materialization_id: str
    snapshot_edition: SnapshotEditionRef
    materialization_kind: str
    candidate_id: str | None
    selection_id: str | None
    placement_id: str | None
    source_artifact: SourceArtifactReference | None
    source_digest: DigestReference | None
    output_digest: DigestReference | None
    byte_size: int | None
    materialized_at: datetime
    materialized_by: ActorAttribution
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=MATERIALIZATION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, MATERIALIZATION_RECORD_TYPE
        )
        object.__setattr__(
            self,
            "materialization_id",
            require_identifier(self.materialization_id, "materialization_id"),
        )
        if not isinstance(self.snapshot_edition, SnapshotEditionRef):
            raise VitrineModelValidationError("snapshot_edition must be SnapshotEditionRef.")
        object.__setattr__(
            self,
            "materialization_kind",
            require_enum(
                self.materialization_kind,
                "materialization_kind",
                MATERIALIZATION_KINDS,
            ),
        )
        for field_name in ("candidate_id", "selection_id", "placement_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self, field_name, require_identifier(value, field_name)
                )
        if self.source_artifact is not None and not isinstance(
            self.source_artifact, SourceArtifactReference
        ):
            raise VitrineModelValidationError("source_artifact must be SourceArtifactReference or null.")
        for field_name in ("source_digest", "output_digest"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, DigestReference):
                raise VitrineModelValidationError(f"{field_name} must be DigestReference or null.")
        if self.byte_size is not None:
            object.__setattr__(
                self, "byte_size", require_nonnegative_int(self.byte_size, "byte_size")
            )
        if self.materialization_kind == "copied_source":
            required = {
                "candidate_id": self.candidate_id,
                "selection_id": self.selection_id,
                "source_artifact": self.source_artifact,
                "source_digest": self.source_digest,
                "output_digest": self.output_digest,
                "byte_size": self.byte_size,
            }
            missing = sorted(name for name, value in required.items() if value is None)
            if missing:
                raise VitrineModelValidationError(
                    "copied_source materialization is missing: " + ", ".join(missing)
                )
        elif self.materialization_kind == "generated_vitrine":
            if self.output_digest is None or self.byte_size is None:
                raise VitrineModelValidationError(
                    "generated_vitrine requires output_digest and byte_size."
                )
            if self.source_artifact is not None or self.source_digest is not None:
                raise VitrineModelValidationError(
                    "generated_vitrine must not fabricate producer source fields."
                )
        else:
            if self.output_digest is not None or self.byte_size is not None:
                raise VitrineModelValidationError(
                    "reference_only must not carry output_digest or byte_size."
                )
        object.__setattr__(
            self,
            "materialized_at",
            require_aware_datetime(self.materialized_at, "materialized_at"),
        )
        if not isinstance(self.materialized_by, ActorAttribution):
            raise VitrineModelValidationError("materialized_by must be ActorAttribution.")


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotEntry:
    snapshot_entry_id: str
    snapshot_edition: SnapshotEditionRef
    materialization_id: str
    section_id: str
    ordinal: int
    relative_path: str
    media_type: str
    content_class: str
    display_title: str | None
    source_placement_id: str | None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_ENTRY_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SNAPSHOT_ENTRY_RECORD_TYPE
        )
        for field_name in (
            "snapshot_entry_id",
            "materialization_id",
            "section_id",
        ):
            object.__setattr__(
                self,
                field_name,
                require_identifier(getattr(self, field_name), field_name),
            )
        if not isinstance(self.snapshot_edition, SnapshotEditionRef):
            raise VitrineModelValidationError("snapshot_edition must be SnapshotEditionRef.")
        object.__setattr__(self, "ordinal", require_positive_int(self.ordinal, "ordinal"))
        object.__setattr__(
            self,
            "relative_path",
            require_relative_path(self.relative_path, "relative_path"),
        )
        object.__setattr__(
            self,
            "media_type",
            require_text(self.media_type, "media_type", maximum=200),
        )
        object.__setattr__(
            self,
            "content_class",
            require_text(self.content_class, "content_class", maximum=128),
        )
        object.__setattr__(
            self,
            "display_title",
            require_optional_text(self.display_title, "display_title", maximum=300),
        )
        if self.source_placement_id is not None:
            object.__setattr__(
                self,
                "source_placement_id",
                require_identifier(self.source_placement_id, "source_placement_id"),
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotOmission:
    snapshot_omission_id: str
    snapshot_edition: SnapshotEditionRef
    candidate_id: str | None
    selection_id: str | None
    placement_id: str | None
    reason_code: str
    audience_context_id: str
    recorded_at: datetime
    recorded_by: ActorAttribution
    note: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_OMISSION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SNAPSHOT_OMISSION_RECORD_TYPE
        )
        object.__setattr__(
            self,
            "snapshot_omission_id",
            require_identifier(self.snapshot_omission_id, "snapshot_omission_id"),
        )
        if not isinstance(self.snapshot_edition, SnapshotEditionRef):
            raise VitrineModelValidationError("snapshot_edition must be SnapshotEditionRef.")
        for field_name in ("candidate_id", "selection_id", "placement_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self, field_name, require_identifier(value, field_name)
                )
        if self.candidate_id is None and self.selection_id is None and self.placement_id is None:
            raise VitrineModelValidationError(
                "SnapshotOmission must reference a Candidate, Selection, or Placement."
            )
        object.__setattr__(
            self,
            "reason_code",
            require_enum(self.reason_code, "reason_code", OMISSION_REASONS),
        )
        object.__setattr__(
            self,
            "audience_context_id",
            require_identifier(self.audience_context_id, "audience_context_id"),
        )
        object.__setattr__(
            self,
            "recorded_at",
            require_aware_datetime(self.recorded_at, "recorded_at"),
        )
        if not isinstance(self.recorded_by, ActorAttribution):
            raise VitrineModelValidationError("recorded_by must be ActorAttribution.")
        object.__setattr__(
            self, "note", require_optional_text(self.note, "note", maximum=1000)
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotManifest:
    manifest_id: str
    manifest_contract_version: str
    snapshot_edition: SnapshotEditionRef
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    composition_revision: int
    audience_context_id: str
    entry_ids: tuple[str, ...]
    omission_ids: tuple[str, ...]
    created_at: datetime
    created_by: ActorAttribution
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_MANIFEST_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SNAPSHOT_MANIFEST_RECORD_TYPE
        )
        for field_name in (
            "manifest_id",
            "manifest_contract_version",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
            "audience_context_id",
        ):
            object.__setattr__(
                self,
                field_name,
                require_identifier(getattr(self, field_name), field_name),
            )
        if not isinstance(self.snapshot_edition, SnapshotEditionRef):
            raise VitrineModelValidationError("snapshot_edition must be SnapshotEditionRef.")
        if not isinstance(self.profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError("profile_revision must be ProfileRevisionRef.")
        object.__setattr__(
            self,
            "composition_revision",
            require_positive_int(self.composition_revision, "composition_revision"),
        )
        object.__setattr__(
            self, "entry_ids", identifier_tuple(self.entry_ids, "entry_ids")
        )
        object.__setattr__(
            self, "omission_ids", identifier_tuple(self.omission_ids, "omission_ids")
        )
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be ActorAttribution.")


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotSeal:
    seal_id: str
    snapshot_edition: SnapshotEditionRef
    manifest_id: str
    manifest_digest: DigestReference
    logical_inventory_digest: DigestReference
    sealed_at: datetime
    sealed_by: ActorAttribution
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_SEAL_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SNAPSHOT_SEAL_RECORD_TYPE
        )
        object.__setattr__(self, "seal_id", require_identifier(self.seal_id, "seal_id"))
        if not isinstance(self.snapshot_edition, SnapshotEditionRef):
            raise VitrineModelValidationError("snapshot_edition must be SnapshotEditionRef.")
        object.__setattr__(
            self, "manifest_id", require_identifier(self.manifest_id, "manifest_id")
        )
        if not isinstance(self.manifest_digest, DigestReference):
            raise VitrineModelValidationError("manifest_digest must be DigestReference.")
        if not isinstance(self.logical_inventory_digest, DigestReference):
            raise VitrineModelValidationError("logical_inventory_digest must be DigestReference.")
        object.__setattr__(
            self, "sealed_at", require_aware_datetime(self.sealed_at, "sealed_at")
        )
        if not isinstance(self.sealed_by, ActorAttribution):
            raise VitrineModelValidationError("sealed_by must be ActorAttribution.")


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotEdition:
    snapshot_series_id: str
    edition_number: int
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    composition_revision: int
    audience_context_id: str
    manifest_id: str
    seal_id: str
    created_at: datetime
    created_by: ActorAttribution
    predecessor_edition: int | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_EDITION_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SNAPSHOT_EDITION_RECORD_TYPE
        )
        for field_name in (
            "snapshot_series_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
            "audience_context_id",
            "manifest_id",
            "seal_id",
        ):
            object.__setattr__(
                self,
                field_name,
                require_identifier(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "edition_number",
            require_positive_int(self.edition_number, "edition_number"),
        )
        if not isinstance(self.profile_revision, ProfileRevisionRef):
            raise VitrineModelValidationError("profile_revision must be ProfileRevisionRef.")
        object.__setattr__(
            self,
            "composition_revision",
            require_positive_int(self.composition_revision, "composition_revision"),
        )
        if self.predecessor_edition is not None:
            predecessor = require_positive_int(
                self.predecessor_edition, "predecessor_edition"
            )
            if predecessor >= self.edition_number:
                raise VitrineModelValidationError(
                    "predecessor_edition must be lower than edition_number."
                )
            object.__setattr__(self, "predecessor_edition", predecessor)
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        if not isinstance(self.created_by, ActorAttribution):
            raise VitrineModelValidationError("created_by must be ActorAttribution.")

    @property
    def reference(self) -> SnapshotEditionRef:
        return SnapshotEditionRef(
            snapshot_series_id=self.snapshot_series_id,
            edition_number=self.edition_number,
        )
