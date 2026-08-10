"""Core-backed Candidate discovery and evaluation application services.

The Core academic catalog is used only to propose publication IDs.  Every source
fact is reloaded from canonical Core state before authorization, manifest access,
producer reading, Portfolio Subject resolution, Profile evaluation, or Vitrine
persistence.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Protocol

from pds_core.academic_catalog import (
    AcademicCatalogCompatibilityError,
    AcademicCatalogConflictError,
    AcademicCatalogIntegrityError,
    AcademicCatalogNotFoundError,
    AcademicCatalogReadError,
    AcademicCatalogSourceError,
    CatalogPublication,
    PublicationCatalogQuery,
    query_publication_catalog,
)
from pds_core.academic_work_registration_storage import (
    AcademicWorkRegistrationIntegrityError,
    AcademicWorkRegistrationNotFoundError,
    AcademicWorkRegistrationReadError,
    load_academic_work_registration_revision,
)
from pds_core.academic_work_registrations import AcademicWorkRegistration
from pds_core.class_metadata import ClassMetadataError, load_class_metadata_for_class
from pds_core.publication_compatibility import (
    PublicationProducerProfileError,
    PublicationProducerRegistry,
    evaluate_publication_compatibility,
)
from pds_core.publication_records import PublicationRecord
from pds_core.publication_storage import (
    PublicationIntegrityError,
    PublicationManifestError,
    PublicationManifestIntegrityError,
    PublicationManifestNotFoundError,
    PublicationReadError,
    list_publication_record_set,
    verify_publication_manifest,
)
from pds_core.registry_services import (
    RegistryServiceIntegrityError,
    RegistryServiceNotFoundError,
    RegistryServiceWriteError,
    get_canonical_publication_record,
    get_canonical_publication_withdrawal,
)

from vitrine.identity_state import (
    collect_identity_state_issues,
    project_identity_state,
)
from vitrine.models import (
    AcademicWorkRegistrationSnapshot,
    ActorAttribution,
    CandidateAvailabilityObservation,
    CandidateEvaluation,
    CandidateSourceEndpoint,
    ClassQualifiedStudentRef,
    CorePublicationSourceReference,
    Portfolio,
    PortfolioCandidate,
    PortfolioProfileBinding,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioSubject,
    PortfolioSubjectRelationshipAssertion,
    VitrineRecord,
)
from vitrine.models.common import (
    lower_key_tuple,
    require_controlled_key,
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
    ProducerProjectionError,
    ProducerReaderError,
    ProjectedProducerSource,
)
from vitrine.profile_state import collect_profile_state_issues, project_profile_state
from vitrine.storage import (
    VitrineStorageConflictError,
    VitrineStorageError,
    VitrineStorageNotFoundError,
    commit_record_batch,
    load_current_state,
    load_state_records,
    load_store_marker,
)

CANDIDATE_EVALUATOR_CONTRACT_VERSION: Final[str] = "vitrine_candidate_evaluator_v1"
SOURCE_READ_OPERATION: Final[str] = "candidate_source_read"
_AUTHORIZATION_OUTCOMES: Final[frozenset[str]] = frozenset(
    {"allowed", "denied", "unresolved"}
)
_RESULT_DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {"created", "existing", "evaluation_only"}
)

CANDIDATE_KIND_BY_ARTIFACT_KIND: Final[dict[str, str]] = {
    "assessment_summary": "assessment_summary",
    "collaborative_artifact": "student_work",
    "original_student_work": "student_work",
    "rendered_feedback": "feedback",
}

CANDIDATE_WORKFLOW_CODES: Final[frozenset[str]] = frozenset(
    {
        "candidate.invalid_request",
        "candidate.context_not_found",
        "candidate.profile_binding_missing",
        "candidate.profile_binding_conflict",
        "candidate.catalog_unavailable",
        "candidate.catalog_incompatible",
        "candidate.catalog_read_failed",
        "candidate.no_matching_publication",
        "candidate.canonical_publication_missing",
        "candidate.canonical_publication_invalid",
        "candidate.catalog_drift",
        "candidate.registration_missing",
        "candidate.registration_mismatch",
        "candidate.series_conflict",
        "candidate.publication_not_selectable",
        "candidate.producer_profile_missing",
        "candidate.producer_incompatible",
        "candidate.adapter_unsupported",
        "candidate.adapter_conflict",
        "candidate.authorization_denied",
        "candidate.authorization_unresolved",
        "candidate.manifest_missing",
        "candidate.manifest_integrity_failed",
        "candidate.reader_failed",
        "candidate.projection_failed",
        "candidate.subject_unresolved",
        "candidate.subject_conflict",
        "candidate.profile_ineligible",
        "candidate.state_conflict",
    }
)

Clock = Callable[[], datetime]
IdFactory = Callable[[str], str]


class CandidateWorkflowError(RuntimeError):
    """Expected Candidate workflow failure with stable privacy-safe metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        diagnostic_fields: tuple[tuple[str, str], ...] = (),
    ) -> None:
        if code not in CANDIDATE_WORKFLOW_CODES:
            raise ValueError(f"unsupported Candidate workflow code: {code}")
        self.code = code
        self.stage = stage
        self.diagnostic_fields = tuple(sorted(diagnostic_fields))
        super().__init__(message)


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceReadAuthorizationRequest:
    portfolio_id: str
    portfolio_subject_id: str
    publication_id: str
    operation: str
    purpose: str

    def __post_init__(self) -> None:
        try:
            for name in ("portfolio_id", "portfolio_subject_id", "publication_id"):
                object.__setattr__(
                    self, name, require_identifier(getattr(self, name), name)
                )
            object.__setattr__(
                self,
                "operation",
                require_controlled_key(self.operation, "operation"),
            )
            object.__setattr__(
                self, "purpose", require_text(self.purpose, "purpose", maximum=500)
            )
        except VitrineModelValidationError as error:
            raise CandidateWorkflowError(
                "candidate.invalid_request",
                "Source-read authorization request is invalid.",
                stage="authorization_request",
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceReadAuthorizationDecision:
    outcome: str
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.outcome not in _AUTHORIZATION_OUTCOMES:
            raise CandidateWorkflowError(
                "candidate.invalid_request",
                "Source-read authorization outcome is invalid.",
                stage="authorization",
            )
        try:
            object.__setattr__(
                self,
                "reason_codes",
                lower_key_tuple(self.reason_codes, "reason_codes"),
            )
        except VitrineModelValidationError as error:
            raise CandidateWorkflowError(
                "candidate.invalid_request",
                "Source-read authorization reason codes are invalid.",
                stage="authorization",
            ) from error


class SourceReadAuthorizationGate(Protocol):
    def authorize(
        self, request: SourceReadAuthorizationRequest
    ) -> SourceReadAuthorizationDecision: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateDiscoveryRequest:
    portfolio_id: str
    requesting_actor: ActorAttribution
    requested_purpose: str
    catalog_query: PublicationCatalogQuery
    expected_state_revision: int

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "portfolio_id",
                require_identifier(self.portfolio_id, "portfolio_id"),
            )
            object.__setattr__(
                self,
                "requested_purpose",
                require_text(self.requested_purpose, "requested_purpose", maximum=500),
            )
            object.__setattr__(
                self,
                "expected_state_revision",
                require_positive_int(
                    self.expected_state_revision, "expected_state_revision"
                ),
            )
        except VitrineModelValidationError as error:
            raise CandidateWorkflowError(
                "candidate.invalid_request",
                "Candidate discovery request is invalid.",
                stage="request",
            ) from error
        if not isinstance(self.requesting_actor, ActorAttribution):
            raise CandidateWorkflowError(
                "candidate.invalid_request",
                "requesting_actor must be ActorAttribution.",
                stage="request",
            )
        if not isinstance(self.catalog_query, PublicationCatalogQuery):
            raise CandidateWorkflowError(
                "candidate.invalid_request",
                "catalog_query must be PublicationCatalogQuery.",
                stage="request",
            )
        limit = self.catalog_query.limit
        if limit is None:
            raise CandidateWorkflowError(
                "candidate.invalid_request",
                "Candidate discovery requires an explicit bounded catalog limit.",
                stage="request",
            )
        if limit > 1000:
            raise CandidateWorkflowError(
                "candidate.invalid_request",
                "Candidate discovery catalog limit must not exceed 1000.",
                stage="request",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateDiscoveryFinding:
    code: str
    stage: str
    proposed_publication_id: str | None = None
    diagnostic_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.code not in CANDIDATE_WORKFLOW_CODES:
            raise ValueError(f"unsupported Candidate finding code: {self.code}")
        if not isinstance(self.stage, str) or not self.stage:
            raise ValueError("stage must be nonempty.")
        if self.proposed_publication_id is not None:
            require_identifier(self.proposed_publication_id, "proposed_publication_id")
        codes = tuple(self.diagnostic_codes)
        if any(not isinstance(code, str) or not code for code in codes):
            raise ValueError("diagnostic_codes must contain nonempty strings.")
        object.__setattr__(self, "diagnostic_codes", tuple(sorted(set(codes))))


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvaluationResult:
    publication_id: str
    projected_source: ProjectedProducerSource
    evaluation: CandidateEvaluation
    candidate: PortfolioCandidate | None
    disposition: str

    def __post_init__(self) -> None:
        require_identifier(self.publication_id, "publication_id")
        if not isinstance(self.projected_source, ProjectedProducerSource):
            raise ValueError("projected_source must be ProjectedProducerSource.")
        if not isinstance(self.evaluation, CandidateEvaluation):
            raise ValueError("evaluation must be CandidateEvaluation.")
        if self.candidate is not None and not isinstance(self.candidate, PortfolioCandidate):
            raise ValueError("candidate must be PortfolioCandidate or null.")
        if self.disposition not in _RESULT_DISPOSITIONS:
            raise ValueError("unsupported Candidate evaluation disposition.")


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateDiscoveryResult:
    proposed_publication_ids: tuple[str, ...]
    findings: tuple[CandidateDiscoveryFinding, ...]
    evaluation_results: tuple[CandidateEvaluationResult, ...]
    committed_state_revision: int | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "proposed_publication_ids",
            tuple(self.proposed_publication_ids),
        )
        if len(set(self.proposed_publication_ids)) != len(
            self.proposed_publication_ids
        ):
            raise ValueError("proposed_publication_ids must be unique.")
        object.__setattr__(self, "findings", tuple(self.findings))
        object.__setattr__(self, "evaluation_results", tuple(self.evaluation_results))
        if self.committed_state_revision is not None:
            require_positive_int(
                self.committed_state_revision, "committed_state_revision"
            )


