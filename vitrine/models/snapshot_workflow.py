"""Additive immutable records for the Vitrine Snapshot build control plane."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from .common import (
    SCHEMA_VERSION,
    identifier_tuple,
    lower_key_tuple,
    require_aware_datetime,
    require_bool,
    require_controlled_key,
    require_enum,
    require_identifier,
    require_optional_text,
    require_positive_int,
    require_record_envelope,
    require_relative_path,
    require_sha256,
    require_text,
)
from .errors import VitrineModelValidationError
from .identity import (
    ActorAttribution,
    DigestReference,
    ProfileRevisionRef,
    SnapshotEditionRef,
)
from .snapshots import OMISSION_REASONS
from .sources import SourceArtifactReference

SNAPSHOT_EXPORT_FORMATS: Final[frozenset[str]] = frozenset({"directory_package"})
SNAPSHOT_ENTRY_PLAN_KINDS: Final[frozenset[str]] = frozenset(
    {"copied_source", "generated_vitrine", "reference_only"}
)
SNAPSHOT_ENTRY_DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {"included", "reference_only", "omitted_permitted", "failed_blocking"}
)
SNAPSHOT_ATTEMPT_OUTCOMES: Final[frozenset[str]] = frozenset(
    {
        "failed",
        "sealed",
        "partial_success_after_seal",
        "durability_uncertain",
        "abandoned_after_explicit_recovery",
    }
)
SNAPSHOT_FINDING_SEVERITIES: Final[frozenset[str]] = frozenset(
    {"warning", "error", "integrity"}
)
SNAPSHOT_SOURCE_STABILITY_RESULTS: Final[frozenset[str]] = frozenset(
    {"verified", "not_applicable", "failed"}
)
SNAPSHOT_VERIFICATION_RESULTS: Final[frozenset[str]] = frozenset(
    {"verified", "failed"}
)

SNAPSHOT_SERIES_RECORD_TYPE: Final[str] = "snapshot_series"
SNAPSHOT_BUILD_REQUEST_RECORD_TYPE: Final[str] = "snapshot_build_request"
SNAPSHOT_BUILD_PLAN_RECORD_TYPE: Final[str] = "snapshot_build_plan"
SNAPSHOT_BUILD_ATTEMPT_RECORD_TYPE: Final[str] = "snapshot_build_attempt"
SNAPSHOT_BUILD_ATTEMPT_RESULT_RECORD_TYPE: Final[str] = "snapshot_build_attempt_result"
SNAPSHOT_MATERIALIZATION_PROVENANCE_RECORD_TYPE: Final[str] = (
    "snapshot_materialization_provenance"
)
SNAPSHOT_EDITION_BUILD_PROVENANCE_RECORD_TYPE: Final[str] = (
    "snapshot_edition_build_provenance"
)
SNAPSHOT_EXPORT_ARTIFACT_RECORD_TYPE: Final[str] = "snapshot_export_artifact"
SNAPSHOT_CURRENT_POINTER_RECORD_TYPE: Final[str] = "snapshot_current_pointer_revision"


def _actor(value: object, field_name: str) -> ActorAttribution:
    if not isinstance(value, ActorAttribution):
        raise VitrineModelValidationError(f"{field_name} must be ActorAttribution.")
    return value


def _profile(value: object, field_name: str) -> ProfileRevisionRef:
    if not isinstance(value, ProfileRevisionRef):
        raise VitrineModelValidationError(f"{field_name} must be ProfileRevisionRef.")
    return value


def _digest(value: object, field_name: str) -> DigestReference:
    if not isinstance(value, DigestReference):
        raise VitrineModelValidationError(f"{field_name} must be DigestReference.")
    return value


def _optional_digest(value: object, field_name: str) -> DigestReference | None:
    if value is None:
        return None
    return _digest(value, field_name)


def _snapshot_relative_path(value: object, field_name: str) -> str:
    path = require_relative_path(value, field_name)
    if ":" in path:
        raise VitrineModelValidationError(
            f"{field_name} must not contain drive or URI-style colon syntax."
        )
    return path


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotInputReference:
    """Exact immutable input reference used by a generated Snapshot Entry."""

    record_type: str
    record_id: str
    record_revision: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "record_type",
            require_controlled_key(self.record_type, "record_type", allow_extension=False),
        )
        object.__setattr__(
            self, "record_id", require_identifier(self.record_id, "record_id")
        )
        if self.record_revision is not None:
            object.__setattr__(
                self,
                "record_revision",
                require_positive_int(self.record_revision, "record_revision"),
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotEntryPlan:
    """One exact logical Entry frozen by a Snapshot Build Plan."""

    entry_plan_id: str
    plan_position: int
    section_id: str
    ordinal: int
    semantic_role: str
    materialization_kind: str
    content_class: str
    selection_id: str | None = None
    placement_id: str | None = None
    candidate_id: str | None = None
    candidate_evaluation_id: str | None = None
    source_publication_id: str | None = None
    producer_module_id: str | None = None
    projection_kind: str | None = None
    projection_contract_version: str | None = None
    source_artifact: SourceArtifactReference | None = None
    producer_source_digest_claim: DigestReference | None = None
    target_relative_path: str | None = None
    media_type: str | None = None
    renderer_id: str | None = None
    renderer_version: str | None = None
    renderer_contract_version: str | None = None
    renderer_configuration_digest: DigestReference | None = None
    renderer_template_digest: DigestReference | None = None
    input_references: tuple[SnapshotInputReference, ...] = ()
    required_review_ids: tuple[str, ...] = ()
    permitted_omission_reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("entry_plan_id", "section_id"):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self, "plan_position", require_positive_int(self.plan_position, "plan_position")
        )
        object.__setattr__(self, "ordinal", require_positive_int(self.ordinal, "ordinal"))
        object.__setattr__(
            self,
            "semantic_role",
            require_controlled_key(self.semantic_role, "semantic_role"),
        )
        kind = require_enum(
            self.materialization_kind,
            "materialization_kind",
            SNAPSHOT_ENTRY_PLAN_KINDS,
        )
        object.__setattr__(self, "materialization_kind", kind)
        object.__setattr__(
            self,
            "content_class",
            require_controlled_key(self.content_class, "content_class"),
        )
        for name in (
            "selection_id",
            "placement_id",
            "candidate_id",
            "candidate_evaluation_id",
            "source_publication_id",
            "producer_module_id",
            "projection_contract_version",
            "renderer_id",
            "renderer_version",
            "renderer_contract_version",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, require_identifier(value, name))
        object.__setattr__(
            self,
            "renderer_configuration_digest",
            _optional_digest(
                self.renderer_configuration_digest, "renderer_configuration_digest"
            ),
        )
        object.__setattr__(
            self,
            "renderer_template_digest",
            _optional_digest(self.renderer_template_digest, "renderer_template_digest"),
        )
        if self.projection_kind is not None:
            object.__setattr__(
                self,
                "projection_kind",
                require_controlled_key(self.projection_kind, "projection_kind"),
            )
        if self.source_artifact is not None and not isinstance(
            self.source_artifact, SourceArtifactReference
        ):
            raise VitrineModelValidationError(
                "source_artifact must be SourceArtifactReference or null."
            )
        object.__setattr__(
            self,
            "producer_source_digest_claim",
            _optional_digest(
                self.producer_source_digest_claim, "producer_source_digest_claim"
            ),
        )
        if self.target_relative_path is not None:
            object.__setattr__(
                self,
                "target_relative_path",
                _snapshot_relative_path(self.target_relative_path, "target_relative_path"),
            )
        if self.media_type is not None:
            object.__setattr__(
                self,
                "media_type",
                require_text(self.media_type, "media_type", maximum=200),
            )
        references = tuple(self.input_references)
        if any(not isinstance(item, SnapshotInputReference) for item in references):
            raise VitrineModelValidationError(
                "input_references must contain SnapshotInputReference values."
            )
        if len(set(references)) != len(references):
            raise VitrineModelValidationError("input_references must not contain duplicates.")
        object.__setattr__(self, "input_references", references)
        object.__setattr__(
            self,
            "required_review_ids",
            identifier_tuple(self.required_review_ids, "required_review_ids"),
        )
        if self.permitted_omission_reason is not None:
            object.__setattr__(
                self,
                "permitted_omission_reason",
                require_enum(
                    self.permitted_omission_reason,
                    "permitted_omission_reason",
                    OMISSION_REASONS,
                ),
            )

        source_fields = (
            self.selection_id,
            self.candidate_id,
            self.candidate_evaluation_id,
            self.source_publication_id,
            self.producer_module_id,
            self.projection_kind,
            self.projection_contract_version,
            self.source_artifact,
        )
        renderer_fields = (
            self.renderer_id,
            self.renderer_version,
            self.renderer_contract_version,
        )

        if kind == "copied_source":
            if any(value is None for value in source_fields):
                raise VitrineModelValidationError(
                    "copied_source Entry Plans require exact Selection, Candidate, Evaluation, "
                    "Publication, producer/projection, and source Artifact provenance."
                )
            if self.target_relative_path is None or self.media_type is None:
                raise VitrineModelValidationError(
                    "copied_source Entry Plans require target_relative_path and media_type."
                )
            if (
                any(value is not None for value in renderer_fields)
                or self.renderer_configuration_digest is not None
                or self.renderer_template_digest is not None
                or references
            ):
                raise VitrineModelValidationError(
                    "copied_source Entry Plans must not carry renderer inputs."
                )
        elif kind == "generated_vitrine":
            if self.target_relative_path is None or self.media_type is None:
                raise VitrineModelValidationError(
                    "generated_vitrine Entry Plans require target_relative_path and media_type."
                )
            if any(value is None for value in renderer_fields):
                raise VitrineModelValidationError(
                    "generated_vitrine Entry Plans require renderer identity and contract."
                )
            if self.renderer_configuration_digest is None:
                raise VitrineModelValidationError(
                    "generated_vitrine Entry Plans require renderer_configuration_digest."
                )
            if not references:
                raise VitrineModelValidationError(
                    "generated_vitrine Entry Plans require exact input_references."
                )
            if any(value is not None for value in source_fields) or self.placement_id is not None:
                raise VitrineModelValidationError(
                    "generated_vitrine Entry Plans must not fabricate producer source provenance."
                )
            if self.producer_source_digest_claim is not None:
                raise VitrineModelValidationError(
                    "generated_vitrine Entry Plans must not carry producer source digests."
                )
            if self.permitted_omission_reason is not None:
                raise VitrineModelValidationError(
                    "generated_vitrine Entry Plans cannot declare permitted omissions because "
                    "the frozen SnapshotOmission contract requires source-backed curation identity."
                )
        else:
            if any(value is None for value in source_fields):
                raise VitrineModelValidationError(
                    "reference_only Entry Plans require exact source provenance."
                )
            if self.target_relative_path is not None or self.media_type is not None:
                raise VitrineModelValidationError(
                    "reference_only Entry Plans must not claim output bytes."
                )
            if (
                any(value is not None for value in renderer_fields)
                or self.renderer_configuration_digest is not None
                or self.renderer_template_digest is not None
                or references
            ):
                raise VitrineModelValidationError(
                    "reference_only Entry Plans must not carry renderer inputs."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotExportPlan:
    export_plan_id: str
    export_format: str
    export_contract_version: str
    included_entry_plan_ids: tuple[str, ...]
    excluded_entry_plan_ids: tuple[str, ...]
    configuration_digest: DigestReference

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "export_plan_id", require_identifier(self.export_plan_id, "export_plan_id")
        )
        object.__setattr__(
            self,
            "export_format",
            require_enum(self.export_format, "export_format", SNAPSHOT_EXPORT_FORMATS),
        )
        object.__setattr__(
            self,
            "export_contract_version",
            require_identifier(self.export_contract_version, "export_contract_version"),
        )
        included = identifier_tuple(
            self.included_entry_plan_ids,
            "included_entry_plan_ids",
            nonempty=True,
        )
        excluded = identifier_tuple(self.excluded_entry_plan_ids, "excluded_entry_plan_ids")
        if set(included) & set(excluded):
            raise VitrineModelValidationError(
                "included_entry_plan_ids and excluded_entry_plan_ids must not overlap."
            )
        object.__setattr__(self, "included_entry_plan_ids", included)
        object.__setattr__(self, "excluded_entry_plan_ids", excluded)
        object.__setattr__(
            self,
            "configuration_digest",
            _digest(self.configuration_digest, "configuration_digest"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotSeries:
    snapshot_series_id: str
    portfolio_id: str
    portfolio_subject_id: str
    snapshot_purpose: str
    audience_context_id: str
    created_at: datetime
    created_by: ActorAttribution
    predecessor_series_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_SERIES_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SNAPSHOT_SERIES_RECORD_TYPE
        )
        for name in (
            "snapshot_series_id",
            "portfolio_id",
            "portfolio_subject_id",
            "audience_context_id",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self,
            "snapshot_purpose",
            require_text(self.snapshot_purpose, "snapshot_purpose", maximum=500),
        )
        object.__setattr__(
            self, "created_at", require_aware_datetime(self.created_at, "created_at")
        )
        object.__setattr__(self, "created_by", _actor(self.created_by, "created_by"))
        if self.predecessor_series_id is not None:
            predecessor = require_identifier(
                self.predecessor_series_id, "predecessor_series_id"
            )
            if predecessor == self.snapshot_series_id:
                raise VitrineModelValidationError(
                    "predecessor_series_id must differ from snapshot_series_id."
                )
            object.__setattr__(self, "predecessor_series_id", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotBuildRequest:
    snapshot_build_request_id: str
    snapshot_series_id: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    composition_revision: int
    audience_context_id: str
    snapshot_purpose: str
    requested_export_formats: tuple[str, ...]
    requested_by: ActorAttribution
    requested_at: datetime
    curation_review_decision_ids: tuple[str, ...] = ()
    idempotency_key: str | None = None
    predecessor_request_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_BUILD_REQUEST_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SNAPSHOT_BUILD_REQUEST_RECORD_TYPE
        )
        for name in (
            "snapshot_build_request_id",
            "snapshot_series_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
            "audience_context_id",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self, "profile_revision", _profile(self.profile_revision, "profile_revision")
        )
        object.__setattr__(
            self,
            "composition_revision",
            require_positive_int(self.composition_revision, "composition_revision"),
        )
        object.__setattr__(
            self,
            "snapshot_purpose",
            require_text(self.snapshot_purpose, "snapshot_purpose", maximum=500),
        )
        formats = tuple(
            require_enum(value, "requested_export_formats", SNAPSHOT_EXPORT_FORMATS)
            for value in self.requested_export_formats
        )
        if not formats or len(set(formats)) != len(formats):
            raise VitrineModelValidationError(
                "requested_export_formats must be nonempty and unique."
            )
        object.__setattr__(self, "requested_export_formats", formats)
        object.__setattr__(self, "requested_by", _actor(self.requested_by, "requested_by"))
        object.__setattr__(
            self, "requested_at", require_aware_datetime(self.requested_at, "requested_at")
        )
        object.__setattr__(
            self,
            "curation_review_decision_ids",
            identifier_tuple(
                self.curation_review_decision_ids, "curation_review_decision_ids"
            ),
        )
        object.__setattr__(
            self,
            "idempotency_key",
            require_optional_text(self.idempotency_key, "idempotency_key", maximum=256),
        )
        if self.predecessor_request_id is not None:
            predecessor = require_identifier(
                self.predecessor_request_id, "predecessor_request_id"
            )
            if predecessor == self.snapshot_build_request_id:
                raise VitrineModelValidationError(
                    "predecessor_request_id must differ from snapshot_build_request_id."
                )
            object.__setattr__(self, "predecessor_request_id", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotBuildPlan:
    snapshot_build_plan_id: str
    snapshot_build_request_id: str
    snapshot_series_id: str
    plan_revision: int
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    composition_revision: int
    audience_context_id: str
    entry_plans: tuple[SnapshotEntryPlan, ...]
    export_plans: tuple[SnapshotExportPlan, ...]
    required_review_references: tuple[str, ...]
    acknowledged_obligation_codes: tuple[str, ...]
    path_policy_id: str
    digest_policy_id: str
    builder_contract_id: str
    builder_contract_version: str
    planned_at: datetime
    planned_by: ActorAttribution
    plan_fingerprint: str
    predecessor_plan_id: str | None = None
    plan_fingerprint_algorithm: str = "sha256"
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_BUILD_PLAN_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SNAPSHOT_BUILD_PLAN_RECORD_TYPE
        )
        for name in (
            "snapshot_build_plan_id",
            "snapshot_build_request_id",
            "snapshot_series_id",
            "portfolio_id",
            "portfolio_subject_id",
            "profile_binding_id",
            "audience_context_id",
            "path_policy_id",
            "digest_policy_id",
            "builder_contract_id",
            "builder_contract_version",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self, "plan_revision", require_positive_int(self.plan_revision, "plan_revision")
        )
        object.__setattr__(
            self, "profile_revision", _profile(self.profile_revision, "profile_revision")
        )
        object.__setattr__(
            self,
            "composition_revision",
            require_positive_int(self.composition_revision, "composition_revision"),
        )
        entries = tuple(self.entry_plans)
        if not entries or any(not isinstance(item, SnapshotEntryPlan) for item in entries):
            raise VitrineModelValidationError(
                "entry_plans must contain at least one SnapshotEntryPlan."
            )
        if len({item.entry_plan_id for item in entries}) != len(entries):
            raise VitrineModelValidationError("entry_plan_id values must be unique.")
        if len({item.plan_position for item in entries}) != len(entries):
            raise VitrineModelValidationError("plan_position values must be unique.")
        if tuple(sorted(entries, key=lambda item: item.plan_position)) != entries:
            raise VitrineModelValidationError(
                "entry_plans must be stored in ascending plan_position order."
            )
        object.__setattr__(self, "entry_plans", entries)
        exports = tuple(self.export_plans)
        if not exports or any(not isinstance(item, SnapshotExportPlan) for item in exports):
            raise VitrineModelValidationError(
                "export_plans must contain at least one SnapshotExportPlan."
            )
        if len({item.export_plan_id for item in exports}) != len(exports):
            raise VitrineModelValidationError("export_plan_id values must be unique.")
        entry_ids = {item.entry_plan_id for item in entries}
        for export in exports:
            referenced = set(export.included_entry_plan_ids) | set(
                export.excluded_entry_plan_ids
            )
            if referenced != entry_ids:
                raise VitrineModelValidationError(
                    "each Export Plan must explicitly partition the complete Entry Plan inventory."
                )
        object.__setattr__(self, "export_plans", exports)
        object.__setattr__(
            self,
            "required_review_references",
            identifier_tuple(
                self.required_review_references, "required_review_references"
            ),
        )
        object.__setattr__(
            self,
            "acknowledged_obligation_codes",
            lower_key_tuple(
                self.acknowledged_obligation_codes, "acknowledged_obligation_codes"
            ),
        )
        object.__setattr__(
            self, "planned_at", require_aware_datetime(self.planned_at, "planned_at")
        )
        object.__setattr__(self, "planned_by", _actor(self.planned_by, "planned_by"))
        if self.plan_fingerprint_algorithm != "sha256":
            raise VitrineModelValidationError(
                "plan_fingerprint_algorithm must be 'sha256'."
            )
        object.__setattr__(
            self,
            "plan_fingerprint",
            require_sha256(self.plan_fingerprint, "plan_fingerprint"),
        )
        if self.predecessor_plan_id is not None:
            predecessor = require_identifier(self.predecessor_plan_id, "predecessor_plan_id")
            if predecessor == self.snapshot_build_plan_id:
                raise VitrineModelValidationError(
                    "predecessor_plan_id must differ from snapshot_build_plan_id."
                )
            object.__setattr__(self, "predecessor_plan_id", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotBuildAttempt:
    snapshot_build_attempt_id: str
    snapshot_build_plan_id: str
    attempt_number: int
    builder_id: str
    builder_version: str
    started_at: datetime
    staging_reference: str
    started_by: ActorAttribution
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_BUILD_ATTEMPT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SNAPSHOT_BUILD_ATTEMPT_RECORD_TYPE
        )
        for name in (
            "snapshot_build_attempt_id",
            "snapshot_build_plan_id",
            "builder_id",
            "builder_version",
            "staging_reference",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self,
            "attempt_number",
            require_positive_int(self.attempt_number, "attempt_number"),
        )
        object.__setattr__(
            self, "started_at", require_aware_datetime(self.started_at, "started_at")
        )
        object.__setattr__(self, "started_by", _actor(self.started_by, "started_by"))


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotBuildFinding:
    code: str
    severity: str
    blocking: bool
    summary: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, "code", maximum=128))
        object.__setattr__(
            self,
            "severity",
            require_enum(self.severity, "severity", SNAPSHOT_FINDING_SEVERITIES),
        )
        object.__setattr__(self, "blocking", require_bool(self.blocking, "blocking"))
        object.__setattr__(
            self,
            "summary",
            require_optional_text(self.summary, "summary", maximum=500),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotEntryOutcome:
    entry_plan_id: str
    disposition: str
    materialization_id: str | None = None
    omission_id: str | None = None
    finding_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "entry_plan_id", require_identifier(self.entry_plan_id, "entry_plan_id")
        )
        disposition = require_enum(
            self.disposition, "disposition", SNAPSHOT_ENTRY_DISPOSITIONS
        )
        object.__setattr__(self, "disposition", disposition)
        for name in ("materialization_id", "omission_id"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, require_identifier(value, name))
        object.__setattr__(
            self,
            "finding_codes",
            tuple(
                require_text(value, "finding_codes", maximum=128)
                for value in self.finding_codes
            ),
        )
        if len(set(self.finding_codes)) != len(self.finding_codes):
            raise VitrineModelValidationError("finding_codes must not contain duplicates.")
        if disposition == "included":
            if self.materialization_id is None or self.omission_id is not None:
                raise VitrineModelValidationError(
                    "included outcomes require materialization_id and no omission_id."
                )
        elif disposition == "omitted_permitted":
            if self.omission_id is None or self.materialization_id is not None:
                raise VitrineModelValidationError(
                    "omitted_permitted outcomes require omission_id and no materialization_id."
                )
        else:
            if self.materialization_id is not None or self.omission_id is not None:
                raise VitrineModelValidationError(
                    "reference_only/failed_blocking outcomes must not claim materialization or omission records."
                )
        if disposition == "failed_blocking" and not self.finding_codes:
            raise VitrineModelValidationError(
                "failed_blocking outcomes require at least one finding code."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotBuildAttemptResult:
    snapshot_build_attempt_result_id: str
    snapshot_build_attempt_id: str
    completed_at: datetime
    terminal_outcome: str
    entry_outcomes: tuple[SnapshotEntryOutcome, ...]
    findings: tuple[SnapshotBuildFinding, ...] = ()
    cleanup_findings: tuple[SnapshotBuildFinding, ...] = ()
    sealed_snapshot_edition: SnapshotEditionRef | None = None
    uncertain_snapshot_edition: SnapshotEditionRef | None = None
    export_artifact_ids: tuple[str, ...] = ()
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_BUILD_ATTEMPT_RESULT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            SNAPSHOT_BUILD_ATTEMPT_RESULT_RECORD_TYPE,
        )
        for name in (
            "snapshot_build_attempt_result_id",
            "snapshot_build_attempt_id",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self, "completed_at", require_aware_datetime(self.completed_at, "completed_at")
        )
        outcome = require_enum(
            self.terminal_outcome, "terminal_outcome", SNAPSHOT_ATTEMPT_OUTCOMES
        )
        object.__setattr__(self, "terminal_outcome", outcome)
        entries = tuple(self.entry_outcomes)
        if any(not isinstance(item, SnapshotEntryOutcome) for item in entries):
            raise VitrineModelValidationError(
                "entry_outcomes must contain SnapshotEntryOutcome values."
            )
        if len({item.entry_plan_id for item in entries}) != len(entries):
            raise VitrineModelValidationError(
                "entry_outcomes must contain at most one outcome per Entry Plan."
            )
        object.__setattr__(self, "entry_outcomes", entries)
        for name in ("findings", "cleanup_findings"):
            values = tuple(getattr(self, name))
            if any(not isinstance(item, SnapshotBuildFinding) for item in values):
                raise VitrineModelValidationError(
                    f"{name} must contain SnapshotBuildFinding values."
                )
            object.__setattr__(self, name, values)
        for name in ("sealed_snapshot_edition", "uncertain_snapshot_edition"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, SnapshotEditionRef):
                raise VitrineModelValidationError(
                    f"{name} must be SnapshotEditionRef or null."
                )
        object.__setattr__(
            self,
            "export_artifact_ids",
            identifier_tuple(self.export_artifact_ids, "export_artifact_ids"),
        )
        if outcome in {"sealed", "partial_success_after_seal"}:
            if self.sealed_snapshot_edition is None or self.uncertain_snapshot_edition is not None:
                raise VitrineModelValidationError(
                    "sealed outcomes require sealed_snapshot_edition and no uncertain edition."
                )
        elif outcome == "durability_uncertain":
            if self.uncertain_snapshot_edition is None or self.sealed_snapshot_edition is not None:
                raise VitrineModelValidationError(
                    "durability_uncertain requires uncertain_snapshot_edition only."
                )
            if self.export_artifact_ids:
                raise VitrineModelValidationError(
                    "durability_uncertain must not claim successful Export Artifacts."
                )
        else:
            if self.sealed_snapshot_edition is not None or self.uncertain_snapshot_edition is not None:
                raise VitrineModelValidationError(
                    "failed/abandoned outcomes must not claim an Edition."
                )
            if self.export_artifact_ids:
                raise VitrineModelValidationError(
                    "failed/abandoned outcomes must not claim Export Artifacts."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotMaterializationProvenance:
    snapshot_materialization_provenance_id: str
    materialization_id: str
    snapshot_edition: SnapshotEditionRef
    entry_plan_id: str
    source_provider_id: str | None
    source_provider_version: str | None
    renderer_id: str | None
    renderer_version: str | None
    renderer_contract_version: str | None
    input_references: tuple[SnapshotInputReference, ...]
    producer_source_digest_claim: DigestReference | None
    source_stability_result: str
    configuration_digest: DigestReference | None
    template_digest: DigestReference | None
    verification_result: str
    recorded_at: datetime
    recorded_by: ActorAttribution
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_MATERIALIZATION_PROVENANCE_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            SNAPSHOT_MATERIALIZATION_PROVENANCE_RECORD_TYPE,
        )
        for name in ("snapshot_materialization_provenance_id", "materialization_id", "entry_plan_id"):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        if not isinstance(self.snapshot_edition, SnapshotEditionRef):
            raise VitrineModelValidationError(
                "snapshot_edition must be SnapshotEditionRef."
            )
        for name in (
            "source_provider_id",
            "source_provider_version",
            "renderer_id",
            "renderer_version",
            "renderer_contract_version",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, require_identifier(value, name))
        references = tuple(self.input_references)
        if any(not isinstance(item, SnapshotInputReference) for item in references):
            raise VitrineModelValidationError(
                "input_references must contain SnapshotInputReference values."
            )
        if len(set(references)) != len(references):
            raise VitrineModelValidationError("input_references must not contain duplicates.")
        object.__setattr__(self, "input_references", references)
        object.__setattr__(
            self,
            "producer_source_digest_claim",
            _optional_digest(
                self.producer_source_digest_claim, "producer_source_digest_claim"
            ),
        )
        object.__setattr__(
            self,
            "source_stability_result",
            require_enum(
                self.source_stability_result,
                "source_stability_result",
                SNAPSHOT_SOURCE_STABILITY_RESULTS,
            ),
        )
        object.__setattr__(
            self,
            "configuration_digest",
            _optional_digest(self.configuration_digest, "configuration_digest"),
        )
        object.__setattr__(
            self,
            "template_digest",
            _optional_digest(self.template_digest, "template_digest"),
        )
        object.__setattr__(
            self,
            "verification_result",
            require_enum(
                self.verification_result,
                "verification_result",
                SNAPSHOT_VERIFICATION_RESULTS,
            ),
        )
        object.__setattr__(
            self, "recorded_at", require_aware_datetime(self.recorded_at, "recorded_at")
        )
        object.__setattr__(self, "recorded_by", _actor(self.recorded_by, "recorded_by"))


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotEditionBuildProvenance:
    snapshot_edition_build_provenance_id: str
    snapshot_edition: SnapshotEditionRef
    snapshot_build_request_id: str
    snapshot_build_plan_id: str
    snapshot_build_attempt_id: str
    snapshot_build_attempt_result_id: str
    portfolio_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    composition_revision: int
    audience_context_id: str
    builder_contract_id: str
    builder_contract_version: str
    path_policy_id: str
    digest_policy_id: str
    recorded_at: datetime
    recorded_by: ActorAttribution
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_EDITION_BUILD_PROVENANCE_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version,
            self.record_type,
            SNAPSHOT_EDITION_BUILD_PROVENANCE_RECORD_TYPE,
        )
        object.__setattr__(
            self,
            "snapshot_edition_build_provenance_id",
            require_identifier(
                self.snapshot_edition_build_provenance_id,
                "snapshot_edition_build_provenance_id",
            ),
        )
        if not isinstance(self.snapshot_edition, SnapshotEditionRef):
            raise VitrineModelValidationError(
                "snapshot_edition must be SnapshotEditionRef."
            )
        for name in (
            "snapshot_build_request_id",
            "snapshot_build_plan_id",
            "snapshot_build_attempt_id",
            "snapshot_build_attempt_result_id",
            "portfolio_id",
            "profile_binding_id",
            "audience_context_id",
            "builder_contract_id",
            "builder_contract_version",
            "path_policy_id",
            "digest_policy_id",
        ):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self, "profile_revision", _profile(self.profile_revision, "profile_revision")
        )
        object.__setattr__(
            self,
            "composition_revision",
            require_positive_int(self.composition_revision, "composition_revision"),
        )
        object.__setattr__(
            self, "recorded_at", require_aware_datetime(self.recorded_at, "recorded_at")
        )
        object.__setattr__(self, "recorded_by", _actor(self.recorded_by, "recorded_by"))


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotExportArtifact:
    snapshot_export_artifact_id: str
    snapshot_edition: SnapshotEditionRef
    export_format: str
    export_contract_version: str
    included_entry_ids: tuple[str, ...]
    excluded_entry_ids: tuple[str, ...]
    packager_id: str
    packager_version: str
    configuration_digest: DigestReference
    generated_at: datetime
    relative_path: str
    directory_inventory_digest: DigestReference
    validation_result: str
    predecessor_export_artifact_id: str | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_EXPORT_ARTIFACT_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SNAPSHOT_EXPORT_ARTIFACT_RECORD_TYPE
        )
        object.__setattr__(
            self,
            "snapshot_export_artifact_id",
            require_identifier(
                self.snapshot_export_artifact_id, "snapshot_export_artifact_id"
            ),
        )
        if not isinstance(self.snapshot_edition, SnapshotEditionRef):
            raise VitrineModelValidationError(
                "snapshot_edition must be SnapshotEditionRef."
            )
        object.__setattr__(
            self,
            "export_format",
            require_enum(self.export_format, "export_format", SNAPSHOT_EXPORT_FORMATS),
        )
        for name in ("export_contract_version", "packager_id", "packager_version"):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        included = identifier_tuple(
            self.included_entry_ids, "included_entry_ids", nonempty=True
        )
        excluded = identifier_tuple(self.excluded_entry_ids, "excluded_entry_ids")
        if set(included) & set(excluded):
            raise VitrineModelValidationError(
                "included_entry_ids and excluded_entry_ids must not overlap."
            )
        object.__setattr__(self, "included_entry_ids", included)
        object.__setattr__(self, "excluded_entry_ids", excluded)
        object.__setattr__(
            self,
            "configuration_digest",
            _digest(self.configuration_digest, "configuration_digest"),
        )
        object.__setattr__(
            self, "generated_at", require_aware_datetime(self.generated_at, "generated_at")
        )
        object.__setattr__(
            self, "relative_path", _snapshot_relative_path(self.relative_path, "relative_path")
        )
        object.__setattr__(
            self,
            "directory_inventory_digest",
            _digest(self.directory_inventory_digest, "directory_inventory_digest"),
        )
        object.__setattr__(
            self,
            "validation_result",
            require_enum(
                self.validation_result,
                "validation_result",
                frozenset({"verified"}),
            ),
        )
        if self.predecessor_export_artifact_id is not None:
            predecessor = require_identifier(
                self.predecessor_export_artifact_id,
                "predecessor_export_artifact_id",
            )
            if predecessor == self.snapshot_export_artifact_id:
                raise VitrineModelValidationError(
                    "predecessor_export_artifact_id must differ from artifact identity."
                )
            object.__setattr__(self, "predecessor_export_artifact_id", predecessor)


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotCurrentPointerRevision:
    snapshot_current_pointer_id: str
    pointer_revision: int
    snapshot_series_id: str
    edition_number: int
    pointed_at: datetime
    pointed_by: ActorAttribution
    authority_reference: str
    reason: str
    predecessor_pointer_revision: int | None = None
    schema_version: str = field(default=SCHEMA_VERSION)
    record_type: str = field(default=SNAPSHOT_CURRENT_POINTER_RECORD_TYPE)

    def __post_init__(self) -> None:
        require_record_envelope(
            self.schema_version, self.record_type, SNAPSHOT_CURRENT_POINTER_RECORD_TYPE
        )
        for name in ("snapshot_current_pointer_id", "snapshot_series_id"):
            object.__setattr__(self, name, require_identifier(getattr(self, name), name))
        object.__setattr__(
            self,
            "pointer_revision",
            require_positive_int(self.pointer_revision, "pointer_revision"),
        )
        object.__setattr__(
            self,
            "edition_number",
            require_positive_int(self.edition_number, "edition_number"),
        )
        object.__setattr__(
            self, "pointed_at", require_aware_datetime(self.pointed_at, "pointed_at")
        )
        object.__setattr__(self, "pointed_by", _actor(self.pointed_by, "pointed_by"))
        object.__setattr__(
            self,
            "authority_reference",
            require_text(self.authority_reference, "authority_reference", maximum=500),
        )
        object.__setattr__(self, "reason", require_text(self.reason, "reason", maximum=1000))
        if self.predecessor_pointer_revision is not None:
            predecessor = require_positive_int(
                self.predecessor_pointer_revision, "predecessor_pointer_revision"
            )
            if predecessor >= self.pointer_revision:
                raise VitrineModelValidationError(
                    "predecessor_pointer_revision must be lower than pointer_revision."
                )
            object.__setattr__(self, "predecessor_pointer_revision", predecessor)

    @property
    def snapshot_edition(self) -> SnapshotEditionRef:
        return SnapshotEditionRef(
            snapshot_series_id=self.snapshot_series_id,
            edition_number=self.edition_number,
        )


__all__ = [
    "SNAPSHOT_ATTEMPT_OUTCOMES",
    "SNAPSHOT_BUILD_ATTEMPT_RECORD_TYPE",
    "SNAPSHOT_BUILD_ATTEMPT_RESULT_RECORD_TYPE",
    "SNAPSHOT_BUILD_PLAN_RECORD_TYPE",
    "SNAPSHOT_BUILD_REQUEST_RECORD_TYPE",
    "SNAPSHOT_CURRENT_POINTER_RECORD_TYPE",
    "SNAPSHOT_EDITION_BUILD_PROVENANCE_RECORD_TYPE",
    "SNAPSHOT_ENTRY_DISPOSITIONS",
    "SNAPSHOT_ENTRY_PLAN_KINDS",
    "SNAPSHOT_EXPORT_ARTIFACT_RECORD_TYPE",
    "SNAPSHOT_EXPORT_FORMATS",
    "SNAPSHOT_MATERIALIZATION_PROVENANCE_RECORD_TYPE",
    "SNAPSHOT_SERIES_RECORD_TYPE",
    "SnapshotBuildAttempt",
    "SnapshotBuildAttemptResult",
    "SnapshotBuildFinding",
    "SnapshotBuildPlan",
    "SnapshotBuildRequest",
    "SnapshotCurrentPointerRevision",
    "SnapshotEditionBuildProvenance",
    "SnapshotEntryOutcome",
    "SnapshotEntryPlan",
    "SnapshotExportArtifact",
    "SnapshotExportPlan",
    "SnapshotInputReference",
    "SnapshotMaterializationProvenance",
    "SnapshotSeries",
]
