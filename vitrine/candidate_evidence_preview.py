"""Read-only exact-authority foundation for Candidate evidence preview.

This module resolves one persisted Candidate Inbox entry to its exact stored
CandidateSourceEndpoint. It performs no producer reads, manifest reads, Artifact
byte acquisition, temporary materialization, launching, Selection, Placement,
or persistence.

Human-readable labels are deliberately absent from request and authorization
contracts. Exact canonical references remain the only routing authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from pds_core.academic_work_registration_storage import (
    AcademicWorkRegistrationIntegrityError,
    AcademicWorkRegistrationNotFoundError,
    AcademicWorkRegistrationReadError,
    load_academic_work_registration_revision,
)
from pds_core.academic_work_registrations import AcademicWorkRegistration
from pds_core.publication_records import PublicationRecord
from pds_core.registry_services import (
    RegistryServiceIntegrityError,
    RegistryServiceNotFoundError,
    RegistryServiceWriteError,
    get_canonical_publication_record,
)

from vitrine.candidate_inbox import (
    CandidateInboxError,
    get_candidate_inbox_detail,
)
from vitrine.models import (
    ActorAttribution,
    CandidateSourceEndpoint,
    CorePublicationSourceReference,
)
from vitrine.models.common import (
    lower_key_tuple,
    require_enum,
    require_identifier,
    require_positive_int,
    require_text,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.producer_adapters import (
    ProducerAdapterConflictError,
    ProducerAdapterError,
    ProducerAdapterSupportRequest,
    ProducerAdapterUnsupportedError,
    ProducerProjectionAdapter,
    ProducerProjectionAdapterRegistry,
    ProducerProjectionBatch,
    ProducerProjectionError,
    ProducerReaderError,
    ProjectedProducerRelationship,
    ProjectedProducerSource,
)
from vitrine.producer_reader_services import (
    ProducerReaderServiceError,
    SourceReadAuthorizationGate,
    SourceReadAuthorizationRequest,
    read_authorized_producer_manifest,
)

CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION: Final[str] = (
    "vitrine_candidate_evidence_preview_v1"
)
CANDIDATE_EVIDENCE_PREVIEW_OPERATION: Final[str] = "candidate_evidence_preview"
CANDIDATE_EVIDENCE_PREVIEW_MANIFEST_OPERATION: Final[str] = (
    "candidate_evidence_preview_manifest"
)
CANDIDATE_EVIDENCE_PREVIEW_KINDS: Final[frozenset[str]] = frozenset(
    {"structured_summary", "artifact_preview", "preview_unavailable"}
)
CANDIDATE_EVIDENCE_PREVIEW_AUTHORIZATION_OUTCOMES: Final[frozenset[str]] = (
    frozenset({"allowed", "denied", "unresolved"})
)
CANDIDATE_EVIDENCE_PREVIEW_CODES: Final[frozenset[str]] = frozenset(
    {
        "candidate_evidence_preview.invalid_request",
        "candidate_evidence_preview.entry_not_found",
        "candidate_evidence_preview.state_invalid",
        "candidate_evidence_preview.state_conflict",
        "candidate_evidence_preview.context_mismatch",
        "candidate_evidence_preview.source_unavailable",
        "candidate_evidence_preview.canonical_source_missing",
        "candidate_evidence_preview.canonical_source_mismatch",
        "candidate_evidence_preview.adapter_unavailable",
        "candidate_evidence_preview.source_read_denied",
        "candidate_evidence_preview.source_read_unresolved",
        "candidate_evidence_preview.manifest_missing",
        "candidate_evidence_preview.source_integrity_failed",
        "candidate_evidence_preview.producer_reader_failed",
        "candidate_evidence_preview.projection_failed",
        "candidate_evidence_preview.source_drift",
        "candidate_evidence_preview.authorization_denied",
        "candidate_evidence_preview.authorization_unresolved",
    }
)


class CandidateEvidencePreviewError(RuntimeError):
    """Stable privacy-safe Candidate evidence-preview foundation failure."""

    def __init__(self, code: str, message: str, *, stage: str) -> None:
        if code not in CANDIDATE_EVIDENCE_PREVIEW_CODES:
            raise ValueError(
                f"unsupported Candidate evidence-preview error code: {code}"
            )
        if not isinstance(stage, str) or not stage:
            raise ValueError("stage must be nonempty.")
        self.code = code
        self.stage = stage
        super().__init__(message)


def _optional_identifier(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    return require_identifier(value, name)


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidencePreviewRequest:
    """Exact persisted-entry request; display text is intentionally absent."""

    portfolio_id: str
    portfolio_subject_id: str
    entry_id: str
    candidate_id: str | None
    candidate_evaluation_id: str | None
    requesting_actor: ActorAttribution
    requested_purpose: str
    observed_state_revision: int

    def __post_init__(self) -> None:
        try:
            for name in ("portfolio_id", "portfolio_subject_id"):
                object.__setattr__(
                    self,
                    name,
                    require_identifier(getattr(self, name), name),
                )
            object.__setattr__(
                self,
                "entry_id",
                require_text(self.entry_id, "entry_id", maximum=500),
            )
            object.__setattr__(
                self,
                "candidate_id",
                _optional_identifier(self.candidate_id, "candidate_id"),
            )
            object.__setattr__(
                self,
                "candidate_evaluation_id",
                _optional_identifier(
                    self.candidate_evaluation_id,
                    "candidate_evaluation_id",
                ),
            )
            if (
                self.candidate_id is None
                and self.candidate_evaluation_id is None
            ):
                raise VitrineModelValidationError(
                    "preview requires Candidate or Evaluation authority."
                )
            if not isinstance(self.requesting_actor, ActorAttribution):
                raise VitrineModelValidationError(
                    "requesting_actor must be ActorAttribution."
                )
            object.__setattr__(
                self,
                "requested_purpose",
                require_text(
                    self.requested_purpose,
                    "requested_purpose",
                    maximum=500,
                ),
            )
            object.__setattr__(
                self,
                "observed_state_revision",
                require_positive_int(
                    self.observed_state_revision,
                    "observed_state_revision",
                ),
            )
        except VitrineModelValidationError as error:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Candidate evidence-preview request is invalid.",
                stage="request",
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidencePreviewAuthority:
    """Exact transient source authority resolved from canonical Vitrine state."""

    contract_version: str
    operation: str
    observed_state_revision: int
    portfolio_id: str
    portfolio_subject_id: str
    entry_id: str
    candidate_id: str | None
    candidate_evaluation_id: str | None
    requesting_actor: ActorAttribution
    requested_purpose: str
    source_publication_id: str
    producer_module_id: str
    source_record_kind: str
    source_record_id: str
    source_artifact_id: str | None
    artifact_kind: str | None
    representation_kind: str | None
    media_type: str | None
    source_endpoint: CandidateSourceEndpoint

    def __post_init__(self) -> None:
        if self.contract_version != CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION:
            raise ValueError("unexpected Candidate evidence-preview contract.")
        if self.operation != CANDIDATE_EVIDENCE_PREVIEW_OPERATION:
            raise ValueError("unexpected Candidate evidence-preview operation.")
        if not isinstance(self.source_endpoint, CandidateSourceEndpoint):
            raise ValueError("source_endpoint must be CandidateSourceEndpoint.")




@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidenceStructuredField:
    """One allowlisted instructional fact in a transient structured preview."""

    source_key: str
    label: str
    value: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "source_key",
                require_text(self.source_key, "source_key", maximum=128),
            )
            object.__setattr__(
                self,
                "label",
                require_text(self.label, "label", maximum=128),
            )
            object.__setattr__(
                self,
                "value",
                require_text(self.value, "value", maximum=1200),
            )
        except VitrineModelValidationError as error:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Structured Candidate preview field is invalid.",
                stage="structured_preview",
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidenceStructuredPreview:
    """Bounded teacher-readable content from an exact revalidated projection."""

    title: str
    evidence_kind: str
    fields: tuple[CandidateEvidenceStructuredField, ...]

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "title",
                require_text(self.title, "title", maximum=300),
            )
            object.__setattr__(
                self,
                "evidence_kind",
                require_text(self.evidence_kind, "evidence_kind", maximum=128),
            )
        except VitrineModelValidationError as error:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Structured Candidate preview is invalid.",
                stage="structured_preview",
            ) from error
        fields = tuple(self.fields)
        if any(
            not isinstance(item, CandidateEvidenceStructuredField)
            for item in fields
        ):
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Structured Candidate preview fields are invalid.",
                stage="structured_preview",
            )
        if len({item.source_key for item in fields}) != len(fields):
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Structured Candidate preview contains duplicate source fields.",
                stage="structured_preview",
            )
        object.__setattr__(self, "fields", fields)


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidencePreviewResult:
    """One exact revalidated preview form with no acquired Artifact bytes."""

    contract_version: str
    preview_kind: str
    authority: CandidateEvidencePreviewAuthority
    verified_source: ProjectedProducerSource
    artifact_authorization_required: bool
    structured_preview: CandidateEvidenceStructuredPreview | None = None
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if self.contract_version != CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION:
            raise ValueError("unexpected Candidate evidence-preview contract.")
        if self.preview_kind not in CANDIDATE_EVIDENCE_PREVIEW_KINDS:
            raise ValueError("unsupported Candidate evidence-preview kind.")
        if not isinstance(self.authority, CandidateEvidencePreviewAuthority):
            raise ValueError("authority must be CandidateEvidencePreviewAuthority.")
        if not isinstance(self.verified_source, ProjectedProducerSource):
            raise ValueError("verified_source must be ProjectedProducerSource.")
        if self.preview_kind == "artifact_preview":
            if self.structured_preview is not None:
                raise ValueError(
                    "artifact preview must not carry structured preview content."
                )
            if not self.artifact_authorization_required:
                raise ValueError(
                    "artifact preview must require explicit Artifact authorization."
                )
            if self.unavailable_reason is not None:
                raise ValueError(
                    "artifact preview must not carry an unavailable reason."
                )
        elif self.preview_kind == "structured_summary":
            if not isinstance(
                self.structured_preview,
                CandidateEvidenceStructuredPreview,
            ):
                raise ValueError(
                    "structured summary requires bounded structured preview content."
                )
            if self.artifact_authorization_required:
                raise ValueError(
                    "structured summary must not require Artifact-byte authorization."
                )
            if self.unavailable_reason is not None:
                raise ValueError(
                    "structured summary must not carry an unavailable reason."
                )
        else:
            if self.structured_preview is not None:
                raise ValueError(
                    "unavailable preview must not carry structured preview content."
                )
            if self.artifact_authorization_required:
                raise ValueError(
                    "unavailable preview must not require Artifact authorization."
                )
            if not isinstance(self.unavailable_reason, str) or not self.unavailable_reason:
                raise ValueError(
                    "unavailable preview requires a bounded explanatory reason."
                )

@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidencePreviewAuthorizationRequest:
    """Exact authorization context for producer Artifact preview access."""

    operation: str
    portfolio_id: str
    portfolio_subject_id: str
    candidate_id: str | None
    candidate_evaluation_id: str | None
    source_publication_id: str
    producer_module_id: str
    source_artifact_id: str | None
    artifact_kind: str | None
    representation_kind: str | None
    requesting_actor: ActorAttribution
    purpose: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "operation",
                require_enum(
                    self.operation,
                    "operation",
                    frozenset({CANDIDATE_EVIDENCE_PREVIEW_OPERATION}),
                ),
            )
            for name in (
                "portfolio_id",
                "portfolio_subject_id",
                "source_publication_id",
                "producer_module_id",
            ):
                object.__setattr__(
                    self,
                    name,
                    require_identifier(getattr(self, name), name),
                )
            for name in (
                "candidate_id",
                "candidate_evaluation_id",
                "source_artifact_id",
            ):
                object.__setattr__(
                    self,
                    name,
                    _optional_identifier(getattr(self, name), name),
                )
            for name in ("artifact_kind", "representation_kind"):
                value = getattr(self, name)
                if value is not None:
                    object.__setattr__(
                        self,
                        name,
                        require_text(value, name, maximum=256),
                    )
            if not isinstance(self.requesting_actor, ActorAttribution):
                raise VitrineModelValidationError(
                    "requesting_actor must be ActorAttribution."
                )
            object.__setattr__(
                self,
                "purpose",
                require_text(self.purpose, "purpose", maximum=500),
            )
        except VitrineModelValidationError as error:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Candidate evidence-preview authorization request is invalid.",
                stage="authorization_request",
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvidencePreviewAuthorizationDecision:
    """Explicit allow/deny/unresolved decision for preview Artifact access."""

    outcome: str
    authority_reference: str | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "outcome",
                require_enum(
                    self.outcome,
                    "outcome",
                    CANDIDATE_EVIDENCE_PREVIEW_AUTHORIZATION_OUTCOMES,
                ),
            )
            if self.authority_reference is not None:
                object.__setattr__(
                    self,
                    "authority_reference",
                    require_text(
                        self.authority_reference,
                        "authority_reference",
                        maximum=500,
                    ),
                )
            object.__setattr__(
                self,
                "reason_codes",
                lower_key_tuple(self.reason_codes, "reason_codes"),
            )
        except VitrineModelValidationError as error:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Candidate evidence-preview authorization decision is invalid.",
                stage="authorization",
            ) from error
        if self.outcome == "allowed" and self.authority_reference is None:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.invalid_request",
                "Allowed Candidate evidence preview requires authority_reference.",
                stage="authorization",
            )


class CandidateEvidencePreviewAuthorizationGate(Protocol):
    def authorize(
        self,
        request: CandidateEvidencePreviewAuthorizationRequest,
    ) -> CandidateEvidencePreviewAuthorizationDecision: ...


def resolve_candidate_evidence_preview_authority(
    workspace_root: str | Path,
    request: CandidateEvidencePreviewRequest,
) -> CandidateEvidencePreviewAuthority:
    """Resolve exact persisted preview authority without producer access."""

    if not isinstance(request, CandidateEvidencePreviewRequest):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.invalid_request",
            "request must be CandidateEvidencePreviewRequest.",
            stage="request",
        )

    try:
        detail = get_candidate_inbox_detail(workspace_root, request.entry_id)
    except CandidateInboxError as error:
        code = (
            "candidate_evidence_preview.entry_not_found"
            if error.code == "candidate_inbox.entry_not_found"
            else "candidate_evidence_preview.state_invalid"
        )
        raise CandidateEvidencePreviewError(
            code,
            "Exact Candidate Inbox preview authority is unavailable.",
            stage="inbox_resolution",
        ) from error

    if detail.observed_state_revision != request.observed_state_revision:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.state_conflict",
            "Vitrine state changed after the Candidate entry was observed.",
            stage="state_replay",
        )

    item = detail.item
    if (
        item.portfolio_id != request.portfolio_id
        or item.portfolio_subject_id != request.portfolio_subject_id
        or item.candidate_id != request.candidate_id
        or item.current_evaluation_id != request.candidate_evaluation_id
    ):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.context_mismatch",
            "Candidate evidence-preview authority no longer matches the exact entry.",
            stage="context_replay",
        )

    endpoint = (
        None
        if detail.evaluation is None
        else detail.evaluation.source_endpoint
    )
    if endpoint is None and detail.candidate is not None:
        endpoint = detail.candidate.source_endpoint
    if endpoint is None:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.source_unavailable",
            "Exact persisted Candidate source authority is unavailable.",
            stage="source_resolution",
        )

    publication = endpoint.core_publication
    producer = endpoint.producer_source
    artifact = endpoint.source_artifact
    return CandidateEvidencePreviewAuthority(
        contract_version=CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION,
        operation=CANDIDATE_EVIDENCE_PREVIEW_OPERATION,
        observed_state_revision=detail.observed_state_revision,
        portfolio_id=item.portfolio_id,
        portfolio_subject_id=item.portfolio_subject_id,
        entry_id=item.entry_id,
        candidate_id=item.candidate_id,
        candidate_evaluation_id=item.current_evaluation_id,
        requesting_actor=request.requesting_actor,
        requested_purpose=request.requested_purpose,
        source_publication_id=publication.publication_id,
        producer_module_id=producer.producer_module_id,
        source_record_kind=producer.source_record_kind,
        source_record_id=producer.source_record_id,
        source_artifact_id=None if artifact is None else artifact.artifact_id,
        artifact_kind=None if artifact is None else artifact.artifact_kind,
        representation_kind=(
            None if artifact is None else artifact.representation_kind
        ),
        media_type=None if artifact is None else artifact.media_type,
        source_endpoint=endpoint,
    )




def _publication_matches_reference(
    publication: PublicationRecord,
    reference: CorePublicationSourceReference,
) -> bool:
    """Compare immutable Core Publication facts, not current series position."""
    return (
        publication.schema_version == reference.core_publication_schema_version
        and publication.publication_id == reference.publication_id
        and publication.work == reference.work
        and publication.source_record == reference.source_record
        and publication.publication_kind == reference.publication_kind
        and tuple(publication.capabilities) == tuple(reference.capabilities)
        and publication.record_set_id == reference.record_set_id
        and publication.record_set_revision == reference.record_set_revision
        and publication.manifest_contract_version == reference.manifest_contract_version
        and publication.manifest_path == reference.manifest_path
        and publication.manifest_digest_algorithm == reference.manifest_digest_algorithm
        and publication.manifest_digest == reference.manifest_digest
        and publication.published_at == reference.published_at
        and publication.academic_work_registration_revision
        == reference.academic_work_registration_revision
        and publication.supersedes_publication_id == reference.supersedes_publication_id
    )


def _load_exact_preview_publication(
    workspace_root: str | Path,
    reference: CorePublicationSourceReference,
) -> PublicationRecord:
    try:
        publication = get_canonical_publication_record(
            workspace_root,
            reference.publication_id,
        )
    except RegistryServiceNotFoundError as error:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.canonical_source_missing",
            "Exact Candidate Publication is no longer available.",
            stage="canonical_publication",
        ) from error
    except (RegistryServiceIntegrityError, RegistryServiceWriteError) as error:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.canonical_source_mismatch",
            "Exact Candidate Publication could not be validated.",
            stage="canonical_publication",
        ) from error
    if not _publication_matches_reference(publication, reference):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.canonical_source_mismatch",
            "Canonical Publication no longer matches the persisted Candidate source.",
            stage="canonical_publication",
        )
    return publication


def _registration_matches_snapshot(
    registration: AcademicWorkRegistration,
    reference: CorePublicationSourceReference,
) -> bool:
    snapshot = reference.registration_snapshot
    if snapshot is None:
        return False
    return (
        registration.work == reference.work
        and registration.registration_revision == snapshot.registration_revision
        and registration.producer_contract_version == snapshot.producer_contract_version
        and registration.title == snapshot.title_snapshot
        and registration.work_kind == snapshot.work_kind
        and registration.academic_intent == snapshot.academic_intent
        and registration.lifecycle == snapshot.lifecycle
        and registration.source_records == snapshot.source_records
    )


def _load_exact_preview_registration(
    workspace_root: str | Path,
    publication: PublicationRecord,
    reference: CorePublicationSourceReference,
) -> AcademicWorkRegistration | None:
    revision = reference.academic_work_registration_revision
    snapshot = reference.registration_snapshot
    if revision is None:
        if snapshot is not None:
            raise CandidateEvidencePreviewError(
                "candidate_evidence_preview.canonical_source_mismatch",
                "Persisted Candidate registration provenance is inconsistent.",
                stage="registration",
            )
        return None
    if snapshot is None or snapshot.registration_revision != revision:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.canonical_source_mismatch",
            "Persisted Candidate registration provenance is incomplete.",
            stage="registration",
        )
    try:
        registration = load_academic_work_registration_revision(
            workspace_root,
            publication.work,
            revision,
        )
    except AcademicWorkRegistrationNotFoundError as error:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.canonical_source_missing",
            "Exact Candidate Academic Work Registration is unavailable.",
            stage="registration",
        ) from error
    except (
        AcademicWorkRegistrationIntegrityError,
        AcademicWorkRegistrationReadError,
    ) as error:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.canonical_source_mismatch",
            "Exact Candidate Academic Work Registration could not be validated.",
            stage="registration",
        ) from error
    if not _registration_matches_snapshot(registration, reference):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.canonical_source_mismatch",
            "Academic Work Registration no longer matches persisted Candidate provenance.",
            stage="registration",
        )
    return registration


def _preview_adapter_request(
    publication: PublicationRecord,
    registration: AcademicWorkRegistration | None,
) -> ProducerAdapterSupportRequest:
    source = publication.source_record
    return ProducerAdapterSupportRequest(
        producer_module_id=publication.work.module_id,
        core_publication_schema_version=publication.schema_version,
        publication_kind=publication.publication_kind,
        manifest_contract_version=publication.manifest_contract_version,
        producer_contract_version=(
            None if registration is None else registration.producer_contract_version
        ),
        source_record_kind=None if source is None else source.record_kind,
        source_record_contract_version=(
            None if source is None else source.contract_version
        ),
        capabilities=tuple(publication.capabilities),
    )


def _select_preview_adapter(
    registry: ProducerProjectionAdapterRegistry,
    request: ProducerAdapterSupportRequest,
) -> ProducerProjectionAdapter:
    try:
        return registry.select_adapter(request)
    except (
        ProducerAdapterUnsupportedError,
        ProducerAdapterConflictError,
        ProducerAdapterError,
    ) as error:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.adapter_unavailable",
            "No exact audited Vitrine adapter can revalidate this Candidate source.",
            stage="adapter_support",
        ) from error


def _read_preview_public_model(
    workspace_root: str | Path,
    *,
    authority: CandidateEvidencePreviewAuthority,
    publication: PublicationRecord,
    adapter: ProducerProjectionAdapter,
    authorization_gate: SourceReadAuthorizationGate,
) -> object:
    request = SourceReadAuthorizationRequest(
        portfolio_id=authority.portfolio_id,
        portfolio_subject_id=authority.portfolio_subject_id,
        publication_id=authority.source_publication_id,
        operation=CANDIDATE_EVIDENCE_PREVIEW_MANIFEST_OPERATION,
        purpose=authority.requested_purpose,
    )
    try:
        result = read_authorized_producer_manifest(
            workspace_root,
            publication=publication,
            authorization_gate=authorization_gate,
            authorization_request=request,
            reader=adapter.reader,
        )
    except ProducerReaderServiceError as error:
        if error.code == "source_read.authorization_denied":
            code = "candidate_evidence_preview.source_read_denied"
        elif error.code == "source_read.authorization_unresolved":
            code = "candidate_evidence_preview.source_read_unresolved"
        elif error.code == "source_read.manifest_missing":
            code = "candidate_evidence_preview.manifest_missing"
        elif error.code == "source_read.manifest_integrity_failed":
            code = "candidate_evidence_preview.source_integrity_failed"
        else:
            code = "candidate_evidence_preview.invalid_request"
        raise CandidateEvidencePreviewError(
            code,
            "Exact Candidate producer source could not be read safely.",
            stage=error.stage,
        ) from error
    except ProducerReaderError as error:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.producer_reader_failed",
            "Producer public reader rejected the exact Candidate manifest.",
            stage="producer_reader",
        ) from error
    return result.public_model


def _project_preview_sources(
    adapter: ProducerProjectionAdapter,
    public_model: object,
) -> tuple[ProjectedProducerSource, ...]:
    try:
        batch = adapter.project(public_model)
    except ProducerProjectionError as error:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.projection_failed",
            "Producer source projection failed safely.",
            stage="producer_projection",
        ) from error
    if not isinstance(batch, ProducerProjectionBatch):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.projection_failed",
            "Producer adapter returned an invalid projection result.",
            stage="producer_projection",
        )
    declaration = adapter.declaration
    if (
        batch.adapter_id != declaration.adapter_id
        or batch.adapter_contract_version != declaration.adapter_contract_version
        or batch.reader_id != declaration.public_reader_id
        or batch.reader_contract_version != declaration.reader_contract_version
        or batch.candidate_projection_contract_version
        != declaration.candidate_projection_contract_version
        or batch.support_key != declaration.support_key
    ):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.projection_failed",
            "Producer projection provenance disagrees with the selected adapter.",
            stage="producer_projection",
        )
    return batch.projected_sources


def _relationship_key(
    value: ProjectedProducerRelationship,
) -> tuple[str, str, str, str, str | None]:
    return (
        value.source_subject_kind,
        value.source_subject_id,
        value.relationship_kind,
        value.relationship_authority,
        value.supporting_source_reference,
    )


def _persisted_relationship_keys(
    endpoint: CandidateSourceEndpoint,
) -> tuple[tuple[str, str, str, str, str | None], ...]:
    return tuple(
        (
            value.source_subject_kind,
            value.source_subject_id,
            value.relationship_kind,
            value.relationship_authority,
            value.supporting_source_reference,
        )
        for value in endpoint.subject_relationship_assertions
    )


def _source_matches_persisted_endpoint(
    source: ProjectedProducerSource,
    endpoint: CandidateSourceEndpoint,
) -> bool:
    if (
        source.producer_source != endpoint.producer_source
        or source.source_artifact != endpoint.source_artifact
        or source.source_privacy != endpoint.source_privacy
    ):
        return False
    projected_relationships = {
        _relationship_key(value) for value in source.source_relationships
    }
    return all(
        value in projected_relationships
        for value in _persisted_relationship_keys(endpoint)
    )


_STRUCTURED_PREVIEW_ALLOWLIST: Final[
    dict[str, tuple[tuple[str, str], ...]]
] = {
    "scoreform": (
        ("attempt_number", "Attempt"),
        ("recorded_at", "Recorded"),
        ("points_earned", "Points earned"),
        ("points_possible", "Points possible"),
        ("question_count", "Questions"),
        ("response_states", "Response summary"),
        ("question_standard_alignments", "Standards / alignment"),
        ("standard_alignments", "Standards / alignment"),
    ),
    "quillan": (
        ("writing_type", "Writing type"),
        ("submission_state", "Submission"),
        ("review_state", "Review status"),
        ("minimum_requirement_status", "Minimum requirement"),
        ("rating_scale_id", "Rating scale"),
        ("rating_scale_values", "Rating scale values"),
        ("observation_standard_ids", "Observed standards"),
        ("observation_evidence_present", "Evidence present"),
        ("observation_ratings", "Observation ratings"),
        ("overall_rating_standard_ids", "Overall rating standards"),
        ("overall_rating_values", "Overall ratings"),
    ),
    "concord": (
        ("activity_title", "Activity"),
        ("criterion_label", "Criterion"),
        ("criterion_definition", "Criterion definition"),
        ("criterion_standard_id", "Criterion standard"),
        ("criterion_alignment_standard_ids", "Standards / alignment"),
        ("scoring_scale_name", "Scale"),
        ("score_target_kind", "Target type"),
        ("score_disposition", "Status"),
        ("score_native_value", "Score"),
        ("score_scored_at", "Recorded"),
        ("score_moderation_complete", "Moderation complete"),
        ("disposition", "Status"),
        ("scale_id", "Scale"),
        ("target_kind", "Target type"),
        ("native_value", "Score"),
    ),
}


def _structured_preview_family(module_id: str) -> str | None:
    if module_id in {"scoreform", "vitrine_scoreform_fixture"}:
        return "scoreform"
    if module_id in {"quillan", "vitrine_quillan_fixture"}:
        return "quillan"
    if module_id in {"concord", "vitrine_concord_fixture"}:
        return "concord"
    return None


def _structured_preview_evidence_kind(family: str | None) -> str:
    if family == "scoreform":
        return "Assessment Attempt"
    if family == "quillan":
        return "Review"
    if family == "concord":
        return "Assessment Evidence"
    return "Evidence Summary"


def _structured_preview_value(value: object) -> str:
    values = value if isinstance(value, tuple) else (value,)
    rendered: list[str] = []
    for item in values[:24]:
        if item is None:
            continue
        if isinstance(item, bool):
            rendered.append("Yes" if item else "No")
        else:
            rendered.append(str(item))
    if not rendered:
        return "Not recorded"
    text = ", ".join(rendered)
    if isinstance(value, tuple) and len(value) > 24:
        text += f" … (+{len(value) - 24} more)"
    if len(text) > 1200:
        text = text[:1197].rstrip() + "..."
    return text


def build_candidate_evidence_structured_preview(
    authority: CandidateEvidencePreviewAuthority,
    source: ProjectedProducerSource,
) -> CandidateEvidenceStructuredPreview:
    """Build a deliberate allowlisted summary from one verified projection."""

    if not isinstance(authority, CandidateEvidencePreviewAuthority):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.invalid_request",
            "Structured preview authority is invalid.",
            stage="structured_preview",
        )
    if not isinstance(source, ProjectedProducerSource):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.invalid_request",
            "Structured preview source is invalid.",
            stage="structured_preview",
        )
    if source.source_artifact.artifact_kind != "assessment_summary":
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.invalid_request",
            "Structured preview requires assessment-summary evidence.",
            stage="structured_preview",
        )

    family = _structured_preview_family(
        source.producer_source.producer_module_id
    )
    allowlist = _STRUCTURED_PREVIEW_ALLOWLIST.get(family or "", ())
    by_key = {item.key: item.value for item in source.display_snapshot.fields}
    fields = tuple(
        CandidateEvidenceStructuredField(
            source_key=source_key,
            label=label,
            value=_structured_preview_value(by_key[source_key]),
        )
        for source_key, label in allowlist
        if source_key in by_key
    )

    registration = authority.source_endpoint.core_publication.registration_snapshot
    title = (
        registration.title_snapshot
        if registration is not None
        else source.display_snapshot.title
    )
    return CandidateEvidenceStructuredPreview(
        title=title,
        evidence_kind=_structured_preview_evidence_kind(family),
        fields=fields,
    )



def _classify_preview_source(
    source: ProjectedProducerSource,
) -> tuple[str, bool, str | None]:
    kind = source.source_artifact.artifact_kind
    if kind == "assessment_summary":
        return "structured_summary", False, None
    if kind in {
        "original_student_work",
        "rendered_feedback",
        "collaborative_artifact",
    }:
        return "artifact_preview", True, None
    return (
        "preview_unavailable",
        False,
        "This exact source has no supported Candidate preview representation.",
    )


def _require_preview_authority_still_current(
    workspace_root: str | Path,
    authority: CandidateEvidencePreviewAuthority,
) -> None:
    try:
        detail = get_candidate_inbox_detail(workspace_root, authority.entry_id)
    except CandidateInboxError as error:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.state_conflict",
            "Candidate state changed while preview authority was being revalidated.",
            stage="state_replay",
        ) from error
    item = detail.item
    if (
        detail.observed_state_revision != authority.observed_state_revision
        or item.portfolio_id != authority.portfolio_id
        or item.portfolio_subject_id != authority.portfolio_subject_id
        or item.candidate_id != authority.candidate_id
        or item.current_evaluation_id != authority.candidate_evaluation_id
    ):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.state_conflict",
            "Candidate state changed while preview authority was being revalidated.",
            stage="state_replay",
        )


def prepare_candidate_evidence_preview(
    workspace_root: str | Path,
    request: CandidateEvidencePreviewRequest,
    *,
    adapter_registry: ProducerProjectionAdapterRegistry,
    source_read_authorization_gate: SourceReadAuthorizationGate,
) -> CandidateEvidencePreviewResult:
    """Revalidate one exact Candidate source and classify its preview form.

    This stage acquires no producer Artifact bytes. ``artifact_preview`` means
    byte-bearing preview is supported by the exact source shape and will require
    the separate Candidate evidence-preview authorization contract before a
    later acquisition step.
    """
    authority = resolve_candidate_evidence_preview_authority(
        workspace_root,
        request,
    )
    reference = authority.source_endpoint.core_publication
    publication = _load_exact_preview_publication(workspace_root, reference)
    registration = _load_exact_preview_registration(
        workspace_root,
        publication,
        reference,
    )
    adapter = _select_preview_adapter(
        adapter_registry,
        _preview_adapter_request(publication, registration),
    )
    public_model = _read_preview_public_model(
        workspace_root,
        authority=authority,
        publication=publication,
        adapter=adapter,
        authorization_gate=source_read_authorization_gate,
    )
    projected_sources = _project_preview_sources(adapter, public_model)
    matches = tuple(
        source
        for source in projected_sources
        if _source_matches_persisted_endpoint(
            source,
            authority.source_endpoint,
        )
    )
    if len(matches) != 1:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.source_drift",
            "Producer state does not resolve to exactly the persisted Candidate source.",
            stage="source_revalidation",
        )
    verified_source = matches[0]
    preview_kind, authorization_required, unavailable_reason = (
        _classify_preview_source(verified_source)
    )
    structured_preview = (
        build_candidate_evidence_structured_preview(
            authority,
            verified_source,
        )
        if preview_kind == "structured_summary"
        else None
    )
    _require_preview_authority_still_current(workspace_root, authority)
    return CandidateEvidencePreviewResult(
        contract_version=CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION,
        preview_kind=preview_kind,
        authority=authority,
        verified_source=verified_source,
        artifact_authorization_required=authorization_required,
        structured_preview=structured_preview,
        unavailable_reason=unavailable_reason,
    )


def build_candidate_evidence_preview_authorization_request(
    authority: CandidateEvidencePreviewAuthority,
) -> CandidateEvidencePreviewAuthorizationRequest:
    """Build exact producer-Artifact authorization context from resolved state."""

    if not isinstance(authority, CandidateEvidencePreviewAuthority):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.invalid_request",
            "authority must be CandidateEvidencePreviewAuthority.",
            stage="authorization_request",
        )
    return CandidateEvidencePreviewAuthorizationRequest(
        operation=CANDIDATE_EVIDENCE_PREVIEW_OPERATION,
        portfolio_id=authority.portfolio_id,
        portfolio_subject_id=authority.portfolio_subject_id,
        candidate_id=authority.candidate_id,
        candidate_evaluation_id=authority.candidate_evaluation_id,
        source_publication_id=authority.source_publication_id,
        producer_module_id=authority.producer_module_id,
        source_artifact_id=authority.source_artifact_id,
        artifact_kind=authority.artifact_kind,
        representation_kind=authority.representation_kind,
        requesting_actor=authority.requesting_actor,
        purpose=authority.requested_purpose,
    )


def authorize_candidate_evidence_preview(
    gate: CandidateEvidencePreviewAuthorizationGate,
    request: CandidateEvidencePreviewAuthorizationRequest,
) -> CandidateEvidencePreviewAuthorizationDecision:
    """Require one explicit allowed preview decision and otherwise fail closed."""

    if not isinstance(request, CandidateEvidencePreviewAuthorizationRequest):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.invalid_request",
            "Preview authorization request is invalid.",
            stage="authorization_request",
        )
    try:
        decision = gate.authorize(request)
    except Exception as error:
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.authorization_unresolved",
            "Candidate evidence-preview authorization could not be established.",
            stage="authorization",
        ) from error
    if not isinstance(
        decision,
        CandidateEvidencePreviewAuthorizationDecision,
    ):
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.authorization_unresolved",
            "Candidate evidence-preview gate returned an invalid decision.",
            stage="authorization",
        )
    if decision.outcome == "denied":
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.authorization_denied",
            "Candidate evidence-preview authorization was denied.",
            stage="authorization",
        )
    if decision.outcome != "allowed":
        raise CandidateEvidencePreviewError(
            "candidate_evidence_preview.authorization_unresolved",
            "Candidate evidence-preview authorization is unresolved.",
            stage="authorization",
        )
    return decision


__all__ = [
    "CANDIDATE_EVIDENCE_PREVIEW_AUTHORIZATION_OUTCOMES",
    "CANDIDATE_EVIDENCE_PREVIEW_CODES",
    "CANDIDATE_EVIDENCE_PREVIEW_CONTRACT_VERSION",
    "CANDIDATE_EVIDENCE_PREVIEW_KINDS",
    "CANDIDATE_EVIDENCE_PREVIEW_MANIFEST_OPERATION",
    "CANDIDATE_EVIDENCE_PREVIEW_OPERATION",
    "CandidateEvidencePreviewAuthorizationDecision",
    "CandidateEvidencePreviewAuthorizationGate",
    "CandidateEvidencePreviewAuthorizationRequest",
    "CandidateEvidencePreviewAuthority",
    "CandidateEvidencePreviewError",
    "CandidateEvidencePreviewRequest",
    "CandidateEvidencePreviewResult",
    "CandidateEvidenceStructuredField",
    "CandidateEvidenceStructuredPreview",
    "authorize_candidate_evidence_preview",
    "build_candidate_evidence_preview_authorization_request",
    "build_candidate_evidence_structured_preview",
    "prepare_candidate_evidence_preview",
    "resolve_candidate_evidence_preview_authority",
]