def _clock() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CandidateWorkflowError(
            "candidate.invalid_request",
            "Candidate service clock must return a timezone-aware datetime.",
            stage="clock",
        )
    return value.astimezone(timezone.utc)


def _finding(error: CandidateWorkflowError, publication_id: str | None) -> CandidateDiscoveryFinding:
    diagnostic_codes = tuple(value for key, value in error.diagnostic_fields if key == "code")
    return CandidateDiscoveryFinding(
        code=error.code,
        stage=error.stage,
        proposed_publication_id=publication_id,
        diagnostic_codes=diagnostic_codes,
    )


def _catalog_failure(error: BaseException) -> CandidateWorkflowError:
    if isinstance(error, AcademicCatalogNotFoundError):
        code = "candidate.catalog_unavailable"
    elif isinstance(error, AcademicCatalogCompatibilityError):
        code = "candidate.catalog_incompatible"
    else:
        code = "candidate.catalog_read_failed"
    return CandidateWorkflowError(
        code,
        "Core academic catalog could not be used safely.",
        stage="catalog",
    )


def _load_vitrine_context(
    workspace_root: str | Path,
    request: CandidateDiscoveryRequest,
) -> tuple[
    tuple[VitrineRecord, ...],
    Portfolio,
    PortfolioSubject,
    PortfolioProfileBinding,
    PortfolioProfileRevision,
    tuple[PortfolioProfileRequirement, ...],
]:
    try:
        load_store_marker(workspace_root)
        current = load_current_state(workspace_root)
    except VitrineStorageNotFoundError as error:
        raise CandidateWorkflowError(
            "candidate.context_not_found",
            "Vitrine canonical state does not exist.",
            stage="context",
        ) from error
    except VitrineStorageError as error:
        raise CandidateWorkflowError(
            "candidate.context_not_found",
            "Vitrine canonical state could not be validated.",
            stage="context",
        ) from error
    if current.state_revision != request.expected_state_revision:
        raise CandidateWorkflowError(
            "candidate.state_conflict",
            "Vitrine state changed before Candidate evaluation began.",
            stage="context",
        )
    try:
        records = load_state_records(workspace_root, current.state_revision)
    except VitrineStorageError as error:
        raise CandidateWorkflowError(
            "candidate.context_not_found",
            "Vitrine canonical context could not be loaded safely.",
            stage="context",
        ) from error

    profile_state = project_profile_state(records)
    profile_issues = collect_profile_state_issues(profile_state)
    if profile_issues:
        raise CandidateWorkflowError(
            "candidate.context_not_found",
            "Portfolio Profile state is invalid.",
            stage="context",
        )
    identity_state = project_identity_state(records)
    identity_issues = tuple(
        issue
        for issue in collect_identity_state_issues(identity_state)
        if issue.code != "identity.duplicate_active_association"
    )
    if identity_issues:
        raise CandidateWorkflowError(
            "candidate.context_not_found",
            "Portfolio Subject identity state is invalid.",
            stage="context",
        )

    portfolio = next(
        (
            item
            for item in profile_state.portfolios
            if item.portfolio_id == request.portfolio_id
        ),
        None,
    )
    if portfolio is None:
        raise CandidateWorkflowError(
            "candidate.context_not_found",
            "Portfolio does not exist.",
            stage="context",
        )
    subject = next(
        (
            item
            for item in identity_state.subjects
            if item.portfolio_subject_id == portfolio.portfolio_subject_id
        ),
        None,
    )
    if subject is None:
        raise CandidateWorkflowError(
            "candidate.context_not_found",
            "Portfolio Subject does not exist.",
            stage="context",
        )
    binding_heads = profile_state.active_binding_heads(portfolio.portfolio_id)
    if not binding_heads:
        raise CandidateWorkflowError(
            "candidate.profile_binding_missing",
            "Portfolio has no active Profile Binding head.",
            stage="context",
        )
    if len(binding_heads) != 1:
        raise CandidateWorkflowError(
            "candidate.profile_binding_conflict",
            "Portfolio has multiple unresolved Profile Binding heads.",
            stage="context",
        )
    binding = binding_heads[0]
    revision = profile_state.revision(binding.profile_revision)
    if revision is None or revision.purpose_kind not in {"improvement", "showcase"}:
        raise CandidateWorkflowError(
            "candidate.context_not_found",
            "Bound Profile Revision is unavailable for Candidate evaluation.",
            stage="context",
        )
    requirements = profile_state.requirements_for(binding.profile_revision)
    return records, portfolio, subject, binding, revision, requirements


