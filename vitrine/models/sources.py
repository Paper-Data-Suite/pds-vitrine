"""Exact publication, producer, artifact, privacy, and subject source references."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from pds_core.routing_models import ModuleRecordRef, ModuleWorkRef

from .common import (
    lower_key_tuple,
    require_aware_datetime,
    require_bool,
    require_controlled_key,
    require_enum,
    require_identifier,
    require_lower_identifier,
    require_nonnegative_int,
    require_optional_text,
    require_positive_int,
    require_relative_path,
    require_text,
)
from .errors import VitrineModelValidationError
from .identity import ActorAttribution, DigestReference

PUBLICATION_KINDS: Final[frozenset[str]] = frozenset(
    {"academic_result_set", "intervention_record_set"}
)
SERIES_STATES: Final[frozenset[str]] = frozenset(
    {
        "current_selectable",
        "withdrawn_head",
        "historical",
        "withdrawn_historical",
        "unknown",
    }
)
WITHDRAWAL_STATES: Final[frozenset[str]] = frozenset(
    {"not_withdrawn", "withdrawn", "unknown"}
)
ARTIFACT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "original_student_work",
        "rendered_feedback",
        "assessment_summary",
        "collaborative_artifact",
        "audience_safe_attribution",
    }
)
RELATIONSHIP_KINDS: Final[frozenset[str]] = frozenset(
    {
        "attempt_subject",
        "submission_subject",
        "artifact_author",
        "artifact_subject",
        "group_member",
        "documented_contributor",
        "recorder",
        "represented_group",
        "individual_score_target",
        "group_score_target",
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class AcademicWorkRegistrationSnapshot:
    registration_revision: int
    producer_contract_version: str
    title_snapshot: str
    work_kind: str
    academic_intent: str
    lifecycle: str
    source_records: tuple[ModuleRecordRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "registration_revision",
            require_positive_int(self.registration_revision, "registration_revision"),
        )
        object.__setattr__(
            self,
            "producer_contract_version",
            require_identifier(
                self.producer_contract_version, "producer_contract_version"
            ),
        )
        object.__setattr__(
            self,
            "title_snapshot",
            require_text(self.title_snapshot, "title_snapshot", maximum=300),
        )
        object.__setattr__(
            self,
            "work_kind",
            require_lower_identifier(self.work_kind, "work_kind"),
        )
        object.__setattr__(
            self,
            "academic_intent",
            require_lower_identifier(self.academic_intent, "academic_intent"),
        )
        object.__setattr__(
            self,
            "lifecycle",
            require_lower_identifier(self.lifecycle, "lifecycle"),
        )
        object.__setattr__(self, "source_records", tuple(self.source_records))
        if any(not isinstance(item, ModuleRecordRef) for item in self.source_records):
            raise VitrineModelValidationError("source_records must contain ModuleRecordRef values.")
        if len(set(self.source_records)) != len(self.source_records):
            raise VitrineModelValidationError("source_records must not contain duplicates.")


@dataclass(frozen=True, slots=True, kw_only=True)
class CorePublicationSourceReference:
    core_publication_schema_version: str
    publication_id: str
    work: ModuleWorkRef
    source_record: ModuleRecordRef | None
    publication_kind: str
    capabilities: tuple[str, ...]
    record_set_id: str
    record_set_revision: int
    manifest_contract_version: str
    manifest_path: str
    manifest_digest_algorithm: str
    manifest_digest: str
    published_at: datetime
    academic_work_registration_revision: int | None
    registration_snapshot: AcademicWorkRegistrationSnapshot | None
    supersedes_publication_id: str | None
    observed_series_state: str
    observed_withdrawal_state: str
    verified_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "core_publication_schema_version",
            require_identifier(
                self.core_publication_schema_version,
                "core_publication_schema_version",
            ),
        )
        object.__setattr__(
            self,
            "publication_id",
            require_identifier(self.publication_id, "publication_id"),
        )
        if not isinstance(self.work, ModuleWorkRef):
            raise VitrineModelValidationError("work must be a ModuleWorkRef.")
        if self.source_record is not None and not isinstance(
            self.source_record, ModuleRecordRef
        ):
            raise VitrineModelValidationError("source_record must be a ModuleRecordRef or null.")
        object.__setattr__(
            self,
            "publication_kind",
            require_enum(
                self.publication_kind, "publication_kind", PUBLICATION_KINDS
            ),
        )
        object.__setattr__(
            self,
            "capabilities",
            lower_key_tuple(self.capabilities, "capabilities"),
        )
        object.__setattr__(
            self,
            "record_set_id",
            require_identifier(self.record_set_id, "record_set_id"),
        )
        object.__setattr__(
            self,
            "record_set_revision",
            require_positive_int(self.record_set_revision, "record_set_revision"),
        )
        object.__setattr__(
            self,
            "manifest_contract_version",
            require_identifier(
                self.manifest_contract_version, "manifest_contract_version"
            ),
        )
        object.__setattr__(
            self,
            "manifest_path",
            require_relative_path(self.manifest_path, "manifest_path"),
        )
        if self.manifest_digest_algorithm != "sha256":
            raise VitrineModelValidationError("manifest_digest_algorithm must be 'sha256'.")
        digest = DigestReference(
            algorithm=self.manifest_digest_algorithm, value=self.manifest_digest
        )
        object.__setattr__(self, "manifest_digest", digest.value)
        object.__setattr__(
            self,
            "published_at",
            require_aware_datetime(self.published_at, "published_at"),
        )
        if self.academic_work_registration_revision is not None:
            object.__setattr__(
                self,
                "academic_work_registration_revision",
                require_positive_int(
                    self.academic_work_registration_revision,
                    "academic_work_registration_revision",
                ),
            )
        if self.registration_snapshot is not None and not isinstance(
            self.registration_snapshot, AcademicWorkRegistrationSnapshot
        ):
            raise VitrineModelValidationError(
                "registration_snapshot must be an AcademicWorkRegistrationSnapshot."
            )
        if self.publication_kind == "academic_result_set":
            if self.academic_work_registration_revision is None:
                raise VitrineModelValidationError(
                    "academic publications require academic_work_registration_revision."
                )
            if self.registration_snapshot is None:
                raise VitrineModelValidationError(
                    "academic publications require registration_snapshot."
                )
            if (
                self.registration_snapshot.registration_revision
                != self.academic_work_registration_revision
            ):
                raise VitrineModelValidationError(
                    "registration_snapshot revision must match the publication reference."
                )
        else:
            if self.academic_work_registration_revision is not None:
                raise VitrineModelValidationError(
                    "intervention publications must not carry a registration revision."
                )
            if self.registration_snapshot is not None:
                raise VitrineModelValidationError(
                    "intervention publications must not carry registration_snapshot."
                )
        if self.supersedes_publication_id is not None:
            predecessor = require_identifier(
                self.supersedes_publication_id, "supersedes_publication_id"
            )
            if predecessor == self.publication_id:
                raise VitrineModelValidationError(
                    "supersedes_publication_id must differ from publication_id."
                )
            object.__setattr__(self, "supersedes_publication_id", predecessor)
        object.__setattr__(
            self,
            "observed_series_state",
            require_enum(
                self.observed_series_state,
                "observed_series_state",
                SERIES_STATES,
            ),
        )
        object.__setattr__(
            self,
            "observed_withdrawal_state",
            require_enum(
                self.observed_withdrawal_state,
                "observed_withdrawal_state",
                WITHDRAWAL_STATES,
            ),
        )
        if (
            self.observed_withdrawal_state == "withdrawn"
            and self.observed_series_state
            not in {"withdrawn_head", "withdrawn_historical", "unknown"}
        ):
            raise VitrineModelValidationError("withdrawal and series observations contradict.")
        if (
            self.observed_withdrawal_state == "not_withdrawn"
            and self.observed_series_state
            in {"withdrawn_head", "withdrawn_historical"}
        ):
            raise VitrineModelValidationError("withdrawal and series observations contradict.")
        object.__setattr__(
            self,
            "verified_at",
            require_aware_datetime(self.verified_at, "verified_at"),
        )


NativeRevision = str | int


@dataclass(frozen=True, slots=True, kw_only=True)
class ProducerSourceReference:
    producer_module_id: str
    producer_contract_version: str
    source_record_kind: str
    source_record_id: str
    source_record_contract_version: str | None
    native_revision: NativeRevision | None
    native_lifecycle: str | None
    native_disposition: str | None
    lineage_reference: str | None
    reader_contract_version: str
    projection_contract_version: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "producer_module_id",
            require_lower_identifier(
                self.producer_module_id, "producer_module_id"
            ),
        )
        object.__setattr__(
            self,
            "producer_contract_version",
            require_identifier(
                self.producer_contract_version, "producer_contract_version"
            ),
        )
        object.__setattr__(
            self,
            "source_record_kind",
            require_lower_identifier(self.source_record_kind, "source_record_kind"),
        )
        object.__setattr__(
            self,
            "source_record_id",
            require_identifier(self.source_record_id, "source_record_id"),
        )
        if self.source_record_contract_version is not None:
            object.__setattr__(
                self,
                "source_record_contract_version",
                require_identifier(
                    self.source_record_contract_version,
                    "source_record_contract_version",
                ),
            )
        if self.native_revision is not None:
            if isinstance(self.native_revision, bool) or not isinstance(
                self.native_revision, (str, int)
            ):
                raise VitrineModelValidationError("native_revision must be a string, integer, or null.")
            if isinstance(self.native_revision, int) and self.native_revision <= 0:
                raise VitrineModelValidationError("integer native_revision must be positive.")
            if isinstance(self.native_revision, str):
                object.__setattr__(
                    self,
                    "native_revision",
                    require_text(
                        self.native_revision, "native_revision", maximum=128
                    ),
                )
        for field_name in (
            "native_lifecycle",
            "native_disposition",
            "lineage_reference",
        ):
            object.__setattr__(
                self,
                field_name,
                require_optional_text(getattr(self, field_name), field_name, maximum=256),
            )
        object.__setattr__(
            self,
            "reader_contract_version",
            require_identifier(
                self.reader_contract_version, "reader_contract_version"
            ),
        )
        object.__setattr__(
            self,
            "projection_contract_version",
            require_identifier(
                self.projection_contract_version, "projection_contract_version"
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceArtifactReference:
    artifact_id: str
    artifact_kind: str
    representation_kind: str
    media_type: str
    source_locator: str | None
    native_revision: NativeRevision | None
    source_digest: DigestReference | None
    byte_size: int | None
    language: str | None
    accessibility_relationship: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "artifact_id", require_identifier(self.artifact_id, "artifact_id")
        )
        object.__setattr__(
            self,
            "artifact_kind",
            require_enum(
                self.artifact_kind,
                "artifact_kind",
                ARTIFACT_KINDS,
                allow_extension=True,
            ),
        )
        object.__setattr__(
            self,
            "representation_kind",
            require_controlled_key(
                self.representation_kind, "representation_kind"
            ),
        )
        object.__setattr__(
            self,
            "media_type",
            require_text(self.media_type, "media_type", maximum=200),
        )
        if self.source_locator is not None:
            object.__setattr__(
                self,
                "source_locator",
                require_relative_path(self.source_locator, "source_locator"),
            )
        if self.native_revision is not None:
            if isinstance(self.native_revision, bool) or not isinstance(
                self.native_revision, (str, int)
            ):
                raise VitrineModelValidationError("native_revision must be a string, integer, or null.")
            if isinstance(self.native_revision, int) and self.native_revision <= 0:
                raise VitrineModelValidationError("integer native_revision must be positive.")
            if isinstance(self.native_revision, str):
                object.__setattr__(
                    self,
                    "native_revision",
                    require_text(
                        self.native_revision, "native_revision", maximum=128
                    ),
                )
        if self.source_digest is not None and not isinstance(
            self.source_digest, DigestReference
        ):
            raise VitrineModelValidationError("source_digest must be a DigestReference or null.")
        if self.byte_size is not None:
            object.__setattr__(
                self, "byte_size", require_nonnegative_int(self.byte_size, "byte_size")
            )
        object.__setattr__(
            self,
            "language",
            require_optional_text(self.language, "language", maximum=64),
        )
        object.__setattr__(
            self,
            "accessibility_relationship",
            require_optional_text(
                self.accessibility_relationship,
                "accessibility_relationship",
                maximum=256,
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SourcePrivacyMetadata:
    classification: str
    subject_scope: str
    metadata_visibility: str
    collaborator_information_present: bool
    third_party_information_present: bool
    rights_review_required: bool
    redaction_review_required: bool
    multi_subject_review_required: bool
    minimum_necessary_projection_required: bool
    policy_reference: str | None

    def __post_init__(self) -> None:
        for field_name in (
            "classification",
            "subject_scope",
            "metadata_visibility",
        ):
            object.__setattr__(
                self,
                field_name,
                require_text(getattr(self, field_name), field_name, maximum=128),
            )
        for field_name in (
            "collaborator_information_present",
            "third_party_information_present",
            "rights_review_required",
            "redaction_review_required",
            "multi_subject_review_required",
            "minimum_necessary_projection_required",
        ):
            object.__setattr__(
                self, field_name, require_bool(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self,
            "policy_reference",
            require_optional_text(self.policy_reference, "policy_reference", maximum=500),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioSubjectRelationshipAssertion:
    assertion_id: str
    portfolio_subject_id: str
    subject_link_id: str
    source_subject_kind: str
    source_subject_id: str
    relationship_kind: str
    relationship_authority: str
    supporting_source_reference: str | None
    verified_at: datetime
    verified_by: ActorAttribution

    def __post_init__(self) -> None:
        for field_name in (
            "assertion_id",
            "portfolio_subject_id",
            "subject_link_id",
            "source_subject_id",
        ):
            object.__setattr__(
                self, field_name, require_identifier(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self,
            "source_subject_kind",
            require_text(self.source_subject_kind, "source_subject_kind", maximum=128),
        )
        object.__setattr__(
            self,
            "relationship_kind",
            require_enum(
                self.relationship_kind,
                "relationship_kind",
                RELATIONSHIP_KINDS,
                allow_extension=True,
            ),
        )
        object.__setattr__(
            self,
            "relationship_authority",
            require_text(
                self.relationship_authority,
                "relationship_authority",
                maximum=256,
            ),
        )
        object.__setattr__(
            self,
            "supporting_source_reference",
            require_optional_text(
                self.supporting_source_reference,
                "supporting_source_reference",
                maximum=500,
            ),
        )
        object.__setattr__(
            self,
            "verified_at",
            require_aware_datetime(self.verified_at, "verified_at"),
        )
        if not isinstance(self.verified_by, ActorAttribution):
            raise VitrineModelValidationError("verified_by must be an ActorAttribution.")