def _catalog_matches_canonical(row: CatalogPublication, record: PublicationRecord) -> bool:
    return (
        row.publication_id == record.publication_id
        and row.work == record.work
        and row.source_record == record.source_record
        and row.publication_kind == record.publication_kind
        and tuple(row.capabilities) == tuple(record.capabilities)
        and row.record_set_id == record.record_set_id
        and row.record_set_revision == record.record_set_revision
        and row.manifest_contract_version == record.manifest_contract_version
        and row.manifest_path == record.manifest_path
        and row.manifest_digest_algorithm == record.manifest_digest_algorithm
        and row.manifest_digest == record.manifest_digest
        and row.published_at == record.published_at
        and row.academic_work_registration_revision
        == record.academic_work_registration_revision
        and row.supersedes_publication_id == record.supersedes_publication_id
    )


def _load_canonical_publication(
    workspace_root: str | Path, row: CatalogPublication
) -> PublicationRecord:
    try:
        record = get_canonical_publication_record(workspace_root, row.publication_id)
    except RegistryServiceNotFoundError as error:
        raise CandidateWorkflowError(
            "candidate.canonical_publication_missing",
            "Catalog proposal no longer resolves to a canonical Publication Record.",
            stage="canonical_publication",
        ) from error
    except (RegistryServiceIntegrityError, RegistryServiceWriteError) as error:
        raise CandidateWorkflowError(
            "candidate.canonical_publication_invalid",
            "Canonical Publication Record could not be validated.",
            stage="canonical_publication",
        ) from error
    if not _catalog_matches_canonical(row, record):
        raise CandidateWorkflowError(
            "candidate.catalog_drift",
            "Catalog proposal differs from canonical Publication state.",
            stage="canonical_publication",
        )
    return record


def _load_registration(
    workspace_root: str | Path, publication: PublicationRecord
) -> AcademicWorkRegistration | None:
    if publication.publication_kind != "academic_result_set":
        return None
    revision = publication.academic_work_registration_revision
    if revision is None:
        raise CandidateWorkflowError(
            "candidate.registration_missing",
            "Academic Publication has no referenced registration revision.",
            stage="registration",
        )
    try:
        registration = load_academic_work_registration_revision(
            workspace_root, publication.work, revision
        )
    except AcademicWorkRegistrationNotFoundError as error:
        raise CandidateWorkflowError(
            "candidate.registration_missing",
            "Referenced Academic Work Registration revision does not exist.",
            stage="registration",
        ) from error
    except (
        AcademicWorkRegistrationIntegrityError,
        AcademicWorkRegistrationReadError,
    ) as error:
        raise CandidateWorkflowError(
            "candidate.registration_mismatch",
            "Referenced Academic Work Registration could not be validated.",
            stage="registration",
        ) from error
    if (
        registration.work != publication.work
        or registration.registration_revision != revision
    ):
        raise CandidateWorkflowError(
            "candidate.registration_mismatch",
            "Referenced Academic Work Registration disagrees with Publication identity.",
            stage="registration",
        )
    return registration


def _series_state(
    workspace_root: str | Path, publication: PublicationRecord
) -> tuple[str, str]:
    try:
        series = list_publication_record_set(
            workspace_root,
            publication.work,
            publication.publication_kind,
            publication.record_set_id,
        )
    except (PublicationIntegrityError, PublicationReadError) as error:
        raise CandidateWorkflowError(
            "candidate.series_conflict",
            "Canonical Publication series could not be validated.",
            stage="series_state",
        ) from error
    successor_ids = {
        item.supersedes_publication_id
        for item in series
        if item.supersedes_publication_id is not None
    }
    heads = tuple(item for item in series if item.publication_id not in successor_ids)
    if len(heads) != 1:
        raise CandidateWorkflowError(
            "candidate.series_conflict",
            "Canonical Publication series has no unique explicit head.",
            stage="series_state",
        )
    try:
        withdrawal = get_canonical_publication_withdrawal(
            workspace_root, publication.publication_id
        )
    except (
        RegistryServiceNotFoundError,
        RegistryServiceIntegrityError,
        RegistryServiceWriteError,
    ) as error:
        raise CandidateWorkflowError(
            "candidate.series_conflict",
            "Canonical Publication withdrawal state could not be validated.",
            stage="series_state",
        ) from error
    is_head = heads[0].publication_id == publication.publication_id
    is_withdrawn = withdrawal is not None
    if is_head and not is_withdrawn:
        return "current_selectable", "not_withdrawn"
    if is_head:
        return "withdrawn_head", "withdrawn"
    if is_withdrawn:
        return "withdrawn_historical", "withdrawn"
    return "historical", "not_withdrawn"


def _adapter_request(
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


def _select_adapter(
    registry: ProducerProjectionAdapterRegistry,
    request: ProducerAdapterSupportRequest,
) -> ProducerProjectionAdapter:
    try:
        return registry.select_adapter(request)
    except ProducerAdapterUnsupportedError as error:
        raise CandidateWorkflowError(
            "candidate.adapter_unsupported",
            "No exact Vitrine adapter supports the canonical Publication contract.",
            stage="adapter_support",
            diagnostic_fields=(("code", error.code),),
        ) from error
    except ProducerAdapterConflictError as error:
        raise CandidateWorkflowError(
            "candidate.adapter_conflict",
            "More than one Vitrine adapter claims the canonical Publication contract.",
            stage="adapter_support",
            diagnostic_fields=(("code", error.code),),
        ) from error
    except ProducerAdapterError as error:
        raise CandidateWorkflowError(
            "candidate.adapter_unsupported",
            "Vitrine adapter selection failed safely.",
            stage="adapter_support",
            diagnostic_fields=(("code", error.code),),
        ) from error


def _authorize(
    gate: SourceReadAuthorizationGate,
    *,
    portfolio: Portfolio,
    publication: PublicationRecord,
    purpose: str,
) -> SourceReadAuthorizationDecision:
    request = SourceReadAuthorizationRequest(
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        publication_id=publication.publication_id,
        operation=SOURCE_READ_OPERATION,
        purpose=purpose,
    )
    try:
        decision = gate.authorize(request)
    except Exception as error:
        raise CandidateWorkflowError(
            "candidate.authorization_unresolved",
            "Source-read authorization could not be established.",
            stage="source_authorization",
        ) from error
    if not isinstance(decision, SourceReadAuthorizationDecision):
        raise CandidateWorkflowError(
            "candidate.authorization_unresolved",
            "Source-read authorization gate returned an invalid decision.",
            stage="source_authorization",
        )
    if decision.outcome == "denied":
        raise CandidateWorkflowError(
            "candidate.authorization_denied",
            "Source-read authorization was denied.",
            stage="source_authorization",
        )
    if decision.outcome != "allowed":
        raise CandidateWorkflowError(
            "candidate.authorization_unresolved",
            "Source-read authorization is unresolved.",
            stage="source_authorization",
        )
    return decision


def _read_verified_manifest_bytes(
    workspace_root: str | Path, publication: PublicationRecord
) -> bytes:
    lexical_root = Path(workspace_root).absolute()
    lexical_path = lexical_root.joinpath(*publication.manifest_path.split("/"))
    current = lexical_path
    try:
        while current != lexical_root:
            if current.is_symlink():
                raise CandidateWorkflowError(
                    "candidate.manifest_integrity_failed",
                    "Canonical Publication manifest path traverses a symlink.",
                    stage="manifest_integrity",
                )
            current = current.parent
    except OSError as error:
        raise CandidateWorkflowError(
            "candidate.manifest_integrity_failed",
            "Canonical Publication manifest path could not be inspected safely.",
            stage="manifest_integrity",
        ) from error
    try:
        path = verify_publication_manifest(workspace_root, publication)
    except PublicationManifestNotFoundError as error:
        raise CandidateWorkflowError(
            "candidate.manifest_missing",
            "Canonical Publication manifest is unavailable.",
            stage="manifest_integrity",
        ) from error
    except (PublicationManifestIntegrityError, PublicationManifestError) as error:
        raise CandidateWorkflowError(
            "candidate.manifest_integrity_failed",
            "Canonical Publication manifest failed integrity verification.",
            stage="manifest_integrity",
        ) from error
    try:
        data = path.read_bytes()
    except OSError as error:
        raise CandidateWorkflowError(
            "candidate.manifest_missing",
            "Verified Publication manifest could not be read.",
            stage="manifest_integrity",
        ) from error
    actual = hashlib.sha256(data).hexdigest()
    if not hmac.compare_digest(actual, publication.manifest_digest):
        raise CandidateWorkflowError(
            "candidate.manifest_integrity_failed",
            "Publication manifest changed before producer reading.",
            stage="manifest_integrity",
        )
    return data


def _project(
    adapter: ProducerProjectionAdapter, data: bytes
) -> tuple[ProjectedProducerSource, ...]:
    try:
        public_model = adapter.reader.read(data)
    except ProducerReaderError as error:
        raise CandidateWorkflowError(
            "candidate.reader_failed",
            "Producer public reader rejected the verified manifest.",
            stage="producer_reader",
            diagnostic_fields=(("code", error.code),),
        ) from error
    try:
        batch = adapter.project(public_model)
    except ProducerProjectionError as error:
        raise CandidateWorkflowError(
            "candidate.projection_failed",
            "Producer projection failed safely.",
            stage="producer_parse",
            diagnostic_fields=(("code", error.code),),
        ) from error
    declaration = adapter.declaration
    if (
        batch.adapter_id != declaration.adapter_id
        or batch.adapter_contract_version != declaration.adapter_contract_version
        or batch.reader_contract_version != declaration.reader_contract_version
        or batch.candidate_projection_contract_version
        != declaration.candidate_projection_contract_version
        or batch.support_key != declaration.support_key
    ):
        raise CandidateWorkflowError(
            "candidate.projection_failed",
            "Producer projection provenance disagrees with the selected adapter.",
            stage="producer_parse",
        )
    return batch.projected_sources


def _core_source_reference(
    publication: PublicationRecord,
    registration: AcademicWorkRegistration | None,
    *,
    series_state: str,
    withdrawal_state: str,
    verified_at: datetime,
) -> CorePublicationSourceReference:
    snapshot = (
        None
        if registration is None
        else AcademicWorkRegistrationSnapshot(
            registration_revision=registration.registration_revision,
            producer_contract_version=registration.producer_contract_version,
            title_snapshot=registration.title,
            work_kind=registration.work_kind,
            academic_intent=registration.academic_intent,
            lifecycle=registration.lifecycle,
            source_records=registration.source_records,
        )
    )
    return CorePublicationSourceReference(
        core_publication_schema_version=publication.schema_version,
        publication_id=publication.publication_id,
        work=publication.work,
        source_record=publication.source_record,
        publication_kind=publication.publication_kind,
        capabilities=tuple(publication.capabilities),
        record_set_id=publication.record_set_id,
        record_set_revision=publication.record_set_revision,
        manifest_contract_version=publication.manifest_contract_version,
        manifest_path=publication.manifest_path,
        manifest_digest_algorithm=publication.manifest_digest_algorithm,
        manifest_digest=publication.manifest_digest,
        published_at=publication.published_at,
        academic_work_registration_revision=publication.academic_work_registration_revision,
        registration_snapshot=snapshot,
        supersedes_publication_id=publication.supersedes_publication_id,
        observed_series_state=series_state,
        observed_withdrawal_state=withdrawal_state,
        verified_at=verified_at,
    )


def _assertions_for_source(
    records: tuple[VitrineRecord, ...],
    *,
    source: ProjectedProducerSource,
    publication: PublicationRecord,
    portfolio_subject_id: str,
    school_year: str,
    verified_at: datetime,
    verified_by: ActorAttribution,
    id_factory: IdFactory,
) -> tuple[tuple[PortfolioSubjectRelationshipAssertion, ...], bool]:
    identity_state = project_identity_state(records)
    assertions: list[PortfolioSubjectRelationshipAssertion] = []
    conflict = False
    for relationship in source.source_relationships:
        if relationship.source_subject_kind != "core_student":
            continue
        reference = ClassQualifiedStudentRef(
            class_id=publication.work.class_id,
            student_id=relationship.source_subject_id,
            school_year=school_year,
        )
        subjects = identity_state.current_subjects_for_reference(reference)
        if len(subjects) > 1:
            conflict = True
            continue
        if subjects != (portfolio_subject_id,):
            continue
        links = tuple(
            link
            for link in identity_state.current_links(portfolio_subject_id)
            if link.student_reference == reference
        )
        if len(links) != 1:
            conflict = True
            continue
        link = links[0]
        assertions.append(
            PortfolioSubjectRelationshipAssertion(
                assertion_id=id_factory("source_assertion"),
                portfolio_subject_id=portfolio_subject_id,
                subject_link_id=link.subject_link_id,
                source_subject_kind=relationship.source_subject_kind,
                source_subject_id=relationship.source_subject_id,
                relationship_kind=relationship.relationship_kind,
                relationship_authority=relationship.relationship_authority,
                supporting_source_reference=relationship.supporting_source_reference,
                verified_at=verified_at,
                verified_by=verified_by,
            )
        )
    return (
        tuple(
            sorted(
                assertions,
                key=lambda item: (
                    item.relationship_kind,
                    item.source_subject_kind,
                    item.source_subject_id,
                    item.subject_link_id,
                ),
            )
        ),
        conflict,
    )


def _eligible_profile_sections(
    revision: PortfolioProfileRevision,
    requirements: tuple[PortfolioProfileRequirement, ...],
    source: ProjectedProducerSource,
    assertions: tuple[PortfolioSubjectRelationshipAssertion, ...],
) -> tuple[str | None, tuple[str, ...], tuple[str, ...]]:
    candidate_kind = CANDIDATE_KIND_BY_ARTIFACT_KIND.get(
        source.source_artifact.artifact_kind
    )
    if candidate_kind is None:
        return None, (), ()
    relationship_kinds = {item.relationship_kind for item in assertions}
    eligible: list[str] = []
    for section in revision.sections:
        if section.obligation == "prohibited":
            continue
        if candidate_kind not in section.allowed_candidate_kinds:
            continue
        if not set(section.required_relationship_kinds).issubset(relationship_kinds):
            continue
        eligible.append(section.section_id)
    eligible_ids = tuple(eligible)
    rule_ids = tuple(
        sorted(
            requirement.requirement_id
            for requirement in requirements
            if requirement.requirement_kind == "section"
            and requirement.scope_kind == "section"
            and requirement.scope_reference in eligible_ids
        )
    )
    return candidate_kind, eligible_ids, rule_ids


def _condition_state(source: ProjectedProducerSource) -> str:
    privacy = source.source_privacy
    if privacy.rights_review_required:
        return "rights_review_required"
    if privacy.collaborator_information_present or privacy.multi_subject_review_required:
        return "collaborator_review_required"
    if (
        privacy.redaction_review_required
        or privacy.third_party_information_present
    ):
        return "review_required"
    return "ready_for_consideration"


def _availability(
    now: datetime,
    *,
    registration_present: bool,
    authorization_codes: tuple[str, ...],
    subject_outcome: str,
    profile_outcome: str,
) -> tuple[CandidateAvailabilityObservation, ...]:
    return (
        CandidateAvailabilityObservation(
            dimension="canonical_publication", outcome="loaded", checked_at=now
        ),
        CandidateAvailabilityObservation(
            dimension="registration",
            outcome="loaded" if registration_present else "absent_by_contract",
            checked_at=now,
        ),
        CandidateAvailabilityObservation(
            dimension="series_state", outcome="current_selectable", checked_at=now
        ),
        CandidateAvailabilityObservation(
            dimension="producer_profile", outcome="compatible", checked_at=now
        ),
        CandidateAvailabilityObservation(
            dimension="adapter_support", outcome="selected", checked_at=now
        ),
        CandidateAvailabilityObservation(
            dimension="source_authorization",
            outcome="allowed",
            checked_at=now,
            reason_codes=authorization_codes,
        ),
        CandidateAvailabilityObservation(
            dimension="manifest_integrity", outcome="verified", checked_at=now
        ),
        CandidateAvailabilityObservation(
            dimension="producer_reader", outcome="available", checked_at=now
        ),
        CandidateAvailabilityObservation(
            dimension="producer_parse", outcome="parsed", checked_at=now
        ),
        CandidateAvailabilityObservation(
            dimension="source_resolution", outcome="resolved", checked_at=now
        ),
        CandidateAvailabilityObservation(
            dimension="artifact_availability", outcome="available", checked_at=now
        ),
        CandidateAvailabilityObservation(
            dimension="subject_relationship", outcome=subject_outcome, checked_at=now
        ),
        CandidateAvailabilityObservation(
            dimension="profile_eligibility", outcome=profile_outcome, checked_at=now
        ),
        CandidateAvailabilityObservation(
            dimension="disclosure_review", outcome="not_evaluated", checked_at=now
        ),
    )


def _display_snapshot(source: ProjectedProducerSource) -> str:
    title = source.display_snapshot.title
    summary = source.display_snapshot.summary
    value = title if summary is None else f"{title} — {summary}"
    if len(value) <= 500:
        return value
    return value[:497].rstrip() + "..."


def _assertion_semantic_key(
    value: PortfolioSubjectRelationshipAssertion,
) -> tuple[object, ...]:
    return (
        value.portfolio_subject_id,
        value.subject_link_id,
        value.source_subject_kind,
        value.source_subject_id,
        value.relationship_kind,
        value.relationship_authority,
        value.supporting_source_reference,
    )


def _endpoint_semantic_key(value: CandidateSourceEndpoint) -> tuple[object, ...]:
    return (
        value.core_publication.publication_id,
        value.producer_source,
        value.source_artifact,
        tuple(_assertion_semantic_key(item) for item in value.subject_relationship_assertions),
        value.source_privacy,
    )


def _existing_positive_result(
    records: tuple[VitrineRecord, ...],
    *,
    request: CandidateDiscoveryRequest,
    portfolio: Portfolio,
    binding: PortfolioProfileBinding,
    endpoint: CandidateSourceEndpoint,
    eligible_rule_ids: tuple[str, ...],
    eligible_section_ids: tuple[str, ...],
    outcome: str,
    condition_state: str,
    display_snapshot: str,
    source: ProjectedProducerSource,
) -> CandidateEvaluationResult | None:
    profile_binding_id = binding.profile_binding_id
    profile_revision = binding.profile_revision
    evaluations = {
        item.candidate_evaluation_id: item
        for item in records
        if isinstance(item, CandidateEvaluation)
    }
    for candidate in records:
        if not isinstance(candidate, PortfolioCandidate):
            continue
        if (
            candidate.portfolio_id != portfolio.portfolio_id
            or candidate.portfolio_subject_id != portfolio.portfolio_subject_id
            or candidate.profile_binding_id != profile_binding_id
            or candidate.profile_revision != profile_revision
            or candidate.eligible_profile_rule_ids != eligible_rule_ids
            or candidate.eligible_section_ids != eligible_section_ids
            or candidate.condition_state != condition_state
            or candidate.display_snapshot != display_snapshot
            or _endpoint_semantic_key(candidate.source_endpoint)
            != _endpoint_semantic_key(endpoint)
        ):
            continue
        evaluation = evaluations.get(candidate.candidate_evaluation_id)
        if evaluation is None:
            continue
        if (
            evaluation.requesting_actor == request.requesting_actor
            and evaluation.purpose == request.requested_purpose
            and evaluation.outcome == outcome
            and evaluation.matched_profile_rule_ids == eligible_rule_ids
            and evaluation.eligible_section_ids == eligible_section_ids
        ):
            return CandidateEvaluationResult(
                publication_id=endpoint.core_publication.publication_id,
                projected_source=source,
                evaluation=evaluation,
                candidate=candidate,
                disposition="existing",
            )
    return None


def _evaluate_source(
    records: tuple[VitrineRecord, ...],
    *,
    request: CandidateDiscoveryRequest,
    portfolio: Portfolio,
    binding: PortfolioProfileBinding,
    revision: PortfolioProfileRevision,
    requirements: tuple[PortfolioProfileRequirement, ...],
    publication: PublicationRecord,
    registration: AcademicWorkRegistration | None,
    core_reference: CorePublicationSourceReference,
    source: ProjectedProducerSource,
    school_year: str,
    authorization: SourceReadAuthorizationDecision,
    now: datetime,
    id_factory: IdFactory,
) -> tuple[CandidateEvaluationResult, tuple[VitrineRecord, ...]]:
    assertions, subject_conflict = _assertions_for_source(
        records,
        source=source,
        publication=publication,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        school_year=school_year,
        verified_at=now,
        verified_by=request.requesting_actor,
        id_factory=id_factory,
    )
    endpoint = CandidateSourceEndpoint(
        core_publication=core_reference,
        producer_source=source.producer_source,
        source_artifact=source.source_artifact,
        subject_relationship_assertions=assertions,
        source_privacy=source.source_privacy,
    )
    candidate_kind, eligible_sections, rule_ids = _eligible_profile_sections(
        revision, requirements, source, assertions
    )
    if subject_conflict:
        outcome = "unresolved"
        reason_codes = ("candidate:subject_conflict",)
        condition_state = "review_required"
        subject_outcome = "conflict"
        profile_outcome = "not_evaluated"
        eligible_sections = ()
        rule_ids = ()
    elif not assertions:
        outcome = "unresolved"
        reason_codes = ("candidate:subject_unresolved",)
        condition_state = "review_required"
        subject_outcome = "unresolved"
        profile_outcome = "not_evaluated"
        eligible_sections = ()
        rule_ids = ()
    elif candidate_kind is None or not eligible_sections:
        outcome = "ineligible"
        reason_codes = ("candidate:profile_ineligible",)
        condition_state = "review_required"
        subject_outcome = "supported"
        profile_outcome = "ineligible"
        eligible_sections = ()
        rule_ids = ()
    else:
        condition_state = _condition_state(source)
        outcome = (
            "eligible"
            if condition_state == "ready_for_consideration"
            else "conditionally_eligible"
        )
        reason_codes = (
            ("candidate:eligible",)
            if outcome == "eligible"
            else ("candidate:conditional_review",)
        )
        subject_outcome = "supported"
        profile_outcome = "permitted" if outcome == "eligible" else "conditional"

    evaluation = CandidateEvaluation(
        candidate_evaluation_id=id_factory("candidate_evaluation"),
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=binding.profile_revision,
        requesting_actor=request.requesting_actor,
        purpose=request.requested_purpose,
        source_endpoint=endpoint,
        availability_observations=_availability(
            now,
            registration_present=registration is not None,
            authorization_codes=authorization.reason_codes,
            subject_outcome=subject_outcome,
            profile_outcome=profile_outcome,
        ),
        matched_profile_rule_ids=rule_ids,
        eligible_section_ids=eligible_sections,
        outcome=outcome,
        reason_codes=reason_codes,
        evaluated_at=now,
        evaluator_contract_version=CANDIDATE_EVALUATOR_CONTRACT_VERSION,
    )

    if outcome not in {"eligible", "conditionally_eligible"}:
        return (
            CandidateEvaluationResult(
                publication_id=publication.publication_id,
                projected_source=source,
                evaluation=evaluation,
                candidate=None,
                disposition="evaluation_only",
            ),
            (evaluation,),
        )

    display = _display_snapshot(source)
    existing = _existing_positive_result(
        records,
        request=request,
        portfolio=portfolio,
        binding=binding,
        endpoint=endpoint,
        eligible_rule_ids=rule_ids,
        eligible_section_ids=eligible_sections,
        outcome=outcome,
        condition_state=condition_state,
        display_snapshot=display,
        source=source,
    )
    if existing is not None:
        return existing, ()

    candidate = PortfolioCandidate(
        candidate_id=id_factory("candidate"),
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=binding.profile_revision,
        candidate_evaluation_id=evaluation.candidate_evaluation_id,
        source_endpoint=endpoint,
        eligible_profile_rule_ids=rule_ids,
        eligible_section_ids=eligible_sections,
        condition_state=condition_state,
        display_snapshot=display,
        created_at=now,
        created_by=request.requesting_actor,
    )
    return (
        CandidateEvaluationResult(
            publication_id=publication.publication_id,
            projected_source=source,
            evaluation=evaluation,
            candidate=candidate,
            disposition="created",
        ),
        (evaluation, candidate),
    )


def _process_publication(
    workspace_root: str | Path,
    row: CatalogPublication,
    *,
    records: tuple[VitrineRecord, ...],
    request: CandidateDiscoveryRequest,
    portfolio: Portfolio,
    binding: PortfolioProfileBinding,
    revision: PortfolioProfileRevision,
    requirements: tuple[PortfolioProfileRequirement, ...],
    producer_registry: PublicationProducerRegistry,
    adapter_registry: ProducerProjectionAdapterRegistry,
    authorization_gate: SourceReadAuthorizationGate,
    now: datetime,
    id_factory: IdFactory,
) -> tuple[tuple[CandidateEvaluationResult, ...], tuple[VitrineRecord, ...]]:
    publication = _load_canonical_publication(workspace_root, row)
    registration = _load_registration(workspace_root, publication)
    series_state, withdrawal_state = _series_state(workspace_root, publication)
    if series_state != "current_selectable":
        raise CandidateWorkflowError(
            "candidate.publication_not_selectable",
            "Canonical Publication is not the current selectable series head.",
            stage="series_state",
        )
    try:
        class_metadata = load_class_metadata_for_class(
            workspace_root, publication.work.class_id
        )
    except (ClassMetadataError, OSError) as error:
        raise CandidateWorkflowError(
            "candidate.subject_unresolved",
            "Canonical class context is unavailable for Subject resolution.",
            stage="subject_relationship",
        ) from error
    if row.school_year is not None and row.school_year != class_metadata.school_year:
        raise CandidateWorkflowError(
            "candidate.catalog_drift",
            "Catalog class context differs from canonical class metadata.",
            stage="canonical_publication",
        )

    profile = producer_registry.get(publication.work.module_id)
    if profile is None:
        raise CandidateWorkflowError(
            "candidate.producer_profile_missing",
            "No explicit Core producer compatibility Profile is available.",
            stage="producer_profile",
        )
    try:
        compatibility = evaluate_publication_compatibility(
            publication, profile, registration
        )
    except PublicationProducerProfileError as error:
        raise CandidateWorkflowError(
            "candidate.producer_incompatible",
            "Producer compatibility metadata could not be evaluated safely.",
            stage="producer_profile",
        ) from error
    if not compatibility.compatible:
        raise CandidateWorkflowError(
            "candidate.producer_incompatible",
            "Canonical Publication is incompatible with its producer Profile.",
            stage="producer_profile",
            diagnostic_fields=tuple(("code", code) for code in compatibility.codes),
        )

    adapter = _select_adapter(adapter_registry, _adapter_request(publication, registration))
    authorization = _authorize(
        authorization_gate,
        portfolio=portfolio,
        publication=publication,
        purpose=request.requested_purpose,
    )
    data = _read_verified_manifest_bytes(workspace_root, publication)
    sources = _project(adapter, data)

    core_reference = _core_source_reference(
        publication,
        registration,
        series_state=series_state,
        withdrawal_state=withdrawal_state,
        verified_at=now,
    )
    results: list[CandidateEvaluationResult] = []
    records_to_commit: list[VitrineRecord] = []
    for source in sources:
        if source.producer_source.producer_module_id != publication.work.module_id:
            raise CandidateWorkflowError(
                "candidate.projection_failed",
                "Projected producer identity disagrees with canonical Publication work.",
                stage="producer_parse",
            )
        result, new_records = _evaluate_source(
            records,
            request=request,
            portfolio=portfolio,
            binding=binding,
            revision=revision,
            requirements=requirements,
            publication=publication,
            registration=registration,
            core_reference=core_reference,
            source=source,
            school_year=class_metadata.school_year,
            authorization=authorization,
            now=now,
            id_factory=id_factory,
        )
        results.append(result)
        records_to_commit.extend(new_records)

    final_series_state, final_withdrawal_state = _series_state(
        workspace_root, publication
    )
    if (final_series_state, final_withdrawal_state) != (
        series_state,
        withdrawal_state,
    ) or final_series_state != "current_selectable":
        raise CandidateWorkflowError(
            "candidate.publication_not_selectable",
            "Canonical Publication state changed during Candidate evaluation.",
            stage="series_state",
        )
    final_bytes = _read_verified_manifest_bytes(workspace_root, publication)
    if final_bytes != data:
        raise CandidateWorkflowError(
            "candidate.manifest_integrity_failed",
            "Publication manifest bytes changed during Candidate evaluation.",
            stage="manifest_integrity",
        )
    return tuple(results), tuple(records_to_commit)


def discover_and_evaluate_candidates(
    workspace_root: str | Path,
    request: CandidateDiscoveryRequest,
    *,
    producer_registry: PublicationProducerRegistry,
    adapter_registry: ProducerProjectionAdapterRegistry,
    authorization_gate: SourceReadAuthorizationGate,
    clock: Clock = _clock,
    id_factory: IdFactory = _id,
) -> CandidateDiscoveryResult:
    """Discover, verify, evaluate, and persist Candidates under one exact context."""

    if not isinstance(request, CandidateDiscoveryRequest):
        raise CandidateWorkflowError(
            "candidate.invalid_request",
            "request must be CandidateDiscoveryRequest.",
            stage="request",
        )
    if not isinstance(producer_registry, PublicationProducerRegistry):
        raise CandidateWorkflowError(
            "candidate.invalid_request",
            "producer_registry must be an explicit PublicationProducerRegistry.",
            stage="request",
        )
    if not isinstance(adapter_registry, ProducerProjectionAdapterRegistry):
        raise CandidateWorkflowError(
            "candidate.invalid_request",
            "adapter_registry must be an explicit ProducerProjectionAdapterRegistry.",
            stage="request",
        )

    records, portfolio, _subject, binding, revision, requirements = _load_vitrine_context(
        workspace_root, request
    )
    try:
        rows = query_publication_catalog(workspace_root, request.catalog_query)
    except (
        AcademicCatalogNotFoundError,
        AcademicCatalogCompatibilityError,
        AcademicCatalogConflictError,
        AcademicCatalogIntegrityError,
        AcademicCatalogReadError,
        AcademicCatalogSourceError,
    ) as error:
        failure = _catalog_failure(error)
        return CandidateDiscoveryResult(
            proposed_publication_ids=(),
            findings=(_finding(failure, None),),
            evaluation_results=(),
            committed_state_revision=None,
        )

    proposed = tuple(row.publication_id for row in rows)
    if not rows:
        return CandidateDiscoveryResult(
            proposed_publication_ids=(),
            findings=(
                CandidateDiscoveryFinding(
                    code="candidate.no_matching_publication",
                    stage="catalog",
                ),
            ),
            evaluation_results=(),
            committed_state_revision=None,
        )

    now = _aware_utc(clock())
    findings: list[CandidateDiscoveryFinding] = []
    results: list[CandidateEvaluationResult] = []
    new_records: list[VitrineRecord] = []
    for row in rows:
        try:
            publication_results, publication_records = _process_publication(
                workspace_root,
                row,
                records=records,
                request=request,
                portfolio=portfolio,
                binding=binding,
                revision=revision,
                requirements=requirements,
                producer_registry=producer_registry,
                adapter_registry=adapter_registry,
                authorization_gate=authorization_gate,
                now=now,
                id_factory=id_factory,
            )
        except CandidateWorkflowError as error:
            findings.append(_finding(error, row.publication_id))
            continue
        results.extend(publication_results)
        new_records.extend(publication_records)

    committed_revision: int | None = None
    if new_records:
        try:
            commit = commit_record_batch(
                workspace_root,
                new_records,
                expected_state_revision=request.expected_state_revision,
            )
        except VitrineStorageConflictError as error:
            raise CandidateWorkflowError(
                "candidate.state_conflict",
                "Vitrine state changed before Candidate persistence.",
                stage="persistence",
            ) from error
        committed_revision = commit.state_revision

    return CandidateDiscoveryResult(
        proposed_publication_ids=proposed,
        findings=tuple(findings),
        evaluation_results=tuple(results),
        committed_state_revision=committed_revision,
    )


__all__ = [
    "CANDIDATE_EVALUATOR_CONTRACT_VERSION",
    "CANDIDATE_KIND_BY_ARTIFACT_KIND",
    "CANDIDATE_WORKFLOW_CODES",
    "SOURCE_READ_OPERATION",
    "CandidateDiscoveryFinding",
    "CandidateDiscoveryRequest",
    "CandidateDiscoveryResult",
    "CandidateEvaluationResult",
    "CandidateWorkflowError",
    "SourceReadAuthorizationDecision",
    "SourceReadAuthorizationGate",
    "SourceReadAuthorizationRequest",
    "discover_and_evaluate_candidates",
]
